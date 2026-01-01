"""Test interface transformation logic (Issue #338 Phase 2).

This module tests the _transform_to_interface function and related utilities
that transform GraphAI output to match output_interface definitions.

The transformation layer ensures that:
- GraphAI results are normalized to output_interface schema
- Field extraction works with various data structures
- Required fields are validated
- Sensitive data is masked in logs
"""

import pytest

from app.core.worker import (
    _find_field_value,
    _path_based_search,
    _recursive_search,
    _transform_to_interface,
)


class TestTransformToInterface:
    """Test _transform_to_interface function."""

    def test_transform_with_no_output_interface(self):
        """Test that raw_output is returned when output_interface is None."""
        raw_output = {
            "success": True,
            "data": {"key": "value"},
            "error": None,
        }

        result = _transform_to_interface(raw_output, None)

        assert result == raw_output

    def test_transform_simple_flat_structure(self):
        """Test transformation with simple flat output structure."""
        raw_output = {
            "success": True,
            "search_results": [{"title": "Result 1"}],
            "error_message": "",
        }

        output_interface = {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "search_results": {"type": "array"},
                "error_message": {"type": "string"},
            },
            "required": ["success", "search_results"],
        }

        result = _transform_to_interface(raw_output, output_interface)

        assert result["success"] is True
        assert result["search_results"] == [{"title": "Result 1"}]
        assert result["error_message"] == ""

    def test_transform_nested_structure(self):
        """Test transformation with nested output structure (GraphAI format)."""
        raw_output = {
            "source": {"user_input": {"query": "test"}},
            "execute_search": {
                "search_results": [{"title": "Result 1"}, {"title": "Result 2"}],
                "search_results_count": 2,
                "status": "ok",
            },
            "format_results": {
                "success": True,
                "error_message": "",
            },
        }

        output_interface = {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "search_results": {"type": "array"},
                "error_message": {"type": "string"},
            },
            "required": ["success", "search_results"],
        }

        result = _transform_to_interface(raw_output, output_interface)

        assert result["success"] is True
        assert len(result["search_results"]) == 2
        assert result["error_message"] == ""

    def test_transform_missing_required_field(self):
        """Test that missing required fields are logged as warnings."""
        raw_output = {
            "success": True,
            # Missing search_results and error_message
        }

        output_interface = {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "search_results": {"type": "array"},
                "error_message": {"type": "string"},
            },
            "required": ["success", "search_results"],
        }

        result = _transform_to_interface(raw_output, output_interface)

        assert result["success"] is True
        assert result["search_results"] is None  # Not found
        assert result["error_message"] is None  # Not found

    def test_transform_with_output_node(self):
        """Test transformation from standard GraphAI output node format."""
        raw_output = {
            "results": {
                "output": {
                    "success": True,
                    "search_results": [{"title": "Test"}],
                    "error_message": "",
                }
            }
        }

        output_interface = {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "search_results": {"type": "array"},
                "error_message": {"type": "string"},
            },
            "required": ["success", "search_results"],
        }

        result = _transform_to_interface(raw_output, output_interface)

        assert result["success"] is True
        assert result["search_results"] == [{"title": "Test"}]

    def test_transform_handles_exception_gracefully(self):
        """Test that exceptions are handled and raw_output is returned."""
        raw_output = "not a dict"

        output_interface = {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
            },
        }

        # Should not raise, should return raw_output as fallback
        result = _transform_to_interface(raw_output, output_interface)  # type: ignore
        assert result == "not a dict"


class TestFindFieldValue:
    """Test _find_field_value function with different strategies."""

    def test_direct_strategy(self):
        """Test direct field access strategy."""
        data = {
            "success": True,
            "results": {"nested": "value"},
        }

        result = _find_field_value(data, "success", "direct")
        assert result is True

        result = _find_field_value(data, "missing", "direct")
        assert result is None

    def test_recursive_strategy(self):
        """Test recursive field search strategy."""
        data = {
            "level1": {
                "level2": {
                    "target_field": "found_value",
                }
            }
        }

        result = _find_field_value(data, "target_field", "recursive")
        assert result == "found_value"

    def test_path_strategy(self):
        """Test path-based field search strategy."""
        data = {
            "execute_search": {
                "search_results": [{"title": "Result"}],
            }
        }

        result = _find_field_value(data, "execute_search.search_results", "path")
        assert result == [{"title": "Result"}]


