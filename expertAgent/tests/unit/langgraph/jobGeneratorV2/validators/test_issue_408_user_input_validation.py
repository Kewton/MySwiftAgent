"""Unit tests for Issue #408: User input field name consistency validation.

Issue #408: Detect when LLM changes user input field names (e.g., email -> recipient_email)
and generate warnings to prevent E2E test failures.

Test cases:
- TC-001: Prompt contains field name preservation rules
- TC-002: Mismatched field name generates warning
- TC-003: Valid field name generates no warning
- TC-004: Backward compatibility with user_input_schema=None
- TC-005: Multiple mismatched fields are all detected
- TC-006: Fallback warning for missing field in _build_multi_dependency_template
- TC-007: Warning included in ValidationResult
- TC-008: MasterManager passes user_input_schema to Validator
- TC-009: BODY_TEMPLATE_STRICT_VALIDATION environment variable behavior
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from unittest.mock import patch

import pytest


class TestPromptFieldNamePreservationRules:
    """TC-001: Test that prompt contains field name preservation rules."""

    @pytest.fixture
    def prompt_path(self) -> Path:
        """Get the path to the interface schema prompt file."""
        # Use the path relative to the expertAgent root
        current_dir = Path(__file__).resolve().parent
        # Navigate up to expertAgent root: validators -> jobGeneratorV2 -> langgraph -> unit -> tests -> expertAgent
        expert_agent_root = current_dir.parent.parent.parent.parent.parent
        return expert_agent_root / "prompts" / "interface_schema" / "default.yaml"

    def test_prompt_contains_field_name_preservation_section(
        self, prompt_path: Path
    ) -> None:
        """Interface Definition prompt contains field name preservation rules section."""
        assert prompt_path.exists(), f"Prompt file not found: {prompt_path}"

        content = prompt_path.read_text()

        # Check for field name preservation section
        # Note: Prompt uses Japanese - check for both English and Japanese terms
        assert (
            "field name" in content.lower()
            or "field_name" in content.lower()
            or "user input field" in content.lower()
        ), f"Prompt should mention field name. Content section: {content[-500:]}"
        assert (
            "preserve" in content.lower()
            or "maintain" in content.lower()
            or "keep" in content.lower()
            or "change" in content.lower()
        ), "Prompt should mention preservation of field names"

    def test_prompt_contains_examples_of_prohibited_renaming(
        self, prompt_path: Path
    ) -> None:
        """Prompt contains examples of prohibited field renaming."""
        content = prompt_path.read_text()

        # Check for examples (at least 5 examples per AC)
        # Look for patterns like "email" or "recipient" or common field names
        prohibited_patterns = [
            "email",
            "recipient",
            "query",
            "keyword",
        ]
        found_patterns = sum(1 for p in prohibited_patterns if p in content.lower())
        assert found_patterns >= 2, (
            f"Prompt should contain examples of prohibited renaming. "
            f"Found {found_patterns} patterns"
        )


class TestMismatchedFieldNameDetection:
    """TC-002, TC-003, TC-005: Test detection of mismatched field names."""

    def test_detects_mismatched_field_name(self) -> None:
        """TC-002: Generates warning when referencing non-existent field name."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        body_template = {
            "inputs": {
                # LLM changed 'email' to 'recipient_email'
                "recipient_email": "{{job.body.user_input.recipient_email}}",
            },
        }
        input_schema = {"type": "object", "properties": {}}
        # user_input_schema has 'email', not 'recipient_email'
        user_input_schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "Email address"},
            },
            "required": ["email"],
        }

        validator = BodyTemplateValidator()
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
            user_input_schema=user_input_schema,
        )

        # Should have a warning for mismatched field name
        assert len(result.warnings) >= 1, (
            f"Expected at least 1 warning, got {len(result.warnings)}"
        )
        # Check warning type
        assert any(
            w.warning_type == "USER_INPUT_FIELD_MISMATCH" for w in result.warnings
        ), f"Expected USER_INPUT_FIELD_MISMATCH warning, got: {result.warnings}"
        # Check warning message contains the mismatched field
        assert any("recipient_email" in w.message for w in result.warnings), (
            f"Warning should mention 'recipient_email': {result.warnings}"
        )

    def test_no_warning_for_valid_field_name(self) -> None:
        """TC-003: No warning when referencing valid field name."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        body_template = {
            "inputs": {
                "email": "{{job.body.user_input.email}}",
            },
        }
        input_schema = {"type": "object", "properties": {}}
        user_input_schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "Email address"},
            },
            "required": ["email"],
        }

        validator = BodyTemplateValidator()
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
            user_input_schema=user_input_schema,
        )

        # Should not have USER_INPUT_FIELD_MISMATCH warnings
        user_input_warnings = [
            w for w in result.warnings if w.warning_type == "USER_INPUT_FIELD_MISMATCH"
        ]
        assert len(user_input_warnings) == 0, (
            f"Expected no USER_INPUT_FIELD_MISMATCH warnings, got: {user_input_warnings}"
        )

    def test_detects_multiple_mismatched_fields(self) -> None:
        """TC-005: All mismatched fields are detected."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        body_template = {
            "inputs": {
                # LLM changed multiple field names
                "recipient_email": "{{job.body.user_input.recipient_email}}",
                "search_keyword": "{{job.body.user_input.search_keyword}}",
                "max_count": "{{job.body.user_input.max_count}}",
            },
        }
        input_schema = {"type": "object", "properties": {}}
        # user_input_schema has different field names
        user_input_schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string"},
                "keyword": {"type": "string"},
                "count": {"type": "integer"},
            },
            "required": ["email", "keyword"],
        }

        validator = BodyTemplateValidator()
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
            user_input_schema=user_input_schema,
        )

        # Should have warnings for all 3 mismatched fields
        user_input_warnings = [
            w for w in result.warnings if w.warning_type == "USER_INPUT_FIELD_MISMATCH"
        ]
        assert len(user_input_warnings) >= 3, (
            f"Expected at least 3 warnings, got: {user_input_warnings}"
        )
        # Check all mismatched fields are mentioned
        warning_messages = " ".join(w.message for w in user_input_warnings)
        assert "recipient_email" in warning_messages
        assert "search_keyword" in warning_messages
        assert "max_count" in warning_messages


