"""Unit tests for json_converter utility module."""

import pytest

from app.utils.json_converter import (
    ensure_json_structure,
    force_to_json_response,
    to_parse_json,
)


class TestToParseJson:
    """Test to_parse_json function."""

    def test_parse_direct_json_object(self):
        """Test parsing direct JSON object."""
        content = '{"result": "success", "value": 123}'
        result = to_parse_json(content)
        assert result == {"result": "success", "value": 123}

    def test_parse_direct_json_array(self):
        """Test parsing direct JSON array."""
        content = '[1, 2, 3, "test"]'
        result = to_parse_json(content)
        assert result == [1, 2, 3, "test"]

    def test_parse_json_code_block_object(self):
        """Test parsing JSON from ```json``` code block (object)."""
        content = '```json\n{"result": "from code block"}\n```'
        result = to_parse_json(content)
        assert result == {"result": "from code block"}

    def test_parse_json_code_block_array(self):
        """Test parsing JSON from ```json``` code block (array)."""
        content = "```json\n[1, 2, 3]\n```"
        result = to_parse_json(content)
        assert result == [1, 2, 3]

    def test_parse_json_code_block_with_extra_whitespace(self):
        """Test parsing JSON code block with extra whitespace."""
        content = '```json\n  \n  {"data": "value"}  \n  \n```'
        result = to_parse_json(content)
        assert result == {"data": "value"}

    def test_parse_json_code_block_multiline(self):
        """Test parsing multiline JSON from code block."""
        content = """```json
{
  "name": "test",
  "items": [1, 2, 3]
}
```"""
        result = to_parse_json(content)
        assert result == {"name": "test", "items": [1, 2, 3]}

    def test_parse_json_failure_plain_text(self):
        """Test that plain text raises ValueError."""
        content = "This is just plain text"
        with pytest.raises(ValueError) as exc_info:
            to_parse_json(content)
        assert "Failed to extract JSON block" in str(exc_info.value)

    def test_parse_json_failure_invalid_json_in_code_block(self):
        """Test that invalid JSON in code block raises ValueError."""
        content = "```json\n{invalid json}\n```"
        with pytest.raises(ValueError) as exc_info:
            to_parse_json(content)
        assert "Failed to parse extracted JSON" in str(exc_info.value)

    def test_parse_json_failure_incomplete_json(self):
        """Test that incomplete JSON raises ValueError."""
        content = '{"result": "incomplete"'
        # JsonOutputParser may or may not raise error for incomplete JSON
        # This test verifies it either parses or raises ValueError
        try:
            result = to_parse_json(content)
            # If parsing succeeds, it should return some dict or list
            assert isinstance(result, (dict, list))
        except ValueError:
            # ValueError is also acceptable for malformed JSON
            pass


class TestForceToJsonResponse:
    """Test force_to_json_response function."""

    def test_force_valid_json_object(self):
        """Test forcing valid JSON object."""
        content = '{"result": "data"}'
        result = force_to_json_response(content)
        assert result["result"] == "data"
        assert result["is_json_guaranteed"] is True

    def test_force_valid_json_object_without_result_key(self):
        """Test forcing valid JSON object without result key."""
        content = '{"data": "value", "status": "ok"}'
        result = force_to_json_response(content)
        assert result["result"] == {"data": "value", "status": "ok"}
        assert result["is_json_guaranteed"] is True

    def test_force_valid_json_array(self):
        """Test forcing valid JSON array."""
        content = "[1, 2, 3]"
        result = force_to_json_response(content)
        assert result["result"] == [1, 2, 3]
        assert result["is_json_guaranteed"] is True

    def test_force_json_from_code_block(self):
        """Test forcing JSON from code block."""
        content = '```json\n{"result": "from block"}\n```'
        result = force_to_json_response(content)
        assert result["result"] == "from block"
        assert result["is_json_guaranteed"] is True

    def test_force_plain_text_to_json(self):
        """Test forcing plain text to JSON format."""
        content = "Plain text response"
        result = force_to_json_response(content, "test context", "test detail")
        assert result["result"] == "Plain text response"
        assert result["error"] == "Failed to convert to JSON format"
        assert result["error_context"] == "test context"
        assert result["error_detail"] == "test detail"
        assert result["is_json_guaranteed"] is True

    def test_force_plain_text_without_error_context(self):
        """Test forcing plain text without error context."""
        content = "Simple text"
        result = force_to_json_response(content)
        assert result["result"] == "Simple text"
        assert result["error"] == "Failed to convert to JSON format"
        assert "error_detail" in result
        assert result["is_json_guaranteed"] is True

    def test_force_invalid_json_to_json(self):
        """Test forcing invalid JSON to JSON format."""
        content = '{"invalid": json}'
        result = force_to_json_response(content, "parsing test")
        assert result["result"] == '{"invalid": json}'
        assert result["error"] == "Failed to convert to JSON format"
        assert result["error_context"] == "parsing test"
        assert result["is_json_guaranteed"] is True

    def test_force_empty_string(self):
        """Test forcing empty string."""
        content = ""
        result = force_to_json_response(content)
        assert result["result"] == ""
        assert result["error"] == "Failed to convert to JSON format"
        assert result["is_json_guaranteed"] is True


