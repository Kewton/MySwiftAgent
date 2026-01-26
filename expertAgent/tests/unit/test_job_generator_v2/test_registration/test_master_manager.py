"""Unit tests for MasterManagerSubWorkflow.

Issue #342 Phase D.3: Tests for master creation sub-workflow.
Issue #402: Tests for topological sort integration.

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
        Issue #396: Changed from {{job.body}} to {{job.body.user_input}} for inputs.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(engine="taskflow")
        template = manager._build_body_template(order=0)

        # Issue #390: mySwiftAgentCore expects "workflow" field (not "workflow_name")
        # Issue #391: project uses {{job.body.project}} (Job model has no project attr)
        # Issue #396: inputs uses {{job.body.user_input}} (not entire body)
        assert template["workflow"] == "__PENDING__"
        assert template["inputs"] == "{{job.body.user_input}}"
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


class TestMasterManagerTopologicalSort:
    """Issue #402: Test topological sort integration in MasterManagerSubWorkflow."""

    def test_topological_sort_import(self):
        """topological_sort_tasks should be imported in master_manager."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration import (
            master_manager,
        )

        # Verify the import exists
        assert hasattr(master_manager, "topological_sort_tasks")

    @pytest.fixture
    def dependency_tasks(self) -> list[TaskDefinition]:
        """Create tasks with dependencies for topological sort testing."""
        return [
            TaskDefinition(
                id="task_003",
                name="Final Task",
                description="Depends on task_001 and task_002",
                task_type="send",
                recommended_api="/api/send",
                priority=1,  # Highest priority but depends on others
                dependencies=["task_001", "task_002"],
            ),
            TaskDefinition(
                id="task_001",
                name="First Task",
                description="No dependencies",
                task_type="fetch",
                recommended_api="/api/fetch",
                priority=3,
                dependencies=[],
            ),
            TaskDefinition(
                id="task_002",
                name="Second Task",
                description="Depends on first",
                task_type="transform",
                recommended_api="/api/transform",
                priority=2,
                dependencies=["task_001"],
            ),
        ]

    @pytest.fixture
    def dependency_interfaces(self) -> dict[str, InterfaceSchema]:
        """Create interfaces for dependency testing."""
        return {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
                output_schema={
                    "type": "object",
                    "properties": {"data": {"type": "array"}},
                },
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={
                    "type": "object",
                    "properties": {"data": {"type": "array"}},
                },
                output_schema={
                    "type": "object",
                    "properties": {"result": {"type": "string"}},
                },
            ),
            "task_003": InterfaceSchema(
                task_id="task_003",
                input_schema={
                    "type": "object",
                    "properties": {"result": {"type": "string"}},
                },
                output_schema={
                    "type": "object",
                    "properties": {"status": {"type": "string"}},
                },
            ),
        }

    @requires_external_services
    @pytest.mark.asyncio
    async def test_topological_sort_respects_dependencies(
        self,
        dependency_tasks: list[TaskDefinition],
        dependency_interfaces: dict[str, InterfaceSchema],
    ):
        """AC-1: Tasks should be sorted by dependencies, not priority.

        Issue #402: Verify that topological sort orders tasks correctly.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        mock_context = ExecutionContext(
            job_id="test-topo-sort",
            user_requirement="Test topological sort",
            max_phase_retries=3,
            max_total_retries=5,
        )

        manager = MasterManagerSubWorkflow()
        result = await manager.create_masters(
            tasks=dependency_tasks,
            interfaces=dependency_interfaces,
            project_id="test-project",
            context=mock_context,
        )

        # Verify order respects dependencies
        orders = {tm.task_id: tm.order for tm in result.task_masters}

        # task_001 must come before task_002 and task_003
        assert orders["task_001"] < orders["task_002"]
        assert orders["task_001"] < orders["task_003"]

        # task_002 must come before task_003
        assert orders["task_002"] < orders["task_003"]

    @pytest.mark.asyncio
    async def test_circular_dependency_raises_error(self):
        """AC-2: Circular dependencies should raise WorkflowError.

        Issue #402: Verify that circular dependencies are detected.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        circular_tasks = [
            TaskDefinition(
                id="task_001",
                name="Task 1",
                description="Depends on task_003",
                task_type="fetch",
                recommended_api="/api/fetch",
                priority=1,
                dependencies=["task_003"],
            ),
            TaskDefinition(
                id="task_002",
                name="Task 2",
                description="Depends on task_001",
                task_type="transform",
                recommended_api="/api/transform",
                priority=2,
                dependencies=["task_001"],
            ),
            TaskDefinition(
                id="task_003",
                name="Task 3",
                description="Depends on task_002",
                task_type="send",
                recommended_api="/api/send",
                priority=3,
                dependencies=["task_002"],
            ),
        ]

        interfaces = {
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
            "task_003": InterfaceSchema(
                task_id="task_003",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            ),
        }

        mock_context = ExecutionContext(
            job_id="test-circular",
            user_requirement="Test circular dependency",
            max_phase_retries=3,
            max_total_retries=5,
        )

        manager = MasterManagerSubWorkflow()
        with pytest.raises(WorkflowError) as exc_info:
            await manager.create_masters(
                tasks=circular_tasks,
                interfaces=interfaces,
                project_id="test-project",
                context=mock_context,
            )

        assert "circular dependency" in str(exc_info.value).lower()


class TestFindFieldSource:
    """Issue #403: Test _find_field_source method for multi-dependency field resolution."""

    @pytest.fixture
    def multi_dep_interfaces(self) -> dict[str, InterfaceSchema]:
        """Create interfaces for multi-dependency testing.

        Scenario: task_006 depends on task_001 and task_005
        - task_001 outputs: keyword
        - task_005 outputs: summary, recipient_email
        """
        return {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
                output_schema={
                    "type": "object",
                    "properties": {"keyword": {"type": "string"}},
                },
            ),
            "task_005": InterfaceSchema(
                task_id="task_005",
                input_schema={
                    "type": "object",
                    "properties": {"data": {"type": "array"}},
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "recipient_email": {"type": "string"},
                    },
                },
            ),
            "task_006": InterfaceSchema(
                task_id="task_006",
                input_schema={
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string"},
                        "summary": {"type": "string"},
                        "recipient_email": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {"status": {"type": "string"}},
                },
            ),
        }

    def test_find_field_source_single_dependency(
        self, multi_dep_interfaces: dict[str, InterfaceSchema]
    ):
        """AC-8: _find_field_source finds field from single dependency.

        Issue #403: When field exists in only one dependency, return that task.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(engine="taskflow")

        # task_order_map: task_id -> order in execution
        task_order_map = {"task_001": 0, "task_005": 4, "task_006": 5}

        result = manager._find_field_source(
            field="keyword",
            dependencies=["task_001"],
            interfaces=multi_dep_interfaces,
            task_order_map=task_order_map,
        )

        assert result == "task_001"

    def test_find_field_source_multiple_deps_first_match(
        self, multi_dep_interfaces: dict[str, InterfaceSchema]
    ):
        """AC-8: _find_field_source returns first matching task in dependencies order.

        Issue #403: When multiple dependencies have the field, prefer dependencies order.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(engine="taskflow")
        task_order_map = {"task_001": 0, "task_005": 4, "task_006": 5}

        # summary is in task_005's output
        result = manager._find_field_source(
            field="summary",
            dependencies=["task_001", "task_005"],  # task_005 has summary
            interfaces=multi_dep_interfaces,
            task_order_map=task_order_map,
        )

        assert result == "task_005"

    def test_find_field_source_field_not_found(
        self, multi_dep_interfaces: dict[str, InterfaceSchema]
    ):
        """AC-8: _find_field_source returns None when field not in any dependency.

        Issue #403: When field doesn't exist in any dependency, return None.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(engine="taskflow")
        task_order_map = {"task_001": 0, "task_005": 4, "task_006": 5}

        result = manager._find_field_source(
            field="nonexistent_field",
            dependencies=["task_001", "task_005"],
            interfaces=multi_dep_interfaces,
            task_order_map=task_order_map,
        )

        assert result is None


class TestBuildBodyTemplateMultiDependency:
    """Issue #403: Test _build_body_template with interfaceDefinitions for multi-dependency."""

    @pytest.fixture
    def multi_dep_task(self) -> TaskDefinition:
        """Create task with multiple dependencies (task_006 scenario)."""
        return TaskDefinition(
            id="task_006",
            name="Send Email Report",
            description="Send email with keyword and summary",
            task_type="email_send",
            recommended_api="/api/email/send",
            priority=6,
            dependencies=["task_001", "task_005"],
        )

    @pytest.fixture
    def multi_dep_interfaces(self) -> dict[str, InterfaceSchema]:
        """Create interfaces for multi-dependency testing."""
        return {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
                output_schema={
                    "type": "object",
                    "properties": {"keyword": {"type": "string"}},
                },
            ),
            "task_005": InterfaceSchema(
                task_id="task_005",
                input_schema={
                    "type": "object",
                    "properties": {"data": {"type": "array"}},
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "summary": {"type": "string"},
                        "recipient_email": {"type": "string"},
                    },
                },
            ),
            "task_006": InterfaceSchema(
                task_id="task_006",
                input_schema={
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string"},
                        "summary": {"type": "string"},
                        "recipient_email": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {"status": {"type": "string"}},
                },
            ),
        }

    def test_build_body_template_multi_dependency_aggregation(
        self,
        multi_dep_task: TaskDefinition,
        multi_dep_interfaces: dict[str, InterfaceSchema],
    ):
        """AC-3, AC-4: _build_body_template aggregates fields from multiple dependencies.

        Issue #403: task_006 needs keyword from task_001 and summary/recipient_email from task_005.
        Expected body_template.inputs:
        {
            "keyword": "{{tasks[0].output_data.keyword}}",
            "summary": "{{tasks[4].output_data.summary}}",
            "recipient_email": "{{tasks[4].output_data.recipient_email}}"
        }
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(engine="taskflow")
        task_order_map = {"task_001": 0, "task_005": 4, "task_006": 5}

        template = manager._build_body_template(
            order=5,
            task=multi_dep_task,
            interfaces=multi_dep_interfaces,
            task_order_map=task_order_map,
        )

        # Verify structure
        assert "workflow" in template
        assert "inputs" in template
        assert "project" in template

        # Verify inputs is a dict (not a string like {{tasks[N].output_data}})
        assert isinstance(template["inputs"], dict)

        # Verify field mappings
        inputs = template["inputs"]
        assert inputs["keyword"] == "{{tasks[0].output_data.keyword}}"
        assert inputs["summary"] == "{{tasks[4].output_data.summary}}"
        assert inputs["recipient_email"] == "{{tasks[4].output_data.recipient_email}}"

    def test_build_body_template_backward_compatibility(self):
        """AC-5, AC-7: _build_body_template maintains backward compatibility.

        Issue #403: When interfaces are not provided, use legacy behavior.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(engine="taskflow")

        # Call without optional parameters (backward compatible)
        template = manager._build_body_template(order=1)

        # Should use legacy format: inputs as string reference
        assert template["workflow"] == "__PENDING__"
        assert template["inputs"] == "{{tasks[0].output_data}}"
        assert template["project"] == "{{job.body.project}}"

    def test_build_body_template_first_task_with_interfaces(
        self, multi_dep_interfaces: dict[str, InterfaceSchema]
    ):
        """AC-5: First task still uses user_input even with interfaces.

        Issue #403: First task (order=0) should use {{job.body.user_input}}.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(engine="taskflow")
        first_task = TaskDefinition(
            id="task_001",
            name="First Task",
            description="First task",
            task_type="fetch",
            recommended_api="/api/fetch",
            priority=1,
            dependencies=[],  # No dependencies
        )
        task_order_map = {"task_001": 0}

        template = manager._build_body_template(
            order=0,
            task=first_task,
            interfaces=multi_dep_interfaces,
            task_order_map=task_order_map,
        )

        # First task should still use user_input
        assert template["inputs"] == "{{job.body.user_input}}"

    def test_build_body_template_fallback_with_warning_log(
        self, multi_dep_interfaces: dict[str, InterfaceSchema], caplog
    ):
        """AC-6: Fields not found in dependencies fallback to user_input with warning.

        Issue #403: If a required field is not in any dependency's output,
        fallback to {{job.body.user_input.field_name}} and log a warning.
        """
        import logging

        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        # Create task requiring a field that doesn't exist in dependencies
        task = TaskDefinition(
            id="task_006",
            name="Send Email",
            description="Send email",
            task_type="email_send",
            recommended_api="/api/email/send",
            priority=6,
            dependencies=["task_001"],  # task_001 only outputs 'keyword'
        )

        # task_006 needs 'missing_field' which is not in task_001's output
        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"type": "object"},
                output_schema={
                    "type": "object",
                    "properties": {"keyword": {"type": "string"}},
                },
            ),
            "task_006": InterfaceSchema(
                task_id="task_006",
                input_schema={
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string"},
                        "missing_field": {"type": "string"},  # Not in task_001 output
                    },
                },
                output_schema={"type": "object"},
            ),
        }

        manager = MasterManagerSubWorkflow(engine="taskflow")
        task_order_map = {"task_001": 0, "task_006": 5}

        with caplog.at_level(logging.WARNING):
            template = manager._build_body_template(
                order=5,
                task=task,
                interfaces=interfaces,
                task_order_map=task_order_map,
            )

        # Verify fallback
        inputs = template["inputs"]
        assert inputs["keyword"] == "{{tasks[0].output_data.keyword}}"
        assert inputs["missing_field"] == "{{job.body.user_input.missing_field}}"

        # Verify warning was logged
        assert any(
            "missing_field" in record.message.lower()
            and "fallback" in record.message.lower()
            for record in caplog.records
        )

    def test_build_body_template_single_dependency_task(
        self, multi_dep_interfaces: dict[str, InterfaceSchema]
    ):
        """AC-5: Single dependency task uses dict format with field mappings.

        Issue #403: Even single dependency tasks should use the new dict format
        when interfaces are provided.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        # task_005 depends only on one task
        task = TaskDefinition(
            id="task_005",
            name="Process Data",
            description="Process data",
            task_type="transform",
            recommended_api="/api/transform",
            priority=5,
            dependencies=["task_001"],
        )

        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"type": "object"},
                output_schema={
                    "type": "object",
                    "properties": {"keyword": {"type": "string"}},
                },
            ),
            "task_005": InterfaceSchema(
                task_id="task_005",
                input_schema={
                    "type": "object",
                    "properties": {"keyword": {"type": "string"}},
                },
                output_schema={"type": "object"},
            ),
        }

        manager = MasterManagerSubWorkflow(engine="taskflow")
        task_order_map = {"task_001": 0, "task_005": 4}

        template = manager._build_body_template(
            order=4,
            task=task,
            interfaces=interfaces,
            task_order_map=task_order_map,
        )

        # With interfaces, should use dict format
        assert isinstance(template["inputs"], dict)
        assert template["inputs"]["keyword"] == "{{tasks[0].output_data.keyword}}"


