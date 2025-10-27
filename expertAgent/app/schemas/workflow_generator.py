"""Pydantic schemas for GraphAI Workflow Generator API."""

from typing import Any

from pydantic import BaseModel, Field, model_validator


class WorkflowGeneratorRequest(BaseModel):
    """Request schema for GraphAI Workflow Generator API.

    Attributes:
        job_master_id: JobMaster ID to generate workflows for all tasks (XOR with task_master_id)
        task_master_id: TaskMaster ID to generate workflow for single task (XOR with job_master_id)
    """

    job_master_id: int | str | None = Field(
        default=None,
        description="JobMaster ID to generate workflows for all tasks in the job (supports both int and ULID string)",
        examples=[123, "jm_01K8DXE62NFJNB0SHJZPAWQWVT"],
    )
    task_master_id: int | str | None = Field(
        default=None,
        description="TaskMaster ID to generate workflow for single task (supports both int and ULID string)",
        examples=[456, "tm_01K8DXE601HMZWW0K5HR9FDYCQ"],
    )

    @model_validator(mode="after")
    def validate_xor(self) -> "WorkflowGeneratorRequest":
        """Validate XOR constraint: exactly one of job_master_id or task_master_id must be provided."""
        if (self.job_master_id is None) == (self.task_master_id is None):
            raise ValueError(
                "Exactly one of 'job_master_id' or 'task_master_id' must be provided"
            )
        return self


class WorkflowResult(BaseModel):
    """Result schema for single workflow generation.

    Attributes:
        task_master_id: TaskMaster ID
        task_name: Task name
        workflow_name: Generated workflow name
        yaml_content: Generated YAML content
        status: Status of workflow generation ("success", "failed")
        validation_result: Validation result (if executed)
        error_message: Error message (on failure)
        retry_count: Number of retries during self-repair loop
    """

    task_master_id: str | int = Field(
        ...,
        description="TaskMaster ID (ULID string or int)",
        examples=["tm_01K8K13NC8PRJ3V4R35C1AP2JP", 456],
    )
    task_name: str = Field(
        ...,
        description="Task name",
        examples=["Send email notification"],
    )
    workflow_name: str = Field(
        ...,
        description="Generated workflow name",
        examples=["send_email_notification"],
    )
    yaml_content: str = Field(
        ...,
        description="Generated YAML content",
    )
    status: str = Field(
        ...,
        description='Status of workflow generation: "success" or "failed"',
        examples=["success"],
    )
    validation_result: dict[str, Any] | None = Field(
        default=None,
        description="Validation result (if executed)",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message (on failure)",
    )
    retry_count: int = Field(
        default=0,
        description="Number of retries during self-repair loop",
        examples=[0],
    )


class WorkflowGeneratorResponse(BaseModel):
    """Response schema for GraphAI Workflow Generator API.

    Attributes:
        status: Overall status ("success", "failed", "partial_success")
        workflows: List of workflow generation results
        total_tasks: Total number of tasks processed
        successful_tasks: Number of successfully generated workflows
        failed_tasks: Number of failed workflow generations
        generation_time_ms: Total generation time in milliseconds
        error_message: Error message (on failure)
    """

    status: str = Field(
        ...,
        description='Overall status: "success", "failed", or "partial_success"',
        examples=["success"],
    )
    workflows: list[WorkflowResult] = Field(
        default_factory=list,
        description="List of workflow generation results",
    )
    total_tasks: int = Field(
        default=0,
        description="Total number of tasks processed",
        examples=[3],
    )
    successful_tasks: int = Field(
        default=0,
        description="Number of successfully generated workflows",
        examples=[3],
    )
    failed_tasks: int = Field(
        default=0,
        description="Number of failed workflow generations",
        examples=[0],
    )
    generation_time_ms: float = Field(
        default=0.0,
        description="Total generation time in milliseconds",
        examples=[5432.1],
    )
    error_message: str | None = Field(
        default=None,
        description="Error message (on overall failure)",
    )
