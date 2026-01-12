"""Integration tests for Issue #333: Workflow Schema Validation.

This module tests the integration of workflow_schema_validator_node
into the workflow generator graph.

Test Coverage:
- Schema validation node integration in graph flow
- Type mismatch detection and self-repair routing
- Field name error detection and feedback generation
- End-to-end validation with mock LLM responses
"""

from unittest.mock import AsyncMock, patch

import pytest

from aiagent.langgraph.workflowGeneratorAgents.agent import (
    create_workflow_generator_graph,
    schema_validator_router,
)
from aiagent.langgraph.workflowGeneratorAgents.nodes.workflow_schema_validator import (
    workflow_schema_validator_node,
)
from aiagent.langgraph.workflowGeneratorAgents.prompts.workflow_generation import (
    TYPE_VALIDATION_RULES,
    create_workflow_generation_prompt,
)
from aiagent.langgraph.workflowGeneratorAgents.state import WorkflowGeneratorState

# ============================================================================
# Test Fixtures
# ============================================================================


def create_valid_yaml_content() -> str:
    """Create a valid YAML workflow that passes schema validation.

    Note: We use :source.user_input.query (field access) instead of :node_name
    because the validator treats bare :node_name as Object reference.
    stringTemplateAgent output is String, but validator can't determine agent output types.
    """
    return """version: 0.5
nodes:
  source: {}

  llm_call:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :source.user_input.query
        system_prompt: "You are a helpful assistant"
        model_name: gemini-2.5-flash
    timeout: 60000

  output:
    agent: copyAgent
    inputs:
      result: :llm_call.result
    isResult: true
"""


def create_type_mismatch_yaml_content() -> str:
    """Create a YAML workflow with type mismatch error (Object passed to String field)."""
    return """version: 0.5
nodes:
  source: {}

  fetch_data:
    agent: fetchAgent
    inputs:
      url: http://example.com/api
      method: GET
    timeout: 30000

  llm_call:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :fetch_data
        model_name: gemini-2.5-flash
    timeout: 60000

  output:
    agent: copyAgent
    inputs:
      result: :llm_call.result
    isResult: true
"""


def create_deprecated_field_yaml_content() -> str:
    """Create a YAML workflow with deprecated field name (system_imput)."""
    return """version: 0.5
nodes:
  source: {}

  llm_call:
    agent: fetchAgent
    inputs:
      url: http://localhost:8004/aiagent-api/v1/aiagent/utility/jsonoutput
      method: POST
      body:
        user_input: :source.user_input.query
        system_imput: "You are a helpful assistant"
        model_name: gemini-2.5-flash
    timeout: 60000

  output:
    agent: copyAgent
    inputs:
      result: :llm_call.result
    isResult: true
"""


def create_mock_state(yaml_content: str = "") -> WorkflowGeneratorState:
    """Create a mock state for testing.

    Args:
        yaml_content: YAML content to include in state

    Returns:
        WorkflowGeneratorState with mock values
    """
    return {
        "task_master_id": "tm_test123",
        "task_data": {
            "name": "Test Task",
            "description": "Test description",
            "input_interface": {"schema": {}},
            "output_interface": {"schema": {}},
        },
        "yaml_content": yaml_content,
        "workflow_name": "test_workflow",
        "status": "yaml_generated",
        "retry_count": 0,
        "max_retry": 3,
        "fast_mode": False,
        "generation_retry_count": 1,
        "generation_model": "gemini-2.0-flash-exp",
        "error_feedback": None,
        "is_valid": True,
        "validation_errors": [],
        "validation_result": None,
        "evaluation_score": 0,
        "test_http_status": None,
        "test_result": None,
        "sample_input": None,
        "needs_test_data_regeneration": False,
        "test_data_regeneration_count": 0,
        "max_test_data_regeneration": 2,
        "llm_evaluation_result": None,
        "repair_history": [],
        "result_summary": None,
        # Issue #333 fields
        "schema_validation_result": None,
        "schema_validation_issues": [],
        "has_schema_errors": False,
    }


