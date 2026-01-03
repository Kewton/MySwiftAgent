"""Unit tests for [object Object] pattern detection in workflow tester (Issue #340).

Tests for Layer 3 runtime detection: detecting [object Object] patterns
in workflow execution results to catch missed validations.
"""

from typing import Any

from aiagent.langgraph.workflowGeneratorAgents.nodes.workflow_tester import (
    _detect_object_object_pattern,
)


class TestDetectObjectObjectPattern:
    """Tests for _detect_object_object_pattern function."""

    def test_detect_in_simple_string(self):
        """Should detect [object Object] in simple string value."""
        execution_result = {
            "result": "Search results: [object Object], [object Object]"
        }

        issues = _detect_object_object_pattern(execution_result)

        assert len(issues) == 1
        assert issues[0]["issue_type"] == "object_object_detected"
        assert issues[0]["field_name"] == "result"
        assert issues[0]["severity"] == "error"

    def test_detect_in_nested_string(self):
        """Should detect [object Object] in nested object string."""
        execution_result = {"data": {"analysis": {"summary": "Found: [object Object]"}}}

        issues = _detect_object_object_pattern(execution_result)

        assert len(issues) == 1
        assert "data.analysis.summary" in issues[0]["field_name"]

    def test_detect_in_array_elements(self):
        """Should detect [object Object] in array string elements."""
        execution_result = {
            "items": [
                "Normal string",
                "Item: [object Object]",
                "Another normal string",
            ]
        }

        issues = _detect_object_object_pattern(execution_result)

        assert len(issues) == 1
        assert "[1]" in issues[0]["field_name"]

    def test_detect_multiple_occurrences(self):
        """Should detect multiple [object Object] occurrences in different fields."""
        execution_result = {
            "field1": "Has [object Object]",
            "field2": "Also has [object Object]",
            "field3": "Clean value",
        }

        issues = _detect_object_object_pattern(execution_result)

        assert len(issues) == 2
        field_names = [i["field_name"] for i in issues]
        assert "field1" in field_names
        assert "field2" in field_names

    def test_clean_result_no_issues(self):
        """Should return empty list for clean execution results."""
        execution_result = {
            "result": "Normal analysis result",
            "data": {
                "items": ["item1", "item2"],
                "count": 2,
            },
            "success": True,
        }

        issues = _detect_object_object_pattern(execution_result)

        assert len(issues) == 0

    def test_empty_result(self):
        """Should handle empty execution result."""
        issues = _detect_object_object_pattern({})
        assert len(issues) == 0

    def test_detect_case_sensitive(self):
        """Should only detect exact [object Object] pattern."""
        execution_result = {
            "text": "[OBJECT OBJECT]",  # Different case
            "text2": "[Object object]",  # Different case
            "text3": "[object Object]",  # Exact match
        }

        issues = _detect_object_object_pattern(execution_result)

        # Should only detect exact match
        assert len(issues) == 1
        assert issues[0]["field_name"] == "text3"

    def test_issue_contains_actual_value_truncated(self):
        """Should truncate long actual values in issue."""
        long_value = "Result: " + "[object Object] " * 100

        execution_result = {"result": long_value}

        issues = _detect_object_object_pattern(execution_result)

        assert len(issues) == 1
        # Actual value should be truncated
        assert len(issues[0]["actual_value"]) <= 103  # 100 + "..."

    def test_issue_contains_suggestion(self):
        """Should include helpful suggestion in issue."""
        execution_result = {"result": "[object Object]"}

        issues = _detect_object_object_pattern(execution_result)

        assert len(issues) == 1
        assert "suggestion" in issues[0]
        assert "stringTemplateAgent" in issues[0]["suggestion"]

    def test_detect_in_deeply_nested_structure(self):
        """Should detect [object Object] in deeply nested structures."""
        execution_result = {
            "level1": {
                "level2": {"level3": {"level4": {"value": "Deep: [object Object]"}}}
            }
        }

        issues = _detect_object_object_pattern(execution_result)

        assert len(issues) == 1
        assert "level1.level2.level3.level4.value" in issues[0]["field_name"]

    def test_detect_in_mixed_nested_array(self):
        """Should detect [object Object] in nested arrays."""
        execution_result = {
            "results": [
                {
                    "items": [
                        "Clean",
                        "[object Object] found here",
                    ]
                }
            ]
        }

        issues = _detect_object_object_pattern(execution_result)

        assert len(issues) == 1
        assert "[0]" in issues[0]["field_name"]
        assert "[1]" in issues[0]["field_name"]

    def test_non_string_values_ignored(self):
        """Should ignore non-string values without error."""
        execution_result = {
            "count": 42,
            "success": True,
            "data": None,
            "items": [1, 2, 3],
        }

        issues = _detect_object_object_pattern(execution_result)

        assert len(issues) == 0

    def test_detect_at_start_of_string(self):
        """Should detect [object Object] at start of string."""
        execution_result = {"result": "[object Object] is the first"}

        issues = _detect_object_object_pattern(execution_result)

        assert len(issues) == 1

    def test_detect_at_end_of_string(self):
        """Should detect [object Object] at end of string."""
        execution_result = {"result": "The last is [object Object]"}

        issues = _detect_object_object_pattern(execution_result)

        assert len(issues) == 1


class TestDetectObjectObjectPatternEdgeCases:
    """Edge case tests for _detect_object_object_pattern."""

    def test_handle_none_values_in_dict(self):
        """Should handle None values in dictionary."""
        execution_result: dict[str, Any] = {
            "result": None,
            "data": "Normal value",
        }

        issues = _detect_object_object_pattern(execution_result)

        assert len(issues) == 0

    def test_handle_nested_none(self):
        """Should handle nested None values."""
        execution_result = {
            "data": {
                "nested": None,
            }
        }

        issues = _detect_object_object_pattern(execution_result)

        assert len(issues) == 0

    def test_handle_empty_string(self):
        """Should handle empty strings."""
        execution_result = {
            "result": "",
        }

        issues = _detect_object_object_pattern(execution_result)

        assert len(issues) == 0

    def test_handle_whitespace_only(self):
        """Should handle whitespace-only strings."""
        execution_result = {
            "result": "   \n\t  ",
        }

        issues = _detect_object_object_pattern(execution_result)

        assert len(issues) == 0
