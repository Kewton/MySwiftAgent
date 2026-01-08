"""Tests for TaskBreakdownWorkflow (Issue #342 Phase B).

This module tests the TaskBreakdownWorkflow implementation including:
- TaskDecomposerSubWorkflow (B.1)
- FeasibilitySubWorkflow (B.2)
- AlternativeSubWorkflow (B.3)
- TaskBreakdownWorkflow (B.4)

TDD approach: Tests are written first, then implementation follows.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiagent.langgraph.jobGeneratorV2.context import (
    ContextBuilder,
    ExecutionContext,
    LLMContext,
)
from aiagent.langgraph.jobGeneratorV2.protocols import (
    ErrorType,
    RetryPolicy,
    WorkflowError,
    WorkflowProtocol,
)
from aiagent.langgraph.jobGeneratorV2.types import (
    Capability,
    FeasibilityReport,
    Phase,
    PhaseStatus,
    RelaxationSuggestion,
    TaskBreakdownInput,
    TaskBreakdownOutput,
    TaskDefinition,
)

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_capabilities() -> list[Capability]:
    """Create sample capabilities for testing."""
    return [
        Capability(
            name="Gmail Search",
            description="Search Gmail messages",
            endpoint="/v1/utility/gmail/search",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"messages": {"type": "array"}}},
        ),
        Capability(
            name="Gmail Send",
            description="Send email via Gmail",
            endpoint="/v1/utility/gmail/send",
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
            },
            output_schema={"type": "object", "properties": {"message_id": {"type": "string"}}},
        ),
        Capability(
            name="JSON Output Agent",
            description="LLM with structured JSON output",
            endpoint="/v1/aiagent/utility/jsonoutput",
            input_schema={
                "type": "object",
                "properties": {"user_input": {"type": "string"}},
            },
            output_schema={"type": "object", "properties": {"result": {"type": "object"}}},
        ),
    ]


@pytest.fixture
def execution_context() -> ExecutionContext:
    """Create execution context for testing."""
    return (
        ContextBuilder()
        .with_job_id("test-job-123")
        .with_user_requirement("Search emails and send summary")
        .with_llm_context(LLMContext(model_name="claude-haiku-4-5"))
        .build()
    )


@pytest.fixture
def task_breakdown_input(sample_capabilities: list[Capability]) -> TaskBreakdownInput:
    """Create sample TaskBreakdownInput."""
    return TaskBreakdownInput(
        user_requirement="Search Gmail for invoices and send summary to manager",
        available_capabilities=sample_capabilities,
        max_tasks=10,
    )


@pytest.fixture
def sample_tasks() -> list[TaskDefinition]:
    """Create sample task definitions."""
    return [
        TaskDefinition(
            id="task_001",
            name="Search Gmail",
            description="Search Gmail for invoices",
            task_type="gmail_search",
            recommended_api="/v1/utility/gmail/search",
            priority=1,
            dependencies=[],
        ),
        TaskDefinition(
            id="task_002",
            name="Summarize Results",
            description="Use LLM to summarize search results",
            task_type="llm_processing",
            recommended_api="/v1/aiagent/utility/jsonoutput",
            priority=2,
            dependencies=["task_001"],
        ),
        TaskDefinition(
            id="task_003",
            name="Send Email",
            description="Send summary via email",
            task_type="email_send",
            recommended_api="/v1/utility/gmail/send",
            priority=3,
            dependencies=["task_002"],
        ),
    ]


# =============================================================================
# B.1: TaskDecomposerSubWorkflow Tests
# =============================================================================


class TestTaskDecomposerSubWorkflow:
    """Tests for TaskDecomposerSubWorkflow."""

    @pytest.mark.asyncio
    async def test_decompose_returns_task_definitions(
        self,
        task_breakdown_input: TaskBreakdownInput,
        execution_context: ExecutionContext,
    ):
        """Test that decomposer returns a list of TaskDefinition."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            TaskDecomposerSubWorkflow,
        )

        # Mock LLM response
        mock_llm_response = {
            "tasks": [
                {
                    "task_id": "task_001",
                    "name": "Search Gmail",
                    "description": "Search Gmail for invoices",
                    "dependencies": [],
                    "expected_output": "JSON with email list",
                    "priority": 1,
                    "recommended_apis": [
                        {
                            "api_name": "Gmail Search",
                            "endpoint": "/v1/utility/gmail/search",
                            "method": "POST",
                            "reason": "Fast direct API",
                        }
                    ],
                },
                {
                    "task_id": "task_002",
                    "name": "Send Summary",
                    "description": "Send email summary",
                    "dependencies": ["task_001"],
                    "expected_output": "Send confirmation",
                    "priority": 2,
                    "recommended_apis": [
                        {
                            "api_name": "Gmail Send",
                            "endpoint": "/v1/utility/gmail/send",
                            "method": "POST",
                            "reason": "Direct email send",
                        }
                    ],
                },
            ],
            "overall_summary": "Search and send workflow",
        }

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer.invoke_structured_llm"
        ) as mock_invoke:
            # Create mock tasks using SimpleNamespace to avoid MagicMock.name issues
            from types import SimpleNamespace

            mock_api_1 = SimpleNamespace(
                api_name="Gmail Search",
                endpoint="/v1/utility/gmail/search",
                method="POST",
                reason="Fast direct API",
            )
            mock_api_2 = SimpleNamespace(
                api_name="Gmail Send",
                endpoint="/v1/utility/gmail/send",
                method="POST",
                reason="Direct email send",
            )
            mock_task_1 = SimpleNamespace(
                task_id="task_001",
                name="Search Gmail",
                description="Search Gmail for invoices",
                dependencies=[],
                expected_output="JSON with email list",
                priority=1,
                recommended_apis=[mock_api_1],
            )
            mock_task_2 = SimpleNamespace(
                task_id="task_002",
                name="Send Summary",
                description="Send email summary",
                dependencies=["task_001"],
                expected_output="Send confirmation",
                priority=2,
                recommended_apis=[mock_api_2],
            )

            mock_result = MagicMock()
            mock_result.result = SimpleNamespace(
                tasks=[mock_task_1, mock_task_2],
                overall_summary="Search and send workflow",
            )
            mock_invoke.return_value = mock_result

            decomposer = TaskDecomposerSubWorkflow()
            tasks = await decomposer.decompose(task_breakdown_input, execution_context)

            assert len(tasks) == 2
            assert all(isinstance(t, TaskDefinition) for t in tasks)
            assert tasks[0].id == "task_001"
            assert tasks[0].name == "Search Gmail"
            assert tasks[1].dependencies == ["task_001"]

    @pytest.mark.asyncio
    async def test_decompose_handles_empty_requirement(
        self,
        execution_context: ExecutionContext,
    ):
        """Test that decomposer raises error for empty requirement."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            TaskDecomposerSubWorkflow,
        )

        empty_input = TaskBreakdownInput(
            user_requirement="",
            available_capabilities=[],
            max_tasks=10,
        )

        decomposer = TaskDecomposerSubWorkflow()
        with pytest.raises(WorkflowError) as exc_info:
            await decomposer.decompose(empty_input, execution_context)

        assert exc_info.value.error_type == ErrorType.VALIDATION

    @pytest.mark.asyncio
    async def test_decompose_respects_max_tasks(
        self,
        task_breakdown_input: TaskBreakdownInput,
        execution_context: ExecutionContext,
    ):
        """Test that decomposer respects max_tasks limit."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            TaskDecomposerSubWorkflow,
        )

        # Create input with max_tasks=2
        limited_input = TaskBreakdownInput(
            user_requirement=task_breakdown_input.user_requirement,
            available_capabilities=task_breakdown_input.available_capabilities,
            max_tasks=2,
        )

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer.invoke_structured_llm"
        ) as mock_invoke:
            # Mock returns 3 tasks but we requested max 2
            from types import SimpleNamespace

            mock_tasks = [
                SimpleNamespace(
                    task_id=f"task_00{i}",
                    name=f"Task {i}",
                    description=f"Description {i}",
                    dependencies=[],
                    expected_output="output",
                    priority=i,
                    recommended_apis=[],
                )
                for i in range(1, 4)
            ]
            mock_result = MagicMock()
            mock_result.result = SimpleNamespace(
                tasks=mock_tasks,
                overall_summary="Test workflow",
            )
            mock_invoke.return_value = mock_result

            decomposer = TaskDecomposerSubWorkflow()
            tasks = await decomposer.decompose(limited_input, execution_context)

            # Should be limited to 2 tasks
            assert len(tasks) <= 2


