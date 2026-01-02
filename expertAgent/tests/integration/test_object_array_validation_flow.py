"""Integration tests for object array validation flow (Issue #340).

Tests the complete validation flow:
- Layer 1: Test data type validation in sample_input_generator
- Layer 2: Prompt type constraints verification
- Layer 3: Runtime [object Object] pattern detection in workflow_tester

These tests verify the integration between components without
actually executing workflows on graphAiServer.
"""

from typing import Any

import pytest

from aiagent.langgraph.workflowGeneratorAgents.nodes.sample_input_generator import (
    _get_string_template_input_fields,
    _validate_primitive_arrays,
)
from aiagent.langgraph.workflowGeneratorAgents.nodes.workflow_tester import (
    _detect_object_object_pattern,
)
from aiagent.langgraph.workflowGeneratorAgents.prompts.workflow_generation import (
    TYPE_VALIDATION_RULES,
)
from aiagent.langgraph.workflowGeneratorAgents.state import (
    create_initial_state,
)


class TestLayer1AndLayer3Integration:
    """Integration tests for Layer 1 (validation) and Layer 3 (detection) flow."""

    @pytest.fixture
    def workflow_yaml_with_string_template(self) -> str:
        """Create a workflow YAML that uses stringTemplateAgent with user_input fields."""
        return """
version: 0.5
nodes:
  source: {}

  build_prompt:
    agent: stringTemplateAgent
    inputs:
      search_results: :source.user_input.search_results
      focus_points: :source.user_input.focus_points
      query: :source.user_input.query
    params:
      template: |-
        検索結果を分析してください。

        検索結果: ${search_results}
        フォーカス: ${focus_points}
        クエリ: ${query}

  analyze:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :build_prompt
        model_name: gemini-2.5-flash
    timeout: 60000

  output:
    agent: copyAgent
    inputs:
      result: :analyze.result
    isResult: true
"""

    @pytest.fixture
    def sample_input_with_object_array(self) -> dict[str, Any]:
        """Create sample input with object array (problematic)."""
        return {
            "search_results": [
                {"title": "Result 1", "url": "http://example1.com", "snippet": "..."},
                {"title": "Result 2", "url": "http://example2.com", "snippet": "..."},
            ],
            "focus_points": ["news", "technology"],  # Primitive array (OK)
            "query": "AI trends 2024",
        }

    @pytest.fixture
    def sample_input_with_primitive_arrays(self) -> dict[str, Any]:
        """Create sample input with only primitive arrays (correct)."""
        return {
            "search_results": [
                "Result 1: http://example1.com",
                "Result 2: http://example2.com",
            ],
            "focus_points": ["news", "technology"],
            "query": "AI trends 2024",
        }

    def test_layer1_detects_object_array_in_target_field(
        self,
        workflow_yaml_with_string_template: str,
        sample_input_with_object_array: dict[str, Any],
    ):
        """Layer 1 should detect object arrays in stringTemplateAgent input fields."""
        # Extract target fields from workflow
        target_fields = _get_string_template_input_fields(
            workflow_yaml_with_string_template
        )

        # Validate sample input
        issues = _validate_primitive_arrays(
            sample_input_with_object_array, target_fields
        )

        # Should detect object array in search_results
        assert len(issues) > 0
        assert any(
            issue["field_name"] == "search_results"
            and issue["issue_type"] == "object_in_array"
            for issue in issues
        )

        # Should NOT flag focus_points (primitive array)
        assert all(issue["field_name"] != "focus_points" for issue in issues)

    def test_layer1_passes_primitive_arrays(
        self,
        workflow_yaml_with_string_template: str,
        sample_input_with_primitive_arrays: dict[str, Any],
    ):
        """Layer 1 should pass validation for primitive arrays."""
        # Extract target fields from workflow
        target_fields = _get_string_template_input_fields(
            workflow_yaml_with_string_template
        )

        # Validate sample input
        issues = _validate_primitive_arrays(
            sample_input_with_primitive_arrays, target_fields
        )

        # Should pass with no issues
        assert len(issues) == 0

    def test_layer3_detects_object_object_in_result(self):
        """Layer 3 should detect [object Object] patterns in execution results."""
        # Simulated execution result with [object Object] pattern
        execution_result = {
            "result": {
                "analysis": "検索結果を分析しました。検索結果: [object Object],[object Object]",
                "focus": "フォーカス: news,technology",
            }
        }

        issues = _detect_object_object_pattern(execution_result)

        assert len(issues) == 1
        assert issues[0]["issue_type"] == "object_object_detected"
        assert "analysis" in issues[0]["field_name"]

    def test_layer3_passes_clean_result(self):
        """Layer 3 should pass clean results without [object Object]."""
        # Clean execution result
        execution_result = {
            "result": {
                "analysis": "検索結果を分析しました。正常に処理されました。",
                "summary": "AI trends are evolving rapidly.",
            }
        }

        issues = _detect_object_object_pattern(execution_result)

        assert len(issues) == 0


