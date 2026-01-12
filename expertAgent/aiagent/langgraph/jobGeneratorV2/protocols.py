"""Protocol definitions for Job Generator V2.

This module defines protocols and supporting types for workflow components:
- WorkflowProtocol: Interface for all workflows
- RetryPolicy: Configuration for retry behavior
- ErrorType: Classification of errors
- WorkflowError: Custom exception for workflow errors
- PhaseExecution: Tracking of phase execution
- ProgressReporter: Interface for progress reporting

Issue #342: These protocols enable proper dependency injection and testing.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Protocol, TypeVar, runtime_checkable

from .types import Phase, PhaseStatus


class ErrorType(Enum):
    """Classification of errors for recovery strategy selection.

    - TRANSIENT: Temporary errors that may resolve on retry (e.g., network timeout)
    - VALIDATION: Input/output validation errors (e.g., schema mismatch)
    - COMPATIBILITY: Inter-phase compatibility errors (e.g., interface mismatch)
    - BUSINESS: Business rule violations (e.g., infeasible requirement)
    - FATAL: Unrecoverable errors (e.g., database connection failure)
    - API: External API call errors (e.g., JobQueue API errors, typically retryable)
    - INCOMPLETE_WORKFLOW: WORKFLOW_GEN phase incomplete (Issue #353)
    """

    TRANSIENT = "transient"
    VALIDATION = "validation"
    COMPATIBILITY = "compatibility"
    BUSINESS = "business"
    FATAL = "fatal"
    API = "api"
    INCOMPLETE_WORKFLOW = "incomplete_workflow"  # Issue #353


class WorkflowError(Exception):
    """Custom exception for workflow errors.

    This exception carries additional context about the error type and
    the phase where it occurred, enabling intelligent error recovery.

    Attributes:
        message: Human-readable error description
        error_type: Classification of the error
        phase: Optional phase where the error occurred
        details: Optional additional error details
    """

    def __init__(
        self,
        message: str,
        error_type: ErrorType,
        phase: Phase | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.phase = phase
        self.details = details or {}

    def __str__(self) -> str:
        return super().__str__()


@dataclass
class RetryPolicy:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retries allowed (default: 3)
        backoff_factor: Multiplier for exponential backoff (default: 1.0)
        retry_on: List of error types to retry on
    """

    max_retries: int = 3
    backoff_factor: float = 1.0
    retry_on: list[ErrorType] = field(
        default_factory=lambda: [ErrorType.TRANSIENT, ErrorType.VALIDATION]
    )


@dataclass
class PhaseExecution:
    """Record of a phase execution.

    Attributes:
        phase: The phase that was executed
        status: Resulting status
        started_at: When execution started
        duration: How long execution took
        retry_count: Number of retries attempted
        error: Error message if failed
    """

    phase: Phase
    status: PhaseStatus
    started_at: datetime
    duration: timedelta
    retry_count: int = 0
    error: str | None = None


# Type variables for generic protocols
WorkflowInput = TypeVar("WorkflowInput")
WorkflowOutput = TypeVar("WorkflowOutput")


@runtime_checkable
class WorkflowProtocol(Protocol):
    """Protocol for workflow implementations.

    All workflows must implement this protocol to be used by the orchestrator.
    The execute method is async to support LLM calls and other I/O operations.

    Example:
        class TaskBreakdownWorkflow:
            async def execute(
                self,
                input: TaskBreakdownInput,
                context: ExecutionContext,
            ) -> TaskBreakdownOutput:
                # Implementation
                ...

            def get_retry_policy(self) -> RetryPolicy:
                return RetryPolicy(max_retries=3)
    """

    async def execute(
        self,
        input: Any,
        context: Any,
    ) -> Any:
        """Execute the workflow.

        Args:
            input: Workflow-specific input data
            context: Execution context with dependencies

        Returns:
            Workflow-specific output data

        Raises:
            WorkflowError: If the workflow fails
        """
        ...

    def get_retry_policy(self) -> RetryPolicy:
        """Get the retry policy for this workflow.

        Returns:
            RetryPolicy instance
        """
        ...


@runtime_checkable
class ProgressReporter(Protocol):
    """Protocol for progress reporting.

    Implementations can report progress to various destinations:
    - Console/logging
    - WebSocket
    - Database
    - External monitoring systems
    """

    def report(
        self,
        phase: Phase,
        context: Any,
    ) -> None:
        """Report progress on a phase.

        Args:
            phase: The phase being reported
            context: Current execution context
        """
        ...

    def report_recovery(
        self,
        phase: Phase,
        decision: Any,
        context: Any,
    ) -> None:
        """Report an error recovery decision.

        Args:
            phase: The phase where recovery is happening
            decision: The recovery decision made
            context: Current execution context
        """
        ...


# Convenience type alias for workflow implementations
WorkflowDict = dict[Phase, WorkflowProtocol]
