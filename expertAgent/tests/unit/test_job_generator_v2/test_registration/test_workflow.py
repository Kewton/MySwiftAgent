"""Unit tests for RegistrationWorkflow.

Issue #342 Phase D.3: Tests for main registration workflow.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
from aiagent.langgraph.jobGeneratorV2.protocols import RetryPolicy, WorkflowProtocol
from aiagent.langgraph.jobGeneratorV2.types import (
    InterfaceSchema,
    PhaseStatus,
    RegistrationInput,
    RegistrationOutput,
    TaskDefinition,
)

# Use old Phase enum for 4-phase architecture tests (ExecutionContext uses types_old)
from aiagent.langgraph.jobGeneratorV2.types_old import Phase


class TestRegistrationWorkflowExists:
    """Test that RegistrationWorkflow exists and is importable."""

    def test_registration_workflow_importable(self):
        """RegistrationWorkflow should be importable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.workflow import (
            RegistrationWorkflow,
        )

        assert RegistrationWorkflow is not None

    def test_registration_workflow_has_execute_method(self):
        """RegistrationWorkflow should have an execute method."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.workflow import (
            RegistrationWorkflow,
        )

        workflow = RegistrationWorkflow()
        assert hasattr(workflow, "execute")
        assert callable(workflow.execute)

    def test_registration_workflow_has_get_retry_policy(self):
        """RegistrationWorkflow should have get_retry_policy method."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.workflow import (
            RegistrationWorkflow,
        )

        workflow = RegistrationWorkflow()
        assert hasattr(workflow, "get_retry_policy")
        assert callable(workflow.get_retry_policy)


class TestRegistrationWorkflowProtocol:
    """Test RegistrationWorkflow implements WorkflowProtocol."""

    def test_workflow_protocol_compatibility(self):
        """RegistrationWorkflow should be compatible with WorkflowProtocol."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.workflow import (
            RegistrationWorkflow,
        )

        workflow = RegistrationWorkflow()

        # Check protocol compliance
        assert isinstance(workflow, WorkflowProtocol)

    def test_get_retry_policy_returns_retry_policy(self):
        """get_retry_policy should return RetryPolicy instance."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.workflow import (
            RegistrationWorkflow,
        )

        workflow = RegistrationWorkflow()
        policy = workflow.get_retry_policy()

        assert isinstance(policy, RetryPolicy)
        assert policy.max_retries >= 1


