"""Workflow schema validator node for API type and field name validation (Issue #333).

This module provides the workflow_schema_validator_node that validates
API type compatibility and field name correctness in generated workflows.

Key validations:
1. Type compatibility (Object vs String)
2. Field name correctness (e.g., system_prompt vs system_imput)
3. Required fields presence
4. Reference type compatibility
"""

import logging
from typing import Any, Literal

import yaml

from ..state import WorkflowGeneratorState

logger = logging.getLogger(__name__)

# Known API endpoints that expect specific types
JSONOUTPUT_ENDPOINTS = [
    "/v1/aiagent/utility/jsonoutput",
    "/aiagent-api/v1/aiagent/utility/jsonoutput",
]

# Deprecated field names mapping (typo/old name -> correct name)
# Note: This single mapping handles both field name corrections and deprecation warnings
DEPRECATED_FIELDS = {
    "system_imput": "system_prompt",
}

# Fields that expect String type
STRING_TYPE_FIELDS = ["user_input", "system_prompt"]


def _issue(
    node_id: str,
    issue_type: Literal[
        "type_mismatch",
        "field_name_error",
        "deprecated_field",
        "missing_required",
        "unknown_agent",
        "yaml_parse_error",
    ],
    message: str,
    severity: Literal["error", "warning"] = "error",
    field_name: str = "",
    expected_value: str = "",
    actual_value: str = "",
    suggestion: str | None = None,
) -> dict[str, Any]:
    """Create a standardized validation issue.

    Args:
        node_id: ID of the node with the issue
        issue_type: Type of validation issue
        message: Human-readable error message
        severity: Issue severity (error or warning)
        field_name: Name of the problematic field
        expected_value: Expected value or type
        actual_value: Actual value or type found
        suggestion: Suggestion for fixing the issue

    Returns:
        Standardized issue dictionary
    """
    return {
        "node_id": node_id,
        "issue_type": issue_type,
        "message": message,
        "severity": severity,
        "field_name": field_name,
        "expected_value": expected_value,
        "actual_value": actual_value,
        "suggestion": suggestion,
    }


def _is_object_reference(value: Any) -> bool:
    """Check if a value is an object reference (e.g., :node_name without field access).

    Object references like ':fetch_data' return the entire node output (Object type).
    Field references like ':fetch_data.result' return a specific field.

    Args:
        value: Value to check

    Returns:
        True if value is an object reference
    """
    if not isinstance(value, str):
        return False

    value = value.strip()

    # Must start with : to be a reference
    if not value.startswith(":"):
        return False

    # Check if it's a simple node reference without field access
    # :node_name -> Object reference
    # :node_name.field -> Field reference (could be any type)
    reference_part = value[1:]  # Remove leading :

    # If there's no dot, it's a full object reference
    if "." not in reference_part:
        return True

    return False


def _check_type_mismatch(
    node_id: str,
    node_def: dict[str, Any],
    endpoint: str,
) -> list[dict[str, Any]]:
    """Check for type mismatches in API calls.

    Args:
        node_id: Node ID being checked
        node_def: Node definition from YAML
        endpoint: API endpoint being called

    Returns:
        List of type mismatch issues
    """
    issues: list[dict[str, Any]] = []

    # Check if this is a jsonoutput API call
    is_jsonoutput = any(ep in endpoint for ep in JSONOUTPUT_ENDPOINTS)
    if not is_jsonoutput:
        return issues

    # Get body from inputs
    inputs = node_def.get("inputs", {})
    body = inputs.get("body", {})

    if not isinstance(body, dict):
        return issues

    # Check user_input field
    user_input = body.get("user_input")
    if user_input is not None and _is_object_reference(user_input):
        issues.append(
            _issue(
                node_id=node_id,
                issue_type="type_mismatch",
                message=f"user_input expects String type but receives Object reference '{user_input}'",
                severity="error",
                field_name="user_input",
                expected_value="String",
                actual_value="Object (node reference)",
                suggestion="Use stringTemplateAgent to convert Object to String, or access a specific field like ':node.result'",
            )
        )

    return issues


