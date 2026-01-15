"""Unit tests for Job Generator V2 orchestrator module.

Tests for JobGenerationOrchestrator.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestJobGenerationOrchestrator:
    """Test cases for JobGenerationOrchestrator."""

    def test_orchestrator_exists(self):
        """JobGenerationOrchestrator should be importable."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator_old import (
            JobGenerationOrchestrator,
        )

        assert JobGenerationOrchestrator is not None

    def test_orchestrator_creation(self):
        """JobGenerationOrchestrator should be creatable."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator_old import (
            JobGenerationOrchestrator,
        )
        from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryManager

        recovery_manager = ErrorRecoveryManager()
        orchestrator = JobGenerationOrchestrator(recovery_manager=recovery_manager)
        assert orchestrator is not None

    def test_orchestrator_has_recovery_manager(self):
        """Orchestrator should have a recovery manager."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator_old import (
            JobGenerationOrchestrator,
        )
        from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryManager

        recovery_manager = ErrorRecoveryManager()
        orchestrator = JobGenerationOrchestrator(recovery_manager=recovery_manager)
        assert orchestrator.recovery_manager is recovery_manager

    def test_orchestrator_registers_workflows(self):
        """Orchestrator should allow registering workflows for each phase."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator_old import (
            JobGenerationOrchestrator,
        )
        from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryManager
        from aiagent.langgraph.jobGeneratorV2.types_old import Phase

        orchestrator = JobGenerationOrchestrator(
            recovery_manager=ErrorRecoveryManager()
        )

        # Create a mock workflow
        mock_workflow = MagicMock()

        # Register it
        orchestrator.register_workflow(Phase.TASK_BREAKDOWN, mock_workflow)

        # Should be registered
        assert orchestrator.get_workflow(Phase.TASK_BREAKDOWN) is mock_workflow


class TestOrchestratorExecutePhase:
    """Test cases for execute_phase method."""

    @pytest.mark.asyncio
    async def test_execute_phase_success(self):
        """execute_phase should return output on success."""
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
        from aiagent.langgraph.jobGeneratorV2.orchestrator_old import (
            JobGenerationOrchestrator,
        )
        from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryManager
        from aiagent.langgraph.jobGeneratorV2.types_old import Phase, PhaseStatus

        orchestrator = JobGenerationOrchestrator(
            recovery_manager=ErrorRecoveryManager()
        )

        # Create a mock workflow that succeeds
        mock_output = MagicMock()
        mock_output.status = PhaseStatus.SUCCESS
        mock_workflow = AsyncMock()
        mock_workflow.execute = AsyncMock(return_value=mock_output)
        mock_workflow.get_retry_policy = MagicMock(
            return_value=MagicMock(max_retries=3)
        )

        orchestrator.register_workflow(Phase.TASK_BREAKDOWN, mock_workflow)

        context = ExecutionContext(
            job_id="test-job",
            user_requirement="Test requirement",
        )

        result = await orchestrator.execute_phase(
            phase=Phase.TASK_BREAKDOWN,
            input=MagicMock(),
            context=context,
        )

        assert result == mock_output

    @pytest.mark.asyncio
    async def test_execute_phase_with_retry(self):
        """execute_phase should retry on recoverable error."""
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
        from aiagent.langgraph.jobGeneratorV2.orchestrator_old import (
            JobGenerationOrchestrator,
        )
        from aiagent.langgraph.jobGeneratorV2.protocols import ErrorType, WorkflowError
        from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryManager
        from aiagent.langgraph.jobGeneratorV2.types_old import Phase, PhaseStatus

        orchestrator = JobGenerationOrchestrator(
            recovery_manager=ErrorRecoveryManager()
        )

        # First call fails, second succeeds
        mock_output = MagicMock()
        mock_output.status = PhaseStatus.SUCCESS
        mock_workflow = AsyncMock()
        mock_workflow.execute = AsyncMock(
            side_effect=[
                WorkflowError("Validation failed", ErrorType.VALIDATION),
                mock_output,
            ]
        )
        mock_workflow.get_retry_policy = MagicMock(
            return_value=MagicMock(max_retries=3)
        )

        orchestrator.register_workflow(Phase.TASK_BREAKDOWN, mock_workflow)

        context = ExecutionContext(
            job_id="test-job",
            user_requirement="Test requirement",
        )

        result = await orchestrator.execute_phase(
            phase=Phase.TASK_BREAKDOWN,
            input=MagicMock(),
            context=context,
        )

        # Should have succeeded after retry
        assert result == mock_output
        # Retry should have been recorded
        assert context.get_phase_retry_state(Phase.TASK_BREAKDOWN).count == 1


class TestOrchestratorRunWorkflow:
    """Test cases for run_workflow method."""

    @pytest.mark.asyncio
    async def test_run_workflow_all_phases(self):
        """run_workflow should execute all phases in order."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator_old import (
            JobGenerationOrchestrator,
        )
        from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryManager
        from aiagent.langgraph.jobGeneratorV2.types_old import (
            InterfaceDesignOutput,
            InterfaceSchema,
            JobGenerationRequest,
            JobGenerationResult,
            Phase,
            PhaseStatus,
            RegistrationOutput,
            TaskBreakdownOutput,
            TaskDefinition,
            WorkflowGenOutput,
        )

        orchestrator = JobGenerationOrchestrator(
            recovery_manager=ErrorRecoveryManager()
        )

        # Create proper mock outputs for each phase
        # Issue #342 Bug #1: Tests must provide proper data for TaskIdMapping
        task = TaskDefinition(
            id="task_001",
            name="Test Task",
            description="Test description",
            task_type="fetch",
            recommended_api="fetchAgent",
        )

        interface = InterfaceSchema(
            task_id="task_001",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )

        # TaskBreakdown output with actual tasks
        breakdown_output = TaskBreakdownOutput(
            status=PhaseStatus.SUCCESS,
            tasks=[task],
        )

        # InterfaceDesign output with interfaces
        interface_output = InterfaceDesignOutput(
            status=PhaseStatus.SUCCESS,
            interfaces={"task_001": interface},
        )

        # Registration output with task_id_to_master_id mapping
        registration_output = RegistrationOutput(
            status=PhaseStatus.SUCCESS,
            job_master_id="jm_001",
            task_master_ids=["tm_task_001"],
            job_id="job_001",
            task_id_to_master_id={"task_001": "tm_task_001"},  # Bug #1 fix
        )

        # WorkflowGen output (single task)
        workflow_output = WorkflowGenOutput(
            status=PhaseStatus.SUCCESS,
            task_id="task_001",
            workflow_yaml="version: '0.6'\nnodes: {}",
        )

        # Create mock workflows for each phase with proper outputs
        phase_outputs = {
            Phase.TASK_BREAKDOWN: breakdown_output,
            Phase.INTERFACE_DESIGN: interface_output,
            Phase.REGISTRATION: registration_output,
            Phase.WORKFLOW_GEN: workflow_output,
        }

        for phase in Phase:
            mock_workflow = AsyncMock()
            mock_workflow.execute = AsyncMock(return_value=phase_outputs[phase])
            mock_workflow.get_retry_policy = MagicMock(
                return_value=MagicMock(max_retries=3)
            )
            orchestrator.register_workflow(phase, mock_workflow)

        request = JobGenerationRequest(
            user_requirement="Test requirement",
            project_id="test-project",
        )

        result = await orchestrator.run_workflow(request)

        assert isinstance(result, JobGenerationResult)
        # First 3 phases should have been called directly
        for phase in [Phase.TASK_BREAKDOWN, Phase.INTERFACE_DESIGN, Phase.REGISTRATION]:
            workflow = orchestrator.get_workflow(phase)
            assert workflow.execute.called, (
                f"Phase {phase.value} execute should be called"
            )

        # WORKFLOW_GEN is called per-task via _execute_workflow_gen_per_task
        workflow_gen = orchestrator.get_workflow(Phase.WORKFLOW_GEN)
        assert workflow_gen.execute.called, "WORKFLOW_GEN execute should be called"


