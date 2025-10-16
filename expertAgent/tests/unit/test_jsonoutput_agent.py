"""Tests for jsonOutput_agent utility functions."""

import pytest

from aiagent.langgraph.utilityaiagents.jsonOutput_agent import toParseJson


class TestToParseJson:
    """Test toParseJson utility function."""

    def test_parse_json_object_in_markdown(self):
        """Test parsing JSON object wrapped in markdown code block."""
        input_text = '```json\n{"key": "value", "number": 42}\n```'
        result = toParseJson(input_text)
        assert result == {"key": "value", "number": 42}

    def test_parse_json_array_in_markdown(self):
        """Test parsing JSON array wrapped in markdown code block."""
        input_text = '```json\n["item1", "item2", "item3"]\n```'
        result = toParseJson(input_text)
        assert result == ["item1", "item2", "item3"]

    def test_parse_empty_json_array_in_markdown(self):
        """Test parsing empty JSON array wrapped in markdown code block."""
        input_text = "```json\n[]\n```"
        result = toParseJson(input_text)
        assert result == []

    def test_parse_json_array_with_objects(self):
        """Test parsing JSON array containing objects."""
        input_text = (
            '```json\n[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]\n```'
        )
        result = toParseJson(input_text)
        assert result == [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

    def test_parse_nested_json_object(self):
        """Test parsing nested JSON object."""
        input_text = '```json\n{"outer": {"inner": "value"}}\n```'
        result = toParseJson(input_text)
        assert result == {"outer": {"inner": "value"}}

    def test_parse_plain_json_without_markdown(self):
        """Test parsing plain JSON without markdown wrapper."""
        input_text = '{"key": "value"}'
        result = toParseJson(input_text)
        assert result == {"key": "value"}

    def test_parse_plain_json_array_without_markdown(self):
        """Test parsing plain JSON array without markdown wrapper."""
        input_text = '["item1", "item2"]'
        result = toParseJson(input_text)
        assert result == ["item1", "item2"]

    def test_parse_json_with_whitespace(self):
        """Test parsing JSON with extra whitespace."""
        input_text = '```json\n  \n  ["url1", "url2"]  \n  \n```'
        result = toParseJson(input_text)
        assert result == ["url1", "url2"]

    def test_parse_invalid_json_raises_error(self):
        """Test that invalid JSON raises JSONDecodeError."""
        import json

        input_text = "```json\n{invalid json}\n```"
        with pytest.raises(json.JSONDecodeError):
            toParseJson(input_text)

    def test_parse_no_json_block_raises_error(self):
        """Test that text without JSON block raises ValueError."""
        input_text = "This is just plain text with no JSON"
        with pytest.raises(ValueError, match="Failed to extract JSON block"):
            toParseJson(input_text)

    def test_parse_json_with_surrounding_text(self):
        """Test parsing JSON with surrounding explanatory text."""
        input_text = (
            "Here are the results:\n```json\n"
            '["https://example.com/file1.pdf", '
            '"https://example.com/file2.pdf"]\n```\nEnd of results'
        )
        result = toParseJson(input_text)
        assert result == [
            "https://example.com/file1.pdf",
            "https://example.com/file2.pdf",
        ]
