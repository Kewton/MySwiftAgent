"""Unit tests for schema_comparator.py.

Issue #358: Tests for comparing schemas and validating field references.

Test cases:
1. Field exists in schema
2. Field missing from schema
3. Nested field validation
4. Schema comparison results
"""


class TestCompareSchemas:
    """Test compare_schemas() function."""

    def test_field_exists_in_flat_schema(self) -> None:
        """Field exists in flat schema."""
        from aiagent.langgraph.jobGeneratorV2.validators.schema_comparator import (
            compare_schemas,
        )

        schema = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
                "recipient_email": {"type": "string"},
            },
        }
        required_fields = {"user_input", "recipient_email"}

        result = compare_schemas(required_fields, schema)

        assert result.is_valid
        assert len(result.missing_fields) == 0

    def test_field_missing_from_schema(self) -> None:
        """Field missing from schema returns error."""
        from aiagent.langgraph.jobGeneratorV2.validators.schema_comparator import (
            compare_schemas,
        )

        schema = {
            "type": "object",
            "properties": {
                "user_input": {"type": "string"},
            },
        }
        required_fields = {"user_input", "missing_field"}

        result = compare_schemas(required_fields, schema)

        assert not result.is_valid
        assert "missing_field" in result.missing_fields

    def test_nested_field_validation(self) -> None:
        """Nested field paths validated correctly."""
        from aiagent.langgraph.jobGeneratorV2.validators.schema_comparator import (
            compare_schemas,
        )

        schema = {
            "type": "object",
            "properties": {
                "config": {
                    "type": "object",
                    "properties": {
                        "api_key": {"type": "string"},
                    },
                },
            },
        }
        required_fields = {"config.api_key"}

        result = compare_schemas(required_fields, schema)

        assert result.is_valid

    def test_nested_field_missing(self) -> None:
        """Missing nested field detected."""
        from aiagent.langgraph.jobGeneratorV2.validators.schema_comparator import (
            compare_schemas,
        )

        schema = {
            "type": "object",
            "properties": {
                "config": {
                    "type": "object",
                    "properties": {
                        "timeout": {"type": "integer"},
                    },
                },
            },
        }
        required_fields = {"config.api_key"}

        result = compare_schemas(required_fields, schema)

        assert not result.is_valid
        assert "config.api_key" in result.missing_fields

    def test_empty_schema_with_fields(self) -> None:
        """Empty schema with required fields returns all missing."""
        from aiagent.langgraph.jobGeneratorV2.validators.schema_comparator import (
            compare_schemas,
        )

        schema: dict = {}
        required_fields = {"field1", "field2"}

        result = compare_schemas(required_fields, schema)

        assert not result.is_valid
        assert "field1" in result.missing_fields
        assert "field2" in result.missing_fields

    def test_empty_required_fields(self) -> None:
        """Empty required fields with any schema is valid."""
        from aiagent.langgraph.jobGeneratorV2.validators.schema_comparator import (
            compare_schemas,
        )

        schema = {
            "type": "object",
            "properties": {
                "field": {"type": "string"},
            },
        }
        required_fields: set[str] = set()

        result = compare_schemas(required_fields, schema)

        assert result.is_valid


class TestSchemaComparisonResult:
    """Test SchemaComparisonResult dataclass."""

    def test_result_contains_matched_fields(self) -> None:
        """Result contains list of matched fields."""
        from aiagent.langgraph.jobGeneratorV2.validators.schema_comparator import (
            compare_schemas,
        )

        schema = {
            "type": "object",
            "properties": {
                "field1": {"type": "string"},
                "field2": {"type": "string"},
            },
        }
        required_fields = {"field1", "field2"}

        result = compare_schemas(required_fields, schema)

        assert "field1" in result.matched_fields
        assert "field2" in result.matched_fields

    def test_to_validation_errors(self) -> None:
        """Convert result to ValidationError list."""
        from aiagent.langgraph.jobGeneratorV2.validators.schema_comparator import (
            compare_schemas,
        )

        schema = {
            "type": "object",
            "properties": {
                "field1": {"type": "string"},
            },
        }
        required_fields = {"field1", "missing_field"}

        result = compare_schemas(required_fields, schema)
        errors = result.to_validation_errors("input_schema")

        assert len(errors) == 1
        assert errors[0].location == "input_schema"
        assert "missing_field" in errors[0].message


class TestFieldInSchema:
    """Test field_in_schema() helper function."""

    def test_simple_field_check(self) -> None:
        """Check if simple field exists in schema."""
        from aiagent.langgraph.jobGeneratorV2.validators.schema_comparator import (
            field_in_schema,
        )

        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
        }

        assert field_in_schema("name", schema)
        assert not field_in_schema("age", schema)

    def test_nested_field_check(self) -> None:
        """Check nested field path."""
        from aiagent.langgraph.jobGeneratorV2.validators.schema_comparator import (
            field_in_schema,
        )

        schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "profile": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                            },
                        },
                    },
                },
            },
        }

        assert field_in_schema("user.profile.name", schema)
        assert not field_in_schema("user.profile.age", schema)