# =============================================================================
# B.2: FeasibilitySubWorkflow Tests
# =============================================================================


class TestFeasibilitySubWorkflow:
    """Tests for FeasibilitySubWorkflow."""

    @pytest.mark.asyncio
    async def test_check_returns_feasibility_report(
        self,
        sample_tasks: list[TaskDefinition],
        sample_capabilities: list[Capability],
        execution_context: ExecutionContext,
    ):
        """Test that feasibility check returns FeasibilityReport."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.feasibility import (
            FeasibilitySubWorkflow,
        )

        feasibility = FeasibilitySubWorkflow(capabilities=sample_capabilities)
        report = await feasibility.check(sample_tasks, execution_context)

        assert isinstance(report, FeasibilityReport)
        assert report.is_feasible is True
        assert len(report.infeasible_tasks) == 0

    @pytest.mark.asyncio
    async def test_check_identifies_infeasible_tasks(
        self,
        sample_capabilities: list[Capability],
        execution_context: ExecutionContext,
    ):
        """Test that feasibility check identifies infeasible tasks."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.feasibility import (
            FeasibilitySubWorkflow,
        )

        # Task with unsupported API
        infeasible_tasks = [
            TaskDefinition(
                id="task_001",
                name="Slack Send",
                description="Send message to Slack",
                task_type="slack_send",
                recommended_api="/v1/utility/slack/send",  # Not in capabilities
                priority=1,
                dependencies=[],
            ),
        ]

        feasibility = FeasibilitySubWorkflow(capabilities=sample_capabilities)
        report = await feasibility.check(infeasible_tasks, execution_context)

        assert report.is_feasible is False
        assert "task_001" in report.infeasible_tasks
        assert len(report.recommendations) > 0

    @pytest.mark.asyncio
    async def test_check_with_empty_tasks(
        self,
        sample_capabilities: list[Capability],
        execution_context: ExecutionContext,
    ):
        """Test feasibility check with empty task list."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.feasibility import (
            FeasibilitySubWorkflow,
        )

        feasibility = FeasibilitySubWorkflow(capabilities=sample_capabilities)
        report = await feasibility.check([], execution_context)

        assert report.is_feasible is True
        assert len(report.infeasible_tasks) == 0

    @pytest.mark.asyncio
    async def test_check_loads_capabilities_from_yaml(
        self,
        sample_tasks: list[TaskDefinition],
        execution_context: ExecutionContext,
    ):
        """Test that capabilities can be loaded from YAML config."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.feasibility import (
            FeasibilitySubWorkflow,
            load_capabilities_from_yaml,
        )

        capabilities = load_capabilities_from_yaml()
        assert len(capabilities) > 0

        feasibility = FeasibilitySubWorkflow(capabilities=capabilities)
        report = await feasibility.check(sample_tasks, execution_context)
        assert isinstance(report, FeasibilityReport)


