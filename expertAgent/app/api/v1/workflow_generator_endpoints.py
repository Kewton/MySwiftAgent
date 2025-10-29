"""API endpoints for GraphAI Workflow Generator."""

import time
from typing import Any

from fastapi import APIRouter, HTTPException, status

from aiagent.langgraph.jobTaskGeneratorAgents.utils.jobqueue_client import (
    JobqueueAPIError,
)
from aiagent.langgraph.workflowGeneratorAgents import (
    generate_workflow as generate_workflow_with_agent,
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
            # Convert to string if int (for backward compatibility)
            job_master_id_str = (
                str(request.job_master_id)
                if isinstance(request.job_master_id, int)
                else request.job_master_id
            )
            task_data_list = (
                await task_data_fetcher.fetch_task_masters_by_job_master_id(
                    job_master_id_str
                )
            )
        elif request.task_master_id is not None:
            # Fetch single task
            # Convert to string if int (for backward compatibility)
            task_master_id_str = (
                str(request.task_master_id)
                if isinstance(request.task_master_id, int)
                else request.task_master_id
            )
            task_data = await task_data_fetcher.fetch_task_master_by_id(
                task_master_id_str
            )
            task_data_list = [task_data]

        # Phase 3: Integrate LangGraph Agent for workflow generation
        workflows: list[WorkflowResult] = []
        for task_data in task_data_list:
            # Get task_master_id (ULID string or int)
            task_master_id_value = task_data["task_master_id"]

            # Generate workflow using LangGraph Agent
            final_state = await generate_workflow_with_agent(
                task_master_id=task_master_id_value,
                task_data=task_data,
                max_retry=3,
            )

            # Extract workflow result from final state
            workflow_status = final_state.get("status", "unknown")
            is_valid = final_state.get("is_valid", False)
            error_message = final_state.get("error_message")
            yaml_content = final_state.get("yaml_content", "")
            workflow_name = final_state.get(
                "workflow_name", task_data["name"].lower().replace(" ", "_")
            )
            retry_count = final_state.get("retry_count", 0)
            validation_result = final_state.get("validation_result")

            # Determine workflow result status
            if is_valid:
                result_status = "success"
            elif workflow_status == "max_retries_exceeded":
                result_status = "failed"
                error_message = f"Max retries exceeded ({retry_count} attempts)"
            else:
                result_status = "failed"

            workflow_result = WorkflowResult(
                task_master_id=task_master_id_value,
                task_name=task_data["name"],
                workflow_name=workflow_name,
                yaml_content=yaml_content,
                status=result_status,
                retry_count=retry_count,
                error_message=error_message,
                validation_result=validation_result,
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
