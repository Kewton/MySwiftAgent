"""Unit tests for WorkflowGenWorkflow.

Issue #342 Phase D.3: Tests for main workflow generation workflow.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
from aiagent.langgraph.jobGeneratorV2.protocols import RetryPolicy, WorkflowProtocol
from aiagent.langgraph.jobGeneratorV2.types import (
    InterfaceSchema,
    Phase,
    PhaseStatus,
    WorkflowGenInput,
    WorkflowGenOutput,
)


class TestWorkflowGenWorkflowExists:
    """Test that WorkflowGenWorkflow exists and is importable."""

    def test_workflow_gen_workflow_importable(self):
        """WorkflowGenWorkflow should be importable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
            WorkflowGenWorkflow,
        )

        assert WorkflowGenWorkflow is not None

    def test_workflow_gen_workflow_has_execute_method(self):
        """WorkflowGenWorkflow should have an execute method."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
            WorkflowGenWorkflow,
        )

        workflow = WorkflowGenWorkflow()
        assert hasattr(workflow, "execute")
        assert callable(workflow.execute)

    def test_workflow_gen_workflow_has_get_retry_policy(self):
        """WorkflowGenWorkflow should have get_retry_policy method."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
            WorkflowGenWorkflow,
        )

        workflow = WorkflowGenWorkflow()
        assert hasattr(workflow, "get_retry_policy")
        assert callable(workflow.get_retry_policy)


class TestWorkflowGenWorkflowProtocol:
    """Test WorkflowGenWorkflow implements WorkflowProtocol."""

    def test_workflow_protocol_compatibility(self):
        """WorkflowGenWorkflow should be compatible with WorkflowProtocol."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
            WorkflowGenWorkflow,
        )

        workflow = WorkflowGenWorkflow()

        # Check protocol compliance
        assert isinstance(workflow, WorkflowProtocol)

    def test_get_retry_policy_returns_retry_policy(self):
        """get_retry_policy should return RetryPolicy instance."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
            WorkflowGenWorkflow,
        )

        workflow = WorkflowGenWorkflow()
        policy = workflow.get_retry_policy()

        assert isinstance(policy, RetryPolicy)
        assert policy.max_retries >= 1


