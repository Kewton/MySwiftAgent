"""Integration tests for Job Generator V2.

Tests the full workflow from Orchestrator through all 4 workflow phases
with mocked external services.

Issue #342 Phase E.1: Integration tests for V2 architecture.

Run these tests with:
    cd expertAgent
    uv run pytest tests/integration/test_job_generator_v2_integration.py -v
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestJobGeneratorV2Integration:
    """Integration tests for Job Generator V2 full workflow."""

    @pytest.fixture
    def mock_llm_response(self):
        """Create a mock LLM response for task breakdown."""
        from aiagent.langgraph.jobGeneratorV2.types import TaskBreakdownResponse

        return TaskBreakdownResponse(
            tasks=[
                {
                    "task_id": "task_001",
                    "name": "Search Gmail",
                    "description": "Search Gmail for recent emails",
                    "dependencies": [],
                    "expected_output": "List of email messages",
                    "priority": 1,
                    "recommended_apis": [],
                }
            ],
            overall_summary="Email search workflow",
            job_body_parameters=[],
        )

    @pytest.fixture
    def mock_interface_response(self):
        """Create a mock LLM response for interface design."""
        from aiagent.langgraph.jobGeneratorV2.types import InterfaceSchemaResponse

        return InterfaceSchemaResponse(
            interfaces=[
                {
                    "task_id": "task_001",
                    "interface_name": "gmail_search_interface",
                    "description": "Interface for Gmail search",
                    "input_schema": {
                        "type": "object",
                        "properties": {"query": {"type": "string"}},
                        "required": ["query"],
                    },
                    "output_schema": {
                        "type": "object",
                        "properties": {"messages": {"type": "array"}},
                    },
                    "derived_fields": {},
                }
            ]
        )

    def test_orchestrator_phase_order(self):
        """Orchestrator should execute phases in correct order."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )
        from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryManager
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        recovery_manager = ErrorRecoveryManager()
        orchestrator = JobGenerationOrchestrator(recovery_manager=recovery_manager)

        order = orchestrator.get_phase_order()
        assert order == [
            Phase.TASK_BREAKDOWN,
            Phase.INTERFACE_DESIGN,
            Phase.REGISTRATION,
            Phase.WORKFLOW_GEN,
        ]

    @pytest.mark.asyncio
    async def test_full_workflow_with_mocked_services(self):
        """Test full workflow execution with mocked external services."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )
        from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryManager
        from aiagent.langgraph.jobGeneratorV2.types import (
            InterfaceSchema,
            JobGenerationRequest,
            Phase,
            PhaseStatus,
            TaskDefinition,
        )

        recovery_manager = ErrorRecoveryManager()
        orchestrator = JobGenerationOrchestrator(recovery_manager=recovery_manager)

        # Create mock workflows for each phase
        # TaskBreakdown mock
        breakdown_output = MagicMock()
        breakdown_output.status = PhaseStatus.SUCCESS
        breakdown_output.tasks = [
            TaskDefinition(
                id="task_001",
                name="Search Gmail",
                description="Search for emails",
                task_type="fetch",
                recommended_api="/v1/utility/gmail/search",
                priority=1,
                dependencies=[],
            )
        ]
        breakdown_output.relaxation_suggestions = []
        breakdown_workflow = AsyncMock()
        breakdown_workflow.execute = AsyncMock(return_value=breakdown_output)
        breakdown_workflow.get_retry_policy = MagicMock(
            return_value=MagicMock(max_retries=3)
        )

        # InterfaceDesign mock
        interface_output = MagicMock()
        interface_output.status = PhaseStatus.SUCCESS
        interface_output.interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                description="Gmail search interface",
            )
        }
        interface_workflow = AsyncMock()
        interface_workflow.execute = AsyncMock(return_value=interface_output)
        interface_workflow.get_retry_policy = MagicMock(
            return_value=MagicMock(max_retries=3)
        )

        # Registration mock
        registration_output = MagicMock()
        registration_output.status = PhaseStatus.SUCCESS
        registration_output.job_master_id = "jm_test123"
        registration_output.task_master_ids = ["tm_test001"]
        registration_output.interface_master_ids = ["im_test001"]
        registration_output.job_id = "job_test123"
        registration_workflow = AsyncMock()
        registration_workflow.execute = AsyncMock(return_value=registration_output)
        registration_workflow.get_retry_policy = MagicMock(
            return_value=MagicMock(max_retries=3)
        )

        # WorkflowGen mock
        workflow_gen_output = MagicMock()
        workflow_gen_output.status = PhaseStatus.SUCCESS
        workflow_gen_output.workflow_yaml = "version: 0.6\nnodes: {}"
        workflow_gen_output.test_result = {"validation": "passed"}
        workflow_gen_workflow = AsyncMock()
        workflow_gen_workflow.execute = AsyncMock(return_value=workflow_gen_output)
        workflow_gen_workflow.get_retry_policy = MagicMock(
            return_value=MagicMock(max_retries=3)
        )

        # Register workflows
        orchestrator.register_workflow(Phase.TASK_BREAKDOWN, breakdown_workflow)
        orchestrator.register_workflow(Phase.INTERFACE_DESIGN, interface_workflow)
        orchestrator.register_workflow(Phase.REGISTRATION, registration_workflow)
        orchestrator.register_workflow(Phase.WORKFLOW_GEN, workflow_gen_workflow)

        # Create request
        request = JobGenerationRequest(
            user_requirement="Search Gmail for recent emails",
            project_id="test-project",
            max_tasks=5,
        )

        # Execute workflow
        result = await orchestrator.run_workflow(request)

        # Verify result
        assert result.success is True
        assert result.job_master_id == "jm_test123"
        assert result.task_master_ids == ["tm_test001"]
        assert result.workflow_yaml == "version: 0.6\nnodes: {}"

        # Verify all workflows were called
        breakdown_workflow.execute.assert_called_once()
        interface_workflow.execute.assert_called_once()
        registration_workflow.execute.assert_called_once()
        workflow_gen_workflow.execute.assert_called_once()


class TestErrorRecoveryIntegration:
    """Integration tests for error recovery scenarios."""

    @pytest.mark.asyncio
    async def test_retry_on_transient_error(self):
        """Orchestrator should retry on transient errors."""
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )
        from aiagent.langgraph.jobGeneratorV2.protocols import ErrorType, WorkflowError
        from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryManager
        from aiagent.langgraph.jobGeneratorV2.types import (
            Phase,
            PhaseStatus,
        )

        recovery_manager = ErrorRecoveryManager()
        orchestrator = JobGenerationOrchestrator(recovery_manager=recovery_manager)

        # Create mock workflow that fails once, then succeeds
        success_output = MagicMock()
        success_output.status = PhaseStatus.SUCCESS
        mock_workflow = AsyncMock()
        mock_workflow.execute = AsyncMock(
            side_effect=[
                WorkflowError("Transient error", ErrorType.TRANSIENT, Phase.TASK_BREAKDOWN),
                success_output,
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

        # Execute phase - should succeed after retry
        result = await orchestrator.execute_phase(
            phase=Phase.TASK_BREAKDOWN,
            input=MagicMock(),
            context=context,
        )

        assert result == success_output
        assert mock_workflow.execute.call_count == 2
        assert context.get_phase_retry_state(Phase.TASK_BREAKDOWN).count == 1

    @pytest.mark.asyncio
    async def test_retry_limit_prevents_infinite_loop(self):
        """Retry limit should prevent infinite loops."""
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )
        from aiagent.langgraph.jobGeneratorV2.protocols import ErrorType, WorkflowError
        from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryManager
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        recovery_manager = ErrorRecoveryManager()
        orchestrator = JobGenerationOrchestrator(recovery_manager=recovery_manager)

        # Create mock workflow that always fails
        mock_workflow = AsyncMock()
        mock_workflow.execute = AsyncMock(
            side_effect=WorkflowError(
                "Always failing",
                ErrorType.TRANSIENT,
                Phase.TASK_BREAKDOWN,
            )
        )
        mock_workflow.get_retry_policy = MagicMock(
            return_value=MagicMock(max_retries=3)
        )

        orchestrator.register_workflow(Phase.TASK_BREAKDOWN, mock_workflow)

        context = ExecutionContext(
            job_id="test-job",
            user_requirement="Test requirement",
            max_phase_retries=3,  # Max 3 retries per phase
        )

        # Execute phase - should fail after 4 attempts (initial + 3 retries)
        with pytest.raises(WorkflowError):
            await orchestrator.execute_phase(
                phase=Phase.TASK_BREAKDOWN,
                input=MagicMock(),
                context=context,
            )

        # Verify retry limit was respected
        assert mock_workflow.execute.call_count == 4  # 1 initial + 3 retries
        assert context.get_phase_retry_state(Phase.TASK_BREAKDOWN).count == 3

    @pytest.mark.asyncio
    async def test_fatal_error_no_retry(self):
        """Fatal errors should not trigger retry."""
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )
        from aiagent.langgraph.jobGeneratorV2.protocols import ErrorType, WorkflowError
        from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryManager
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        recovery_manager = ErrorRecoveryManager()
        orchestrator = JobGenerationOrchestrator(recovery_manager=recovery_manager)

        # Create mock workflow that fails with fatal error
        mock_workflow = AsyncMock()
        mock_workflow.execute = AsyncMock(
            side_effect=WorkflowError(
                "Fatal database error",
                ErrorType.FATAL,
                Phase.REGISTRATION,
            )
        )
        mock_workflow.get_retry_policy = MagicMock(
            return_value=MagicMock(max_retries=3)
        )

        orchestrator.register_workflow(Phase.REGISTRATION, mock_workflow)

        context = ExecutionContext(
            job_id="test-job",
            user_requirement="Test requirement",
        )

        # Execute phase - should fail immediately without retry
        with pytest.raises(WorkflowError) as exc_info:
            await orchestrator.execute_phase(
                phase=Phase.REGISTRATION,
                input=MagicMock(),
                context=context,
            )

        assert "Fatal database error" in str(exc_info.value)
        # Should only be called once (no retry)
        assert mock_workflow.execute.call_count == 1


class TestAdapterIntegration:
    """Integration tests for V2 adapter."""

    def test_adapter_creates_orchestrator(self):
        """Adapter should create orchestrator with all workflows."""
        from aiagent.langgraph.jobGeneratorV2.adapter import JobGeneratorV2Adapter
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        adapter = JobGeneratorV2Adapter(max_retry=5)

        # Verify orchestrator is created
        assert adapter._orchestrator is not None

        # Verify all workflows are registered
        for phase in Phase:
            workflow = adapter._orchestrator.get_workflow(phase)
            assert workflow is not None, f"Workflow for {phase} should be registered"

    @pytest.mark.asyncio
    async def test_adapter_converts_result_success(self):
        """Adapter should convert successful result to response."""
        from aiagent.langgraph.jobGeneratorV2.adapter import JobGeneratorV2Adapter
        from aiagent.langgraph.jobGeneratorV2.types import JobGenerationResult

        adapter = JobGeneratorV2Adapter(max_retry=5)

        # Create successful result
        result = JobGenerationResult(
            success=True,
            job_id="job_123",
            job_master_id="jm_123",
            task_master_ids=["tm_001"],
            workflow_yaml="version: 0.6",
        )

        # Convert to response
        response = adapter._convert_result(result, "job_123")

        assert response.status == "success"
        assert response.job_id == "job_123"
        assert response.job_master_id == "jm_123"
        assert response.error_message is None

    @pytest.mark.asyncio
    async def test_adapter_converts_result_failure(self):
        """Adapter should convert failed result to response."""
        from aiagent.langgraph.jobGeneratorV2.adapter import JobGeneratorV2Adapter
        from aiagent.langgraph.jobGeneratorV2.types import JobGenerationResult

        adapter = JobGeneratorV2Adapter(max_retry=5)

        # Create failed result
        result = JobGenerationResult(
            success=False,
            error="Requirements could not be satisfied",
        )

        # Convert to response
        response = adapter._convert_result(result, "job_456")

        assert response.status == "failed"
        assert response.job_id == "job_456"
        assert response.error_message == "Requirements could not be satisfied"


class TestFeatureFlagIntegration:
    """Integration tests for feature flag."""

    def test_feature_flag_default_value(self):
        """Feature flag should default to False."""
        # Default should be False (backward compatible)
        # Note: This test may fail if USE_JOB_GENERATOR_V2 is set in env
        import os

        from core.feature_flags import use_job_generator_v2

        if "USE_JOB_GENERATOR_V2" not in os.environ:
            assert use_job_generator_v2() is False

    def test_feature_flag_with_settings(self):
        """Feature flag should read from settings."""
        from core.config import settings

        # Verify setting exists
        assert hasattr(settings, "USE_JOB_GENERATOR_V2")

    @pytest.mark.asyncio
    async def test_feature_flag_controls_v1_v2_switch(self):
        """Feature flag should control V1/V2 switch in API."""
        from core.feature_flags import use_job_generator_v2

        # This test verifies the feature flag function exists and is callable
        result = use_job_generator_v2()
        assert isinstance(result, bool)


class TestContextManagement:
    """Integration tests for context management."""

    def test_context_tracks_per_phase_retries(self):
        """Context should track retries per phase separately."""
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        context = ExecutionContext(
            job_id="test-job",
            user_requirement="Test requirement",
            max_phase_retries=3,
        )

        # Record retries for different phases
        context.record_retry(Phase.TASK_BREAKDOWN, "Error 1")
        context.record_retry(Phase.TASK_BREAKDOWN, "Error 2")
        context.record_retry(Phase.INTERFACE_DESIGN, "Error 3")

        # Check phase-specific counts
        assert context.get_phase_retry_state(Phase.TASK_BREAKDOWN).count == 2
        assert context.get_phase_retry_state(Phase.INTERFACE_DESIGN).count == 1
        assert context.get_phase_retry_state(Phase.REGISTRATION).count == 0
        assert context.get_phase_retry_state(Phase.WORKFLOW_GEN).count == 0

        # Total should be sum of all
        assert context.total_retry_count() == 3

    def test_context_respects_per_phase_limits(self):
        """Context should respect per-phase retry limits."""
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        context = ExecutionContext(
            job_id="test-job",
            user_requirement="Test requirement",
            max_phase_retries=2,
        )

        # Can retry initially
        assert context.can_retry(Phase.TASK_BREAKDOWN) is True

        # After max retries, cannot retry
        context.record_retry(Phase.TASK_BREAKDOWN, "Error 1")
        context.record_retry(Phase.TASK_BREAKDOWN, "Error 2")

        assert context.can_retry(Phase.TASK_BREAKDOWN) is False

        # But other phases can still retry
        assert context.can_retry(Phase.INTERFACE_DESIGN) is True

    def test_context_respects_total_limits(self):
        """Context should respect total retry limits."""
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        context = ExecutionContext(
            job_id="test-job",
            user_requirement="Test requirement",
            max_total_retries=3,
            max_phase_retries=5,
        )

        # Record retries across phases
        context.record_retry(Phase.TASK_BREAKDOWN, "Error 1")
        context.record_retry(Phase.INTERFACE_DESIGN, "Error 2")
        context.record_retry(Phase.REGISTRATION, "Error 3")

        # Total limit reached
        assert context.total_retry_count() == 3
        assert context.can_retry_any() is False

        # No phase can retry anymore (total limit)
        for phase in Phase:
            # Per-phase limits not reached, but total is
            assert context.can_retry(phase) is False
