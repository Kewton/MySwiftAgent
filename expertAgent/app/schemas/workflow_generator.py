"""Pydantic schemas for GraphAI Workflow Generator API."""

from typing import Any

from pydantic import BaseModel, Field, model_validator

from app.schemas.prompt_config import PromptConfig


class WorkflowGeneratorRequest(BaseModel):
    """Request schema for GraphAI Workflow Generator API.

    Attributes:
        job_master_id: JobMaster ID to generate workflows for all tasks (XOR with task_master_id)
        task_master_id: TaskMaster ID to generate workflow for single task (XOR with job_master_id)
        prompt_configs: Optional list of prompt configurations for custom versions
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
    prompt_configs: list[PromptConfig] = Field(
        default_factory=list,
        description="Optional list of prompt configurations for custom versions",
        examples=[
            [
                {
                    "agent_type": "workflowGeneratorAgents",
                    "prompt_name": "workflow_generation",
                    "version": "v3.0",
                }
            ]
        ],
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

    Issue #278: Added langfuse_trace_id field for LLM observability.

    Attributes:
        status: Overall status ("success", "failed", "partial_success")
        workflows: List of workflow generation results
        total_tasks: Total number of tasks processed
        successful_tasks: Number of successfully generated workflows
        failed_tasks: Number of failed workflow generations
        generation_time_ms: Total generation time in milliseconds
        error_message: Error message (on failure)
        langfuse_trace_id: Langfuse trace ID for debugging (Issue #278)
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

    # Issue #278: Langfuse tracing
    langfuse_trace_id: str | None = Field(
        default=None,
        description="Langfuse trace ID for LLM observability and debugging",
        examples=["trace-abc123-def456"],
    )


# Issue #333: Schema validation endpoint schemas
class SchemaValidationIssue(BaseModel):
    """Schema validation issue details.

    Attributes:
        node_id: ID of the node with the issue
        issue_type: Type of validation issue
        message: Human-readable error message
        severity: Issue severity (error or warning)
        field_name: Name of the problematic field
        expected_value: Expected value or type
        actual_value: Actual value or type found
        suggestion: Suggestion for fixing the issue
    """

    node_id: str = Field(..., description="ID of the node with the issue")
    issue_type: str = Field(
        ...,
        description="Type of issue: type_mismatch, deprecated_field, yaml_parse_error, etc.",
    )
    message: str = Field(..., description="Human-readable error message")
    severity: str = Field(..., description='Issue severity: "error" or "warning"')
    field_name: str = Field(default="", description="Name of the problematic field")
    expected_value: str = Field(default="", description="Expected value or type")
    actual_value: str = Field(default="", description="Actual value or type found")
    suggestion: str | None = Field(
        default=None, description="Suggestion for fixing the issue"
    )


class SchemaValidationRequest(BaseModel):
    """Request schema for workflow schema validation (Issue #333).

    Attributes:
        yaml_content: YAML content to validate
    """

    yaml_content: str = Field(
        ...,
        description="GraphAI workflow YAML content to validate",
        examples=[
            """version: 0.5
nodes:
  source: {}
  llm_call:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :source.user_input.query
        system_prompt: "You are a helpful assistant"
"""
        ],
    )


class SchemaValidationResponse(BaseModel):
    """Response schema for workflow schema validation (Issue #333).

    Attributes:
        is_valid: Whether the workflow passes schema validation
        issues: List of validation issues found
        validated_nodes: Number of nodes validated
        api_calls_detected: Number of API calls detected
        warning_count: Number of warnings
        error_count: Number of errors
    """

    is_valid: bool = Field(
        ..., description="Whether the workflow passes schema validation (no errors)"
    )
    issues: list[SchemaValidationIssue] = Field(
        default_factory=list, description="List of validation issues found"
    )
    validated_nodes: int = Field(default=0, description="Number of nodes validated")
    api_calls_detected: int = Field(
        default=0, description="Number of fetchAgent API calls detected"
    )
    warning_count: int = Field(default=0, description="Number of warnings")
    error_count: int = Field(default=0, description="Number of errors")
