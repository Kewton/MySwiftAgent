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
from ..utils.jobqueue_client import JobqueueAPIError, JobqueueClient
from ..utils.llm_invocation import StructuredLLMError, invoke_structured_llm
from ..utils.schema_matcher import SchemaMatcher

logger = logging.getLogger(__name__)


def normalize_json_schema_properties(schema: dict[str, Any]) -> dict[str, Any]:
    """Normalize LLM-generated JSON Schema to valid JSON Schema Draft 7.

    This function fixes common LLM errors where property types are specified as
    shorthand formats instead of proper JSON Schema objects:
    - "string" → {"type": "string"} (bare string type)
    - ["string"] → {"type": "string"} (array shorthand)
    - ["boolean"] → {"type": "boolean"}
    - ["array"] → {"type": "array"}
    - ["object"] → {"type": "object"}
    - ["integer"] → {"type": "integer"}
    - ["number"] → {"type": "number"}

    Additionally (Issue #293):
    - Removes metadata fields that should not be in JSON Schema
    - Handles non-dict "properties" values by converting to empty object

    Args:
        schema: JSON Schema dictionary (input_schema or output_schema)

    Returns:
        Normalized JSON Schema dictionary with correct property definitions

    Examples:
        >>> schema = {"properties": {"name": "string"}}
        >>> normalize_json_schema_properties(schema)
        {"properties": {"name": {"type": "string"}}}

        >>> schema = {"properties": {"name": ["string"]}}
        >>> normalize_json_schema_properties(schema)
        {"properties": {"name": {"type": "string"}}}

        >>> schema = {"properties": {"active": ["boolean"], "count": ["integer"]}}
        >>> normalize_json_schema_properties(schema)
        {"properties": {"active": {"type": "boolean"}, "count": {"type": "integer"}}}

        >>> schema = {"properties": "boolean", "task_id": "task_001"}
        >>> normalize_json_schema_properties(schema)
        {"properties": {}}
    """
    valid_types = {"string", "boolean", "array", "object", "integer", "number", "null"}

    # Issue #293: Metadata fields that LLM sometimes incorrectly includes in JSON Schema
    # These should be filtered out as they are not valid JSON Schema keywords
    metadata_fields_to_remove = {
        "task_id",
        "interface_name",
        "output_schema",  # When incorrectly nested inside input_schema
        "input_schema",  # When incorrectly nested inside output_schema
    }

    def normalize_value(value: Any, prop_name: str = "") -> Any:
        """Normalize a single value in the schema."""
        # Handle null/None value - LLM sometimes generates null instead of type definition
        if value is None:
            logger.warning(
                f"Found null value for property '{prop_name}', defaulting to {{'type': 'string'}}"
            )
            return {"type": "string"}
        # Handle integer values (likely misplaced schema keywords like minLength)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            logger.warning(
                f"Found numeric value {value} for property '{prop_name}', "
                f"converting to {{'type': 'integer', 'default': {value}}}"
            )
            if isinstance(value, int):
                return {"type": "integer", "default": value}
            else:
                return {"type": "number", "default": value}
        # Handle bare string type like "string", "boolean", etc.
        if isinstance(value, str):
            if value in valid_types:
                logger.debug(
                    f"Normalizing bare string type '{value}' → {{'type': '{value}'}}"
                )
                return {"type": value}
            else:
                # Handle arbitrary strings (likely descriptions placed incorrectly)
                logger.warning(
                    f"Found non-type string '{value[:50]}...' for property '{prop_name}', "
                    f"converting to {{'type': 'string', 'description': ...}}"
                )
                return {"type": "string", "description": value}
        # Handle array shorthand like ["string"]
        if isinstance(value, list):
            # Check if it's a shorthand type like ["string"]
            if (
                len(value) == 1
                and isinstance(value[0], str)
                and value[0] in valid_types
            ):
                type_name = value[0]
                logger.debug(
                    f"Normalizing shorthand type [{type_name}] → {{'type': '{type_name}'}}"
                )
                return {"type": type_name}
            # Check if it's a malformed enum pattern like:
            # [{'type': 'string', 'description': 'NEUTRAL'}, {'type': 'string', 'description': 'MALE'}]
            # This should be converted to: {"type": "string", "enum": ["NEUTRAL", "MALE"]}
            if (
                len(value) > 0
                and all(isinstance(item, dict) for item in value)
                and all("type" in item and "description" in item for item in value)
            ):
                # Extract enum values from description fields
                enum_values = [item.get("description", "") for item in value]
                base_type = value[0].get("type", "string")
                logger.warning(
                    f"Found malformed enum pattern for property '{prop_name}', "
                    f"converting to {{'type': '{base_type}', 'enum': {enum_values}}}"
                )
                return {"type": base_type, "enum": enum_values}
            # It might be an array with objects inside (e.g., items in allOf)
            return [normalize_value(item) for item in value]
        elif isinstance(value, dict):
            return normalize_schema_dict(value)
        return value

    # JSON Schema keywords that contain string arrays (property names, type names, etc.)
    # These should NOT be normalized as they are not schema definitions
    string_array_keywords = {
        "required",
        "enum",
        "allOf",
        "anyOf",
        "oneOf",
        "dependencies",
    }

    def normalize_schema_dict(obj: dict[str, Any]) -> dict[str, Any]:
        """Recursively normalize all fields in a schema dict."""
        result: dict[str, Any] = {}
        for key, value in obj.items():
            # Issue #293: Remove metadata fields that should not be in JSON Schema
            if key in metadata_fields_to_remove:
                logger.warning(
                    f"Removing metadata field '{key}' from JSON Schema "
                    f"(value: {str(value)[:50]}...)"
                )
                continue

            if key == "properties":
                # Issue #293: Handle non-dict properties values
                if not isinstance(value, dict):
                    logger.warning(
                        f"properties is not a dict ({type(value).__name__}: {value}), "
                        "converting to empty object"
                    )
                    result[key] = {}
                else:
                    # Normalize each property
                    result[key] = {}
                    for prop_name, prop_value in value.items():
                        result[key][prop_name] = normalize_value(prop_value, prop_name)
            elif key == "items" and isinstance(value, (dict, list)):
                # Handle array items
                result[key] = normalize_value(value, "items")
            elif key in string_array_keywords:
                # Don't normalize string arrays like "required", "enum", etc.
                result[key] = value
            elif isinstance(value, dict):
                result[key] = normalize_schema_dict(value)
            elif isinstance(value, list):
                result[key] = [normalize_value(item, key) for item in value]
            else:
                result[key] = value
        return result

    if not isinstance(schema, dict):
        return schema

    return normalize_schema_dict(schema)


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

    # Internal retry loop for LLM call (handles transient validation failures)
    max_internal_retries = 3
    last_error: StructuredLLMError | None = None

    for attempt in range(max_internal_retries):
        try:
            call_result = await invoke_structured_llm(
                messages=messages,
                response_model=InterfaceSchemaResponse,
                context_label="interface_definition",
                model_env_var="JOB_GENERATOR_INTERFACE_DEFINITION_MODEL",
                default_model="claude-haiku-4-5",
                validator=_validate_interface_response,
            )
            # Success - break out of retry loop
            break
        except StructuredLLMError as exc:
            last_error = exc
            logger.warning(
                "Interface schema generation attempt %d/%d failed: %s",
                attempt + 1,
                max_internal_retries,
                exc,
            )
            if attempt < max_internal_retries - 1:
                logger.info("Retrying interface schema generation...")
                continue
            # All retries exhausted
            logger.error(
                "Interface schema generation failed after %d attempts: %s",
                max_internal_retries,
                exc,
            )
            new_retry = state.get("retry_count", 0) + 1
            return {
                **state,
                "error_message": str(exc),
                "retry_count": new_retry,
            }
    else:
        # This should not happen, but handle it just in case
        if last_error:
            new_retry = state.get("retry_count", 0) + 1
            return {
                **state,
                "error_message": str(last_error),
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
        # First normalize shorthand types like ["string"] → {"type": "string"}
        iface.input_schema = normalize_json_schema_properties(iface.input_schema)
        iface.output_schema = normalize_json_schema_properties(iface.output_schema)
        # Then fix over-escaped regex patterns
        iface.input_schema = fix_regex_over_escaping(iface.input_schema)
        iface.output_schema = fix_regex_over_escaping(iface.output_schema)

    client = JobqueueClient()
    matcher = SchemaMatcher(client)
    interface_masters: dict[str, dict[str, Any]] = {}
    # Issue #293: Collect schema validation errors for evaluator feedback
    schema_validation_errors: list[dict[str, Any]] = []

    for interface_def in response.interfaces:
        task_id = interface_def.task_id
        interface_name = interface_def.interface_name

        logger.info(
            "Registering interface for task %s (%s)",
            task_id,
            interface_name,
        )

        try:
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
        except JobqueueAPIError as e:
            # Issue #293: Capture schema validation errors for evaluator feedback
            logger.warning(
                "Schema validation failed for task %s (%s): %s",
                task_id,
                interface_name,
                e.message,
            )
            schema_validation_errors.append(
                {
                    "task_id": task_id,
                    "interface_name": interface_name,
                    "error": e.message,
                    "input_schema": interface_def.input_schema,
                    "output_schema": interface_def.output_schema,
                }
            )
            continue

    # Increment retry_count if this is a retry (from evaluator or validation)
    # Issue #293: Also increment if there are schema validation errors
    current_retry = state.get("retry_count", 0)
    evaluation_feedback = state.get("evaluation_feedback")
    validation_result = state.get("validation_result")

    if (
        evaluation_feedback
        or (validation_result and not validation_result.get("is_valid", True))
        or schema_validation_errors  # Issue #293: Increment on schema errors
    ):
        updated_retry = current_retry + 1
    else:
        updated_retry = 0

    if schema_validation_errors:
        logger.warning(
            "Interface definition node completed with %s schema validation errors",
            len(schema_validation_errors),
        )
    logger.info(
        "Interface definition node completed with %s interfaces",
        len(interface_masters),
    )

    return {
        **state,
        "interface_definitions": interface_masters,
        "evaluator_stage": "after_interface_definition",
        "retry_count": updated_retry,
        # Issue #293: Include schema validation errors for evaluator feedback
        "schema_validation_errors": schema_validation_errors,
    }
