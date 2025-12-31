"""Unit tests for workflow schema validator node (Issue #333).

Tests for the workflow_schema_validator_node that validates API type
and field name compatibility in generated workflows.
"""

from typing import Any

import pytest

from aiagent.langgraph.workflowGeneratorAgents.nodes.workflow_schema_validator import (
    DEPRECATED_FIELDS,
    JSONOUTPUT_ENDPOINTS,
    STRING_TYPE_FIELDS,
    _check_field_names,
    _check_type_mismatch,
    _create_error_state,
    _is_object_reference,
    _issue,
    _validate_fetch_agent_nodes,
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
        validation_result = result["schema_validation_result"]
        assert validation_result is not None
        assert validation_result["is_valid"] is True
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
        validation_result = result["schema_validation_result"]
        assert validation_result is not None
        assert validation_result["is_valid"] is False
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
        assert validation_result is not None
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
        validation_result = result["schema_validation_result"]
        assert validation_result is not None
        assert validation_result["validated_nodes"] == 0


class TestHelperFunctions:
    """Tests for private helper functions to improve coverage."""

    def test_issue_creates_standardized_dict(self):
        """_issue() should create a standardized validation issue dict."""
        result = _issue(
            node_id="test_node",
            issue_type="type_mismatch",
            message="Test message",
            severity="error",
            field_name="user_input",
            expected_value="String",
            actual_value="Object",
            suggestion="Fix it",
        )

        assert result["node_id"] == "test_node"
        assert result["issue_type"] == "type_mismatch"
        assert result["message"] == "Test message"
        assert result["severity"] == "error"
        assert result["field_name"] == "user_input"
        assert result["expected_value"] == "String"
        assert result["actual_value"] == "Object"
        assert result["suggestion"] == "Fix it"

    def test_issue_with_default_values(self):
        """_issue() should use default values for optional parameters."""
        result = _issue(
            node_id="test_node",
            issue_type="yaml_parse_error",
            message="Parse error",
        )

        assert result["node_id"] == "test_node"
        assert result["severity"] == "error"
        assert result["field_name"] == ""
        assert result["expected_value"] == ""
        assert result["actual_value"] == ""
        assert result["suggestion"] is None

    def test_is_object_reference_with_simple_reference(self):
        """_is_object_reference() should return True for simple node references."""
        assert _is_object_reference(":fetch_data") is True
        assert _is_object_reference(":source") is True
        assert _is_object_reference(":node123") is True

    def test_is_object_reference_with_field_access(self):
        """_is_object_reference() should return False for field access references."""
        assert _is_object_reference(":fetch_data.result") is False
        assert _is_object_reference(":source.user_input") is False
        assert _is_object_reference(":node.field.subfield") is False

    def test_is_object_reference_with_non_reference(self):
        """_is_object_reference() should return False for non-reference strings."""
        assert _is_object_reference("hello") is False
        assert _is_object_reference("123") is False
        assert _is_object_reference("") is False

    def test_is_object_reference_with_non_string(self):
        """_is_object_reference() should return False for non-string values."""
        assert _is_object_reference(123) is False
        assert _is_object_reference(None) is False
        assert _is_object_reference({"key": "value"}) is False
        assert _is_object_reference(["item"]) is False

    def test_is_object_reference_with_whitespace(self):
        """_is_object_reference() should handle whitespace correctly."""
        assert _is_object_reference("  :fetch_data  ") is True
        assert _is_object_reference("  :fetch_data.result  ") is False

    def test_check_type_mismatch_non_jsonoutput_endpoint(self):
        """_check_type_mismatch() should return empty list for non-jsonoutput endpoints."""
        node_def = {
            "agent": "fetchAgent",
            "inputs": {
                "url": "http://example.com/api",
                "body": {"user_input": ":fetch_data"},
            },
        }
        result = _check_type_mismatch(
            "test_node", node_def, "http://example.com/api", {}
        )
        assert result == []

    def test_check_type_mismatch_with_field_reference(self):
        """_check_type_mismatch() should not flag field access references."""
        node_def = {
            "agent": "fetchAgent",
            "inputs": {
                "url": "/v1/aiagent/utility/jsonoutput",
                "body": {"user_input": ":fetch_data.result"},
            },
        }
        result = _check_type_mismatch(
            "test_node", node_def, "/v1/aiagent/utility/jsonoutput", {}
        )
        assert result == []

    def test_check_type_mismatch_with_object_reference(self):
        """_check_type_mismatch() should flag object references to jsonoutput."""
        node_def = {
            "agent": "fetchAgent",
            "inputs": {
                "url": "/v1/aiagent/utility/jsonoutput",
                "body": {"user_input": ":fetch_data"},
            },
        }
        # fetch_data is a generic node (not a string output agent)
        workflow_nodes = {"fetch_data": {"agent": "fetchAgent"}}
        result = _check_type_mismatch(
            "test_node", node_def, "/v1/aiagent/utility/jsonoutput", workflow_nodes
        )
        assert len(result) == 1
        assert result[0]["issue_type"] == "type_mismatch"
        assert result[0]["node_id"] == "test_node"

    def test_check_type_mismatch_with_non_dict_body(self):
        """_check_type_mismatch() should handle non-dict body gracefully."""
        node_def = {
            "agent": "fetchAgent",
            "inputs": {
                "url": "/v1/aiagent/utility/jsonoutput",
                "body": "string_body",
            },
        }
        result = _check_type_mismatch(
            "test_node", node_def, "/v1/aiagent/utility/jsonoutput", {}
        )
        assert result == []

    def test_check_type_mismatch_with_none_user_input(self):
        """_check_type_mismatch() should handle None user_input."""
        node_def = {
            "agent": "fetchAgent",
            "inputs": {
                "url": "/v1/aiagent/utility/jsonoutput",
                "body": {"model_name": "gpt-4"},
            },
        }
        result = _check_type_mismatch(
            "test_node", node_def, "/v1/aiagent/utility/jsonoutput", {}
        )
        assert result == []

    def test_check_type_mismatch_with_string_template_agent_reference(self):
        """_check_type_mismatch() should NOT flag stringTemplateAgent references.

        Issue #333 fix: stringTemplateAgent outputs String type, not Object.
        References to stringTemplateAgent nodes should not trigger type_mismatch errors.
        """
        node_def = {
            "agent": "fetchAgent",
            "inputs": {
                "url": "/v1/aiagent/utility/jsonoutput",
                "body": {"user_input": ":build_summary_prompt"},
            },
        }
        # build_summary_prompt is a stringTemplateAgent node (outputs String)
        workflow_nodes = {
            "build_summary_prompt": {"agent": "stringTemplateAgent"},
        }
        result = _check_type_mismatch(
            "test_node", node_def, "/v1/aiagent/utility/jsonoutput", workflow_nodes
        )
        # Should NOT flag as error because stringTemplateAgent outputs String
        assert result == []

    def test_check_type_mismatch_with_sleeper_agent_reference(self):
        """_check_type_mismatch() should NOT flag sleeperAgent references.

        sleeperAgent is a simple value passthrough that outputs String type.
        """
        node_def = {
            "agent": "fetchAgent",
            "inputs": {
                "url": "/v1/aiagent/utility/jsonoutput",
                "body": {"user_input": ":delay_node"},
            },
        }
        # delay_node is a sleeperAgent (outputs String)
        workflow_nodes = {
            "delay_node": {"agent": "sleeperAgent"},
        }
        result = _check_type_mismatch(
            "test_node", node_def, "/v1/aiagent/utility/jsonoutput", workflow_nodes
        )
        # Should NOT flag as error because sleeperAgent outputs String
        assert result == []

    def test_check_field_names_with_deprecated_field(self):
        """_check_field_names() should flag deprecated fields."""
        node_def = {
            "agent": "fetchAgent",
            "inputs": {
                "body": {"system_imput": "You are helpful"},
            },
        }
        result = _check_field_names("test_node", node_def)
        assert len(result) == 1
        assert result[0]["issue_type"] == "deprecated_field"
        assert result[0]["severity"] == "warning"
        assert result[0]["field_name"] == "system_imput"

    def test_check_field_names_with_correct_field(self):
        """_check_field_names() should not flag correct field names."""
        node_def = {
            "agent": "fetchAgent",
            "inputs": {
                "body": {"system_prompt": "You are helpful", "user_input": "test"},
            },
        }
        result = _check_field_names("test_node", node_def)
        assert result == []

    def test_check_field_names_with_non_dict_body(self):
        """_check_field_names() should handle non-dict body gracefully."""
        node_def = {
            "agent": "fetchAgent",
            "inputs": {"body": "string_body"},
        }
        result = _check_field_names("test_node", node_def)
        assert result == []

    def test_validate_fetch_agent_nodes_with_non_dict_nodes(self):
        """_validate_fetch_agent_nodes() should handle non-dict nodes gracefully."""
        workflow = {"nodes": "not_a_dict"}
        result = _validate_fetch_agent_nodes(workflow)
        assert result == []

    def test_validate_fetch_agent_nodes_with_non_dict_node_def(self):
        """_validate_fetch_agent_nodes() should skip non-dict node definitions."""
        workflow = {
            "nodes": {
                "source": {},
                "invalid_node": "not_a_dict",
                "valid_node": {"agent": "copyAgent"},
            }
        }
        result = _validate_fetch_agent_nodes(workflow)
        assert result == []

    def test_validate_fetch_agent_nodes_skips_non_fetchagent(self):
        """_validate_fetch_agent_nodes() should skip non-fetchAgent nodes."""
        workflow = {
            "nodes": {
                "source": {},
                "copy_node": {
                    "agent": "copyAgent",
                    "inputs": {"body": {"system_imput": "test"}},
                },
            }
        }
        result = _validate_fetch_agent_nodes(workflow)
        assert result == []

    def test_create_error_state_creates_valid_state(
        self, base_task_data: dict[str, Any]
    ):
        """_create_error_state() should create a valid error state."""
        state = create_initial_state("test_id", base_task_data)
        error_message = "Test error message"

        result = _create_error_state(state, error_message)

        assert result["has_schema_errors"] is True
        validation_result = result["schema_validation_result"]
        assert validation_result is not None
        assert validation_result["is_valid"] is False
        assert len(result["schema_validation_issues"]) == 1
        assert result["schema_validation_issues"][0]["message"] == error_message
        assert result["schema_validation_issues"][0]["issue_type"] == "yaml_parse_error"


class TestConstants:
    """Tests for module-level constants."""

    def test_jsonoutput_endpoints_list(self):
        """JSONOUTPUT_ENDPOINTS should contain expected endpoints."""
        assert len(JSONOUTPUT_ENDPOINTS) >= 2
        assert "/v1/aiagent/utility/jsonoutput" in JSONOUTPUT_ENDPOINTS
        assert "/aiagent-api/v1/aiagent/utility/jsonoutput" in JSONOUTPUT_ENDPOINTS

    def test_deprecated_fields_mapping(self):
        """DEPRECATED_FIELDS should contain system_imput mapping."""
        assert "system_imput" in DEPRECATED_FIELDS
        assert DEPRECATED_FIELDS["system_imput"] == "system_prompt"

    def test_string_type_fields_list(self):
        """STRING_TYPE_FIELDS should contain expected fields."""
        assert "user_input" in STRING_TYPE_FIELDS
        assert "system_prompt" in STRING_TYPE_FIELDS


class TestYamlParsingErrors:
    """Tests for YAML parsing error handling."""

    @pytest.mark.asyncio
    async def test_yaml_not_dictionary(self, base_task_data: dict[str, Any]):
        """Should handle YAML that parses to non-dictionary."""
        yaml_content = """- item1
- item2
- item3
"""
        state = create_initial_state("test_id", base_task_data)
        state["yaml_content"] = yaml_content
        state["workflow_name"] = "test_workflow"

        result = await workflow_schema_validator_node(state)

        assert result["has_schema_errors"] is True
        assert "YAML content is not a dictionary" in str(
            result["schema_validation_issues"]
        )
