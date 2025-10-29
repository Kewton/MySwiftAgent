"""Unit tests for Unicode property escapes regex support in interface_validator."""

import pytest

from app.services.interface_validator import (
    InterfaceValidationError,
    InterfaceValidator,
)


class TestUnicodePropertyEscapes:
    """Test Unicode property escapes in regex patterns."""

    def test_unicode_letter_pattern_is_valid(self):
        """Test that \\p{L} pattern is recognized as valid."""
        schema = {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "pattern": r"^[\p{L}\p{N}\s\-\(\)&\\.、。]+$",
                }
            },
            "required": ["name"],
        }

        # Should not raise error
        InterfaceValidator.validate_json_schema_v7(schema)

    def test_unicode_number_pattern_is_valid(self):
        """Test that \\p{N} pattern is recognized as valid."""
        schema = {
            "type": "object",
            "properties": {"code": {"type": "string", "pattern": r"^\p{N}+$"}},
        }

        # Should not raise error
        InterfaceValidator.validate_json_schema_v7(schema)

    def test_invalid_regex_pattern_raises_error(self):
        """Test that invalid regex pattern raises validation error."""
        schema = {
            "type": "object",
            "properties": {
                "field": {
                    "type": "string",
                    "pattern": r"[unclosed",  # Invalid: unclosed bracket
                }
            },
        }

        with pytest.raises(InterfaceValidationError) as exc_info:
            InterfaceValidator.validate_json_schema_v7(schema)

        assert "Invalid regex pattern in schema" in str(exc_info.value)

    @pytest.mark.skip(
        reason="Python's standard 're' module does not support Unicode property escapes (\\p{L}). "
        "jsonschema uses 're' internally for pattern validation, causing failures. "
        "This requires using the 'regex' library with a custom validator implementation. "
        "Tracked in issue #111."
    )
    def test_data_validation_with_unicode_pattern(self):
        """Test that data validation works with Unicode property escapes."""
        schema = {
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "pattern": r"^[\p{L}\p{N}\s\-\(\)&\\.、。]+$",
                }
            },
            "required": ["company_name"],
        }

        # Valid data
        valid_data = {"company_name": "株式会社ABC"}
        InterfaceValidator.validate_data(valid_data, schema, "input")

        # Invalid data (empty string - pattern requires at least one character)
        invalid_data = {"company_name": ""}
        with pytest.raises(InterfaceValidationError):
            InterfaceValidator.validate_data(invalid_data, schema, "input")

    @pytest.mark.skip(
        reason="Python's standard 're' module does not support Unicode property escapes (\\p{L}, \\p{N}, etc.). "
        "jsonschema uses 're' internally for pattern validation, causing failures. "
        "This requires using the 'regex' library with a custom validator implementation. "
        "Tracked in issue #111."
    )
    def test_multiple_unicode_properties(self):
        """Test pattern with multiple Unicode property types."""
        schema = {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "pattern": r"^[\p{L}\p{N}\p{P}\p{Z}]+$",  # Letters, Numbers, Punctuation, Spaces
                }
            },
        }

        InterfaceValidator.validate_json_schema_v7(schema)

        # Valid data
        valid_data = {"text": "Hello 世界！123"}
        InterfaceValidator.validate_data(valid_data, schema, "input")
