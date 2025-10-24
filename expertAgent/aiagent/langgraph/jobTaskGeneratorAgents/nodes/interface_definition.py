"""Interface definition node for job task generator.

This module provides the interface definition node that generates JSON Schema
definitions for task inputs and outputs, then creates or finds existing
InterfaceMasters in jobqueue.
"""

import logging
import os
from typing import Any

from ..prompts.interface_schema import (
    INTERFACE_SCHEMA_SYSTEM_PROMPT,
    InterfaceSchemaResponse,
    create_interface_schema_prompt,
)
from ..state import JobTaskGeneratorState
from ..utils.jobqueue_client import JobqueueClient
from ..utils.llm_factory import create_llm_with_fallback
from ..utils.schema_matcher import SchemaMatcher

logger = logging.getLogger(__name__)


def fix_regex_over_escaping(schema: dict[str, Any]) -> dict[str, Any]:
    """Fix over-escaped regex patterns in JSON Schema.

    This function fixes common over-escaping issues in JSON Schema patterns:
    - Quadruple backslash (\\\\) → Double backslash (\\)
    - Sextuple backslash (\\\\\\) → Double backslash (\\)

    LLMs sometimes generate over-escaped regex patterns when creating JSON Schema.
    For example, they might generate "\\\\d{4}" instead of "\\d{4}".
    This causes JSON Schema V7 validation to fail with "is not a 'regex'" error.

    Args:
        schema: JSON Schema dictionary (input_schema or output_schema)

    Returns:
        Fixed JSON Schema dictionary with corrected regex patterns

    Examples:
        >>> schema = {"pattern": "^\\\\\\\\d{4}$"}
        >>> fix_regex_over_escaping(schema)
        {"pattern": "^\\\\d{4}$"}

        >>> schema = {"properties": {"name": {"pattern": "^[\\\\\\\\p{L}]+$"}}}
        >>> fix_regex_over_escaping(schema)
        {"properties": {"name": {"pattern": "^[\\\\p{L}]+$"}}}
    """

    def fix_pattern_value(value: str) -> str:
        """Fix a single pattern string by reducing over-escaping."""
        original = value

        # Fix quadruple backslash → double backslash
        # Examples: \\\\d → \\d, \\\\p{L} → \\p{L}, \\\\s → \\s
        fixed = value.replace("\\\\\\\\", "\\\\")

        # Fix sextuple backslash → double backslash (rare but possible)
        fixed = fixed.replace("\\\\\\\\\\\\", "\\\\")

        if original != fixed:
            logger.debug(
                f"Fixed over-escaped regex pattern:\n"
                f"  Before: {original}\n"
                f"  After:  {fixed}"
            )

        return fixed

    def traverse_and_fix(obj: Any) -> Any:
        """Recursively traverse and fix all pattern fields in the schema."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "pattern" and isinstance(value, str):
                    # Fix the pattern string
                    obj[key] = fix_pattern_value(value)
                else:
                    # Recursively process nested objects
                    obj[key] = traverse_and_fix(value)
        elif isinstance(obj, list):
            return [traverse_and_fix(item) for item in obj]

        return obj

    return traverse_and_fix(schema)


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

    # Initialize LLM with fallback mechanism (Issue #111)
    max_tokens = int(os.getenv("JOB_GENERATOR_MAX_TOKENS", "8192"))
    model_name = os.getenv(
        "JOB_GENERATOR_INTERFACE_DEFINITION_MODEL", "claude-haiku-4-5"
    )
    model, perf_tracker, cost_tracker = create_llm_with_fallback(
        model_name=model_name,
        temperature=0.0,
        max_tokens=max_tokens,
    )
    logger.debug(f"Using model={model_name}, max_tokens={max_tokens}")

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

        # Validate response
        if response is None or not hasattr(response, "interfaces"):
            logger.error("LLM response is None or missing 'interfaces' attribute")
            raise ValueError(
                "Interface definition failed: LLM returned invalid response"
            )

        logger.info(
            f"Interface schema definition completed: {len(response.interfaces)} interfaces"
        )
        logger.debug(
            f"Interfaces: {[iface.interface_name for iface in response.interfaces]}"
        )

        # Fix over-escaped regex patterns in schemas (Phase 3-A)
        logger.info("Applying regex over-escaping fix to interface schemas")
        for iface in response.interfaces:
            # Fix regex patterns in input and output schemas
            iface.input_schema = fix_regex_over_escaping(iface.input_schema)
            iface.output_schema = fix_regex_over_escaping(iface.output_schema)

        # Log detailed response for debugging (enhanced logging)
        for iface in response.interfaces:
            logger.debug(
                f"Interface {iface.task_id} ({iface.interface_name}):\n"
                f"  Input Schema (after fix): {iface.input_schema}\n"
                f"  Output Schema (after fix): {iface.output_schema}"
            )

        # Initialize jobqueue client and schema matcher
        client = JobqueueClient()
        matcher = SchemaMatcher(client)

        # Find or create InterfaceMasters
        interface_masters: dict[str, dict[str, Any]] = {}

        for interface_def in response.interfaces:
            task_id = interface_def.task_id
            interface_name = interface_def.interface_name

            logger.info(f"Processing interface for task {task_id}: {interface_name}")

            # Find or create InterfaceMaster
            interface_master = await matcher.find_or_create_interface_master(
                name=interface_name,
                description=interface_def.description,
                input_schema=interface_def.input_schema,
                output_schema=interface_def.output_schema,
            )

            # Enhanced error handling: Log response and validate structure
            logger.debug(
                f"InterfaceMaster response for task {task_id}: {interface_master}"
            )

            # Defensive programming: Check if 'id' field exists
            if "id" not in interface_master:
                error_msg = (
                    f"InterfaceMaster response missing 'id' field for task {task_id}.\n"
                    f"Interface name: {interface_name}\n"
                    f"Response content: {interface_master}\n"
                    f"Response keys: {list(interface_master.keys()) if isinstance(interface_master, dict) else 'Not a dict'}"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

            interface_masters[task_id] = {
                "interface_master_id": interface_master["id"],
                "input_interface_id": interface_master["id"],  # Explicit input interface ID
                "output_interface_id": interface_master["id"],  # Explicit output interface ID
                "interface_name": interface_name,
                "input_schema": interface_def.input_schema,
                "output_schema": interface_def.output_schema,
            }

            logger.info(
                f"Interface for task {task_id}: {interface_master['id']} ({interface_name})"
            )
            logger.debug(
                f"Interface definition for task {task_id}:\n"
                f"  input_interface_id: {interface_master['id']}\n"
                f"  output_interface_id: {interface_master['id']}"
            )

        # Update state
        current_stage = state.get("evaluator_stage", "after_task_breakdown")
        new_stage = "after_interface_definition"
        current_retry = state.get("retry_count", 0)
        new_retry = current_retry + 1 if current_retry > 0 else 0

        logger.info("=" * 80)
        logger.info("✅ Interface definition node completed successfully")
        logger.info(f"📋 Created {len(interface_masters)} interface definitions")
        logger.info(f"🔄 Stage transition: {current_stage} → {new_stage}")
        logger.info(f"🔄 Retry count: {current_retry} → {new_retry}")
        logger.info(
            "⚠️  CRITICAL: Returning state with evaluator_stage='after_interface_definition'"
        )
        logger.info("=" * 80)

        return {
            **state,
            "interface_definitions": interface_masters,
            "evaluator_stage": new_stage,
            "retry_count": new_retry,
        }

    except Exception as e:
        logger.error(f"Failed to define interfaces: {e}", exc_info=True)

        # Increment retry_count to enable proper retry logic
        current_retry = state.get("retry_count", 0)
        new_retry = current_retry + 1

        logger.warning(
            f"🔄 Interface definition failed, retry count: {current_retry} → {new_retry}"
        )

        return {
            **state,
            "error_message": f"Interface definition failed: {str(e)}",
            "retry_count": new_retry,
        }
