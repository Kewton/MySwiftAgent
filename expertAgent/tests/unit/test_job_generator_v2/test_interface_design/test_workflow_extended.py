"""Extended unit tests for InterfaceDesignWorkflow.

Issue #342 Phase C.4: Additional tests for coverage improvement.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
from aiagent.langgraph.jobGeneratorV2.types import (
    CompatibilityReport,
    EnrichmentReport,
    InterfaceDesignInput,
    InterfaceSchema,
    Phase,
    PhaseStatus,
    TaskDefinition,
)


class TestInterfaceDesignWorkflowRetryPolicy:
    """Tests for retry policy configuration."""

    def test_retry_policy_includes_compatibility_error(self):
        """Retry policy should include COMPATIBILITY error type."""
        from aiagent.langgraph.jobGeneratorV2.protocols import ErrorType
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow import (
            InterfaceDesignWorkflow,
        )

        workflow = InterfaceDesignWorkflow()
        policy = workflow.get_retry_policy()

        assert ErrorType.COMPATIBILITY in policy.retry_on


class TestInterfaceDesignWorkflowEmptyTasks:
    """Tests for empty tasks handling."""

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock context."""
        return ExecutionContext(
            job_id="test-job",
            user_requirement="Test",
        )

    @pytest.mark.asyncio
    async def test_execute_empty_tasks_returns_failed(
        self, mock_context: ExecutionContext
    ):
        """Should return FAILED status for empty tasks."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow import (
            InterfaceDesignWorkflow,
        )

        input_data = InterfaceDesignInput(tasks=[])

        workflow = InterfaceDesignWorkflow()
        result = await workflow.execute(input_data, mock_context)

        assert result.status == PhaseStatus.FAILED
        assert result.interfaces == {}


class TestInterfaceDesignWorkflowErrors:
    """Tests for error handling in workflow."""

    @pytest.fixture
    def sample_task(self) -> TaskDefinition:
        """Create sample task."""
        return TaskDefinition(
            id="task_001",
            name="Test Task",
            description="Test",
            task_type="test",
            recommended_api="/test",
            priority=1,
        )

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock context."""
        return ExecutionContext(
            job_id="test-job",
            user_requirement="Test",
        )

    @pytest.mark.asyncio
    async def test_execute_schema_generator_workflow_error(
        self, sample_task: TaskDefinition, mock_context: ExecutionContext
    ):
        """Should re-raise WorkflowError from schema generator."""
        from aiagent.langgraph.jobGeneratorV2.protocols import ErrorType, WorkflowError
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow import (
            InterfaceDesignWorkflow,
        )

        mock_generator = MagicMock()
        mock_generator.generate = AsyncMock(
            side_effect=WorkflowError("Test error", ErrorType.VALIDATION, Phase.INTERFACE_DESIGN)
        )

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.SchemaGeneratorSubWorkflow",
            return_value=mock_generator,
        ):
            workflow = InterfaceDesignWorkflow()
            input_data = InterfaceDesignInput(tasks=[sample_task])

            with pytest.raises(WorkflowError):
                await workflow.execute(input_data, mock_context)

    @pytest.mark.asyncio
    async def test_execute_schema_generator_unexpected_error(
        self, sample_task: TaskDefinition, mock_context: ExecutionContext
    ):
        """Should wrap unexpected error in WorkflowError."""
        from aiagent.langgraph.jobGeneratorV2.protocols import WorkflowError
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow import (
            InterfaceDesignWorkflow,
        )

        mock_generator = MagicMock()
        mock_generator.generate = AsyncMock(
            side_effect=RuntimeError("Unexpected error")
        )

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.SchemaGeneratorSubWorkflow",
            return_value=mock_generator,
        ):
            workflow = InterfaceDesignWorkflow()
            input_data = InterfaceDesignInput(tasks=[sample_task])

            with pytest.raises(WorkflowError) as exc_info:
                await workflow.execute(input_data, mock_context)

            assert "Unexpected error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_schema_generator_empty_result(
        self, sample_task: TaskDefinition, mock_context: ExecutionContext
    ):
        """Should raise WorkflowError when schema generator returns empty."""
        from aiagent.langgraph.jobGeneratorV2.protocols import WorkflowError
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow import (
            InterfaceDesignWorkflow,
        )

        mock_generator = MagicMock()
        mock_generator.generate = AsyncMock(return_value={})  # Empty result

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.SchemaGeneratorSubWorkflow",
            return_value=mock_generator,
        ):
            workflow = InterfaceDesignWorkflow()
            input_data = InterfaceDesignInput(tasks=[sample_task])

            with pytest.raises(WorkflowError) as exc_info:
                await workflow.execute(input_data, mock_context)

            assert "no interfaces" in str(exc_info.value).lower()


