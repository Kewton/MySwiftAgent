"""Unit tests for ErrorRecoveryManager.

Issue #359: Tests for phase-specific error handling and recovery strategies.

TDD Red Phase: These tests define the expected behavior of error recovery.
"""

from aiagent.langgraph.jobGeneratorV2.error_recovery_v3 import (
    ErrorRecoveryManager,
    JobAnalysisErrorContract,
    RegistrationErrorContract,
    WorkflowGenErrorContract,
)
from aiagent.langgraph.jobGeneratorV2.types_v3 import (
    ErrorType,
    PhaseError,
    RecoveryStrategy,
)


class TestJobAnalysisErrorContract:
    """Test suite for JobAnalysisErrorContract."""

    def test_validation_error_retry_with_feedback(self):
        """VALIDATION errors should trigger RETRY_WITH_FEEDBACK."""
        error = PhaseError(
            phase="JOB_ANALYSIS",
            error_type=ErrorType.VALIDATION,
            message="Schema validation failed",
        )
        strategy = JobAnalysisErrorContract.get_recovery_strategy(error)

        assert strategy == RecoveryStrategy.RETRY_WITH_FEEDBACK

    def test_api_error_retry_current(self):
        """API errors should trigger RETRY_CURRENT."""
        error = PhaseError(
            phase="JOB_ANALYSIS",
            error_type=ErrorType.API,
            message="LLM API rate limited",
        )
        strategy = JobAnalysisErrorContract.get_recovery_strategy(error)

        assert strategy == RecoveryStrategy.RETRY_CURRENT

    def test_business_error_relaxation(self):
        """BUSINESS errors should trigger RELAXATION."""
        error = PhaseError(
            phase="JOB_ANALYSIS",
            error_type=ErrorType.BUSINESS,
            message="Task count exceeds limit",
        )
        strategy = JobAnalysisErrorContract.get_recovery_strategy(error)

        assert strategy == RecoveryStrategy.RELAXATION

    def test_fatal_error_fail_fast(self):
        """FATAL errors should trigger FAIL_FAST."""
        error = PhaseError(
            phase="JOB_ANALYSIS",
            error_type=ErrorType.FATAL,
            message="Authentication failed",
        )
        strategy = JobAnalysisErrorContract.get_recovery_strategy(error)

        assert strategy == RecoveryStrategy.FAIL_FAST

    def test_get_max_retries(self):
        """Test max retry counts for different error types."""
        validation_error = PhaseError(
            phase="JOB_ANALYSIS", error_type=ErrorType.VALIDATION, message="test"
        )
        api_error = PhaseError(
            phase="JOB_ANALYSIS", error_type=ErrorType.API, message="test"
        )
        fatal_error = PhaseError(
            phase="JOB_ANALYSIS", error_type=ErrorType.FATAL, message="test"
        )

        assert JobAnalysisErrorContract.get_max_retries(validation_error) == 3
        assert JobAnalysisErrorContract.get_max_retries(api_error) == 3
        assert JobAnalysisErrorContract.get_max_retries(fatal_error) == 0

    def test_create_feedback_for_validation(self):
        """Test feedback generation for validation errors."""
        error = PhaseError(
            phase="JOB_ANALYSIS",
            error_type=ErrorType.VALIDATION,
            message="Invalid JSON schema",
            details={"field": "input_schema"},
        )
        feedback = JobAnalysisErrorContract.create_feedback(error)

        assert feedback is not None
        assert "Invalid JSON schema" in feedback
        assert "input_schema" in feedback or "validation" in feedback.lower()


class TestRegistrationErrorContract:
    """Test suite for RegistrationErrorContract."""

    def test_validation_error_rollback(self):
        """VALIDATION errors should trigger ROLLBACK_TO_ANALYSIS."""
        error = PhaseError(
            phase="REGISTRATION",
            error_type=ErrorType.VALIDATION,
            message="BodyTemplate validation failed",
        )
        strategy = RegistrationErrorContract.get_recovery_strategy(error)

        assert strategy == RecoveryStrategy.ROLLBACK_TO_ANALYSIS

    def test_api_error_retry_current(self):
        """API errors should trigger RETRY_CURRENT."""
        error = PhaseError(
            phase="REGISTRATION",
            error_type=ErrorType.API,
            message="JobQueue API unavailable",
        )
        strategy = RegistrationErrorContract.get_recovery_strategy(error)

        assert strategy == RecoveryStrategy.RETRY_CURRENT

    def test_transient_error_retry_current(self):
        """TRANSIENT errors should trigger RETRY_CURRENT."""
        error = PhaseError(
            phase="REGISTRATION",
            error_type=ErrorType.TRANSIENT,
            message="DB connection timeout",
        )
        strategy = RegistrationErrorContract.get_recovery_strategy(error)

        assert strategy == RecoveryStrategy.RETRY_CURRENT

    def test_should_rollback_for_validation(self):
        """Validation errors should trigger rollback."""
        error = PhaseError(
            phase="REGISTRATION", error_type=ErrorType.VALIDATION, message="test"
        )

        assert RegistrationErrorContract.should_rollback(error) is True

    def test_should_not_rollback_for_api(self):
        """API errors should not trigger rollback."""
        error = PhaseError(
            phase="REGISTRATION", error_type=ErrorType.API, message="test"
        )

        assert RegistrationErrorContract.should_rollback(error) is False


