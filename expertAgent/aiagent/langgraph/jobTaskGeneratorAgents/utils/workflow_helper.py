"""Workflow generation helper for Job/Task Generator.

Issue #305: This module provides a helper function to generate GraphAI YAML
workflows for individual TaskMasters.

Issue #305 Extension: Added summary data extraction for UI display.

Note: Uses lazy import to avoid circular dependency with workflowGeneratorAgents.
"""

import logging
from typing import Any, Optional

from app.services.failure_details_builder import build_failure_details
from app.services.job_creation_state import (
    EvaluationSummary,
    RetryInfo,
    TestExecutionSummary,
    WorkflowGenerationSummary,
)

logger = logging.getLogger(__name__)


def _build_summary_from_state(state: dict[str, Any]) -> WorkflowGenerationSummary:
    """Build WorkflowGenerationSummary from WorkflowGeneratorState.

    Args:
        state: Final state from workflow generator

    Returns:
        WorkflowGenerationSummary with extracted data
    """
    # YAML preview (first 500 chars) and full content
    yaml_content_full = state.get("yaml_content", "")
    yaml_preview = yaml_content_full[:500] if yaml_content_full else None

    # Sample input
    sample_input = state.get("sample_input")
    if sample_input is not None and not isinstance(sample_input, dict):
        sample_input = {"value": sample_input}

    # Test execution summary
    test_result = None
    test_http_status = state.get("test_http_status")
    if test_http_status is not None:
        test_result = TestExecutionSummary(
            http_status=test_http_status,
            is_valid=state.get("is_valid", False),
            validation_errors=state.get("validation_errors", []),
            execution_time_ms=None,  # Not tracked separately
        )

    # Evaluation summary
    evaluation = None
    llm_eval = state.get("llm_evaluation_result")
    if llm_eval:
        evaluation = EvaluationSummary(
            score=llm_eval.get("overall_score"),
            structural_score=llm_eval.get("structural_score"),
            requirement_score=llm_eval.get("requirement_score"),
            output_quality_score=llm_eval.get("output_quality_score"),
            error_handling_score=llm_eval.get("error_handling_score"),
            test_data_quality_score=llm_eval.get("test_data_quality_score"),
            strengths=llm_eval.get("strengths", []),
            weaknesses=llm_eval.get("weaknesses", []),
            suggestions=llm_eval.get("suggestions", []),
            confidence=llm_eval.get("confidence"),
        )
    elif state.get("evaluation_score") is not None:
        # Fast mode may skip LLM evaluation but still have a score
        evaluation = EvaluationSummary(
            score=state.get("evaluation_score"),
            suggestions=state.get("evaluation_suggestions", []),
        )

    # Retry info
    retry_info = RetryInfo(
        retry_count=state.get("retry_count", 0),
        max_retry=state.get("max_retry", 3),
        generation_model=state.get("generation_model"),
    )

    # Failure details (only if failed)
    failure_details = None
    if state.get("status") == "failed" or not state.get("is_valid", False):
        failure_details = build_failure_details(state)

    return WorkflowGenerationSummary(
        yaml_preview=yaml_preview,
        yaml_content=yaml_content_full if yaml_content_full else None,
        sample_input=sample_input,
        test_result=test_result,
        evaluation=evaluation,
        retry_info=retry_info,
        failure_details=failure_details,
    )


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
    # Lazy import to avoid circular dependency
    # (jobTaskGeneratorAgents.utils → workflowGeneratorAgents.agent → nodes → generator
    #  → jobTaskGeneratorAgents.utils)
    from aiagent.langgraph.workflowGeneratorAgents.agent import generate_workflow

    task_id = task_master.get("id", "unknown")
    task_name = task_master.get("name", "Unknown Task")

    logger.info(f"Generating workflow for task {task_id}: {task_name}")

    try:
        # Build task_data in the format expected by generate_workflow
        # Note: sample_input_generator expects input_interface.schema structure
        task_data = {
            "name": task_name,
            "description": task_master.get("description", ""),
            "recommended_apis": task_master.get("recommended_apis", []),
            "input_interface": {"schema": task_master.get("input_schema", {})},
            "output_interface": {"schema": task_master.get("output_schema", {})},
        }

        # Call the existing Workflow Generator
        result = await generate_workflow(
            task_master_id=task_id,
            task_data=task_data,
            max_retry=3,
            callback_handler=langfuse_handler,
        )

        # Build summary from the result state
        summary = _build_summary_from_state(result)

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
                "summary": summary,
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
                "summary": summary,
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
