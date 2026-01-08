"""Unit tests for Job Generator V2 recovery module.

Tests for ErrorRecoveryManager and related types.
This is CRITICAL for fixing the retry_count bug (Issue #342).
"""



class TestErrorRecoveryStrategy:
    """Test cases for ErrorRecoveryStrategy enum."""

    def test_error_recovery_strategy_exists(self):
        """ErrorRecoveryStrategy should be importable."""
        from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryStrategy

        assert ErrorRecoveryStrategy is not None

    def test_error_recovery_strategy_values(self):
        """ErrorRecoveryStrategy should have all expected values."""
        from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryStrategy

        assert ErrorRecoveryStrategy.FAIL_FAST.value == "fail_fast"
        assert ErrorRecoveryStrategy.RETRY_CURRENT.value == "retry_current"
        assert ErrorRecoveryStrategy.ROLLBACK_ONE.value == "rollback_one"
        assert (
            ErrorRecoveryStrategy.ROLLBACK_TO_BREAKDOWN.value == "rollback_to_breakdown"
        )
        assert ErrorRecoveryStrategy.RELAXATION.value == "relaxation"


class TestErrorRecoveryDecision:
    """Test cases for ErrorRecoveryDecision dataclass."""

    def test_error_recovery_decision_exists(self):
        """ErrorRecoveryDecision should be importable."""
        from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryDecision

        assert ErrorRecoveryDecision is not None

    def test_error_recovery_decision_creation(self):
        """ErrorRecoveryDecision should be creatable."""
        from aiagent.langgraph.jobGeneratorV2.recovery import (
            ErrorRecoveryDecision,
            ErrorRecoveryStrategy,
        )

        decision = ErrorRecoveryDecision(
            strategy=ErrorRecoveryStrategy.RETRY_CURRENT,
            target_phase=None,
            feedback="Retry due to transient error",
            relaxation_suggestions=None,
            should_notify_user=False,
        )
        assert decision.strategy == ErrorRecoveryStrategy.RETRY_CURRENT
        assert decision.feedback == "Retry due to transient error"


