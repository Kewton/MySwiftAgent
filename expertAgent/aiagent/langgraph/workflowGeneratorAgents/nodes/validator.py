"""Validator node for GraphAI workflow validation (non-LLM).

This module provides the validator node that performs rule-based validation
of workflow execution results without using LLM.
"""

import logging
from typing import Any

import yaml

from ..state import WorkflowGeneratorState

logger = logging.getLogger(__name__)


def _validate_yaml_syntax(yaml_content: str) -> tuple[bool, list[str]]:
    """Validate YAML syntax.

    Args:
        yaml_content: YAML content string

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    try:
        yaml.safe_load(yaml_content)
        return True, []
    except yaml.YAMLError as e:
        errors.append(f"YAML syntax error: {str(e)}")
        return False, errors


def _validate_http_status(http_status: int | None) -> tuple[bool, list[str]]:
    """Validate HTTP response status code.

    Args:
        http_status: HTTP status code from graphAiServer

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    if http_status is None:
        errors.append("HTTP status is missing")
        return False, errors

    if http_status == 200:
        return True, []
    elif http_status == 500:
        errors.append("Workflow execution failed (HTTP 500)")
        return False, errors
    elif http_status == 400:
        errors.append("Invalid workflow request (HTTP 400)")
        return False, errors
    elif http_status == 404:
        errors.append("Workflow not found (HTTP 404)")
        return False, errors
    elif http_status == 504:
        errors.append("Workflow execution timeout (HTTP 504)")
        return False, errors
    else:
        errors.append(f"Unexpected HTTP status: {http_status}")
        return False, errors


def _validate_graphai_execution(
    execution_result: dict[str, Any] | None,
) -> tuple[bool, list[str]]:
    """Validate GraphAI execution result (errors and logs).

    Args:
        execution_result: GraphAI execution result from graphAiServer

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    if execution_result is None:
        errors.append("Execution result is missing")
        return False, errors

    # Check GraphAI errors
    graphai_errors = execution_result.get("errors", {})
    if graphai_errors:
        for node_id, error_info in graphai_errors.items():
            error_message = error_info.get("message", "Unknown error")
            errors.append(f"Node '{node_id}' error: {error_message}")

    # Check GraphAI logs for timed-out nodes
    graphai_logs = execution_result.get("logs", [])
    for log in graphai_logs:
        if log.get("state") == "timed-out":
            node_id = log.get("nodeId", "unknown")
            errors.append(f"Node '{node_id}' timed out")

    if errors:
        return False, errors
    else:
        return True, []


def _validate_output_schema(
    execution_result: dict[str, Any] | None,
    output_schema: dict[str, Any],
) -> tuple[bool, list[str]]:
    """Validate workflow output against output interface schema.

    Args:
        execution_result: GraphAI execution result
        output_schema: Output interface JSON schema

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    if execution_result is None:
        errors.append("Execution result is missing for output validation")
        return False, errors

    # Extract results from GraphAI execution
    results = execution_result.get("results", {})

    if not results:
        errors.append("Workflow produced no results")
        return False, errors

    # For now, just check if results exist
    # TODO: Implement JSON Schema validation in the future
    logger.debug(f"Output schema validation: results exist = {bool(results)}")
    logger.debug(f"Expected output schema: {output_schema}")
    logger.debug(f"Actual results keys: {list(results.keys())}")

    return True, []


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

    yaml_content = state["yaml_content"]
    test_http_status = state.get("test_http_status")
    test_execution_result = state.get("test_execution_result")
    task_data = state["task_data"]
    output_interface = task_data.get("output_interface", {})
    output_schema = output_interface.get("schema", {})

    all_errors: list[str] = []

    # Validation 1: YAML syntax
    logger.debug("Validating YAML syntax")
    yaml_valid, yaml_errors = _validate_yaml_syntax(yaml_content)
    if not yaml_valid:
        all_errors.extend(yaml_errors)
        logger.error(f"YAML validation failed: {yaml_errors}")

    # Validation 2: HTTP status
    logger.debug("Validating HTTP status")
    http_valid, http_errors = _validate_http_status(test_http_status)
    if not http_valid:
        all_errors.extend(http_errors)
        logger.error(f"HTTP status validation failed: {http_errors}")

    # Validation 3: GraphAI execution (errors and logs)
    logger.debug("Validating GraphAI execution")
    execution_valid, execution_errors = _validate_graphai_execution(
        test_execution_result
    )
    if not execution_valid:
        all_errors.extend(execution_errors)
        logger.error(f"GraphAI execution validation failed: {execution_errors}")

    # Validation 4: Output schema
    logger.debug("Validating output schema")
    schema_valid, schema_errors = _validate_output_schema(
        test_execution_result, output_schema
    )
    if not schema_valid:
        all_errors.extend(schema_errors)
        logger.warning(f"Output schema validation failed: {schema_errors}")

    # Determine overall validation result
    is_valid = len(all_errors) == 0

    if is_valid:
        logger.info("Validation passed: workflow is valid")
        return {
            **state,
            "validation_result": {
                "is_valid": True,
                "errors": [],
            },
            "validation_errors": [],
            "is_valid": True,
            "status": "validated",
        }
    else:
        logger.warning(f"Validation failed with {len(all_errors)} errors")
        return {
            **state,
            "validation_result": {
                "is_valid": False,
                "errors": all_errors,
            },
            "validation_errors": all_errors,
            "is_valid": False,
            "status": "validation_failed",
        }
