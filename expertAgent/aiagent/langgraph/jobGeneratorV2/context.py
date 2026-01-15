"""Execution context for Job Generator V2.

This module provides context classes that carry dependencies and state
through the workflow execution:

- ExecutionContext: Main context with job info and retry management
- LLMContext: Configuration for LLM calls
- StorageContext: Access to storage/persistence
- IntegrationContext: External service clients
- ObservabilityContext: Tracing and monitoring
- ContextBuilder: Fluent builder for context creation

Issue #342: ExecutionContext manages per-phase RetryState to fix the
retry_count bug where retry_count was incorrectly reset.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from .types_old import Phase, RetryState

logger = logging.getLogger(__name__)


@dataclass
class LLMContext:
    """Configuration for LLM invocations.

    Attributes:
        model_name: Name of the model to use
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response
        model_env_var: Environment variable for model override
    """

    model_name: str = "claude-haiku-4-5"
    temperature: float = 0.7
    max_tokens: int = 4096
    model_env_var: str | None = None


@dataclass
class StorageContext:
    """Context for storage/persistence operations.

    Attributes:
        jobqueue_client: Client for jobqueue API
        task_id_mapping: TaskIdMapping for task_id <-> task_master_id lookup
            (Issue #342 Bug #1: Required for correct interface lookup in workflow gen)
    """

    jobqueue_client: Any = None
    task_id_mapping: Any = None  # TaskIdMapping, using Any to avoid circular import


@dataclass
class IntegrationContext:
    """Context for external integrations.

    Attributes:
        graphai_client: Client for GraphAI server
        myvault_client: Client for MyVault secret management
        jobqueue_base_url: Base URL for JobQueue API (for TaskMaster validation)
    """

    graphai_client: Any = None
    myvault_client: Any = None
    jobqueue_base_url: str = ""


@dataclass
class ObservabilityContext:
    """Context for observability features.

    Attributes:
        tracer: Langfuse or other tracing client
        metrics_client: Metrics collection client
    """

    tracer: Any = None
    metrics_client: Any = None


@dataclass
class RollbackRecord:
    """Record of a rollback event.

    Attributes:
        from_phase: Phase that triggered rollback
        to_phase: Target phase of rollback
        reason: Why the rollback happened
    """

    from_phase: Phase
    to_phase: Phase
    reason: str = ""


@dataclass
class ExecutionContext:
    """Main execution context for job generation workflow.

    This context carries all state and dependencies through the workflow.
    Key feature: Each phase has its own RetryState to prevent the
    retry_count reset bug.

    Attributes:
        job_id: Unique job identifier
        user_requirement: The user's requirement string
        max_total_retries: Maximum total retries across all phases
        max_phase_retries: Maximum retries per phase
        llm: LLM configuration
        storage: Storage access
        integration: External service clients
        observability: Tracing and monitoring
    """

    job_id: str
    user_requirement: str
    max_total_retries: int = 5
    max_phase_retries: int = 3

    # Sub-contexts (initialized with defaults if not provided)
    llm: LLMContext = field(default_factory=LLMContext)
    storage: StorageContext = field(default_factory=StorageContext)
    integration: IntegrationContext = field(default_factory=IntegrationContext)
    observability: ObservabilityContext = field(default_factory=ObservabilityContext)

    # Per-phase retry states (initialized in __post_init__)
    _phase_retry_states: dict[Phase, RetryState] = field(
        default_factory=dict, repr=False
    )
    _rollback_history: list[RollbackRecord] = field(default_factory=list, repr=False)

    def __post_init__(self):
        """Initialize per-phase retry states."""
        # Create retry state for each phase
        for phase in Phase:
            if phase not in self._phase_retry_states:
                self._phase_retry_states[phase] = RetryState(
                    count=0,
                    max_count=self.max_phase_retries,
                )

    def get_phase_retry_state(self, phase: Phase) -> RetryState:
        """Get the retry state for a specific phase.

        Args:
            phase: The phase to get retry state for

        Returns:
            RetryState for the phase
        """
        return self._phase_retry_states[phase]

    def can_retry(self, phase: Phase | None = None) -> bool:
        """Check if retries are available.

        Args:
            phase: Optional specific phase to check. If None, checks any phase.

        Returns:
            True if retries are available, False otherwise
        """
        # Check total limit first
        if self.total_retry_count() >= self.max_total_retries:
            return False

        # If specific phase provided, check that phase
        if phase is not None:
            return self._phase_retry_states[phase].can_retry()

        # Check if any phase can retry
        return any(state.can_retry() for state in self._phase_retry_states.values())

    def can_retry_any(self) -> bool:
        """Check if any more retries are available across all phases.

        Returns:
            True if total retries haven't been exhausted
        """
        return self.total_retry_count() < self.max_total_retries

    def record_retry(self, phase: Phase, reason: str, error: Exception | None = None):
        """Record a retry attempt for a phase.

        Args:
            phase: The phase being retried
            reason: Reason for the retry
            error: Optional exception that caused the retry
        """
        logger.info(
            "Recording retry for phase %s: %s (retry #%d)",
            phase.value,
            reason,
            self._phase_retry_states[phase].count + 1,
        )
        self._phase_retry_states[phase].record(reason, error)

    def total_retry_count(self) -> int:
        """Get the total retry count across all phases.

        Returns:
            Total number of retries
        """
        return sum(state.count for state in self._phase_retry_states.values())

    def get_rollback_count(self) -> int:
        """Get the total number of rollbacks.

        Returns:
            Number of rollbacks that have occurred
        """
        return len(self._rollback_history)

    def record_rollback(
        self,
        from_phase: Phase,
        to_phase: Phase,
        reason: str = "",
    ):
        """Record a rollback event.

        Args:
            from_phase: Phase that triggered rollback
            to_phase: Target phase of rollback
            reason: Why the rollback happened
        """
        logger.info(
            "Recording rollback from %s to %s: %s",
            from_phase.value,
            to_phase.value,
            reason,
        )
        self._rollback_history.append(
            RollbackRecord(
                from_phase=from_phase,
                to_phase=to_phase,
                reason=reason,
            )
        )


class ContextBuilder:
    """Fluent builder for creating ExecutionContext.

    Example:
        context = (
            ContextBuilder()
            .with_job_id("job-123")
            .with_user_requirement("Fetch emails")
            .with_llm_context(LLMContext(model_name="claude-haiku-4-5"))
            .build()
        )
    """

    def __init__(self):
        self._job_id: str | None = None
        self._user_requirement: str | None = None
        self._max_total_retries: int = 5
        self._max_phase_retries: int = 3
        self._llm_context: LLMContext | None = None
        self._storage_context: StorageContext | None = None
        self._integration_context: IntegrationContext | None = None
        self._observability_context: ObservabilityContext | None = None

    def with_job_id(self, job_id: str) -> "ContextBuilder":
        """Set the job ID.

        Args:
            job_id: Unique job identifier

        Returns:
            Self for chaining
        """
        self._job_id = job_id
        return self

    def with_user_requirement(self, requirement: str) -> "ContextBuilder":
        """Set the user requirement.

        Args:
            requirement: User's requirement string

        Returns:
            Self for chaining
        """
        self._user_requirement = requirement
        return self

    def with_max_retries(
        self,
        total: int = 5,
        per_phase: int = 3,
    ) -> "ContextBuilder":
        """Set retry limits.

        Args:
            total: Maximum total retries across all phases
            per_phase: Maximum retries per phase

        Returns:
            Self for chaining
        """
        self._max_total_retries = total
        self._max_phase_retries = per_phase
        return self

    def with_llm_context(self, llm: LLMContext) -> "ContextBuilder":
        """Set LLM context.

        Args:
            llm: LLM configuration

        Returns:
            Self for chaining
        """
        self._llm_context = llm
        return self

    def with_storage_context(self, storage: StorageContext) -> "ContextBuilder":
        """Set storage context.

        Args:
            storage: Storage configuration

        Returns:
            Self for chaining
        """
        self._storage_context = storage
        return self

    def with_integration_context(
        self, integration: IntegrationContext
    ) -> "ContextBuilder":
        """Set integration context.

        Args:
            integration: Integration configuration

        Returns:
            Self for chaining
        """
        self._integration_context = integration
        return self

    def with_observability_context(
        self, observability: ObservabilityContext
    ) -> "ContextBuilder":
        """Set observability context.

        Args:
            observability: Observability configuration

        Returns:
            Self for chaining
        """
        self._observability_context = observability
        return self

    def build(self) -> ExecutionContext:
        """Build the ExecutionContext.

        Returns:
            Configured ExecutionContext

        Raises:
            ValueError: If required fields are missing
        """
        if not self._job_id:
            raise ValueError("job_id is required")
        if not self._user_requirement:
            raise ValueError("user_requirement is required")

        return ExecutionContext(
            job_id=self._job_id,
            user_requirement=self._user_requirement,
            max_total_retries=self._max_total_retries,
            max_phase_retries=self._max_phase_retries,
            llm=self._llm_context or LLMContext(),
            storage=self._storage_context or StorageContext(),
            integration=self._integration_context or IntegrationContext(),
            observability=self._observability_context or ObservabilityContext(),
        )
