"""Workflow output node validation for Issue #338 and Issue #340.

This module provides validation functions to ensure generated workflow YAML
follows the output node naming convention:
- Output node MUST be named 'output'
- Output node MUST have isResult: true

Issue #340: Added array validation for stringTemplateAgent inputs to prevent
[object Object] conversion issues.

This enforces interface contracts in task chains.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of workflow output node validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_output_node_convention(yaml_content: str) -> ValidationResult:
    """Validate that workflow YAML follows output node naming convention.

    This function checks:
    1. YAML syntax is valid
    2. 'nodes' section exists
    3. 'output' node exists
    4. 'output' node has isResult: true

    Args:
        yaml_content: GraphAI workflow YAML content

    Returns:
        ValidationResult with is_valid, errors, and warnings
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Check for empty content
    if not yaml_content or not yaml_content.strip():
        return ValidationResult(
            is_valid=False,
            errors=["Empty YAML content provided"],
            warnings=[],
        )

    # Parse YAML
    try:
        workflow = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        return ValidationResult(
            is_valid=False,
            errors=[f"Invalid YAML syntax: {e}"],
            warnings=[],
        )

    # Check for valid structure
    if not isinstance(workflow, dict):
        return ValidationResult(
            is_valid=False,
            errors=["YAML content is not a valid dictionary structure"],
            warnings=[],
        )

    # Check for nodes section
    nodes = workflow.get("nodes")
    if not nodes:
        return ValidationResult(
            is_valid=False,
            errors=["No 'nodes' section found in workflow YAML"],
            warnings=[],
        )

    if not isinstance(nodes, dict):
        return ValidationResult(
            is_valid=False,
            errors=["'nodes' section is not a dictionary"],
            warnings=[],
        )

    # Check for output node
    if "output" not in nodes:
        # Find any node with isResult: true for the error message
        is_result_nodes = []
        for node_name, node_def in nodes.items():
            if isinstance(node_def, dict) and node_def.get("isResult") is True:
                is_result_nodes.append(node_name)

        error_msg = (
            "Missing required 'output' node. "
            "Workflow must have a node named 'output' with isResult: true."
        )
        if is_result_nodes:
            error_msg += (
                f" Found isResult: true on node(s): {', '.join(is_result_nodes)}. "
            )
            error_msg += "Please rename to 'output'."

        return ValidationResult(
            is_valid=False,
            errors=[error_msg],
            warnings=[],
        )

    # Check output node has isResult: true
    output_node = nodes.get("output")
    if not isinstance(output_node, dict):
        return ValidationResult(
            is_valid=False,
            errors=["'output' node is not a valid dictionary"],
            warnings=[],
        )

    is_result = output_node.get("isResult")
    if is_result is not True:
        if is_result is False:
            errors.append(
                "Output node has isResult: false. "
                "The 'output' node must have isResult: true."
            )
        elif is_result is None:
            errors.append(
                "Output node is missing isResult attribute. "
                "The 'output' node must have isResult: true."
            )
        else:
            errors.append(
                f"Output node has invalid isResult value: {is_result}. "
                "Must be 'true' (boolean)."
            )

    if errors:
        return ValidationResult(
            is_valid=False,
            errors=errors,
            warnings=warnings,
        )

    # Check for multiple isResult: true nodes (warning only)
    is_result_count = 0
    is_result_nodes = []
    for node_name, node_def in nodes.items():
        if isinstance(node_def, dict) and node_def.get("isResult") is True:
            is_result_count += 1
            is_result_nodes.append(node_name)

    if is_result_count > 1:
        warnings.append(
            f"Multiple nodes have isResult: true ({', '.join(is_result_nodes)}). "
            "Only the 'output' node should have isResult: true for clear data flow."
        )

    logger.info(
        f"Workflow validation passed: output node found with isResult: true. "
        f"Warnings: {len(warnings)}"
    )

    return ValidationResult(
        is_valid=True,
        errors=[],
        warnings=warnings,
    )


