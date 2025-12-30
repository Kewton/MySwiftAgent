"""API endpoints for GraphAI Workflow Generator.

Issue #278: Added Langfuse tracing integration for LLM observability.
"""

import logging
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
    SchemaValidationIssue,
    SchemaValidationRequest,
    SchemaValidationResponse,
    WorkflowGeneratorRequest,
    WorkflowGeneratorResponse,
    WorkflowResult,
)
from app.services.langfuse_service import LangfuseService, langfuse_service

logger = logging.getLogger(__name__)

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

    Issue #278: Added Langfuse tracing integration for LLM observability.

    Args:
        request: WorkflowGeneratorRequest with job_master_id or task_master_id

    Returns:
        WorkflowGeneratorResponse with generated workflows

    Raises:
        HTTPException: If JobMaster/TaskMaster not found or API error occurs
    """
    start_time = time.time()

    # Issue #278: Create a session ID for Langfuse tracing
    session_id = str(request.job_master_id or request.task_master_id)

    # Issue #278: Get Langfuse callback handler for tracing
    langfuse_handler = langfuse_service.get_callback_handler(
        trace_name="workflow_generation",
        session_id=session_id,
        tags=["workflow_generator"],
    )

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

            # Issue #278: Generate workflow using LangGraph Agent with Langfuse handler
            final_state = await generate_workflow_with_agent(
                task_master_id=task_master_id_value,
                task_data=task_data,
                max_retry=3,
                callback_handler=langfuse_handler,
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

        # Issue #278: Extract trace_id from Langfuse handler
        trace_id = LangfuseService.extract_trace_id(langfuse_handler)
        if trace_id:
            logger.info(f"Workflow generation Langfuse trace_id: {trace_id}")

        # Issue #278: Flush Langfuse traces to ensure they're sent
        if langfuse_handler is not None:
            langfuse_service.flush()

        return WorkflowGeneratorResponse(
            status=overall_status,
            workflows=workflows,
            total_tasks=total_tasks,
            successful_tasks=successful_tasks,
            failed_tasks=failed_tasks,
            generation_time_ms=generation_time_ms,
            langfuse_trace_id=trace_id,  # Issue #278
        )

    except JobqueueAPIError as e:
        # Issue #278: Flush traces even on failure
        if langfuse_handler is not None:
            langfuse_service.flush()
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
        # Issue #278: Flush traces even on failure
        if langfuse_handler is not None:
            langfuse_service.flush()
        # Handle unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        ) from e


@router.post(
    "/workflow-generator/validate-schema",
    response_model=SchemaValidationResponse,
    status_code=status.HTTP_200_OK,
    summary="Validate GraphAI Workflow Schema (Issue #333)",
    description="Validate GraphAI workflow YAML for API type compatibility and field name correctness. "
    "This endpoint performs rule-based validation without LLM calls.",
)
async def validate_workflow_schema(
    request: SchemaValidationRequest,
) -> SchemaValidationResponse:
    """Validate GraphAI workflow YAML schema (Issue #333).

    This endpoint validates:
    1. Type compatibility (Object vs String for API fields)
    2. Field name correctness (e.g., system_prompt vs system_imput typo)
    3. Required fields presence

    No LLM calls are made - this is pure rule-based validation.

    Args:
        request: SchemaValidationRequest with yaml_content

    Returns:
        SchemaValidationResponse with validation results
    """
    import yaml

    from aiagent.langgraph.workflowGeneratorAgents.nodes.workflow_schema_validator import (
        _check_field_names,
        _check_type_mismatch,
    )

    yaml_content = request.yaml_content

    # Handle empty YAML
    if not yaml_content or not yaml_content.strip():
        return SchemaValidationResponse(
            is_valid=True,
            issues=[],
            validated_nodes=0,
            api_calls_detected=0,
            warning_count=0,
            error_count=0,
        )

    # Parse YAML
    try:
        workflow = yaml.safe_load(yaml_content)
        if not isinstance(workflow, dict):
            return SchemaValidationResponse(
                is_valid=False,
                issues=[
                    SchemaValidationIssue(
                        node_id="yaml",
                        issue_type="yaml_parse_error",
                        message="YAML content is not a dictionary",
                        severity="error",
                    )
                ],
                validated_nodes=0,
                api_calls_detected=0,
                warning_count=0,
                error_count=1,
            )
    except yaml.YAMLError as e:
        return SchemaValidationResponse(
            is_valid=False,
            issues=[
                SchemaValidationIssue(
                    node_id="yaml",
                    issue_type="yaml_parse_error",
                    message=f"YAML parse error: {e}",
                    severity="error",
                )
            ],
            validated_nodes=0,
            api_calls_detected=0,
            warning_count=0,
            error_count=1,
        )

    # Validate nodes
    issues_raw: list[dict] = []
    nodes = workflow.get("nodes", {})
    validated_nodes = len(nodes) if isinstance(nodes, dict) else 0
    api_calls_detected = 0

    if isinstance(nodes, dict):
        for node_id, node_def in nodes.items():
            if not isinstance(node_def, dict):
                continue

            agent = node_def.get("agent")
            if agent != "fetchAgent":
                continue

            api_calls_detected += 1

            # Get URL from inputs
            inputs = node_def.get("inputs", {})
            url = inputs.get("url", "")

            # Check type mismatches
            issues_raw.extend(_check_type_mismatch(node_id, node_def, url))

            # Check field names
            issues_raw.extend(_check_field_names(node_id, node_def))

    # Convert to Pydantic models
    issues = [
        SchemaValidationIssue(
            node_id=i.get("node_id", ""),
            issue_type=i.get("issue_type", ""),
            message=i.get("message", ""),
            severity=i.get("severity", "error"),
            field_name=i.get("field_name", ""),
            expected_value=i.get("expected_value", ""),
            actual_value=i.get("actual_value", ""),
            suggestion=i.get("suggestion"),
        )
        for i in issues_raw
    ]

    warning_count = sum(1 for i in issues if i.severity == "warning")
    error_count = sum(1 for i in issues if i.severity == "error")

    return SchemaValidationResponse(
        is_valid=error_count == 0,
        issues=issues,
        validated_nodes=validated_nodes,
        api_calls_detected=api_calls_detected,
        warning_count=warning_count,
        error_count=error_count,
    )
