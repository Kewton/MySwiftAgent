"""Unit tests for derived_fields feature (Issue #337).

Tests for DerivedFieldDefinition schema and InterfaceSchemaDefinition extension.
"""

import pytest
from pydantic import ValidationError

from aiagent.langgraph.jobTaskGeneratorAgents.prompts.interface_schema import (
    DerivedFieldDefinition,
    InterfaceSchemaDefinition,
)


class TestDerivedFieldDefinition:
    """Tests for DerivedFieldDefinition Pydantic model."""

    def test_basic_creation(self) -> None:
        """Test basic DerivedFieldDefinition creation with required fields."""
        field = DerivedFieldDefinition(
            template="Hello {name}",
        )
        assert field.template == "Hello {name}"
        assert field.type == "string"  # default
        assert field.description is None
        assert field.source_mapping is None

    def test_full_creation(self) -> None:
        """Test DerivedFieldDefinition with all fields."""
        field = DerivedFieldDefinition(
            template="Result: {summary} - {query}",
            type="string",
            description="Email subject line",
            source_mapping={"query": "source.user_input.query"},
        )
        assert field.template == "Result: {summary} - {query}"
        assert field.type == "string"
        assert field.description == "Email subject line"
        assert field.source_mapping == {"query": "source.user_input.query"}

    def test_missing_template_raises_error(self) -> None:
        """Test that missing template field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            DerivedFieldDefinition()  # type: ignore[call-arg]
        assert "template" in str(exc_info.value)

    def test_extra_fields_forbidden(self) -> None:
        """Test that extra fields are forbidden (extra='forbid')."""
        with pytest.raises(ValidationError) as exc_info:
            DerivedFieldDefinition(
                template="Test",
                unknown_field="value",  # type: ignore[call-arg]
            )
        assert "extra" in str(exc_info.value).lower()

    def test_source_mapping_with_multiple_mappings(self) -> None:
        """Test source_mapping with multiple variable mappings."""
        field = DerivedFieldDefinition(
            template="File: {date}_{subject}.mp3",
            source_mapping={
                "date": "source.user_input.date",
                "subject": "extract_body.subject",
            },
        )
        assert len(field.source_mapping) == 2
        assert field.source_mapping["date"] == "source.user_input.date"
        assert field.source_mapping["subject"] == "extract_body.subject"

    def test_type_field_alternatives(self) -> None:
        """Test that type field accepts different values."""
        field_string = DerivedFieldDefinition(template="Test", type="string")
        field_int = DerivedFieldDefinition(template="Test", type="integer")
        field_bool = DerivedFieldDefinition(template="Test", type="boolean")

        assert field_string.type == "string"
        assert field_int.type == "integer"
        assert field_bool.type == "boolean"


class TestInterfaceSchemaDefinitionWithDerivedFields:
    """Tests for InterfaceSchemaDefinition with derived_fields extension."""

    def test_without_derived_fields(self) -> None:
        """Test InterfaceSchemaDefinition without derived_fields (backward compat)."""
        interface = InterfaceSchemaDefinition(
            task_id="task_001",
            interface_name="gmail_search_interface",
            description="Gmail search interface",
            input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
            output_schema={
                "type": "object",
                "properties": {"results": {"type": "array"}},
            },
        )
        assert interface.task_id == "task_001"
        assert interface.derived_fields == {}

    def test_with_derived_fields(self) -> None:
        """Test InterfaceSchemaDefinition with derived_fields."""
        interface = InterfaceSchemaDefinition(
            task_id="task_002",
            interface_name="summarize_interface",
            description="Summarization interface",
            input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
            output_schema={
                "type": "object",
                "properties": {"summary_text": {"type": "string"}},
            },
            derived_fields={
                "email_subject": DerivedFieldDefinition(
                    template="Summary: {query}",
                    description="Email subject",
                ),
                "email_body": DerivedFieldDefinition(
                    template="{summary_text}\n\nKey points: {key_points}",
                ),
            },
        )
        assert len(interface.derived_fields) == 2
        assert "email_subject" in interface.derived_fields
        assert "email_body" in interface.derived_fields
        assert interface.derived_fields["email_subject"].template == "Summary: {query}"

    def test_derived_fields_serialization(self) -> None:
        """Test that derived_fields can be serialized to dict."""
        interface = InterfaceSchemaDefinition(
            task_id="task_003",
            interface_name="test_interface",
            description="Test interface",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            derived_fields={
                "formatted_result": DerivedFieldDefinition(
                    template="Result: {data}",
                    type="string",
                    source_mapping={"data": "prev_task.output.data"},
                ),
            },
        )
        data = interface.model_dump()
        assert "derived_fields" in data
        assert "formatted_result" in data["derived_fields"]
        assert data["derived_fields"]["formatted_result"]["template"] == "Result: {data}"
        assert data["derived_fields"]["formatted_result"]["source_mapping"] == {
            "data": "prev_task.output.data"
        }

    def test_derived_fields_from_dict(self) -> None:
        """Test InterfaceSchemaDefinition creation from dict with derived_fields."""
        data = {
            "task_id": "task_004",
            "interface_name": "from_dict_interface",
            "description": "Interface from dict",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "derived_fields": {
                "slack_message": {
                    "template": "Update: {status}",
                    "type": "string",
                    "description": "Slack notification message",
                }
            },
        }
        interface = InterfaceSchemaDefinition.model_validate(data)
        assert "slack_message" in interface.derived_fields
        assert interface.derived_fields["slack_message"].template == "Update: {status}"

    def test_empty_derived_fields_dict(self) -> None:
        """Test that empty derived_fields dict is valid."""
        interface = InterfaceSchemaDefinition(
            task_id="task_005",
            interface_name="empty_derived",
            description="No derived fields",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            derived_fields={},
        )
        assert interface.derived_fields == {}
