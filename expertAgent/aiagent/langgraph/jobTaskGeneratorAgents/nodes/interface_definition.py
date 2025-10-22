"""Interface definition node for job task generator.

This module provides the interface definition node that generates JSON Schema
definitions for task inputs and outputs, then creates or finds existing
InterfaceMasters in jobqueue.
"""

import logging
import os
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

    # Initialize LLM (claude-haiku-4-5) - Faster execution with improved error handling
    max_tokens = int(os.getenv("JOB_GENERATOR_MAX_TOKENS", "8192"))
    model = ChatAnthropic(
        model="claude-haiku-4-5",
        temperature=0.0,
        max_tokens=max_tokens,
    )
    logger.debug(f"Using model=claude-haiku-4-5, max_tokens={max_tokens}")

    # Create structured output model
    # Set include_raw=True to debug any parsing errors
    structured_model = model.with_structured_output(
        InterfaceSchemaResponse,
        method="json_mode",  # Use JSON mode instead of function calling
        include_raw=False
    )

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

        # First get the raw response to see what the LLM is actually returning
        raw_model = ChatAnthropic(
            model="claude-haiku-4-5",
            temperature=0.0,
            max_tokens=max_tokens,
        )
        raw_response = await raw_model.ainvoke(messages)
        raw_content = str(raw_response.content)

        # Save raw response to file for debugging
        with open('/tmp/interface_definition_raw_response.txt', 'w', encoding='utf-8') as f:
            f.write(raw_content)

        # Manual parsing to handle markdown-wrapped JSON
        import json
        import re

        # Strip markdown code blocks if present
        content_stripped = raw_content.strip()
        if content_stripped.startswith("```json"):
            # Remove ```json at start and ``` at end
            content_stripped = re.sub(r'^```json\s*', '', content_stripped)
            content_stripped = re.sub(r'\s*```$', '', content_stripped)

        # Parse JSON manually
        try:
            json_data = json.loads(content_stripped)
            response = InterfaceSchemaResponse(**json_data)
        except Exception as parse_error:
            logger.debug(f"Manual parsing failed: {parse_error}, falling back to structured output")
            # Fallback to structured output
            response = await structured_model.ainvoke(messages)

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
                "interface_name": interface_name,
                "input_schema": interface_def.input_schema,
                "output_schema": interface_def.output_schema,
            }

            logger.info(
                f"Interface for task {task_id}: {interface_master['id']} ({interface_name})"
            )

        # Update state
        # Do NOT modify retry_count here - validation_node manages retry logic
        return {
            **state,
            "interface_definitions": interface_masters,
            "evaluator_stage": "after_interface_definition",
            # Note: retry_count is NOT reset here to prevent infinite loop
            # validation_node increments retry_count on failure
            # validation success (is_valid=True) should be the only place to reset
        }

    except Exception as e:
        logger.error(f"Failed to define interfaces: {e}", exc_info=True)
        return {
            **state,
            "error_message": f"Interface definition failed: {str(e)}",
        }
