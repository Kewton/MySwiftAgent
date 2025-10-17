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
