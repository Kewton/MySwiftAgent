"""Type definitions for Job Generator V2 - 3-Phase Architecture.

Issue #359: New types for the 3-phase unified ID architecture.

This module defines the core types for the refactored architecture:
- UnifiedTaskIdentifier: Single carrier for task_id + task_master_id
- TaskResult: Result of individual task execution
- ParallelExecutionResult: Aggregated parallel execution results
- ErrorType: Classification of errors
- RecoveryStrategy: Recovery action strategies
- PhaseError: Phase-specific error with details
- RecoveryAction: Recovery decision with feedback
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

# Re-export types from types_old for backward compatibility
from .types_old import (
    Capability,
    CompatibilityReport,
    DerivedFieldDefinition,
    EnrichmentReport,
    FeasibilityReport,
    InterfaceDesignInput,
    InterfaceDesignOutput,
    InterfaceSchema,
    InterfaceSchemaDefinition,
    InterfaceSchemaResponse,
    JobBodyParameter,
    JobGenerationRequest,
    JobGenerationResult,
    RecommendedAPI,
    RegistrationInput,
    RegistrationOutput,
    RelaxationSuggestion,
    RetryAttempt,
    RetryState,
    SchemaCountMismatchResult,
    SkipAggregator,
    SkipInfo,
    TaskBreakdownInput,
    TaskBreakdownItem,
    TaskBreakdownOutput,
    TaskBreakdownResponse,
    TaskDefinition,
    TaskIdMapping,
    WorkflowGenInput,
    WorkflowGenOutput,
    WorkflowGenPhaseOutput,
)


class ErrorType(Enum):
    """Error type classification for recovery decisions.

    These types determine how errors should be handled:
    - TRANSIENT: Temporary issue, can retry (e.g., network timeout)
    - VALIDATION: Schema/format error, can retry with feedback
    - API: External API error, may retry with backoff
    - BUSINESS: Business rule violation, requires user intervention
    - FATAL: Unrecoverable error, fail immediately
    """

    TRANSIENT = "transient"
    VALIDATION = "validation"
    API = "api"
    BUSINESS = "business"
    FATAL = "fatal"


class RecoveryStrategy(Enum):
    """Recovery strategies for error handling.

    These strategies are chosen based on error type and retry history:
    - RETRY_CURRENT: Retry the current operation
    - RETRY_WITH_FEEDBACK: Retry with LLM feedback about the error
    - ROLLBACK_TO_ANALYSIS: Go back to JOB_ANALYSIS phase
    - RELAXATION: Ask user to relax requirements
    - FAIL_FAST: Stop immediately
    """

    RETRY_CURRENT = "retry_current"
    RETRY_WITH_FEEDBACK = "retry_with_feedback"
    ROLLBACK_TO_ANALYSIS = "rollback_to_analysis"
    RELAXATION = "relaxation"
    FAIL_FAST = "fail_fast"


@dataclass
class TaskExecutionError:
    """Error details for task execution failures.

    Attributes:
        error_type: Classification of the error
        message: Human-readable error message
        recoverable: Whether the error can be recovered from
        details: Additional error details (optional)
    """

    error_type: ErrorType
    message: str
    recoverable: bool = True
    details: Optional[dict[str, Any]] = None


@dataclass(frozen=True)
class UnifiedTaskIdentifier:
    """Unified task identifier carrying both logical and master IDs.

    This class solves the task_id vs task_master_id confusion by
    carrying both IDs together throughout the workflow.

    Equality and hashing are based on task_id only, allowing
    identifiers to be used as dictionary keys consistently.

    Example:
        # Create identifier during job analysis
        task = UnifiedTaskIdentifier(task_id="task_001")

        # Update with master_id after registration
        registered_task = task.with_master_id("tm_abc123")

        # Use as dict key
        workflows = {task: some_workflow}
        assert workflows[registered_task] == some_workflow  # True

    Attributes:
        task_id: Logical task identifier (e.g., "task_001")
        task_master_id: Database master ID (e.g., "tm_abc123"), None until registered
    """

    task_id: str
    task_master_id: Optional[str] = None

    def __hash__(self) -> int:
        """Hash based on task_id only for consistent dict key behavior."""
        return hash(self.task_id)

    def __eq__(self, other: object) -> bool:
        """Equality based on task_id only."""
        if not isinstance(other, UnifiedTaskIdentifier):
            return NotImplemented
        return self.task_id == other.task_id

    def with_master_id(self, master_id: str) -> "UnifiedTaskIdentifier":
        """Create new identifier with master_id set.

        Returns a new instance to preserve immutability.

        Args:
            master_id: The task_master_id to set

        Returns:
            New UnifiedTaskIdentifier with master_id set
        """
        return UnifiedTaskIdentifier(
            task_id=self.task_id,
            task_master_id=master_id
        )


@dataclass
class TaskResult:
    """Result of individual task execution.

    Used to track the outcome of each task in parallel execution.

    Attributes:
        task_id: ID of the task
        success: Whether execution succeeded
        workflow: Generated workflow (if successful)
        error: Error details (if failed)
        retry_count: Number of retries attempted
        execution_time_ms: Execution time in milliseconds
    """

    task_id: str
    success: bool
    workflow: Optional[dict[str, Any]] = None
    error: Optional[TaskExecutionError] = None
    retry_count: int = 0
    execution_time_ms: float = 0.0


@dataclass
class ParallelExecutionResult:
    """Aggregated result from parallel task execution.

    Provides convenience properties to check execution status
    and generate error summaries.

    Attributes:
        successful_tasks: List of tasks that succeeded
        failed_tasks: List of tasks that failed
        total_execution_time_ms: Total execution time
    """

    successful_tasks: list[TaskResult] = field(default_factory=list)
    failed_tasks: list[TaskResult] = field(default_factory=list)
    total_execution_time_ms: float = 0.0

    @property
    def all_succeeded(self) -> bool:
        """Check if all tasks succeeded."""
        return len(self.failed_tasks) == 0 and len(self.successful_tasks) > 0

    @property
    def partial_success(self) -> bool:
        """Check if some tasks succeeded and some failed."""
        return len(self.successful_tasks) > 0 and len(self.failed_tasks) > 0

    @property
    def all_failed(self) -> bool:
        """Check if all tasks failed."""
        return len(self.successful_tasks) == 0 and len(self.failed_tasks) > 0

    def get_error_summary(self) -> str:
        """Generate error summary for failed tasks.

        Returns:
            Formatted string with error details
        """
        if not self.failed_tasks:
            return ""

        lines = [f"Failed tasks ({len(self.failed_tasks)}):"]
        for task in self.failed_tasks:
            if task.error:
                lines.append(f"- {task.task_id}: {task.error.message}")
            else:
                lines.append(f"- {task.task_id}: Unknown error")

        return "\n".join(lines)


@dataclass
class PhaseError:
    """Phase-specific error with details.

    Used to capture errors during phase execution with
    enough context for recovery decisions.

    Attributes:
        phase: Phase where error occurred
        error_type: Classification of the error
        message: Human-readable error message
        details: Additional error details
        recoverable: Whether error can be recovered
        retry_count: Current retry count
        max_retries: Maximum allowed retries
    """

    phase: str
    error_type: ErrorType
    message: str
    details: Optional[dict[str, Any]] = None
    recoverable: bool = True
    retry_count: int = 0
    max_retries: int = 3


@dataclass
class RecoveryAction:
    """Recovery action to take after an error.

    Contains the strategy and any context needed
    for the recovery attempt.

    Attributes:
        strategy: Recovery strategy to use
        feedback: Feedback message for LLM (if retrying)
        retry_count: Current retry count
        max_retries: Maximum retries for this phase
        reason: Reason for this recovery action
        error_summary: Summary of errors encountered
    """

    strategy: RecoveryStrategy
    feedback: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 0
    reason: Optional[str] = None
    error_summary: Optional[str] = None


# Phase enum for the new 3-phase architecture
class Phase(Enum):
    """Job generation phases in 3-phase architecture.

    The workflow proceeds through these phases in order:
    1. JOB_ANALYSIS - Combined task breakdown and interface design
    2. REGISTRATION - Register masters in jobqueue
    3. WORKFLOW_GEN - Generate TaskFlow JSON workflows (parallel)
    """

    JOB_ANALYSIS = "job_analysis"
    REGISTRATION = "registration"
    WORKFLOW_GEN = "workflow_gen"


class PhaseStatus(Enum):
    """Status of a phase execution.

    - SUCCESS: Phase completed successfully
    - FAILED: Phase failed (cannot recover)
    - NEEDS_RETRY: Phase needs to be retried (recoverable error)
    - NEEDS_RELAXATION: Requirements need to be relaxed (business constraint)
    """

    SUCCESS = "success"
    FAILED = "failed"
    NEEDS_RETRY = "needs_retry"
    NEEDS_RELAXATION = "needs_relaxation"


# Export all types
__all__ = [
    # New V3 types
    "ErrorType",
    "RecoveryStrategy",
    "TaskExecutionError",
    "UnifiedTaskIdentifier",
    "TaskResult",
    "ParallelExecutionResult",
    "PhaseError",
    "PhaseStatus",
    "RecoveryAction",
    "Phase",
    # Re-exported from types_old for backward compatibility
    "Capability",
    "CompatibilityReport",
    "DerivedFieldDefinition",
    "EnrichmentReport",
    "FeasibilityReport",
    "InterfaceDesignInput",
    "InterfaceDesignOutput",
    "InterfaceSchema",
    "InterfaceSchemaDefinition",
    "InterfaceSchemaResponse",
    "JobBodyParameter",
    "JobGenerationRequest",
    "JobGenerationResult",
    "RecommendedAPI",
    "RegistrationInput",
    "RegistrationOutput",
    "RelaxationSuggestion",
    "RetryAttempt",
    "RetryState",
    "SchemaCountMismatchResult",
    "SkipAggregator",
    "SkipInfo",
    "TaskBreakdownInput",
    "TaskBreakdownItem",
    "TaskBreakdownOutput",
    "TaskBreakdownResponse",
    "TaskDefinition",
    "TaskIdMapping",
    "WorkflowGenInput",
    "WorkflowGenOutput",
    "WorkflowGenPhaseOutput",
]