class TestErrorRecoveryManager:
    """Test cases for ErrorRecoveryManager."""

    def test_error_recovery_manager_exists(self):
        """ErrorRecoveryManager should be importable."""
        from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryManager

        assert ErrorRecoveryManager is not None

    def test_decide_recovery_for_transient_error(self):
        """Transient errors should result in RETRY_CURRENT strategy."""
        from unittest.mock import MagicMock

        from aiagent.langgraph.jobGeneratorV2.protocols import (
            ErrorType,
            WorkflowError,
        )
        from aiagent.langgraph.jobGeneratorV2.recovery import (
            ErrorRecoveryManager,
            ErrorRecoveryStrategy,
        )
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        manager = ErrorRecoveryManager()
        error = WorkflowError("Network timeout", ErrorType.TRANSIENT)
        context = MagicMock()
        context.can_retry.return_value = True

        decision = manager.decide_recovery(
            Phase.TASK_BREAKDOWN,
            error,
            context,
        )

        assert decision.strategy == ErrorRecoveryStrategy.RETRY_CURRENT

    def test_decide_recovery_for_validation_error(self):
        """Validation errors should result in RETRY_CURRENT strategy."""
        from unittest.mock import MagicMock

        from aiagent.langgraph.jobGeneratorV2.protocols import (
            ErrorType,
            WorkflowError,
        )
        from aiagent.langgraph.jobGeneratorV2.recovery import (
            ErrorRecoveryManager,
            ErrorRecoveryStrategy,
        )
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        manager = ErrorRecoveryManager()
        error = WorkflowError("Schema validation failed", ErrorType.VALIDATION)
        context = MagicMock()
        context.can_retry.return_value = True

        decision = manager.decide_recovery(
            Phase.INTERFACE_DESIGN,
            error,
            context,
        )

        assert decision.strategy == ErrorRecoveryStrategy.RETRY_CURRENT

    def test_decide_recovery_for_compatibility_error(self):
        """Compatibility errors should result in ROLLBACK_ONE strategy."""
        from unittest.mock import MagicMock

        from aiagent.langgraph.jobGeneratorV2.protocols import (
            ErrorType,
            WorkflowError,
        )
        from aiagent.langgraph.jobGeneratorV2.recovery import (
            ErrorRecoveryManager,
            ErrorRecoveryStrategy,
        )
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        manager = ErrorRecoveryManager()
        error = WorkflowError("Interface compatibility error", ErrorType.COMPATIBILITY)
        context = MagicMock()
        context.can_retry.return_value = True
        context.get_rollback_count.return_value = 0

        decision = manager.decide_recovery(
            Phase.INTERFACE_DESIGN,
            error,
            context,
        )

        assert decision.strategy == ErrorRecoveryStrategy.ROLLBACK_ONE

    def test_decide_recovery_for_business_error(self):
        """Business errors should result in RELAXATION strategy."""
        from unittest.mock import MagicMock

        from aiagent.langgraph.jobGeneratorV2.protocols import (
            ErrorType,
            WorkflowError,
        )
        from aiagent.langgraph.jobGeneratorV2.recovery import (
            ErrorRecoveryManager,
            ErrorRecoveryStrategy,
        )
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        manager = ErrorRecoveryManager()
        error = WorkflowError("Infeasible requirement", ErrorType.BUSINESS)
        context = MagicMock()

        decision = manager.decide_recovery(
            Phase.TASK_BREAKDOWN,
            error,
            context,
        )

        assert decision.strategy == ErrorRecoveryStrategy.RELAXATION
        assert decision.should_notify_user is True

    def test_decide_recovery_for_fatal_error(self):
        """Fatal errors should result in FAIL_FAST strategy."""
        from unittest.mock import MagicMock

        from aiagent.langgraph.jobGeneratorV2.protocols import (
            ErrorType,
            WorkflowError,
        )
        from aiagent.langgraph.jobGeneratorV2.recovery import (
            ErrorRecoveryManager,
            ErrorRecoveryStrategy,
        )
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        manager = ErrorRecoveryManager()
        error = WorkflowError("Database connection failed", ErrorType.FATAL)
        context = MagicMock()

        decision = manager.decide_recovery(
            Phase.REGISTRATION,
            error,
            context,
        )

        assert decision.strategy == ErrorRecoveryStrategy.FAIL_FAST
        assert decision.should_notify_user is True

    def test_escalate_when_retry_limit_exceeded(self):
        """When retry limit exceeded, should escalate to rollback or fail."""
        from unittest.mock import MagicMock

        from aiagent.langgraph.jobGeneratorV2.protocols import (
            ErrorType,
            WorkflowError,
        )
        from aiagent.langgraph.jobGeneratorV2.recovery import (
            ErrorRecoveryManager,
            ErrorRecoveryStrategy,
        )
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        manager = ErrorRecoveryManager()
        error = WorkflowError("Validation failed", ErrorType.VALIDATION)
        context = MagicMock()
        context.can_retry.return_value = False  # Retry limit exceeded
        context.get_rollback_count.return_value = 0

        decision = manager.decide_recovery(
            Phase.INTERFACE_DESIGN,  # Not Phase 1
            error,
            context,
        )

        # Should escalate to rollback when retry limit exceeded for non-Phase1
        assert decision.strategy in (
            ErrorRecoveryStrategy.ROLLBACK_ONE,
            ErrorRecoveryStrategy.FAIL_FAST,
        )

    def test_escalate_to_relaxation_for_phase1_retry_exhausted(self):
        """When Phase 1 retry limit exceeded, should escalate to RELAXATION."""
        from unittest.mock import MagicMock

        from aiagent.langgraph.jobGeneratorV2.protocols import (
            ErrorType,
            WorkflowError,
        )
        from aiagent.langgraph.jobGeneratorV2.recovery import (
            ErrorRecoveryManager,
            ErrorRecoveryStrategy,
        )
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        manager = ErrorRecoveryManager()
        error = WorkflowError("Validation failed", ErrorType.VALIDATION)
        context = MagicMock()
        context.can_retry.return_value = False  # Retry limit exceeded

        decision = manager.decide_recovery(
            Phase.TASK_BREAKDOWN,  # Phase 1
            error,
            context,
        )

        # Phase 1 retry exhausted should result in relaxation
        assert decision.strategy == ErrorRecoveryStrategy.RELAXATION

    def test_rollback_target_calculation(self):
        """Should correctly calculate rollback target phase."""
        from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryManager
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        manager = ErrorRecoveryManager()

        # Interface design should rollback to task breakdown
        assert (
            manager._get_rollback_target(Phase.INTERFACE_DESIGN)
            == Phase.TASK_BREAKDOWN
        )

        # Registration should rollback to interface design
        assert (
            manager._get_rollback_target(Phase.REGISTRATION)
            == Phase.INTERFACE_DESIGN
        )

        # Workflow gen should rollback to registration
        assert (
            manager._get_rollback_target(Phase.WORKFLOW_GEN)
            == Phase.REGISTRATION
        )


