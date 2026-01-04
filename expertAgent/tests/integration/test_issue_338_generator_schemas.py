"""Integration tests for Issue #338 - generator.py API schema injection.

These tests verify that get_api_response_schemas is actually CALLED
in the generator node flow, not just that it exists.

Issue #338: Dead code detection - get_api_response_schemas must be called.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aiagent.langgraph.workflowGeneratorAgents.nodes.generator import generator_node
from aiagent.langgraph.workflowGeneratorAgents.prompts.workflow_generation import (
    create_workflow_generation_prompt,
    create_workflow_generation_prompt_with_feedback,
)


@pytest.mark.integration
class TestGeneratorSchemaInjectionIntegration:
    """Integration tests verifying get_api_response_schemas is called in generator."""

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.workflowGeneratorAgents.nodes.generator.invoke_structured_llm"
    )
    @patch(
        "aiagent.langgraph.workflowGeneratorAgents.nodes.generator.get_api_response_schemas"
    )
    @patch(
        "aiagent.langgraph.workflowGeneratorAgents.nodes.generator._load_capabilities"
    )
    async def test_get_api_response_schemas_is_called_when_recommended_apis_exist(
        self, mock_load_capabilities, mock_get_schemas, mock_invoke_llm
    ):
        """Verify that get_api_response_schemas is called when task_data has recommended_apis.

        This test ensures the function is not dead code but actually integrated
        into the generator node's execution flow.
        """
        # Setup mocks
        mock_load_capabilities.return_value = (
            {"agents": []},
            {"utility_apis": [], "ai_agent_apis": []},
        )
        mock_get_schemas.return_value = {
            "/v1/utility/google_search": {
                "response_schema": {
                    "results": {"type": "array"},
                    "count": {"type": "integer"},
                }
            }
        }

        # Mock LLM response
        from aiagent.langgraph.workflowGeneratorAgents.prompts.workflow_generation import (
            WorkflowGenerationResponse,
        )
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=WorkflowGenerationResponse(
                workflow_name="test_workflow",
                yaml_content="version: 0.5\nnodes:\n  source: {}",
                reasoning="Test reasoning",
            ),
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

        # Create state with recommended_apis
        state = {
            "task_data": {
                "name": "Test Task",
                "description": "Test description",
                "recommended_apis": ["/v1/utility/google_search"],
                "input_interface": {"schema": {}},
                "output_interface": {"schema": {}},
            },
            "error_feedback": None,
        }

        # Execute generator node
        result = await generator_node(state)

        # Verify get_api_response_schemas was called with recommended_apis
        mock_get_schemas.assert_called_once_with(["/v1/utility/google_search"])

        # Verify result is successful
        assert result["status"] == "yaml_generated"

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.workflowGeneratorAgents.nodes.generator.invoke_structured_llm"
    )
    @patch(
        "aiagent.langgraph.workflowGeneratorAgents.nodes.generator.get_api_response_schemas"
    )
    @patch(
        "aiagent.langgraph.workflowGeneratorAgents.nodes.generator._load_capabilities"
    )
    async def test_generator_continues_if_schema_retrieval_fails(
        self, mock_load_capabilities, mock_get_schemas, mock_invoke_llm
    ):
        """Verify generator continues even if get_api_response_schemas fails."""
        # Setup mocks
        mock_load_capabilities.return_value = (
            {"agents": []},
            {"utility_apis": [], "ai_agent_apis": []},
        )
        mock_get_schemas.side_effect = Exception("Schema retrieval failed")

        # Mock LLM response
        from aiagent.langgraph.workflowGeneratorAgents.prompts.workflow_generation import (
            WorkflowGenerationResponse,
        )
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=WorkflowGenerationResponse(
                workflow_name="test_workflow",
                yaml_content="version: 0.5\nnodes:\n  source: {}",
                reasoning="Test reasoning",
            ),
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

        state = {
            "task_data": {
                "name": "Test Task",
                "description": "Test description",
                "recommended_apis": ["/v1/utility/google_search"],
                "input_interface": {"schema": {}},
                "output_interface": {"schema": {}},
            },
            "error_feedback": None,
        }

        # Should not raise - generator should continue without schemas
        result = await generator_node(state)

        # Verify get_api_response_schemas was attempted
        mock_get_schemas.assert_called_once()

        # Generator should still succeed
        assert result["status"] == "yaml_generated"


@pytest.mark.integration
class TestPromptApiSchemasParameter:
    """Tests for api_schemas parameter in prompt generation functions."""

    def test_create_workflow_generation_prompt_accepts_api_schemas(self):
        """Test that create_workflow_generation_prompt accepts api_schemas parameter."""
        task_data = {
            "name": "Test Task",
            "description": "Test description",
            "input_interface": {"schema": {}},
            "output_interface": {"schema": {}},
        }
        graphai_capabilities = {"agents": []}
        expert_agent_capabilities = {"utility_apis": [], "ai_agent_apis": []}
        api_schemas = {
            "/v1/utility/google_search": {
                "response_schema": {"results": {"type": "array"}}
            }
        }

        # Should not raise - api_schemas parameter should be accepted
        prompt = create_workflow_generation_prompt(
            task_data,
            graphai_capabilities,
            expert_agent_capabilities,
            api_schemas=api_schemas,
        )

        # Prompt should be a string
        assert isinstance(prompt, str)
        # API schema info should be included in prompt
        assert "google_search" in prompt or "API" in prompt

    def test_create_workflow_generation_prompt_with_feedback_accepts_api_schemas(self):
        """Test that create_workflow_generation_prompt_with_feedback accepts api_schemas."""
        task_data = {
            "name": "Test Task",
            "description": "Test description",
            "input_interface": {"schema": {}},
            "output_interface": {"schema": {}},
        }
        graphai_capabilities = {"agents": []}
        expert_agent_capabilities = {"utility_apis": [], "ai_agent_apis": []}
        error_feedback = "Previous error message"
        api_schemas = {
            "/v1/utility/google_search": {
                "response_schema": {"results": {"type": "array"}}
            }
        }

        # Should not raise - api_schemas parameter should be accepted
        prompt = create_workflow_generation_prompt_with_feedback(
            task_data,
            graphai_capabilities,
            expert_agent_capabilities,
            error_feedback,
            api_schemas=api_schemas,
        )

        assert isinstance(prompt, str)
