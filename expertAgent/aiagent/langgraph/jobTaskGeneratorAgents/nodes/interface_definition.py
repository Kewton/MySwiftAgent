"""Interface definition node for job task generator.

This module provides the interface definition node that generates JSON Schema
definitions for task inputs and outputs, then creates or finds existing
InterfaceMasters in jobqueue.
"""

import logging
from typing import Any

from langchain_anthropic import ChatAnthropic

from ..prompts.interface_schema import (
    INTERFACE_SCHEMA_SYSTEM_PROMPT,
    InterfaceSchemaResponse,
    create_interface_schema_prompt,
)
from ..state import JobTaskGeneratorState
from ..utils.jobqueue_client import JobqueueClient
from ..utils.schema_matcher import SchemaMatcher

logger = logging.getLogger(__name__)


async def interface_definition_node(
    state: JobTaskGeneratorState,
) -> JobTaskGeneratorState:
    """Define interfaces and create/find InterfaceMasters.

    This node:
    1. Generates JSON Schema definitions for task I/O using LLM
    2. Searches for existing InterfaceMasters by name
    3. Creates new InterfaceMasters if not found
    4. Returns InterfaceMaster IDs mapped to task IDs

    Args:
        state: Current job task generator state

    Returns:
        Updated state with interface definitions
    """
    logger.info("Starting interface definition node")

    task_breakdown = state.get("task_breakdown", [])
    if not task_breakdown:
        logger.error("Task breakdown is empty")
        return {
            **state,
            "error_message": "Task breakdown is required for interface definition",
        }

    logger.debug(f"Task breakdown count: {len(task_breakdown)}")

    # Initialize LLM (claude-haiku-4-5)
    model = ChatAnthropic(
        model="claude-3-5-haiku-20241022",  # claude-haiku-4-5
        temperature=0.0,
    )

    # Create structured output model
    structured_model = model.with_structured_output(InterfaceSchemaResponse)

    # Create prompt
    user_prompt = create_interface_schema_prompt(task_breakdown)
    logger.debug(f"Created interface schema prompt (length: {len(user_prompt)})")

    try:
        # Invoke LLM
        messages = [
            {"role": "system", "content": INTERFACE_SCHEMA_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        logger.info("Invoking LLM for interface schema definition")
        response = await structured_model.ainvoke(messages)

        logger.info(
            f"Interface schema definition completed: {len(response.interfaces)} interfaces"
        )
        logger.debug(
            f"Interfaces: {[iface.interface_name for iface in response.interfaces]}"
        )

        # Initialize jobqueue client and schema matcher
        client = JobqueueClient()
        matcher = SchemaMatcher(client)

        # Find or create InterfaceMasters
        interface_masters: dict[str, dict[str, Any]] = {}

        for interface_def in response.interfaces:
            task_id = interface_def.task_id
            interface_name = interface_def.interface_name

            logger.info(
                f"Processing interface for task {task_id}: {interface_name}"
            )

            # Find or create InterfaceMaster
            interface_master = await matcher.find_or_create_interface_master(
                name=interface_name,
                description=interface_def.description,
                input_schema=interface_def.input_schema,
                output_schema=interface_def.output_schema,
            )

            interface_masters[task_id] = {
                "interface_master_id": interface_master["id"],
                "interface_name": interface_name,
                "input_schema": interface_def.input_schema,
                "output_schema": interface_def.output_schema,
            }

            logger.info(
                f"Interface for task {task_id}: {interface_master['id']} ({interface_name})"
            )

        # Update state
        return {
            **state,
            "interface_definitions": interface_masters,
            "retry_count": 0,
        }

    except Exception as e:
        logger.error(f"Failed to define interfaces: {e}", exc_info=True)
        return {
            **state,
            "error_message": f"Interface definition failed: {str(e)}",
        }