# =============================================================================
# B.3: AlternativeSubWorkflow Tests
# =============================================================================


class TestAlternativeSubWorkflow:
    """Tests for AlternativeSubWorkflow."""

    @pytest.mark.asyncio
    async def test_generate_returns_alternative_tasks(
        self,
        sample_capabilities: list[Capability],
        execution_context: ExecutionContext,
    ):
        """Test that alternative generator creates alternative tasks."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.alternative import (
            AlternativeSubWorkflow,
        )

        infeasible_tasks = [
            TaskDefinition(
                id="task_001",
                name="Slack Send",
                description="Send notification to Slack",
                task_type="notification",
                recommended_api="/v1/utility/slack/send",
                priority=1,
                dependencies=[],
            ),
        ]

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.alternative.invoke_structured_llm"
        ) as mock_invoke:
            from types import SimpleNamespace

            mock_alt_task = SimpleNamespace(
                task_id="task_001_alt",
                name="Email Send",
                description="Send notification via email",
                dependencies=[],
                expected_output="Send confirmation",
                priority=1,
                recommended_apis=[
                    {
                        "api_name": "Gmail Send",
                        "endpoint": "/v1/utility/gmail/send",
                        "method": "POST",
                        "reason": "Alternative to Slack",
                    }
                ],
            )
            mock_alternative = SimpleNamespace(
                original_task_id="task_001",
                alternative_task=mock_alt_task,
                reason="Gmail is available",
            )
            mock_result = MagicMock()
            mock_result.result = SimpleNamespace(
                alternatives=[mock_alternative],
                relaxation_needed=False,
                relaxation_reason="",
                tasks_needing_relaxation=[],
            )
            mock_invoke.return_value = mock_result

            alternative = AlternativeSubWorkflow(capabilities=sample_capabilities)
            alt_tasks, suggestions = await alternative.generate(
                infeasible_tasks, execution_context
            )

            assert len(alt_tasks) == 1
            assert alt_tasks[0].name == "Email Send"
            assert len(suggestions) == 0  # No relaxation needed

    @pytest.mark.asyncio
    async def test_generate_returns_relaxation_when_no_alternative(
        self,
        sample_capabilities: list[Capability],
        execution_context: ExecutionContext,
    ):
        """Test relaxation suggestion when no alternative exists."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.alternative import (
            AlternativeSubWorkflow,
        )

        infeasible_tasks = [
            TaskDefinition(
                id="task_001",
                name="Custom API Call",
                description="Call non-existent API",
                task_type="custom",
                recommended_api="/v1/nonexistent/api",
                priority=1,
                dependencies=[],
            ),
        ]

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.alternative.invoke_structured_llm"
        ) as mock_invoke:
            from types import SimpleNamespace

            mock_result = MagicMock()
            mock_result.result = SimpleNamespace(
                alternatives=[],  # No alternatives found
                relaxation_needed=True,
                relaxation_reason="No API supports this functionality",
                tasks_needing_relaxation=["task_001"],
            )
            mock_invoke.return_value = mock_result

            alternative = AlternativeSubWorkflow(capabilities=sample_capabilities)
            alt_tasks, suggestions = await alternative.generate(
                infeasible_tasks, execution_context
            )

            assert len(alt_tasks) == 0
            assert len(suggestions) == 1
            assert isinstance(suggestions[0], RelaxationSuggestion)

    @pytest.mark.asyncio
    async def test_generate_with_empty_infeasible_tasks(
        self,
        sample_capabilities: list[Capability],
        execution_context: ExecutionContext,
    ):
        """Test alternative generation with empty infeasible task list."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.alternative import (
            AlternativeSubWorkflow,
        )

        alternative = AlternativeSubWorkflow(capabilities=sample_capabilities)
        alt_tasks, suggestions = await alternative.generate([], execution_context)

        assert len(alt_tasks) == 0
        assert len(suggestions) == 0


# =============================================================================
# B.4: TaskBreakdownWorkflow Tests
# =============================================================================


class TestTaskBreakdownWorkflow:
    """Tests for TaskBreakdownWorkflow."""

    def test_implements_workflow_protocol(self):
        """Test that TaskBreakdownWorkflow implements WorkflowProtocol."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow import (
            TaskBreakdownWorkflow,
        )

        workflow = TaskBreakdownWorkflow()
        assert isinstance(workflow, WorkflowProtocol)

    def test_get_retry_policy(self):
        """Test that workflow returns proper retry policy."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow import (
            TaskBreakdownWorkflow,
        )

        workflow = TaskBreakdownWorkflow()
        policy = workflow.get_retry_policy()

        assert isinstance(policy, RetryPolicy)
        assert policy.max_retries >= 1

    @pytest.mark.asyncio
    async def test_execute_success_path(
        self,
        task_breakdown_input: TaskBreakdownInput,
        execution_context: ExecutionContext,
        sample_tasks: list[TaskDefinition],
    ):
        """Test successful workflow execution."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow import (
            TaskBreakdownWorkflow,
        )

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow.TaskDecomposerSubWorkflow"
        ) as MockDecomposer, patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow.FeasibilitySubWorkflow"
        ) as MockFeasibility:
            # Mock decomposer
            mock_decomposer = AsyncMock()
            mock_decomposer.decompose.return_value = sample_tasks
            MockDecomposer.return_value = mock_decomposer

            # Mock feasibility
            mock_feasibility = AsyncMock()
            mock_feasibility.check.return_value = FeasibilityReport(
                is_feasible=True,
                infeasible_tasks=[],
                recommendations=[],
            )
            MockFeasibility.return_value = mock_feasibility

            workflow = TaskBreakdownWorkflow()
            output = await workflow.execute(task_breakdown_input, execution_context)

            assert isinstance(output, TaskBreakdownOutput)
            assert output.status == PhaseStatus.SUCCESS
            assert len(output.tasks) == 3
            assert output.feasibility_report is not None
            assert output.feasibility_report.is_feasible is True

    @pytest.mark.asyncio
    async def test_execute_with_infeasible_tasks_alternatives_found(
        self,
        task_breakdown_input: TaskBreakdownInput,
        execution_context: ExecutionContext,
    ):
        """Test workflow with infeasible tasks that have alternatives."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow import (
            TaskBreakdownWorkflow,
        )

        original_task = TaskDefinition(
            id="task_001",
            name="Slack Send",
            description="Send to Slack",
            task_type="notification",
            recommended_api="/v1/utility/slack/send",
            priority=1,
            dependencies=[],
        )

        alternative_task = TaskDefinition(
            id="task_001_alt",
            name="Email Send",
            description="Send via email",
            task_type="notification",
            recommended_api="/v1/utility/gmail/send",
            priority=1,
            dependencies=[],
        )

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow.TaskDecomposerSubWorkflow"
        ) as MockDecomposer, patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow.FeasibilitySubWorkflow"
        ) as MockFeasibility, patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow.AlternativeSubWorkflow"
        ) as MockAlternative:
            # Mock decomposer
            mock_decomposer = AsyncMock()
            mock_decomposer.decompose.return_value = [original_task]
            MockDecomposer.return_value = mock_decomposer

            # Mock feasibility - task is infeasible
            mock_feasibility = AsyncMock()
            mock_feasibility.check.return_value = FeasibilityReport(
                is_feasible=False,
                infeasible_tasks=["task_001"],
                recommendations=["Use email instead"],
            )
            MockFeasibility.return_value = mock_feasibility

            # Mock alternative - provides alternative
            mock_alternative = AsyncMock()
            mock_alternative.generate.return_value = ([alternative_task], [])
            MockAlternative.return_value = mock_alternative

            workflow = TaskBreakdownWorkflow()
            output = await workflow.execute(task_breakdown_input, execution_context)

            assert output.status == PhaseStatus.SUCCESS
            assert len(output.tasks) == 1
            assert output.tasks[0].name == "Email Send"

    @pytest.mark.asyncio
    async def test_execute_needs_relaxation(
        self,
        task_breakdown_input: TaskBreakdownInput,
        execution_context: ExecutionContext,
    ):
        """Test workflow returns NEEDS_RELAXATION when no alternatives."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow import (
            TaskBreakdownWorkflow,
        )

        original_task = TaskDefinition(
            id="task_001",
            name="Custom Task",
            description="Unsupported task",
            task_type="custom",
            recommended_api="/v1/nonexistent/api",
            priority=1,
            dependencies=[],
        )

        relaxation = RelaxationSuggestion(
            original_requirement="Custom task",
            suggested_alternative="Consider using available APIs",
            reason="No API supports this",
        )

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow.TaskDecomposerSubWorkflow"
        ) as MockDecomposer, patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow.FeasibilitySubWorkflow"
        ) as MockFeasibility, patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow.AlternativeSubWorkflow"
        ) as MockAlternative:
            # Mock decomposer
            mock_decomposer = AsyncMock()
            mock_decomposer.decompose.return_value = [original_task]
            MockDecomposer.return_value = mock_decomposer

            # Mock feasibility - task is infeasible
            mock_feasibility = AsyncMock()
            mock_feasibility.check.return_value = FeasibilityReport(
                is_feasible=False,
                infeasible_tasks=["task_001"],
                recommendations=[],
            )
            MockFeasibility.return_value = mock_feasibility

            # Mock alternative - no alternative, returns relaxation
            mock_alternative = AsyncMock()
            mock_alternative.generate.return_value = ([], [relaxation])
            MockAlternative.return_value = mock_alternative

            workflow = TaskBreakdownWorkflow()
            output = await workflow.execute(task_breakdown_input, execution_context)

            assert output.status == PhaseStatus.NEEDS_RELAXATION
            assert len(output.relaxation_suggestions) == 1
            assert output.relaxation_suggestions[0].reason == "No API supports this"

    @pytest.mark.asyncio
    async def test_execute_handles_decomposer_error(
        self,
        task_breakdown_input: TaskBreakdownInput,
        execution_context: ExecutionContext,
    ):
        """Test workflow handles decomposer errors."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow import (
            TaskBreakdownWorkflow,
        )

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow.TaskDecomposerSubWorkflow"
        ) as MockDecomposer:
            mock_decomposer = AsyncMock()
            mock_decomposer.decompose.side_effect = WorkflowError(
                "LLM failed",
                ErrorType.TRANSIENT,
                Phase.TASK_BREAKDOWN,
            )
            MockDecomposer.return_value = mock_decomposer

            workflow = TaskBreakdownWorkflow()
            with pytest.raises(WorkflowError) as exc_info:
                await workflow.execute(task_breakdown_input, execution_context)

            assert exc_info.value.error_type == ErrorType.TRANSIENT


# =============================================================================
# B.5: Integration Tests
# =============================================================================


class TestTaskBreakdownWorkflowIntegration:
    """Integration tests for TaskBreakdownWorkflow."""

    @pytest.mark.asyncio
    async def test_workflow_full_pipeline_mocked(
        self,
        execution_context: ExecutionContext,
    ):
        """Test full pipeline with mocked LLM calls."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow import (
            TaskBreakdownWorkflow,
        )

        input_data = TaskBreakdownInput(
            user_requirement="Search Gmail for invoices and send summary to manager",
            available_capabilities=[],
            max_tasks=5,
        )

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer.invoke_structured_llm"
        ) as mock_llm, patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.feasibility.load_capabilities_from_yaml"
        ) as mock_load_caps:
            # Mock capabilities loading
            mock_load_caps.return_value = [
                Capability(
                    name="Gmail Search",
                    description="Search Gmail",
                    endpoint="/v1/utility/gmail/search",
                ),
                Capability(
                    name="Gmail Send",
                    description="Send email",
                    endpoint="/v1/utility/gmail/send",
                ),
                Capability(
                    name="JSON Output",
                    description="LLM JSON output",
                    endpoint="/v1/aiagent/utility/jsonoutput",
                ),
            ]

            # Mock LLM response
            from types import SimpleNamespace

            mock_api_1 = SimpleNamespace(
                api_name="Gmail Search",
                endpoint="/v1/utility/gmail/search",
                method="POST",
                reason="Direct API",
            )
            mock_api_2 = SimpleNamespace(
                api_name="Gmail Send",
                endpoint="/v1/utility/gmail/send",
                method="POST",
                reason="Direct API",
            )
            mock_task_1 = SimpleNamespace(
                task_id="task_001",
                name="Search Gmail",
                description="Search for invoices",
                dependencies=[],
                expected_output="Email list",
                priority=1,
                recommended_apis=[mock_api_1],
            )
            mock_task_2 = SimpleNamespace(
                task_id="task_002",
                name="Send Summary",
                description="Send summary email",
                dependencies=["task_001"],
                expected_output="Send confirmation",
                priority=2,
                recommended_apis=[mock_api_2],
            )

            mock_result = MagicMock()
            mock_result.result = SimpleNamespace(
                tasks=[mock_task_1, mock_task_2],
                overall_summary="Search and send workflow",
            )
            mock_llm.return_value = mock_result

            workflow = TaskBreakdownWorkflow()
            output = await workflow.execute(input_data, execution_context)

            assert output.status == PhaseStatus.SUCCESS
            assert len(output.tasks) >= 1

    @pytest.mark.asyncio
    async def test_workflow_registered_in_orchestrator(
        self,
        execution_context: ExecutionContext,
    ):
        """Test that workflow can be registered in orchestrator."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )
        from aiagent.langgraph.jobGeneratorV2.recovery import ErrorRecoveryManager
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow import (
            TaskBreakdownWorkflow,
        )

        orchestrator = JobGenerationOrchestrator(
            recovery_manager=ErrorRecoveryManager()
        )
        workflow = TaskBreakdownWorkflow()

        orchestrator.register_workflow(Phase.TASK_BREAKDOWN, workflow)

        registered = orchestrator.get_workflow(Phase.TASK_BREAKDOWN)
        assert registered is workflow


# =============================================================================
# Additional Coverage Tests
# =============================================================================


class TestTaskDecomposerHelperFunctions:
    """Tests for helper functions in decomposer module."""

    def test_infer_task_type_gmail_search(self):
        """Test task type inference for gmail search."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            _infer_task_type,
        )

        result = _infer_task_type("Search emails", "/v1/utility/gmail/search")
        assert result == "gmail_search"

    def test_infer_task_type_gmail_send(self):
        """Test task type inference for gmail send."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            _infer_task_type,
        )

        result = _infer_task_type("Send email", "/v1/utility/gmail/send")
        assert result == "email_send"

    def test_infer_task_type_drive(self):
        """Test task type inference for Google Drive."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            _infer_task_type,
        )

        result = _infer_task_type("Upload file", "/v1/utility/drive/upload")
        assert result == "file_upload"

    def test_infer_task_type_jsonoutput(self):
        """Test task type inference for JSON output."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            _infer_task_type,
        )

        result = _infer_task_type("Process data", "/v1/aiagent/utility/jsonoutput")
        assert result == "llm_processing"

    def test_infer_task_type_tts(self):
        """Test task type inference for text-to-speech."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            _infer_task_type,
        )

        result = _infer_task_type("Convert to audio", "/v1/utility/text_to_speech")
        assert result == "tts"

    def test_infer_task_type_web_search(self):
        """Test task type inference for web search."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            _infer_task_type,
        )

        result = _infer_task_type("Find info", "/v1/utility/google_search")
        assert result == "web_search"

    def test_infer_task_type_from_description(self):
        """Test task type inference from description."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            _infer_task_type,
        )

        assert _infer_task_type("Search for documents", "") == "search"
        assert _infer_task_type("Send notification", "") == "notification"
        assert _infer_task_type("Upload report", "") == "file_upload"
        assert _infer_task_type("Summarize text", "") == "llm_processing"
        assert _infer_task_type("Unknown task", "") == "general"

    def test_convert_to_task_definition_without_apis(self):
        """Test converting task item without recommended APIs."""
        from types import SimpleNamespace

        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            _convert_to_task_definition,
        )

        task_item = SimpleNamespace(
            task_id="task_001",
            name="Test Task",
            description="A test task",
            dependencies=[],
            priority=5,
            recommended_apis=[],
        )

        result = _convert_to_task_definition(task_item)
        assert result.id == "task_001"
        assert result.name == "Test Task"
        assert result.recommended_api == ""


