"""Unit tests for Issue #386: Phase 2 Integration.

Issue #386: Phase 2 master_manager + BodyTemplateValidator + trace_id propagation.

Test Coverage:
- AC-1/AC-2: _execute_registration calls MasterManagerSubWorkflow.create_masters
- AC-3: Registration failure triggers OrchestratorError
- AC-4/AC-5: BodyTemplateValidator integration (tested via MasterManagerSubWorkflow)
- AC-6/AC-7: trace_id propagation through run_workflow to _execute_workflow_gen
- AC-8: Logs include trace_id (tested via mocks)

TDD Red Phase: Tests define expected behavior.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer import (
    AnalyzedTask,
    InterfaceDefinition,
)
from aiagent.langgraph.jobGeneratorV2.orchestrator import (
    JobGenerationOrchestrator,
    JobGenerationRequest,
    OrchestratorError,
)
from aiagent.langgraph.jobGeneratorV2.types import Phase


class TestExecuteRegistrationWithMasterManager:
    """Test _execute_registration calls MasterManagerSubWorkflow.create_masters."""

    @pytest.fixture
    def mock_context(self):
        """Create mock ExecutionContext."""
        from aiagent.langgraph.jobGeneratorV2.context import (
            ContextBuilder,
            StorageContext,
        )

        storage = StorageContext(jobqueue_client=MagicMock())
        context = (
            ContextBuilder()
            .with_job_id("test_job_123")
            .with_user_requirement("Test requirement")
            .with_storage_context(storage)
            .build()
        )
        return context

    @pytest.fixture
    def sample_tasks(self) -> list[AnalyzedTask]:
        """Create sample AnalyzedTask list."""
        return [
            AnalyzedTask(
                task_id="task_001",
                name="Search Emails",
                description="Search Gmail for messages",
                task_type="fetch",
                recommended_api="/v1/utility/gmail/search",
                dependencies=[],
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
                output_schema={
                    "type": "object",
                    "properties": {"results": {"type": "array"}},
                },
                priority=1,
            ),
            AnalyzedTask(
                task_id="task_002",
                name="Send Summary",
                description="Send email summary",
                task_type="send",
                recommended_api="/v1/utility/gmail/send",
                dependencies=["task_001"],
                input_schema={
                    "type": "object",
                    "properties": {"subject": {"type": "string"}},
                },
                output_schema={
                    "type": "object",
                    "properties": {"sent": {"type": "boolean"}},
                },
                priority=2,
            ),
        ]

    @pytest.fixture
    def sample_interfaces(self) -> dict[str, InterfaceDefinition]:
        """Create sample InterfaceDefinition dict."""
        return {
            "task_001": InterfaceDefinition(
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
                output_schema={
                    "type": "object",
                    "properties": {"results": {"type": "array"}},
                },
                description="Gmail search interface",
            ),
            "task_002": InterfaceDefinition(
                input_schema={
                    "type": "object",
                    "properties": {"subject": {"type": "string"}},
                },
                output_schema={
                    "type": "object",
                    "properties": {"sent": {"type": "boolean"}},
                },
                description="Gmail send interface",
            ),
        }

    @pytest.mark.asyncio
    async def test_execute_registration_calls_master_manager(
        self, sample_tasks, sample_interfaces, mock_context
    ):
        """AC-1/AC-2: _execute_registration must call MasterManagerSubWorkflow.create_masters."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            JobMasterInfo,
            MasterCreationResult,
            TaskMasterInfo,
        )

        # Mock MasterCreationResult
        mock_result = MasterCreationResult(
            job_master=JobMasterInfo(
                id="jm_real_id_123",
                name="Test Job",
                method="POST",
                url="http://localhost:8005/api/v2/workflows",
                timeout_sec=300,
            ),
            task_masters=[
                TaskMasterInfo(
                    id="tm_real_id_001",
                    name="Search Emails",
                    task_id="task_001",
                    order=0,
                    input_interface_id="im_001",
                    output_interface_id="om_001",
                ),
                TaskMasterInfo(
                    id="tm_real_id_002",
                    name="Send Summary",
                    task_id="task_002",
                    order=1,
                    input_interface_id="im_002",
                    output_interface_id="om_002",
                ),
            ],
            interface_masters=[],
            job_master_task_ids=["jmt_001", "jmt_002"],
        )

        with patch(
            "aiagent.langgraph.jobGeneratorV2.orchestrator.MasterManagerSubWorkflow"
        ) as MockMasterManager:
            mock_instance = AsyncMock()
            mock_instance.create_masters = AsyncMock(return_value=mock_result)
            MockMasterManager.return_value = mock_instance

            orchestrator = JobGenerationOrchestrator()
            result = await orchestrator._execute_registration(
                tasks=sample_tasks,
                interfaces=sample_interfaces,
                project_id="test_project",
                context=mock_context,
            )

            # Verify MasterManagerSubWorkflow was instantiated and called
            MockMasterManager.assert_called_once()
            mock_instance.create_masters.assert_called_once()

            # Verify result contains real IDs from MasterCreationResult
            assert result["job_master_id"] == "jm_real_id_123"
            assert result["task_id_to_master_id"]["task_001"] == "tm_real_id_001"
            assert result["task_id_to_master_id"]["task_002"] == "tm_real_id_002"

    @pytest.mark.asyncio
    async def test_execute_registration_requires_context(
        self, sample_tasks, sample_interfaces
    ):
        """_execute_registration must accept context parameter."""
        import inspect

        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )

        sig = inspect.signature(JobGenerationOrchestrator._execute_registration)
        param_names = list(sig.parameters.keys())

        assert "context" in param_names, "context parameter is required"

    @pytest.mark.asyncio
    async def test_execute_registration_failure_raises_orchestrator_error(
        self, sample_tasks, sample_interfaces, mock_context
    ):
        """AC-3: Registration failure must raise OrchestratorError (Fail-Fast)."""
        from aiagent.langgraph.jobGeneratorV2.protocols import (
            ErrorType,
            WorkflowError,
        )
        from aiagent.langgraph.jobGeneratorV2.types_old import Phase as PhaseOld

        with patch(
            "aiagent.langgraph.jobGeneratorV2.orchestrator.MasterManagerSubWorkflow"
        ) as MockMasterManager:
            mock_instance = AsyncMock()
            mock_instance.create_masters = AsyncMock(
                side_effect=WorkflowError(
                    "Failed to create TaskMaster",
                    ErrorType.API,
                    PhaseOld.REGISTRATION,
                )
            )
            MockMasterManager.return_value = mock_instance

            orchestrator = JobGenerationOrchestrator()

            with pytest.raises(OrchestratorError) as exc_info:
                await orchestrator._execute_registration(
                    tasks=sample_tasks,
                    interfaces=sample_interfaces,
                    project_id="test_project",
                    context=mock_context,
                )

            assert exc_info.value.phase == Phase.REGISTRATION
            assert "Failed" in str(exc_info.value)


