"""Pydantic schemas for Job/Task Auto-Generation API."""

from typing import Any

from pydantic import BaseModel, Field


class JobGeneratorRequest(BaseModel):
    """Request schema for Job/Task Auto-Generation API.

    Attributes:
        user_requirement: User requirement in natural language
        max_retry: Maximum retry count for evaluation and validation (default: 5)
    """

    user_requirement: str = Field(
        ...,
        description="User requirement in natural language for job/task generation",
        min_length=1,
        examples=["PDFファイルをGoogle Driveにアップロードして、完了をメール通知する"],
    )
    max_retry: int = Field(
        default=5,
        description="Maximum retry count for evaluation and validation",
        ge=1,
        le=10,
    )


class JobGeneratorResponse(BaseModel):
    """Response schema for Job/Task Auto-Generation API.

    Attributes:
        status: Status of job generation ("success", "failed", "partial_success")
        job_id: Created Job ID (only on success)
        job_master_id: Created JobMaster ID
        task_breakdown: Task breakdown result
        evaluation_result: Evaluation result
        infeasible_tasks: List of infeasible tasks
        alternative_proposals: List of alternative proposals for infeasible tasks
        api_extension_proposals: List of API extension proposals
        validation_errors: List of validation errors
        error_message: Error message (on failure)
    """

    status: str = Field(
        ...,
        description='Status of job generation: "success", "failed", "partial_success"',
        examples=["success"],
    )

    # Success fields
    job_id: str | None = Field(
        default=None,
        description="Created Job ID (only on success)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    job_master_id: int | None = Field(
        default=None,
        description="Created JobMaster ID",
        examples=[123],
    )

    # Task breakdown and evaluation
    task_breakdown: list[dict[str, Any]] | None = Field(
        default=None,
        description="Task breakdown result from requirement analysis",
    )
    evaluation_result: dict[str, Any] | None = Field(
        default=None,
        description="Evaluation result (quality, feasibility, etc.)",
    )

    # Feasibility analysis
    infeasible_tasks: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of infeasible tasks with reasons",
    )
    alternative_proposals: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of alternative proposals for infeasible tasks",
    )
    api_extension_proposals: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of API extension proposals for unsupported features",
    )
    requirement_relaxation_suggestions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of requirement relaxation suggestions for infeasible tasks",
    )

    # Validation
    validation_errors: list[str] = Field(
        default_factory=list,
        description="List of validation errors",
    )

    # Error fields
    error_message: str | None = Field(
        default=None,
        description="Error message (on failure)",
    )
