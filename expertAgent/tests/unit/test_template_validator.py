"""Unit tests for template_validator module (Issue #337).

Tests for template variable extraction and validation.
"""

from aiagent.langgraph.jobTaskGeneratorAgents.utils.template_validator import (
    get_template_variables,
    validate_derived_fields,
    validate_template,
)


class TestGetTemplateVariables:
    """Tests for get_template_variables function."""

    def test_single_variable(self) -> None:
        """Test extraction of single variable."""
        variables = get_template_variables("Hello {name}")
        assert variables == ["name"]

    def test_multiple_variables(self) -> None:
        """Test extraction of multiple variables."""
        variables = get_template_variables("Result: {summary} by {author}")
        assert variables == ["summary", "author"]

    def test_no_variables(self) -> None:
        """Test template without variables."""
        variables = get_template_variables("Plain text without variables")
        assert variables == []

    def test_empty_template(self) -> None:
        """Test empty template string."""
        variables = get_template_variables("")
        assert variables == []

    def test_repeated_variable(self) -> None:
        """Test template with repeated variable names."""
        variables = get_template_variables("{name} and {name} again")
        assert variables == ["name", "name"]

    def test_nested_braces_not_supported(self) -> None:
        """Test that nested braces are not supported (simple regex)."""
        # This tests current behavior - nested braces extract content with leading brace
        variables = get_template_variables("{{nested}}")
        # The regex will extract '{nested' from the first match
        assert "{nested" in variables

    def test_multiline_template(self) -> None:
        """Test multiline template."""
        template = """{title}

        {body}

        Regards,
        {sender}"""
        variables = get_template_variables(template)
        assert "title" in variables
        assert "body" in variables
        assert "sender" in variables

    def test_underscore_in_variable(self) -> None:
        """Test variable names with underscores."""
        variables = get_template_variables("{summary_text} and {key_points}")
        assert variables == ["summary_text", "key_points"]

    def test_dot_notation_in_variable(self) -> None:
        """Test variable names with dot notation."""
        variables = get_template_variables("{source.user_input.query}")
        assert variables == ["source.user_input.query"]


class TestValidateTemplate:
    """Tests for validate_template function."""

    def test_all_variables_in_properties(self) -> None:
        """Test template where all variables exist in properties."""
        template = "{summary_text} - {key_points}"
        properties = {
            "summary_text": {"type": "string"},
            "key_points": {"type": "string"},
        }
        unresolved = validate_template(template, properties)
        assert unresolved == []

    def test_variable_not_in_properties(self) -> None:
        """Test template with variable not in properties (from source.user_input)."""
        template = "Search result for: {query}"
        properties = {"summary_text": {"type": "string"}}
        unresolved = validate_template(template, properties)
        assert unresolved == ["query"]

    def test_mixed_variables(self) -> None:
        """Test template with mix of resolved and unresolved variables."""
        template = "{summary_text} for query: {query}"
        properties = {"summary_text": {"type": "string"}}
        unresolved = validate_template(template, properties)
        assert unresolved == ["query"]
        assert "summary_text" not in unresolved

    def test_source_mapping_resolves_variable(self) -> None:
        """Test that source_mapping resolves variables."""
        template = "File: {date}_{subject}.mp3"
        properties = {}
        source_mapping = {
            "date": "source.user_input.date",
            "subject": "extract_body.subject",
        }
        unresolved = validate_template(template, properties, source_mapping)
        assert unresolved == []

    def test_partial_source_mapping(self) -> None:
        """Test source_mapping that only partially resolves variables."""
        template = "Report: {title} - {status}"
        properties = {}
        source_mapping = {"title": "source.user_input.title"}
        unresolved = validate_template(template, properties, source_mapping)
        assert unresolved == ["status"]
        assert "title" not in unresolved

    def test_empty_template(self) -> None:
        """Test validation of empty template."""
        unresolved = validate_template("", {})
        assert unresolved == []

    def test_no_variables_template(self) -> None:
        """Test template without any variables."""
        unresolved = validate_template("Static text only", {"field": {"type": "string"}})
        assert unresolved == []


class TestValidateDerivedFields:
    """Tests for validate_derived_fields function."""

    def test_all_variables_resolved(self) -> None:
        """Test schema where all derived field variables are resolved."""
        output_schema = {
            "properties": {
                "summary_text": {"type": "string"},
                "key_points": {"type": "string"},
            },
            "x-derived-fields": {
                "email_body": {
                    "template": "{summary_text}\n\n{key_points}",
                }
            },
        }
        errors = validate_derived_fields(output_schema)
        assert errors == []

    def test_unresolved_variables_warning(self) -> None:
        """Test schema with unresolved variables (from source.user_input)."""
        output_schema = {
            "properties": {"summary_text": {"type": "string"}},
            "x-derived-fields": {
                "email_subject": {
                    "template": "Results for: {query}",
                }
            },
        }
        errors = validate_derived_fields(output_schema)
        assert len(errors) == 1
        assert errors[0]["field"] == "email_subject"
        assert "query" in errors[0]["unresolved_variables"]
        assert "source.user_input" in errors[0]["message"]

    def test_multiple_derived_fields(self) -> None:
        """Test validation of multiple derived fields."""
        output_schema = {
            "properties": {"result": {"type": "string"}},
            "x-derived-fields": {
                "email_subject": {"template": "Subject: {title}"},
                "email_body": {"template": "Body: {content}"},
                "valid_field": {"template": "Result: {result}"},
            },
        }
        errors = validate_derived_fields(output_schema)
        assert len(errors) == 2
        field_names = [e["field"] for e in errors]
        assert "email_subject" in field_names
        assert "email_body" in field_names
        assert "valid_field" not in field_names

    def test_no_derived_fields(self) -> None:
        """Test schema without x-derived-fields."""
        output_schema = {"properties": {"data": {"type": "string"}}}
        errors = validate_derived_fields(output_schema)
        assert errors == []

    def test_empty_derived_fields(self) -> None:
        """Test schema with empty x-derived-fields."""
        output_schema = {"properties": {}, "x-derived-fields": {}}
        errors = validate_derived_fields(output_schema)
        assert errors == []

    def test_source_mapping_in_derived_field(self) -> None:
        """Test derived field with source_mapping."""
        output_schema = {
            "properties": {},
            "x-derived-fields": {
                "filename": {
                    "template": "podcast_{date}_{subject}.mp3",
                    "source_mapping": {
                        "date": "source.user_input.date",
                        "subject": "extract_body.subject",
                    },
                }
            },
        }
        errors = validate_derived_fields(output_schema)
        assert errors == []

    def test_no_properties_key(self) -> None:
        """Test schema without properties key."""
        output_schema = {
            "x-derived-fields": {
                "field1": {"template": "Value: {var}"},
            }
        }
        errors = validate_derived_fields(output_schema)
        assert len(errors) == 1
        assert "var" in errors[0]["unresolved_variables"]
