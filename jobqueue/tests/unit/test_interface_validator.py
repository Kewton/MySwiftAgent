"""Unit tests for InterfaceValidator service."""

import pytest

from app.services.interface_validator import (
    InterfaceValidationError,
    InterfaceValidator,
)


class TestInterfaceValidator:
    """Test suite for InterfaceValidator."""

    def test_validate_data_success_simple_schema(self) -> None:
        """Test successful validation with simple schema."""
        data = {"name": "Alice", "age": 30}
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name", "age"],
        }
        # Should not raise
        InterfaceValidator.validate_data(data, schema, "test_data")

    def test_validate_data_success_nested_schema(self) -> None:
        """Test successful validation with nested schema."""
        data = {"user": {"name": "Bob", "email": "bob@example.com"}, "status": "active"}
        schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string", "format": "email"},
                    },
                    "required": ["name", "email"],
                },
                "status": {"type": "string"},
            },
            "required": ["user", "status"],
        }
        InterfaceValidator.validate_data(data, schema, "test_data")

    def test_validate_data_success_array_schema(self) -> None:
        """Test successful validation with array schema."""
        data = {"items": [1, 2, 3], "total": 3}
        schema = {
            "type": "object",
            "properties": {
                "items": {"type": "array", "items": {"type": "integer"}},
                "total": {"type": "integer"},
            },
            "required": ["items", "total"],
        }
        InterfaceValidator.validate_data(data, schema, "test_data")

    def test_validate_data_error_type_mismatch(self) -> None:
        """Test validation error on type mismatch."""
        data = {"name": "Alice", "age": "thirty"}  # age should be integer
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name", "age"],
        }
        with pytest.raises(InterfaceValidationError) as exc_info:
            InterfaceValidator.validate_data(data, schema, "input")

        assert "input validation failed" in str(exc_info.value)
        assert len(exc_info.value.errors) > 0
        assert "age" in exc_info.value.errors[0] or "thirty" in exc_info.value.errors[0]

    def test_validate_data_error_missing_required_field(self) -> None:
        """Test validation error on missing required field."""
        data = {"name": "Alice"}  # missing 'age'
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name", "age"],
        }
        with pytest.raises(InterfaceValidationError) as exc_info:
            InterfaceValidator.validate_data(data, schema, "input")

        assert "input validation failed" in str(exc_info.value)
        assert any("age" in error for error in exc_info.value.errors)

    def test_validate_data_error_additional_properties(self) -> None:
        """Test validation error on additional properties when not allowed."""
        data = {"name": "Alice", "age": 30, "extra": "value"}
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name", "age"],
            "additionalProperties": False,
        }
        with pytest.raises(InterfaceValidationError) as exc_info:
            InterfaceValidator.validate_data(data, schema, "input")

        assert "input validation failed" in str(exc_info.value)
        assert any(
            "extra" in error or "Additional" in error for error in exc_info.value.errors
        )

    def test_validate_data_error_array_item_type_mismatch(self) -> None:
        """Test validation error on array item type mismatch."""
        data = {"items": [1, 2, "three"], "total": 3}  # "three" should be integer
        schema = {
            "type": "object",
            "properties": {
                "items": {"type": "array", "items": {"type": "integer"}},
                "total": {"type": "integer"},
            },
            "required": ["items", "total"],
        }
        with pytest.raises(InterfaceValidationError) as exc_info:
            InterfaceValidator.validate_data(data, schema, "input")

        assert "input validation failed" in str(exc_info.value)
        assert len(exc_info.value.errors) > 0

    def test_validate_data_error_nested_field(self) -> None:
        """Test validation error on nested field."""
        data = {"user": {"name": "Bob"}, "status": "active"}  # missing 'email'
        schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "email": {"type": "string"},
                    },
                    "required": ["name", "email"],
                },
                "status": {"type": "string"},
            },
            "required": ["user", "status"],
        }
        with pytest.raises(InterfaceValidationError) as exc_info:
            InterfaceValidator.validate_data(data, schema, "input")

        assert "input validation failed" in str(exc_info.value).lower()
        # Missing required field validation should fail

    def test_validate_data_multiple_errors(self) -> None:
        """Test validation with multiple errors."""
        data = {"age": "thirty"}  # missing 'name', wrong type for 'age'
        schema = {
            "type": "object",
            "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
            "required": ["name", "age"],
        }
        with pytest.raises(InterfaceValidationError) as exc_info:
            InterfaceValidator.validate_data(data, schema, "input")

        assert "input validation failed" in str(exc_info.value)
        assert len(exc_info.value.errors) >= 2  # At least 2 errors

    def test_validate_input_wrapper(self) -> None:
        """Test validate_input wrapper method."""
        data = {"key": "value"}
        schema = {"type": "object", "properties": {"key": {"type": "string"}}}
        # Should not raise
        InterfaceValidator.validate_input(data, schema)

    def test_validate_output_wrapper(self) -> None:
        """Test validate_output wrapper method."""
        data = {"result": 42}
        schema = {"type": "object", "properties": {"result": {"type": "integer"}}}
        # Should not raise
        InterfaceValidator.validate_output(data, schema)

    def test_validate_input_wrapper_error(self) -> None:
        """Test validate_input wrapper with error."""
        data = {"key": 123}  # should be string
        schema = {"type": "object", "properties": {"key": {"type": "string"}}}
        with pytest.raises(InterfaceValidationError) as exc_info:
            InterfaceValidator.validate_input(data, schema)
        assert "input validation failed" in str(exc_info.value).lower()

    def test_validate_output_wrapper_error(self) -> None:
        """Test validate_output wrapper with error."""
        data = {"result": "wrong"}  # should be integer
        schema = {"type": "object", "properties": {"result": {"type": "integer"}}}
        with pytest.raises(InterfaceValidationError) as exc_info:
            InterfaceValidator.validate_output(data, schema)
        assert "output validation failed" in str(exc_info.value).lower()

    def test_validate_data_enum_constraint(self) -> None:
        """Test validation with enum constraint."""
        data = {"status": "active"}
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "inactive", "pending"]}
            },
            "required": ["status"],
        }
        InterfaceValidator.validate_data(data, schema, "test")

    def test_validate_data_enum_constraint_error(self) -> None:
        """Test validation error with invalid enum value."""
        data = {"status": "unknown"}
        schema = {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["active", "inactive", "pending"]}
            },
            "required": ["status"],
        }
        with pytest.raises(InterfaceValidationError) as exc_info:
            InterfaceValidator.validate_data(data, schema, "test")
        assert "test validation failed" in str(exc_info.value)

    def test_validate_data_min_max_constraints(self) -> None:
        """Test validation with min/max constraints."""
        data = {"age": 25}
        schema = {
            "type": "object",
            "properties": {"age": {"type": "integer", "minimum": 0, "maximum": 120}},
            "required": ["age"],
        }
        InterfaceValidator.validate_data(data, schema, "test")

    def test_validate_data_min_constraint_error(self) -> None:
        """Test validation error with minimum constraint."""
        data = {"age": -5}
        schema = {
            "type": "object",
            "properties": {"age": {"type": "integer", "minimum": 0}},
            "required": ["age"],
        }
        with pytest.raises(InterfaceValidationError) as exc_info:
            InterfaceValidator.validate_data(data, schema, "test")
        assert "test validation failed" in str(exc_info.value)

    # New tests for Phase 1.1 implementation
    def test_validate_json_schema_v7_success(self) -> None:
        """Test successful JSON Schema V7 validation."""
        valid_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer", "minimum": 0},
            },
            "required": ["name"],
        }
        # Should not raise
        InterfaceValidator.validate_json_schema_v7(valid_schema)

    def test_validate_json_schema_v7_invalid_type(self) -> None:
        """Test JSON Schema V7 validation with invalid type."""
        invalid_schema = {
            "type": "invalid_type",  # Not a valid JSON Schema type
            "properties": {"name": {"type": "string"}},
        }
        with pytest.raises(InterfaceValidationError) as exc_info:
            InterfaceValidator.validate_json_schema_v7(invalid_schema)
        assert "Invalid JSON Schema V7" in str(exc_info.value)

    def test_validate_json_schema_v7_invalid_format(self) -> None:
        """Test JSON Schema V7 validation with malformed schema."""
        invalid_schema = {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "minLength": "not_a_number",  # Should be integer
                }
            },
        }
        with pytest.raises(InterfaceValidationError) as exc_info:
            InterfaceValidator.validate_json_schema_v7(invalid_schema)
        assert "Invalid JSON Schema V7" in str(exc_info.value)

    def test_check_output_contains_input_properties_success(self) -> None:
        """Test successful compatibility check (考慮①)."""
        output_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "address": {"type": "string"},  # Extra property is OK
            },
        }
        input_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name"],
        }

        is_compatible, missing = (
            InterfaceValidator.check_output_contains_input_properties(
                output_schema, input_schema
            )
        )

        assert is_compatible is True
        assert len(missing) == 0

    def test_check_output_contains_input_properties_missing_required(self) -> None:
        """Test compatibility check fails when required property is missing."""
        output_schema = {
            "type": "object",
            "properties": {
                "age": {"type": "integer"},
            },
        }
        input_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
            },
            "required": ["name"],  # 'name' is required but not in output
        }

        is_compatible, missing = (
            InterfaceValidator.check_output_contains_input_properties(
                output_schema, input_schema
            )
        )

        assert is_compatible is False
        assert len(missing) > 0
        assert any("name" in msg for msg in missing)

    def test_check_output_contains_input_properties_type_mismatch(self) -> None:
        """Test compatibility check fails on type mismatch."""
        output_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "string"},  # Wrong type
            },
        }
        input_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},  # Expects integer
            },
            "required": ["age"],
        }

        is_compatible, missing = (
            InterfaceValidator.check_output_contains_input_properties(
                output_schema, input_schema
            )
        )

        assert is_compatible is False
        assert len(missing) > 0
        assert any("age" in msg and "type mismatch" in msg for msg in missing)

    def test_check_output_contains_input_properties_optional_fields_ok(self) -> None:
        """Test compatibility check succeeds when optional fields are missing (考慮①)."""
        output_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
            },
        }
        input_schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},  # Optional (not in required)
            },
            "required": ["name"],
        }

        is_compatible, missing = (
            InterfaceValidator.check_output_contains_input_properties(
                output_schema, input_schema
            )
        )

        # Should be compatible because 'age' is not required
        assert is_compatible is True
        assert len(missing) == 0

    def test_check_output_contains_input_properties_array_types(self) -> None:
        """Test compatibility check with array type definitions."""
        output_schema = {
            "type": "object",
            "properties": {
                "value": {"type": ["string", "integer"]},  # Union type
            },
        }
        input_schema = {
            "type": "object",
            "properties": {
                "value": {"type": "string"},
            },
            "required": ["value"],
        }

        is_compatible, missing = (
            InterfaceValidator.check_output_contains_input_properties(
                output_schema, input_schema
            )
        )

        # Output accepts string or integer, input expects string -> compatible
        assert is_compatible is True
        assert len(missing) == 0
