"""Sample input generator node for workflow testing.

This module provides the sample input generator node that creates sample
user_input data from Input Interface JSON Schema for workflow testing.

Issue #340: Added object array validation for stringTemplateAgent inputs
to prevent [object Object] conversion issues.
"""

import logging
from typing import Any

import yaml

from ..state import WorkflowGeneratorState

logger = logging.getLogger(__name__)


def _get_string_template_input_fields(yaml_content: str) -> set[str]:
    """Extract user_input field names used by stringTemplateAgent nodes.

    This function parses the workflow YAML and identifies which user_input
    fields are passed to stringTemplateAgent nodes via :source.user_input.xxx
    references. These fields need to be validated for primitive array types
    to prevent [object Object] conversion issues.

    Args:
        yaml_content: Workflow YAML content

    Returns:
        Set of field names from user_input that are used by stringTemplateAgent
    """
    if not yaml_content:
        return set()

    try:
        workflow = yaml.safe_load(yaml_content)
    except yaml.YAMLError:
        logger.warning("Failed to parse YAML for stringTemplateAgent field extraction")
        return set()

    if not isinstance(workflow, dict):
        return set()

    nodes = workflow.get("nodes", {})
    if not isinstance(nodes, dict):
        return set()

    fields: set[str] = set()

    for _node_id, node_def in nodes.items():
        if not isinstance(node_def, dict):
            continue

        agent = node_def.get("agent")
        if agent != "stringTemplateAgent":
            continue

        inputs = node_def.get("inputs", {})
        if not isinstance(inputs, dict):
            continue

        for _field_name, field_ref in inputs.items():
            if not isinstance(field_ref, str):
                continue

            # Extract field name from :source.user_input.xxx pattern
            if field_ref.startswith(":source.user_input."):
                # Extract the field name after :source.user_input.
                field_parts = field_ref.split(".")
                if len(field_parts) >= 3:
                    # The field name is the third part (index 2)
                    user_input_field = field_parts[2]
                    fields.add(user_input_field)

    return fields


def _object_array_issue(
    field_name: str,
    index: int,
    actual_type: str,
) -> dict[str, Any]:
    """Create standardized issue dict for object in array detection.

    Following the same pattern as workflow_schema_validator._issue().

    Args:
        field_name: Name of the array field containing object
        index: Index of the object in the array
        actual_type: Actual type of the element (e.g., 'dict')

    Returns:
        Standardized issue dictionary
    """
    return {
        "node_id": "sample_input",
        "issue_type": "object_in_array",
        "message": (
            f"Array field '{field_name}' contains object at index {index}. "
            f"stringTemplateAgent will convert this to '[object Object]'."
        ),
        "severity": "error",
        "field_name": field_name,
        "expected_value": "primitive type (string, number, boolean)",
        "actual_value": actual_type,
        "suggestion": (
            "Use primitive types in arrays, or serialize objects before "
            "passing to stringTemplateAgent. Consider extracting specific "
            "fields from objects instead of passing entire objects."
        ),
    }


def _validate_primitive_arrays(
    sample_input: dict[str, Any],
    target_fields: set[str],
) -> list[dict[str, Any]]:
    """Validate that array elements in target fields are primitive types.

    Only validates arrays in fields that are identified as being passed
    to stringTemplateAgent nodes (target_fields). Non-target fields are
    ignored to prevent false positives.

    Args:
        sample_input: Sample input data to validate
        target_fields: Set of field names to validate (from stringTemplateAgent inputs)

    Returns:
        List of validation issues for object arrays
    """
    if not sample_input or not target_fields:
        return []

    issues: list[dict[str, Any]] = []

    for field_name, value in sample_input.items():
        # Only validate target fields (stringTemplateAgent inputs)
        if field_name not in target_fields:
            continue

        # Only validate array fields
        if not isinstance(value, list):
            continue

        # Check each element in the array
        for index, item in enumerate(value):
            if isinstance(item, dict):
                issues.append(
                    _object_array_issue(field_name, index, type(item).__name__)
                )

    return issues


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


def _generate_string_sample(schema: dict[str, Any], prop_name: str = "") -> str:
    """Generate appropriate string sample based on property name and schema.

    Args:
        schema: JSON Schema for the string property
        prop_name: Property name (used to infer appropriate sample value)

    Returns:
        Appropriate sample string value
    """
    # Check for format hint in schema
    fmt = schema.get("format", "")

    # Generate sample based on format
    if fmt == "date":
        return "2024-01-15"
    if fmt == "date-time":
        return "2024-01-15T10:30:00Z"
    if fmt == "email":
        return "sample@example.com"
    if fmt == "uri" or fmt == "url":
        return "https://example.com/sample"

    # Generate sample based on property name patterns
    prop_lower = prop_name.lower()

    # File name patterns
    if "file" in prop_lower and "name" in prop_lower:
        return "sample_file.txt"
    if prop_lower.endswith("_file") or prop_lower == "filename":
        return "sample_file.txt"

    # Date patterns
    if "date" in prop_lower:
        return "2024-01-15"

    # Email patterns
    if "email" in prop_lower or "mail" in prop_lower:
        return "sample@example.com"

    # URL patterns
    if "url" in prop_lower or "link" in prop_lower:
        return "https://example.com/sample"

    # ID patterns
    if prop_lower.endswith("_id") or prop_lower == "id":
        return "sample_id_001"

    # Name patterns
    if "name" in prop_lower:
        return "Sample Name"

    # Title patterns
    if "title" in prop_lower:
        return "Sample Title"

    # Script/text patterns
    if "script" in prop_lower or "text" in prop_lower or "content" in prop_lower:
        return "これはサンプルテキストです。テスト用の内容が含まれています。"

    # Default
    return "sample_text"


def _generate_sample_from_schema(
    schema: dict[str, Any], prop_name: str = ""
) -> SchemaValue:
    """Generate sample value from JSON Schema.

    Args:
        schema: JSON Schema definition
        prop_name: Property name (used for string type to generate appropriate value)

    Returns:
        Sample value matching the schema
    """
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
        for child_prop_name, prop_schema in properties.items():
            if not isinstance(prop_schema, dict):
                sample[child_prop_name] = None
                continue
            sample[child_prop_name] = _generate_sample_from_schema(
                prop_schema, child_prop_name
            )
        return sample

    if schema_type == "array":
        items_schema = schema.get("items", {})
        if isinstance(items_schema, list) and items_schema:
            items_schema = _first_dict(items_schema)
        if not isinstance(items_schema, dict):
            items_schema = {}
        return [_generate_sample_from_schema(items_schema, prop_name)]

    if schema_type == "string":
        # Generate appropriate string sample based on property name and schema
        return _generate_string_sample(schema, prop_name)

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
