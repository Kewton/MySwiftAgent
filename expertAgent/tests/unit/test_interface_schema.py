"""Unit tests for interface schema definition.

Issue #338 Phase 8: Tests for derived_fields validation and graceful degradation.
"""

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents.prompts.interface_schema import (
    DerivedFieldDefinition,
    InterfaceSchemaDefinition,
    InterfaceSchemaResponse,
    get_derived_fields_degradation_count,
    reset_derived_fields_degradation_count,
)


class TestDerivedFieldDefinition:
    """Tests for DerivedFieldDefinition model."""

    def test_valid_derived_field(self):
        """Valid derived field definition should be accepted."""
        data = {
            "template": "Search results: {query}",
            "type": "string",
            "description": "Email subject line",
        }
        result = DerivedFieldDefinition.model_validate(data)
        assert result.template == "Search results: {query}"
        assert result.type == "string"
        assert result.description == "Email subject line"

    def test_minimal_derived_field(self):
        """Minimal derived field (template only) should work."""
        data = {"template": "{count} items found"}
        result = DerivedFieldDefinition.model_validate(data)
        assert result.template == "{count} items found"
        assert result.type == "string"  # default
        assert result.description is None

    def test_derived_field_with_source_mapping(self):
        """Derived field with source_mapping should be accepted."""
        data = {
            "template": "Query: {q}",
            "type": "string",
            "source_mapping": {"q": "source.user_input.query"},
        }
        result = DerivedFieldDefinition.model_validate(data)
        assert result.source_mapping == {"q": "source.user_input.query"}


class TestInterfaceSchemaDefinitionDerivedFields:
    """Issue #338 Phase 8: Tests for derived_fields validation."""

    def setup_method(self):
        """Reset degradation counter before each test."""
        reset_derived_fields_degradation_count()

    def test_derived_fields_dict_passthrough(self):
        """Valid dict format should pass through unchanged."""
        data = {
            "task_id": "task_001",
            "interface_name": "test_interface",
            "description": "Test interface",
            "input_schema": {"type": "object", "properties": {}},
            "output_schema": {"type": "object", "properties": {}},
            "derived_fields": {
                "email_subject": {"template": "{query}", "type": "string"}
            },
        }
        result = InterfaceSchemaDefinition.model_validate(data)
        assert "email_subject" in result.derived_fields
        assert result.derived_fields["email_subject"].template == "{query}"

    def test_derived_fields_string_graceful_degradation(self, caplog):
        """String format should degrade to empty dict with warning."""
        data = {
            "task_id": "task_001",
            "interface_name": "test_interface",
            "description": "Test interface",
            "input_schema": {"type": "object", "properties": {}},
            "output_schema": {"type": "object", "properties": {}},
            "derived_fields": "results -> task_002.input.search_results",
        }
        result = InterfaceSchemaDefinition.model_validate(data)
        assert result.derived_fields == {}
        assert get_derived_fields_degradation_count() == 1
        assert "Issue #338" in caplog.text
        assert "graceful degradation" in caplog.text

    def test_derived_fields_none_to_empty_dict(self):
        """None should become empty dict without warning."""
        data = {
            "task_id": "task_001",
            "interface_name": "test_interface",
            "description": "Test interface",
            "input_schema": {"type": "object", "properties": {}},
            "output_schema": {"type": "object", "properties": {}},
            "derived_fields": None,
        }
        result = InterfaceSchemaDefinition.model_validate(data)
        assert result.derived_fields == {}
        # None should not increment degradation count (it's expected)
        assert get_derived_fields_degradation_count() == 0

    def test_derived_fields_empty_dict_passthrough(self):
        """Empty dict should pass through unchanged."""
        data = {
            "task_id": "task_001",
            "interface_name": "test_interface",
            "description": "Test interface",
            "input_schema": {"type": "object", "properties": {}},
            "output_schema": {"type": "object", "properties": {}},
            "derived_fields": {},
        }
        result = InterfaceSchemaDefinition.model_validate(data)
        assert result.derived_fields == {}
        assert get_derived_fields_degradation_count() == 0

    def test_derived_fields_list_graceful_degradation(self, caplog):
        """List format should degrade to empty dict with warning."""
        data = {
            "task_id": "task_001",
            "interface_name": "test_interface",
            "description": "Test interface",
            "input_schema": {"type": "object", "properties": {}},
            "output_schema": {"type": "object", "properties": {}},
            "derived_fields": ["invalid", "list", "format"],
        }
        result = InterfaceSchemaDefinition.model_validate(data)
        assert result.derived_fields == {}
        assert get_derived_fields_degradation_count() == 1
        assert "unexpected type" in caplog.text

    def test_derived_fields_int_graceful_degradation(self, caplog):
        """Integer format should degrade to empty dict with warning."""
        data = {
            "task_id": "task_001",
            "interface_name": "test_interface",
            "description": "Test interface",
            "input_schema": {"type": "object", "properties": {}},
            "output_schema": {"type": "object", "properties": {}},
            "derived_fields": 42,
        }
        result = InterfaceSchemaDefinition.model_validate(data)
        assert result.derived_fields == {}
        assert get_derived_fields_degradation_count() == 1

    def test_derived_fields_long_string_preview(self, caplog):
        """Long string should be truncated in log message."""
        long_string = "a" * 100 + " -> task_002.input.results"
        data = {
            "task_id": "task_001",
            "interface_name": "test_interface",
            "description": "Test interface",
            "input_schema": {"type": "object", "properties": {}},
            "output_schema": {"type": "object", "properties": {}},
            "derived_fields": long_string,
        }
        result = InterfaceSchemaDefinition.model_validate(data)
        assert result.derived_fields == {}
        # Check that the preview is truncated (first 50 chars + "...")
        assert "a" * 50 in caplog.text
        assert long_string not in caplog.text

    def test_multiple_degradations_increment_counter(self):
        """Multiple degradations should increment counter correctly."""
        base_data = {
            "task_id": "task_001",
            "interface_name": "test_interface",
            "description": "Test interface",
            "input_schema": {"type": "object", "properties": {}},
            "output_schema": {"type": "object", "properties": {}},
        }

        # First degradation
        data1 = {**base_data, "derived_fields": "string1"}
        InterfaceSchemaDefinition.model_validate(data1)
        assert get_derived_fields_degradation_count() == 1

        # Second degradation
        data2 = {**base_data, "derived_fields": "string2"}
        InterfaceSchemaDefinition.model_validate(data2)
        assert get_derived_fields_degradation_count() == 2

        # Third degradation (list type)
        data3 = {**base_data, "derived_fields": ["list"]}
        InterfaceSchemaDefinition.model_validate(data3)
        assert get_derived_fields_degradation_count() == 3


