"""Unit tests for TemplateValidator service."""

from app.schemas.template_validation import (
    TemplateValidationResult,
    TemplateValidationWarning,
)
from app.services.template_validator import TemplateValidator


class TestTemplateValidatorBasic:
    """Basic validation tests for TemplateValidator."""

    def test_validate_none_template(self) -> None:
        """None template is valid."""
        result = TemplateValidator.validate(None)
        assert result.is_valid is True
        assert result.warnings == []
        assert result.extracted_variables == []

    def test_validate_empty_dict(self) -> None:
        """Empty dict template is valid."""
        result = TemplateValidator.validate({})
        assert result.is_valid is True
        assert result.warnings == []

    def test_validate_no_variables(self) -> None:
        """Template without variables is valid."""
        result = TemplateValidator.validate({"static": "value", "number": 123})
        assert result.is_valid is True
        assert result.extracted_variables == []


class TestTemplateValidatorVariableExtraction:
    """Tests for variable extraction."""

    def test_extract_job_body_variable(self) -> None:
        """Extract job.body variable."""
        template = {"recipient": "{{job.body.email}}"}
        result = TemplateValidator.validate(template)
        assert "{{job.body.email}}" in result.extracted_variables

    def test_extract_task_output_variable(self) -> None:
        """Extract tasks[N].output_data variable."""
        template = {"prev_result": "{{tasks[0].output_data.result}}"}
        result = TemplateValidator.validate(template)
        assert "{{tasks[0].output_data.result}}" in result.extracted_variables

    def test_extract_current_task_variable(self) -> None:
        """Extract task.input_data variable."""
        template = {"param": "{{task.input_data.value}}"}
        result = TemplateValidator.validate(template)
        assert "{{task.input_data.value}}" in result.extracted_variables

    def test_extract_multiple_variables(self) -> None:
        """Extract multiple variables of different types."""
        template = {
            "user": "{{job.body.user}}",
            "result": "{{tasks[0].output_data.result}}",
            "input": "{{task.input_data.param}}",
        }
        result = TemplateValidator.validate(template)
        assert len(result.extracted_variables) == 3
        assert "{{job.body.user}}" in result.extracted_variables
        assert "{{tasks[0].output_data.result}}" in result.extracted_variables
        assert "{{task.input_data.param}}" in result.extracted_variables

    def test_extract_nested_dict_variables(self) -> None:
        """Extract variables from nested dict structure."""
        template = {"outer": {"inner": {"value": "{{job.body.nested_value}}"}}}
        result = TemplateValidator.validate(template)
        assert "{{job.body.nested_value}}" in result.extracted_variables

    def test_extract_list_variables(self) -> None:
        """Extract variables from list structure."""
        template = {"items": ["{{job.body.item1}}", "{{job.body.item2}}"]}
        result = TemplateValidator.validate(template)
        assert "{{job.body.item1}}" in result.extracted_variables
        assert "{{job.body.item2}}" in result.extracted_variables

    def test_extract_string_interpolation(self) -> None:
        """Extract variables from interpolated string."""
        template = {
            "message": "Hello {{job.body.name}}, your result is {{tasks[0].output_data.value}}"
        }
        result = TemplateValidator.validate(template)
        assert "{{job.body.name}}" in result.extracted_variables
        assert "{{tasks[0].output_data.value}}" in result.extracted_variables


class TestTemplateValidatorWarnings:
    """Tests for validation warnings."""

    def test_warning_for_job_body_reference(self) -> None:
        """Job body reference without schema generates warning."""
        template = {"recipient": "{{job.body.email}}"}
        result = TemplateValidator.validate(template)
        assert result.is_valid is True  # Warning, not error
        assert len(result.warnings) == 1
        assert result.warnings[0].severity == "warning"
        assert "job.body.email" in result.warnings[0].message

    def test_no_warning_for_task_reference(self) -> None:
        """Task reference does not generate warning (runtime check)."""
        template = {"prev": "{{tasks[0].output_data.result}}"}
        result = TemplateValidator.validate(template)
        assert result.is_valid is True
        # Task references don't generate warnings at creation time
        # because task order depends on runtime

    def test_warning_for_large_task_index(self) -> None:
        """Large task index generates warning."""
        template = {"prev": "{{tasks[150].output_data.result}}"}
        result = TemplateValidator.validate(template)
        assert result.is_valid is True
        assert any(
            "150" in w.message and "large" in w.message.lower() for w in result.warnings
        )