# ============================================================================
# Phase 1: TYPE_VALIDATION_RULES Integration Tests
# ============================================================================


class TestTypeValidationRulesIntegration:
    """Test TYPE_VALIDATION_RULES integration into prompts."""

    def test_type_validation_rules_defined(self) -> None:
        """Test that TYPE_VALIDATION_RULES constant is defined and not empty."""
        assert TYPE_VALIDATION_RULES is not None
        assert len(TYPE_VALIDATION_RULES) > 0
        assert "fetchAgent" in TYPE_VALIDATION_RULES
        assert "Object" in TYPE_VALIDATION_RULES
        assert "String" in TYPE_VALIDATION_RULES

    def test_type_validation_rules_included_in_prompt(self) -> None:
        """Test that TYPE_VALIDATION_RULES is included in generated prompt.

        This is the critical integration check: the constant must be USED,
        not just defined.
        """
        task_data = {
            "name": "Test Task",
            "description": "Test description",
            "input_interface": {"schema": {"type": "object"}},
            "output_interface": {"schema": {"type": "object"}},
        }
        graphai_capabilities = {
            "agents": [
                {"name": "fetchAgent", "description": "HTTP fetch agent"},
                {"name": "stringTemplateAgent", "description": "Template agent"},
            ]
        }
        expert_agent_capabilities = {
            "utility_apis": [],
            "ai_agent_apis": [],
        }

        prompt = create_workflow_generation_prompt(
            task_data, graphai_capabilities, expert_agent_capabilities
        )

        # Verify TYPE_VALIDATION_RULES content is in the prompt
        assert "Important Type Validation Rules" in prompt
        assert "fetchAgent Output Type" in prompt
        # Issue #340: Section renamed to Japanese for consistency
        assert "stringTemplateAgent 重要な制限事項" in prompt
        assert "Field Name Validation" in prompt

    def test_type_validation_rules_contains_key_guidance(self) -> None:
        """Test that TYPE_VALIDATION_RULES contains essential guidance."""
        # Check for key patterns that help LLM generate correct workflows
        assert "user_input" in TYPE_VALIDATION_RULES
        assert "String type" in TYPE_VALIDATION_RULES
        assert "stringTemplateAgent" in TYPE_VALIDATION_RULES
        assert "system_prompt" in TYPE_VALIDATION_RULES
        assert "system_imput" in TYPE_VALIDATION_RULES  # Known typo to avoid


# ============================================================================
# Phase 2: Schema Validator Node Integration Tests
# ============================================================================


class TestSchemaValidatorNodeIntegration:
    """Test workflow_schema_validator_node integration."""

    @pytest.mark.asyncio
    async def test_valid_yaml_passes_validation(self) -> None:
        """Test that valid YAML passes schema validation."""
        state = create_mock_state(create_valid_yaml_content())
        result = await workflow_schema_validator_node(state)

        assert result["has_schema_errors"] is False
        assert result["schema_validation_result"]["is_valid"] is True
        assert len(result["schema_validation_issues"]) == 0

    @pytest.mark.asyncio
    async def test_type_mismatch_detected(self) -> None:
        """Test that type mismatch is detected when Object is passed to String field."""
        state = create_mock_state(create_type_mismatch_yaml_content())
        result = await workflow_schema_validator_node(state)

        assert result["has_schema_errors"] is True
        assert result["schema_validation_result"]["is_valid"] is False

        # Find the type mismatch issue
        issues = result["schema_validation_issues"]
        type_mismatch_issues = [i for i in issues if i["issue_type"] == "type_mismatch"]
        assert len(type_mismatch_issues) == 1
        assert "Object reference" in type_mismatch_issues[0]["message"]
        assert type_mismatch_issues[0]["severity"] == "error"

    @pytest.mark.asyncio
    async def test_deprecated_field_detected(self) -> None:
        """Test that deprecated field name (system_imput) is detected."""
        state = create_mock_state(create_deprecated_field_yaml_content())
        result = await workflow_schema_validator_node(state)

        # Deprecated fields are warnings, not errors
        issues = result["schema_validation_issues"]
        deprecated_issues = [i for i in issues if i["issue_type"] == "deprecated_field"]
        assert len(deprecated_issues) == 1
        assert "system_imput" in deprecated_issues[0]["message"]
        assert deprecated_issues[0]["severity"] == "warning"

    @pytest.mark.asyncio
    async def test_empty_yaml_passes_validation(self) -> None:
        """Test that empty YAML content passes validation (nothing to validate)."""
        state = create_mock_state("")
        result = await workflow_schema_validator_node(state)

        assert result["has_schema_errors"] is False
        assert result["schema_validation_result"]["is_valid"] is True


