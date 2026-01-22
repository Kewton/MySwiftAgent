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
