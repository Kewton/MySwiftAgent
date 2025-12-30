"""Unit tests for workflow schema validator node (Issue #333).

Tests for the workflow_schema_validator_node that validates API type
and field name compatibility in generated workflows.
"""

from typing import Any

import pytest

from aiagent.langgraph.workflowGeneratorAgents.nodes.workflow_schema_validator import (
    workflow_schema_validator_node,
)
from aiagent.langgraph.workflowGeneratorAgents.state import (
    create_initial_state,
)


@pytest.fixture
def base_task_data() -> dict[str, Any]:
    """Create base task data for testing."""
    return {
        "name": "Test Task",
        "description": "Test description",
        "input_interface": {
            "type": "json_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                },
                "required": ["query"],
            },
        },
        "output_interface": {
            "type": "json_schema",
            "schema": {
                "type": "object",
                "properties": {
                    "result": {"type": "string"},
                },
                "required": ["result"],
            },
        },
    }


@pytest.fixture
def valid_yaml_content() -> str:
    """Create valid workflow YAML content.

    Note: Uses :build_prompt.text to access a specific field (String type),
    not the full object reference :build_prompt which would be Object type.
    """
    return """version: 0.5
nodes:
  source: {}

  # Build prompt using stringTemplateAgent
  build_prompt:
    agent: stringTemplateAgent
    inputs:
      query: :source.user_input.query
    params:
      template: "Process this query: ${query}"

  # LLM processing - uses :build_prompt.text (field access = String type)
  llm_process:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :build_prompt.text
        model_name: gemini-2.5-flash
    timeout: 60000

  # Output
  output:
    agent: copyAgent
    inputs:
      result: :llm_process.result
    isResult: true
"""


@pytest.fixture
def type_mismatch_yaml_content() -> str:
    """Create YAML with type mismatch (Object type to String field)."""
    return """version: 0.5
nodes:
  source: {}

  # Fetch data
  fetch_data:
    agent: fetchAgent
    inputs:
      url: http://example.com/api
      method: GET
    timeout: 30000

  # Type mismatch: passing Object type to user_input (expects String)
  process_data:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :fetch_data
    timeout: 60000

  output:
    agent: copyAgent
    inputs:
      result: :process_data.result
    isResult: true
"""


@pytest.fixture
def field_name_error_yaml_content() -> str:
    """Create YAML with field name error (system_imput typo)."""
    return """version: 0.5
nodes:
  source: {}

  build_prompt:
    agent: stringTemplateAgent
    inputs:
      query: :source.user_input.query
    params:
      template: "Process: ${query}"

  # Field name error: system_imput instead of system_prompt
  llm_process:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :build_prompt
        system_imput: "You are a helpful assistant"
    timeout: 60000

  output:
    agent: copyAgent
    inputs:
      result: :llm_process.result
    isResult: true
"""


class TestWorkflowSchemaValidatorNode:
    """Tests for workflow_schema_validator_node function."""

    @pytest.mark.asyncio
    async def test_valid_workflow_passes(
        self, base_task_data: dict[str, Any], valid_yaml_content: str
    ):
        """Valid workflow should pass validation without errors."""
        state = create_initial_state("test_id", base_task_data)
        state["yaml_content"] = valid_yaml_content
        state["workflow_name"] = "test_workflow"

        result = await workflow_schema_validator_node(state)

        assert result["has_schema_errors"] is False
        assert result["schema_validation_result"]["is_valid"] is True
        assert len(result["schema_validation_issues"]) == 0

    @pytest.mark.asyncio
    async def test_detect_type_mismatch(
        self, base_task_data: dict[str, Any], type_mismatch_yaml_content: str
    ):
        """Should detect type mismatch (Object to String)."""
        state = create_initial_state("test_id", base_task_data)
        state["yaml_content"] = type_mismatch_yaml_content
        state["workflow_name"] = "test_workflow"

        result = await workflow_schema_validator_node(state)

        assert result["has_schema_errors"] is True
        assert result["schema_validation_result"]["is_valid"] is False
        issues = result["schema_validation_issues"]
        assert len(issues) > 0
        # Check for type_mismatch issue
        assert any(issue.get("issue_type") == "type_mismatch" for issue in issues)

    @pytest.mark.asyncio
    async def test_detect_field_name_error(
        self, base_task_data: dict[str, Any], field_name_error_yaml_content: str
    ):
        """Should detect field name error (system_imput typo)."""
        state = create_initial_state("test_id", base_task_data)
        state["yaml_content"] = field_name_error_yaml_content
        state["workflow_name"] = "test_workflow"

        result = await workflow_schema_validator_node(state)

        # Should detect the field name error
        issues = result["schema_validation_issues"]
        # Check for field_name_error or deprecation warning
        has_field_issue = any(
            issue.get("issue_type") in ("field_name_error", "deprecated_field")
            for issue in issues
        )
        assert has_field_issue or result["has_schema_errors"] is True

    @pytest.mark.asyncio
    async def test_missing_yaml_content(self, base_task_data: dict[str, Any]):
        """Should handle missing yaml_content gracefully."""
        state = create_initial_state("test_id", base_task_data)
        state["yaml_content"] = ""
        state["workflow_name"] = "test_workflow"

        result = await workflow_schema_validator_node(state)

        # Should handle gracefully - either pass (empty = no issues) or fail with clear error
        assert "schema_validation_result" in result
        assert "has_schema_errors" in result

    @pytest.mark.asyncio
    async def test_invalid_yaml_syntax(self, base_task_data: dict[str, Any]):
        """Should handle invalid YAML syntax gracefully."""
        state = create_initial_state("test_id", base_task_data)
        state["yaml_content"] = "invalid: yaml: : content"
        state["workflow_name"] = "test_workflow"

        result = await workflow_schema_validator_node(state)

        # Should handle YAML parse errors gracefully
        assert "schema_validation_result" in result
        # Invalid YAML should result in errors
        assert result["has_schema_errors"] is True