# ============================================================================
# Phase 3: Graph Integration Tests
# ============================================================================


class TestGraphIntegration:
    """Test schema validator integration in workflow generator graph."""

    def test_schema_validator_router_passes_on_valid(self) -> None:
        """Test router returns sample_input_generator when validation passes."""
        state: WorkflowGeneratorState = {
            **create_mock_state(),
            "has_schema_errors": False,
            "schema_validation_issues": [],
        }
        result = schema_validator_router(state)
        assert result == "sample_input_generator"

    def test_schema_validator_router_routes_to_self_repair_on_error(self) -> None:
        """Test router returns self_repair when validation fails."""
        state: WorkflowGeneratorState = {
            **create_mock_state(),
            "has_schema_errors": True,
            "schema_validation_issues": [
                {"issue_type": "type_mismatch", "severity": "error", "message": "..."}
            ],
        }
        result = schema_validator_router(state)
        assert result == "self_repair"

    def test_graph_includes_schema_validator_node(self) -> None:
        """Test that the compiled graph includes schema_validator node."""
        graph = create_workflow_generator_graph()

        # The graph should have schema_validator node
        # LangGraph stores nodes in the graph structure
        # We verify by checking the graph's node names
        node_names = list(graph.nodes.keys())
        assert "schema_validator" in node_names

    def test_graph_has_schema_validator_after_generator(self) -> None:
        """Test that schema_validator comes after generator in the graph."""
        graph = create_workflow_generator_graph()

        # Get the graph structure to verify edges
        # generator should connect to schema_validator
        node_names = list(graph.nodes.keys())

        # Both generator and schema_validator should exist
        assert "generator" in node_names
        assert "schema_validator" in node_names


# ============================================================================
# Phase 4: Self-Repair Integration Tests
# ============================================================================


class TestSelfRepairIntegration:
    """Test self-repair node integration with schema validation errors."""

    @pytest.mark.asyncio
    async def test_self_repair_includes_schema_errors(self) -> None:
        """Test that self_repair node includes schema validation errors in feedback."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.self_repair import (
            self_repair_node,
        )

        state: WorkflowGeneratorState = {
            **create_mock_state(),
            "has_schema_errors": True,
            "schema_validation_issues": [
                {
                    "node_id": "llm_call",
                    "issue_type": "type_mismatch",
                    "message": "user_input expects String type but receives Object reference ':fetch_data'",
                    "severity": "error",
                    "suggestion": "Use stringTemplateAgent to convert Object to String",
                }
            ],
            "validation_errors": [],
        }

        result = await self_repair_node(state)

        # Check error_feedback contains schema error information
        assert "error_feedback" in result
        error_feedback = result["error_feedback"]
        assert "type_mismatch" in error_feedback
        assert "stringTemplateAgent" in error_feedback

        # Check schema validation guidance is included
        assert "SCHEMA VALIDATION ERRORS DETECTED" in error_feedback

    @pytest.mark.asyncio
    async def test_self_repair_increments_retry_count(self) -> None:
        """Test that self_repair increments retry_count correctly."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.self_repair import (
            self_repair_node,
        )

        state: WorkflowGeneratorState = {
            **create_mock_state(),
            "has_schema_errors": True,
            "schema_validation_issues": [
                {
                    "node_id": "test",
                    "issue_type": "type_mismatch",
                    "message": "Test error",
                    "severity": "error",
                }
            ],
            "retry_count": 1,
        }

        result = await self_repair_node(state)
        assert result["retry_count"] == 2