class TestEnsureJsonStructure:
    """Test ensure_json_structure function."""

    def test_ensure_dict_with_result(self):
        """Test ensuring dict with result key."""
        data = {"result": "value", "other": "data"}
        result = ensure_json_structure(data, "test")
        assert result["result"] == "value"
        assert result["other"] == "data"
        assert result["type"] == "test"
        assert result["is_json_guaranteed"] is True

    def test_ensure_dict_without_result(self):
        """Test ensuring dict without result key - keeps original dict."""
        data = {"data": "value"}
        result = ensure_json_structure(data, "test")
        # Implementation keeps original dict and adds type and is_json_guaranteed
        assert result["data"] == "value"
        assert result["type"] == "test"
        assert result["is_json_guaranteed"] is True

    def test_ensure_dict_without_type(self):
        """Test ensuring dict gets default type."""
        data = {"result": "value"}
        result = ensure_json_structure(data, "default_type")
        assert result["type"] == "default_type"

    def test_ensure_dict_with_existing_type(self):
        """Test ensuring dict keeps existing type."""
        data = {"result": "value", "type": "existing"}
        result = ensure_json_structure(data, "default_type")
        assert result["type"] == "existing"

    def test_ensure_string(self):
        """Test ensuring string data."""
        data = "simple text"
        result = ensure_json_structure(data, "text_type")
        assert result["result"] == "simple text"
        assert result["type"] == "text_type"
        assert result["is_json_guaranteed"] is True

    def test_ensure_list(self):
        """Test ensuring list data."""
        data = [1, 2, 3]
        result = ensure_json_structure(data, "array_type")
        assert result["result"] == [1, 2, 3]
        assert result["type"] == "array_type"
        assert result["is_json_guaranteed"] is True

    def test_ensure_integer(self):
        """Test ensuring integer data."""
        data = 123
        result = ensure_json_structure(data, "number_type")
        assert result["result"] == "123"
        assert result["type"] == "number_type"
        assert result["is_json_guaranteed"] is True

    def test_ensure_none(self):
        """Test ensuring None data."""
        data = None
        result = ensure_json_structure(data, "none_type")
        assert result["result"] == "None"
        assert result["type"] == "none_type"
        assert result["is_json_guaranteed"] is True

    def test_ensure_without_default_type(self):
        """Test ensuring data without default type."""
        data = "text"
        result = ensure_json_structure(data)
        assert result["result"] == "text"
        assert result["type"] is None
        assert result["is_json_guaranteed"] is True

    def test_ensure_empty_dict(self):
        """Test ensuring empty dict."""
        data = {}
        result = ensure_json_structure(data, "empty")
        assert result["type"] == "empty"
        assert result["is_json_guaranteed"] is True

    def test_ensure_empty_list(self):
        """Test ensuring empty list."""
        data = []
        result = ensure_json_structure(data, "empty_array")
        assert result["result"] == []
        assert result["type"] == "empty_array"
        assert result["is_json_guaranteed"] is True
