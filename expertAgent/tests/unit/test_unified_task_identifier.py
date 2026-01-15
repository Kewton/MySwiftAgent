"""Unit tests for UnifiedTaskIdentifier and related types.

Issue #359: Tests for the new unified ID system.

TDD Red Phase: These tests define the expected behavior of the new types.
"""

import pytest

from aiagent.langgraph.jobGeneratorV2.types_v3 import (
    UnifiedTaskIdentifier,
    TaskResult,
    ParallelExecutionResult,
    ErrorType,
    RecoveryStrategy,
    PhaseError,
    RecoveryAction,
    TaskExecutionError,
)


class TestUnifiedTaskIdentifier:
    """Test suite for UnifiedTaskIdentifier."""

    def test_create_with_task_id_only(self):
        """Test creating identifier with just task_id."""
        identifier = UnifiedTaskIdentifier(task_id="task_001")

        assert identifier.task_id == "task_001"
        assert identifier.task_master_id is None

    def test_create_with_both_ids(self):
        """Test creating identifier with both IDs."""
        identifier = UnifiedTaskIdentifier(
            task_id="task_001",
            task_master_id="tm_abc123"
        )

        assert identifier.task_id == "task_001"
        assert identifier.task_master_id == "tm_abc123"

    def test_equality_based_on_task_id(self):
        """Test that equality is based on task_id only."""
        id1 = UnifiedTaskIdentifier(task_id="task_001")
        id2 = UnifiedTaskIdentifier(task_id="task_001", task_master_id="tm_xxx")

        assert id1 == id2

    def test_hash_consistency(self):
        """Test that hash is consistent with equality."""
        id1 = UnifiedTaskIdentifier(task_id="task_001")
        id2 = UnifiedTaskIdentifier(task_id="task_001", task_master_id="tm_xxx")

        assert hash(id1) == hash(id2)

    def test_can_be_used_as_dict_key(self):
        """Test that identifier can be used as dictionary key."""
        id1 = UnifiedTaskIdentifier(task_id="task_001")
        id2 = UnifiedTaskIdentifier(task_id="task_001", task_master_id="tm_xxx")

        mapping = {id1: "value"}

        assert mapping[id2] == "value"

    def test_inequality_for_different_task_ids(self):
        """Test that different task_ids are not equal."""
        id1 = UnifiedTaskIdentifier(task_id="task_001")
        id2 = UnifiedTaskIdentifier(task_id="task_002")

        assert id1 != id2

    def test_with_master_id_returns_new_instance(self):
        """Test with_master_id creates new instance with master_id."""
        original = UnifiedTaskIdentifier(task_id="task_001")
        updated = original.with_master_id("tm_abc123")

        # Original unchanged
        assert original.task_master_id is None
        # New instance has master_id
        assert updated.task_master_id == "tm_abc123"
        assert updated.task_id == "task_001"


class TestTaskResult:
    """Test suite for TaskResult."""

    def test_create_successful_result(self):
        """Test creating a successful task result."""
        result = TaskResult(
            task_id="task_001",
            success=True,
            workflow={"workflow_name": "test_workflow"},
            execution_time_ms=150.5
        )

        assert result.task_id == "task_001"
        assert result.success is True
        assert result.workflow == {"workflow_name": "test_workflow"}
        assert result.error is None
        assert result.retry_count == 0
        assert result.execution_time_ms == 150.5

    def test_create_failed_result(self):
        """Test creating a failed task result."""
        error = TaskExecutionError(
            error_type=ErrorType.VALIDATION,
            message="Schema validation failed",
            recoverable=True
        )
        result = TaskResult(
            task_id="task_001",
            success=False,
            error=error,
            retry_count=2
        )

        assert result.success is False
        assert result.error.message == "Schema validation failed"
        assert result.retry_count == 2


