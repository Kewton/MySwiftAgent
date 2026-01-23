"""TaskMaster utility functions for Job Generator V2.

This module contains utility functions for TaskMaster operations,
particularly for updating body_template fields.

Issue #393: Relocated update_task_master_body_template_taskflow function
from workflow_gen/workflow_registrar.py to this module for better
organization within the registration package.

Functions:
    update_task_master_body_template_taskflow: Update TaskMaster body_template
        for TaskFlow V2 workflow execution.
"""

from __future__ import annotations

import logging

from core.config import settings

logger = logging.getLogger(__name__)

# JobQueue configuration
JOBQUEUE_API_URL = settings.JOBQUEUE_API_URL or "http://localhost:8001"


async def update_task_master_body_template_taskflow(
    task_master_id: str,
    workflow_name: str,
) -> bool:
    """Update TaskMaster body_template for TaskFlow V2 workflow execution.

    Issue #350: TaskFlow V2 uses different body_template structure:
    - workflow_name: Name of registered workflow
    - inputs: Maps user_input to TaskFlow inputs format
    - project: Project for secrets resolution

    Issue #390: Updated to use 'workflow' field instead of 'workflow_name'
    in body_template, as mySwiftAgentCore expects 'workflow' field.

    Issue #393: Relocated from workflow_gen/workflow_registrar.py to
    registration/task_master_utils.py for better organization.

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

        # Issue #390: Get existing inputs and project to preserve task chaining
        # Issue #396: Use {{job.body.project}} instead of {{job.project}}
        # TemplateResolver only supports {{job.body}} and {{job.body.field}} patterns
        # Issue #396: Use existing user_input field as the basis for inputs
        # For task 1: user_input = "{{job.body.user_input}}"
        # For task N: user_input = "{{tasks[N-1].output_data}}"
        # This preserves task chaining by using previous task's output
        existing_user_input = existing_body_template.get("user_input")
        existing_inputs = existing_body_template.get(
            "inputs", existing_user_input or "{{job.body.user_input}}"
        )
        existing_project = existing_body_template.get("project", "{{job.body.project}}")

        # Build TaskFlow V2 body_template
        # Issue #390: Use 'workflow' field instead of 'workflow_name'
        # TaskFlow API expects: workflow, inputs (object), project
        body_template = {
            "workflow": workflow_name,  # Issue #390: Changed from workflow_name
            "inputs": existing_inputs,  # Preserve for task chaining
            "project": existing_project,  # Preserve for secrets
            "job_params": existing_job_params,  # Preserve for compatibility
        }

        await client.update_task_master(
            master_id=task_master_id,
            body_template=body_template,
            updated_by="job_generator_v2",
            change_reason="Set workflow for TaskFlow V2 execution",
        )

        logger.info(
            "Updated TaskMaster %s body_template for TaskFlow V2: workflow=%s",
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


__all__ = [
    "update_task_master_body_template_taskflow",
    "JOBQUEUE_API_URL",
]