class TestWorkflowGenErrorContract:
    """Test suite for WorkflowGenErrorContract."""

    def test_validation_error_retry_with_feedback(self):
        """VALIDATION errors should trigger RETRY_WITH_FEEDBACK."""
        error = PhaseError(
            phase="WORKFLOW_GEN",
            error_type=ErrorType.VALIDATION,
            message="Invalid TaskFlow JSON",
        )
        strategy = WorkflowGenErrorContract.get_recovery_strategy(error)

        assert strategy == RecoveryStrategy.RETRY_WITH_FEEDBACK

    def test_api_error_retry_current(self):
        """API errors should trigger RETRY_CURRENT."""
        error = PhaseError(
            phase="WORKFLOW_GEN", error_type=ErrorType.API, message="LLM API timeout"
        )
        strategy = WorkflowGenErrorContract.get_recovery_strategy(error)

        assert strategy == RecoveryStrategy.RETRY_CURRENT

    def test_transient_error_retry_current(self):
        """TRANSIENT errors should trigger RETRY_CURRENT."""
        error = PhaseError(
            phase="WORKFLOW_GEN",
            error_type=ErrorType.TRANSIENT,
            message="Task execution timeout",
        )
        strategy = WorkflowGenErrorContract.get_recovery_strategy(error)

        assert strategy == RecoveryStrategy.RETRY_CURRENT

    def test_fatal_error_fail_fast(self):
        """FATAL errors should trigger FAIL_FAST (Issue #359).

        FATAL errors are unrecoverable by definition, so they should fail fast
        rather than attempt rollback which could lead to infinite loops.
        """
        error = PhaseError(
            phase="WORKFLOW_GEN", error_type=ErrorType.FATAL, message="All tasks failed"
        )
        strategy = WorkflowGenErrorContract.get_recovery_strategy(error)

        assert strategy == RecoveryStrategy.FAIL_FAST

    def test_is_task_isolated_error(self):
        """Test which errors are task-isolated."""
        validation_error = PhaseError(
            phase="WORKFLOW_GEN", error_type=ErrorType.VALIDATION, message="test"
        )
        fatal_error = PhaseError(
            phase="WORKFLOW_GEN", error_type=ErrorType.FATAL, message="test"
        )

        assert WorkflowGenErrorContract.is_task_isolated_error(validation_error) is True
        assert WorkflowGenErrorContract.is_task_isolated_error(fatal_error) is False