class TestParallelExecutionResult:
    """Test suite for ParallelExecutionResult."""

    def test_all_succeeded(self):
        """Test result when all tasks succeed."""
        successful = [
            TaskResult(task_id="task_001", success=True),
            TaskResult(task_id="task_002", success=True),
        ]
        result = ParallelExecutionResult(
            successful_tasks=successful,
            failed_tasks=[],
            total_execution_time_ms=500.0
        )

        assert result.all_succeeded is True
        assert result.partial_success is False
        assert result.all_failed is False

    def test_partial_success(self):
        """Test result when some tasks succeed."""
        successful = [
            TaskResult(task_id="task_001", success=True),
        ]
        failed = [
            TaskResult(
                task_id="task_002",
                success=False,
                error=TaskExecutionError(
                    error_type=ErrorType.TRANSIENT,
                    message="Timeout",
                    recoverable=True
                )
            ),
        ]
        result = ParallelExecutionResult(
            successful_tasks=successful,
            failed_tasks=failed,
            total_execution_time_ms=500.0
        )

        assert result.all_succeeded is False
        assert result.partial_success is True
        assert result.all_failed is False

    def test_all_failed(self):
        """Test result when all tasks fail."""
        failed = [
            TaskResult(
                task_id="task_001",
                success=False,
                error=TaskExecutionError(
                    error_type=ErrorType.FATAL,
                    message="Fatal error",
                    recoverable=False
                )
            ),
        ]
        result = ParallelExecutionResult(
            successful_tasks=[],
            failed_tasks=failed,
            total_execution_time_ms=500.0
        )

        assert result.all_succeeded is False
        assert result.partial_success is False
        assert result.all_failed is True

    def test_get_error_summary(self):
        """Test error summary generation."""
        failed = [
            TaskResult(
                task_id="task_001",
                success=False,
                error=TaskExecutionError(
                    error_type=ErrorType.VALIDATION,
                    message="Validation failed",
                    recoverable=True
                )
            ),
            TaskResult(
                task_id="task_002",
                success=False,
                error=TaskExecutionError(
                    error_type=ErrorType.TRANSIENT,
                    message="Timeout occurred",
                    recoverable=True
                )
            ),
        ]
        result = ParallelExecutionResult(
            successful_tasks=[],
            failed_tasks=failed,
            total_execution_time_ms=500.0
        )

        summary = result.get_error_summary()

        assert "Failed tasks (2)" in summary
        assert "task_001" in summary
        assert "task_002" in summary
        assert "Validation failed" in summary
        assert "Timeout occurred" in summary


class TestErrorType:
    """Test suite for ErrorType enum."""

    def test_error_types_exist(self):
        """Test all required error types exist."""
        assert ErrorType.TRANSIENT.value == "transient"
        assert ErrorType.VALIDATION.value == "validation"
        assert ErrorType.API.value == "api"
        assert ErrorType.BUSINESS.value == "business"
        assert ErrorType.FATAL.value == "fatal"


class TestRecoveryStrategy:
    """Test suite for RecoveryStrategy enum."""

    def test_strategies_exist(self):
        """Test all required recovery strategies exist."""
        assert RecoveryStrategy.RETRY_CURRENT.value == "retry_current"
        assert RecoveryStrategy.RETRY_WITH_FEEDBACK.value == "retry_with_feedback"
        assert RecoveryStrategy.ROLLBACK_TO_ANALYSIS.value == "rollback_to_analysis"
        assert RecoveryStrategy.RELAXATION.value == "relaxation"
        assert RecoveryStrategy.FAIL_FAST.value == "fail_fast"


class TestPhaseError:
    """Test suite for PhaseError."""

    def test_create_phase_error(self):
        """Test creating a phase error."""
        error = PhaseError(
            phase="JOB_ANALYSIS",
            error_type=ErrorType.VALIDATION,
            message="Schema validation failed",
            details={"field": "input_schema", "issue": "missing required property"},
            recoverable=True
        )

        assert error.phase == "JOB_ANALYSIS"
        assert error.error_type == ErrorType.VALIDATION
        assert error.message == "Schema validation failed"
        assert error.details["field"] == "input_schema"
        assert error.recoverable is True

    def test_default_values(self):
        """Test default values for optional fields."""
        error = PhaseError(
            phase="WORKFLOW_GEN",
            error_type=ErrorType.TRANSIENT,
            message="Timeout"
        )

        assert error.details is None
        assert error.recoverable is True
        assert error.retry_count == 0
        assert error.max_retries == 3


class TestRecoveryAction:
    """Test suite for RecoveryAction."""

    def test_create_retry_action(self):
        """Test creating a retry action."""
        action = RecoveryAction(
            strategy=RecoveryStrategy.RETRY_WITH_FEEDBACK,
            feedback="Please fix the schema validation errors",
            retry_count=1
        )

        assert action.strategy == RecoveryStrategy.RETRY_WITH_FEEDBACK
        assert action.feedback == "Please fix the schema validation errors"
        assert action.retry_count == 1

    def test_create_fail_fast_action(self):
        """Test creating a fail fast action."""
        action = RecoveryAction(
            strategy=RecoveryStrategy.FAIL_FAST,
            feedback="Fatal error occurred",
            error_summary="Authentication failed"
        )

        assert action.strategy == RecoveryStrategy.FAIL_FAST
        assert action.error_summary == "Authentication failed"


class TestTaskExecutionError:
    """Test suite for TaskExecutionError."""

    def test_create_execution_error(self):
        """Test creating task execution error."""
        error = TaskExecutionError(
            error_type=ErrorType.VALIDATION,
            message="Invalid workflow YAML",
            recoverable=True,
            details={"line": 10, "error": "syntax error"}
        )

        assert error.error_type == ErrorType.VALIDATION
        assert error.message == "Invalid workflow YAML"
        assert error.recoverable is True
        assert error.details["line"] == 10

    def test_default_recoverable(self):
        """Test default recoverable is True."""
        error = TaskExecutionError(
            error_type=ErrorType.TRANSIENT,
            message="Timeout"
        )

        assert error.recoverable is True
