"""Integration tests for registration phase body_template validation.

Issue #358: Tests for BodyTemplateValidator integration with MasterManagerSubWorkflow.

Test scenarios:
1. Validation passes - workflow creation proceeds
2. Validation errors - workflow creation blocked with clear error
3. Validation warnings - workflow creation proceeds with logged warnings
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


class TestRegistrationBodyTemplateValidation:
    """Integration tests for body_template validation in registration phase."""

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create mock execution context."""
        context = MagicMock()
        context.job_id = "test_job_id"
        context.user_requirement = "Test requirement"
        context.storage = MagicMock()
        context.storage.jobqueue_client = None
        return context

    @pytest.fixture
    def sample_tasks(self) -> list:
        """Create sample task definitions."""
        from aiagent.langgraph.jobGeneratorV2.types import TaskDefinition

        return [
            TaskDefinition(
                id="task_001",
                name="fetch_data",
                description="Fetch data from API",
                task_type="fetch",
                recommended_api="/api/fetch",
                priority=1,
            ),
            TaskDefinition(
                id="task_002",
                name="process_data",
                description="Process fetched data",
                task_type="transform",
                recommended_api="/api/process",
                priority=2,
                dependencies=["task_001"],
            ),
        ]

    @pytest.fixture
    def sample_interfaces(self) -> dict:
        """Create sample interface schemas.

        Note: input_schema must include 'project' field as it's required by
        body_template validation (Issue #391).
        """
        from aiagent.langgraph.jobGeneratorV2.types import InterfaceSchema

        return {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {
                        "user_input": {"type": "string"},
                        "api_key": {"type": "string"},
                        "project": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "data": {"type": "array"},
                    },
                },
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={
                    "type": "object",
                    "properties": {
                        "data": {"type": "array"},
                        "project": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "result": {"type": "object"},
                    },
                },
            ),
        }

    @pytest.mark.asyncio
    async def test_validation_passes_workflow_created(
        self,
        mock_context: MagicMock,
        sample_tasks: list,
        sample_interfaces: dict,
    ) -> None:
        """When validation passes, workflow masters are created."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        # Mock jobqueue client
        mock_client = AsyncMock()
        mock_client.create_interface_master.return_value = {"id": "im_test"}
        mock_client.create_task_master.return_value = {"id": "tm_test"}
        mock_client.create_job_master.return_value = {"id": "jm_test"}
        mock_client.add_task_to_workflow.return_value = {"id": "jmt_test"}

        manager = MasterManagerSubWorkflow(
            engine="taskflow",
            jobqueue_client=mock_client,
        )

        result = await manager.create_masters(
            tasks=sample_tasks,
            interfaces=sample_interfaces,
            project_id="test_project",
            context=mock_context,
        )

        assert result.job_master is not None
        assert len(result.task_masters) == 2

    @pytest.mark.asyncio
    async def test_validation_integration_with_body_template(
        self,
        mock_context: MagicMock,
        sample_tasks: list,
        sample_interfaces: dict,
    ) -> None:
        """Body template validation integrated with master creation."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        # Create validator
        validator = BodyTemplateValidator()

        # Get body template from manager
        manager = MasterManagerSubWorkflow(engine="taskflow")
        body_template = manager._build_body_template(order=0)

        # Validate body template against first task's input schema
        result = validator.validate(
            body_template=body_template,
            input_schema=sample_interfaces["task_001"].input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # First task uses {{job.body}} which is valid
        assert result.is_valid

    @pytest.mark.asyncio
    async def test_chained_task_body_template_validation(
        self,
        sample_interfaces: dict,
    ) -> None:
        """Validate body template for chained tasks (tasks[N].output_data)."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        validator = BodyTemplateValidator()
        manager = MasterManagerSubWorkflow(engine="taskflow")

        # Second task (order=1) references tasks[0].output_data
        body_template = manager._build_body_template(order=1)

        # Get output schema from first task as task_output_schemas
        task_output_schemas = [sample_interfaces["task_001"].output_schema]

        result = validator.validate(
            body_template=body_template,
            input_schema=sample_interfaces["task_002"].input_schema,
            task_count=1,  # One previous task exists
            task_output_schemas=task_output_schemas,
        )

        assert result.is_valid

    @pytest.mark.asyncio
    async def test_invalid_task_reference_detected(self) -> None:
        """Invalid task reference in body template is detected."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        validator = BodyTemplateValidator()

        # Template referencing task that doesn't exist yet
        body_template = {
            "workflow_name": "test",
            "inputs": "{{tasks[5].output_data}}",  # Invalid: only task_count=2
            "project": "{{job.project}}",
        }

        result = validator.validate(
            body_template=body_template,
            input_schema={},
            task_count=2,
            task_output_schemas=[{}, {}],
        )

        assert not result.is_valid
        assert any("index" in e.message.lower() for e in result.errors)

    @pytest.mark.asyncio
    async def test_graphai_body_template_validation(
        self,
        sample_interfaces: dict,
    ) -> None:
        """Validate GraphAI engine body template format."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
            GraphAIValidationStrategy,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        validator = BodyTemplateValidator(strategy=GraphAIValidationStrategy())
        manager = MasterManagerSubWorkflow(engine="graphai")

        # First task body template for GraphAI
        body_template = manager._build_body_template(order=0)

        result = validator.validate(
            body_template=body_template,
            input_schema=sample_interfaces["task_001"].input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # GraphAI template should reference job.body.user_input which exists
        assert result.is_valid


class TestValidationErrorMessages:
    """Test validation error message clarity."""

    def test_missing_field_error_message(self) -> None:
        """Error message clearly indicates missing field."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        validator = BodyTemplateValidator()
        body_template = {"field": "{{job.body.nonexistent_field}}"}
        input_schema = {
            "type": "object",
            "properties": {"actual_field": {"type": "string"}},
        }

        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        assert not result.is_valid
        error_messages = [e.message for e in result.errors]
        assert any("nonexistent_field" in msg for msg in error_messages)

    def test_invalid_index_error_message(self) -> None:
        """Error message clearly indicates invalid task index."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        validator = BodyTemplateValidator()
        body_template = {"field": "{{tasks[10].output_data}}"}

        result = validator.validate(
            body_template=body_template,
            input_schema={},
            task_count=3,
            task_output_schemas=[{}, {}, {}],
        )

        assert not result.is_valid
        error_messages = [e.message for e in result.errors]
        # Should mention the invalid index and valid range
        assert any("10" in msg or "index" in msg.lower() for msg in error_messages)


class TestMultiDependencyWorkflowRegistration:
    """Issue #403: Integration tests for multi-dependency workflow registration."""

    @pytest.fixture
    def multi_dep_tasks(self) -> list:
        """Create tasks with multiple dependencies (task_006 scenario)."""
        from aiagent.langgraph.jobGeneratorV2.types import TaskDefinition

        return [
            TaskDefinition(
                id="task_001",
                name="search_keywords",
                description="Search for keywords",
                task_type="search",
                recommended_api="/api/search",
                priority=1,
                dependencies=[],
            ),
            TaskDefinition(
                id="task_005",
                name="summarize_results",
                description="Summarize search results",
                task_type="summarize",
                recommended_api="/api/summarize",
                priority=5,
                dependencies=["task_001"],
            ),
            TaskDefinition(
                id="task_006",
                name="send_email_report",
                description="Send email with keyword and summary",
                task_type="email_send",
                recommended_api="/api/email/send",
                priority=6,
                dependencies=["task_001", "task_005"],
            ),
        ]

    @pytest.fixture
    def multi_dep_interfaces(self) -> dict:
        """Create interfaces for multi-dependency testing."""
        from aiagent.langgraph.jobGeneratorV2.types import InterfaceSchema

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
                    "properties": {"keyword": {"type": "string"}},
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

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create mock execution context."""
        context = MagicMock()
        context.job_id = "test_multi_dep_job"
        context.user_requirement = "Multi-dependency workflow test"
        context.storage = MagicMock()
        context.storage.jobqueue_client = None
        return context

    @pytest.mark.asyncio
    async def test_multi_dependency_workflow_registration(
        self,
        mock_context: MagicMock,
        multi_dep_tasks: list,
        multi_dep_interfaces: dict,
    ) -> None:
        """AC-10: Multi-dependency workflow registration E2E test.

        Issue #403: Verify that task_006 with dependencies on task_001 and task_005
        generates correct body_template with field-level references.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        # Mock jobqueue client to capture body_template
        mock_client = AsyncMock()
        captured_body_templates = []

        async def capture_task_master(**kwargs):
            captured_body_templates.append(kwargs.get("body_template"))
            return {"id": f"tm_{len(captured_body_templates)}"}

        mock_client.create_interface_master.return_value = {"id": "im_test"}
        mock_client.create_task_master.side_effect = capture_task_master
        mock_client.create_job_master.return_value = {"id": "jm_test"}
        mock_client.add_task_to_workflow.return_value = {"id": "jmt_test"}

        manager = MasterManagerSubWorkflow(
            engine="taskflow",
            jobqueue_client=mock_client,
        )

        result = await manager.create_masters(
            tasks=multi_dep_tasks,
            interfaces=multi_dep_interfaces,
            project_id="test_project",
            context=mock_context,
        )

        # Verify all task masters created
        assert len(result.task_masters) == 3

        # Verify task_006's body_template (should be the last one)
        task_006_template = captured_body_templates[2]

        # Verify inputs is a dict with field-level references
        assert isinstance(task_006_template["inputs"], dict)

        # Expected format: keyword from task_001 (order 0), summary/recipient from task_005 (order 1)
        inputs = task_006_template["inputs"]
        assert inputs["keyword"] == "{{tasks[0].output_data.keyword}}"
        assert inputs["summary"] == "{{tasks[1].output_data.summary}}"
        assert inputs["recipient_email"] == "{{tasks[1].output_data.recipient_email}}"

        # Verify project is still at top level
        assert task_006_template["project"] == "{{job.body.project}}"

    @pytest.mark.asyncio
    async def test_single_dependency_still_works(
        self,
        mock_context: MagicMock,
        multi_dep_interfaces: dict,
    ) -> None:
        """AC-5: Single dependency tasks still work correctly.

        Issue #403: Verify that task_005 (single dependency on task_001)
        generates correct body_template.
        """
        from aiagent.langgraph.jobGeneratorV2.types import TaskDefinition
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        # Create simple two-task workflow
        tasks = [
            TaskDefinition(
                id="task_001",
                name="search_keywords",
                description="Search for keywords",
                task_type="search",
                recommended_api="/api/search",
                priority=1,
                dependencies=[],
            ),
            TaskDefinition(
                id="task_005",
                name="summarize_results",
                description="Summarize search results",
                task_type="summarize",
                recommended_api="/api/summarize",
                priority=5,
                dependencies=["task_001"],
            ),
        ]

        # Mock jobqueue client
        mock_client = AsyncMock()
        captured_body_templates = []

        async def capture_task_master(**kwargs):
            captured_body_templates.append(kwargs.get("body_template"))
            return {"id": f"tm_{len(captured_body_templates)}"}

        mock_client.create_interface_master.return_value = {"id": "im_test"}
        mock_client.create_task_master.side_effect = capture_task_master
        mock_client.create_job_master.return_value = {"id": "jm_test"}
        mock_client.add_task_to_workflow.return_value = {"id": "jmt_test"}

        manager = MasterManagerSubWorkflow(
            engine="taskflow",
            jobqueue_client=mock_client,
        )

        await manager.create_masters(
            tasks=tasks,
            interfaces=multi_dep_interfaces,
            project_id="test_project",
            context=mock_context,
        )

        # Verify task_005's body_template
        task_005_template = captured_body_templates[1]

        # Single dependency should also use dict format
        assert isinstance(task_005_template["inputs"], dict)
        assert (
            task_005_template["inputs"]["keyword"] == "{{tasks[0].output_data.keyword}}"
        )

    def test_fallback_to_user_input_for_missing_field(self) -> None:
        """AC-6: Fields not found in dependencies fallback to user_input.

        Issue #403: Verify that missing fields fallback to job.body.user_input.
        This test directly tests _build_multi_dependency_template without going
        through create_masters (which would trigger body_template validation).
        """
        from aiagent.langgraph.jobGeneratorV2.types import (
            InterfaceSchema,
            TaskDefinition,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        # Create task requiring field not in dependency output
        task = TaskDefinition(
            id="task_002",
            name="process_data",
            description="Process data with extra field",
            task_type="process",
            recommended_api="/api/process",
            priority=2,
            dependencies=["task_001"],
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
                    "properties": {"data": {"type": "array"}},  # Only outputs 'data'
                },
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={
                    "type": "object",
                    "properties": {
                        "data": {"type": "array"},
                        "extra_param": {"type": "string"},  # Not in task_001 output
                    },
                },
                output_schema={"type": "object"},
            ),
        }

        task_order_map = {"task_001": 0, "task_002": 1}

        manager = MasterManagerSubWorkflow(engine="taskflow")

        # Directly test _build_multi_dependency_template
        template = manager._build_multi_dependency_template(
            task=task,
            interfaces=interfaces,
            task_order_map=task_order_map,
        )

        inputs = template["inputs"]

        # data should come from task_001
        assert inputs["data"] == "{{tasks[0].output_data.data}}"

        # extra_param should fallback to user_input
        assert inputs["extra_param"] == "{{job.body.user_input.extra_param}}"