class TestValidationFlowWithState:
    """Integration tests for validation flow with WorkflowGeneratorState."""

    @pytest.fixture
    def task_data(self) -> dict[str, Any]:
        """Create task data for testing."""
        return {
            "name": "Search Result Analysis",
            "description": "Analyze search results and generate summary",
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
                    "required": ["search_results", "query"],
                },
            },
            "output_interface": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "analysis": {"type": "string"},
                    },
                },
            },
        }

    def test_state_initialization_includes_object_array_fields(
        self, task_data: dict[str, Any]
    ):
        """State should include object_array_issues and has_object_array_errors fields."""
        state = create_initial_state("test_id", task_data)

        assert "object_array_issues" in state
        assert "has_object_array_errors" in state
        assert state["object_array_issues"] == []
        assert state["has_object_array_errors"] is False


class TestPromptContainsValidationRules:
    """Integration tests for prompt validation rules."""

    def test_type_validation_rules_contains_array_constraint_info(self):
        """TYPE_VALIDATION_RULES should contain array constraint information."""
        # Check for Issue #340 specific content
        assert "Issue #340" in TYPE_VALIDATION_RULES

        # Check for [object Object] warning
        assert "[object Object]" in TYPE_VALIDATION_RULES

        # Check for array type constraint explanation
        assert "配列" in TYPE_VALIDATION_RULES

        # Check for correct pattern example
        assert "プリミティブ" in TYPE_VALIDATION_RULES

    def test_type_validation_rules_integrated_with_string_template_rules(self):
        """Array constraints should be integrated with stringTemplateAgent rules."""
        # Check that array constraints are near stringTemplateAgent rules
        string_template_pos = TYPE_VALIDATION_RULES.find("stringTemplateAgent")
        array_constraint_pos = TYPE_VALIDATION_RULES.find("配列の型制約")

        assert string_template_pos >= 0
        assert array_constraint_pos >= 0


class TestCompleteValidationFlow:
    """End-to-end tests for the complete validation flow."""

    def test_complete_flow_with_object_array(self):
        """Test complete validation flow from Layer 1 through Layer 3."""
        # Workflow with stringTemplateAgent
        workflow_yaml = """
version: 0.5
nodes:
  source: {}
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      items: :source.user_input.items
    params:
      template: "Items: ${items}"
  output:
    agent: copyAgent
    inputs:
      result: :build_prompt
    isResult: true
"""
        # Sample input with object array
        sample_input = {
            "items": [{"name": "Item 1"}, {"name": "Item 2"}],
        }

        # Simulated execution result (what would happen if validation was bypassed)
        execution_result = {"result": "Items: [object Object],[object Object]"}

        # Layer 1: Extract target fields and validate
        target_fields = _get_string_template_input_fields(workflow_yaml)
        layer1_issues = _validate_primitive_arrays(sample_input, target_fields)

        # Layer 3: Detect [object Object] in result
        layer3_issues = _detect_object_object_pattern(execution_result)

        # Both layers should detect issues
        assert len(layer1_issues) > 0, "Layer 1 should detect object array"
        assert len(layer3_issues) > 0, "Layer 3 should detect [object Object]"

        # Layer 1 issues should indicate the field name
        assert any(issue["field_name"] == "items" for issue in layer1_issues)

        # Layer 3 issues should indicate the detected pattern
        assert any(
            issue["issue_type"] == "object_object_detected" for issue in layer3_issues
        )

    def test_complete_flow_with_primitive_arrays(self):
        """Test complete validation flow with correct primitive arrays."""
        # Workflow with stringTemplateAgent
        workflow_yaml = """
version: 0.5
nodes:
  source: {}
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      items: :source.user_input.items
    params:
      template: "Items: ${items}"
  output:
    agent: copyAgent
    inputs:
      result: :build_prompt
    isResult: true
"""
        # Sample input with primitive array (correct)
        sample_input = {
            "items": ["Item 1", "Item 2", "Item 3"],
        }

        # Simulated clean execution result
        execution_result = {"result": "Items: Item 1,Item 2,Item 3"}

        # Layer 1: Extract target fields and validate
        target_fields = _get_string_template_input_fields(workflow_yaml)
        layer1_issues = _validate_primitive_arrays(sample_input, target_fields)

        # Layer 3: Check result
        layer3_issues = _detect_object_object_pattern(execution_result)

        # Both layers should pass
        assert len(layer1_issues) == 0, "Layer 1 should pass for primitive arrays"
        assert len(layer3_issues) == 0, "Layer 3 should pass for clean results"
