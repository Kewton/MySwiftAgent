"""Unit tests for InterfaceDesignWorkflow.

Issue #342 Phase C.4: Tests for main workflow integration.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
from aiagent.langgraph.jobGeneratorV2.types import (
    CompatibilityReport,
    EnrichmentReport,
    InterfaceDesignInput,
    InterfaceDesignOutput,
    InterfaceSchema,
    PhaseStatus,
    TaskDefinition,
)

# Use old Phase enum for 4-phase architecture tests (ExecutionContext uses types_old)
from aiagent.langgraph.jobGeneratorV2.types_old import Phase


class TestInterfaceDesignWorkflowExists:
    """Test that InterfaceDesignWorkflow exists and is importable."""

    def test_interface_design_workflow_importable(self):
        """InterfaceDesignWorkflow should be importable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow import (
            InterfaceDesignWorkflow,
        )

        assert InterfaceDesignWorkflow is not None

    def test_interface_design_workflow_has_execute_method(self):
        """InterfaceDesignWorkflow should have an execute method."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow import (
            InterfaceDesignWorkflow,
        )

        workflow = InterfaceDesignWorkflow()
        assert hasattr(workflow, "execute")
        assert callable(workflow.execute)

    def test_interface_design_workflow_has_get_retry_policy(self):
        """InterfaceDesignWorkflow should have get_retry_policy method."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow import (
            InterfaceDesignWorkflow,
        )

        workflow = InterfaceDesignWorkflow()
        assert hasattr(workflow, "get_retry_policy")
        assert callable(workflow.get_retry_policy)


class TestInterfaceDesignWorkflowProtocol:
    """Test InterfaceDesignWorkflow implements WorkflowProtocol."""

    def test_workflow_protocol_compatibility(self):
        """InterfaceDesignWorkflow should be compatible with WorkflowProtocol."""
        from aiagent.langgraph.jobGeneratorV2.protocols import WorkflowProtocol
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow import (
            InterfaceDesignWorkflow,
        )

        workflow = InterfaceDesignWorkflow()

        # Check protocol compliance
        assert isinstance(workflow, WorkflowProtocol)

    def test_get_retry_policy_returns_retry_policy(self):
        """get_retry_policy should return RetryPolicy instance."""
        from aiagent.langgraph.jobGeneratorV2.protocols import RetryPolicy
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow import (
            InterfaceDesignWorkflow,
        )

        workflow = InterfaceDesignWorkflow()
        policy = workflow.get_retry_policy()

        assert isinstance(policy, RetryPolicy)
        assert policy.max_retries >= 1


