"""Unit tests for Job Generator V2 types module.

Tests for Phase, PhaseStatus, RetryState, and related types.
"""

import pytest
from datetime import datetime


class TestPhaseEnum:
    """Test cases for Phase enum."""

    def test_phase_enum_exists(self):
        """Phase enum should be importable."""
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        assert Phase is not None

    def test_phase_has_four_values(self):
        """Phase enum should have exactly 4 phases."""
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        assert len(list(Phase)) == 4

    def test_phase_values(self):
        """Phase enum should have correct values."""
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        assert Phase.TASK_BREAKDOWN.value == "task_breakdown"
        assert Phase.INTERFACE_DESIGN.value == "interface_design"
        assert Phase.REGISTRATION.value == "registration"
        assert Phase.WORKFLOW_GEN.value == "workflow_gen"


class TestPhaseStatusEnum:
    """Test cases for PhaseStatus enum."""

    def test_phase_status_enum_exists(self):
        """PhaseStatus enum should be importable."""
        from aiagent.langgraph.jobGeneratorV2.types import PhaseStatus

        assert PhaseStatus is not None

    def test_phase_status_values(self):
        """PhaseStatus enum should have correct values."""
        from aiagent.langgraph.jobGeneratorV2.types import PhaseStatus

        assert PhaseStatus.SUCCESS.value == "success"
        assert PhaseStatus.FAILED.value == "failed"
        assert PhaseStatus.NEEDS_RETRY.value == "needs_retry"
        assert PhaseStatus.NEEDS_RELAXATION.value == "needs_relaxation"


class TestRetryAttempt:
    """Test cases for RetryAttempt dataclass."""

    def test_retry_attempt_exists(self):
        """RetryAttempt should be importable."""
        from aiagent.langgraph.jobGeneratorV2.types import RetryAttempt

        assert RetryAttempt is not None

    def test_retry_attempt_creation(self):
        """RetryAttempt should be creatable with required fields."""
        from aiagent.langgraph.jobGeneratorV2.types import RetryAttempt

        attempt = RetryAttempt(
            attempt=1,
            reason="Test retry",
            error=None,
            timestamp=datetime.now(),
        )
        assert attempt.attempt == 1
        assert attempt.reason == "Test retry"
        assert attempt.error is None

    def test_retry_attempt_with_error(self):
        """RetryAttempt should store error string."""
        from aiagent.langgraph.jobGeneratorV2.types import RetryAttempt

        attempt = RetryAttempt(
            attempt=2,
            reason="Validation failed",
            error="Schema validation error",
            timestamp=datetime.now(),
        )
        assert attempt.error == "Schema validation error"


class TestRetryState:
    """Test cases for RetryState dataclass."""

    def test_retry_state_exists(self):
        """RetryState should be importable."""
        from aiagent.langgraph.jobGeneratorV2.types import RetryState

        assert RetryState is not None

    def test_retry_state_default_values(self):
        """RetryState should have sensible defaults."""
        from aiagent.langgraph.jobGeneratorV2.types import RetryState

        state = RetryState()
        assert state.count == 0
        assert state.max_count == 3
        assert state.history == []

    def test_can_retry_when_under_limit(self):
        """can_retry should return True when count < max_count."""
        from aiagent.langgraph.jobGeneratorV2.types import RetryState

        state = RetryState(count=0, max_count=3)
        assert state.can_retry() is True

        state = RetryState(count=2, max_count=3)
        assert state.can_retry() is True

    def test_cannot_retry_when_at_limit(self):
        """can_retry should return False when count >= max_count."""
        from aiagent.langgraph.jobGeneratorV2.types import RetryState

        state = RetryState(count=3, max_count=3)
        assert state.can_retry() is False

        state = RetryState(count=5, max_count=3)
        assert state.can_retry() is False

    def test_record_increments_count(self):
        """record should increment count and add to history."""
        from aiagent.langgraph.jobGeneratorV2.types import RetryState

        state = RetryState()
        assert state.count == 0

        state.record("First retry reason")
        assert state.count == 1
        assert len(state.history) == 1
        assert state.history[0].reason == "First retry reason"
        assert state.history[0].attempt == 1

    def test_record_with_error(self):
        """record should store error in history."""
        from aiagent.langgraph.jobGeneratorV2.types import RetryState

        state = RetryState()
        error = ValueError("Test error")
        state.record("Error occurred", error)

        assert state.history[0].error == "Test error"


class TestTaskDefinition:
    """Test cases for TaskDefinition dataclass."""

    def test_task_definition_exists(self):
        """TaskDefinition should be importable."""
        from aiagent.langgraph.jobGeneratorV2.types import TaskDefinition

        assert TaskDefinition is not None

    def test_task_definition_creation(self):
        """TaskDefinition should be creatable with required fields."""
        from aiagent.langgraph.jobGeneratorV2.types import TaskDefinition

        task = TaskDefinition(
            id="task_1",
            name="Fetch emails",
            description="Fetch unread emails from Gmail",
            task_type="fetch",
            recommended_api="/v1/utility/gmail/fetch",
            priority=1,
        )
        assert task.id == "task_1"
        assert task.name == "Fetch emails"