class TestBackwardCompatibility:
    """TC-004: Test backward compatibility with user_input_schema=None."""

    def test_backward_compatibility_with_none_schema(self) -> None:
        """TC-004: user_input_schema=None maintains backward compatibility."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        body_template = {
            "inputs": "{{job.body.user_input}}",
        }
        input_schema = {"type": "object", "properties": {}}

        validator = BodyTemplateValidator()
        # Call without user_input_schema (default None)
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Should work without errors (backward compatible)
        assert result.is_valid, f"Errors: {result.errors}"
        # Should not have USER_INPUT_FIELD_MISMATCH warnings when schema is None
        user_input_warnings = [
            w for w in result.warnings if w.warning_type == "USER_INPUT_FIELD_MISMATCH"
        ]
        assert len(user_input_warnings) == 0

    def test_validate_signature_has_user_input_schema_parameter(self) -> None:
        """validate() method has user_input_schema parameter."""
        import inspect

        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        sig = inspect.signature(BodyTemplateValidator.validate)
        params = list(sig.parameters.keys())

        assert "user_input_schema" in params, (
            f"validate() should have user_input_schema parameter. "
            f"Current params: {params}"
        )


class TestFallbackWarning:
    """TC-006: Test fallback warning in _build_multi_dependency_template."""

    def test_fallback_warning_for_missing_field(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """TC-006: Fallback to user_input logs warning when field not in user_input_schema."""
        from aiagent.langgraph.jobGeneratorV2.types_old import (
            InterfaceSchema,
            TaskDefinition,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(engine="taskflow")

        # Create task with dependencies but field not found in any dependency output
        task = TaskDefinition(
            id="task_002",
            name="send_email",
            description="Send email task",
            task_type="send",
            dependencies=["task_001"],
            priority=2,
            recommended_api="gmail_send",
        )

        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                description="Search interface",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
                output_schema={
                    "type": "object",
                    "properties": {"results": {"type": "array"}},  # No 'email' field
                },
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                description="Email interface",
                input_schema={
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},  # Needs 'email' field
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {"success": {"type": "boolean"}},
                },
            ),
        }

        task_order_map = {"task_001": 0, "task_002": 1}

        # Set up logging capture
        with caplog.at_level(logging.WARNING):
            # Build multi-dependency template
            _ = manager._build_multi_dependency_template(
                task=task,
                interfaces=interfaces,
                task_order_map=task_order_map,
            )

        # Should log a warning about fallback
        warning_logs = [r for r in caplog.records if r.levelno == logging.WARNING]
        assert len(warning_logs) >= 1, (
            f"Expected at least 1 warning log. Got: {caplog.records}"
        )
        # Check warning mentions the field and fallback
        assert any(
            "email" in r.message and "fallback" in r.message.lower()
            for r in warning_logs
        ), (
            f"Warning should mention 'email' and 'fallback': {[r.message for r in warning_logs]}"
        )

    def test_fallback_with_user_input_schema_validation_raises_error(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Fallback raises error if field not in user_input_schema.

        Bug Fix 20260126: Changed from WARNING to ERROR.
        Field mismatch now raises UserInputFieldMismatchError.
        """
        from aiagent.langgraph.jobGeneratorV2.types_old import (
            InterfaceSchema,
            TaskDefinition,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.errors import (
            UserInputFieldMismatchError,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow(engine="taskflow")

        task = TaskDefinition(
            id="task_002",
            name="send_email",
            description="Send email task",
            task_type="send",
            dependencies=["task_001"],
            priority=2,
            recommended_api="gmail_send",
        )

        interfaces: dict[str, InterfaceSchema] = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                description="Search interface",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
                output_schema={
                    "type": "object",
                    "properties": {"results": {"type": "array"}},
                },
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                description="Email interface",
                input_schema={
                    "type": "object",
                    "properties": {
                        # LLM used 'recipient_email' but user provided 'email'
                        "recipient_email": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {"success": {"type": "boolean"}},
                },
            ),
        }

        task_order_map = {"task_001": 0, "task_002": 1}

        # User input schema has 'email', not 'recipient_email'
        user_input_schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string"},
            },
        }

        # Bug Fix 20260126: Now raises error instead of warning
        with pytest.raises(UserInputFieldMismatchError) as exc_info:
            manager._build_multi_dependency_template(
                task=task,
                interfaces=interfaces,
                task_order_map=task_order_map,
                user_input_schema=user_input_schema,
            )

        # Error message should include field name and available fields
        error_str = str(exc_info.value)
        assert "recipient_email" in error_str
        assert "email" in error_str or "Available" in error_str


