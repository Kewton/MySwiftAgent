"""Unit tests for body_template_validator.py.

Issue #358: Tests for BodyTemplateValidator class.

Test cases:
1. Valid body_template with correct references
2. Invalid job.body reference (missing field in input_schema)
3. Invalid tasks[N] reference (N >= task_count)
4. Valid task output reference
5. Multiple errors reported together
6. Warnings for optional issues
7. ValidationStrategy pattern (TaskFlow/GraphAI)
"""

from typing import Any


class TestBodyTemplateValidator:
    """Test BodyTemplateValidator class."""

    def test_valid_body_template(self) -> None:
        """Valid body_template passes validation."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        body_template = {
            "workflow_name": "test",
            "inputs": "{{job.body}}",
            "project": "{{job.project}}",
        }
        input_schema = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
            },
        }

        validator = BodyTemplateValidator()
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        assert result.is_valid
        assert len(result.errors) == 0

    def test_invalid_job_body_reference(self) -> None:
        """Invalid job.body field reference returns error."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        body_template = {
            "user_input": "{{job.body.nonexistent_field}}",
        }
        input_schema = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
            },
        }

        validator = BodyTemplateValidator()
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        assert not result.is_valid
        assert len(result.errors) >= 1
        assert any("nonexistent_field" in e.message for e in result.errors)

    def test_invalid_task_index_reference(self) -> None:
        """Invalid task index (N >= task_count) returns error."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        body_template = {
            "inputs": "{{tasks[5].output_data}}",  # Only 2 tasks exist
        }
        input_schema: dict[str, Any] = {}

        validator = BodyTemplateValidator()
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=2,  # tasks[0] and tasks[1] are valid
            task_output_schemas=[{}, {}],
        )

        assert not result.is_valid
        assert any("task index" in e.message.lower() for e in result.errors)

    def test_valid_task_output_reference(self) -> None:
        """Valid task output reference passes."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        body_template = {
            "inputs": "{{tasks[0].output_data}}",
        }
        input_schema: dict[str, Any] = {}
        task_output_schemas = [
            {"type": "object", "properties": {"result": {"type": "string"}}},
        ]

        validator = BodyTemplateValidator()
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=1,
            task_output_schemas=task_output_schemas,
        )

        assert result.is_valid

    def test_task_output_field_validation(self) -> None:
        """Validate field path in task output reference."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        body_template = {
            "result": "{{tasks[0].output_data.missing_field}}",
        }
        task_output_schemas = [
            {"type": "object", "properties": {"result": {"type": "string"}}},
        ]

        validator = BodyTemplateValidator()
        result = validator.validate(
            body_template=body_template,
            input_schema={},
            task_count=1,
            task_output_schemas=task_output_schemas,
        )

        assert not result.is_valid
        assert any("missing_field" in e.message for e in result.errors)

    def test_multiple_errors_reported(self) -> None:
        """Multiple errors are collected and reported."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        body_template = {
            "field1": "{{job.body.missing1}}",
            "field2": "{{job.body.missing2}}",
            "field3": "{{tasks[10].output_data}}",
        }
        input_schema = {
            "type": "object",
            "properties": {},
        }

        validator = BodyTemplateValidator()
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=2,
            task_output_schemas=[{}, {}],
        )

        assert not result.is_valid
        assert len(result.errors) >= 2  # At least missing fields + invalid task index

    def test_warnings_for_unreferenced_schema_fields(self) -> None:
        """Warnings generated for schema fields not referenced in template."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        body_template = {
            "inputs": "{{job.body}}",  # References all of job.body
        }
        input_schema = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
                "optional_param": {"type": "string"},  # Not specifically referenced
            },
        }

        validator = BodyTemplateValidator()
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # When using {{job.body}}, all fields are referenced
        assert result.is_valid

    def test_result_contains_required_job_body_fields(self) -> None:
        """Result contains list of required job body fields."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        body_template = {
            "user_input": "{{job.body.user_input}}",
            "email": "{{job.body.recipient_email}}",
        }
        input_schema = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
                "recipient_email": {"type": "string"},
            },
        }

        validator = BodyTemplateValidator()
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        assert "user_input" in result.required_job_body_fields
        assert "recipient_email" in result.required_job_body_fields


