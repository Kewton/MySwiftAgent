"""Type definitions for WorkflowGeneratorClient.

Issue #361: Data models for mySwiftAgentCore workflow generation API.

This module defines:
- Request types: TaskRequest, BatchWorkflowGenerationRequest
- Response types: WorkflowResult, BatchWorkflowGenerationResponse
- Status enums: BatchStatus, WorkflowStatus, RecoverySuggestion
- Options: GenerationOptions, TraceContext
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class BatchStatus(str, Enum):
    """Batch operation status.

    Design decision: 3-value status for clear partial success handling.
    - SUCCESS: All tasks completed successfully
    - PARTIAL_SUCCESS: Some tasks succeeded, some failed
    - FAILED: All tasks failed

    Example:
        if response.status == BatchStatus.PARTIAL_SUCCESS:
            # Handle partial success - some workflows generated
            successful = [w for w in workflows if w.status == WorkflowStatus.SUCCESS]
    """

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class WorkflowStatus(str, Enum):
    """Individual workflow generation status.

    Values:
        SUCCESS: Workflow generated successfully
        FAILED: Workflow generation failed
    """

    SUCCESS = "success"
    FAILED = "failed"


class RecoverySuggestion(str, Enum):
    """Recovery suggestion for failed operations.

    Used by mySwiftAgentCore to suggest recovery actions
    when workflow generation fails.

    Values:
        ROLLBACK_TO_ANALYSIS: Go back to job analysis phase
        RELAXATION: Relax requirements and retry
    """

    ROLLBACK_TO_ANALYSIS = "ROLLBACK_TO_ANALYSIS"
    RELAXATION = "RELAXATION"


@dataclass
class TaskInterface:
    """Task input/output interface definition.

    Attributes:
        input: Input schema (field name -> type)
        output: Output schema (field name -> type)
    """

    input: dict[str, str]
    output: dict[str, str]


@dataclass
class TaskRequest:
    """Request for single task workflow generation.

    Attributes:
        task_id: Unique task identifier
        name: Human-readable task name
        description: Detailed task description
        interface: Input/output interface definition
    """

    task_id: str
    name: str
    description: str
    interface: TaskInterface


@dataclass
class TraceContext:
    """Langfuse trace context for distributed tracing.

    Used to propagate trace context to mySwiftAgentCore
    for correlated observability.

    Attributes:
        trace_id: Langfuse trace ID
        parent_span_id: Parent span ID for nesting
    """

    trace_id: str
    parent_span_id: str | None = None


@dataclass
class GenerationOptions:
    """Workflow generation options.

    Attributes:
        max_concurrency: Maximum parallel task generations
        timeout_per_task_ms: Per-task timeout in milliseconds
        validate_before_register: Validate workflows before registration
    """

    max_concurrency: int = 10
    timeout_per_task_ms: int = 180000  # 3 minutes
    validate_before_register: bool = True


@dataclass
class WorkflowResult:
    """Result for single workflow generation.

    Attributes:
        workflow_name: Generated workflow name
        status: Generation status
        error: Error message if failed
    """

    workflow_name: str
    status: WorkflowStatus
    error: str | None = None


@dataclass
class FailedTask:
    """Information about a failed task.

    Attributes:
        task_id: ID of the failed task
        error_type: Classification of the error
        message: Human-readable error message
    """

    task_id: str
    error_type: str
    message: str


@dataclass
class BatchWorkflowGenerationRequest:
    """Request for batch workflow generation.

    Sent to mySwiftAgentCore's /api/v1/generator/workflow/batch endpoint.

    Attributes:
        tasks: List of tasks to generate workflows for
        capabilities: Available capabilities (APIs, agents)
        project_id: Target project ID
        options: Generation options
        trace_context: Langfuse trace context
    """

    tasks: list[TaskRequest]
    capabilities: list[dict[str, Any]]
    project_id: str
    options: GenerationOptions | None = None
    trace_context: TraceContext | None = None


@dataclass
class BatchWorkflowGenerationResponse:
    """Response from batch workflow generation.

    Contains results for all tasks, with status indicating
    overall success/partial/failure.

    Attributes:
        status: Overall batch status (success/partial_success/failed)
        success: Boolean for backward compatibility
        workflows: Generated workflows keyed by task_id
        failed_tasks: List of failed tasks
        recovery_suggestion: Suggested recovery action
        total_tasks: Total number of tasks
        succeeded_tasks: Number of successful tasks
        failed_task_count: Number of failed tasks
    """

    status: BatchStatus
    success: bool
    workflows: dict[str, WorkflowResult]
    failed_tasks: list[FailedTask] | None = None
    recovery_suggestion: RecoverySuggestion | None = None
    total_tasks: int = 0
    succeeded_tasks: int = 0
    failed_task_count: int = 0

    @classmethod
    def from_results(
        cls,
        workflows: dict[str, WorkflowResult],
        failed_tasks: list[FailedTask] | None = None,
        recovery_suggestion: RecoverySuggestion | None = None,
    ) -> "BatchWorkflowGenerationResponse":
        """Create response from results with automatic status calculation.

        This factory method calculates the appropriate BatchStatus
        based on success/failure counts.

        Args:
            workflows: Generated workflows (may include failures)
            failed_tasks: List of failed tasks
            recovery_suggestion: Recovery suggestion if applicable

        Returns:
            BatchWorkflowGenerationResponse with calculated status

        Example:
            response = BatchWorkflowGenerationResponse.from_results(
                workflows={"task_001": WorkflowResult(...)},
                failed_tasks=[FailedTask(task_id="task_002", ...)]
            )
            assert response.status == BatchStatus.PARTIAL_SUCCESS
        """
        succeeded = sum(
            1 for w in workflows.values() if w.status == WorkflowStatus.SUCCESS
        )
        failed = len(failed_tasks) if failed_tasks else 0
        total = len(workflows) + failed

        # Status determination logic
        if failed == 0 and succeeded > 0:
            status = BatchStatus.SUCCESS
        elif succeeded > 0 and failed > 0:
            status = BatchStatus.PARTIAL_SUCCESS
        else:
            status = BatchStatus.FAILED

        return cls(
            status=status,
            success=(status != BatchStatus.FAILED),
            workflows=workflows,
            failed_tasks=failed_tasks,
            recovery_suggestion=recovery_suggestion,
            total_tasks=total,
            succeeded_tasks=succeeded,
            failed_task_count=failed,
        )
