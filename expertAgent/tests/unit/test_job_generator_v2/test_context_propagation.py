"""Tests for ExecutionContext propagation in Job Generator V2.

Issue #342: Verify that ExecutionContext is properly propagated from
adapter -> orchestrator -> workflows for Langfuse integration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from aiagent.langgraph.jobGeneratorV2.adapter import JobGeneratorV2Adapter
from aiagent.langgraph.jobGeneratorV2.context import (
    ContextBuilder,
    ExecutionContext,
    ObservabilityContext,
)
from aiagent.langgraph.jobGeneratorV2.orchestrator import JobGenerationOrchestrator
from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryManager
from aiagent.langgraph.jobGeneratorV2.types import (
    JobGenerationRequest,
    JobGenerationResult,
    Phase,
    PhaseStatus,
    TaskBreakdownOutput,
    TaskDefinition,
)


class TestOrchestratorContextParameter:
    """Tests for orchestrator.run_workflow() context parameter."""

    def test_run_workflow_accepts_context_parameter(self):
        """run_workflow() should accept an optional context parameter."""
        orchestrator = JobGenerationOrchestrator(
            recovery_manager=ErrorRecoveryManager()
        )

        # Check that run_workflow accepts context parameter
        import inspect
        sig = inspect.signature(orchestrator.run_workflow)
        param_names = list(sig.parameters.keys())

        assert "context" in param_names, (
            "run_workflow() should have a 'context' parameter"
        )

    @pytest.mark.asyncio
    async def test_run_workflow_uses_provided_context(self):
        """run_workflow() should use provided context instead of creating new one."""
        orchestrator = JobGenerationOrchestrator(
            recovery_manager=ErrorRecoveryManager()
        )

        # Create a custom context with a specific job_id
        custom_job_id = "custom-job-id-12345"
        custom_context = (
            ContextBuilder()
            .with_job_id(custom_job_id)
            .with_user_requirement("Test requirement")
            .build()
        )

        # Create a mock workflow that captures the context
        captured_contexts: list[ExecutionContext] = []

        async def capture_context(input_data, context):
            captured_contexts.append(context)
            return TaskBreakdownOutput(
                tasks=[
                    TaskDefinition(
                        id="task_001",
                        name="Test Task",
                        description="Test task",
                        task_type="test",
                        recommended_api="",
                        priority=1,
                        dependencies=[],
                    )
                ],
                status=PhaseStatus.SUCCESS,
            )

        mock_workflow = MagicMock()
        mock_workflow.execute = AsyncMock(side_effect=capture_context)

        orchestrator.register_workflow(Phase.TASK_BREAKDOWN, mock_workflow)

        # Register other workflows to prevent errors (they won't be reached)
        for phase in [Phase.INTERFACE_DESIGN, Phase.REGISTRATION, Phase.WORKFLOW_GEN]:
            mock_wf = MagicMock()
            mock_wf.execute = AsyncMock()
            orchestrator.register_workflow(phase, mock_wf)

        request = JobGenerationRequest(
            user_requirement="Test requirement",
            project_id="test-project",
            max_tasks=5,
        )

        # Run with custom context
        await orchestrator.run_workflow(request, context=custom_context)

        # Verify the custom context was used (not a new one)
        assert len(captured_contexts) > 0
        assert captured_contexts[0].job_id == custom_job_id

    @pytest.mark.asyncio
    async def test_run_workflow_creates_default_context_when_none_provided(self):
        """run_workflow() should create default context when none is provided."""
        orchestrator = JobGenerationOrchestrator(
            recovery_manager=ErrorRecoveryManager()
        )

        # Create a mock workflow that captures the context
        captured_contexts: list[ExecutionContext] = []

        async def capture_context(input_data, context):
            captured_contexts.append(context)
            return TaskBreakdownOutput(
                tasks=[
                    TaskDefinition(
                        id="task_001",
                        name="Test Task",
                        description="Test task",
                        task_type="test",
                        recommended_api="",
                        priority=1,
                        dependencies=[],
                    )
                ],
                status=PhaseStatus.SUCCESS,
            )

        mock_workflow = MagicMock()
        mock_workflow.execute = AsyncMock(side_effect=capture_context)

        orchestrator.register_workflow(Phase.TASK_BREAKDOWN, mock_workflow)

        # Register other workflows
        for phase in [Phase.INTERFACE_DESIGN, Phase.REGISTRATION, Phase.WORKFLOW_GEN]:
            mock_wf = MagicMock()
            mock_wf.execute = AsyncMock()
            orchestrator.register_workflow(phase, mock_wf)

        request = JobGenerationRequest(
            user_requirement="Test requirement",
            project_id="test-project",
            max_tasks=5,
        )

        # Run without providing context
        await orchestrator.run_workflow(request)

        # Verify a context was created (job_id should be a UUID)
        assert len(captured_contexts) > 0
        assert captured_contexts[0].job_id is not None
        # UUID format check
        assert len(captured_contexts[0].job_id) == 36  # UUID string length


class TestAdapterContextPropagation:
    """Tests for adapter passing context to orchestrator."""

    @pytest.mark.asyncio
    async def test_adapter_passes_context_to_orchestrator(self):
        """Adapter should pass the context it creates to orchestrator.run_workflow()."""
        langfuse_handler = MagicMock()
        langfuse_handler.some_property = "test_value"
        # Issue #342: Mock last_trace_id for LangfuseService.extract_trace_id()
        langfuse_handler.last_trace_id = "test-trace-id-12345"

        adapter = JobGeneratorV2Adapter(
            max_retry=3,
            langfuse_handler=langfuse_handler,
        )

        # Mock orchestrator's run_workflow to capture the context
        captured_contexts: list[ExecutionContext | None] = []

        async def mock_run_workflow(request, context=None):
            captured_contexts.append(context)
            return JobGenerationResult(
                success=True,
                job_id="test-job-id",
                job_master_id="test-master-id",
                task_master_ids=["task-1"],
                workflow_yaml="version: 0.6\nnodes: {}\n",
            )

        adapter._orchestrator.run_workflow = mock_run_workflow

        # Call generate
        await adapter.generate(
            user_requirement="Test requirement",
            project_id="test-project",
        )

        # Verify context was passed
        assert len(captured_contexts) == 1
        assert captured_contexts[0] is not None
        assert isinstance(captured_contexts[0], ExecutionContext)

        # Verify context has observability with tracer
        assert captured_contexts[0].observability is not None
        assert captured_contexts[0].observability.tracer is langfuse_handler

    @pytest.mark.asyncio
    async def test_adapter_context_contains_langfuse_handler(self):
        """Adapter's context should contain the Langfuse handler for tracing."""
        langfuse_handler = MagicMock()

        adapter = JobGeneratorV2Adapter(
            max_retry=3,
            langfuse_handler=langfuse_handler,
        )

        # Build context directly to verify structure
        context = adapter._create_context_builder(
            job_id="test-job-id",
            user_requirement="Test requirement",
        ).build()

        # Verify observability context contains the tracer
        assert context.observability is not None
        assert context.observability.tracer is langfuse_handler


class TestContextObservabilityIntegration:
    """Tests for context's observability integration."""

    def test_context_has_observability_field(self):
        """ExecutionContext should have an observability field."""
        context = (
            ContextBuilder()
            .with_job_id("test-job-id")
            .with_user_requirement("Test requirement")
            .build()
        )

        assert hasattr(context, "observability")
        assert context.observability is not None

    def test_observability_context_has_tracer_field(self):
        """ObservabilityContext should have a tracer field."""
        obs_context = ObservabilityContext()

        assert hasattr(obs_context, "tracer")

    def test_context_with_tracer(self):
        """Context should accept and store a tracer."""
        tracer = MagicMock()

        context = (
            ContextBuilder()
            .with_job_id("test-job-id")
            .with_user_requirement("Test requirement")
            .with_observability_context(ObservabilityContext(tracer=tracer))
            .build()
        )

        assert context.observability.tracer is tracer
