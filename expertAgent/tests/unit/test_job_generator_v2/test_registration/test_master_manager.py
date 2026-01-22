"""Unit tests for MasterManagerSubWorkflow.

Issue #342 Phase D.3: Tests for master creation sub-workflow.

Note: Tests in TestMasterManagerCreateMasters require external services (myVault, graphAiServer)
and are skipped in CI. Run locally with `./scripts/dev-hybrid.sh` for full test coverage.
"""

import os

import pytest

from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
from aiagent.langgraph.jobGeneratorV2.protocols import WorkflowError
from aiagent.langgraph.jobGeneratorV2.types import (
    InterfaceSchema,
    TaskDefinition,
)

# Skip tests that require external services when not available
requires_external_services = pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="Requires external services (myVault, graphAiServer) - run locally only",
)


class TestMasterManagerSubWorkflowExists:
    """Test that MasterManagerSubWorkflow exists and is importable."""

    def test_master_manager_importable(self):
        """MasterManagerSubWorkflow should be importable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        assert MasterManagerSubWorkflow is not None

    def test_master_manager_has_create_masters_method(self):
        """MasterManagerSubWorkflow should have create_masters method."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow()
        assert hasattr(manager, "create_masters")
        assert callable(manager.create_masters)

    def test_master_creation_result_importable(self):
        """MasterCreationResult should be importable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterCreationResult,
        )

        assert MasterCreationResult is not None


class TestMasterManagerSubWorkflowDataclasses:
    """Test dataclasses defined in master_manager."""

    def test_interface_master_info_creation(self):
        """InterfaceMasterInfo should be creatable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            InterfaceMasterInfo,
        )

        info = InterfaceMasterInfo(
            id="im_001",
            name="test_input",
            task_id="task_001",
            is_input=True,
        )
        assert info.id == "im_001"
        assert info.name == "test_input"
        assert info.task_id == "task_001"
        assert info.is_input is True

    def test_task_master_info_creation(self):
        """TaskMasterInfo should be creatable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            TaskMasterInfo,
        )

        info = TaskMasterInfo(
            id="tm_001",
            name="Test Task",
            task_id="task_001",
            order=0,
            input_interface_id="im_input",
            output_interface_id="im_output",
        )
        assert info.id == "tm_001"
        assert info.name == "Test Task"
        assert info.order == 0

    def test_job_master_info_creation(self):
        """JobMasterInfo should be creatable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            JobMasterInfo,
        )

        info = JobMasterInfo(
            id="jm_001",
            name="Test Job",
            method="POST",
            url="http://localhost:8005/api/v1/myagent",
            timeout_sec=300,
        )
        assert info.id == "jm_001"
        assert info.method == "POST"

    def test_master_creation_result_creation(self):
        """MasterCreationResult should be creatable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            JobMasterInfo,
            MasterCreationResult,
        )

        job_master = JobMasterInfo(
            id="jm_001",
            name="Test Job",
            method="POST",
            url="http://localhost:8005",
            timeout_sec=300,
        )
        result = MasterCreationResult(
            job_master=job_master,
            task_masters=[],
            interface_masters=[],
        )
        assert result.job_master.id == "jm_001"
        assert result.task_masters == []


class TestMasterManagerCreateMasters:
    """Test MasterManagerSubWorkflow.create_masters() method."""

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
        """Create sample interfaces for testing.

        Note: input_schema must include 'project' field as it's required by
        body_template validation (Issue #391).
        """
        return {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "project": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {"emails": {"type": "array"}},
                },
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={
                    "type": "object",
                    "properties": {
                        "emails": {"type": "array"},
                        "project": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {"summary": {"type": "string"}},
                },
            ),
        }

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock execution context."""
        return ExecutionContext(
            job_id="test-job-123",
            user_requirement="Search and summarize emails",
            max_phase_retries=3,
            max_total_retries=5,
        )

    @requires_external_services
    @pytest.mark.asyncio
    async def test_create_masters_returns_result(
        self,
        sample_tasks: list[TaskDefinition],
        sample_interfaces: dict[str, InterfaceSchema],
        mock_context: ExecutionContext,
    ):
        """create_masters should return MasterCreationResult.

        Note: This test requires external services (myVault, graphAiServer).
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterCreationResult,
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow()
        result = await manager.create_masters(
            tasks=sample_tasks,
            interfaces=sample_interfaces,
            project_id="test-project",
            context=mock_context,
        )

        assert isinstance(result, MasterCreationResult)
        assert result.job_master is not None
        assert len(result.task_masters) == 2
        assert len(result.interface_masters) == 4  # 2 tasks * 2 (input + output)

    @pytest.mark.asyncio
    async def test_create_masters_empty_tasks_raises_error(
        self,
        sample_interfaces: dict[str, InterfaceSchema],
        mock_context: ExecutionContext,
    ):
        """create_masters should raise WorkflowError for empty tasks."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow()
        with pytest.raises(WorkflowError) as exc_info:
            await manager.create_masters(
                tasks=[],
                interfaces=sample_interfaces,
                project_id="test-project",
                context=mock_context,
            )

        assert "No tasks provided" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_masters_empty_interfaces_raises_error(
        self,
        sample_tasks: list[TaskDefinition],
        mock_context: ExecutionContext,
    ):
        """create_masters should raise WorkflowError for empty interfaces."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow()
        with pytest.raises(WorkflowError) as exc_info:
            await manager.create_masters(
                tasks=sample_tasks,
                interfaces={},
                project_id="test-project",
                context=mock_context,
            )

        assert "No interfaces provided" in str(exc_info.value)

    @requires_external_services
    @pytest.mark.asyncio
    async def test_create_masters_sorts_by_priority(
        self,
        sample_interfaces: dict[str, InterfaceSchema],
        mock_context: ExecutionContext,
    ):
        """create_masters should sort tasks by priority.

        Note: This test requires external services (myVault, graphAiServer).
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        # Create tasks with reversed priority
        tasks = [
            TaskDefinition(
                id="task_002",
                name="Second",
                description="Second task",
                task_type="test",
                recommended_api="/test",
                priority=2,  # Lower priority (higher number)
            ),
            TaskDefinition(
                id="task_001",
                name="First",
                description="First task",
                task_type="test",
                recommended_api="/test",
                priority=1,  # Higher priority (lower number)
            ),
        ]

        manager = MasterManagerSubWorkflow()
        result = await manager.create_masters(
            tasks=tasks,
            interfaces=sample_interfaces,
            project_id="test-project",
            context=mock_context,
        )

        # First task master should have order 0, second should have order 1
        task_001_master = next(
            tm for tm in result.task_masters if tm.task_id == "task_001"
        )
        task_002_master = next(
            tm for tm in result.task_masters if tm.task_id == "task_002"
        )

        assert task_001_master.order == 0
        assert task_002_master.order == 1


class TestMasterManagerBodyTemplate:
    """Test body template generation for task chaining."""

    def test_first_task_body_template_graphai(self):
        """First task (GraphAI) should use job.body.user_input to avoid double nesting.

        Issue #342 Phase 1: Fixed body_template double nesting.
        user_input should reference {{job.body.user_input}} directly, not {{job.body}}.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(engine="graphai")
        template = manager._build_body_template(order=0)

        # Issue #342: user_input should extract job.body.user_input to avoid double nesting
        assert template["user_input"] == "{{job.body.user_input}}"
        assert template["job_params"] == "{{job.body}}"

    def test_subsequent_task_body_template_graphai(self):
        """Subsequent tasks (GraphAI) should use previous task output."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(engine="graphai")
        template = manager._build_body_template(order=1)

        assert template["user_input"] == "{{tasks[0].output_data}}"
        assert template["job_params"] == "{{job.body}}"

    def test_third_task_body_template_graphai(self):
        """Third task (GraphAI) should reference second task's output."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(engine="graphai")
        template = manager._build_body_template(order=2)

        assert template["user_input"] == "{{tasks[1].output_data}}"
        assert template["job_params"] == "{{job.body}}"

    def test_first_task_body_template_taskflow(self):
        """First task (TaskFlow) should use inputs for workflow execution.

        Issue #350: TaskFlow V2 body_template format.
        Issue #390: Changed from workflow_name to workflow for mySwiftAgentCore API.
        Issue #391: Changed from {{job.project}} to {{job.body.project}}.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(engine="taskflow")
        template = manager._build_body_template(order=0)

        # Issue #390: mySwiftAgentCore expects "workflow" field (not "workflow_name")
        # Issue #391: project uses {{job.body.project}} (Job model has no project attr)
        assert template["workflow"] == "__PENDING__"
        assert template["inputs"] == "{{job.body}}"
        assert template["project"] == "{{job.body.project}}"

    def test_subsequent_task_body_template_taskflow(self):
        """Subsequent tasks (TaskFlow) should use previous task output as inputs.

        Issue #390: Changed from workflow_name to workflow for mySwiftAgentCore API.
        Issue #391: Changed from {{job.project}} to {{job.body.project}}.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(engine="taskflow")
        template = manager._build_body_template(order=1)

        # Issue #390: mySwiftAgentCore expects "workflow" field (not "workflow_name")
        # Issue #391: project uses {{job.body.project}} (Job model has no project attr)
        assert template["workflow"] == "__PENDING__"
        assert template["inputs"] == "{{tasks[0].output_data}}"
        assert template["project"] == "{{job.body.project}}"

    # Legacy test name aliases for backward compatibility
    def test_first_task_body_template(self):
        """Alias for test_first_task_body_template_graphai for backward compatibility."""
        self.test_first_task_body_template_graphai()

    def test_subsequent_task_body_template(self):
        """Alias for test_subsequent_task_body_template_graphai for backward compatibility."""
        self.test_subsequent_task_body_template_graphai()

    def test_third_task_body_template(self):
        """Alias for test_third_task_body_template_graphai for backward compatibility."""
        self.test_third_task_body_template_graphai()


class TestMasterManagerInitialization:
    """Test MasterManagerSubWorkflow initialization."""

    def test_default_initialization(self):
        """Should initialize with default values."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow()
        assert manager._graphai_server_url == "http://localhost:8005"
        assert manager._default_timeout_sec == 60

    def test_custom_initialization(self):
        """Should initialize with custom values."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(
            graphai_server_url="http://custom:8000",
            default_timeout_sec=120,
        )
        assert manager._graphai_server_url == "http://custom:8000"
        assert manager._default_timeout_sec == 120
