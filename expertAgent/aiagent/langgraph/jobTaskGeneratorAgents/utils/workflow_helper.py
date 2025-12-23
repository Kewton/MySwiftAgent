"""Workflow generation helper for Job/Task Generator.

Issue #305: This module provides a helper function to generate GraphAI YAML
workflows for individual TaskMasters.
"""

import logging
from typing import Any, Optional

from aiagent.langgraph.workflowGeneratorAgents.agent import generate_workflow

logger = logging.getLogger(__name__)


async def generate_workflow_for_task(
    task_master: dict[str, Any],
    langfuse_handler: Optional[Any] = None,
) -> dict[str, Any]:
    """Generate GraphAI YAML workflow for a TaskMaster.

    This function wraps the existing Workflow Generator Agent and converts
    TaskMaster format to Workflow Generator input format.

    Issue #305: Added to support automatic workflow generation during job
    creation.

    Args:
        task_master: TaskMaster definition with id, name, description,
            recommended_apis, input_schema, output_schema
        langfuse_handler: Optional Langfuse callback handler for tracing

    Returns:
        dict with:
            - workflow_name: str (e.g., "workflow_tm_001")
            - yaml_content: str (GraphAI YAML content)
            - status: "success" | "failed"
            - error_message: Optional[str] (if failed)
    """
    task_id = task_master.get("id", "unknown")
    task_name = task_master.get("name", "Unknown Task")

    logger.info(f"Generating workflow for task {task_id}: {task_name}")

    try:
        # Build task_data in the format expected by generate_workflow
        task_data = {
            "name": task_name,
            "description": task_master.get("description", ""),
            "recommended_apis": task_master.get("recommended_apis", []),
            "input_interface": task_master.get("input_schema", {}),
            "output_interface": task_master.get("output_schema", {}),
        }

        # Call the existing Workflow Generator
        result = await generate_workflow(
            task_master_id=task_id,
            task_data=task_data,
            max_retry=3,
            callback_handler=langfuse_handler,
        )

        # Check if workflow generation was successful
        if result.get("status") == "success" or result.get("is_valid", False):
            yaml_content = result.get("workflow_yaml", result.get("yaml_content", ""))
            workflow_name = f"workflow_{task_id}"

            logger.info(
                f"Successfully generated workflow for task {task_id}: {workflow_name}"
            )

            return {
                "status": "success",
                "workflow_name": workflow_name,
                "yaml_content": yaml_content,
            }
        else:
            # Note: result.get("error_message", default) returns None if key exists
            # but value is None, so we need to handle None explicitly with `or`
            validation_errors = result.get("validation_errors", [])
            error_message = (
                result.get("error_message")
                or (validation_errors[0] if validation_errors else None)
                or f"Workflow generation failed (status={result.get('status', 'unknown')})"
            )
            logger.warning(
                f"Workflow generation failed for task {task_id}: {error_message}"
            )
            return {
                "status": "failed",
                "workflow_name": None,
                "yaml_content": None,
                "error_message": error_message,
            }

    except Exception as e:
        error_message = str(e)
        logger.error(
            f"Exception during workflow generation for task {task_id}: {error_message}",
            exc_info=True,
        )
        return {
            "status": "failed",
            "workflow_name": None,
            "yaml_content": None,
            "error_message": error_message,
        }
