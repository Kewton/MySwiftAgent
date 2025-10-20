"""API endpoints for Job/Task Auto-Generation."""

import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException

from aiagent.langgraph.jobTaskGeneratorAgents import (
    create_initial_state,
    create_job_task_generator_agent,
)
from app.schemas.job_generator import JobGeneratorRequest, JobGeneratorResponse
from core.secrets import secrets_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/job-generator",
    response_model=JobGeneratorResponse,
    summary="Job/Task Auto-Generation",
    description="Automatically generate Job and Tasks from natural language requirements using LangGraph agent",
    tags=["Job Generator"],
)
async def generate_job_and_tasks(
    request: JobGeneratorRequest,
) -> JobGeneratorResponse:
    """Generate Job and Tasks from natural language requirements.

    This endpoint uses a LangGraph agent to:
    1. Analyze user requirements and decompose into tasks
    2. Evaluate task quality and feasibility
    3. Define JSON Schema interfaces
    4. Create TaskMasters, JobMaster, and JobMasterTask associations
    5. Validate workflow interfaces
    6. Register executable Job

    Args:
        request: Job generation request with user requirement

    Returns:
        Job generation response with job_id, status, and detailed results

    Raises:
        HTTPException: If job generation fails critically
    """
    logger.info(f"Job generation request received: {request.user_requirement[:100]}...")

    try:
        # Load ANTHROPIC_API_KEY from myVault and set as environment variable
        # This is required for ChatAnthropic to work properly
        try:
            anthropic_api_key = secrets_manager.get_secret(
                "ANTHROPIC_API_KEY", project=None
            )
            os.environ["ANTHROPIC_API_KEY"] = anthropic_api_key
            logger.info(
                f"ANTHROPIC_API_KEY loaded from myVault (prefix: {anthropic_api_key[:20]}..., length: {len(anthropic_api_key)})"
            )
        except ValueError as e:
            logger.error(f"Failed to load ANTHROPIC_API_KEY from myVault: {e}")
            raise HTTPException(
                status_code=500,
                detail="ANTHROPIC_API_KEY not configured in myVault. Please add it via CommonUI.",
            ) from e

        # Create initial state
        initial_state = create_initial_state(
            user_requirement=request.user_requirement,
        )

        # Override max retry count if specified
        if request.max_retry != 5:
            logger.info(f"Using custom max_retry: {request.max_retry}")
            # Note: MAX_RETRY_COUNT is defined in agent.py (5 by default)
            # This would require agent modification to support dynamic retry count
            # For now, we log the request but use the default value

        # Create and invoke LangGraph agent
        logger.info("Creating Job/Task Generator Agent")
        agent = create_job_task_generator_agent()

        logger.info("Invoking LangGraph agent")
        # Phase 8: Set recursion_limit to 50 (default is 25)
        final_state = await agent.ainvoke(initial_state, config={"recursion_limit": 50})

        logger.info("LangGraph agent execution completed")
        logger.debug(f"Final state keys: {final_state.keys()}")

        # Extract results from final state
        return _build_response_from_state(final_state)

    except Exception as e:
        logger.error(f"Job generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Job generation failed: {str(e)}",
        ) from e