def _check_field_names(
    node_id: str,
    node_def: dict[str, Any],
) -> list[dict[str, Any]]:
    """Check for field name errors and deprecated fields.

    Args:
        node_id: Node ID being checked
        node_def: Node definition from YAML

    Returns:
        List of field name issues
    """
    issues: list[dict[str, Any]] = []

    # Get body from inputs
    inputs = node_def.get("inputs", {})
    body = inputs.get("body", {})

    if not isinstance(body, dict):
        return issues

    # Check for deprecated field names
    for field_name in body.keys():
        if field_name in DEPRECATED_FIELDS:
            correct_name = DEPRECATED_FIELDS[field_name]
            issues.append(
                _issue(
                    node_id=node_id,
                    issue_type="deprecated_field",
                    message=f"Field '{field_name}' is deprecated, use '{correct_name}' instead",
                    severity="warning",
                    field_name=field_name,
                    expected_value=correct_name,
                    actual_value=field_name,
                    suggestion=f"Replace '{field_name}' with '{correct_name}'",
                )
            )

    return issues


def _validate_fetch_agent_nodes(
    workflow: dict[str, Any],
) -> list[dict[str, Any]]:
    """Validate all fetchAgent nodes in the workflow.

    Args:
        workflow: Parsed workflow YAML

    Returns:
        List of validation issues
    """
    issues: list[dict[str, Any]] = []

    nodes = workflow.get("nodes", {})
    if not isinstance(nodes, dict):
        return issues

    for node_id, node_def in nodes.items():
        if not isinstance(node_def, dict):
            continue

        agent = node_def.get("agent")
        if agent != "fetchAgent":
            continue

        # Get URL from inputs
        inputs = node_def.get("inputs", {})
        url = inputs.get("url", "")

        # Check type mismatches
        issues.extend(_check_type_mismatch(node_id, node_def, url))

        # Check field names
        issues.extend(_check_field_names(node_id, node_def))

    return issues


def _create_error_state(
    state: WorkflowGeneratorState,
    error_message: str,
) -> WorkflowGeneratorState:
    """Create an error state with a YAML parse error issue (DRY helper).

    Args:
        state: Current workflow generator state
        error_message: Error message to include in the issue

    Returns:
        Updated state with error information
    """
    error_issue = _issue(
        node_id="yaml",
        issue_type="yaml_parse_error",
        message=error_message,
        severity="error",
    )
    return {
        **state,
        "schema_validation_result": {
            "is_valid": False,
            "issues": [error_issue],
        },
        "schema_validation_issues": [error_issue],
        "has_schema_errors": True,
    }


async def workflow_schema_validator_node(
    state: WorkflowGeneratorState,
) -> WorkflowGeneratorState:
    """Validate API schema compatibility in generated workflow (Issue #333).

    This node performs rule-based validation for:
    1. Type compatibility (Object vs String)
    2. Field name correctness
    3. Required fields presence

    Args:
        state: Current workflow generator state

    Returns:
        Updated state with schema validation results
    """
    logger.info("Starting workflow_schema_validator_node (Issue #333)")

    yaml_content = state.get("yaml_content", "")
    if not yaml_content:
        logger.info("No YAML content to validate, skipping schema validation")
        return {
            **state,
            "schema_validation_result": {
                "is_valid": True,
                "issues": [],
                "validated_nodes": 0,
                "api_calls_detected": 0,
            },
            "schema_validation_issues": [],
            "has_schema_errors": False,
        }

    # Parse YAML
    try:
        workflow = yaml.safe_load(yaml_content)
        if not isinstance(workflow, dict):
            raise ValueError("YAML content is not a dictionary")
    except yaml.YAMLError as e:
        logger.error(f"YAML parse error: {e}")
        return _create_error_state(state, f"YAML parse error: {e}")
    except ValueError as e:
        logger.error(f"Invalid YAML structure: {e}")
        return _create_error_state(state, str(e))

    # Validate fetchAgent nodes
    issues = _validate_fetch_agent_nodes(workflow)

    # Count statistics
    nodes = workflow.get("nodes", {})
    validated_nodes = len(nodes) if isinstance(nodes, dict) else 0
    api_calls_detected = sum(
        1
        for node_def in (nodes.values() if isinstance(nodes, dict) else [])
        if isinstance(node_def, dict) and node_def.get("agent") == "fetchAgent"
    )

    # Determine if there are errors (not just warnings)
    has_errors = any(issue.get("severity") == "error" for issue in issues)

    logger.info(
        f"Schema validation completed: {len(issues)} issues found, "
        f"{api_calls_detected} API calls detected, has_errors={has_errors}"
    )

    return {
        **state,
        "schema_validation_result": {
            "is_valid": not has_errors,
            "issues": issues,
            "validated_nodes": validated_nodes,
            "api_calls_detected": api_calls_detected,
            "warning_count": sum(
                1 for issue in issues if issue.get("severity") == "warning"
            ),
            "error_count": sum(
                1 for issue in issues if issue.get("severity") == "error"
            ),
        },
        "schema_validation_issues": issues,
        "has_schema_errors": has_errors,
    }
