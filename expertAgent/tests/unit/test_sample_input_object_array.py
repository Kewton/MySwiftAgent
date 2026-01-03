"""Unit tests for object array validation in sample input generator (Issue #340).

Tests for Layer 1 validation: detecting object arrays in stringTemplateAgent
input fields to prevent [object Object] conversion issues.
"""

from typing import Any

import pytest

from aiagent.langgraph.workflowGeneratorAgents.nodes.sample_input_generator import (
    _get_string_template_input_fields,
    _object_array_issue,
    _validate_primitive_arrays,
)
from aiagent.langgraph.workflowGeneratorAgents.state import (
    create_initial_state,
)


class TestGetStringTemplateInputFields:
    """Tests for _get_string_template_input_fields function."""

    def test_single_string_template_node(self):
        """Should extract input fields from a single stringTemplateAgent node."""
        yaml_content = """
version: 0.5
nodes:
  source: {}
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      search_results: :source.user_input.search_results
      focus_points: :source.user_input.focus_points
    params:
      template: "Results: ${search_results}, Focus: ${focus_points}"
"""
        fields = _get_string_template_input_fields(yaml_content)
        assert "search_results" in fields
        assert "focus_points" in fields
        assert len(fields) == 2

    def test_multiple_string_template_nodes(self):
        """Should extract input fields from multiple stringTemplateAgent nodes."""
        yaml_content = """
version: 0.5
nodes:
  source: {}
  build_prompt1:
    agent: stringTemplateAgent
    inputs:
      query: :source.user_input.query
    params:
      template: "Query: ${query}"
  build_prompt2:
    agent: stringTemplateAgent
    inputs:
      keywords: :source.user_input.keywords
    params:
      template: "Keywords: ${keywords}"
"""
        fields = _get_string_template_input_fields(yaml_content)
        assert "query" in fields
        assert "keywords" in fields
        assert len(fields) == 2

    def test_no_string_template_nodes(self):
        """Should return empty set when no stringTemplateAgent nodes exist."""
        yaml_content = """
version: 0.5
nodes:
  source: {}
  fetch_data:
    agent: fetchAgent
    inputs:
      url: http://example.com/api
      method: GET
"""
        fields = _get_string_template_input_fields(yaml_content)
        assert len(fields) == 0

    def test_non_user_input_references(self):
        """Should not extract fields from non-user_input references."""
        yaml_content = """
version: 0.5
nodes:
  source: {}
  fetch_data:
    agent: fetchAgent
    inputs:
      url: http://example.com/api
      method: GET
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      data: :fetch_data.result
      query: :source.user_input.query
    params:
      template: "Data: ${data}, Query: ${query}"
"""
        fields = _get_string_template_input_fields(yaml_content)
        # Only query is from user_input, data is from previous node
        assert "query" in fields
        assert "data" not in fields
        assert len(fields) == 1

    def test_invalid_yaml(self):
        """Should return empty set for invalid YAML."""
        yaml_content = "invalid: yaml: : content"
        fields = _get_string_template_input_fields(yaml_content)
        assert len(fields) == 0

    def test_empty_yaml(self):
        """Should return empty set for empty YAML."""
        fields = _get_string_template_input_fields("")
        assert len(fields) == 0

    def test_yaml_without_nodes(self):
        """Should return empty set for YAML without nodes."""
        yaml_content = """
version: 0.5
"""
        fields = _get_string_template_input_fields(yaml_content)
        assert len(fields) == 0


