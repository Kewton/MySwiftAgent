"""Sample input generator node for workflow testing.

This module provides the sample input generator node that creates sample
user_input data from Input Interface JSON Schema for workflow testing.
"""

import logging
from typing import Any

from ..state import WorkflowGeneratorState

logger = logging.getLogger(__name__)


SchemaValue = dict[str, Any] | str | int | float | bool | list[Any] | None


def _first_dict(items: list[Any]) -> dict[str, Any]:
    for candidate in items:
        if isinstance(candidate, dict):
            return candidate
    return {}


def _resolve_schema(schema: dict[str, Any]) -> dict[str, Any]:
    if "oneOf" in schema and isinstance(schema["oneOf"], list):
        return _first_dict(schema["oneOf"])
    if "anyOf" in schema and isinstance(schema["anyOf"], list):
        return _first_dict(schema["anyOf"])
    if "allOf" in schema and isinstance(schema["allOf"], list):
        merged = {}
        for part in schema["allOf"]:
            if isinstance(part, dict):
                merged.update(part)
        return merged or schema
    return schema


def _enum_or_default(schema: dict[str, Any]) -> SchemaValue:
    if "const" in schema:
        return schema["const"]  # type: ignore[no-any-return]
    enums = schema.get("enum")
    if isinstance(enums, list) and enums:
        return enums[0]  # type: ignore[no-any-return]
    examples = schema.get("examples")
    if isinstance(examples, list) and examples:
        return examples[0]  # type: ignore[no-any-return]
    default = schema.get("default")
    if default is not None:
        return default  # type: ignore[no-any-return]
    example = schema.get("example")
    if example is not None:
        return example  # type: ignore[no-any-return]
    return None


def _normalise_type(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        for entry in value:
            if entry != "null":
                return str(entry)
        if value:
            return str(value[0])
    return None


def _generate_sample_from_schema(schema: dict[str, Any]) -> SchemaValue:
    schema = _resolve_schema(schema)

    enum_value = _enum_or_default(schema)
    if enum_value is not None:
        return enum_value

    schema_type = _normalise_type(schema.get("type")) or "object"

    if schema_type == "object":
        properties = schema.get("properties", {})
        if not isinstance(properties, dict):
            properties = {}
        sample: dict[str, Any] = {}
        for prop_name, prop_schema in properties.items():
            if not isinstance(prop_schema, dict):
                sample[prop_name] = None
                continue
            sample[prop_name] = _generate_sample_from_schema(prop_schema)
        return sample

    if schema_type == "array":
        items_schema = schema.get("items", {})
        if isinstance(items_schema, list) and items_schema:
            items_schema = _first_dict(items_schema)
        if not isinstance(items_schema, dict):
            items_schema = {}
        return [_generate_sample_from_schema(items_schema)]

    if schema_type == "string":
        pattern = schema.get("pattern")
        if pattern:
            return f"sample_matching_{pattern[:12]}"
        return "sample_text"

    if schema_type == "integer":
        return 1

    if schema_type == "number":
        return 1.0

    if schema_type == "boolean":
        return True

    if schema_type == "null":
        return None

    return {}


async def sample_input_generator_node(
    state: WorkflowGeneratorState,
) -> WorkflowGeneratorState:
    """Generate sample user_input from Input Interface JSON Schema.

    This node:
    1. Extracts Input Interface JSON Schema from task_data
    2. Generates sample data matching the schema
    3. Updates state with sample_input

    Args:
        state: Current workflow generator state

    Returns:
        Updated state with sample_input
    """
    logger.info("Starting sample input generator node")

    task_data = state.get("task_data")
    if task_data is None:
        message = "Sample input generation failed: task_data missing"
        logger.error(message)
        return {
            **state,
            "status": "failed",
            "error_message": message,
        }
    input_interface = task_data.get("input_interface", {})
    input_schema = input_interface.get("schema", {})

    logger.debug(f"Input schema: {input_schema}")

    try:
        # Generate sample input from schema
        sample_input = _generate_sample_from_schema(input_schema)

        logger.info(f"Generated sample input: {sample_input}")
        logger.debug(f"Sample input type: {type(sample_input)}")

        # Update state
        return {
            **state,
            "sample_input": sample_input,
            "status": "sample_input_generated",
        }

    except Exception as e:
        logger.error(
            "Error during sample input generation: %s",
            e,
            exc_info=True,
        )
        return {
            **state,
            "status": "failed",
            "error_message": f"Sample input generation failed: {str(e)}",
        }