def _get_array_fields_from_schema(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract array field definitions from interface schema.

    Issue #340: Helper function to identify array fields and their items types.

    Args:
        schema: Interface JSON Schema

    Returns:
        Dictionary mapping field name to array field definition
    """
    if not isinstance(schema, dict):
        return {}

    properties = schema.get("properties", {})
    if not isinstance(properties, dict):
        return {}

    array_fields: dict[str, dict[str, Any]] = {}

    for field_name, field_def in properties.items():
        if not isinstance(field_def, dict):
            continue

        if field_def.get("type") == "array":
            array_fields[field_name] = field_def

    return array_fields


def _is_primitive_items_type(items_def: dict[str, Any]) -> bool:
    """Check if array items type is a primitive type.

    Issue #340: Primitive types that stringTemplateAgent can safely convert.

    Args:
        items_def: The 'items' definition from array schema

    Returns:
        True if items type is primitive (string, number, integer, boolean)
    """
    if not isinstance(items_def, dict):
        return False

    items_type = items_def.get("type")
    return items_type in ("string", "number", "integer", "boolean")


def _workflow_array_issue(
    node_id: str,
    field_name: str,
    items_type: str,
) -> dict[str, Any]:
    """Create standardized issue dict for object array in stringTemplateAgent.

    Issue #340: Following the same pattern as _object_array_issue in sample_input_generator.

    Args:
        node_id: The node ID in the workflow
        field_name: Name of the array field containing objects
        items_type: The items.type from schema (e.g., 'object')

    Returns:
        Standardized issue dictionary
    """
    return {
        "node_id": node_id,
        "issue_type": "object_array_in_string_template",
        "message": (
            f"Array field '{field_name}' with items.type='{items_type}' is passed to "
            f"stringTemplateAgent node '{node_id}'. Objects in arrays will be "
            "converted to '[object Object]'."
        ),
        "severity": "error",
        "field_name": field_name,
        "expected_items_type": "primitive (string, number, integer, boolean)",
        "actual_items_type": items_type,
        "suggestion": (
            "Either change the schema to use primitive array items, or use copyAgent "
            "to extract specific fields before passing to stringTemplateAgent. "
            "Consider serializing objects to JSON strings if full object data is needed."
        ),
    }


def validate_workflow_arrays(
    workflow_yaml: str,
    interface_schema: dict[str, Any],
) -> list[dict[str, Any]]:
    """Validate that arrays passed to stringTemplateAgent contain only primitives.

    Issue #340: Layer 4 validation - Check for object arrays that would cause
    [object Object] errors when passed to stringTemplateAgent.

    Args:
        workflow_yaml: Generated GraphAI workflow YAML
        interface_schema: Interface schema with type definitions

    Returns:
        List of validation issues (empty if no issues)
    """
    issues: list[dict[str, Any]] = []

    # Handle empty inputs
    if not workflow_yaml or not workflow_yaml.strip():
        return issues

    if not interface_schema:
        return issues

    # Parse YAML
    try:
        workflow = yaml.safe_load(workflow_yaml)
    except yaml.YAMLError:
        logger.warning("Failed to parse YAML for array validation")
        return issues

    if not isinstance(workflow, dict):
        return issues

    nodes = workflow.get("nodes", {})
    if not isinstance(nodes, dict):
        return issues

    # Extract array field definitions from interface schema
    array_fields = _get_array_fields_from_schema(interface_schema)
    if not array_fields:
        return issues

    # Check each node for stringTemplateAgent with object array inputs
    for node_id, node_def in nodes.items():
        if not isinstance(node_def, dict):
            continue

        agent = node_def.get("agent")
        if agent != "stringTemplateAgent":
            continue

        inputs = node_def.get("inputs", {})
        if not isinstance(inputs, dict):
            continue

        # Check each input for user_input references to object arrays
        for _input_name, input_ref in inputs.items():
            if not isinstance(input_ref, str):
                continue

            # Check for :source.user_input.xxx pattern
            if not input_ref.startswith(":source.user_input."):
                continue

            # Extract field name from reference
            field_parts = input_ref.split(".")
            if len(field_parts) < 3:
                continue

            user_input_field = field_parts[2]

            # Check if this field is an array with non-primitive items
            if user_input_field in array_fields:
                field_def = array_fields[user_input_field]
                items_def = field_def.get("items", {})

                # If items type is not primitive, it's an object array
                if not _is_primitive_items_type(items_def):
                    items_type = (
                        items_def.get("type", "unknown") if items_def else "unknown"
                    )
                    issues.append(
                        _workflow_array_issue(node_id, user_input_field, items_type)
                    )

    if issues:
        logger.warning(
            f"[WORKFLOW_ARRAY_VALIDATION] Detected {len(issues)} object array issues "
            f"in stringTemplateAgent nodes"
        )

    return issues
