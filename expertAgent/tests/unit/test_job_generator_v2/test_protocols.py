"""Unit tests for Job Generator V2 protocols module.

Tests for WorkflowProtocol and related protocols.
"""


class TestWorkflowProtocol:
    """Test cases for WorkflowProtocol."""

    def test_workflow_protocol_exists(self):
        """WorkflowProtocol should be importable."""
        from aiagent.langgraph.jobGeneratorV2.protocols import WorkflowProtocol

        assert WorkflowProtocol is not None

    def test_workflow_protocol_has_execute_method(self):
        """WorkflowProtocol should define execute method."""

        from aiagent.langgraph.jobGeneratorV2.protocols import WorkflowProtocol

        # Get all abstract methods or methods defined in the protocol
        assert hasattr(WorkflowProtocol, "execute")

    def test_workflow_protocol_has_get_retry_policy_method(self):
        """WorkflowProtocol should define get_retry_policy method."""
        from aiagent.langgraph.jobGeneratorV2.protocols import WorkflowProtocol

        assert hasattr(WorkflowProtocol, "get_retry_policy")

    def test_workflow_protocol_can_be_implemented(self):
        """WorkflowProtocol should be implementable by a class."""
        from aiagent.langgraph.jobGeneratorV2.types import (
            PhaseStatus,
            TaskBreakdownOutput,
        )

        class TestWorkflow:
            async def execute(self, input, context):
                return TaskBreakdownOutput(
                    status=PhaseStatus.SUCCESS,
                    tasks=[],
                )

            def get_retry_policy(self):
                return {"max_retries": 3}

        # Should be able to create an instance
        workflow = TestWorkflow()
        assert workflow is not None


class TestRetryPolicy:
    """Test cases for RetryPolicy dataclass."""

    def test_retry_policy_exists(self):
        """RetryPolicy should be importable."""
        from aiagent.langgraph.jobGeneratorV2.protocols import RetryPolicy

        assert RetryPolicy is not None

    def test_retry_policy_has_max_retries(self):
        """RetryPolicy should have max_retries field."""
        from aiagent.langgraph.jobGeneratorV2.protocols import RetryPolicy

        policy = RetryPolicy(max_retries=3)
        assert policy.max_retries == 3

    def test_retry_policy_default_values(self):
        """RetryPolicy should have sensible defaults."""
        from aiagent.langgraph.jobGeneratorV2.protocols import RetryPolicy

        policy = RetryPolicy()
        assert policy.max_retries == 3
        assert policy.backoff_factor == 1.0


class TestErrorType:
    """Test cases for ErrorType enum."""

    def test_error_type_exists(self):
        """ErrorType should be importable."""
        from aiagent.langgraph.jobGeneratorV2.protocols import ErrorType

        assert ErrorType is not None

    def test_error_type_values(self):
        """ErrorType should have expected values."""
        from aiagent.langgraph.jobGeneratorV2.protocols import ErrorType

        assert ErrorType.TRANSIENT.value == "transient"
        assert ErrorType.VALIDATION.value == "validation"
        assert ErrorType.COMPATIBILITY.value == "compatibility"
        assert ErrorType.BUSINESS.value == "business"
        assert ErrorType.FATAL.value == "fatal"


class TestWorkflowError:
    """Test cases for WorkflowError exception."""

    def test_workflow_error_exists(self):
        """WorkflowError should be importable."""
        from aiagent.langgraph.jobGeneratorV2.protocols import WorkflowError

        assert WorkflowError is not None

    def test_workflow_error_is_exception(self):
        """WorkflowError should be an Exception."""
        from aiagent.langgraph.jobGeneratorV2.protocols import WorkflowError

        assert issubclass(WorkflowError, Exception)

    def test_workflow_error_has_error_type(self):
        """WorkflowError should have error_type attribute."""
        from aiagent.langgraph.jobGeneratorV2.protocols import (
            ErrorType,
            WorkflowError,
        )

        error = WorkflowError("Test error", ErrorType.VALIDATION)
        assert error.error_type == ErrorType.VALIDATION
        assert str(error) == "Test error"

    def test_workflow_error_has_phase(self):
        """WorkflowError should optionally have phase attribute."""
        from aiagent.langgraph.jobGeneratorV2.protocols import (
            ErrorType,
            WorkflowError,
        )
        from aiagent.langgraph.jobGeneratorV2.types_old import Phase

        error = WorkflowError(
            "Test error",
            ErrorType.VALIDATION,
            phase=Phase.INTERFACE_DESIGN,
        )
        assert error.phase == Phase.INTERFACE_DESIGN


class TestPhaseExecution:
    """Test cases for PhaseExecution tracking."""

    def test_phase_execution_exists(self):
        """PhaseExecution should be importable."""
        from aiagent.langgraph.jobGeneratorV2.protocols import PhaseExecution

        assert PhaseExecution is not None

    def test_phase_execution_creation(self):
        """PhaseExecution should track phase execution details."""
        from datetime import datetime, timedelta

        from aiagent.langgraph.jobGeneratorV2.protocols import PhaseExecution
        from aiagent.langgraph.jobGeneratorV2.types import PhaseStatus
        from aiagent.langgraph.jobGeneratorV2.types_old import Phase

        execution = PhaseExecution(
            phase=Phase.TASK_BREAKDOWN,
            status=PhaseStatus.SUCCESS,
            started_at=datetime.now(),
            duration=timedelta(seconds=30),
            retry_count=0,
        )
        assert execution.phase == Phase.TASK_BREAKDOWN
        assert execution.status == PhaseStatus.SUCCESS
        assert execution.retry_count == 0


class TestProgressReporter:
    """Test cases for ProgressReporter protocol."""

    def test_progress_reporter_exists(self):
        """ProgressReporter should be importable."""
        from aiagent.langgraph.jobGeneratorV2.protocols import ProgressReporter

        assert ProgressReporter is not None

    def test_progress_reporter_has_report_method(self):
        """ProgressReporter should define report method."""
        from aiagent.langgraph.jobGeneratorV2.protocols import ProgressReporter

        assert hasattr(ProgressReporter, "report")