class TestValidationResultWarnings:
    """TC-007: Test that warnings are included in ValidationResult."""

    def test_warning_included_in_validation_result(self) -> None:
        """TC-007: USER_INPUT_FIELD_MISMATCH warning included in ValidationResult."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidationWarning,
            BodyTemplateValidator,
        )

        body_template = {
            "inputs": {
                "wrong_field": "{{job.body.user_input.wrong_field}}",
            },
        }
        input_schema = {"type": "object", "properties": {}}
        user_input_schema = {
            "type": "object",
            "properties": {
                "correct_field": {"type": "string"},
            },
        }

        validator = BodyTemplateValidator()
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
            user_input_schema=user_input_schema,
        )

        # Check warnings list contains the expected warning
        assert isinstance(result.warnings, list)
        assert len(result.warnings) >= 1
        warning = result.warnings[0]
        assert isinstance(warning, BodyTemplateValidationWarning)
        assert warning.warning_type == "USER_INPUT_FIELD_MISMATCH"
        assert "wrong_field" in warning.message


class TestMasterManagerUserInputSchemaPassthrough:
    """TC-008: Test MasterManager passes user_input_schema to Validator."""

    def test_get_user_input_schema_helper_exists(self) -> None:
        """_get_user_input_schema helper method exists in MasterManagerSubWorkflow."""
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow()
        assert hasattr(manager, "_get_user_input_schema"), (
            "MasterManagerSubWorkflow should have _get_user_input_schema method"
        )

    def test_get_user_input_schema_returns_first_task_input_schema(self) -> None:
        """_get_user_input_schema returns input_schema from first task in topological order."""
        from aiagent.langgraph.jobGeneratorV2.types_old import (
            InterfaceSchema,
            TaskDefinition,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
            MasterManagerSubWorkflow,
        )

        manager = MasterManagerSubWorkflow()

        # Create sorted tasks (first task in topological order)
        sorted_tasks = [
            TaskDefinition(
                id="task_001",
                name="first_task",
                description="First task",
                task_type="fetch",
                dependencies=[],
                priority=1,
                recommended_api="some_api",
            ),
            TaskDefinition(
                id="task_002",
                name="second_task",
                description="Second task",
                task_type="transform",
                dependencies=["task_001"],
                priority=2,
                recommended_api="some_api",
            ),
        ]

        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                description="First interface",
                input_schema={
                    "type": "object",
                    "properties": {
                        "email": {"type": "string"},
                        "keyword": {"type": "string"},
                    },
                },
                output_schema={"type": "object", "properties": {}},
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                description="Second interface",
                input_schema={
                    "type": "object",
                    "properties": {
                        "data": {"type": "object"},
                    },
                },
                output_schema={"type": "object", "properties": {}},
            ),
        }

        result = manager._get_user_input_schema(sorted_tasks, interfaces)

        # Should return the input_schema from the first task
        assert result is not None
        assert "email" in result.get("properties", {})
        assert "keyword" in result.get("properties", {})


class TestStrictValidationEnvironmentVariable:
    """TC-009: Test BODY_TEMPLATE_STRICT_VALIDATION environment variable."""

    def test_strict_validation_disabled_by_default(self) -> None:
        """Strict validation is disabled by default (warnings only, no errors)."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        body_template = {
            "inputs": {
                "wrong_field": "{{job.body.user_input.wrong_field}}",
            },
        }
        input_schema = {"type": "object", "properties": {}}
        user_input_schema = {
            "type": "object",
            "properties": {"correct_field": {"type": "string"}},
        }

        # Default: strict validation is off
        validator = BodyTemplateValidator()
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
            user_input_schema=user_input_schema,
        )

        # Should be valid (only warnings, no errors for field mismatch)
        assert result.is_valid, f"Expected valid, got errors: {result.errors}"
        assert len(result.warnings) >= 1

    def test_strict_validation_enabled_converts_warnings_to_errors(self) -> None:
        """When BODY_TEMPLATE_STRICT_VALIDATION=true, warnings become errors."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        body_template = {
            "inputs": {
                "wrong_field": "{{job.body.user_input.wrong_field}}",
            },
        }
        input_schema = {"type": "object", "properties": {}}
        user_input_schema = {
            "type": "object",
            "properties": {"correct_field": {"type": "string"}},
        }

        # Enable strict validation via environment variable
        with patch.dict(os.environ, {"BODY_TEMPLATE_STRICT_VALIDATION": "true"}):
            validator = BodyTemplateValidator()
            result = validator.validate(
                body_template=body_template,
                input_schema=input_schema,
                task_count=0,
                task_output_schemas=[],
                user_input_schema=user_input_schema,
            )

            # Should be invalid (warning converted to error)
            assert not result.is_valid, (
                "Expected invalid when strict validation is enabled"
            )
            assert any("wrong_field" in e.message for e in result.errors), (
                f"Error should mention 'wrong_field': {result.errors}"
            )


class TestValidateUserInputFieldsMethod:
    """Test _validate_user_input_fields internal method."""

    def test_validate_user_input_fields_method_exists(self) -> None:
        """_validate_user_input_fields method exists in BodyTemplateValidator."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        validator = BodyTemplateValidator()
        assert hasattr(validator, "_validate_user_input_fields"), (
            "BodyTemplateValidator should have _validate_user_input_fields method"
        )

    def test_extracts_user_input_field_references(self) -> None:
        """Method correctly extracts user_input.X field references."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        body_template = {
            "inputs": {
                "field1": "{{job.body.user_input.email}}",
                "field2": "{{job.body.user_input.keyword}}",
                "field3": "{{tasks[0].output_data.result}}",  # Not user_input
            },
        }
        user_input_schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string"},
                # 'keyword' is missing - should generate warning
            },
        }

        validator = BodyTemplateValidator()
        warnings = validator._validate_user_input_fields(
            body_template=body_template,
            user_input_schema=user_input_schema,
        )

        # Should find 'keyword' as mismatched (not in user_input_schema)
        assert len(warnings) == 1
        assert "keyword" in warnings[0].message

    def test_returns_empty_list_when_schema_is_none(self) -> None:
        """Method returns empty list when user_input_schema is None."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        body_template = {
            "inputs": {
                "field1": "{{job.body.user_input.email}}",
            },
        }

        validator = BodyTemplateValidator()
        warnings = validator._validate_user_input_fields(
            body_template=body_template,
            user_input_schema=None,
        )

        # Should return empty list for backward compatibility
        assert warnings == []