class TestInterfaceSchemaDefinitionJsonSchema:
    """Tests for input_schema and output_schema JSON parsing."""

    def test_input_schema_dict_passthrough(self):
        """Dict input_schema should pass through unchanged."""
        data = {
            "task_id": "task_001",
            "interface_name": "test_interface",
            "description": "Test",
            "input_schema": {"type": "object", "properties": {"q": {"type": "string"}}},
            "output_schema": {"type": "object"},
        }
        result = InterfaceSchemaDefinition.model_validate(data)
        assert result.input_schema["properties"]["q"]["type"] == "string"

    def test_input_schema_json_string_parsing(self):
        """JSON string input_schema should be parsed."""
        data = {
            "task_id": "task_001",
            "interface_name": "test_interface",
            "description": "Test",
            "input_schema": '{"type": "object", "properties": {}}',
            "output_schema": {"type": "object"},
        }
        result = InterfaceSchemaDefinition.model_validate(data)
        assert result.input_schema["type"] == "object"

    def test_input_schema_invalid_json_raises_error(self):
        """Invalid JSON string should raise ValueError."""
        data = {
            "task_id": "task_001",
            "interface_name": "test_interface",
            "description": "Test",
            "input_schema": "not valid json",
            "output_schema": {"type": "object"},
        }
        with pytest.raises(ValueError, match="Invalid JSON schema string"):
            InterfaceSchemaDefinition.model_validate(data)


class TestInterfaceSchemaResponse:
    """Tests for InterfaceSchemaResponse model."""

    def test_empty_interfaces(self):
        """Empty interfaces list should be valid."""
        data = {"interfaces": []}
        result = InterfaceSchemaResponse.model_validate(data)
        assert result.interfaces == []

    def test_interfaces_with_derived_fields(self):
        """Interfaces with derived_fields should be parsed correctly."""
        data = {
            "interfaces": [
                {
                    "task_id": "task_001",
                    "interface_name": "search_interface",
                    "description": "Search",
                    "input_schema": {"type": "object"},
                    "output_schema": {"type": "object"},
                    "derived_fields": {
                        "summary": {"template": "{count} results", "type": "string"}
                    },
                }
            ]
        }
        result = InterfaceSchemaResponse.model_validate(data)
        assert len(result.interfaces) == 1
        assert "summary" in result.interfaces[0].derived_fields


class TestDegradationCounterFunctions:
    """Tests for degradation counter helper functions."""

    def test_reset_counter(self):
        """reset_derived_fields_degradation_count should reset to zero."""
        # Create some degradations
        data = {
            "task_id": "task_001",
            "interface_name": "test_interface",
            "description": "Test",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "derived_fields": "invalid",
        }
        InterfaceSchemaDefinition.model_validate(data)
        assert get_derived_fields_degradation_count() > 0

        # Reset
        reset_derived_fields_degradation_count()
        assert get_derived_fields_degradation_count() == 0

    def test_get_counter_returns_current_value(self):
        """get_derived_fields_degradation_count should return current value."""
        reset_derived_fields_degradation_count()
        assert get_derived_fields_degradation_count() == 0

        # Add degradation
        data = {
            "task_id": "task_001",
            "interface_name": "test_interface",
            "description": "Test",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "derived_fields": "invalid",
        }
        InterfaceSchemaDefinition.model_validate(data)
        assert get_derived_fields_degradation_count() == 1
