"""API endpoints for GraphAI Workflow Generator."""

import time
from typing import Any

from fastapi import APIRouter, HTTPException, status

from aiagent.langgraph.jobTaskGeneratorAgents.utils.jobqueue_client import (
    JobqueueAPIError,
)
from aiagent.langgraph.workflowGeneratorAgents.utils.task_data_fetcher import (
    TaskDataFetcher,
)
from app.schemas.workflow_generator import (
    WorkflowGeneratorRequest,
    WorkflowGeneratorResponse,
    WorkflowResult,
)

router = APIRouter()


@router.post(
    "/workflow-generator",
    response_model=WorkflowGeneratorResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate GraphAI Workflow YAML",
    description="Generate GraphAI workflow YAML files from JobMaster or TaskMaster",
)
async def generate_workflow(
    request: WorkflowGeneratorRequest,
) -> WorkflowGeneratorResponse:
    """Generate GraphAI workflow YAML files.

    Args:
        request: WorkflowGeneratorRequest with job_master_id or task_master_id

    Returns:
        WorkflowGeneratorResponse with generated workflows

    Raises:
        HTTPException: If JobMaster/TaskMaster not found or API error occurs
    """
    start_time = time.time()

    try:
        # Initialize TaskDataFetcher
        task_data_fetcher = TaskDataFetcher()

        # Fetch task data based on input type
        task_data_list: list[dict[str, Any]] = []
        if request.job_master_id is not None:
            # Fetch all tasks in the job
            task_data_list = (
                await task_data_fetcher.fetch_task_masters_by_job_master_id(
                    request.job_master_id
                )
            )
        elif request.task_master_id is not None:
            # Fetch single task
            task_data = await task_data_fetcher.fetch_task_master_by_id(
                request.task_master_id
            )
            task_data_list = [task_data]

        # TODO: Phase 3 - Integrate LangGraph Agent for workflow generation
        # For now, return stub response with task data
        workflows: list[WorkflowResult] = []
        for task_data in task_data_list:
            # Generate workflow name from task name
            workflow_name = task_data["name"].lower().replace(" ", "_")

            # Create stub YAML content
            yaml_content = f"""# Stub workflow for task: {task_data["name"]}
# TODO: LangGraph Agent will generate this in Phase 3
version: 0.5
nodes:
  stub_node:
    value: "This is a stub workflow"
"""

            # Create WorkflowResult
            # task_master_id can be string or int from jobqueue API
            task_master_id_value = task_data["task_master_id"]
            if isinstance(task_master_id_value, str):
                # Extract numeric part if it's a string like "task_1" or just "123"
                import re

                match = re.search(r"\d+", task_master_id_value)
                if match:
                    task_master_id_int = int(match.group())
                else:
                    # Use hash as fallback if no numeric part found
                    task_master_id_int = hash(task_master_id_value) % (10**8)
            else:
                task_master_id_int = int(task_master_id_value)

            workflow_result = WorkflowResult(
                task_master_id=task_master_id_int,
                task_name=task_data["name"],
                workflow_name=workflow_name,
                yaml_content=yaml_content,
                status="success",
                retry_count=0,
            )
            workflows.append(workflow_result)

        # Calculate statistics
        total_tasks = len(workflows)
        successful_tasks = sum(1 for w in workflows if w.status == "success")
        failed_tasks = sum(1 for w in workflows if w.status == "failed")

        # Determine overall status
        if failed_tasks == 0:
            overall_status = "success"
        elif successful_tasks == 0:
            overall_status = "failed"
        else:
            overall_status = "partial_success"

        # Calculate generation time
        generation_time_ms = (time.time() - start_time) * 1000

        return WorkflowGeneratorResponse(
            status=overall_status,
            workflows=workflows,
            total_tasks=total_tasks,
            successful_tasks=successful_tasks,
            failed_tasks=failed_tasks,
            generation_time_ms=generation_time_ms,
        )

    except JobqueueAPIError as e:
        # Handle JobqueueAPI errors (404, 500, etc.)
        if e.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"JobMaster or TaskMaster not found: {e.message}",
            ) from e
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Jobqueue API error: {e.message}",
            ) from e
    except Exception as e:
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e