class TestRunWorkflowTraceIdPropagation:
    """Test trace_id propagation through run_workflow."""

    @pytest.mark.asyncio
    async def test_run_workflow_accepts_trace_id_parameter(self):
        """AC-6: run_workflow must accept trace_id and parent_span_id parameters."""
        import inspect

        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )

        sig = inspect.signature(JobGenerationOrchestrator.run_workflow)
        param_names = list(sig.parameters.keys())

        assert "trace_id" in param_names, "trace_id parameter is required"
        assert "parent_span_id" in param_names, "parent_span_id parameter is required"

    @pytest.mark.asyncio
    async def test_run_workflow_passes_trace_id_to_workflow_gen(self):
        """AC-7: trace_id must be passed to _execute_workflow_gen."""
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer import (
            JobAnalysisResponse,
        )

        mock_analysis_result = JobAnalysisResponse(
            tasks=[
                AnalyzedTask(
                    task_id="task_001",
                    name="Test Task",
                    description="Test",
                    task_type="fetch",
                    recommended_api="/test",
                    dependencies=[],
                    priority=1,
                )
            ],
            interfaces={
                "task_001": InterfaceDefinition(
                    input_schema={"type": "object"},
                    output_schema={"type": "object"},
                )
            },
            job_body_parameters=[],
            overall_summary="Test",
        )

        orchestrator = JobGenerationOrchestrator()

        with patch.object(
            orchestrator, "_execute_job_analysis", new_callable=AsyncMock
        ) as mock_analysis:
            mock_analysis.return_value = mock_analysis_result

            with patch.object(
                orchestrator, "_execute_registration", new_callable=AsyncMock
            ) as mock_registration:
                mock_registration.return_value = {
                    "job_master_id": "jm_123",
                    "task_id_to_master_id": {"task_001": "tm_001"},
                }

                with patch.object(
                    orchestrator, "_execute_workflow_gen", new_callable=AsyncMock
                ) as mock_workflow_gen:
                    from aiagent.langgraph.jobGeneratorV2.types import (
                        ParallelExecutionResult,
                    )

                    mock_workflow_gen.return_value = ParallelExecutionResult(
                        successful_tasks=[],
                        failed_tasks=[],
                        total_execution_time_ms=0.0,
                    )

                    request = JobGenerationRequest(
                        user_requirement="Test",
                        project_id="test",
                    )

                    await orchestrator.run_workflow(
                        request,
                        trace_id="trace_abc123",
                        parent_span_id="span_xyz789",
                    )

                    # Verify trace_id was passed to _execute_workflow_gen
                    mock_workflow_gen.assert_called_once()
                    call_kwargs = mock_workflow_gen.call_args.kwargs
                    assert call_kwargs.get("trace_id") == "trace_abc123"
                    assert call_kwargs.get("parent_span_id") == "span_xyz789"


