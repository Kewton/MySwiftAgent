"""Error Recovery Manager for 3-Phase Architecture.

Issue #359: Phase-specific error contracts and recovery strategies.

This module implements:
- Phase-specific error contracts (JOB_ANALYSIS, REGISTRATION, WORKFLOW_GEN)
- ErrorRecoveryManager for centralized recovery decisions
- Strategy escalation when retry limits are exceeded

Key design principles:
1. Each phase has its own error contract defining recovery behavior
2. Total and per-phase retry limits prevent infinite loops
3. Escalation path: RETRY -> ROLLBACK -> RELAXATION/FAIL_FAST
"""

import logging
from dataclasses import dataclass
from typing import Optional, Protocol

from .types import (
    ErrorType,
    PhaseError,
    RecoveryAction,
    RecoveryStrategy,
)


class ErrorContractProtocol(Protocol):
    """Protocol for phase-specific error contracts."""

    @staticmethod
    def get_recovery_strategy(error: PhaseError) -> RecoveryStrategy:
        """Get recovery strategy for error."""
        ...

    @staticmethod
    def get_max_retries(error: PhaseError) -> int:
        """Get max retries for error type."""
        ...

    @staticmethod
    def create_feedback(error: PhaseError) -> Optional[str]:
        """Create feedback for retry."""
        ...

logger = logging.getLogger(__name__)


@dataclass
class JobAnalysisErrorContract:
    """Error contract for JOB_ANALYSIS phase.

    This phase combines task breakdown and interface design.
    Most errors are retriable with feedback since they involve LLM output.
    """

    @staticmethod
    def get_recovery_strategy(error: PhaseError) -> RecoveryStrategy:
        """Determine recovery strategy for JOB_ANALYSIS errors."""
        strategy_map = {
            ErrorType.VALIDATION: RecoveryStrategy.RETRY_WITH_FEEDBACK,
            ErrorType.API: RecoveryStrategy.RETRY_CURRENT,
            ErrorType.TRANSIENT: RecoveryStrategy.RETRY_CURRENT,
            ErrorType.BUSINESS: RecoveryStrategy.RELAXATION,
            ErrorType.FATAL: RecoveryStrategy.FAIL_FAST,
        }
        return strategy_map.get(error.error_type, RecoveryStrategy.FAIL_FAST)

    @staticmethod
    def get_max_retries(error: PhaseError) -> int:
        """Get maximum retries for error type in JOB_ANALYSIS phase."""
        retry_map = {
            ErrorType.VALIDATION: 3,
            ErrorType.API: 3,
            ErrorType.TRANSIENT: 3,
            ErrorType.BUSINESS: 0,
            ErrorType.FATAL: 0,
        }
        return retry_map.get(error.error_type, 0)

    @staticmethod
    def create_feedback(error: PhaseError) -> Optional[str]:
        """Create LLM feedback for retry attempt."""
        if error.error_type != ErrorType.VALIDATION:
            return None

        feedback_lines = [
            "## Previous Attempt Failed - Validation Error",
            "",
            f"**Error:** {error.message}",
        ]

        if error.details:
            feedback_lines.append(f"**Details:** {error.details}")

        feedback_lines.extend([
            "",
            "### Please fix the following:",
            "- Ensure JSON structure is valid",
            "- Include all required fields",
            "- Verify task dependencies have no cycles",
            "- Check schema definitions are valid JSON Schema",
        ])

        return "\n".join(feedback_lines)


