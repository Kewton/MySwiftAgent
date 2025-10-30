"""Interface definition node for job task generator.

This module provides the interface definition node that generates JSON Schema
definitions for task inputs and outputs, then creates or finds existing
InterfaceMasters in jobqueue.
"""

import logging
from typing import Any

from ..prompts.interface_schema import (
    INTERFACE_SCHEMA_SYSTEM_PROMPT,
    InterfaceSchemaResponse,
    create_interface_schema_prompt,
)
from ..state import JobTaskGeneratorState
from ..utils.jobqueue_client import JobqueueClient
from ..utils.llm_invocation import StructuredLLMError, invoke_structured_llm
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
        LLMs sometimes generate over-escaped regex patterns when creating JSON
        Schema.
        For example, they might generate "\\\\d{4}" instead of "\\d{4}".
        This causes JSON Schema V7 validation to fail with "is not a 'regex'"
        error.

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

    result = traverse_and_fix(schema)
    return result if isinstance(result, dict) else {}


def _validate_interface_response(
    response: InterfaceSchemaResponse | None,
) -> InterfaceSchemaResponse:
    """Ensure the LLM response contains interface definitions."""

    if response is None:
        logger.error(
            "LLM structured output returned None for interface definition",
        )
        raise ValueError(
            "Interface definition failed: structured output was empty.",
        )

    if not response.interfaces:
        logger.error("LLM structured output missing interfaces array")
        raise ValueError(
            "Interface definition failed: no interfaces were generated.",
        )

    return response


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
        message = "Interface definition requires a task breakdown"
        logger.error(message)
        return {**state, "error_message": message}

    logger.debug("Task breakdown count: %s", len(task_breakdown))

    user_prompt = create_interface_schema_prompt(task_breakdown)
    messages = [
        {"role": "system", "content": INTERFACE_SCHEMA_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        call_result = await invoke_structured_llm(
            messages=messages,
            response_model=InterfaceSchemaResponse,
            context_label="interface_definition",
            model_env_var="JOB_GENERATOR_INTERFACE_DEFINITION_MODEL",
            default_model="claude-haiku-4-5",
            validator=_validate_interface_response,
        )
    except StructuredLLMError as exc:
        logger.error("Interface schema generation failed: %s", exc)
        new_retry = state.get("retry_count", 0) + 1
        return {
            **state,
            "error_message": str(exc),
            "retry_count": new_retry,
        }

    response = call_result.result
    logger.info(
        "Generated %s interface candidates (model=%s)",
        len(response.interfaces),
        call_result.model_name,
    )
    if call_result.recovered_via_json:
        logger.info("Interface schema generation succeeded via JSON fallback")

    for iface in response.interfaces:
        iface.input_schema = fix_regex_over_escaping(iface.input_schema)
        iface.output_schema = fix_regex_over_escaping(iface.output_schema)

    client = JobqueueClient()
    matcher = SchemaMatcher(client)
    interface_masters: dict[str, dict[str, Any]] = {}

    for interface_def in response.interfaces:
        task_id = interface_def.task_id
        interface_name = interface_def.interface_name

        logger.info(
            "Registering interface for task %s (%s)",
            task_id,
            interface_name,
        )

        interface_master = await matcher.find_or_create_interface_master(
            name=interface_name,
            description=interface_def.description,
            input_schema=interface_def.input_schema,
            output_schema=interface_def.output_schema,
        )

        master_id = interface_master.get("id")
        if not master_id:
            logger.error(
                "InterfaceMaster response missing id for task %s: %s",
                task_id,
                interface_master,
            )
            raise ValueError(f"InterfaceMaster creation failed for task {task_id}")

        interface_masters[task_id] = {
            "interface_master_id": master_id,
            "input_interface_id": master_id,
            "output_interface_id": master_id,
            "interface_name": interface_name,
            "input_schema": interface_def.input_schema,
            "output_schema": interface_def.output_schema,
        }

    # Increment retry_count if this is a retry (from evaluator or validation)
    current_retry = state.get("retry_count", 0)
    evaluation_feedback = state.get("evaluation_feedback")
    validation_result = state.get("validation_result")

    if evaluation_feedback or (
        validation_result and not validation_result.get("is_valid", True)
    ):
        updated_retry = current_retry + 1
    else:
        updated_retry = 0

    logger.info(
        "Interface definition node completed with %s interfaces",
        len(interface_masters),
    )

    return {
        **state,
        "interface_definitions": interface_masters,
        "evaluator_stage": "after_interface_definition",
        "retry_count": updated_retry,
    }