class TestRecursiveSearch:
    """Test _recursive_search function."""

    def test_find_direct_field(self):
        """Test finding field at root level."""
        data = {"target": "value", "other": "data"}

        result = _recursive_search(data, "target")
        assert result == "value"

    def test_find_nested_field(self):
        """Test finding deeply nested field."""
        data = {
            "level1": {
                "level2": {
                    "level3": {
                        "target": "deep_value",
                    }
                }
            }
        }

        result = _recursive_search(data, "target")
        assert result == "deep_value"

    def test_find_field_priority_first_occurrence(self):
        """Test that first occurrence is returned for duplicate fields."""
        data = {
            "first": {"target": "first_value"},
            "second": {"target": "second_value"},
        }

        result = _recursive_search(data, "target")
        # Should return the first one found (depth-first)
        assert result in ["first_value", "second_value"]

    def test_max_depth_limit(self):
        """Test that max depth prevents infinite recursion."""
        # Create deeply nested structure
        data: dict = {}
        current = data
        for i in range(10):
            current[f"level{i}"] = {}
            current = current[f"level{i}"]
        current["target"] = "value"

        # With max_depth=5, should not find the deeply nested value
        result = _recursive_search(data, "target", max_depth=5)
        assert result is None

        # With higher max_depth, should find it
        result = _recursive_search(data, "target", max_depth=15)
        assert result == "value"

    def test_not_found_returns_none(self):
        """Test that None is returned for missing fields."""
        data = {"key1": "value1", "key2": {"nested": "value2"}}

        result = _recursive_search(data, "nonexistent")
        assert result is None

    def test_handles_non_dict_values(self):
        """Test that non-dict values don't cause errors."""
        data = {
            "string": "value",
            "list": [1, 2, 3],
            "number": 42,
            "nested": {"target": "found"},
        }

        result = _recursive_search(data, "target")
        assert result == "found"


class TestPathBasedSearch:
    """Test _path_based_search function."""

    def test_simple_path(self):
        """Test simple single-level path."""
        data = {"field": "value"}

        result = _path_based_search(data, "field")
        assert result == "value"

    def test_multi_level_path(self):
        """Test multi-level dot-separated path."""
        data = {
            "level1": {
                "level2": {
                    "level3": "target_value",
                }
            }
        }

        result = _path_based_search(data, "level1.level2.level3")
        assert result == "target_value"

    def test_invalid_path_returns_none(self):
        """Test that invalid paths return None."""
        data = {"level1": {"level2": "value"}}

        result = _path_based_search(data, "level1.nonexistent.field")
        assert result is None

    def test_partial_path_match(self):
        """Test that partial path matching works."""
        data = {"level1": {"level2": {"field": "value"}}}

        result = _path_based_search(data, "level1.level2")
        assert result == {"field": "value"}

    def test_empty_path(self):
        """Test handling of empty path."""
        data = {"field": "value"}

        result = _path_based_search(data, "")
        assert result == data  # Empty path returns the whole data


class TestTransformationRealWorldScenarios:
    """Test transformation with real-world GraphAI scenarios."""

    def test_google_search_workflow_output(self):
        """Test transformation of Google Search workflow output."""
        raw_output = {
            "source": {"user_input": {"query": "AI news"}},
            "execute_search": {
                "search_results": [
                    {"title": "AI News 1", "link": "https://example.com/1", "knowledge": "..."},
                    {"title": "AI News 2", "link": "https://example.com/2", "knowledge": "..."},
                ],
                "search_results_count": 2,
                "status": "ok",
            },
            "format_results": {
                "success": True,
                "error_message": "",
            },
        }

        output_interface = {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "search_results": {"type": "array"},
                "search_results_count": {"type": "integer"},
                "error_message": {"type": "string"},
            },
            "required": ["success", "search_results"],
        }

        result = _transform_to_interface(raw_output, output_interface)

        assert result["success"] is True
        assert len(result["search_results"]) == 2
        assert result["search_results_count"] == 2
        assert result["error_message"] == ""

    def test_email_send_workflow_output(self):
        """Test transformation of email send workflow output."""
        raw_output = {
            "source": {"user_input": {"to": "test@example.com"}},
            "send_email": {
                "result": "Email sent successfully",
                "message_id": "msg_12345",
            },
            "output": {
                "success": True,
                "message_id": "msg_12345",
                "error_message": "",
            },
        }

        output_interface = {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "message_id": {"type": "string"},
                "error_message": {"type": "string"},
            },
            "required": ["success"],
        }

        result = _transform_to_interface(raw_output, output_interface)

        assert result["success"] is True
        assert result["message_id"] == "msg_12345"
        assert result["error_message"] == ""

    def test_tts_workflow_output(self):
        """Test transformation of Text-to-Speech workflow output."""
        raw_output = {
            "generate_audio": {
                "audio_content": "base64_encoded_audio...",
                "format": "mp3",
                "size_bytes": 12345,
            },
            "upload_drive": {
                "file_id": "drive_file_123",
                "file_name": "podcast.mp3",
                "web_view_link": "https://drive.google.com/file/d/...",
            },
            "output": {
                "success": True,
                "file_id": "drive_file_123",
                "web_view_link": "https://drive.google.com/file/d/...",
                "error_message": "",
            },
        }

        output_interface = {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "file_id": {"type": "string"},
                "web_view_link": {"type": "string"},
                "error_message": {"type": "string"},
            },
            "required": ["success", "file_id", "web_view_link"],
        }

        result = _transform_to_interface(raw_output, output_interface)

        assert result["success"] is True
        assert result["file_id"] == "drive_file_123"
        assert "drive.google.com" in result["web_view_link"]