class TestWorkflowGenWorkflowExecute:
    """Test WorkflowGenWorkflow.execute() method."""

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
    def sample_input(self, sample_interfaces: dict[str, InterfaceSchema]) -> WorkflowGenInput:
        """Create sample input for testing."""
        return WorkflowGenInput(
            task_master_ids=["tm_task_001", "tm_task_002"],
            job_master_id="jm_123",
            interfaces=sample_interfaces,
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
    async def test_execute_returns_workflow_gen_output(
        self,
        sample_input: WorkflowGenInput,
        mock_context: ExecutionContext,
    ):
        """execute() should return WorkflowGenOutput.

        Issue #350: Uses engine='graphai' for backward compatibility with
        existing mocking approach for YamlGeneratorSubWorkflow.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
            WorkflowGenWorkflow,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGenerationResult,
        )

        mock_yaml_result = YamlGenerationResult(
            yaml_content="version: \"0.6\"\nnodes:\n  task_001:\n    agent: fetchAgent\n    isResult: true\n",
            workflow_name="test_workflow",
            node_count=2,
        )

        mock_yaml_generator = AsyncMock()
        # Issue #342 V2: Mock generate_with_llm() as it's now the default
        mock_yaml_generator.generate_with_llm = AsyncMock(return_value=mock_yaml_result)
        mock_yaml_generator.generate = AsyncMock(return_value=mock_yaml_result)

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow.YamlGeneratorSubWorkflow",
            return_value=mock_yaml_generator,
        ):
            # Issue #350: Use graphai engine to test GraphAI code path
            workflow = WorkflowGenWorkflow(enable_testing=False, engine="graphai")
            result = await workflow.execute(sample_input, mock_context)

            assert isinstance(result, WorkflowGenOutput)
            assert hasattr(result, "status")
            assert hasattr(result, "workflow_yaml")
            assert hasattr(result, "test_result")

    @pytest.mark.asyncio
    async def test_execute_success_status(
        self,
        sample_input: WorkflowGenInput,
        mock_context: ExecutionContext,
    ):
        """execute() should return SUCCESS status on successful generation.

        Issue #350: Uses engine='graphai' for backward compatibility with
        existing mocking approach for YamlGeneratorSubWorkflow.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
            WorkflowGenWorkflow,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGenerationResult,
        )

        mock_yaml_result = YamlGenerationResult(
            yaml_content="version: \"0.6\"\nnodes:\n  task_001:\n    agent: fetchAgent\n    isResult: true\n",
            workflow_name="test_workflow",
            node_count=2,
        )

        mock_yaml_generator = AsyncMock()
        # Issue #342 V2: Mock generate_with_llm() as it's now the default
        mock_yaml_generator.generate_with_llm = AsyncMock(return_value=mock_yaml_result)
        mock_yaml_generator.generate = AsyncMock(return_value=mock_yaml_result)

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow.YamlGeneratorSubWorkflow",
            return_value=mock_yaml_generator,
        ):
            # Issue #350: Use graphai engine to test GraphAI code path
            workflow = WorkflowGenWorkflow(enable_testing=False, engine="graphai")
            result = await workflow.execute(sample_input, mock_context)

            assert result.status == PhaseStatus.SUCCESS
            assert result.workflow_yaml is not None

    @pytest.mark.asyncio
    async def test_execute_empty_task_masters_returns_failed(
        self,
        sample_interfaces: dict[str, InterfaceSchema],
        mock_context: ExecutionContext,
    ):
        """execute() should return FAILED status for empty task masters."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
            WorkflowGenWorkflow,
        )

        input_data = WorkflowGenInput(
            task_master_ids=[],
            job_master_id="jm_123",
            interfaces=sample_interfaces,
        )

        workflow = WorkflowGenWorkflow()
        result = await workflow.execute(input_data, mock_context)

        assert result.status == PhaseStatus.FAILED
        assert result.workflow_yaml is None

    @pytest.mark.asyncio
    async def test_execute_empty_job_master_returns_failed(
        self,
        sample_interfaces: dict[str, InterfaceSchema],
        mock_context: ExecutionContext,
    ):
        """execute() should return FAILED status for empty job master."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
            WorkflowGenWorkflow,
        )

        input_data = WorkflowGenInput(
            task_master_ids=["tm_001"],
            job_master_id="",
            interfaces=sample_interfaces,
        )

        workflow = WorkflowGenWorkflow()
        result = await workflow.execute(input_data, mock_context)

        assert result.status == PhaseStatus.FAILED
        assert result.workflow_yaml is None