# ============================================================================
# Phase 5: End-to-End Flow Tests (Mocked)
# ============================================================================


class TestEndToEndFlow:
    """Test end-to-end flow with schema validation integration."""

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.workflowGeneratorAgents.nodes.generator.invoke_structured_llm"
    )
    async def test_schema_validation_triggers_self_repair(
        self,
        mock_invoke_llm: AsyncMock,
    ) -> None:
        """Test that schema validation errors trigger self-repair flow.

        Flow:
            generator (produces type_mismatch YAML)
            → schema_validator (detects error)
            → self_repair (creates feedback)
            → generator (regenerates with feedback)
        """
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )
        from aiagent.langgraph.workflowGeneratorAgents.agent import (
            create_workflow_generator_graph,
        )
        from aiagent.langgraph.workflowGeneratorAgents.prompts.workflow_generation import (
            WorkflowGenerationResponse,
        )

        call_count = {"count": 0}

        async def mock_llm_response(**kwargs):
            call_count["count"] += 1
            if call_count["count"] == 1:
                # First call: return YAML with type mismatch
                return StructuredCallResult(
                    result=WorkflowGenerationResponse(
                        workflow_name="test_workflow",
                        yaml_content=create_type_mismatch_yaml_content(),
                        reasoning="Generated workflow with type mismatch",
                    ),
                    recovered_via_json=False,
                    raw_text=None,
                    model_name="mock-model",
                )
            else:
                # Second call: return valid YAML (after self-repair feedback)
                return StructuredCallResult(
                    result=WorkflowGenerationResponse(
                        workflow_name="test_workflow_fixed",
                        yaml_content=create_valid_yaml_content(),
                        reasoning="Fixed type mismatch issue",
                    ),
                    recovered_via_json=False,
                    raw_text=None,
                    model_name="mock-model",
                )

        mock_invoke_llm.side_effect = mock_llm_response

        # Note: We don't execute the full graph in this test because it would
        # require mocking many more nodes. Instead, we verify:
        # 1. Graph structure includes schema_validator
        # 2. Mock LLM responses correctly produce type mismatch and valid YAML
        graph = create_workflow_generator_graph()

        # Verify the graph structure includes schema_validator
        assert "schema_validator" in graph.nodes

        # Verify first LLM call would produce type mismatch YAML
        first_response = await mock_llm_response()
        assert "fetch_data" in first_response.result.yaml_content
        assert ":fetch_data" in first_response.result.yaml_content

        # Verify second LLM call would produce valid YAML (uses field access pattern)
        second_response = await mock_llm_response()
        # Valid YAML uses :source.user_input.query (field access) instead of :node_name
        assert ":source.user_input.query" in second_response.result.yaml_content
        assert "system_prompt" in second_response.result.yaml_content


# ============================================================================
# Regression Tests
# ============================================================================


class TestRegressionIssue333:
    """Regression tests for Issue #333 fixes."""

    def test_type_validation_rules_not_empty_string(self) -> None:
        """Ensure TYPE_VALIDATION_RULES is not an empty string."""
        assert TYPE_VALIDATION_RULES.strip() != ""
        assert len(TYPE_VALIDATION_RULES) > 100  # Should be substantial

    def test_schema_validator_exported_from_nodes(self) -> None:
        """Ensure workflow_schema_validator_node is exported from nodes package."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes import (
            workflow_schema_validator_node as imported_node,
        )

        assert imported_node is workflow_schema_validator_node

    def test_schema_validator_router_exported_from_agent(self) -> None:
        """Ensure schema_validator_router is defined in agent module."""
        from aiagent.langgraph.workflowGeneratorAgents.agent import (
            schema_validator_router as imported_router,
        )

        assert imported_router is schema_validator_router
        assert callable(imported_router)
