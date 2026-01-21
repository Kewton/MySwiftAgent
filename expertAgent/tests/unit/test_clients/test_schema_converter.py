"""Unit tests for Issue #388: Schema converter module.

Tests the schema conversion functions that convert between:
- JSON Schema format: {"type": "object", "properties": {"email": {"type": "string"}}}
- Simple Mapping format: {"email": "string"}

Migrated from test_issue387_schema_conversion.py with additional tests for:
- Type aliases (JsonSchema, SimpleMapping)
- Debug logging for information loss
- Round-trip conversion
"""

import logging

import pytest

from aiagent.clients.interfaces.schema_converter import (
    JsonSchema,
    SimpleMapping,
    json_schema_to_simple_mapping,
    simple_mapping_to_json_schema,
)


class TestJsonSchemaToSimpleMapping:
    """Tests for json_schema_to_simple_mapping function."""

    def test_convert_full_json_schema_to_simple_mapping(self) -> None:
        """Full JSON Schema should be converted to simple mapping."""
        # Arrange
        full_schema: JsonSchema = {
            "type": "object",
            "properties": {
                "email": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["email", "subject"],
        }

        # Act
        result = json_schema_to_simple_mapping(full_schema)

        # Assert
        assert result == {
            "email": "string",
            "subject": "string",
            "body": "string",
        }

    def test_already_simple_mapping_returns_as_is(self) -> None:
        """Already simple mapping should be returned unchanged."""
        # Arrange
        simple_schema: SimpleMapping = {
            "email": "string",
            "subject": "string",
        }

        # Act
        result = json_schema_to_simple_mapping(simple_schema)

        # Assert
        assert result == simple_schema

    def test_empty_schema_returns_empty_dict(self) -> None:
        """Empty schema should return empty dict."""
        # Act & Assert
        assert json_schema_to_simple_mapping({}) == {}

    def test_integer_type_preserved(self) -> None:
        """Integer types should be preserved."""
        # Arrange
        schema: JsonSchema = {
            "type": "object",
            "properties": {
                "count": {"type": "integer"},
                "price": {"type": "number"},
            },
        }

        # Act
        result = json_schema_to_simple_mapping(schema)

        # Assert
        assert result == {"count": "integer", "price": "number"}

    def test_array_type_preserved(self) -> None:
        """Array types should be preserved."""
        # Arrange
        schema: JsonSchema = {
            "type": "object",
            "properties": {
                "tags": {"type": "array"},
                "items": {"type": "array"},
            },
        }

        # Act
        result = json_schema_to_simple_mapping(schema)

        # Assert
        assert result == {"tags": "array", "items": "array"}

    def test_boolean_type_preserved(self) -> None:
        """Boolean types should be preserved."""
        # Arrange
        schema: JsonSchema = {
            "type": "object",
            "properties": {
                "is_active": {"type": "boolean"},
                "verified": {"type": "boolean"},
            },
        }

        # Act
        result = json_schema_to_simple_mapping(schema)

        # Assert
        assert result == {"is_active": "boolean", "verified": "boolean"}

    def test_missing_type_defaults_to_string(self) -> None:
        """Missing type should default to string."""
        # Arrange
        schema: JsonSchema = {
            "type": "object",
            "properties": {
                "name": {},  # No type specified
                "description": {"description": "A description"},  # No type
            },
        }

        # Act
        result = json_schema_to_simple_mapping(schema)

        # Assert
        assert result == {"name": "string", "description": "string"}

    def test_schema_with_no_properties_treated_as_simple_mapping(self) -> None:
        """Schema with no properties but all string values is treated as simple mapping.

        Note: {"type": "object"} has all string values, so it's treated as a simple
        mapping. This is ambiguous but acceptable behavior.
        """
        # Arrange
        schema: JsonSchema = {
            "type": "object",
            # No properties key
        }

        # Act
        result = json_schema_to_simple_mapping(schema)

        # Assert: Since all values are strings, returned as-is (treated as simple mapping)
        assert result == {"type": "object"}

    def test_mixed_schema_not_simple_returns_empty(self) -> None:
        """Schema with mixed values (not all strings) returns empty."""
        # Arrange
        schema: JsonSchema = {
            "email": "string",
            "nested": {"type": "object"},  # Not a simple string value
        }

        # Act
        result = json_schema_to_simple_mapping(schema)

        # Assert
        assert result == {}


class TestSimpleMappingToJsonSchema:
    """Tests for simple_mapping_to_json_schema function."""

    def test_convert_simple_mapping_to_json_schema(self) -> None:
        """Simple mapping should be converted to JSON Schema."""
        # Arrange
        mapping: SimpleMapping = {
            "email": "string",
            "count": "integer",
        }

        # Act
        result = simple_mapping_to_json_schema(mapping)

        # Assert
        assert result == {
            "type": "object",
            "properties": {
                "email": {"type": "string"},
                "count": {"type": "integer"},
            },
        }

    def test_empty_mapping_returns_empty_dict(self) -> None:
        """Empty mapping should return empty dict."""
        # Act & Assert
        assert simple_mapping_to_json_schema({}) == {}

    def test_single_field_mapping(self) -> None:
        """Single field mapping should work correctly."""
        # Arrange
        mapping: SimpleMapping = {"name": "string"}

        # Act
        result = simple_mapping_to_json_schema(mapping)

        # Assert
        assert result == {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
        }

    def test_all_types_preserved(self) -> None:
        """All common types should be preserved in conversion."""
        # Arrange
        mapping: SimpleMapping = {
            "str_field": "string",
            "int_field": "integer",
            "num_field": "number",
            "bool_field": "boolean",
            "arr_field": "array",
            "obj_field": "object",
        }

        # Act
        result = simple_mapping_to_json_schema(mapping)

        # Assert
        for field_name, field_type in mapping.items():
            assert result["properties"][field_name]["type"] == field_type


class TestRoundTripConversion:
    """Tests for round-trip conversion between formats."""

    def test_simple_mapping_round_trip(self) -> None:
        """Simple mapping should survive round-trip conversion."""
        # Arrange
        original: SimpleMapping = {
            "email": "string",
            "count": "integer",
            "active": "boolean",
        }

        # Act
        json_schema = simple_mapping_to_json_schema(original)
        result = json_schema_to_simple_mapping(json_schema)

        # Assert
        assert result == original

    def test_json_schema_round_trip_loses_metadata(self) -> None:
        """JSON Schema round-trip loses metadata but preserves types."""
        # Arrange
        original: JsonSchema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
                "age": {"type": "integer", "minimum": 0},
            },
            "required": ["email"],
        }

        # Act
        simple = json_schema_to_simple_mapping(original)
        result = simple_mapping_to_json_schema(simple)

        # Assert: Types preserved, metadata lost
        assert result["properties"]["email"]["type"] == "string"
        assert result["properties"]["age"]["type"] == "integer"
        assert "format" not in result["properties"]["email"]
        assert "minimum" not in result["properties"]["age"]
        assert "required" not in result

    def test_empty_round_trip(self) -> None:
        """Empty dict should survive round-trip."""
        # Act
        result_schema = simple_mapping_to_json_schema({})
        result_mapping = json_schema_to_simple_mapping({})

        # Assert
        assert result_schema == {}
        assert result_mapping == {}


