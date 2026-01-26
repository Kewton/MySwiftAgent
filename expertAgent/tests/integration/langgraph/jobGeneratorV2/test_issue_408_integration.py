"""Integration tests for Issue #408: User input field name consistency validation.

Issue #408: Test that MasterManager integrates with BodyTemplateValidator
for user_input field validation.

Test scenarios:
- MasterManager passes user_input_schema to Validator
- Warning is included in ValidationResult
- Full workflow with multi-dependency template
"""

from __future__ import annotations

import logging
from typing import Any
from unittest.mock import MagicMock

import pytest


class TestMasterManagerValidatorIntegration:
    """Test MasterManager integration with BodyTemplateValidator."""

    @pytest.fixture
    def mock_context(self) -> MagicMock:
        """Create mock ExecutionContext."""
        context = MagicMock()
        context.job_id = "test_job_001"
        context.user_requirement = "Test workflow"
        context.storage.jobqueue_client = None
        return context

    @pytest.fixture
    def sample_interfaces(self) -> dict[str, Any]:
        """Create sample interfaces for testing."""
        from aiagent.langgraph.jobGeneratorV2.types_old import InterfaceSchema

        return {
            "task_001": InterfaceSchema(
                task_id="task_001",
                description="Search interface",
                input_schema={
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                        "keyword": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "results": {"type": "array"},
                    },
                },
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                description="Email interface",
                input_schema={
                    "type": "object",
                    "properties": {
                        "recipient_email": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                    },
                },
            ),
        }

    @pytest.fixture
    def sample_tasks(self) -> list[Any]:
        """Create sample tasks for testing."""
        from aiagent.langgraph.jobGeneratorV2.types_old import TaskDefinition

        return [
            TaskDefinition(
                id="task_001",
                name="search_task",
                description="Search for data",
                task_type="fetch",
                dependencies=[],
                priority=1,
                recommended_api="search_api",
            ),
            TaskDefinition(
                id="task_002",
                name="email_task",
                description="Send email",
                task_type="send",
                dependencies=["task_001"],
                priority=2,
                recommended_api="email_api",
            ),
        ]

    def test_master_manager_uses_user_input_schema(
        self,
        sample_tasks: list[Any],
        sample_interfaces: dict[str, Any],
    ) -> None:
        """MasterManager uses _get_user_input_schema to get first task input schema."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(engine="taskflow")

        # Get user_input_schema
        user_input_schema = manager._get_user_input_schema(
            sorted_tasks=sample_tasks,
            interfaces=sample_interfaces,
        )

        # Should return the first task's input_schema
        assert user_input_schema is not None
        assert "email" in user_input_schema.get("properties", {})
        assert "keyword" in user_input_schema.get("properties", {})

    def test_build_multi_dependency_template_with_user_input_schema(
        self,
        sample_tasks: list[Any],
        sample_interfaces: dict[str, Any],
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Multi-dependency template validates field names against user_input_schema."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(engine="taskflow")

        # Get user_input_schema from first task
        user_input_schema = manager._get_user_input_schema(
            sorted_tasks=sample_tasks,
            interfaces=sample_interfaces,
        )

        task_order_map = {"task_001": 0, "task_002": 1}

        # Build template for task_002 which needs 'recipient_email'
        # but user_input_schema only has 'email'
        with caplog.at_level(logging.WARNING):
            _ = manager._build_multi_dependency_template(
                task=sample_tasks[1],
                interfaces=sample_interfaces,
                task_order_map=task_order_map,
                user_input_schema=user_input_schema,
            )

        # Check that warning was logged about field mismatch
        warning_messages = [r.message for r in caplog.records]
        assert any("recipient_email" in msg for msg in warning_messages), (
            f"Expected warning about 'recipient_email': {warning_messages}"
        )

    def test_body_template_validator_called_with_user_input_schema(
        self,
        sample_interfaces: dict[str, Any],
    ) -> None:
        """Validator properly validates user_input field references."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        validator = BodyTemplateValidator()

        # Body template with mismatched field name
        body_template = {
            "inputs": {
                "recipient_email": "{{job.body.user_input.recipient_email}}",
            },
        }

        # user_input_schema has 'email', not 'recipient_email'
        user_input_schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string"},
                "keyword": {"type": "string"},
            },
        }

        result = validator.validate(
            body_template=body_template,
            input_schema={"type": "object", "properties": {}},
            task_count=0,
            task_output_schemas=[],
            user_input_schema=user_input_schema,
        )

        # Should have warning about mismatched field
        assert len(result.warnings) >= 1
        assert result.warnings[0].warning_type == "USER_INPUT_FIELD_MISMATCH"
        assert "recipient_email" in result.warnings[0].message


class TestEndToEndValidationFlow:
    """Test complete validation flow from interface to template."""

    def test_validation_detects_llm_field_renaming(self) -> None:
        """Complete flow: LLM renames field -> detected by validator."""
        from aiagent.langgraph.jobGeneratorV2.types_old import InterfaceSchema
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        # Simulate user requirement: user wants to use "email" field
        user_input_schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string"},
            },
        }

        # But LLM generated interface with renamed field
        llm_generated_interface = InterfaceSchema(
            task_id="task_001",
            description="Email sending interface",
            input_schema={
                "type": "object",
                "properties": {
                    "recipient_email": {"type": "string"},  # LLM renamed it
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                },
            },
        )

        # Body template references the LLM-generated field name
        body_template = {
            "workflow": "__PENDING__",
            "inputs": {
                "recipient_email": "{{job.body.user_input.recipient_email}}",
            },
            "project": "{{job.body.project}}",
        }

        validator = BodyTemplateValidator()
        result = validator.validate(
            body_template=body_template,
            input_schema=llm_generated_interface.input_schema,
            task_count=0,
            task_output_schemas=[],
            user_input_schema=user_input_schema,
        )

        # Should detect the mismatch
        assert len(result.warnings) >= 1
        warning = result.warnings[0]
        assert warning.warning_type == "USER_INPUT_FIELD_MISMATCH"
        assert "recipient_email" in warning.message
        assert "email" in warning.message  # Should suggest valid field

    def test_validation_passes_when_fields_match(self) -> None:
        """Validation passes when LLM preserves field names."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        # User requirement uses "email" field
        user_input_schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string"},
                "keyword": {"type": "string"},
            },
        }

        # LLM correctly preserved field names
        body_template = {
            "workflow": "__PENDING__",
            "inputs": {
                "email": "{{job.body.user_input.email}}",
                "keyword": "{{job.body.user_input.keyword}}",
            },
            "project": "{{job.body.project}}",
        }

        validator = BodyTemplateValidator()
        result = validator.validate(
            body_template=body_template,
            input_schema={"type": "object", "properties": {}},
            task_count=0,
            task_output_schemas=[],
            user_input_schema=user_input_schema,
        )

        # Should have no USER_INPUT_FIELD_MISMATCH warnings
        mismatch_warnings = [
            w for w in result.warnings if w.warning_type == "USER_INPUT_FIELD_MISMATCH"
        ]
        assert len(mismatch_warnings) == 0
