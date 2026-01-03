"""Unit tests for P2-8: workflow_validator array validation (Issue #340).

Tests for Layer 4 validation: detecting object arrays in stringTemplateAgent
input fields from the workflow YAML and interface schema.
"""

from typing import Any

import pytest

from aiagent.langgraph.workflowGeneratorAgents.utils.workflow_validator import (
    validate_workflow_arrays,
)


class TestValidateWorkflowArrays:
    """Tests for validate_workflow_arrays function."""

    @pytest.fixture
    def basic_interface_schema(self) -> dict[str, Any]:
        """Create basic interface schema with array type definitions."""
        return {
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
                "focus_points": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "query": {"type": "string"},
            },
        }

    def test_detects_object_array_in_string_template(
        self, basic_interface_schema: dict[str, Any]
    ):
        """Should detect object array passed to stringTemplateAgent."""
        yaml_content = """
version: 0.5
nodes:
  source: {}
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      search_results: :source.user_input.search_results
    params:
      template: "Results: ${search_results}"
  output:
    agent: copyAgent
    inputs:
      text: :build_prompt.text
    isResult: true
"""
        issues = validate_workflow_arrays(yaml_content, basic_interface_schema)

        assert len(issues) >= 1
        assert any(
            issue["issue_type"] == "object_array_in_string_template" for issue in issues
        )
        assert any(issue["field_name"] == "search_results" for issue in issues)

    def test_primitive_array_passes(self, basic_interface_schema: dict[str, Any]):
        """Should not report issues for primitive array passed to stringTemplateAgent."""
        yaml_content = """
version: 0.5
nodes:
  source: {}
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      focus_points: :source.user_input.focus_points
    params:
      template: "Focus: ${focus_points}"
  output:
    agent: copyAgent
    inputs:
      text: :build_prompt.text
    isResult: true
"""
        issues = validate_workflow_arrays(yaml_content, basic_interface_schema)

        # focus_points is items.type=string, so no issues
        assert len(issues) == 0

    def test_non_string_template_agent_ignored(
        self, basic_interface_schema: dict[str, Any]
    ):
        """Should not validate arrays passed to non-stringTemplateAgent nodes."""
        yaml_content = """
version: 0.5
nodes:
  source: {}
  process_data:
    agent: copyAgent
    inputs:
      search_results: :source.user_input.search_results
  output:
    agent: copyAgent
    inputs:
      data: :process_data.result
    isResult: true
"""
        issues = validate_workflow_arrays(yaml_content, basic_interface_schema)

        # copyAgent can handle object arrays fine
        assert len(issues) == 0

    def test_empty_yaml(self, basic_interface_schema: dict[str, Any]):
        """Should return empty list for empty YAML."""
        issues = validate_workflow_arrays("", basic_interface_schema)
        assert len(issues) == 0

    def test_invalid_yaml(self, basic_interface_schema: dict[str, Any]):
        """Should return empty list for invalid YAML."""
        issues = validate_workflow_arrays("invalid: yaml: : :", basic_interface_schema)
        assert len(issues) == 0

    def test_yaml_without_nodes(self, basic_interface_schema: dict[str, Any]):
        """Should return empty list for YAML without nodes."""
        yaml_content = """
version: 0.5
"""
        issues = validate_workflow_arrays(yaml_content, basic_interface_schema)
        assert len(issues) == 0

    def test_empty_interface_schema(self):
        """Should return empty list for empty interface schema."""
        yaml_content = """
version: 0.5
nodes:
  source: {}
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      data: :source.user_input.data
    params:
      template: "Data: ${data}"
  output:
    agent: copyAgent
    inputs:
      text: :build_prompt.text
    isResult: true
"""
        issues = validate_workflow_arrays(yaml_content, {})
        assert len(issues) == 0

    def test_issue_structure(self, basic_interface_schema: dict[str, Any]):
        """Should return properly structured issue dict."""
        yaml_content = """
version: 0.5
nodes:
  source: {}
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      search_results: :source.user_input.search_results
    params:
      template: "Results: ${search_results}"
  output:
    agent: copyAgent
    inputs:
      text: :build_prompt.text
    isResult: true
"""
        issues = validate_workflow_arrays(yaml_content, basic_interface_schema)

        assert len(issues) >= 1
        issue = issues[0]

        # Verify issue structure follows standard pattern
        assert "node_id" in issue
        assert "issue_type" in issue
        assert "message" in issue
        assert "severity" in issue
        assert "field_name" in issue
        assert "suggestion" in issue

    def test_multiple_string_template_nodes(
        self, basic_interface_schema: dict[str, Any]
    ):
        """Should validate all stringTemplateAgent nodes."""
        yaml_content = """
version: 0.5
nodes:
  source: {}
  build_prompt1:
    agent: stringTemplateAgent
    inputs:
      search_results: :source.user_input.search_results
    params:
      template: "Results1: ${search_results}"
  build_prompt2:
    agent: stringTemplateAgent
    inputs:
      focus_points: :source.user_input.focus_points
    params:
      template: "Focus: ${focus_points}"
  output:
    agent: copyAgent
    inputs:
      text1: :build_prompt1.text
      text2: :build_prompt2.text
    isResult: true
"""
        issues = validate_workflow_arrays(yaml_content, basic_interface_schema)

        # Only search_results should be flagged (object array)
        # focus_points is string array, should pass
        assert len(issues) >= 1
        assert all(issue["field_name"] != "focus_points" for issue in issues)

    def test_nested_user_input_reference(self, basic_interface_schema: dict[str, Any]):
        """Should not validate non-user_input references."""
        yaml_content = """
version: 0.5
nodes:
  source: {}
  fetch_data:
    agent: fetchAgent
    inputs:
      url: http://example.com
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      data: :fetch_data.result
    params:
      template: "Data: ${data}"
  output:
    agent: copyAgent
    inputs:
      text: :build_prompt.text
    isResult: true
"""
        issues = validate_workflow_arrays(yaml_content, basic_interface_schema)

        # fetch_data.result is not from user_input, should not be validated
        assert len(issues) == 0

    def test_integer_array_type(self):
        """Should not flag integer arrays passed to stringTemplateAgent."""
        interface_schema = {
            "type": "object",
            "properties": {
                "scores": {
                    "type": "array",
                    "items": {"type": "integer"},
                },
            },
        }
        yaml_content = """
version: 0.5
nodes:
  source: {}
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      scores: :source.user_input.scores
    params:
      template: "Scores: ${scores}"
  output:
    agent: copyAgent
    inputs:
      text: :build_prompt.text
    isResult: true
"""
        issues = validate_workflow_arrays(yaml_content, interface_schema)

        # integer arrays are primitives, should pass
        assert len(issues) == 0

    def test_boolean_array_type(self):
        """Should not flag boolean arrays passed to stringTemplateAgent."""
        interface_schema = {
            "type": "object",
            "properties": {
                "flags": {
                    "type": "array",
                    "items": {"type": "boolean"},
                },
            },
        }
        yaml_content = """
version: 0.5
nodes:
  source: {}
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      flags: :source.user_input.flags
    params:
      template: "Flags: ${flags}"
  output:
    agent: copyAgent
    inputs:
      text: :build_prompt.text
    isResult: true
"""
        issues = validate_workflow_arrays(yaml_content, interface_schema)

        # boolean arrays are primitives, should pass
        assert len(issues) == 0