class TestOrchestratorPhaseOrder:
    """Test cases for phase ordering."""

    def test_get_phase_order(self):
        """get_phase_order should return phases in correct order."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator_old import (
            JobGenerationOrchestrator,
        )
        from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryManager
        from aiagent.langgraph.jobGeneratorV2.types_old import Phase

        orchestrator = JobGenerationOrchestrator(
            recovery_manager=ErrorRecoveryManager()
        )

        order = orchestrator.get_phase_order()

        assert order == [
            Phase.TASK_BREAKDOWN,
            Phase.INTERFACE_DESIGN,
            Phase.REGISTRATION,
            Phase.WORKFLOW_GEN,
        ]

    def test_get_next_phase(self):
        """get_next_phase should return the next phase."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator_old import (
            JobGenerationOrchestrator,
        )
        from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryManager
        from aiagent.langgraph.jobGeneratorV2.types_old import Phase

        orchestrator = JobGenerationOrchestrator(
            recovery_manager=ErrorRecoveryManager()
        )

        assert (
            orchestrator.get_next_phase(Phase.TASK_BREAKDOWN) == Phase.INTERFACE_DESIGN
        )
        assert orchestrator.get_next_phase(Phase.INTERFACE_DESIGN) == Phase.REGISTRATION
        assert orchestrator.get_next_phase(Phase.REGISTRATION) == Phase.WORKFLOW_GEN
        assert orchestrator.get_next_phase(Phase.WORKFLOW_GEN) is None


class TestOrchestratorRecovery:
    """Test cases for error recovery in orchestrator."""

    @pytest.mark.asyncio
    async def test_orchestrator_uses_recovery_manager(self):
        """Orchestrator should use recovery manager for error handling."""
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
        from aiagent.langgraph.jobGeneratorV2.orchestrator_old import (
            JobGenerationOrchestrator,
        )
        from aiagent.langgraph.jobGeneratorV2.protocols import ErrorType, WorkflowError
        from aiagent.langgraph.jobGeneratorV2.recovery import (
            ErrorRecoveryDecision,
            ErrorRecoveryManager,
            ErrorRecoveryStrategy,
        )
        from aiagent.langgraph.jobGeneratorV2.types_old import Phase

        # Mock recovery manager
        mock_recovery = MagicMock(spec=ErrorRecoveryManager)
        mock_recovery.decide_recovery.return_value = ErrorRecoveryDecision(
            strategy=ErrorRecoveryStrategy.FAIL_FAST,
            feedback="Fatal error",
            should_notify_user=True,
        )

        orchestrator = JobGenerationOrchestrator(recovery_manager=mock_recovery)

        # Create a workflow that fails with fatal error
        mock_workflow = AsyncMock()
        mock_workflow.execute = AsyncMock(
            side_effect=WorkflowError("Database error", ErrorType.FATAL)
        )
        mock_workflow.get_retry_policy = MagicMock(
            return_value=MagicMock(max_retries=3)
        )

        orchestrator.register_workflow(Phase.REGISTRATION, mock_workflow)

        context = ExecutionContext(
            job_id="test-job",
            user_requirement="Test",
        )

        # Should use recovery manager
        with pytest.raises(WorkflowError):
            await orchestrator.execute_phase(
                phase=Phase.REGISTRATION,
                input=MagicMock(),
                context=context,
            )

        # Recovery manager should have been called
        mock_recovery.decide_recovery.assert_called()
