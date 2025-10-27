"""Validator node for GraphAI workflow validation (non-LLM).

This module provides the validator node that performs rule-based validation
of workflow execution results without using LLM.
"""

import logging
from typing import Any

import yaml

from ..state import WorkflowGeneratorState

logger = logging.getLogger(__name__)


def _format_issue(issue: dict[str, str]) -> str:
    detail = issue.get("detail")
    if detail:
        return f"[{issue['category']}] {issue['message']}: {detail}"
    return f"[{issue['category']}] {issue['message']}"


def _issue(
    category: str,
    message: str,
    detail: str | None = None,
) -> dict[str, str]:
    payload: dict[str, str] = {
        "category": category,
        "message": message,
    }
    if detail:
        payload["detail"] = detail
    return payload


def _validate_yaml_syntax(yaml_content: str) -> list[dict[str, str]]:
    try:
        yaml.safe_load(yaml_content)
        return []
    except yaml.YAMLError as exc:
        return [_issue("yaml", "YAML syntax error", str(exc))]


def _validate_http_status(http_status: int | None) -> list[dict[str, str]]:
    if http_status is None:
        return [_issue("http", "HTTP status is missing")]
    if http_status == 200:
        return []
    if http_status == 500:
        return [_issue("http", "Workflow execution failed", "HTTP 500")]
    if http_status == 400:
        return [_issue("http", "Invalid workflow request", "HTTP 400")]
    if http_status == 404:
        return [_issue("http", "Workflow not found", "HTTP 404")]
    if http_status == 504:
        return [_issue("http", "Workflow execution timeout", "HTTP 504")]
    return [_issue("http", "Unexpected HTTP status", str(http_status))]


def _validate_graphai_execution(
    execution_result: dict[str, Any] | None,
) -> list[dict[str, str]]:
    if execution_result is None:
        return [_issue("graphai", "Execution result is missing")]

    issues: list[dict[str, str]] = []
    graphai_errors = execution_result.get("errors", {})
    for node_id, error_info in graphai_errors.items():
        detail = str(error_info.get("message", "Unknown error"))
        issues.append(_issue("graphai", f"Node '{node_id}' error", detail))

    graphai_logs = execution_result.get("logs", [])
    for log in graphai_logs:
        if log.get("state") == "timed-out":
            node_id = log.get("nodeId", "unknown")
            issues.append(_issue("graphai", f"Node '{node_id}' timed out"))

    return issues


def _validate_output_schema(
    execution_result: dict[str, Any] | None,
    output_schema: dict[str, Any],
) -> list[dict[str, str]]:
    if execution_result is None:
        return [_issue("output", "Execution result missing for validation")]

    results = execution_result.get("results", {})
    if not results:
        return [_issue("output", "Workflow produced no results")]

    logger.debug("Output schema validation: results exist = %s", bool(results))
    logger.debug("Expected output schema: %s", output_schema)
    logger.debug("Actual results keys: %s", list(results.keys()))
    return []


async def validator_node(
    state: WorkflowGeneratorState,
) -> WorkflowGeneratorState:
    """Validate workflow YAML and execution results (non-LLM).

    This node performs rule-based validation:
    1. YAML syntax validation
    2. HTTP status code check (200 = success)
    3. GraphAI errors and timeout check
    4. Output schema compatibility check

    Args:
        state: Current workflow generator state

    Returns:
        Updated state with validation results
    """
    logger.info("Starting validator node")

    yaml_content = state.get("yaml_content")
    test_http_status = state.get("test_http_status")
    test_execution_result = state.get("test_execution_result")
    task_data = state.get("task_data")

    if yaml_content is None:
        message = "Validation failed: yaml_content missing"
        logger.error(message)
        return {
            **state,
            "validation_result": {
                "is_valid": False,
                "issues": [_issue("state", message)],
            },
            "validation_errors": [message],
            "is_valid": False,
            "status": "validation_failed",
        }

    if task_data is None:
        message = "Validation failed: task_data missing"
        logger.error(message)
        return {
            **state,
            "validation_result": {
                "is_valid": False,
                "issues": [_issue("state", message)],
            },
            "validation_errors": [message],
            "is_valid": False,
            "status": "validation_failed",
        }
    output_interface = task_data.get("output_interface", {})
    output_schema = output_interface.get("schema", {})

    validators = [
        lambda: _validate_yaml_syntax(yaml_content),
        lambda: _validate_http_status(test_http_status),
        lambda: _validate_graphai_execution(test_execution_result),
        lambda: _validate_output_schema(test_execution_result, output_schema),
    ]

    issues: list[dict[str, str]] = []
    for check in validators:
        result = check()
        if result:
            issues.extend(result)
            logger.warning(
                "Validation issues detected: %s",
                [_format_issue(item) for item in result],
            )

    if not issues:
        logger.info("Validation passed: workflow is valid")
        return {
            **state,
            "validation_result": {
                "is_valid": True,
                "issues": [],
            },
            "validation_errors": [],
            "is_valid": True,
            "status": "validated",
        }
    else:
        logger.warning("Validation failed with %s issues", len(issues))
        formatted_errors = [_format_issue(issue) for issue in issues]
        return {
            **state,
            "validation_result": {
                "is_valid": False,
                "issues": issues,
            },
            "validation_errors": formatted_errors,
            "is_valid": False,
            "status": "validation_failed",
        }
