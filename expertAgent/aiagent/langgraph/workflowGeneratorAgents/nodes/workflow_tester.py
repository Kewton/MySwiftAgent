"""Workflow tester node for GraphAI workflow execution testing.

This module provides the workflow tester node that:
1. Validates workflow input/output schemas using Pydantic
2. Registers the generated workflow to graphAiServer
3. Executes workflow with sample input
"""

import logging
import os
from typing import Any, Dict

import httpx

from ..state import WorkflowGeneratorState
from .workflow_validator import WorkflowSchemaValidator

logger = logging.getLogger(__name__)

# GraphAI Server URL
GRAPHAISERVER_BASE_URL = os.getenv(
    "GRAPHAISERVER_BASE_URL",
    "http://localhost:8105",
)


def _safe_json(response: httpx.Response) -> dict[str, Any]:
    try:
        result: dict[str, Any] = response.json()
        return result
    except ValueError:
        return {"raw": response.text[:500]}


async def _register_workflow(
    client: httpx.AsyncClient,
    workflow_name: str,
    yaml_content: str,
    task_master_id: str | int | None = None,
) -> tuple[bool, dict[str, Any], int, str | None]:
    register_url = f"{GRAPHAISERVER_BASE_URL}/api/v1/workflows/register"
    payload = {
        "workflow_name": workflow_name,
        "yaml_content": yaml_content,
        "overwrite": True,
    }

    # Add directory parameter if task_master_id is provided
    if task_master_id:
        payload["directory"] = f"taskmaster/{task_master_id}"
        logger.info("Registering workflow to directory: taskmaster/%s", task_master_id)

    logger.info("Registering workflow to %s", register_url)
    response = await client.post(register_url, json=payload)
    body = _safe_json(response)
    status = response.status_code
    logger.debug("Register response status: %s", status)
    if status not in (200, 201):
        logger.error("Workflow registration failed: %s", body)
        return False, body, status, None
    file_path = body.get("file_path")
    logger.info("Workflow registered successfully: %s", file_path)
    return True, body, status, file_path


async def _execute_workflow(
    client: httpx.AsyncClient,
    workflow_name: str,
    sample_input: Any,
    task_master_id: str | int | None = None,
) -> tuple[dict[str, Any], int]:
    execute_url = f"{GRAPHAISERVER_BASE_URL}/api/v1/myagent"

    # Include directory path in model_name if task_master_id is provided
    model_name = (
        f"taskmaster/{task_master_id}/{workflow_name}"
        if task_master_id
        else workflow_name
    )

    payload = {
        "user_input": sample_input,
        "model_name": model_name,
    }
    logger.info("Executing workflow at %s with model_name: %s", execute_url, model_name)
    response = await client.post(execute_url, json=payload)
    status = response.status_code
    body = _safe_json(response)
    logger.debug("Execute response status: %s", status)
    if status == 200:
        logger.info("Workflow execution successful")
    else:
        logger.warning("Workflow execution returned status %s", status)
    return body, status


async def workflow_tester_node(
    state: WorkflowGeneratorState,
) -> WorkflowGeneratorState:
    """Validate and test workflow execution.

    This node:
    1. Validates input schema using Pydantic (pre-execution validation)
    2. Registers YAML workflow (POST /api/v1/workflows/register)
       - Saves to /taskmaster/{task_master_id}/ directory if task_master_id exists
       - Otherwise saves to root config/graphai/ directory
    3. Executes workflow with sample_input (POST /api/v1/myagent)
    4. Validates output schema using Pydantic (post-execution validation)
    5. Updates state with execution results and HTTP status

    Args:
        state: Current workflow generator state

    Returns:
        Updated state with validation and test execution results
    """
    logger.info("Starting workflow tester node")

    workflow_name = state.get("workflow_name")
    yaml_content = state.get("yaml_content")
    sample_input = state.get("sample_input")
    task_master_id = state.get("task_master_id")
    input_schema: Dict[str, Any] = state.get("input_schema", {})  # type: ignore
    output_schema: Dict[str, Any] = state.get("output_schema", {})  # type: ignore

    if not workflow_name or not yaml_content:
        message = "Workflow testing failed: missing workflow content"
        logger.error(message)
        return {
            **state,
            "status": "failed",
            "error_message": message,
        }

    if sample_input is None:
        logger.info("Sample input missing; defaulting to empty object")
        sample_input = {}

    # Step 0: Pre-execution schema validation with Pydantic
    logger.info("Starting pre-execution schema validation")
    validator = WorkflowSchemaValidator(input_schema, output_schema)

    # Ensure sample_input is a dict for validation
    if not isinstance(sample_input, dict):
        sample_input_dict: Dict[str, Any] = {"value": sample_input}
        logger.warning("Sample input is not a dict, wrapping in {'value': ...}")
    else:
        sample_input_dict = sample_input

    input_validation = validator.validate_input(sample_input_dict)

    if not input_validation.is_valid:
        logger.error("Input schema validation failed: %s", input_validation.errors)
        return {
            **state,
            "validation_errors": input_validation.errors,
            "status": "validation_failed",
            "error_message": f"Input validation failed: {'; '.join(input_validation.errors)}",
        }

    logger.info("Pre-execution schema validation passed")

    logger.debug(f"Testing workflow: {workflow_name}")
    logger.debug(f"Sample input: {sample_input}")

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Step 1: Register workflow to graphAiServer
            (
                registered,
                register_body,
                register_status,
                workflow_file_path,
            ) = await _register_workflow(
                client, workflow_name, yaml_content, task_master_id
            )

            if not registered:
                return {
                    **state,
                    "workflow_registered": False,
                    "test_http_status": register_status,
                    "test_execution_result": register_body,
                    "status": "registration_failed",
                    "error_message": "Workflow registration failed",
                }

            # Step 2: Execute workflow
            execution_result, execution_status = await _execute_workflow(
                client,
                workflow_name,
                sample_input,
                task_master_id,
            )

            # Step 3: Post-execution output validation (if execution succeeded)
            output_validation_errors: list[str] = []
            if (
                execution_status == 200
                and execution_result
                and isinstance(execution_result, dict)
            ):
                logger.info("Starting post-execution output schema validation")
                output_validation = validator.validate_output(execution_result)

                if not output_validation.is_valid:
                    logger.warning(
                        "Output schema validation failed: %s",
                        output_validation.errors,
                    )
                    output_validation_errors = output_validation.errors
                else:
                    logger.info("Post-execution output validation passed")
            elif execution_status == 200 and execution_result:
                logger.warning(
                    "Execution result is not a dict, skipping output validation"
                )

            return {
                **state,
                "workflow_registered": True,
                "workflow_file_path": workflow_file_path,
                "test_execution_result": execution_result,
                "test_http_status": execution_status,
                "validation_errors": output_validation_errors,
                "status": "workflow_tested",
            }

    except httpx.TimeoutException as e:
        logger.error(f"Workflow execution timeout: {e}", exc_info=True)
        return {
            **state,
            "workflow_registered": state.get("workflow_registered", False),
            "test_http_status": 504,
            "status": "execution_timeout",
            "error_message": f"Workflow execution timeout: {str(e)}",
        }
    except Exception as e:
        logger.error(f"Error during workflow testing: {e}", exc_info=True)
        return {
            **state,
            "status": "failed",
            "error_message": f"Workflow testing failed: {str(e)}",
        }