class TestFeasibilityHelperFunctions:
    """Tests for helper functions in feasibility module."""

    def test_is_api_available_exact_match(self):
        """Test API availability with exact match."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.feasibility import (
            _is_api_available,
        )

        caps = [
            Capability(
                name="Gmail Send",
                description="Send email",
                endpoint="/v1/utility/gmail/send",
            )
        ]

        assert _is_api_available("/v1/utility/gmail/send", caps) is True
        assert _is_api_available("/v1/utility/slack/send", caps) is False

    def test_is_api_available_empty_api(self):
        """Test API availability with empty API string."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.feasibility import (
            _is_api_available,
        )

        assert _is_api_available("", []) is True

    def test_parse_api_to_capability_invalid(self):
        """Test parsing invalid API definition."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.feasibility import (
            _parse_api_to_capability,
        )

        assert _parse_api_to_capability({}) is None
        assert _parse_api_to_capability({"name": "Test"}) is None
        assert _parse_api_to_capability({"endpoint": "/test"}) is None

    def test_parse_api_to_capability_valid(self):
        """Test parsing valid API definition."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.feasibility import (
            _parse_api_to_capability,
        )

        api = {
            "name": "Gmail Send",
            "endpoint": "/v1/utility/gmail/send",
            "description": "Send email",
            "request_schema": {
                "to": {"type": "string", "required": True},
                "subject": {"type": "string", "description": "Email subject"},
            },
            "response_schema": {
                "message_id": {"type": "string", "description": "Message ID"},
            },
        }

        result = _parse_api_to_capability(api)
        assert result is not None
        assert result.name == "Gmail Send"
        assert result.endpoint == "/v1/utility/gmail/send"
        assert "to" in result.input_schema["properties"]
        assert "message_id" in result.output_schema["properties"]

    def test_find_similar_capabilities(self):
        """Test finding similar capabilities."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.feasibility import (
            _find_similar_capabilities,
        )

        task = TaskDefinition(
            id="task_001",
            name="Send notification",
            description="Send email notification to user",
            task_type="notification",
            recommended_api="/v1/slack/send",
            priority=1,
            dependencies=[],
        )

        caps = [
            Capability(
                name="Gmail Send",
                description="Send email to user",
                endpoint="/v1/utility/gmail/send",
            ),
            Capability(
                name="TTS",
                description="Text to speech conversion",
                endpoint="/v1/utility/tts",
            ),
        ]

        similar = _find_similar_capabilities(task, caps)
        assert len(similar) >= 1
        assert similar[0].name == "Gmail Send"


class TestAlternativeHelperFunctions:
    """Tests for helper functions in alternative module."""

    def test_build_alternative_system_prompt(self):
        """Test building alternative system prompt."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.alternative import (
            _build_alternative_system_prompt,
        )

        caps = [
            Capability(
                name="Gmail Send",
                description="Send email",
                endpoint="/v1/utility/gmail/send",
            )
        ]

        prompt = _build_alternative_system_prompt(caps)
        assert "Gmail Send" in prompt
        assert "/v1/utility/gmail/send" in prompt
        assert "alternative" in prompt.lower()

    def test_build_alternative_user_prompt(self):
        """Test building alternative user prompt."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.alternative import (
            _build_alternative_user_prompt,
        )

        tasks = [
            TaskDefinition(
                id="task_001",
                name="Slack Send",
                description="Send to Slack",
                task_type="notification",
                recommended_api="/v1/slack/send",
                priority=1,
                dependencies=[],
            )
        ]

        prompt = _build_alternative_user_prompt(tasks)
        assert "task_001" in prompt
        assert "Slack Send" in prompt
        assert "/v1/slack/send" in prompt


class TestWorkflowUpdateDependencies:
    """Tests for dependency update helper."""

    def test_update_dependencies(self):
        """Test updating task dependencies after replacement."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow import (
            _update_dependencies,
        )

        original_tasks = [
            TaskDefinition(
                id="task_001",
                name="Original",
                description="Original task",
                task_type="test",
                recommended_api="",
                priority=1,
                dependencies=[],
            )
        ]

        alternative_tasks = [
            TaskDefinition(
                id="task_001_alt",
                name="Alternative",
                description="Alternative task",
                task_type="test",
                recommended_api="",
                priority=1,
                dependencies=[],
            )
        ]

        tasks_with_deps = [
            TaskDefinition(
                id="task_002",
                name="Dependent",
                description="Depends on original",
                task_type="test",
                recommended_api="",
                priority=2,
                dependencies=["task_001"],
            ),
            alternative_tasks[0],
        ]

        updated = _update_dependencies(
            tasks_with_deps, original_tasks, alternative_tasks
        )

        # The task with dependency on task_001 should now depend on task_001_alt
        dependent_task = next(t for t in updated if t.id == "task_002")
        assert "task_001_alt" in dependent_task.dependencies