class TestRegistrationWorkflowExecute:
    """Test RegistrationWorkflow.execute() method."""

    @pytest.fixture
    def sample_tasks(self) -> list[TaskDefinition]:
        """Create sample tasks for testing."""
        return [
            TaskDefinition(
                id="task_001",
                name="Gmail Search",
                description="Search for emails",
                task_type="gmail_search",
                recommended_api="/v1/utility/gmail/search",
                priority=1,
                dependencies=[],
            ),
            TaskDefinition(
                id="task_002",
                name="Summarize",
                description="Summarize results",
                task_type="llm_processing",
                recommended_api="/v1/ai/json_output",
                priority=2,
                dependencies=["task_001"],
            ),
        ]

    @pytest.fixture
    def sample_interfaces(self) -> dict[str, InterfaceSchema]:
        """Create sample interfaces for testing."""
        return {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            ),
        }

    @pytest.fixture
    def sample_input(
        self,
        sample_tasks: list[TaskDefinition],
        sample_interfaces: dict[str, InterfaceSchema],
    ) -> RegistrationInput:
        """Create sample input for testing."""
        return RegistrationInput(
            tasks=sample_tasks,
            interfaces=sample_interfaces,
            project_id="test-project",
        )

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock execution context."""
        return ExecutionContext(
            job_id="test-job-123",
            user_requirement="Search and summarize emails",
            max_phase_retries=3,
            max_total_retries=5,
        )

    @pytest.mark.asyncio
    async def test_execute_returns_registration_output(
        self,
        sample_input: RegistrationInput,
        mock_context: ExecutionContext,
    ):
        """execute() should return RegistrationOutput."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobRegistrationResult,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            InterfaceMasterInfo,
            JobMasterInfo,
            MasterCreationResult,
            TaskMasterInfo,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.workflow import (
            RegistrationWorkflow,
        )

        # Create mock results
        mock_master_result = MasterCreationResult(
            job_master=JobMasterInfo(
                id="jm_123",
                name="Test Job",
                method="POST",
                url="http://localhost:8005",
                timeout_sec=300,
            ),
            task_masters=[
                TaskMasterInfo(
                    id="tm_001",
                    name="Task 1",
                    task_id="task_001",
                    order=0,
                    input_interface_id="im_001_input",
                    output_interface_id="im_001_output",
                ),
            ],
            interface_masters=[
                InterfaceMasterInfo(
                    id="im_001_input",
                    name="Task 1 Input",
                    task_id="task_001",
                    is_input=True,
                ),
            ],
        )

        mock_job_result = JobRegistrationResult(
            job_id="job_123",
            job_name="Test Job",
        )

        mock_master_manager = AsyncMock()
        mock_master_manager.create_masters = AsyncMock(return_value=mock_master_result)

        mock_job_registrar = AsyncMock()
        mock_job_registrar.register_job = AsyncMock(return_value=mock_job_result)

        with (
            patch(
                "aiagent.langgraph.jobGeneratorV2.workflows.registration.workflow.MasterManagerSubWorkflow",
                return_value=mock_master_manager,
            ),
            patch(
                "aiagent.langgraph.jobGeneratorV2.workflows.registration.workflow.JobRegistrarSubWorkflow",
                return_value=mock_job_registrar,
            ),
        ):
            workflow = RegistrationWorkflow()
            result = await workflow.execute(sample_input, mock_context)

            assert isinstance(result, RegistrationOutput)
            assert hasattr(result, "status")
            assert hasattr(result, "job_master_id")
            assert hasattr(result, "task_master_ids")
            assert hasattr(result, "interface_master_ids")
            assert hasattr(result, "job_id")

    @pytest.mark.asyncio
    async def test_execute_success_status(
        self,
        sample_input: RegistrationInput,
        mock_context: ExecutionContext,
    ):
        """execute() should return SUCCESS status on successful registration."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobRegistrationResult,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            JobMasterInfo,
            MasterCreationResult,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.workflow import (
            RegistrationWorkflow,
        )

        mock_master_result = MasterCreationResult(
            job_master=JobMasterInfo(
                id="jm_123",
                name="Test Job",
                method="POST",
                url="http://localhost:8005",
                timeout_sec=300,
            ),
        )
        mock_job_result = JobRegistrationResult(
            job_id="job_123",
            job_name="Test Job",
        )

        mock_master_manager = AsyncMock()
        mock_master_manager.create_masters = AsyncMock(return_value=mock_master_result)

        mock_job_registrar = AsyncMock()
        mock_job_registrar.register_job = AsyncMock(return_value=mock_job_result)

        with (
            patch(
                "aiagent.langgraph.jobGeneratorV2.workflows.registration.workflow.MasterManagerSubWorkflow",
                return_value=mock_master_manager,
            ),
            patch(
                "aiagent.langgraph.jobGeneratorV2.workflows.registration.workflow.JobRegistrarSubWorkflow",
                return_value=mock_job_registrar,
            ),
        ):
            workflow = RegistrationWorkflow()
            result = await workflow.execute(sample_input, mock_context)

            assert result.status == PhaseStatus.SUCCESS
            assert result.job_master_id == "jm_123"
            assert result.job_id == "job_123"

    @pytest.mark.asyncio
    async def test_execute_empty_tasks_returns_failed(
        self,
        sample_interfaces: dict[str, InterfaceSchema],
        mock_context: ExecutionContext,
    ):
        """execute() should return FAILED status for empty tasks."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.workflow import (
            RegistrationWorkflow,
        )

        input_data = RegistrationInput(
            tasks=[],
            interfaces=sample_interfaces,
            project_id="test-project",
        )

        workflow = RegistrationWorkflow()
        result = await workflow.execute(input_data, mock_context)

        assert result.status == PhaseStatus.FAILED
        assert result.job_master_id is None

    @pytest.mark.asyncio
    async def test_execute_empty_interfaces_returns_failed(
        self,
        sample_tasks: list[TaskDefinition],
        mock_context: ExecutionContext,
    ):
        """execute() should return FAILED status for empty interfaces."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.workflow import (
            RegistrationWorkflow,
        )

        input_data = RegistrationInput(
            tasks=sample_tasks,
            interfaces={},
            project_id="test-project",
        )

        workflow = RegistrationWorkflow()
        result = await workflow.execute(input_data, mock_context)

        assert result.status == PhaseStatus.FAILED
        assert result.job_master_id is None


class TestRegistrationWorkflowRetryBugFix:
    """Test retry_count bug fix in RegistrationWorkflow (Issue #342)."""

    @pytest.fixture
    def mock_context_with_retries(self) -> ExecutionContext:
        """Create context with existing retry state."""
        ctx = ExecutionContext(
            job_id="test-job-retry",
            user_requirement="Test retry handling",
            max_phase_retries=3,
            max_total_retries=5,
        )
        # Simulate previous phases having used retries
        ctx.record_retry(Phase.TASK_BREAKDOWN, "Previous phase retry")
        ctx.record_retry(Phase.INTERFACE_DESIGN, "Previous phase retry")
        return ctx

    def test_registration_workflow_respects_retry_limits(
        self, mock_context_with_retries: ExecutionContext
    ):
        """Workflow should respect per-phase retry limits."""
        # REGISTRATION phase should have independent retry state
        registration_retry = mock_context_with_retries.get_phase_retry_state(
            Phase.REGISTRATION
        )

        # Should be able to retry (hasn't hit its own limit)
        assert registration_retry.can_retry() is True
        assert registration_retry.count == 0

        # Record retries up to limit
        for i in range(3):
            mock_context_with_retries.record_retry(
                Phase.REGISTRATION, f"Registration retry {i + 1}"
            )

        # Now should not be able to retry
        assert registration_retry.can_retry() is False

    def test_phase_retries_are_independent(
        self, mock_context_with_retries: ExecutionContext
    ):
        """Each phase should have independent retry tracking."""
        # Previous phases already have retries
        task_breakdown = mock_context_with_retries.get_phase_retry_state(
            Phase.TASK_BREAKDOWN
        )
        assert task_breakdown.count == 1

        interface_design = mock_context_with_retries.get_phase_retry_state(
            Phase.INTERFACE_DESIGN
        )
        assert interface_design.count == 1

        # REGISTRATION should start fresh
        registration = mock_context_with_retries.get_phase_retry_state(
            Phase.REGISTRATION
        )
        assert registration.count == 0


class TestRegistrationWorkflowSubWorkflowOrchestration:
    """Test that workflow orchestrates sub-workflows correctly."""

    @pytest.fixture
    def sample_tasks(self) -> list[TaskDefinition]:
        """Create sample tasks."""
        return [
            TaskDefinition(
                id="task_001",
                name="Test Task",
                description="Test",
                task_type="test",
                recommended_api="/test",
                priority=1,
            )
        ]

    @pytest.fixture
    def sample_interfaces(self) -> dict[str, InterfaceSchema]:
        """Create sample interfaces."""
        return {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            )
        }

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock context."""
        return ExecutionContext(
            job_id="test-job",
            user_requirement="Test",
        )

    @pytest.mark.asyncio
    async def test_workflow_calls_subworkflows_in_order(
        self,
        sample_tasks: list[TaskDefinition],
        sample_interfaces: dict[str, InterfaceSchema],
        mock_context: ExecutionContext,
    ):
        """Workflow should call sub-workflows in order: master_manager -> job_registrar."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.job_registrar import (
            JobRegistrationResult,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            JobMasterInfo,
            MasterCreationResult,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.workflow import (
            RegistrationWorkflow,
        )

        call_order: list[str] = []

        mock_master_result = MasterCreationResult(
            job_master=JobMasterInfo(
                id="jm_123",
                name="Test Job",
                method="POST",
                url="http://localhost:8005",
                timeout_sec=300,
            ),
        )
        mock_job_result = JobRegistrationResult(
            job_id="job_123",
            job_name="Test Job",
        )

        mock_master_manager = MagicMock()

        async def mock_create_masters(*args, **kwargs):
            call_order.append("create_masters")
            return mock_master_result

        mock_master_manager.create_masters = mock_create_masters

        mock_job_registrar = MagicMock()

        async def mock_register_job(*args, **kwargs):
            call_order.append("register_job")
            return mock_job_result

        mock_job_registrar.register_job = mock_register_job

        with (
            patch(
                "aiagent.langgraph.jobGeneratorV2.workflows.registration.workflow.MasterManagerSubWorkflow",
                return_value=mock_master_manager,
            ),
            patch(
                "aiagent.langgraph.jobGeneratorV2.workflows.registration.workflow.JobRegistrarSubWorkflow",
                return_value=mock_job_registrar,
            ),
        ):
            workflow = RegistrationWorkflow()
            input_data = RegistrationInput(
                tasks=sample_tasks,
                interfaces=sample_interfaces,
                project_id="test-project",
            )
            await workflow.execute(input_data, mock_context)

            assert call_order == ["create_masters", "register_job"]


class TestRegistrationWorkflowInitialization:
    """Test RegistrationWorkflow initialization."""

    def test_default_initialization(self):
        """Should initialize with default values."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.workflow import (
            RegistrationWorkflow,
        )

        workflow = RegistrationWorkflow()
        assert workflow._graphai_server_url == "http://localhost:8005"

    def test_custom_initialization(self):
        """Should initialize with custom values."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.workflow import (
            RegistrationWorkflow,
        )

        workflow = RegistrationWorkflow(graphai_server_url="http://custom:8000")
        assert workflow._graphai_server_url == "http://custom:8000"