class TestInterfaceDesignWorkflowFullFlow:
    """Tests for full workflow execution flow."""

    @pytest.fixture
    def sample_tasks(self) -> list[TaskDefinition]:
        """Create sample tasks."""
        return [
            TaskDefinition(
                id="task_001",
                name="Task 1",
                description="Test",
                task_type="test",
                recommended_api="/test",
                priority=1,
            ),
            TaskDefinition(
                id="task_002",
                name="Task 2",
                description="Test",
                task_type="test",
                recommended_api="/test",
                priority=2,
                dependencies=["task_001"],
            ),
        ]

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock context."""
        return ExecutionContext(
            job_id="test-job",
            user_requirement="Test",
        )

    @pytest.mark.asyncio
    async def test_execute_full_flow_success(
        self, sample_tasks: list[TaskDefinition], mock_context: ExecutionContext
    ):
        """Should execute full flow and return SUCCESS."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow import (
            InterfaceDesignWorkflow,
        )

        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"type": "object"},
                output_schema={"type": "object", "properties": {"data": {"type": "string"}}},
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={"type": "object", "properties": {"data": {"type": "string"}}},
                output_schema={"type": "object"},
            ),
        }

        mock_generator = MagicMock()
        mock_generator.generate = AsyncMock(return_value=interfaces)

        mock_checker = MagicMock()
        mock_checker.check = AsyncMock(
            return_value=CompatibilityReport(is_compatible=True, issues=[])
        )

        mock_enricher = MagicMock()
        mock_enricher.enrich = AsyncMock(
            return_value=(interfaces, EnrichmentReport())
        )

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.SchemaGeneratorSubWorkflow",
            return_value=mock_generator,
        ), patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.CompatibilityCheckerSubWorkflow",
            return_value=mock_checker,
        ), patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.SchemaEnricherSubWorkflow",
            return_value=mock_enricher,
        ):
            workflow = InterfaceDesignWorkflow()
            input_data = InterfaceDesignInput(tasks=sample_tasks)
            result = await workflow.execute(input_data, mock_context)

            assert result.status == PhaseStatus.SUCCESS
            assert len(result.interfaces) == 2
            assert result.compatibility_report.is_compatible is True

    @pytest.mark.asyncio
    async def test_execute_with_incompatibility_returns_needs_retry(
        self, sample_tasks: list[TaskDefinition], mock_context: ExecutionContext
    ):
        """Should return NEEDS_RETRY when compatibility fails."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow import (
            InterfaceDesignWorkflow,
        )

        interfaces = {
            "task_001": InterfaceSchema(task_id="task_001", input_schema={}, output_schema={}),
            "task_002": InterfaceSchema(task_id="task_002", input_schema={}, output_schema={}),
        }

        mock_generator = MagicMock()
        mock_generator.generate = AsyncMock(return_value=interfaces)

        mock_checker = MagicMock()
        mock_checker.check = AsyncMock(
            return_value=CompatibilityReport(
                is_compatible=False,
                issues=["Incompatible types"],
            )
        )

        mock_enricher = MagicMock()
        mock_enricher.enrich = AsyncMock(
            return_value=(interfaces, EnrichmentReport())
        )

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.SchemaGeneratorSubWorkflow",
            return_value=mock_generator,
        ), patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.CompatibilityCheckerSubWorkflow",
            return_value=mock_checker,
        ), patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.workflow.SchemaEnricherSubWorkflow",
            return_value=mock_enricher,
        ):
            workflow = InterfaceDesignWorkflow()
            input_data = InterfaceDesignInput(tasks=sample_tasks)
            result = await workflow.execute(input_data, mock_context)

            assert result.status == PhaseStatus.NEEDS_RETRY
            assert result.compatibility_report.is_compatible is False
            assert len(result.compatibility_report.issues) > 0