class TestValidationFunctions:
    """Tests for validation functions."""

    def test_validate_task_breakdown_response_none(self):
        """Test validation raises for None response."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            _validate_task_breakdown_response,
        )

        with pytest.raises(ValueError) as exc_info:
            _validate_task_breakdown_response(None)

        assert "LLM returned None" in str(exc_info.value)

    def test_validate_task_breakdown_response_no_tasks(self):
        """Test validation raises when tasks field is None."""
        from types import SimpleNamespace

        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            _validate_task_breakdown_response,
        )

        response = SimpleNamespace(tasks=None, overall_summary="test")

        with pytest.raises(ValueError) as exc_info:
            _validate_task_breakdown_response(response)

        assert "missing 'tasks'" in str(exc_info.value)

    def test_validate_task_breakdown_response_empty_tasks(self):
        """Test validation raises for empty tasks list."""
        from types import SimpleNamespace

        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            _validate_task_breakdown_response,
        )

        response = SimpleNamespace(tasks=[], overall_summary="test")

        with pytest.raises(ValueError) as exc_info:
            _validate_task_breakdown_response(response)

        assert "empty task list" in str(exc_info.value)


class TestFeasibilityRecommendations:
    """Tests for recommendation generation."""

    def test_generate_recommendations_slack_task(self):
        """Test recommendations for Slack task."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.feasibility import (
            _generate_recommendations,
        )

        tasks = [
            TaskDefinition(
                id="task_001",
                name="Slack Message",
                description="Send Slack message",
                task_type="slack",
                recommended_api="/v1/utility/slack/send",
                priority=1,
                dependencies=[],
            )
        ]

        caps = [
            Capability(
                name="Gmail Send",
                description="Send email",
                endpoint="/v1/utility/gmail/send",
            )
        ]

        recommendations = _generate_recommendations(tasks, caps)
        assert len(recommendations) == 1
        assert "Gmail" in recommendations[0] or "email" in recommendations[0].lower()

    def test_generate_recommendations_notification_task(self):
        """Test recommendations for notification task."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.feasibility import (
            _generate_recommendations,
        )

        tasks = [
            TaskDefinition(
                id="task_001",
                name="Send Alert",
                description="Send alert to user",
                task_type="notification",
                recommended_api="/v1/utility/alert/send",
                priority=1,
                dependencies=[],
            )
        ]

        caps = []  # No capabilities

        recommendations = _generate_recommendations(tasks, caps)
        assert len(recommendations) == 1
        assert "notification" in recommendations[0].lower() or "alert" in recommendations[0].lower()


class TestAlternativeSubWorkflowLLMError:
    """Tests for AlternativeSubWorkflow LLM error handling."""

    @pytest.mark.asyncio
    async def test_generate_handles_llm_error(
        self,
        sample_capabilities: list[Capability],
        execution_context: ExecutionContext,
    ):
        """Test that LLM errors are handled gracefully."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.alternative import (
            AlternativeSubWorkflow,
        )
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredLLMError,
        )

        infeasible_tasks = [
            TaskDefinition(
                id="task_001",
                name="Slack Send",
                description="Send to Slack",
                task_type="notification",
                recommended_api="/v1/utility/slack/send",
                priority=1,
                dependencies=[],
            )
        ]

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.alternative.invoke_structured_llm"
        ) as mock_invoke:
            mock_invoke.side_effect = StructuredLLMError("LLM timeout")

            alternative = AlternativeSubWorkflow(capabilities=sample_capabilities)
            alt_tasks, suggestions = await alternative.generate(
                infeasible_tasks, execution_context
            )

            # On LLM error, should return relaxation suggestions for all tasks
            assert len(alt_tasks) == 0
            assert len(suggestions) == 1
            assert "LLM error" in suggestions[0].suggested_alternative