def _build_response_from_state(state: dict[str, Any]) -> JobGeneratorResponse:
    """Build JobGeneratorResponse from final LangGraph state.

    Args:
        state: Final state from LangGraph agent execution

    Returns:
        JobGeneratorResponse with extracted information
    """
    # Check for error in state
    error_message = state.get("error_message")

    # Extract job information
    job_id = state.get("job_id")
    job_master_id = state.get("job_master_id")

    # Extract task breakdown
    task_breakdown = state.get("task_breakdown")

    # Extract evaluation result
    evaluation_result = state.get("evaluation_result")

    # Extract infeasible tasks and proposals from evaluation_result
    infeasible_tasks: list[dict[str, Any]] = []
    alternative_proposals: list[dict[str, Any]] = []
    api_extension_proposals: list[dict[str, Any]] = []

    if evaluation_result:
        infeasible_tasks = evaluation_result.get("infeasible_tasks", [])
        alternative_proposals = evaluation_result.get("alternative_proposals", [])
        api_extension_proposals = evaluation_result.get("api_extension_proposals", [])

    # Extract validation errors
    validation_result = state.get("validation_result")
    validation_errors: list[str] = []
    if validation_result and not validation_result.get("is_valid", True):
        validation_errors = validation_result.get("errors", [])

    # Determine status and generate user-friendly feedback
    if error_message:
        status = "failed"
        logger.warning(f"Job generation failed: {error_message}")
    elif job_id:
        if infeasible_tasks or api_extension_proposals:
            status = "partial_success"
            logger.info(
                f"Job generation partially successful (Job ID: {job_id}) "
                f"with {len(infeasible_tasks)} infeasible tasks"
            )

            # Generate user-friendly feedback for partial success
            feedback_parts = [
                f"Job successfully created (ID: {job_id}), but some tasks may require manual review:"
            ]

            if infeasible_tasks:
                feedback_parts.append(
                    f"\n{len(infeasible_tasks)} task(s) marked as potentially infeasible:"
                )
                for task in infeasible_tasks[:3]:  # Show first 3 tasks
                    task_name = task.get("task_name", "Unknown")
                    reason = task.get("reason", "No reason provided")
                    feedback_parts.append(f"  - {task_name}: {reason}")
                if len(infeasible_tasks) > 3:
                    feedback_parts.append(
                        f"  ... and {len(infeasible_tasks) - 3} more. See 'infeasible_tasks' for full list."
                    )

            if alternative_proposals:
                feedback_parts.append(
                    f"\n{len(alternative_proposals)} alternative proposal(s) available:"
                )
                for proposal in alternative_proposals[:3]:  # Show first 3 proposals
                    task_id = proposal.get("task_id", "unknown")
                    api = proposal.get("api_to_use", "unknown API")
                    feedback_parts.append(f"  - Task {task_id}: Consider using {api}")
                if len(alternative_proposals) > 3:
                    feedback_parts.append(
                        f"  ... and {len(alternative_proposals) - 3} more. See 'alternative_proposals' for details."
                    )

            if api_extension_proposals:
                feedback_parts.append(
                    f"\n{len(api_extension_proposals)} API extension(s) proposed for future improvement."
                )

            error_message = "\n".join(feedback_parts)
        else:
            status = "success"
            logger.info(f"Job generation successful (Job ID: {job_id})")
    else:
        # No job_id and no error_message means workflow ended before job_registration
        status = "failed"
        if not error_message:
            feedback_parts = ["Job generation did not complete successfully."]

            if infeasible_tasks:
                feedback_parts.append(
                    f"\nEvaluation detected {len(infeasible_tasks)} infeasible task(s):"
                )
                for task in infeasible_tasks[:3]:
                    task_name = task.get("task_name", "Unknown")
                    reason = task.get("reason", "No reason provided")
                    feedback_parts.append(f"  - {task_name}: {reason}")

            if alternative_proposals:
                feedback_parts.append(
                    f"\n{len(alternative_proposals)} alternative solution(s) proposed. "
                    "Consider revising requirements based on 'alternative_proposals'."
                )

            if validation_errors:
                feedback_parts.append(
                    f"\nValidation errors detected: {len(validation_errors)} error(s). "
                    "See 'validation_errors' for details."
                )

            if not infeasible_tasks and not validation_errors:
                feedback_parts.append(
                    "\nPlease check evaluation result and retry count. "
                    "Workflow may have exceeded maximum retry attempts."
                )

            error_message = "\n".join(feedback_parts)

    return JobGeneratorResponse(
        status=status,
        job_id=job_id,
        job_master_id=job_master_id,
        task_breakdown=task_breakdown,
        evaluation_result=evaluation_result,
        infeasible_tasks=infeasible_tasks,
        alternative_proposals=alternative_proposals,
        api_extension_proposals=api_extension_proposals,
        validation_errors=validation_errors,
        error_message=error_message,
    )