@dataclass
class RegistrationErrorContract:
    """Error contract for REGISTRATION phase.

    This phase registers TaskMasters and JobMasters.
    Validation errors require rollback to JOB_ANALYSIS.
    Transient errors can be retried.
    """

    @staticmethod
    def get_recovery_strategy(error: PhaseError) -> RecoveryStrategy:
        """Determine recovery strategy for REGISTRATION errors."""
        strategy_map = {
            ErrorType.VALIDATION: RecoveryStrategy.ROLLBACK_TO_ANALYSIS,
            ErrorType.API: RecoveryStrategy.RETRY_CURRENT,
            ErrorType.TRANSIENT: RecoveryStrategy.RETRY_CURRENT,
            ErrorType.BUSINESS: RecoveryStrategy.RELAXATION,
            ErrorType.FATAL: RecoveryStrategy.FAIL_FAST,
        }
        return strategy_map.get(error.error_type, RecoveryStrategy.FAIL_FAST)

    @staticmethod
    def get_max_retries(error: PhaseError) -> int:
        """Get maximum retries for error type in REGISTRATION phase."""
        retry_map = {
            ErrorType.VALIDATION: 0,  # No retry, rollback instead
            ErrorType.API: 3,
            ErrorType.TRANSIENT: 3,
            ErrorType.BUSINESS: 0,
            ErrorType.FATAL: 0,
        }
        return retry_map.get(error.error_type, 0)

    @staticmethod
    def should_rollback(error: PhaseError) -> bool:
        """Check if error requires rollback to JOB_ANALYSIS."""
        return error.error_type == ErrorType.VALIDATION

    @staticmethod
    def create_feedback(error: PhaseError) -> Optional[str]:
        """Create feedback for registration errors."""
        if error.error_type != ErrorType.VALIDATION:
            return None

        return f"""## Registration Failed - Rollback Required

**Error:** {error.message}

The task/interface definitions from JOB_ANALYSIS are incompatible
with registration requirements. Please regenerate with:
- Valid body_template references
- Compatible interface schemas
- Proper task dependencies
"""


@dataclass
class WorkflowGenErrorContract:
    """Error contract for WORKFLOW_GEN phase.

    This phase generates TaskFlow JSON for each task in parallel.
    Individual task failures are isolated and can be retried.
    Total failure triggers rollback to JOB_ANALYSIS.
    """

    @staticmethod
    def get_recovery_strategy(error: PhaseError) -> RecoveryStrategy:
        """Determine recovery strategy for WORKFLOW_GEN errors.

        Issue #359: FATAL errors should always FAIL_FAST, not rollback.
        FATAL errors are unrecoverable by definition, and attempting rollback
        could lead to infinite loops or inconsistent state.
        """
        strategy_map = {
            ErrorType.VALIDATION: RecoveryStrategy.RETRY_WITH_FEEDBACK,
            ErrorType.API: RecoveryStrategy.RETRY_CURRENT,
            ErrorType.TRANSIENT: RecoveryStrategy.RETRY_CURRENT,
            ErrorType.BUSINESS: RecoveryStrategy.RELAXATION,
            ErrorType.FATAL: RecoveryStrategy.FAIL_FAST,  # Issue #359: FATAL must fail fast
        }
        return strategy_map.get(error.error_type, RecoveryStrategy.FAIL_FAST)

    @staticmethod
    def get_max_retries(error: PhaseError) -> int:
        """Get maximum retries for error type in WORKFLOW_GEN phase."""
        retry_map = {
            ErrorType.VALIDATION: 3,
            ErrorType.API: 3,
            ErrorType.TRANSIENT: 2,  # Lower for transient due to timeouts
            ErrorType.BUSINESS: 0,
            ErrorType.FATAL: 0,
        }
        return retry_map.get(error.error_type, 0)

    @staticmethod
    def is_task_isolated_error(error: PhaseError) -> bool:
        """Check if error affects only the specific task."""
        isolated_types = {ErrorType.VALIDATION, ErrorType.API, ErrorType.TRANSIENT}
        return error.error_type in isolated_types

    @staticmethod
    def create_feedback(error: PhaseError) -> Optional[str]:
        """Create LLM feedback for workflow generation retry."""
        if error.error_type != ErrorType.VALIDATION:
            return None

        return f"""## Workflow Generation Failed - Validation Error

**Error:** {error.message}

### Please fix the following:
- Ensure TaskFlow JSON structure is valid
- Check step names are unique
- Verify source paths reference existing outputs
- Validate agent names match available agents
"""