class TestErrorRecoveryManager:
    """Test suite for ErrorRecoveryManager."""

    def test_init_with_defaults(self):
        """Test initialization with default values."""
        manager = ErrorRecoveryManager()

        assert manager.max_total_retries == 5
        assert manager.total_retry_count == 0
        assert len(manager.error_history) == 0

    def test_init_with_custom_max_retries(self):
        """Test initialization with custom max retries."""
        manager = ErrorRecoveryManager(max_total_retries=10)

        assert manager.max_total_retries == 10

    def test_handle_validation_error_returns_retry(self):
        """Test handling validation error returns retry action."""
        manager = ErrorRecoveryManager()
        error = PhaseError(
            phase="JOB_ANALYSIS",
            error_type=ErrorType.VALIDATION,
            message="Schema validation failed",
        )

        action = manager.handle_error(error)

        assert action.strategy in (
            RecoveryStrategy.RETRY_CURRENT,
            RecoveryStrategy.RETRY_WITH_FEEDBACK,
        )

    def test_handle_fatal_error_returns_fail_fast(self):
        """Test handling fatal error returns fail fast."""
        manager = ErrorRecoveryManager()
        error = PhaseError(
            phase="JOB_ANALYSIS",
            error_type=ErrorType.FATAL,
            message="Authentication failed",
        )

        action = manager.handle_error(error)

        assert action.strategy == RecoveryStrategy.FAIL_FAST

    def test_error_history_tracking(self):
        """Test that errors are tracked in history."""
        manager = ErrorRecoveryManager()
        error = PhaseError(
            phase="JOB_ANALYSIS", error_type=ErrorType.VALIDATION, message="Test error"
        )

        manager.handle_error(error)

        assert len(manager.error_history) == 1
        assert manager.error_history[0].message == "Test error"

    def test_total_retry_limit_triggers_fail_fast(self):
        """Test that exceeding total retry limit triggers fail fast."""
        manager = ErrorRecoveryManager(max_total_retries=2)

        # Simulate reaching retry limit
        for _ in range(3):
            error = PhaseError(
                phase="JOB_ANALYSIS",
                error_type=ErrorType.VALIDATION,
                message="Test error",
            )
            action = manager.handle_error(error)

        # Should eventually fail fast
        assert action.strategy == RecoveryStrategy.FAIL_FAST

    def test_phase_retry_limit_escalates(self):
        """Test that exceeding phase retry limit escalates strategy."""
        manager = ErrorRecoveryManager()

        # Simulate exceeding phase retry limit
        for i in range(4):  # More than default 3 retries per phase
            error = PhaseError(
                phase="JOB_ANALYSIS",
                error_type=ErrorType.VALIDATION,
                message=f"Test error {i}",
                retry_count=i,
            )
            action = manager.handle_error(error)

        # Should escalate after phase limit exceeded
        assert action.strategy in (
            RecoveryStrategy.ROLLBACK_TO_ANALYSIS,
            RecoveryStrategy.FAIL_FAST,
            RecoveryStrategy.RELAXATION,
        )

    def test_unknown_phase_returns_fail_fast(self):
        """Test that unknown phase returns fail fast."""
        manager = ErrorRecoveryManager()
        error = PhaseError(
            phase="UNKNOWN_PHASE", error_type=ErrorType.VALIDATION, message="Test error"
        )

        action = manager.handle_error(error)

        assert action.strategy == RecoveryStrategy.FAIL_FAST

    def test_generate_error_summary(self):
        """Test error summary generation."""
        manager = ErrorRecoveryManager()
        manager.handle_error(
            PhaseError(
                phase="JOB_ANALYSIS", error_type=ErrorType.VALIDATION, message="Error 1"
            )
        )
        manager.handle_error(
            PhaseError(
                phase="REGISTRATION", error_type=ErrorType.API, message="Error 2"
            )
        )

        summary = manager._generate_error_summary()

        assert "Error 1" in summary
        assert "Error 2" in summary
        assert "JOB_ANALYSIS" in summary
        assert "REGISTRATION" in summary

    def test_escalate_strategy(self):
        """Test strategy escalation."""
        manager = ErrorRecoveryManager()

        assert (
            manager._escalate_strategy(RecoveryStrategy.RETRY_CURRENT)
            == RecoveryStrategy.ROLLBACK_TO_ANALYSIS
        )
        assert (
            manager._escalate_strategy(RecoveryStrategy.RETRY_WITH_FEEDBACK)
            == RecoveryStrategy.ROLLBACK_TO_ANALYSIS
        )
        assert (
            manager._escalate_strategy(RecoveryStrategy.ROLLBACK_TO_ANALYSIS)
            == RecoveryStrategy.FAIL_FAST
        )
        assert (
            manager._escalate_strategy(RecoveryStrategy.RELAXATION)
            == RecoveryStrategy.FAIL_FAST
        )


class TestErrorRecoveryManagerIntegration:
    """Integration tests for ErrorRecoveryManager."""

    def test_full_recovery_flow_job_analysis(self):
        """Test complete recovery flow for JOB_ANALYSIS phase."""
        manager = ErrorRecoveryManager()

        # First validation error - should retry with feedback
        error1 = PhaseError(
            phase="JOB_ANALYSIS",
            error_type=ErrorType.VALIDATION,
            message="Invalid schema",
        )
        action1 = manager.handle_error(error1)
        assert action1.strategy == RecoveryStrategy.RETRY_WITH_FEEDBACK
        assert action1.feedback is not None

    def test_full_recovery_flow_registration(self):
        """Test complete recovery flow for REGISTRATION phase."""
        manager = ErrorRecoveryManager()

        # Validation error in registration - should rollback
        error = PhaseError(
            phase="REGISTRATION",
            error_type=ErrorType.VALIDATION,
            message="BodyTemplate mismatch",
        )
        action = manager.handle_error(error)
        assert action.strategy == RecoveryStrategy.ROLLBACK_TO_ANALYSIS

    def test_full_recovery_flow_workflow_gen(self):
        """Test complete recovery flow for WORKFLOW_GEN phase."""
        manager = ErrorRecoveryManager()

        # Transient error - should retry current
        error = PhaseError(
            phase="WORKFLOW_GEN", error_type=ErrorType.TRANSIENT, message="Timeout"
        )
        action = manager.handle_error(error)
        assert action.strategy == RecoveryStrategy.RETRY_CURRENT
