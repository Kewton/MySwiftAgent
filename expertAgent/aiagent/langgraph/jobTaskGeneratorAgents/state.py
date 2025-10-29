"""State definition for Job/Task auto-generation agent.

This module defines the state structure for the LangGraph-based agent that
automatically generates jobqueue Jobs and Tasks from natural language
requirements.
"""

from typing import Any, TypedDict


class JobTaskGeneratorState(TypedDict, total=False):
    """State for Job/Task auto-generation workflow.

    This state tracks the complete workflow from user requirements to
    executable Job registration in jobqueue.

    Attributes:
        # Input fields
        user_requirement: Natural language description of the workflow
        max_retry: Maximum retry count for evaluation and validation

        # Intermediate processing fields
        task_breakdown: List of tasks decomposed from requirements
        interface_definitions: Mapping of task_id to interface schema bundle
        schema_enrichment_stats: Statistics from OpenAPI schema enrichment
        task_masters: List of TaskMaster definitions
        task_master_ids: Ordered list of TaskMaster IDs (preserves execution
            order)
        job_master: JobMaster definition
        job_master_id: Registered JobMaster ID

        # Feasibility analysis fields
        feasibility_analysis: Analysis result of task implementability
        infeasible_tasks: List of tasks difficult to implement
        alternative_proposals: Alternative solutions using existing APIs
        api_extension_proposals: Proposals for new Direct API features

        # Evaluation fields
        evaluation_result: Evaluation result against 6 principles
        evaluation_retry_count: Current evaluation retry count
        evaluation_errors: List of evaluation errors
        evaluation_feedback: Feedback from evaluator for retry improvement

        # Validation & retry fields
        validation_result: Workflow validation result from jobqueue
        retry_count: Current validation retry count
        validation_errors: List of validation errors

        # Output fields
        job_id: Registered Job ID (ready for execution)
        status: Workflow status (success, evaluation_failed, validation_failed,
            error)
        error_message: Error message if workflow failed
    """

    # ===== Input =====
    user_requirement: str
    max_retry: int

    # ===== Intermediate =====
    task_breakdown: list[dict[str, Any]]
    overall_summary: str  # Task breakdown summary from LLM
    interface_definitions: dict[str, dict[str, Any]]
    schema_enrichment_stats: dict[str, Any]  # Schema enrichment statistics
    task_masters: list[dict[str, Any]]
    task_master_ids: list[str]
    job_master: dict[str, Any]
    job_master_id: str | None

    # ===== Feasibility Analysis =====
    feasibility_analysis: dict[str, Any] | None
    infeasible_tasks: list[dict[str, Any]]
    alternative_proposals: list[dict[str, Any]]
    api_extension_proposals: list[dict[str, Any]]

    # ===== Evaluation =====
    evaluation_result: dict[str, Any] | None
    evaluation_retry_count: int
    evaluation_errors: list[str]
    evaluation_feedback: str | None
    # "after_task_breakdown" or "after_interface_definition"
    evaluator_stage: str

    # ===== Validation & Retry =====
    validation_result: dict[str, Any] | None
    retry_count: int
    validation_errors: list[str]

    # ===== Output =====
    job_id: str | None
    status: str
    error_message: str | None


def create_initial_state(
    user_requirement: str,
    max_retry: int = 5,
) -> JobTaskGeneratorState:
    """Create initial state with default values.

    Args:
        user_requirement: Natural language description of the workflow
        max_retry: Maximum retry count (default: 5)

    Returns:
        JobTaskGeneratorState: Initial state with default values
    """
    return {
        # Input
        "user_requirement": user_requirement,
        "max_retry": max_retry,
        # Intermediate
        "task_breakdown": [],
        "overall_summary": "",
        "interface_definitions": {},
        "schema_enrichment_stats": {},
        "task_masters": [],
        "task_master_ids": [],
        "job_master": {},
        "job_master_id": None,
        # Feasibility Analysis
        "feasibility_analysis": None,
        "infeasible_tasks": [],
        "alternative_proposals": [],
        "api_extension_proposals": [],
        # Evaluation
        "evaluation_result": None,
        "evaluation_retry_count": 0,
        "evaluation_errors": [],
        "evaluation_feedback": None,
        "evaluator_stage": "after_task_breakdown",  # Initial stage
        # Validation & Retry
        "validation_result": None,
        "retry_count": 0,
        "validation_errors": [],
        # Output
        "job_id": None,
        "status": "initialized",
        "error_message": None,
    }
