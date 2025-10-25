"""Workflow tester node for GraphAI workflow execution testing.

This module provides the workflow tester node that registers the generated
workflow to graphAiServer and executes it with sample input.
"""

import logging
import os

import httpx

from ..state import WorkflowGeneratorState

logger = logging.getLogger(__name__)

# GraphAI Server URL
GRAPHAISERVER_BASE_URL = os.getenv("GRAPHAISERVER_BASE_URL", "http://localhost:8105")


async def workflow_tester_node(
    state: WorkflowGeneratorState,
) -> WorkflowGeneratorState:
    """Register workflow to graphAiServer and execute with sample input.

    This node:
    1. Registers YAML workflow to graphAiServer (POST /api/v1/workflows/register)
    2. Executes workflow with sample_input (POST /api/v1/myagent)
    3. Updates state with execution results and HTTP status

    Args:
        state: Current workflow generator state

    Returns:
        Updated state with test execution results
    """
    logger.info("Starting workflow tester node")

    workflow_name = state["workflow_name"]
    yaml_content = state["yaml_content"]
    sample_input = state["sample_input"]

    logger.debug(f"Testing workflow: {workflow_name}")
    logger.debug(f"Sample input: {sample_input}")

    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            # Step 1: Register workflow to graphAiServer
            register_url = f"{GRAPHAISERVER_BASE_URL}/api/v1/workflows/register"
            register_payload = {
                "workflow_name": workflow_name,
                "yaml_content": yaml_content,
                "overwrite": True,  # Allow overwriting during testing
            }

            logger.info(f"Registering workflow to {register_url}")
            register_response = await client.post(register_url, json=register_payload)

            logger.debug(f"Register response status: {register_response.status_code}")
            logger.debug(f"Register response: {register_response.text[:500]}")

            if register_response.status_code not in [200, 201]:
                logger.error(f"Workflow registration failed: {register_response.text}")
                return {
                    **state,
                    "workflow_registered": False,
                    "test_http_status": register_response.status_code,
                    "test_execution_result": register_response.json(),
                    "status": "registration_failed",
                    "error_message": f"Workflow registration failed: {register_response.text}",
                }

            register_data = register_response.json()
            workflow_file_path = register_data.get("file_path")

            logger.info(f"Workflow registered successfully: {workflow_file_path}")

            # Step 2: Execute workflow with sample input
            # Determine category from workflow_name (default: "test")
            category = "test"
            model_name = workflow_name

            execute_url = (
                f"{GRAPHAISERVER_BASE_URL}/api/v1/myagent/{category}/{model_name}"
            )
            execute_payload = {
                "user_input": sample_input,
            }

            logger.info(f"Executing workflow at {execute_url}")
            execute_response = await client.post(execute_url, json=execute_payload)

            logger.debug(f"Execute response status: {execute_response.status_code}")
            logger.debug(f"Execute response: {execute_response.text[:1000]}")

            # Parse execution result
            if execute_response.status_code == 200:
                execution_result = execute_response.json()
                logger.info("Workflow execution successful")
            else:
                execution_result = execute_response.json()
                logger.warning(
                    f"Workflow execution returned status {execute_response.status_code}"
                )

            # Update state
            return {
                **state,
                "workflow_registered": True,
                "workflow_file_path": workflow_file_path,
                "test_execution_result": execution_result,
                "test_http_status": execute_response.status_code,
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
