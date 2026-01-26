"""
Issue #409 Integration Tests - Multiple Independent Tasks Dataflow

TC-008: Multiple independent tasks integration
TC-010: Issue #408 validation integration

These tests verify that the system correctly handles workflows with multiple
independent tasks (dependencies=[]), ensuring each receives user input directly.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
from aiagent.langgraph.jobGeneratorV2.types import (
    InterfaceSchema,
    TaskDefinition,
)
from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
    MasterManagerSubWorkflow,
)


@pytest.mark.integration
class TestIssue409Integration:
    """Issue #409: Integration tests for multiple independent tasks."""

    @pytest.fixture
    def mock_jobqueue_client(self):
        """Create a mock JobqueueClient for testing."""
        client = MagicMock()

        # Mock interface master creation
        client.create_interface_master = AsyncMock(
            side_effect=lambda **kwargs: {"id": f"im_{kwargs.get('name', 'unknown')}"}
        )

        # Mock task master creation
        client.create_task_master = AsyncMock(
            side_effect=lambda **kwargs: {"id": f"tm_{kwargs.get('name', 'unknown')}"}
        )

        # Mock job master creation
        client.create_job_master = AsyncMock(return_value={"id": "jm_test"})

        # Mock job master task association
        client.add_task_to_workflow = AsyncMock(
            side_effect=lambda **kwargs: {"id": f"jmt_{kwargs.get('order', 0)}"}
        )

        return client

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock execution context."""
        return ExecutionContext(
            job_id="test-job-409",
            user_requirement="Test multiple independent tasks",
            max_phase_retries=3,
            max_total_retries=5,
        )

    @pytest.fixture
    def multiple_independent_tasks(self) -> list[TaskDefinition]:
        """Create tasks with multiple independent tasks (TC-008 scenario)."""
        return [
            TaskDefinition(
                id="task_001",
                name="Keyword Search",
                description="Search by keyword",
                task_type="fetch",
                recommended_api="/api/search",
                priority=1,
                dependencies=[],  # Independent
            ),
            TaskDefinition(
                id="task_002",
                name="Email Lookup",
                description="Lookup email addresses",
                task_type="fetch",
                recommended_api="/api/email/lookup",
                priority=2,
                dependencies=[],  # Also independent
            ),
            TaskDefinition(
                id="task_003",
                name="Combine Results",
                description="Combine search and email results",
                task_type="process",
                recommended_api="/api/combine",
                priority=3,
                dependencies=["task_001", "task_002"],  # Depends on both
            ),
        ]

    @pytest.fixture
    def multiple_independent_interfaces(self) -> dict[str, InterfaceSchema]:
        """Create interfaces for multiple independent tasks."""
        return {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string"},
                        "project": {"type": "string"},
                    },
                    "required": ["keyword"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "search_results": {"type": "array"},
                    },
                },
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={
                    "type": "object",
                    "properties": {
                        "recipient_email": {"type": "string"},
                        "project": {"type": "string"},
                    },
                    "required": ["recipient_email"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "email_info": {"type": "object"},
                    },
                },
            ),
            "task_003": InterfaceSchema(
                task_id="task_003",
                input_schema={
                    "type": "object",
                    "properties": {
                        "search_results": {"type": "array"},
                        "email_info": {"type": "object"},
                        "project": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "combined_report": {"type": "string"},
                    },
                },
            ),
        }

    @pytest.mark.asyncio
    async def test_tc008_multiple_independent_tasks_use_user_input(
        self,
        mock_jobqueue_client,
        mock_context: ExecutionContext,
        multiple_independent_tasks: list[TaskDefinition],
        multiple_independent_interfaces: dict[str, InterfaceSchema],
    ):
        """TC-008: Multiple independent tasks both use user_input.

        Issue #409: AC-1, AC-4 - Both independent tasks should reference
        {{job.body.user_input}} instead of previous task's output.
        """
        manager = MasterManagerSubWorkflow(
            engine="taskflow",
            jobqueue_client=mock_jobqueue_client,
        )

        result = await manager.create_masters(
            tasks=multiple_independent_tasks,
            interfaces=multiple_independent_interfaces,
            project_id="test-project",
            context=mock_context,
        )

        # Verify result structure
        assert result is not None
        assert len(result.task_masters) == 3

        # Capture the body_templates passed to create_task_master
        create_calls = mock_jobqueue_client.create_task_master.call_args_list

        # Extract body_templates from calls
        body_templates = {}
        for call in create_calls:
            name = call.kwargs.get("name")
            body_template = call.kwargs.get("body_template")
            body_templates[name] = body_template

        # Both independent tasks should use user_input
        assert (
            body_templates["Keyword Search"]["inputs"] == "{{job.body.user_input}}"
        ), (
            f"First independent task should use user_input, got: "
            f"{body_templates['Keyword Search']['inputs']}"
        )
        assert body_templates["Email Lookup"]["inputs"] == "{{job.body.user_input}}", (
            f"Second independent task should use user_input, got: "
            f"{body_templates['Email Lookup']['inputs']}"
        )

        # Dependent task should use field references from dependencies
        combine_inputs = body_templates["Combine Results"]["inputs"]
        assert isinstance(combine_inputs, dict), (
            f"Dependent task should have dict inputs, got: {type(combine_inputs)}"
        )

    @pytest.mark.asyncio
    async def test_tc010_issue408_validation_with_merged_schema(
        self,
        mock_jobqueue_client,
        mock_context: ExecutionContext,
    ):
        """TC-010: Issue #408 validation works with merged user_input_schema.

        Issue #409: AC-3 - Ensure that Issue #408's field validation uses
        the merged schema from all independent tasks.
        """
        # Create tasks where dependent task references fields from different independent tasks
        tasks = [
            TaskDefinition(
                id="task_001",
                name="Task A",
                description="Independent task A",
                task_type="fetch",
                recommended_api="/api/a",
                priority=1,
                dependencies=[],
            ),
            TaskDefinition(
                id="task_002",
                name="Task B",
                description="Independent task B",
                task_type="fetch",
                recommended_api="/api/b",
                priority=2,
                dependencies=[],
            ),
            TaskDefinition(
                id="task_003",
                name="Task C",
                description="Uses field from both A and B",
                task_type="process",
                recommended_api="/api/c",
                priority=3,
                dependencies=["task_001", "task_002"],
            ),
        ]

        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {
                        "field_a": {"type": "string"},
                        "project": {"type": "string"},
                    },
                    "required": ["field_a"],
                },
                output_schema={
                    "type": "object",
                    "properties": {"output_a": {"type": "string"}},
                },
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={
                    "type": "object",
                    "properties": {
                        "field_b": {"type": "integer"},
                        "project": {"type": "string"},
                    },
                    "required": ["field_b"],
                },
                output_schema={
                    "type": "object",
                    "properties": {"output_b": {"type": "integer"}},
                },
            ),
            "task_003": InterfaceSchema(
                task_id="task_003",
                input_schema={
                    "type": "object",
                    "properties": {
                        "output_a": {"type": "string"},
                        "output_b": {"type": "integer"},
                        "project": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {"result": {"type": "string"}},
                },
            ),
        }

        manager = MasterManagerSubWorkflow(
            engine="taskflow",
            jobqueue_client=mock_jobqueue_client,
        )

        # Verify user_input_schema is correctly merged
        from aiagent.langgraph.jobGeneratorV2.utils.topological_sort import (
            topological_sort_tasks,
        )

        sorted_tasks = topological_sort_tasks(tasks)
        user_input_schema = manager._get_user_input_schema(sorted_tasks, interfaces)

        # Merged schema should contain fields from both independent tasks
        assert user_input_schema is not None
        properties = user_input_schema.get("properties", {})
        assert "field_a" in properties, (
            "field_a from task_001 should be in merged schema"
        )
        assert "field_b" in properties, (
            "field_b from task_002 should be in merged schema"
        )

        # Required fields should be merged
        required = user_input_schema.get("required", [])
        assert "field_a" in required
        assert "field_b" in required

        # Create masters should succeed
        result = await manager.create_masters(
            tasks=tasks,
            interfaces=interfaces,
            project_id="test-project",
            context=mock_context,
        )

        assert result is not None
        assert len(result.task_masters) == 3


@pytest.mark.integration
class TestIssue409TopologicalSortIntegration:
    """Test topological sort integration with multiple independent tasks."""

    def test_independent_tasks_maintain_order(self):
        """Independent tasks should be sorted by priority within the same level."""
        from aiagent.langgraph.jobGeneratorV2.utils.topological_sort import (
            topological_sort_tasks,
        )

        tasks = [
            TaskDefinition(
                id="task_002",
                name="Second Independent",
                description="Second",
                task_type="fetch",
                recommended_api="/api/b",
                priority=2,
                dependencies=[],
            ),
            TaskDefinition(
                id="task_001",
                name="First Independent",
                description="First",
                task_type="fetch",
                recommended_api="/api/a",
                priority=1,
                dependencies=[],
            ),
        ]

        sorted_tasks = topological_sort_tasks(tasks)

        # Both are independent, so should be sorted by priority
        assert sorted_tasks[0].id == "task_001", (
            "task_001 (priority 1) should come first"
        )
        assert sorted_tasks[1].id == "task_002", (
            "task_002 (priority 2) should come second"
        )