class TestWorkflowEdgeCases:
    """Tests for workflow edge cases."""

    @pytest.mark.asyncio
    async def test_execute_with_unexpected_exception(
        self,
        task_breakdown_input: TaskBreakdownInput,
        execution_context: ExecutionContext,
    ):
        """Test workflow handles unexpected exceptions."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow import (
            TaskBreakdownWorkflow,
        )

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow.TaskDecomposerSubWorkflow"
        ) as MockDecomposer:
            mock_decomposer = AsyncMock()
            mock_decomposer.decompose.side_effect = RuntimeError("Unexpected error")
            MockDecomposer.return_value = mock_decomposer

            workflow = TaskBreakdownWorkflow()
            with pytest.raises(WorkflowError) as exc_info:
                await workflow.execute(task_breakdown_input, execution_context)

            assert "Unexpected error" in str(exc_info.value)
            assert exc_info.value.error_type == ErrorType.TRANSIENT

    @pytest.mark.asyncio
    async def test_execute_no_tasks_from_decomposer(
        self,
        task_breakdown_input: TaskBreakdownInput,
        execution_context: ExecutionContext,
    ):
        """Test workflow handles empty task list from decomposer."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow import (
            TaskBreakdownWorkflow,
        )

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.workflow.TaskDecomposerSubWorkflow"
        ) as MockDecomposer:
            mock_decomposer = AsyncMock()
            mock_decomposer.decompose.return_value = []  # Empty list
            MockDecomposer.return_value = mock_decomposer

            workflow = TaskBreakdownWorkflow()
            with pytest.raises(WorkflowError) as exc_info:
                await workflow.execute(task_breakdown_input, execution_context)

            assert "no tasks" in str(exc_info.value).lower()


class TestInferTaskTypeGmailGeneric:
    """Test gmail generic type."""

    def test_infer_task_type_gmail_generic(self):
        """Test generic gmail type inference."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            _infer_task_type,
        )

        result = _infer_task_type("Gmail operations", "/v1/utility/gmail/labels")
        assert result == "gmail"