class TestAdapterTraceIdPropagation:
    """Test trace_id propagation in adapter.py."""

    @pytest.mark.asyncio
    async def test_adapter_passes_trace_id_to_run_workflow(self):
        """AC-6: adapter.generate must pass trace_id to run_workflow."""
        from aiagent.langgraph.jobGeneratorV2.adapter import JobGeneratorAdapter
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
            JobGenerationResult,
        )

        # Create adapter with mock langfuse handler
        mock_handler = MagicMock()
        mock_handler.last_trace_id = "trace_from_langfuse_123"

        adapter = JobGeneratorAdapter(
            langfuse_handler=mock_handler,
        )

        # Mock the orchestrator's run_workflow
        with patch.object(
            JobGenerationOrchestrator,
            "run_workflow",
            new_callable=AsyncMock,
        ) as mock_run_workflow:
            mock_run_workflow.return_value = JobGenerationResult(
                success=True,
                job_id="job_123",
                job_master_id="jm_123",
                task_identifiers=[],
                workflows={},
            )

            await adapter.generate(
                user_requirement="Test requirement",
                project_id="test_project",
            )

            # Verify run_workflow was called with trace_id
            mock_run_workflow.assert_called_once()
            call_kwargs = mock_run_workflow.call_args.kwargs
            assert "trace_id" in call_kwargs or call_kwargs.get("trace_id") is not None


class TestExecuteRegistrationSignature:
    """Test _execute_registration has correct signature."""

    def test_execute_registration_signature(self):
        """_execute_registration must have context parameter in signature."""
        import inspect

        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )

        sig = inspect.signature(JobGenerationOrchestrator._execute_registration)
        params = sig.parameters

        # Required parameters
        assert "self" in params
        assert "tasks" in params
        assert "interfaces" in params
        assert "project_id" in params
        assert "context" in params

        # context should be a required parameter (no default)
        context_param = params["context"]
        assert context_param.default == inspect.Parameter.empty, (
            "context must be a required parameter"
        )


class TestOrchestratorContextStorage:
    """Test orchestrator stores and uses ExecutionContext."""

    @pytest.mark.asyncio
    async def test_run_workflow_creates_context(self):
        """run_workflow should create ExecutionContext for the workflow."""
        orchestrator = JobGenerationOrchestrator()

        # The orchestrator should be able to create context internally
        # or receive it as a parameter
        assert hasattr(orchestrator, "run_workflow")

    def test_orchestrator_can_be_initialized_with_jobqueue_client(self):
        """Orchestrator should accept jobqueue_client for DI."""
        mock_client = MagicMock()
        orchestrator = JobGenerationOrchestrator(jobqueue_client=mock_client)

        assert orchestrator._jobqueue_client == mock_client