class TestSchemaValidationIssues:
    """Tests for schema validation issue details."""

    @pytest.mark.asyncio
    async def test_issue_contains_node_id(
        self, base_task_data: dict[str, Any], type_mismatch_yaml_content: str
    ):
        """Validation issues should contain node_id."""
        state = create_initial_state("test_id", base_task_data)
        state["yaml_content"] = type_mismatch_yaml_content
        state["workflow_name"] = "test_workflow"

        result = await workflow_schema_validator_node(state)

        issues = result["schema_validation_issues"]
        if issues:
            assert any("node_id" in issue for issue in issues)

    @pytest.mark.asyncio
    async def test_issue_contains_severity(
        self, base_task_data: dict[str, Any], type_mismatch_yaml_content: str
    ):
        """Validation issues should contain severity level."""
        state = create_initial_state("test_id", base_task_data)
        state["yaml_content"] = type_mismatch_yaml_content
        state["workflow_name"] = "test_workflow"

        result = await workflow_schema_validator_node(state)

        issues = result["schema_validation_issues"]
        if issues:
            assert any(
                issue.get("severity") in ("error", "warning") for issue in issues
            )


class TestStateFields:
    """Tests for new state fields added for schema validation."""

    @pytest.mark.asyncio
    async def test_state_has_schema_validation_result(
        self, base_task_data: dict[str, Any], valid_yaml_content: str
    ):
        """State should have schema_validation_result field."""
        state = create_initial_state("test_id", base_task_data)
        state["yaml_content"] = valid_yaml_content
        state["workflow_name"] = "test_workflow"

        result = await workflow_schema_validator_node(state)

        assert "schema_validation_result" in result
        assert result["schema_validation_result"] is not None

    @pytest.mark.asyncio
    async def test_state_has_schema_validation_issues(
        self, base_task_data: dict[str, Any], valid_yaml_content: str
    ):
        """State should have schema_validation_issues field."""
        state = create_initial_state("test_id", base_task_data)
        state["yaml_content"] = valid_yaml_content
        state["workflow_name"] = "test_workflow"

        result = await workflow_schema_validator_node(state)

        assert "schema_validation_issues" in result
        assert isinstance(result["schema_validation_issues"], list)

    @pytest.mark.asyncio
    async def test_state_has_has_schema_errors(
        self, base_task_data: dict[str, Any], valid_yaml_content: str
    ):
        """State should have has_schema_errors field."""
        state = create_initial_state("test_id", base_task_data)
        state["yaml_content"] = valid_yaml_content
        state["workflow_name"] = "test_workflow"

        result = await workflow_schema_validator_node(state)

        assert "has_schema_errors" in result
        assert isinstance(result["has_schema_errors"], bool)