class TestBodyTemplateValidationResult:
    """Test BodyTemplateValidationResult dataclass."""

    def test_is_valid_with_no_errors(self) -> None:
        """is_valid is True when no errors."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidationResult,
        )

        result = BodyTemplateValidationResult(
            errors=[],
            warnings=[],
            required_job_body_fields=set(),
        )

        assert result.is_valid

    def test_is_valid_with_errors(self) -> None:
        """is_valid is False when errors exist."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidationError,
            BodyTemplateValidationResult,
        )

        result = BodyTemplateValidationResult(
            errors=[
                BodyTemplateValidationError(
                    error_type="MISSING_REFERENCE",
                    message="Field not found",
                    location="job.body.field",
                )
            ],
            warnings=[],
            required_job_body_fields=set(),
        )

        assert not result.is_valid

    def test_warnings_do_not_affect_validity(self) -> None:
        """Warnings don't make result invalid."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidationResult,
            BodyTemplateValidationWarning,
        )

        result = BodyTemplateValidationResult(
            errors=[],
            warnings=[
                BodyTemplateValidationWarning(
                    warning_type="UNUSED_FIELD",
                    message="Field not used",
                    location="input_schema.optional_field",
                )
            ],
            required_job_body_fields=set(),
        )

        assert result.is_valid


class TestValidationStrategy:
    """Test ValidationStrategy pattern for different engines."""

    def test_taskflow_strategy(self) -> None:
        """TaskFlowValidationStrategy validates TaskFlow patterns."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
            TaskFlowValidationStrategy,
        )

        strategy = TaskFlowValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)

        body_template = {
            "workflow_name": "__PENDING__",
            "inputs": "{{job.body}}",
            "project": "{{job.project}}",
        }

        result = validator.validate(
            body_template=body_template,
            input_schema={"type": "object", "properties": {}},
            task_count=0,
            task_output_schemas=[],
        )

        assert result.is_valid

    def test_graphai_strategy(self) -> None:
        """GraphAIValidationStrategy validates GraphAI patterns."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
            GraphAIValidationStrategy,
        )

        strategy = GraphAIValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)

        body_template = {
            "user_input": "{{job.body.user_input}}",
            "job_params": "{{job.body}}",
        }
        input_schema = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
            },
        }

        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        assert result.is_valid


class TestValidationErrorTypes:
    """Test error type classification."""

    def test_missing_reference_error_type(self) -> None:
        """MISSING_REFERENCE error type for field not found."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        body_template = {"field": "{{job.body.nonexistent}}"}
        input_schema = {"type": "object", "properties": {}}

        validator = BodyTemplateValidator()
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        assert any(e.error_type == "MISSING_REFERENCE" for e in result.errors)

    def test_invalid_index_error_type(self) -> None:
        """INVALID_INDEX error type for out of bounds task index."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
        )

        body_template = {"field": "{{tasks[99].output_data}}"}

        validator = BodyTemplateValidator()
        result = validator.validate(
            body_template=body_template,
            input_schema={},
            task_count=2,
            task_output_schemas=[{}, {}],
        )

        assert any(e.error_type == "INVALID_INDEX" for e in result.errors)


class TestSystemInjectedFields:
    """Test Issue #395: System-injected fields validation exclusion."""

    def test_system_injected_fields_constant_exists(self) -> None:
        """SYSTEM_INJECTED_FIELDS constant exists and contains 'project'."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            SYSTEM_INJECTED_FIELDS,
        )

        assert SYSTEM_INJECTED_FIELDS is not None
        assert "project" in SYSTEM_INJECTED_FIELDS

    def test_system_injected_fields_is_immutable(self) -> None:
        """SYSTEM_INJECTED_FIELDS is a frozenset and immutable."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            SYSTEM_INJECTED_FIELDS,
        )

        assert isinstance(SYSTEM_INJECTED_FIELDS, frozenset)
        # Attempting to add should raise AttributeError
        import pytest

        with pytest.raises(AttributeError):
            SYSTEM_INJECTED_FIELDS.add("new_field")  # type: ignore[attr-defined]

    def test_project_field_validation_skipped(self) -> None:
        """project field (system-injected) is skipped from validation."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
            TaskFlowValidationStrategy,
        )

        body_template = {
            "project": "{{job.body.project}}",
            "user_input": "{{job.body.user_input}}",
        }
        # input_schema does NOT have 'project' - it's system-injected
        input_schema = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
            },
        }

        strategy = TaskFlowValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Should be valid - 'project' is skipped, 'user_input' exists
        assert result.is_valid, f"Errors: {[e.message for e in result.errors]}"
        assert not any("project" in e.message for e in result.errors)

    def test_user_field_validation_continues_when_missing(self) -> None:
        """Non-system fields continue to be validated and report errors."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
            TaskFlowValidationStrategy,
        )

        body_template = {
            "project": "{{job.body.project}}",
            "missing_field": "{{job.body.nonexistent}}",
        }
        input_schema = {
            "type": "object",
            "properties": {},
        }

        strategy = TaskFlowValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Should fail - 'nonexistent' is not in schema and not a system field
        assert not result.is_valid
        assert any("nonexistent" in e.message for e in result.errors)
        # But 'project' should NOT be in errors
        assert not any("project" in e.message for e in result.errors)

    def test_user_field_validation_passes_when_exists(self) -> None:
        """User fields pass validation when they exist in input_schema."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
            TaskFlowValidationStrategy,
        )

        body_template = {
            "project": "{{job.body.project}}",
            "user_input": "{{job.body.user_input}}",
        }
        input_schema = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
            },
        }

        strategy = TaskFlowValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        assert result.is_valid

    def test_mixed_system_and_user_fields(self) -> None:
        """Mixed system and user fields: system skipped, user validated."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
            TaskFlowValidationStrategy,
        )

        body_template = {
            "project": "{{job.body.project}}",  # system-injected, skip
            "user_input": "{{job.body.user_input}}",  # exists in schema
            "missing": "{{job.body.missing_user_field}}",  # not in schema
        }
        input_schema = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
            },
        }

        strategy = TaskFlowValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        # Should fail for missing_user_field only
        assert not result.is_valid
        assert len(result.errors) == 1
        assert "missing_user_field" in result.errors[0].message
        assert "project" not in result.errors[0].message

    def test_graphai_strategy_also_skips_system_fields(self) -> None:
        """GraphAI strategy also skips system-injected fields."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
            GraphAIValidationStrategy,
        )

        body_template = {
            "project": "{{job.body.project}}",
            "user_input": "{{job.body.user_input}}",
        }
        input_schema = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
            },
        }

        strategy = GraphAIValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        assert result.is_valid, f"Errors: {[e.message for e in result.errors]}"


class TestGraphAIValidationStrategy:
    """Test GraphAIValidationStrategy for complete coverage."""

    def test_graphai_task_reference_invalid_index(self) -> None:
        """GraphAI strategy reports error for invalid task index."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
            GraphAIValidationStrategy,
        )

        body_template = {
            "inputs": "{{tasks[5].output_data}}",
        }

        strategy = GraphAIValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)
        result = validator.validate(
            body_template=body_template,
            input_schema={},
            task_count=2,
            task_output_schemas=[{}, {}],
        )

        assert not result.is_valid
        assert any(e.error_type == "INVALID_INDEX" for e in result.errors)

    def test_graphai_task_reference_valid(self) -> None:
        """GraphAI strategy validates valid task reference."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
            GraphAIValidationStrategy,
        )

        body_template = {
            "inputs": "{{tasks[0].output_data}}",
        }

        strategy = GraphAIValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)
        result = validator.validate(
            body_template=body_template,
            input_schema={},
            task_count=1,
            task_output_schemas=[{"type": "object", "properties": {"result": {}}}],
        )

        assert result.is_valid

    def test_graphai_task_reference_missing_field(self) -> None:
        """GraphAI strategy reports error for missing field in task output."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
            GraphAIValidationStrategy,
        )

        body_template = {
            "result": "{{tasks[0].output_data.nonexistent_field}}",
        }
        task_output_schemas = [
            {"type": "object", "properties": {"result": {"type": "string"}}},
        ]

        strategy = GraphAIValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)
        result = validator.validate(
            body_template=body_template,
            input_schema={},
            task_count=1,
            task_output_schemas=task_output_schemas,
        )

        assert not result.is_valid
        assert any("nonexistent_field" in e.message for e in result.errors)

    def test_graphai_job_body_missing_field(self) -> None:
        """GraphAI strategy reports error for missing field in job.body."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
            GraphAIValidationStrategy,
        )

        body_template = {
            "field": "{{job.body.missing_field}}",
        }
        input_schema = {"type": "object", "properties": {}}

        strategy = GraphAIValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)
        result = validator.validate(
            body_template=body_template,
            input_schema=input_schema,
            task_count=0,
            task_output_schemas=[],
        )

        assert not result.is_valid
        assert any("missing_field" in e.message for e in result.errors)

    def test_graphai_job_body_entire_body(self) -> None:
        """GraphAI strategy accepts {{job.body}} (entire body) reference."""
        from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
            BodyTemplateValidator,
            GraphAIValidationStrategy,
        )

        body_template = {
            "job_params": "{{job.body}}",
        }

        strategy = GraphAIValidationStrategy()
        validator = BodyTemplateValidator(strategy=strategy)
        result = validator.validate(
            body_template=body_template,
            input_schema={"type": "object", "properties": {}},
            task_count=0,
            task_output_schemas=[],
        )

        assert result.is_valid