class TestValidatePrimitiveArrays:
    """Tests for _validate_primitive_arrays function."""

    def test_object_array_in_target_field(self):
        """Should detect objects in array for target fields."""
        sample_input = {
            "search_results": [
                {"title": "Result 1", "url": "http://example1.com"},
                {"title": "Result 2", "url": "http://example2.com"},
            ],
            "query": "test query",
        }
        target_fields = {"search_results"}

        issues = _validate_primitive_arrays(sample_input, target_fields)

        assert len(issues) == 2  # Two objects in array
        assert all(issue["issue_type"] == "object_in_array" for issue in issues)
        assert all(issue["field_name"] == "search_results" for issue in issues)

    def test_primitive_array_passes(self):
        """Should not report issues for primitive arrays."""
        sample_input = {
            "focus_points": ["news", "technology", "science"],
            "query": "test query",
        }
        target_fields = {"focus_points"}

        issues = _validate_primitive_arrays(sample_input, target_fields)

        assert len(issues) == 0

    def test_non_target_field_ignored(self):
        """Should ignore object arrays in non-target fields."""
        sample_input = {
            "search_results": [
                {"title": "Result 1"},
            ],
            "other_data": [
                {"key": "value"},
            ],
        }
        target_fields = {"search_results"}

        issues = _validate_primitive_arrays(sample_input, target_fields)

        # Only search_results should be validated, not other_data
        assert len(issues) == 1
        assert issues[0]["field_name"] == "search_results"

    def test_mixed_array_with_objects(self):
        """Should detect objects in mixed arrays."""
        sample_input = {
            "items": [
                "string",
                {"key": "value"},
                123,
            ],
        }
        target_fields = {"items"}

        issues = _validate_primitive_arrays(sample_input, target_fields)

        assert len(issues) == 1  # Only the dict is an issue

    def test_empty_array(self):
        """Should not report issues for empty arrays."""
        sample_input = {
            "items": [],
        }
        target_fields = {"items"}

        issues = _validate_primitive_arrays(sample_input, target_fields)

        assert len(issues) == 0

    def test_non_array_fields(self):
        """Should not validate non-array fields."""
        sample_input = {
            "query": "test",
            "count": 5,
            "data": {"nested": "object"},
        }
        target_fields = {"query", "count", "data"}

        issues = _validate_primitive_arrays(sample_input, target_fields)

        assert len(issues) == 0

    def test_empty_sample_input(self):
        """Should handle empty sample input."""
        issues = _validate_primitive_arrays({}, {"field1"})
        assert len(issues) == 0

    def test_empty_target_fields(self):
        """Should handle empty target fields."""
        sample_input = {
            "items": [{"key": "value"}],
        }
        issues = _validate_primitive_arrays(sample_input, set())
        assert len(issues) == 0


class TestObjectArrayIssue:
    """Tests for _object_array_issue function."""

    def test_issue_structure(self):
        """Should create standardized issue structure."""
        issue = _object_array_issue("search_results", 0, "dict")

        assert issue["node_id"] == "sample_input"
        assert issue["issue_type"] == "object_in_array"
        assert "search_results" in issue["message"]
        assert "index 0" in issue["message"]
        assert issue["severity"] == "error"
        assert issue["field_name"] == "search_results"
        assert "primitive type" in issue["expected_value"]
        assert issue["actual_value"] == "dict"
        assert "suggestion" in issue

    def test_issue_message_content(self):
        """Should include relevant information in message."""
        issue = _object_array_issue("items", 5, "dict")

        assert "items" in issue["message"]
        assert "index 5" in issue["message"]
        assert "[object Object]" in issue["message"]
        assert "stringTemplateAgent" in issue["message"]


class TestSampleInputGeneratorIntegration:
    """Integration tests for sample_input_generator_node with object array validation."""

    @pytest.fixture
    def base_task_data(self) -> dict[str, Any]:
        """Create base task data for testing."""
        return {
            "name": "Test Task",
            "description": "Test description",
            "input_interface": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "search_results": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "title": {"type": "string"},
                                    "url": {"type": "string"},
                                },
                            },
                        },
                        "query": {"type": "string"},
                    },
                },
            },
            "output_interface": {
                "type": "json_schema",
                "schema": {"type": "object"},
            },
        }

    def test_state_includes_object_array_issues_field(
        self, base_task_data: dict[str, Any]
    ):
        """State should include object_array_issues field."""
        state = create_initial_state("test_id", base_task_data)

        # Check initial state has the new fields
        assert "object_array_issues" in state
        assert isinstance(state["object_array_issues"], list)
        assert len(state["object_array_issues"]) == 0

    def test_state_includes_has_object_array_errors_field(
        self, base_task_data: dict[str, Any]
    ):
        """State should include has_object_array_errors field."""
        state = create_initial_state("test_id", base_task_data)

        assert "has_object_array_errors" in state
        assert isinstance(state["has_object_array_errors"], bool)
        assert state["has_object_array_errors"] is False