class TestWorkflowGenWorkflowWithTesting:
    """Test WorkflowGenWorkflow with testing enabled."""

    @pytest.fixture
    def sample_input(self) -> WorkflowGenInput:
        """Create sample input."""
        return WorkflowGenInput(
            task_master_ids=["tm_task_001"],
            job_master_id="jm_123",
            interfaces={
                "task_001": InterfaceSchema(
                    task_id="task_001",
                    input_schema={"type": "object"},
                    output_schema={"type": "object"},
                )
            },
        )

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock context."""
        return ExecutionContext(
            job_id="test-job",
            user_requirement="Test",
        )

    @pytest.mark.asyncio
    async def test_execute_with_testing_enabled(
        self,
        sample_input: WorkflowGenInput,
        mock_context: ExecutionContext,
    ):
        """execute() should run tests when testing is enabled.

        Issue #350: Uses engine='graphai' for backward compatibility with
        existing mocking approach for YamlGeneratorSubWorkflow.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunResult,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
            WorkflowGenWorkflow,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGenerationResult,
        )

        mock_yaml_result = YamlGenerationResult(
            yaml_content="version: \"0.6\"\nnodes:\n  task_001:\n    isResult: true\n",
            workflow_name="test_workflow",
            node_count=1,
        )
        mock_test_result = TestRunResult(
            tests_run=1,
            tests_passed=1,
            tests_failed=0,
        )

        mock_yaml_generator = MagicMock()
        # Issue #342 V2: Mock generate_with_llm() as it's now the default
        mock_yaml_generator.generate_with_llm = AsyncMock(return_value=mock_yaml_result)
        mock_yaml_generator.generate = AsyncMock(return_value=mock_yaml_result)

        mock_test_runner = MagicMock()
        mock_test_runner.run_tests = AsyncMock(return_value=mock_test_result)

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow.YamlGeneratorSubWorkflow",
            return_value=mock_yaml_generator,
        ), patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow.TestRunnerSubWorkflow",
            return_value=mock_test_runner,
        ):
            # Issue #350: Use graphai engine to test GraphAI code path
            workflow = WorkflowGenWorkflow(enable_testing=True, engine="graphai")
            result = await workflow.execute(sample_input, mock_context)

            assert result.status == PhaseStatus.SUCCESS
            assert result.test_result is not None
            assert result.test_result["tests_passed"] == 1

    @pytest.mark.asyncio
    async def test_execute_needs_retry_on_test_failure(
        self,
        sample_input: WorkflowGenInput,
        mock_context: ExecutionContext,
    ):
        """execute() should return NEEDS_RETRY when tests fail.

        Issue #350: Uses engine='graphai' for backward compatibility with
        existing mocking approach for YamlGeneratorSubWorkflow.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.test_runner import (
            TestRunResult,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
            WorkflowGenWorkflow,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGenerationResult,
        )

        mock_yaml_result = YamlGenerationResult(
            yaml_content="version: \"0.6\"\nnodes:\n  task_001:\n    isResult: true\n",
            workflow_name="test_workflow",
            node_count=1,
        )
        mock_test_result = TestRunResult(
            tests_run=1,
            tests_passed=0,
            tests_failed=1,  # Test failure
        )

        mock_yaml_generator = MagicMock()
        # Issue #342 V2: Mock generate_with_llm() as it's now the default
        mock_yaml_generator.generate_with_llm = AsyncMock(return_value=mock_yaml_result)
        mock_yaml_generator.generate = AsyncMock(return_value=mock_yaml_result)

        mock_test_runner = MagicMock()
        mock_test_runner.run_tests = AsyncMock(return_value=mock_test_result)

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow.YamlGeneratorSubWorkflow",
            return_value=mock_yaml_generator,
        ), patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow.TestRunnerSubWorkflow",
            return_value=mock_test_runner,
        ):
            # Issue #350: Use graphai engine to test GraphAI code path
            workflow = WorkflowGenWorkflow(enable_testing=True, engine="graphai")
            result = await workflow.execute(sample_input, mock_context)

            assert result.status == PhaseStatus.NEEDS_RETRY
            assert result.workflow_yaml is not None  # YAML is still returned


class TestWorkflowGenWorkflowRetryBugFix:
    """Test retry_count bug fix in WorkflowGenWorkflow (Issue #342)."""

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
        ctx.record_retry(Phase.REGISTRATION, "Previous phase retry")
        return ctx

    def test_workflow_gen_respects_retry_limits(
        self, mock_context_with_retries: ExecutionContext
    ):
        """Workflow should respect per-phase retry limits."""
        # WORKFLOW_GEN phase should have independent retry state
        workflow_gen_retry = mock_context_with_retries.get_phase_retry_state(
            Phase.WORKFLOW_GEN
        )

        # Should be able to retry (hasn't hit its own limit)
        assert workflow_gen_retry.can_retry() is True
        assert workflow_gen_retry.count == 0

        # Record retries up to limit
        for i in range(3):
            mock_context_with_retries.record_retry(
                Phase.WORKFLOW_GEN, f"WorkflowGen retry {i+1}"
            )

        # Now should not be able to retry
        assert workflow_gen_retry.can_retry() is False

    def test_phase_retries_are_independent(
        self, mock_context_with_retries: ExecutionContext
    ):
        """Each phase should have independent retry tracking."""
        # Previous phases already have retries
        task_breakdown = mock_context_with_retries.get_phase_retry_state(
            Phase.TASK_BREAKDOWN
        )
        assert task_breakdown.count == 1

        registration = mock_context_with_retries.get_phase_retry_state(
            Phase.REGISTRATION
        )
        assert registration.count == 1

        # WORKFLOW_GEN should start fresh
        workflow_gen = mock_context_with_retries.get_phase_retry_state(
            Phase.WORKFLOW_GEN
        )
        assert workflow_gen.count == 0


class TestWorkflowGenWorkflowSubWorkflowOrchestration:
    """Test that workflow orchestrates sub-workflows correctly."""

    @pytest.fixture
    def sample_input(self) -> WorkflowGenInput:
        """Create sample input."""
        return WorkflowGenInput(
            task_master_ids=["tm_task_001"],
            job_master_id="jm_123",
            interfaces={
                "task_001": InterfaceSchema(
                    task_id="task_001",
                    input_schema={"type": "object"},
                    output_schema={"type": "object"},
                )
            },
        )

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock context."""
        return ExecutionContext(
            job_id="test-job",
            user_requirement="Test",
        )

    @pytest.mark.asyncio
    async def test_workflow_calls_yaml_generator(
        self,
        sample_input: WorkflowGenInput,
        mock_context: ExecutionContext,
    ):
        """Workflow should call YAML generator.

        Issue #350: Uses engine='graphai' for backward compatibility with
        existing mocking approach for YamlGeneratorSubWorkflow.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
            WorkflowGenWorkflow,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.yaml_generator import (
            YamlGenerationResult,
        )

        mock_yaml_result = YamlGenerationResult(
            yaml_content="version: \"0.6\"\nnodes:\n  task:\n    isResult: true\n",
            workflow_name="test",
            node_count=1,
        )

        mock_yaml_generator = MagicMock()
        # Issue #342 V2: Mock generate_with_llm() as it's now the default
        mock_yaml_generator.generate_with_llm = AsyncMock(return_value=mock_yaml_result)
        mock_yaml_generator.generate = AsyncMock(return_value=mock_yaml_result)

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow.YamlGeneratorSubWorkflow",
            return_value=mock_yaml_generator,
        ):
            # Issue #350: Use graphai engine to test GraphAI code path
            workflow = WorkflowGenWorkflow(enable_testing=False, engine="graphai")
            await workflow.execute(sample_input, mock_context)

            # Issue #342 V2: Now calls generate_with_llm() by default
            mock_yaml_generator.generate_with_llm.assert_called_once()


class TestWorkflowGenWorkflowInitialization:
    """Test WorkflowGenWorkflow initialization."""

    def test_default_initialization(self):
        """Should initialize with default values."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
            WorkflowGenWorkflow,
        )

        workflow = WorkflowGenWorkflow()
        assert workflow._enable_testing is False
        # Issue #342 Phase 1: Default version is 0.5 per BASE_RULES
        assert workflow._graphai_version == "0.5"
        # Issue #342 V2: LLM generation is enabled by default
        assert workflow._use_llm_generation is True

    def test_custom_initialization(self):
        """Should initialize with custom values."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow import (
            WorkflowGenWorkflow,
        )

        workflow = WorkflowGenWorkflow(
            enable_testing=True,
            graphai_version="0.7",
            use_llm_generation=False,
        )
        assert workflow._enable_testing is True
        assert workflow._graphai_version == "0.7"
        # Issue #342 V2: Can disable LLM generation
        assert workflow._use_llm_generation is False