class ErrorRecoveryManager:
    """Centralized error recovery manager.

    Manages recovery decisions across all phases with:
    - Per-phase retry tracking
    - Total retry limit
    - Strategy escalation
    - Error history

    Example:
        manager = ErrorRecoveryManager()
        action = manager.handle_error(error)
        if action.strategy == RecoveryStrategy.RETRY_WITH_FEEDBACK:
            # Retry with the provided feedback
            pass
    """

    def __init__(self, max_total_retries: int = 5):
        """Initialize the error recovery manager.

        Args:
            max_total_retries: Maximum retries across all phases
        """
        self.max_total_retries = max_total_retries
        self.total_retry_count = 0
        self.phase_retry_counts: dict[str, int] = {}
        self.error_history: list[PhaseError] = []

        # Phase-specific error contracts (typed as Protocol for static methods)
        self._contracts: dict[str, type[ErrorContractProtocol]] = {
            "JOB_ANALYSIS": JobAnalysisErrorContract,
            "REGISTRATION": RegistrationErrorContract,
            "WORKFLOW_GEN": WorkflowGenErrorContract,
        }

    def handle_error(self, error: PhaseError) -> RecoveryAction:
        """Handle an error and return recovery action.

        Args:
            error: The phase error to handle

        Returns:
            RecoveryAction with strategy and context
        """
        # Track error in history
        self.error_history.append(error)

        logger.info(
            "Handling error in %s phase: %s (%s)",
            error.phase,
            error.message,
            error.error_type.value
        )

        # Check total retry limit first
        if self.total_retry_count >= self.max_total_retries:
            logger.warning(
                "Total retry limit reached (%d/%d)",
                self.total_retry_count,
                self.max_total_retries
            )
            return RecoveryAction(
                strategy=RecoveryStrategy.FAIL_FAST,
                reason="Total retry limit exceeded",
                error_summary=self._generate_error_summary()
            )

        # Get phase-specific contract
        contract_class = self._contracts.get(error.phase)
        if contract_class is None:
            logger.warning("Unknown phase: %s", error.phase)
            return RecoveryAction(
                strategy=RecoveryStrategy.FAIL_FAST,
                reason=f"Unknown phase: {error.phase}"
            )

        # Get strategy from contract
        strategy = contract_class.get_recovery_strategy(error)
        max_retries = contract_class.get_max_retries(error)

        # Check phase-specific retry limit
        phase_retries = self.phase_retry_counts.get(error.phase, 0)

        # Only escalate retry strategies when their limit is exceeded
        # Non-retry strategies (ROLLBACK, RELAXATION, FAIL_FAST) should not be escalated
        # when max_retries is 0 - they are the intended action
        is_retry_strategy = strategy in (
            RecoveryStrategy.RETRY_CURRENT,
            RecoveryStrategy.RETRY_WITH_FEEDBACK
        )

        if is_retry_strategy and phase_retries >= max_retries and max_retries > 0:
            logger.warning(
                "Phase %s retry limit reached (%d/%d), escalating",
                error.phase,
                phase_retries,
                max_retries
            )
            strategy = self._escalate_strategy(strategy)

        # Update retry counts for retry strategies
        if strategy in (RecoveryStrategy.RETRY_CURRENT, RecoveryStrategy.RETRY_WITH_FEEDBACK):
            self.phase_retry_counts[error.phase] = phase_retries + 1
            self.total_retry_count += 1

        # Generate feedback if applicable
        feedback = None
        if strategy == RecoveryStrategy.RETRY_WITH_FEEDBACK:
            feedback = contract_class.create_feedback(error)

        return RecoveryAction(
            strategy=strategy,
            feedback=feedback,
            retry_count=phase_retries + 1,
            max_retries=max_retries
        )

    def _escalate_strategy(self, current: RecoveryStrategy) -> RecoveryStrategy:
        """Escalate strategy when retry limit is exceeded.

        Args:
            current: Current strategy

        Returns:
            Escalated strategy
        """
        escalation_map = {
            RecoveryStrategy.RETRY_CURRENT: RecoveryStrategy.ROLLBACK_TO_ANALYSIS,
            RecoveryStrategy.RETRY_WITH_FEEDBACK: RecoveryStrategy.ROLLBACK_TO_ANALYSIS,
            RecoveryStrategy.ROLLBACK_TO_ANALYSIS: RecoveryStrategy.FAIL_FAST,
            RecoveryStrategy.RELAXATION: RecoveryStrategy.FAIL_FAST,
        }
        return escalation_map.get(current, RecoveryStrategy.FAIL_FAST)

    def _generate_error_summary(self) -> str:
        """Generate summary of all errors in history.

        Returns:
            Formatted error summary string
        """
        if not self.error_history:
            return "No errors recorded"

        lines = ["Error Summary:"]
        for i, error in enumerate(self.error_history, 1):
            lines.append(
                f"  {i}. [{error.phase}] {error.error_type.value}: {error.message}"
            )
        return "\n".join(lines)

    def reset(self) -> None:
        """Reset the manager state.

        Useful for testing or when starting a new workflow execution.
        """
        self.total_retry_count = 0
        self.phase_retry_counts.clear()
        self.error_history.clear()


# Export all
__all__ = [
    "ErrorRecoveryManager",
    "JobAnalysisErrorContract",
    "RegistrationErrorContract",
    "WorkflowGenErrorContract",
]
