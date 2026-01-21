"""Unit tests for Issue #387: Schema conversion logic (DEPRECATED).

DEPRECATED: These tests have been migrated to
    tests/unit/test_clients/test_schema_converter.py

This file is kept for backward compatibility but delegates to the new
centralized schema converter module.

Issue #388: Schema conversion logic has been extracted to
    aiagent/clients/interfaces/schema_converter.py
"""

from aiagent.clients.interfaces.schema_converter import json_schema_to_simple_mapping


class TestSchemaToSimpleMapping:
    """Tests for json_schema_to_simple_mapping function.

    DEPRECATED: See tests/unit/test_clients/test_schema_converter.py
    """

    def test_convert_full_json_schema_to_simple_mapping(self) -> None:
        """Full JSON Schema should be converted to simple mapping."""
        full_schema = {
            "type": "object",
            "properties": {
                "email": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["email", "subject"],
        }

        result = json_schema_to_simple_mapping(full_schema)

        assert result == {
            "email": "string",
            "subject": "string",
            "body": "string",
        }

    def test_already_simple_mapping_returns_as_is(self) -> None:
        """Already simple mapping should be returned unchanged."""
        simple_schema = {
            "email": "string",
            "subject": "string",
        }

        result = json_schema_to_simple_mapping(simple_schema)

        assert result == simple_schema

    def test_empty_schema_returns_empty_dict(self) -> None:
        """Empty schema should return empty dict."""
        assert json_schema_to_simple_mapping({}) == {}


class TestSchemaConversionIntegration:
    """Integration tests for schema conversion in workflow generation context."""

    def test_real_interface_definition_conversion(self) -> None:
        """Test conversion of actual InterfaceDefinition format."""
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer import (
            InterfaceDefinition,
        )

        interface = InterfaceDefinition(
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["to", "subject", "body"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string"},
                    "success": {"type": "boolean"},
                },
            },
            description="Send email interface",
        )

        input_mapping = json_schema_to_simple_mapping(interface.input_schema)
        output_mapping = json_schema_to_simple_mapping(interface.output_schema)

        assert input_mapping == {
            "to": "string",
            "subject": "string",
            "body": "string",
        }
        assert output_mapping == {
            "message_id": "string",
            "success": "boolean",
        }