class TestInterfaceDesignWorkflowExecute:
    """Test InterfaceDesignWorkflow.execute() method."""

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
    def sample_input(self, sample_tasks: list[TaskDefinition]) -> InterfaceDesignInput:
        """Create sample input for testing."""
        return InterfaceDesignInput(
            tasks=sample_tasks,
            openapi_specs={},
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
    async def test_execute_returns_interface_design_output(
        self,
        sample_input: InterfaceDesignInput,
        mock_context: ExecutionContext,
    ):
        """execute() should return InterfaceDesignOutput."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow import (
            InterfaceDesignWorkflow,
        )

        # Create mocks for sub-workflows
        mock_schema_generator = AsyncMock()
        mock_schema_generator.generate = AsyncMock(
            return_value={
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
        )

        mock_compatibility_checker = AsyncMock()
        mock_compatibility_checker.check = AsyncMock(
            return_value=CompatibilityReport(is_compatible=True, issues=[])
        )

        mock_enricher = AsyncMock()
        mock_enricher.enrich = AsyncMock(
            return_value=(
                {
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
                },
                EnrichmentReport(enriched_count=2, skipped_count=0),
            )
        )

        with (
            patch(
                "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.SchemaGeneratorSubWorkflow",
                return_value=mock_schema_generator,
            ),
            patch(
                "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.CompatibilityCheckerSubWorkflow",
                return_value=mock_compatibility_checker,
            ),
            patch(
                "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.SchemaEnricherSubWorkflow",
                return_value=mock_enricher,
            ),
        ):
            workflow = InterfaceDesignWorkflow()
            result = await workflow.execute(sample_input, mock_context)

            assert isinstance(result, InterfaceDesignOutput)
            assert hasattr(result, "status")
            assert hasattr(result, "interfaces")
            assert hasattr(result, "compatibility_report")
            assert hasattr(result, "enrichment_report")

    @pytest.mark.asyncio
    async def test_execute_success_status_on_compatible(
        self,
        sample_input: InterfaceDesignInput,
        mock_context: ExecutionContext,
    ):
        """execute() should return SUCCESS status when interfaces are compatible."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow import (
            InterfaceDesignWorkflow,
        )

        mock_schema_generator = AsyncMock()
        mock_schema_generator.generate = AsyncMock(
            return_value={
                "task_001": InterfaceSchema(
                    task_id="task_001",
                    input_schema={"type": "object"},
                    output_schema={"type": "object"},
                ),
            }
        )

        mock_compatibility_checker = AsyncMock()
        mock_compatibility_checker.check = AsyncMock(
            return_value=CompatibilityReport(is_compatible=True, issues=[])
        )

        mock_enricher = AsyncMock()
        mock_enricher.enrich = AsyncMock(
            return_value=(
                {
                    "task_001": InterfaceSchema(
                        task_id="task_001", input_schema={}, output_schema={}
                    )
                },
                EnrichmentReport(),
            )
        )

        with (
            patch(
                "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.SchemaGeneratorSubWorkflow",
                return_value=mock_schema_generator,
            ),
            patch(
                "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.CompatibilityCheckerSubWorkflow",
                return_value=mock_compatibility_checker,
            ),
            patch(
                "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.SchemaEnricherSubWorkflow",
                return_value=mock_enricher,
            ),
        ):
            workflow = InterfaceDesignWorkflow()
            result = await workflow.execute(sample_input, mock_context)

            assert result.status == PhaseStatus.SUCCESS

    @pytest.mark.asyncio
    async def test_execute_needs_retry_on_incompatible(
        self,
        sample_input: InterfaceDesignInput,
        mock_context: ExecutionContext,
    ):
        """execute() should return NEEDS_RETRY when interfaces are incompatible."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow import (
            InterfaceDesignWorkflow,
        )

        mock_schema_generator = AsyncMock()
        mock_schema_generator.generate = AsyncMock(
            return_value={
                "task_001": InterfaceSchema(
                    task_id="task_001",
                    input_schema={"type": "object"},
                    output_schema={"type": "object"},
                ),
            }
        )

        mock_compatibility_checker = AsyncMock()
        mock_compatibility_checker.check = AsyncMock(
            return_value=CompatibilityReport(
                is_compatible=False,
                issues=["Type mismatch between task_001 and task_002"],
            )
        )

        mock_enricher = AsyncMock()
        mock_enricher.enrich = AsyncMock(
            return_value=(
                {
                    "task_001": InterfaceSchema(
                        task_id="task_001", input_schema={}, output_schema={}
                    )
                },
                EnrichmentReport(),
            )
        )

        with (
            patch(
                "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.SchemaGeneratorSubWorkflow",
                return_value=mock_schema_generator,
            ),
            patch(
                "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.CompatibilityCheckerSubWorkflow",
                return_value=mock_compatibility_checker,
            ),
            patch(
                "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.SchemaEnricherSubWorkflow",
                return_value=mock_enricher,
            ),
        ):
            workflow = InterfaceDesignWorkflow()
            result = await workflow.execute(sample_input, mock_context)

            assert result.status == PhaseStatus.NEEDS_RETRY


class TestInterfaceDesignWorkflowRetryBugFix:
    """Test retry_count bug fix in InterfaceDesignWorkflow (Issue #342)."""

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
        return ctx

    def test_interface_design_workflow_respects_retry_limits(
        self, mock_context_with_retries: ExecutionContext
    ):
        """Workflow should respect per-phase retry limits."""
        # INTERFACE_DESIGN phase should have independent retry state
        interface_retry = mock_context_with_retries.get_phase_retry_state(
            Phase.INTERFACE_DESIGN
        )

        # Should be able to retry (hasn't hit its own limit)
        assert interface_retry.can_retry() is True
        assert interface_retry.count == 0

        # Record retries up to limit
        for i in range(3):
            mock_context_with_retries.record_retry(
                Phase.INTERFACE_DESIGN, f"Interface retry {i + 1}"
            )

        # Now should not be able to retry
        assert interface_retry.can_retry() is False

    def test_phase_retries_are_independent(
        self, mock_context_with_retries: ExecutionContext
    ):
        """Each phase should have independent retry tracking."""
        # TASK_BREAKDOWN already has 1 retry
        task_breakdown = mock_context_with_retries.get_phase_retry_state(
            Phase.TASK_BREAKDOWN
        )
        assert task_breakdown.count == 1

        # INTERFACE_DESIGN should start fresh
        interface_design = mock_context_with_retries.get_phase_retry_state(
            Phase.INTERFACE_DESIGN
        )
        assert interface_design.count == 0

        # Add retries to INTERFACE_DESIGN
        mock_context_with_retries.record_retry(
            Phase.INTERFACE_DESIGN, "Interface retry"
        )

        # TASK_BREAKDOWN should still be 1
        assert task_breakdown.count == 1
        # INTERFACE_DESIGN should now be 1
        assert interface_design.count == 1


class TestInterfaceDesignWorkflowSubWorkflowOrchestration:
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
    def mock_context(self) -> ExecutionContext:
        """Create mock context."""
        return ExecutionContext(
            job_id="test-job",
            user_requirement="Test",
        )

    @pytest.mark.asyncio
    async def test_workflow_calls_subworkflows_in_order(
        self, sample_tasks: list[TaskDefinition], mock_context: ExecutionContext
    ):
        """Workflow should call sub-workflows in order: generate -> check -> enrich."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow import (
            InterfaceDesignWorkflow,
        )

        call_order: list[str] = []

        mock_schema_generator = MagicMock()

        async def mock_generate(*args):
            call_order.append("generate")
            return {
                "task_001": InterfaceSchema(
                    task_id="task_001", input_schema={}, output_schema={}
                )
            }

        mock_schema_generator.generate = mock_generate

        mock_compatibility = MagicMock()

        async def mock_check(*args):
            call_order.append("check")
            return CompatibilityReport(is_compatible=True, issues=[])

        mock_compatibility.check = mock_check

        mock_enricher = MagicMock()

        async def mock_enrich(*args):
            call_order.append("enrich")
            return (
                {
                    "task_001": InterfaceSchema(
                        task_id="task_001", input_schema={}, output_schema={}
                    )
                },
                EnrichmentReport(),
            )

        mock_enricher.enrich = mock_enrich

        with (
            patch(
                "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.SchemaGeneratorSubWorkflow",
                return_value=mock_schema_generator,
            ),
            patch(
                "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.CompatibilityCheckerSubWorkflow",
                return_value=mock_compatibility,
            ),
            patch(
                "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.SchemaEnricherSubWorkflow",
                return_value=mock_enricher,
            ),
        ):
            workflow = InterfaceDesignWorkflow()
            input_data = InterfaceDesignInput(tasks=sample_tasks)
            await workflow.execute(input_data, mock_context)

            assert call_order == ["generate", "check", "enrich"]
