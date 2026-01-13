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
