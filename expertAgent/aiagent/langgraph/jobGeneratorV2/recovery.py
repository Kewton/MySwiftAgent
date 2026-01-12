"""Error recovery management for Job Generator V2.

This module provides intelligent error recovery strategies to prevent
infinite loops and properly manage retries across phases.

Issue #342: This is the CRITICAL fix for the retry_count bug.
The original bug was that retry_count reset to 0 when interface_warnings
existed but evaluation_feedback was empty. This module ensures each phase
has proper retry state management.

Key design decisions:
1. Each phase has its own RetryState (max 3 retries per phase)
2. Total retries across all phases capped at 5
3. ErrorRecoveryStrategy enum defines all possible recovery actions
4. ErrorRecoveryManager decides which strategy to use based on error type
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .protocols import ErrorType, WorkflowError
from .types import Phase, RelaxationSuggestion

logger = logging.getLogger(__name__)


class ErrorRecoveryStrategy(Enum):
    """Recovery strategies for handling workflow errors.

    - FAIL_FAST: Stop immediately (for fatal errors)
    - RETRY_CURRENT: Retry the current phase (for transient/validation errors)
    - ROLLBACK_ONE: Go back one phase (for compatibility errors)
    - ROLLBACK_TO_BREAKDOWN: Go back to task breakdown (for major issues)
    - RELAXATION: Ask user to relax requirements (for business constraints)
    """

    FAIL_FAST = "fail_fast"
    RETRY_CURRENT = "retry_current"
    ROLLBACK_ONE = "rollback_one"
    ROLLBACK_TO_BREAKDOWN = "rollback_to_breakdown"
    RELAXATION = "relaxation"


@dataclass
class ErrorRecoveryDecision:
    """Decision made by ErrorRecoveryManager.

    Attributes:
        strategy: The recovery strategy to use
        target_phase: Target phase for rollback (if applicable)
        feedback: Feedback to provide to LLM for next attempt
        relaxation_suggestions: Suggestions for requirement relaxation
        should_notify_user: Whether to notify user of the issue
    """

    strategy: ErrorRecoveryStrategy
    target_phase: Phase | None = None
    feedback: str | None = None
    relaxation_suggestions: list[RelaxationSuggestion] | None = None
    should_notify_user: bool = False


class ErrorRecoveryManager:
    """Manages error recovery decisions for job generation workflow.

    This class encapsulates the logic for deciding how to recover from
    errors during workflow execution. It considers:
    - Error type (transient, validation, compatibility, business, fatal)
    - Current phase
    - Retry count for the phase
    - Rollback count

    The key improvement over the old system is that each phase has its own
    retry state, preventing the retry_count reset bug.

    Example:
        manager = ErrorRecoveryManager()
        decision = manager.decide_recovery(
            phase=Phase.INTERFACE_DESIGN,
            error=WorkflowError("Schema validation failed", ErrorType.VALIDATION),
            context=execution_context,
        )
        if decision.strategy == ErrorRecoveryStrategy.RETRY_CURRENT:
            # Retry the current phase with feedback
            ...
    """

    # Maximum rollbacks per phase before escalating
    MAX_ROLLBACKS_PER_PHASE = 2

    # Phase order for rollback calculation
    PHASE_ORDER = [
        Phase.TASK_BREAKDOWN,
        Phase.INTERFACE_DESIGN,
        Phase.REGISTRATION,
        Phase.WORKFLOW_GEN,
    ]

    def decide_recovery(
        self,
        phase: Phase,
        error: WorkflowError,
        context: Any,  # ExecutionContext
    ) -> ErrorRecoveryDecision:
        """Decide how to recover from an error.

        Args:
            phase: The phase where the error occurred
            error: The error that occurred
            context: Execution context with retry state information

        Returns:
            ErrorRecoveryDecision with the chosen strategy
        """
        logger.info(
            "Deciding recovery for %s error in %s phase",
            error.error_type.value,
            phase.value,
        )

        # Fatal errors always fail fast
        if error.error_type == ErrorType.FATAL:
            return ErrorRecoveryDecision(
                strategy=ErrorRecoveryStrategy.FAIL_FAST,
                feedback=f"Fatal error: {error}",
                should_notify_user=True,
            )

        # Business errors require user intervention (relaxation)
        if error.error_type == ErrorType.BUSINESS:
            return ErrorRecoveryDecision(
                strategy=ErrorRecoveryStrategy.RELAXATION,
                feedback=f"Business constraint violation: {error}",
                relaxation_suggestions=[
                    RelaxationSuggestion(
                        original_requirement=str(error),
                        suggested_alternative="Consider simplifying the requirement",
                        reason=str(error),
                    )
                ],
                should_notify_user=True,
            )

        # Compatibility errors should rollback to previous phase
        if error.error_type == ErrorType.COMPATIBILITY:
            return self._handle_compatibility_error(phase, error, context)

        # Issue #353: INCOMPLETE_WORKFLOW errors are retriable but should notify user
        if error.error_type == ErrorType.INCOMPLETE_WORKFLOW:
            return self._handle_incomplete_workflow_error(phase, error, context)

        # Transient, validation, and API errors can be retried
        if error.error_type in (ErrorType.TRANSIENT, ErrorType.VALIDATION, ErrorType.API):
            return self._handle_retriable_error(phase, error, context)

        # Default: fail fast for unknown error types
        logger.warning("Unknown error type: %s, failing fast", error.error_type)
        return ErrorRecoveryDecision(
            strategy=ErrorRecoveryStrategy.FAIL_FAST,
            feedback=f"Unknown error type: {error}",
            should_notify_user=True,
        )

    def _handle_compatibility_error(
        self,
        phase: Phase,
        error: WorkflowError,
        context: Any,
    ) -> ErrorRecoveryDecision:
        """Handle compatibility errors with rollback strategy.

        Compatibility errors (e.g., interface mismatch between phases)
        typically require going back to the previous phase.
        """
        # Check rollback limit
        rollback_count = context.get_rollback_count()
        if rollback_count >= self.MAX_ROLLBACKS_PER_PHASE:
            logger.warning(
                "Rollback limit exceeded (%d >= %d), escalating to relaxation",
                rollback_count,
                self.MAX_ROLLBACKS_PER_PHASE,
            )
            return ErrorRecoveryDecision(
                strategy=ErrorRecoveryStrategy.RELAXATION,
                feedback=f"Too many rollbacks: {error}. Please simplify the requirement.",
                should_notify_user=True,
            )

        # Determine rollback target
        target_phase = self._get_rollback_target(phase)
        if target_phase is None:
            # Already at first phase, need relaxation
            return ErrorRecoveryDecision(
                strategy=ErrorRecoveryStrategy.RELAXATION,
                feedback=f"Cannot rollback from first phase: {error}",
                should_notify_user=True,
            )

        return ErrorRecoveryDecision(
            strategy=ErrorRecoveryStrategy.ROLLBACK_ONE,
            target_phase=target_phase,
            feedback=self._generate_rollback_feedback(phase, target_phase, error),
            should_notify_user=False,
        )

    def _handle_retriable_error(
        self,
        phase: Phase,
        error: WorkflowError,
        context: Any,
    ) -> ErrorRecoveryDecision:
        """Handle retriable errors (transient and validation).

        These errors can be retried within the current phase, but
        if retry limit is exceeded, we escalate based on phase.
        """
        can_retry = context.can_retry()

        if can_retry:
            return ErrorRecoveryDecision(
                strategy=ErrorRecoveryStrategy.RETRY_CURRENT,
                feedback=self._generate_retry_feedback(error),
                should_notify_user=False,
            )

        # Retry limit exceeded - escalate based on phase
        logger.warning(
            "Retry limit exceeded in %s phase, escalating",
            phase.value,
        )

        # Phase 1 (TaskBreakdown) - can't rollback, need relaxation
        if phase == Phase.TASK_BREAKDOWN:
            return ErrorRecoveryDecision(
                strategy=ErrorRecoveryStrategy.RELAXATION,
                feedback=(
                    f"Task breakdown failed after maximum retries: {error}. "
                    "Please simplify or clarify the requirement."
                ),
                should_notify_user=True,
            )

        # Other phases - try rollback first
        rollback_count = context.get_rollback_count()
        if rollback_count < self.MAX_ROLLBACKS_PER_PHASE:
            target_phase = self._get_rollback_target(phase)
            return ErrorRecoveryDecision(
                strategy=ErrorRecoveryStrategy.ROLLBACK_ONE,
                target_phase=target_phase,
                feedback=(
                    f"Phase {phase.value} failed after maximum retries. "
                    f"Rolling back to {target_phase.value if target_phase else 'unknown'}."
                ),
                should_notify_user=False,
            )

        # Can't retry, can't rollback - fail
        return ErrorRecoveryDecision(
            strategy=ErrorRecoveryStrategy.FAIL_FAST,
            feedback=(
                f"Phase {phase.value} failed after all recovery attempts: {error}"
            ),
            should_notify_user=True,
        )

    def _get_rollback_target(self, phase: Phase) -> Phase | None:
        """Get the target phase for rollback.

        Args:
            phase: Current phase

        Returns:
            Previous phase or None if at first phase
        """
        try:
            current_index = self.PHASE_ORDER.index(phase)
            if current_index == 0:
                return None
            return self.PHASE_ORDER[current_index - 1]
        except ValueError:
            logger.error("Unknown phase: %s", phase)
            return None

    def _generate_rollback_feedback(
        self,
        from_phase: Phase,
        to_phase: Phase,
        error: WorkflowError,
    ) -> str:
        """Generate feedback for rollback.

        This feedback helps the LLM understand why the rollback happened
        and how to improve.
        """
        feedback_parts = [
            "## Rollback Required",
            "",
            f"Phase `{from_phase.value}` encountered an error that requires rollback.",
            "",
            f"**Error:** {error}",
            f"**Error Type:** {error.error_type.value}",
            "",
            f"### Recommendations for {to_phase.value}:",
        ]

        if from_phase == Phase.INTERFACE_DESIGN:
            feedback_parts.extend(
                [
                    "- Review task outputs to ensure they provide all required fields",
                    "- Check that task chain has compatible interfaces",
                    "- Consider simplifying complex data transformations",
                ]
            )
        elif from_phase == Phase.REGISTRATION:
            feedback_parts.extend(
                [
                    "- Verify interface schemas are valid JSON Schema",
                    "- Check that all required fields have proper types",
                    "- Ensure no circular dependencies between tasks",
                ]
            )

        return "\n".join(feedback_parts)

    def _generate_retry_feedback(self, error: WorkflowError) -> str:
        """Generate feedback for retry.

        This feedback helps the LLM understand what went wrong and
        how to fix it on retry.
        """
        feedback_parts = [
            "## Retry Required",
            "",
            "The previous attempt failed with an error that may be fixed on retry.",
            "",
            f"**Error:** {error}",
            f"**Error Type:** {error.error_type.value}",
            "",
            "### Please address:",
        ]

        if error.error_type == ErrorType.VALIDATION:
            feedback_parts.extend(
                [
                    "- Check that all fields have valid types",
                    "- Ensure required fields are present",
                    "- Verify schema constraints are met",
                ]
            )
        elif error.error_type == ErrorType.TRANSIENT:
            feedback_parts.extend(
                [
                    "- This may be a temporary issue",
                    "- The retry should proceed with the same input",
                ]
            )

        return "\n".join(feedback_parts)

    def _handle_incomplete_workflow_error(
        self,
        phase: Phase,
        error: WorkflowError,
        context: Any,
    ) -> ErrorRecoveryDecision:
        """Handle INCOMPLETE_WORKFLOW errors.

        Issue #353: INCOMPLETE_WORKFLOW errors occur when WORKFLOW_GEN phase
        fails to complete, leaving __PENDING__ placeholders. These are retriable
        but should always notify the user.
        """
        can_retry = context.can_retry()
        rollback_count = context.get_rollback_count()

        if can_retry:
            return ErrorRecoveryDecision(
                strategy=ErrorRecoveryStrategy.RETRY_CURRENT,
                feedback=self._generate_incomplete_workflow_feedback(error),
                should_notify_user=True,  # Always notify for incomplete workflows
            )

        # Retry limit exceeded - check rollback option
        if rollback_count < self.MAX_ROLLBACKS_PER_PHASE:
            logger.warning(
                "INCOMPLETE_WORKFLOW: Retry limit exceeded, attempting rollback"
            )
            target_phase = self._get_rollback_target(phase)
            return ErrorRecoveryDecision(
                strategy=ErrorRecoveryStrategy.ROLLBACK_ONE,
                target_phase=target_phase,
                feedback=(
                    f"WORKFLOW_GEN phase incomplete after maximum retries. "
                    f"Rolling back to {target_phase.value if target_phase else 'unknown'}."
                ),
                should_notify_user=True,
            )

        # Can't retry, can't rollback - fail fast
        logger.error(
            "INCOMPLETE_WORKFLOW: All recovery attempts exhausted, failing"
        )
        return ErrorRecoveryDecision(
            strategy=ErrorRecoveryStrategy.FAIL_FAST,
            feedback=(
                f"WORKFLOW_GEN phase incomplete after all recovery attempts: {error}"
            ),
            should_notify_user=True,
        )

    def _generate_incomplete_workflow_feedback(self, error: WorkflowError) -> str:
        """Generate feedback for INCOMPLETE_WORKFLOW retry.

        Issue #353: Specific feedback for workflow generation failures.
        """
        feedback_parts = [
            "## WORKFLOW_GEN Phase Incomplete",
            "",
            "The workflow generation phase did not complete successfully.",
            "Some tasks still have __PENDING__ workflow_name placeholders.",
            "",
            f"**Error:** {error}",
            "",
            "### Possible causes:",
            "- GraphAiServer connectivity issues",
            "- LLM API rate limiting or timeout",
            "- Invalid workflow YAML generated",
            "",
            "### Retry will:",
            "- Re-attempt workflow generation for pending tasks",
            "- Use exponential backoff to avoid rate limiting",
        ]

        if error.details:
            pending_count = error.details.get("pending_count", "unknown")
            feedback_parts.append(f"\n**Pending tasks:** {pending_count}")

        return "\n".join(feedback_parts)