class TestJobGenerationRequest:
    """Test cases for JobGenerationRequest dataclass."""

    def test_request_exists(self):
        """JobGenerationRequest should be importable."""
        from aiagent.langgraph.jobGeneratorV2.types import (
            JobGenerationRequest,
        )

        assert JobGenerationRequest is not None

    def test_request_creation(self):
        """JobGenerationRequest should be creatable."""
        from aiagent.langgraph.jobGeneratorV2.types import (
            JobGenerationRequest,
        )

        request = JobGenerationRequest(
            user_requirement="Fetch emails and send summary",
            project_id="test_project",
        )
        assert request.user_requirement == "Fetch emails and send summary"
        assert request.project_id == "test_project"


class TestCapability:
    """Test cases for Capability dataclass."""

    def test_capability_exists(self):
        """Capability should be importable."""
        from aiagent.langgraph.jobGeneratorV2.types import Capability

        assert Capability is not None


class TestInterfaceSchema:
    """Test cases for InterfaceSchema dataclass."""

    def test_interface_schema_exists(self):
        """InterfaceSchema should be importable."""
        from aiagent.langgraph.jobGeneratorV2.types import InterfaceSchema

        assert InterfaceSchema is not None

    def test_interface_schema_creation(self):
        """InterfaceSchema should be creatable."""
        from aiagent.langgraph.jobGeneratorV2.types import InterfaceSchema

        schema = InterfaceSchema(
            task_id="task_1",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object", "properties": {}},
        )
        assert schema.task_id == "task_1"


class TestPhaseInput:
    """Test cases for phase input types."""

    def test_task_breakdown_input_exists(self):
        """TaskBreakdownInput should be importable."""
        from aiagent.langgraph.jobGeneratorV2.types import TaskBreakdownInput

        assert TaskBreakdownInput is not None

    def test_interface_design_input_exists(self):
        """InterfaceDesignInput should be importable."""
        from aiagent.langgraph.jobGeneratorV2.types import (
            InterfaceDesignInput,
        )

        assert InterfaceDesignInput is not None

    def test_registration_input_exists(self):
        """RegistrationInput should be importable."""
        from aiagent.langgraph.jobGeneratorV2.types import RegistrationInput

        assert RegistrationInput is not None

    def test_workflow_gen_input_exists(self):
        """WorkflowGenInput should be importable."""
        from aiagent.langgraph.jobGeneratorV2.types import WorkflowGenInput

        assert WorkflowGenInput is not None


class TestPhaseOutput:
    """Test cases for phase output types."""

    def test_task_breakdown_output_exists(self):
        """TaskBreakdownOutput should be importable."""
        from aiagent.langgraph.jobGeneratorV2.types import (
            TaskBreakdownOutput,
        )

        assert TaskBreakdownOutput is not None

    def test_interface_design_output_exists(self):
        """InterfaceDesignOutput should be importable."""
        from aiagent.langgraph.jobGeneratorV2.types import (
            InterfaceDesignOutput,
        )

        assert InterfaceDesignOutput is not None

    def test_registration_output_exists(self):
        """RegistrationOutput should be importable."""
        from aiagent.langgraph.jobGeneratorV2.types import RegistrationOutput

        assert RegistrationOutput is not None

    def test_workflow_gen_output_exists(self):
        """WorkflowGenOutput should be importable."""
        from aiagent.langgraph.jobGeneratorV2.types import WorkflowGenOutput

        assert WorkflowGenOutput is not None


class TestTaskBreakdownOutput:
    """Test cases for TaskBreakdownOutput status handling."""

    def test_task_breakdown_output_success_status(self):
        """TaskBreakdownOutput should support SUCCESS status."""
        from aiagent.langgraph.jobGeneratorV2.types import (
            PhaseStatus,
            TaskBreakdownOutput,
        )

        output = TaskBreakdownOutput(
            status=PhaseStatus.SUCCESS,
            tasks=[],
            feasibility_report=None,
        )
        assert output.status == PhaseStatus.SUCCESS

    def test_task_breakdown_output_needs_relaxation(self):
        """TaskBreakdownOutput should support NEEDS_RELAXATION status."""
        from aiagent.langgraph.jobGeneratorV2.types import (
            PhaseStatus,
            TaskBreakdownOutput,
            RelaxationSuggestion,
        )

        suggestion = RelaxationSuggestion(
            original_requirement="Complex task",
            suggested_alternative="Simplified task",
            reason="Too complex for available APIs",
        )
        output = TaskBreakdownOutput(
            status=PhaseStatus.NEEDS_RELAXATION,
            tasks=[],
            feasibility_report=None,
            relaxation_suggestions=[suggestion],
        )
        assert output.status == PhaseStatus.NEEDS_RELAXATION
        assert len(output.relaxation_suggestions) == 1
