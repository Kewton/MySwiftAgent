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

# Task context for keyword-aware sample generation
_TASK_CONTEXT: dict[str, Any] = {}


def _extract_keywords_from_description(description: str) -> list[str]:
    """Extract keywords from task description for contextual sample generation.

    This function identifies key terms in the task description that should be
    used for generating realistic test data instead of generic "sample_text".

    Args:
        description: Task description text

    Returns:
        List of extracted keywords (e.g., ["大谷翔平", "ニュース"])
    """
    if not description:
        return []

    keywords: list[str] = []

    # Common patterns for extracting key entities
    # Japanese patterns
    import re

    # Extract quoted strings
    quoted = re.findall(r"「(.+?)」", description)
    keywords.extend(quoted)

    # Extract terms before common action words
    patterns = [
        r"(.+?)(?:に関する|について|の最新|をGoogle|で検索|を検索|を取得)",
        r"(.+?)(?:ニュース|情報|データ)",
    ]
    for pattern in patterns:
        matches = re.findall(pattern, description)
        for match in matches:
            # Clean up and add if not too long
            cleaned = match.strip()
            if cleaned and len(cleaned) <= 20 and cleaned not in keywords:
                keywords.append(cleaned)

    # Filter out common generic terms
    generic_terms = {"最新", "ニュース", "情報", "データ", "サマリ", "メール"}
    keywords = [k for k in keywords if k not in generic_terms]

    logger.debug(f"Extracted keywords from description: {keywords}")
    return keywords


def _set_task_context(task_data: dict[str, Any] | None) -> None:
    """Set the task context for keyword-aware sample generation.

    Args:
        task_data: Task data containing description, name, etc.
    """
    global _TASK_CONTEXT
    if task_data is None:
        _TASK_CONTEXT = {}
        return

    description = task_data.get("description", "")
    name = task_data.get("name", "")

    keywords = _extract_keywords_from_description(description)
    # Also try to extract from task name
    name_keywords = _extract_keywords_from_description(name)
    all_keywords = list(dict.fromkeys(keywords + name_keywords))  # Dedupe

    _TASK_CONTEXT = {
        "description": description,
        "name": name,
        "keywords": all_keywords,
        "primary_keyword": all_keywords[0] if all_keywords else None,
    }
    logger.info(f"Task context set: keywords={all_keywords}")


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
    """Extract enum, default, or example value with type validation.

    Issue #340: Added type validation for default values to prevent
    object arrays from being used as string array defaults, which causes
    [object Object] conversion issues in stringTemplateAgent.

    MF-2: Added boolean array validation for completeness.

    Priority order: const > enum > examples > default > example
    """
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
        # Issue #340: Validate default value type for arrays
        if isinstance(default, list):
            items_type = schema.get("items", {}).get("type")
            if items_type == "string":
                # All elements must be strings
                if all(isinstance(item, str) for item in default):
                    return default  # type: ignore[no-any-return]
                # Object array detected, skip this default
                logger.warning(
                    "Skipping invalid default: expected string array, "
                    f"got {[type(x).__name__ for x in default]}"
                )
                return None
            elif items_type in ("number", "integer"):
                # All elements must be numbers
                if all(isinstance(item, (int, float)) for item in default):
                    return default  # type: ignore[no-any-return]
                logger.warning(
                    "Skipping invalid default: expected number array, "
                    f"got {[type(x).__name__ for x in default]}"
                )
                return None
            elif items_type == "boolean":
                # MF-2: All elements must be booleans
                if all(isinstance(item, bool) for item in default):
                    return default  # type: ignore[no-any-return]
                logger.warning(
                    "Skipping invalid default: expected boolean array, "
                    f"got {[type(x).__name__ for x in default]}"
                )
                return None
            # For other types (object, array, or no items.type), allow as-is
            # but log warning if contains dict elements for non-object types
            if items_type is None and any(isinstance(item, dict) for item in default):
                logger.warning(
                    f"Array default contains objects without items.type: "
                    f"{[type(x).__name__ for x in default]}"
                )
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
    """Generate appropriate string sample based on property name, schema, and task context.

    Uses task context (extracted keywords from user requirement) to generate
    realistic test data instead of generic "sample_text".

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

    # Issue #338: Use task context keywords for query/search/keyword fields
    # This ensures test data matches the user's actual requirement
    query_patterns = ["query", "keyword", "search", "term", "input", "subject", "topic"]
    if any(pattern in prop_lower for pattern in query_patterns):
        primary_keyword = _TASK_CONTEXT.get("primary_keyword")
        if primary_keyword:
            logger.debug(
                f"Using task keyword '{primary_keyword}' for property '{prop_name}'"
            )
            return primary_keyword

    # Default: use task keyword if available, otherwise generic sample
    primary_keyword = _TASK_CONTEXT.get("primary_keyword")
    if primary_keyword:
        return primary_keyword
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

    # Issue #338: Set task context for keyword-aware sample generation
    # This extracts keywords like "大谷翔平" from the task description
    _set_task_context(task_data)

    input_interface = task_data.get("input_interface", {})
    input_schema = input_interface.get("schema", {})

    logger.debug(f"Input schema: {input_schema}")

    try:
        # Generate sample input from schema (now uses task context for keywords)
        sample_input = _generate_sample_from_schema(input_schema)

        logger.info(f"Generated sample input: {sample_input}")
        logger.debug(f"Sample input type: {type(sample_input)}")

        # Issue #340: Validate object arrays in sample_input for stringTemplateAgent
        yaml_content = state.get("yaml_content", "")
        if yaml_content and isinstance(sample_input, dict):
            target_fields = _get_string_template_input_fields(yaml_content)
            object_issues = _validate_primitive_arrays(sample_input, target_fields)
            if object_issues:
                logger.warning(
                    "[OBJECT_ARRAY_VALIDATION] Detected object arrays in sample_input: %s",
                    object_issues,
                )
                return {
                    **state,
                    "sample_input": sample_input,
                    "object_array_issues": object_issues,
                    "has_object_array_errors": True,
                    "needs_test_data_regeneration": True,
                    "status": "object_array_detected",
                }

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
