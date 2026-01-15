"""Workflow registration utilities for Job Generator V2.

This module provides functions to:
1. Register workflow YAML to GraphAiServer (GraphAI engine)
2. Register workflow JSON to GraphAiServer (TaskFlow V2 engine)
3. Update TaskMaster body_template with appropriate parameters

Issue #342: Fix for model_name is required error when executing workflows.
The V2 workflow generation was missing the step to register workflows
to GraphAiServer and update TaskMaster body_templates with model_name.

Issue #350: Added TaskFlow V2 registration support using /api/v2/workflows endpoint.
TaskFlow V2 workflows use a different body_template structure:
- workflow_name: Name of registered workflow
- inputs: Mapped from user_input for compatibility

Issue #355: Added TaskFlowAdapter for JSON string to object conversion.
ExpertAgent/LLM may output JSON strings for dict fields (input_schema, output_schema, etc.)
but GraphAiServer expects objects. TaskFlowAdapter converts these before registration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import httpx

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter import (
    TaskFlowAdapter,
)
from core.config import settings

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext

logger = logging.getLogger(__name__)

# Module-level adapter instance for TaskFlow JSON conversion
# Issue #355: Converts JSON string fields to objects before GraphAiServer registration
_adapter = TaskFlowAdapter()

# GraphAiServer configuration
GRAPHAISERVER_BASE_URL = settings.GRAPHAISERVER_BASE_URL or "http://localhost:8005"
JOBQUEUE_API_URL = settings.JOBQUEUE_API_URL or "http://localhost:8001"


@dataclass
class WorkflowRegistrationResult:
    """Result of workflow registration.

    Attributes:
        success: Whether registration succeeded
        workflow_path: Path where workflow is registered
        model_name: model_name for TaskMaster body_template
        error: Error message if registration failed
    """

    success: bool
    workflow_path: str | None = None
    model_name: str | None = None
    error: str | None = None


async def register_workflow_to_graphai(
    workflow_name: str,
    yaml_content: str,
    task_master_id: str,
) -> WorkflowRegistrationResult:
    """Register workflow YAML to GraphAiServer.

    Args:
        workflow_name: Name of the workflow (e.g., workflow_jm_xxx)
        yaml_content: YAML content string
        task_master_id: TaskMaster ID for directory organization

    Returns:
        WorkflowRegistrationResult with registration status
    """
    register_url = f"{GRAPHAISERVER_BASE_URL}/api/v1/workflows/register"

    payload = {
        "workflow_name": workflow_name,
        "yaml_content": yaml_content,
        "overwrite": True,
        "directory": f"taskmaster/{task_master_id}",
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(register_url, json=payload)

            if response.status_code == 200:
                result = response.json()
                workflow_path = result.get(
                    "workflow_path", f"taskmaster/{task_master_id}/{workflow_name}"
                )
                model_name = f"taskmaster/{task_master_id}/{workflow_name}"

                logger.info(
                    "Registered workflow to GraphAiServer: %s -> %s",
                    workflow_name,
                    workflow_path,
                )

                return WorkflowRegistrationResult(
                    success=True,
                    workflow_path=workflow_path,
                    model_name=model_name,
                )
            else:
                error_msg = f"GraphAiServer registration failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return WorkflowRegistrationResult(
                    success=False,
                    error=error_msg,
                )

    except httpx.TimeoutException as e:
        error_msg = f"GraphAiServer registration timeout: {e}"
        logger.error(error_msg)
        return WorkflowRegistrationResult(success=False, error=error_msg)
    except Exception as e:
        error_msg = f"GraphAiServer registration error: {e}"
        logger.error(error_msg, exc_info=True)
        return WorkflowRegistrationResult(success=False, error=error_msg)


async def register_taskflow_workflow(
    workflow_name: str,
    workflow_json: dict,
    admin_token: str | None = None,
) -> WorkflowRegistrationResult:
    """Register TaskFlow V2 workflow JSON to GraphAiServer.

    Issue #350: TaskFlow V2 workflows use /api/v2/workflows/register endpoint.
    Issue #355: Uses TaskFlowAdapter to convert JSON strings to objects before registration.

    Args:
        workflow_name: Name of the workflow (e.g., google_search_workflow)
        workflow_json: TaskFlow V2 workflow definition as dict
        admin_token: Admin token for registration (optional, uses settings if not provided)

    Returns:
        WorkflowRegistrationResult with registration status
    """
    # Issue #355: Convert JSON string fields to objects using TaskFlowAdapter
    conversion_result = _adapter.convert(workflow_json)

    if not conversion_result.success:
        error_msg = "; ".join(conversion_result.errors)
        logger.error("Workflow conversion failed: %s", error_msg)
        return WorkflowRegistrationResult(
            success=False,
            error=f"Schema conversion failed: {error_msg}",
        )

    # Log any warnings from conversion
    for warning in conversion_result.warnings:
        logger.warning("Workflow conversion warning: %s", warning)

    register_url = f"{GRAPHAISERVER_BASE_URL}/api/v2/workflows/register"

    # Use provided token or fall back to settings.GRAPHAISERVER_ADMIN_TOKEN
    # Issue #350: Use GRAPHAISERVER_ADMIN_TOKEN for TaskFlow V2 workflow registration
    token = admin_token or settings.GRAPHAISERVER_ADMIN_TOKEN

    # Use converted data for registration
    payload = {
        "workflow_name": workflow_name,
        "definition": conversion_result.data,  # Use converted data
        "overwrite": True,
    }

    headers = {
        "x-admin-token": token,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(register_url, json=payload, headers=headers)

            if response.status_code == 200:
                result = response.json()
                workflow_path = result.get(
                    "file_path", f"config/taskflow/workflows/{workflow_name}.json"
                )

                logger.info(
                    "Registered TaskFlow V2 workflow to GraphAiServer: %s -> %s",
                    workflow_name,
                    workflow_path,
                )

                return WorkflowRegistrationResult(
                    success=True,
                    workflow_path=workflow_path,
                    model_name=workflow_name,  # For TaskFlow, model_name is the workflow_name
                )
            else:
                error_msg = f"TaskFlow V2 registration failed: {response.status_code} - {response.text}"
                logger.error(error_msg)
                return WorkflowRegistrationResult(
                    success=False,
                    error=error_msg,
                )

    except httpx.TimeoutException as e:
        error_msg = f"TaskFlow V2 registration timeout: {e}"
        logger.error(error_msg)
        return WorkflowRegistrationResult(success=False, error=error_msg)
    except Exception as e:
        error_msg = f"TaskFlow V2 registration error: {e}"
        logger.error(error_msg, exc_info=True)
        return WorkflowRegistrationResult(success=False, error=error_msg)


async def update_task_master_body_template_taskflow(
    task_master_id: str,
    workflow_name: str,
) -> bool:
    """Update TaskMaster body_template for TaskFlow V2 workflow execution.

    Issue #350: TaskFlow V2 uses different body_template structure:
    - workflow_name: Name of registered workflow
    - inputs: Maps user_input to TaskFlow inputs format
    - project: Project for secrets resolution

    Args:
        task_master_id: TaskMaster ID to update
        workflow_name: Name of the registered TaskFlow workflow

    Returns:
        True if update succeeded, False otherwise
    """
    try:
        # Import here to avoid circular dependency
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.jobqueue_client import (
            JobqueueClient,
        )

        client = JobqueueClient(base_url=JOBQUEUE_API_URL)

        # Fetch existing TaskMaster to preserve job_params
        existing_task_master = await client.get_task_master(task_master_id)
        existing_body_template = existing_task_master.get("body_template", {}) or {}
        existing_job_params = existing_body_template.get("job_params", "{{job.body}}")

        # Build TaskFlow V2 body_template
        # TaskFlow API expects: workflow_name, inputs (object), project
        # Issue #350: inputs must be an object, not a string.
        # Pass entire job.body as inputs object - workflow will read user_input from it
        body_template = {
            "workflow_name": workflow_name,
            "inputs": "{{job.body}}",  # Pass entire body as inputs object
            "project": "{{job.project}}",  # Pass project for secrets
            "job_params": existing_job_params,  # Preserve for compatibility
        }

        await client.update_task_master(
            master_id=task_master_id,
            body_template=body_template,
            updated_by="job_generator_v2",
            change_reason="Set workflow_name for TaskFlow V2 execution",
        )

        logger.info(
            "Updated TaskMaster %s body_template for TaskFlow V2: workflow_name=%s",
            task_master_id,
            workflow_name,
        )
        return True

    except Exception as e:
        logger.error(
            "Failed to update TaskMaster %s body_template for TaskFlow V2: %s",
            task_master_id,
            e,
            exc_info=True,
        )
        return False


async def update_task_master_body_template(
    task_master_id: str,
    model_name: str,
) -> bool:
    """Update TaskMaster body_template with model_name.

    After workflow registration, the TaskMaster needs to be updated with
    the correct model_name so that JobQueue can execute the workflow.

    IMPORTANT: This function preserves the existing user_input and job_params values
    in body_template:
    - user_input: Contains task chaining configuration (e.g., {{job.body}} for first task,
      {{tasks[N-1].output_data}} for subsequent tasks)
    - job_params: Contains {{job.body}} for static parameter access

    Args:
        task_master_id: TaskMaster ID to update
        model_name: model_name value (e.g., taskmaster/{id}/{workflow_name})

    Returns:
        True if update succeeded, False otherwise
    """
    try:
        # Import here to avoid circular dependency
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.jobqueue_client import (
            JobqueueClient,
        )

        client = JobqueueClient(base_url=JOBQUEUE_API_URL)

        # Fetch existing TaskMaster to preserve user_input and job_params
        existing_task_master = await client.get_task_master(task_master_id)
        existing_body_template = existing_task_master.get("body_template", {}) or {}
        existing_user_input = existing_body_template.get("user_input", "{{job.body}}")
        existing_job_params = existing_body_template.get("job_params", "{{job.body}}")

        # Build new body_template preserving user_input and job_params, adding model_name
        body_template = {
            "user_input": existing_user_input,  # Preserve task chaining config
            "job_params": existing_job_params,  # Preserve static params access
            "model_name": model_name,
        }

        await client.update_task_master(
            master_id=task_master_id,
            body_template=body_template,
            updated_by="job_generator_v2",
            change_reason="Set model_name for workflow execution",
        )

        logger.info(
            "Updated TaskMaster %s body_template with model_name: %s "
            "(preserved user_input: %s, job_params: %s)",
            task_master_id,
            model_name,
            existing_user_input,
            existing_job_params,
        )
        return True

    except Exception as e:
        logger.error(
            "Failed to update TaskMaster %s body_template: %s",
            task_master_id,
            e,
            exc_info=True,
        )
        return False


async def register_and_update_task_masters(
    task_master_ids: list[str],
    workflow_name: str,
    yaml_content: str,
    context: "ExecutionContext | None" = None,
) -> dict[str, Any]:
    """Register workflow and update all TaskMasters with model_name.

    This is the main entry point for V2 workflow registration.
    It registers the workflow to GraphAiServer once, then updates
    all TaskMaster body_templates to use this workflow.

    Args:
        task_master_ids: List of TaskMaster IDs to update
        workflow_name: Name of the workflow
        yaml_content: YAML content string
        context: Optional execution context

    Returns:
        Dict with registration results:
        - success: bool
        - workflow_path: str (if successful)
        - model_name: str (if successful)
        - updated_task_masters: list of updated TaskMaster IDs
        - failed_task_masters: list of failed TaskMaster IDs
        - error: str (if failed)
    """
    if not task_master_ids:
        return {
            "success": False,
            "error": "No task_master_ids provided",
            "updated_task_masters": [],
            "failed_task_masters": [],
        }

    # Use first TaskMaster ID for directory organization
    primary_task_master_id = task_master_ids[0]

    # Step 1: Register workflow to GraphAiServer
    registration_result = await register_workflow_to_graphai(
        workflow_name=workflow_name,
        yaml_content=yaml_content,
        task_master_id=primary_task_master_id,
    )

    if not registration_result.success:
        logger.error(
            "Failed to register workflow to GraphAiServer: %s",
            registration_result.error,
        )
        return {
            "success": False,
            "error": registration_result.error,
            "updated_task_masters": [],
            "failed_task_masters": task_master_ids,
        }

    model_name = registration_result.model_name
    if model_name is None:
        # This should not happen if registration succeeded
        logger.error("Registration succeeded but model_name is None")
        return {
            "success": False,
            "error": "Registration succeeded but model_name was not returned",
            "updated_task_masters": [],
            "failed_task_masters": task_master_ids,
        }

    # Step 2: Update all TaskMasters with model_name
    updated_task_masters: list[str] = []
    failed_task_masters: list[str] = []

    for task_master_id in task_master_ids:
        success = await update_task_master_body_template(
            task_master_id=task_master_id,
            model_name=model_name,
        )

        if success:
            updated_task_masters.append(task_master_id)
        else:
            failed_task_masters.append(task_master_id)

    # Determine overall success
    # Issue #360: Require all TaskMasters to be updated successfully
    # Changed from: len(updated_task_masters) > 0 (partial success allowed)
    # To: len(failed_task_masters) == 0 (all must succeed)
    overall_success = len(failed_task_masters) == 0 and len(updated_task_masters) > 0

    if failed_task_masters:
        logger.warning(
            "Some TaskMasters failed to update: %s",
            failed_task_masters,
        )

    logger.info(
        "Workflow registration complete: %d/%d TaskMasters updated",
        len(updated_task_masters),
        len(task_master_ids),
    )

    return {
        "success": overall_success,
        "workflow_path": registration_result.workflow_path,
        "model_name": model_name,
        "updated_task_masters": updated_task_masters,
        "failed_task_masters": failed_task_masters,
    }