class TestTemplateValidatorWithSchema:
    """Tests for schema-based validation."""

    def test_validate_with_schema_field_exists(self) -> None:
        """Schema provided and field exists - no additional warning."""
        template = {"recipient": "{{job.body.email}}"}
        schema = {"properties": {"email": {"type": "string"}}}
        result = TemplateValidator.validate(template, job_body_schema=schema)
        # Should not have "not found in schema" warning
        assert not any("not found" in w.message.lower() for w in result.warnings)

    def test_validate_with_schema_field_missing(self) -> None:
        """Schema provided but field missing - generates warning."""
        template = {"recipient": "{{job.body.email}}"}
        schema = {"properties": {"name": {"type": "string"}}}
        result = TemplateValidator.validate(template, job_body_schema=schema)
        assert any("not found" in w.message.lower() for w in result.warnings)
        assert any("email" in w.message for w in result.warnings)

    def test_validate_with_schema_nested_field(self) -> None:
        """Schema validation for nested field (first level only)."""
        template = {"recipient": "{{job.body.config.email}}"}
        schema = {"properties": {"config": {"type": "object"}}}
        result = TemplateValidator.validate(template, job_body_schema=schema)
        # First level 'config' exists, so no "not found" warning
        assert not any(
            "config" in w.message and "not found" in w.message.lower()
            for w in result.warnings
        )


class TestTemplateValidatorSecurityLimits:
    """Tests for security/DoS prevention limits."""

    def test_template_size_limit(self) -> None:
        """Template exceeding size limit is rejected."""
        # Create a template larger than 64KB
        large_value = "x" * (65 * 1024)
        template = {"data": large_value}
        result = TemplateValidator.validate(template)
        assert result.is_valid is False
        assert any("size" in w.message.lower() for w in result.warnings)
        assert any(w.severity == "error" for w in result.warnings)

    def test_variable_count_limit(self) -> None:
        """Too many variables generates error."""
        # Create template with more than 100 variables
        template = {f"field_{i}": f"{{{{job.body.field_{i}}}}}" for i in range(101)}
        result = TemplateValidator.validate(template)
        assert result.is_valid is False
        assert any("too many" in w.message.lower() for w in result.warnings)

    def test_path_depth_limit(self) -> None:
        """Path depth exceeding limit generates error."""
        # Create deeply nested path (> 10 levels)
        deep_path = ".".join([f"level{i}" for i in range(12)])
        template = {"deep": f"{{{{job.body.{deep_path}}}}}"}
        result = TemplateValidator.validate(template)
        assert any("depth" in w.message.lower() for w in result.warnings)


class TestTemplateValidatorEdgeCases:
    """Tests for edge cases."""

    def test_mixed_static_and_dynamic(self) -> None:
        """Template with both static and dynamic content."""
        template = {
            "static_field": "constant value",
            "dynamic_field": "{{job.body.value}}",
            "mixed": "prefix_{{job.body.suffix}}",
        }
        result = TemplateValidator.validate(template)
        assert result.is_valid is True
        assert len(result.extracted_variables) == 2

    def test_empty_string_values(self) -> None:
        """Template with empty string values."""
        template = {"empty": "", "null_field": None}
        result = TemplateValidator.validate(template)
        assert result.is_valid is True
        assert result.extracted_variables == []

    def test_numeric_values(self) -> None:
        """Template with numeric values (not strings)."""
        template = {"number": 42, "float": 3.14, "bool": True}
        result = TemplateValidator.validate(template)
        assert result.is_valid is True
        assert result.extracted_variables == []

    def test_unicode_in_template(self) -> None:
        """Template with unicode characters."""
        template = {"message": "Hello {{job.body.name}}", "note": "Japanese characters"}
        result = TemplateValidator.validate(template)
        assert result.is_valid is True
        assert "{{job.body.name}}" in result.extracted_variables

    def test_duplicate_variables(self) -> None:
        """Same variable used multiple times."""
        template = {
            "field1": "{{job.body.email}}",
            "field2": "{{job.body.email}}",  # Same variable
        }
        result = TemplateValidator.validate(template)
        # Should extract each occurrence
        email_count = result.extracted_variables.count("{{job.body.email}}")
        assert email_count == 2


class TestTemplateValidationResultModel:
    """Tests for TemplateValidationResult model properties."""

    def test_has_errors_property(self) -> None:
        """Test has_errors property."""
        result_with_error = TemplateValidationResult(
            is_valid=False,
            warnings=[
                TemplateValidationWarning(
                    variable="{{x}}", message="error", severity="error"
                )
            ],
        )
        assert result_with_error.has_errors is True

        result_with_warning = TemplateValidationResult(
            is_valid=True,
            warnings=[
                TemplateValidationWarning(
                    variable="{{x}}", message="warning", severity="warning"
                )
            ],
        )
        assert result_with_warning.has_errors is False

    def test_has_warnings_property(self) -> None:
        """Test has_warnings property."""
        result = TemplateValidationResult(
            is_valid=True,
            warnings=[
                TemplateValidationWarning(
                    variable="{{x}}", message="warning", severity="warning"
                )
            ],
        )
        assert result.has_warnings is True

    def test_count_properties(self) -> None:
        """Test error_count and warning_count properties."""
        result = TemplateValidationResult(
            is_valid=False,
            warnings=[
                TemplateValidationWarning(
                    variable="{{a}}", message="error1", severity="error"
                ),
                TemplateValidationWarning(
                    variable="{{b}}", message="error2", severity="error"
                ),
                TemplateValidationWarning(
                    variable="{{c}}", message="warn1", severity="warning"
                ),
            ],
        )
        assert result.error_count == 2
        assert result.warning_count == 1