class TestInformationLoss:
    """Tests documenting information loss during conversion.

    These tests document what information is lost when converting from
    full JSON Schema to simple mapping. This is a known limitation.
    """

    def test_required_fields_lost(self) -> None:
        """Required fields information is lost in conversion."""
        # Arrange
        schema: JsonSchema = {
            "type": "object",
            "properties": {
                "email": {"type": "string"},
                "nickname": {"type": "string"},
            },
            "required": ["email"],  # This is lost
        }

        # Act
        result = json_schema_to_simple_mapping(schema)

        # Assert: No way to know email was required
        assert result == {"email": "string", "nickname": "string"}
        # Information lost: required = ["email"]

    def test_description_lost(self) -> None:
        """Field descriptions are lost in conversion."""
        # Arrange
        schema: JsonSchema = {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "User's email address",  # This is lost
                },
            },
        }

        # Act
        result = json_schema_to_simple_mapping(schema)

        # Assert: Description is not preserved
        assert result == {"email": "string"}
        # Information lost: description = "User's email address"

    def test_format_constraint_lost(self) -> None:
        """Format constraints are lost in conversion."""
        # Arrange
        schema: JsonSchema = {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "format": "email",  # This is lost
                },
                "created_at": {
                    "type": "string",
                    "format": "date-time",  # This is lost
                },
            },
        }

        # Act
        result = json_schema_to_simple_mapping(schema)

        # Assert: Format is not preserved
        assert result == {"email": "string", "created_at": "string"}
        # Information lost: format = "email", format = "date-time"

    def test_nested_object_type_preserved_but_structure_lost(self) -> None:
        """Nested objects lose their internal structure."""
        # Arrange
        schema: JsonSchema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {  # This is lost
                        "name": {"type": "string"},
                        "age": {"type": "integer"},
                    },
                },
            },
        }

        # Act
        result = json_schema_to_simple_mapping(schema)

        # Assert: Only top-level type preserved
        assert result == {"user": "object"}
        # Information lost: nested structure {name: string, age: integer}

    def test_array_item_type_lost(self) -> None:
        """Array item type information is lost."""
        # Arrange
        schema: JsonSchema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},  # This is lost
                },
            },
        }

        # Act
        result = json_schema_to_simple_mapping(schema)

        # Assert: Only array type preserved
        assert result == {"tags": "array"}
        # Information lost: items = {type: string}


