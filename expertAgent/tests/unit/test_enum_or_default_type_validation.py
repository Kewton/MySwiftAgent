"""Unit tests for _enum_or_default type validation.

Issue #340: Test type validation for default values in array fields.
This prevents object arrays from being used as string array defaults,
which causes [object Object] conversion issues in stringTemplateAgent.
"""

from aiagent.langgraph.workflowGeneratorAgents.nodes.sample_input_generator import (
    _enum_or_default,
)


class TestEnumOrDefaultTypeValidation:
    """Test _enum_or_default function with type validation for arrays."""

    # ========== String Array Tests ==========

    def test_valid_string_array_default(self) -> None:
        """Valid string array default should be returned as-is."""
        schema = {
            "type": "array",
            "items": {"type": "string"},
            "default": ["item1", "item2", "item3"],
        }
        result = _enum_or_default(schema)
        assert result == ["item1", "item2", "item3"]

    def test_invalid_object_array_default_for_string_type(self) -> None:
        """Object array default for string type should return None.

        Issue #340: This is the critical case that causes [object Object].
        """
        schema = {
            "type": "array",
            "items": {"type": "string"},
            "default": [{"type": "string", "description": "item description"}],
        }
        result = _enum_or_default(schema)
        assert result is None

    def test_mixed_string_and_object_array_default(self) -> None:
        """Mixed array with objects should return None for string type."""
        schema = {
            "type": "array",
            "items": {"type": "string"},
            "default": ["valid_string", {"invalid": "object"}],
        }
        result = _enum_or_default(schema)
        assert result is None

    def test_empty_string_array_default(self) -> None:
        """Empty array default should be returned as-is (all elements pass validation)."""
        schema = {
            "type": "array",
            "items": {"type": "string"},
            "default": [],
        }
        result = _enum_or_default(schema)
        assert result == []

    # ========== Number Array Tests ==========

    def test_valid_number_array_default(self) -> None:
        """Valid number array default should be returned as-is."""
        schema = {
            "type": "array",
            "items": {"type": "number"},
            "default": [1.5, 2.5, 3.5],
        }
        result = _enum_or_default(schema)
        assert result == [1.5, 2.5, 3.5]

    def test_valid_integer_array_default(self) -> None:
        """Valid integer array default should be returned as-is."""
        schema = {
            "type": "array",
            "items": {"type": "integer"},
            "default": [1, 2, 3],
        }
        result = _enum_or_default(schema)
        assert result == [1, 2, 3]

    def test_invalid_object_array_default_for_number_type(self) -> None:
        """Object array default for number type should return None."""
        schema = {
            "type": "array",
            "items": {"type": "number"},
            "default": [{"value": 1.5}],
        }
        result = _enum_or_default(schema)
        assert result is None

    def test_invalid_string_array_default_for_integer_type(self) -> None:
        """String array default for integer type should return None."""
        schema = {
            "type": "array",
            "items": {"type": "integer"},
            "default": ["1", "2", "3"],
        }
        result = _enum_or_default(schema)
        assert result is None

    # ========== Boolean Array Tests (MF-2) ==========

    def test_valid_boolean_array_default(self) -> None:
        """MF-2: Valid boolean array default should be returned as-is."""
        schema = {
            "type": "array",
            "items": {"type": "boolean"},
            "default": [True, False, True],
        }
        result = _enum_or_default(schema)
        assert result == [True, False, True]

    def test_invalid_string_array_default_for_boolean_type(self) -> None:
        """MF-2: String array default for boolean type should return None."""
        schema = {
            "type": "array",
            "items": {"type": "boolean"},
            "default": ["true", "false"],
        }
        result = _enum_or_default(schema)
        assert result is None

    def test_invalid_object_array_default_for_boolean_type(self) -> None:
        """MF-2: Object array default for boolean type should return None."""
        schema = {
            "type": "array",
            "items": {"type": "boolean"},
            "default": [{"value": True}],
        }
        result = _enum_or_default(schema)
        assert result is None

    def test_mixed_boolean_and_string_array_default(self) -> None:
        """MF-2: Mixed boolean and string array should return None."""
        schema = {
            "type": "array",
            "items": {"type": "boolean"},
            "default": [True, "false"],
        }
        result = _enum_or_default(schema)
        assert result is None

    # ========== Non-Array Tests (Backward Compatibility) ==========

    def test_non_array_default_unchanged(self) -> None:
        """Non-array default values should be returned as-is."""
        schema = {
            "type": "string",
            "default": "default_value",
        }
        result = _enum_or_default(schema)
        assert result == "default_value"

    def test_object_default_unchanged(self) -> None:
        """Object default values should be returned as-is."""
        schema = {
            "type": "object",
            "default": {"key": "value"},
        }
        result = _enum_or_default(schema)
        assert result == {"key": "value"}

    def test_enum_takes_priority_over_default(self) -> None:
        """Enum should take priority over default."""
        schema = {
            "type": "array",
            "items": {"type": "string"},
            "enum": [["enum_value"]],
            "default": [{"type": "string"}],  # Invalid but should not be checked
        }
        result = _enum_or_default(schema)
        assert result == ["enum_value"]

    def test_const_takes_priority_over_enum_and_default(self) -> None:
        """Const should take priority over enum and default."""
        schema = {
            "type": "array",
            "items": {"type": "string"},
            "const": ["const_value"],
            "enum": [["enum_value"]],
            "default": [{"type": "string"}],
        }
        result = _enum_or_default(schema)
        assert result == ["const_value"]

    def test_examples_takes_priority_over_default(self) -> None:
        """Examples should take priority over default."""
        schema = {
            "type": "array",
            "items": {"type": "string"},
            "examples": [["example_value"]],
            "default": [{"type": "string"}],  # Invalid but should not be checked
        }
        result = _enum_or_default(schema)
        assert result == ["example_value"]

    # ========== Edge Cases ==========

    def test_no_items_type_allows_any_default(self) -> None:
        """Array without items.type should allow any default."""
        schema = {
            "type": "array",
            "default": [{"any": "object"}],
        }
        result = _enum_or_default(schema)
        # Without items.type, we cannot validate, so allow as-is
        # But we should log a warning if objects are present
        assert result == [{"any": "object"}]

    def test_object_items_type_allows_object_default(self) -> None:
        """Array with items.type='object' should allow object default."""
        schema = {
            "type": "array",
            "items": {"type": "object"},
            "default": [{"key": "value"}],
        }
        result = _enum_or_default(schema)
        assert result == [{"key": "value"}]