class TestIssue409IndependentTaskDataflow:
    """Issue #409: Tests for independent task (dependencies=[]) dataflow.

    AC-1: dependencies=[]のタスク（TaskFlow）は{{job.body.user_input}}を使用する
    AC-2: _get_user_input_schemaが全独立タスクのフィールドを含む
    """

    def test_tc007_independent_task_uses_user_input(self):
        """TC-007: Independent task (order > 0, dependencies=[]) uses user_input.

        Issue #409: AC-1 - Even if order > 0, a task with dependencies=[] should
        use {{job.body.user_input}} instead of {{tasks[order-1].output_data}}.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(engine="taskflow")

        # Task at order 1 with no dependencies (independent)
        task = TaskDefinition(
            id="task_002",
            name="Independent Second Task",
            description="Independent task at order 1",
            task_type="fetch",
            recommended_api="/api/fetch",
            priority=2,
            dependencies=[],  # No dependencies = independent task
        )

        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
                output_schema={
                    "type": "object",
                    "properties": {"keyword": {"type": "string"}},
                },
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={
                    "type": "object",
                    "properties": {"search_term": {"type": "string"}},
                },
                output_schema={
                    "type": "object",
                    "properties": {"results": {"type": "array"}},
                },
            ),
        }

        task_order_map = {"task_001": 0, "task_002": 1}

        template = manager._build_body_template(
            order=1,  # Not first task
            task=task,
            interfaces=interfaces,
            task_order_map=task_order_map,
        )

        # Independent task should use user_input, not previous task's output
        assert template["inputs"] == "{{job.body.user_input}}", (
            f"Independent task should use user_input, got: {template['inputs']}"
        )
        assert template["workflow"] == "__PENDING__"
        assert template["project"] == "{{job.body.project}}"

    def test_tc009_get_user_input_schema_merges_all_independent_tasks(self):
        """TC-009: _get_user_input_schema merges schemas from all independent tasks.

        Issue #409: AC-2 - The method should merge input schemas from all tasks
        with dependencies=[], not just the first task.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(engine="taskflow")

        # Two independent tasks with different input fields
        sorted_tasks = [
            TaskDefinition(
                id="task_001",
                name="First Independent Task",
                description="First independent task",
                task_type="fetch",
                recommended_api="/api/fetch",
                priority=1,
                dependencies=[],  # Independent
            ),
            TaskDefinition(
                id="task_002",
                name="Second Independent Task",
                description="Second independent task",
                task_type="search",
                recommended_api="/api/search",
                priority=2,
                dependencies=[],  # Also independent
            ),
            TaskDefinition(
                id="task_003",
                name="Dependent Task",
                description="Depends on task_001",
                task_type="process",
                recommended_api="/api/process",
                priority=3,
                dependencies=["task_001"],  # Dependent
            ),
        ]

        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string", "description": "Search keyword"},
                    },
                    "required": ["keyword"],
                },
                output_schema={"type": "object", "properties": {}},
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={
                    "type": "object",
                    "properties": {
                        "recipient_email": {
                            "type": "string",
                            "description": "Email recipient",
                        },
                    },
                    "required": ["recipient_email"],
                },
                output_schema={"type": "object", "properties": {}},
            ),
            "task_003": InterfaceSchema(
                task_id="task_003",
                input_schema={
                    "type": "object",
                    "properties": {"data": {"type": "array"}},
                },
                output_schema={"type": "object", "properties": {}},
            ),
        }

        result = manager._get_user_input_schema(sorted_tasks, interfaces)

        # Should merge fields from both independent tasks
        assert result is not None
        properties = result.get("properties", {})
        assert "keyword" in properties, (
            "keyword from task_001 should be in merged schema"
        )
        assert "recipient_email" in properties, (
            "recipient_email from task_002 should be in merged schema"
        )

        # Required fields should also be merged
        required = result.get("required", [])
        assert "keyword" in required, "keyword should be required"
        assert "recipient_email" in required, "recipient_email should be required"

        # Dependent task's input should NOT be in merged schema
        assert "data" not in properties, "Dependent task fields should not be merged"

    def test_tc011_same_field_same_type_warning_log(self, caplog):
        """TC-011: Same field with same type logs warning with both type info.

        Issue #409: AC-6 - When same field appears in multiple independent tasks
        with the same type, log a warning with both type info and continue.
        """
        import logging

        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(engine="taskflow")

        # Two independent tasks with same field name and same type
        sorted_tasks = [
            TaskDefinition(
                id="task_001",
                name="First Task",
                description="First task",
                task_type="fetch",
                recommended_api="/api/fetch",
                priority=1,
                dependencies=[],
            ),
            TaskDefinition(
                id="task_002",
                name="Second Task",
                description="Second task",
                task_type="fetch",
                recommended_api="/api/fetch",
                priority=2,
                dependencies=[],
            ),
        ]

        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string"},  # Same field, same type
                    },
                },
                output_schema={"type": "object", "properties": {}},
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string"},  # Same field, same type
                    },
                },
                output_schema={"type": "object", "properties": {}},
            ),
        }

        with caplog.at_level(logging.WARNING):
            result = manager._get_user_input_schema(sorted_tasks, interfaces)

        # Should still return merged result
        assert result is not None
        assert "keyword" in result.get("properties", {})

        # Should log warning with both type info
        warning_found = False
        for record in caplog.records:
            if record.levelno == logging.WARNING:
                msg = record.message.lower()
                if "keyword" in msg and "second task" in msg:
                    # Check both type info is present
                    if "string" in msg:
                        warning_found = True
                        break

        assert warning_found, (
            f"Warning log should contain field name, task name, and type info. "
            f"Logs: {[r.message for r in caplog.records]}"
        )

    def test_tc012_same_field_different_type_raises_valueerror(self):
        """TC-012: Same field with different type raises ValueError with both type info.

        Issue #409: AC-7 - When same field appears in multiple independent tasks
        with different types, raise ValueError with both type information.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(engine="taskflow")

        # Two independent tasks with same field name but different types
        sorted_tasks = [
            TaskDefinition(
                id="task_001",
                name="First Task",
                description="First task",
                task_type="fetch",
                recommended_api="/api/fetch",
                priority=1,
                dependencies=[],
            ),
            TaskDefinition(
                id="task_002",
                name="Second Task",
                description="Second task",
                task_type="fetch",
                recommended_api="/api/fetch",
                priority=2,
                dependencies=[],
            ),
        ]

        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "string"},  # string type
                    },
                },
                output_schema={"type": "object", "properties": {}},
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={
                    "type": "object",
                    "properties": {
                        "keyword": {"type": "integer"},  # integer type (conflict!)
                    },
                },
                output_schema={"type": "object", "properties": {}},
            ),
        }

        # Should raise ValueError with both type info
        with pytest.raises(ValueError) as exc_info:
            manager._get_user_input_schema(sorted_tasks, interfaces)

        error_message = str(exc_info.value).lower()
        assert "keyword" in error_message, "Error should mention field name"
        assert "string" in error_message, "Error should mention existing type"
        assert "integer" in error_message, "Error should mention conflicting type"
        assert "second task" in error_message, "Error should mention task name"