class TestMaxRollbacksPerPhase:
    """Test cases for rollback limit enforcement."""

    def test_max_rollbacks_per_phase_constant(self):
        """MAX_ROLLBACKS_PER_PHASE should be defined."""
        from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryManager

        manager = ErrorRecoveryManager()
        assert manager.MAX_ROLLBACKS_PER_PHASE == 2

    def test_fail_when_rollback_limit_exceeded(self):
        """Should fail when rollback limit is exceeded."""
        from unittest.mock import MagicMock

        from aiagent.langgraph.jobGeneratorV2.protocols import (
            ErrorType,
            WorkflowError,
        )
        from aiagent.langgraph.jobGeneratorV2.recovery import (
            ErrorRecoveryManager,
            ErrorRecoveryStrategy,
        )
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        manager = ErrorRecoveryManager()
        error = WorkflowError("Compatibility error", ErrorType.COMPATIBILITY)
        context = MagicMock()
        context.can_retry.return_value = True
        context.get_rollback_count.return_value = 3  # Exceeded limit

        decision = manager.decide_recovery(
            Phase.INTERFACE_DESIGN,
            error,
            context,
        )

        # Should fail or request relaxation when rollback limit exceeded
        assert decision.strategy in (
            ErrorRecoveryStrategy.FAIL_FAST,
            ErrorRecoveryStrategy.RELAXATION,
        )


class TestRetryCountBugFix:
    """Test cases specifically for the retry_count bug fix (Issue #342).

    The original bug was in interface_definition.py:536-543 where
    interface_warnings was not checked, causing retry_count to reset to 0.

    In the new architecture, each phase has its own RetryState managed
    by ErrorRecoveryManager, preventing this issue.
    """

    def test_retry_count_not_reset_when_interface_warnings_exist(self):
        """retry_count should NOT reset when there are interface warnings.

        This test verifies the fix for the original bug where retry_count
        was reset to 0 when interface_warnings existed but evaluation_feedback
        and validation_result were empty.
        """
        from unittest.mock import MagicMock

        from aiagent.langgraph.jobGeneratorV2.protocols import (
            ErrorType,
            WorkflowError,
        )
        from aiagent.langgraph.jobGeneratorV2.recovery import (
            ErrorRecoveryManager,
            ErrorRecoveryStrategy,
        )
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        manager = ErrorRecoveryManager()

        # Simulate interface compatibility warning (the original bug scenario)
        error = WorkflowError(
            "Interface compatibility warning: missing required field",
            ErrorType.COMPATIBILITY,
        )

        context = MagicMock()
        context.can_retry.return_value = True
        context.get_rollback_count.return_value = 0

        decision = manager.decide_recovery(
            Phase.INTERFACE_DESIGN,
            error,
            context,
        )

        # Key assertion: Should NOT be RETRY_CURRENT with reset
        # Should either rollback or continue with proper count management
        assert decision.strategy in (
            ErrorRecoveryStrategy.ROLLBACK_ONE,
            ErrorRecoveryStrategy.ROLLBACK_TO_BREAKDOWN,
        )
        # If rollback, there should be feedback for the LLM
        assert decision.feedback is not None or decision.target_phase is not None

    def test_retry_count_incremented_on_retry(self):
        """retry_count should be incremented when RETRY_CURRENT is chosen."""
        from aiagent.langgraph.jobGeneratorV2.types import RetryState

        state = RetryState(count=0, max_count=3)

        # Simulate recording a retry
        state.record("Interface validation failed")

        assert state.count == 1
        assert len(state.history) == 1
        assert state.history[0].attempt == 1

        # Second retry
        state.record("Interface validation still failing")
        assert state.count == 2

    def test_no_infinite_loop_possible(self):
        """Infinite loop should be impossible with new architecture.

        The original bug allowed infinite loops because retry_count reset.
        The new architecture prevents this by:
        1. Each phase has its own RetryState
        2. RetryState.can_retry() always returns False when count >= max_count
        """
        from aiagent.langgraph.jobGeneratorV2.types import RetryState

        state = RetryState(count=0, max_count=3)

        # Exhaust retries
        for i in range(10):  # Try more than max
            if state.can_retry():
                state.record(f"Retry {i + 1}")
            else:
                break

        # Should have stopped at max_count
        assert state.count == 3
        assert not state.can_retry()

        # Attempting more retries should be prevented
        can_continue = state.can_retry()
        assert can_continue is False