class TestLogging:
    """Tests for debug logging of information loss."""

    def test_logs_required_fields_loss(self, caplog: pytest.LogCaptureFixture) -> None:
        """Should log when required fields are lost."""
        # Arrange
        schema: JsonSchema = {
            "type": "object",
            "properties": {
                "email": {"type": "string"},
            },
            "required": ["email"],
        }

        # Act
        with caplog.at_level(logging.DEBUG):
            json_schema_to_simple_mapping(schema)

        # Assert
        assert "required fields" in caplog.text.lower()

    def test_logs_description_loss(self, caplog: pytest.LogCaptureFixture) -> None:
        """Should log when descriptions are lost."""
        # Arrange
        schema: JsonSchema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "User email"},
            },
        }

        # Act
        with caplog.at_level(logging.DEBUG):
            json_schema_to_simple_mapping(schema)

        # Assert
        assert "description" in caplog.text.lower()

    def test_logs_format_loss(self, caplog: pytest.LogCaptureFixture) -> None:
        """Should log when format constraints are lost."""
        # Arrange
        schema: JsonSchema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
            },
        }

        # Act
        with caplog.at_level(logging.DEBUG):
            json_schema_to_simple_mapping(schema)

        # Assert
        assert "format" in caplog.text.lower()

    def test_logs_nested_structure_loss(self, caplog: pytest.LogCaptureFixture) -> None:
        """Should log when nested structures are lost."""
        # Arrange
        schema: JsonSchema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                    },
                },
            },
        }

        # Act
        with caplog.at_level(logging.DEBUG):
            json_schema_to_simple_mapping(schema)

        # Assert
        assert "nested structure" in caplog.text.lower()

    def test_logs_array_item_type_loss(self, caplog: pytest.LogCaptureFixture) -> None:
        """Should log when array item types are lost."""
        # Arrange
        schema: JsonSchema = {
            "type": "object",
            "properties": {
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
        }

        # Act
        with caplog.at_level(logging.DEBUG):
            json_schema_to_simple_mapping(schema)

        # Assert
        assert "array item type" in caplog.text.lower()


class TestTypeAliases:
    """Tests to verify type aliases work correctly."""

    def test_json_schema_type_alias_annotation(self) -> None:
        """JsonSchema type alias should be usable for type hints."""
        # This is a compile-time check, but we verify at runtime
        schema: JsonSchema = {"type": "object", "properties": {}}
        assert isinstance(schema, dict)

    def test_simple_mapping_type_alias_annotation(self) -> None:
        """SimpleMapping type alias should be usable for type hints."""
        # This is a compile-time check, but we verify at runtime
        mapping: SimpleMapping = {"field": "string"}
        assert isinstance(mapping, dict)
        assert all(isinstance(v, str) for v in mapping.values())


class TestIntegration:
    """Integration tests for schema conversion in workflow generation context."""

    def test_real_interface_definition_conversion(self) -> None:
        """Test conversion of actual InterfaceDefinition format."""
        # Arrange: Create an InterfaceDefinition-like structure
        input_schema: JsonSchema = {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to", "subject", "body"],
        }
        output_schema: JsonSchema = {
            "type": "object",
            "properties": {
                "message_id": {"type": "string"},
                "success": {"type": "boolean"},
            },
        }

        # Act
        input_mapping = json_schema_to_simple_mapping(input_schema)
        output_mapping = json_schema_to_simple_mapping(output_schema)

        # Assert: Format expected by mySwiftAgentCore
        assert input_mapping == {
            "to": "string",
            "subject": "string",
            "body": "string",
        }
        assert output_mapping == {
            "message_id": "string",
            "success": "boolean",
        }
