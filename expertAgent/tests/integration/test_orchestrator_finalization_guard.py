"""Integration tests for Orchestrator finalization guard.

Issue #353: Tests for _can_proceed_to_finalization method and
INCOMPLETE_WORKFLOW error handling.
"""

from unittest.mock import MagicMock

import pytest

from aiagent.langgraph.jobGeneratorV2.context import ContextBuilder
from aiagent.langgraph.jobGeneratorV2.orchestrator import JobGenerationOrchestrator
from aiagent.langgraph.jobGeneratorV2.protocols import ErrorType
from aiagent.langgraph.jobGeneratorV2.recovery import (
    ErrorRecoveryManager,
    ErrorRecoveryStrategy,
)
from aiagent.langgraph.jobGeneratorV2.types import (
    Phase,
    PhaseStatus,
    RegistrationOutput,
    TaskBreakdownOutput,
    TaskDefinition,
    WorkflowGenOutput,
    WorkflowGenPhaseOutput,
)


class TestCanProceedToFinalization:
    """Tests for _can_proceed_to_finalization method."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.recovery_manager = ErrorRecoveryManager()
        self.orchestrator = JobGenerationOrchestrator(
            recovery_manager=self.recovery_manager,
        )

    @pytest.mark.asyncio
    async def test_can_proceed_all_workflows_complete(self) -> None:
        """Should allow finalization when all workflows are complete."""
        # Create phase outputs with complete workflows
        task_breakdown = TaskBreakdownOutput(
            status=PhaseStatus.SUCCESS,
            tasks=[
                TaskDefinition(
                    id="task_001",
                    name="Task 1",
                    description="Test task 1",
                    task_type="fetch",
                    recommended_api="/api/test",
                ),
                TaskDefinition(
                    id="task_002",
                    name="Task 2",
                    description="Test task 2",
                    task_type="transform",
                    recommended_api="/api/transform",
                ),
            ],
        )

        registration = RegistrationOutput(
            status=PhaseStatus.SUCCESS,
            job_master_id="jm_001",
            task_master_ids=["tm_001", "tm_002"],
        )

        workflow_gen = WorkflowGenPhaseOutput(
            status=PhaseStatus.SUCCESS,
            task_workflows={
                "task_001": WorkflowGenOutput(
                    status=PhaseStatus.SUCCESS,
                    task_id="task_001",
                    workflow_yaml="nodes: []",
                ),
                "task_002": WorkflowGenOutput(
                    status=PhaseStatus.SUCCESS,
                    task_id="task_002",
                    workflow_yaml="nodes: []",
                ),
            },
        )

        phase_outputs = {
            Phase.TASK_BREAKDOWN: task_breakdown,
            Phase.REGISTRATION: registration,
            Phase.WORKFLOW_GEN: workflow_gen,
        }

        context = (
            ContextBuilder()
            .with_job_id("test-job-001")
            .with_user_requirement("Test requirement")
            .build()
        )

        can_proceed, error_msg = await self.orchestrator._can_proceed_to_finalization(
            phase_outputs=phase_outputs,
            context=context,
        )

        assert can_proceed is True
        assert error_msg is None

    @pytest.mark.asyncio
    async def test_cannot_proceed_with_pending_workflows(self) -> None:
        """Should block finalization when __PENDING__ workflows exist."""
        task_breakdown = TaskBreakdownOutput(
            status=PhaseStatus.SUCCESS,
            tasks=[
                TaskDefinition(
                    id="task_001",
                    name="Task 1",
                    description="Test task 1",
                    task_type="fetch",
                    recommended_api="/api/test",
                ),
            ],
        )

        registration = RegistrationOutput(
            status=PhaseStatus.SUCCESS,
            job_master_id="jm_001",
            task_master_ids=["tm_001"],
        )

        # Workflow with __PENDING__ (no workflow_yaml means incomplete)
        workflow_gen = WorkflowGenPhaseOutput(
            status=PhaseStatus.FAILED,
            task_workflows={
                "task_001": WorkflowGenOutput(
                    status=PhaseStatus.FAILED,
                    task_id="task_001",
                    workflow_yaml=None,  # __PENDING__ equivalent
                ),
            },
        )

        phase_outputs = {
            Phase.TASK_BREAKDOWN: task_breakdown,
            Phase.REGISTRATION: registration,
            Phase.WORKFLOW_GEN: workflow_gen,
        }

        context = (
            ContextBuilder()
            .with_job_id("test-job-002")
            .with_user_requirement("Test requirement")
            .build()
        )

        can_proceed, error_msg = await self.orchestrator._can_proceed_to_finalization(
            phase_outputs=phase_outputs,
            context=context,
        )

        assert can_proceed is False
        assert error_msg is not None
        assert "task_001" in error_msg or "incomplete" in error_msg.lower()


class TestIncompleteWorkflowErrorRecovery:
    """Tests for INCOMPLETE_WORKFLOW error handling in recovery manager."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.recovery_manager = ErrorRecoveryManager()

    def test_incomplete_workflow_error_handled(self) -> None:
        """INCOMPLETE_WORKFLOW errors should trigger appropriate recovery."""
        from aiagent.langgraph.jobGeneratorV2.protocols import WorkflowError

        error = WorkflowError(
            message="WORKFLOW_GEN phase incomplete: 2 tasks have __PENDING__",
            error_type=ErrorType.INCOMPLETE_WORKFLOW,
            phase=Phase.WORKFLOW_GEN,
            details={"pending_count": 2},
        )

        context = MagicMock()
        context.can_retry.return_value = True
        context.get_rollback_count.return_value = 0

        decision = self.recovery_manager.decide_recovery(
            phase=Phase.WORKFLOW_GEN,
            error=error,
            context=context,
        )

        # INCOMPLETE_WORKFLOW should be retriable (like TRANSIENT/VALIDATION)
        assert decision.strategy in (
            ErrorRecoveryStrategy.RETRY_CURRENT,
            ErrorRecoveryStrategy.FAIL_FAST,
        )
        assert decision.should_notify_user is True

    def test_incomplete_workflow_after_max_retries(self) -> None:
        """Should fail fast after max retries for INCOMPLETE_WORKFLOW."""
        from aiagent.langgraph.jobGeneratorV2.protocols import WorkflowError

        error = WorkflowError(
            message="WORKFLOW_GEN phase incomplete",
            error_type=ErrorType.INCOMPLETE_WORKFLOW,
            phase=Phase.WORKFLOW_GEN,
        )

        context = MagicMock()
        context.can_retry.return_value = False  # Max retries reached
        context.get_rollback_count.return_value = 2  # Max rollbacks also reached

        decision = self.recovery_manager.decide_recovery(
            phase=Phase.WORKFLOW_GEN,
            error=error,
            context=context,
        )

        assert decision.strategy == ErrorRecoveryStrategy.FAIL_FAST
        assert decision.should_notify_user is True