class TestEdgeCases:
    """Tests for edge cases and additional scenarios."""

    @pytest.mark.asyncio
    async def test_non_fetchagent_nodes_ignored(self, base_task_data: dict[str, Any]):
        """Non-fetchAgent nodes should not be validated."""
        yaml_content = """version: 0.5
nodes:
  source: {}

  copy_node:
    agent: copyAgent
    inputs:
      data: :source.user_input

  output:
    agent: copyAgent
    inputs:
      result: :copy_node
    isResult: true
"""
        state = create_initial_state("test_id", base_task_data)
        state["yaml_content"] = yaml_content
        state["workflow_name"] = "test_workflow"

        result = await workflow_schema_validator_node(state)

        # No fetchAgent nodes, so no API validation issues
        assert result["has_schema_errors"] is False
        assert len(result["schema_validation_issues"]) == 0

    @pytest.mark.asyncio
    async def test_non_jsonoutput_fetchagent_not_validated(
        self, base_task_data: dict[str, Any]
    ):
        """fetchAgent calls to non-jsonoutput endpoints should not be validated for user_input type."""
        yaml_content = """version: 0.5
nodes:
  source: {}

  fetch_external:
    agent: fetchAgent
    inputs:
      url: http://example.com/api/data
      method: GET
    timeout: 30000

  output:
    agent: copyAgent
    inputs:
      result: :fetch_external
    isResult: true
"""
        state = create_initial_state("test_id", base_task_data)
        state["yaml_content"] = yaml_content
        state["workflow_name"] = "test_workflow"

        result = await workflow_schema_validator_node(state)

        # External API call, not jsonoutput, so no type validation
        assert result["has_schema_errors"] is False

    @pytest.mark.asyncio
    async def test_field_access_reference_passes_validation(
        self, base_task_data: dict[str, Any]
    ):
        """Field access references like :node.field should pass validation."""
        yaml_content = """version: 0.5
nodes:
  source: {}

  process:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :source.user_input.query
    timeout: 60000

  output:
    agent: copyAgent
    inputs:
      result: :process.result
    isResult: true
"""
        state = create_initial_state("test_id", base_task_data)
        state["yaml_content"] = yaml_content
        state["workflow_name"] = "test_workflow"

        result = await workflow_schema_validator_node(state)

        # :source.user_input.query is a field access, not object reference
        assert result["has_schema_errors"] is False

    @pytest.mark.asyncio
    async def test_validation_result_contains_statistics(
        self, base_task_data: dict[str, Any], type_mismatch_yaml_content: str
    ):
        """Validation result should contain node and API call statistics."""
        state = create_initial_state("test_id", base_task_data)
        state["yaml_content"] = type_mismatch_yaml_content
        state["workflow_name"] = "test_workflow"

        result = await workflow_schema_validator_node(state)

        validation_result = result["schema_validation_result"]
        assert "validated_nodes" in validation_result
        assert "api_calls_detected" in validation_result
        assert validation_result["validated_nodes"] > 0
        assert validation_result["api_calls_detected"] > 0

    @pytest.mark.asyncio
    async def test_both_type_mismatch_and_deprecated_field(
        self, base_task_data: dict[str, Any]
    ):
        """Workflow with both type mismatch and deprecated field should report both issues."""
        yaml_content = """version: 0.5
nodes:
  source: {}

  fetch_data:
    agent: fetchAgent
    inputs:
      url: http://example.com/api
      method: GET

  process:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :fetch_data
        system_imput: "You are a helper"
    timeout: 60000

  output:
    agent: copyAgent
    inputs:
      result: :process.result
    isResult: true
"""
        state = create_initial_state("test_id", base_task_data)
        state["yaml_content"] = yaml_content
        state["workflow_name"] = "test_workflow"

        result = await workflow_schema_validator_node(state)

        issues = result["schema_validation_issues"]
        issue_types = [issue.get("issue_type") for issue in issues]

        # Should have both type_mismatch and deprecated_field issues
        assert "type_mismatch" in issue_types
        assert "deprecated_field" in issue_types

    @pytest.mark.asyncio
    async def test_empty_nodes_section(self, base_task_data: dict[str, Any]):
        """Workflow with empty nodes should pass validation."""
        yaml_content = """version: 0.5
nodes: {}
"""
        state = create_initial_state("test_id", base_task_data)
        state["yaml_content"] = yaml_content
        state["workflow_name"] = "test_workflow"

        result = await workflow_schema_validator_node(state)

        assert result["has_schema_errors"] is False
        assert result["schema_validation_result"]["validated_nodes"] == 0
