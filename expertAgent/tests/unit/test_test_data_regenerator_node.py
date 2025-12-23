"""Unit tests for Test Data Regenerator Node.

This module tests the Test Data Regenerator node which regenerates
test data when the LLM Evaluator detects low-quality test data.
"""

from typing import Any
from unittest.mock import patch

import pytest

from aiagent.langgraph.workflowGeneratorAgents.state import WorkflowGeneratorState


@pytest.fixture
def base_state_needs_regeneration() -> WorkflowGeneratorState:
    """Create base state that needs test data regeneration."""
    return {
        "task_master_id": "tm_01ABC123",
        "task_data": {
            "name": "Get company information",
            "description": "Retrieve company information from database",
            "input_interface": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "company_name": {
                            "type": "string",
                            "description": "Company name to search",
                        },
                    },
                    "required": ["company_name"],
                },
            },
            "output_interface": {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "company_info": {"type": "object"},
                        "status": {"type": "string"},
                    },
                },
            },
            "recommended_apis": ["company_search_api"],
        },
        "max_retry": 3,
        "retry_count": 0,
        "yaml_content": "version: 0.5\nnodes:\n  source: {}\n",
        "workflow_name": "get_company_info",
        "sample_input": {"company_name": "sample_text"},  # Low quality
        "test_http_status": 200,
        "test_execution_result": {"results": {}, "errors": {}, "logs": []},
        "validation_result": {"is_valid": True, "issues": []},
        "validation_errors": [],
        "is_valid": True,
        "status": "validated",
        "max_test_data_regeneration": 2,
        "test_data_regeneration_count": 0,
        "needs_test_data_regeneration": True,
        "test_data_issues": [
            "Test data uses placeholder 'sample_text'",
            "Not realistic company name",
        ],
        "suggested_test_data": {"company_name": "Toyota Motor Corporation"},
    }


@pytest.fixture
def mock_regenerated_test_data() -> dict[str, Any]:
    """Create mock regenerated test data."""
    return {
        "sample_input": {"company_name": "Sony Corporation"},
        "generation_rationale": "Used realistic Japanese company name",
        "expected_behavior": "Should return company information for Sony",
    }


class TestTestDataRegeneratorNode:
    """Test test_data_regenerator_node."""

    @pytest.mark.asyncio
    async def test_test_data_regenerator_uses_suggested_data(
        self, base_state_needs_regeneration: WorkflowGeneratorState
    ):
        """Test that regenerator uses LLM suggested data when available."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.test_data_regenerator import (
            test_data_regenerator_node,
        )

        result = await test_data_regenerator_node(base_state_needs_regeneration)

        # Should use suggested_test_data
        assert result["sample_input"] == {"company_name": "Toyota Motor Corporation"}
        assert result["regenerated_sample_input"] == {
            "company_name": "Toyota Motor Corporation"
        }
        assert result["test_data_regeneration_count"] == 1
        assert result["needs_test_data_regeneration"] is False
        assert result["status"] == "test_data_regenerated"

    @pytest.mark.asyncio
    async def test_test_data_regenerator_llm_generation(
        self,
        base_state_needs_regeneration: WorkflowGeneratorState,
        mock_regenerated_test_data: dict[str, Any],
    ):
        """Test that regenerator calls LLM when no suggested data available."""
        from aiagent.langgraph.workflowGeneratorAgents.models.evaluation import (
            RegeneratedTestData,
        )
        from aiagent.langgraph.workflowGeneratorAgents.nodes.test_data_regenerator import (
            test_data_regenerator_node,
        )

        state_no_suggestion = {
            **base_state_needs_regeneration,
            "suggested_test_data": None,
        }

        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.test_data_regenerator._call_llm_regenerator"
        ) as mock_call:
            mock_call.return_value = RegeneratedTestData(**mock_regenerated_test_data)

            result = await test_data_regenerator_node(state_no_suggestion)

            mock_call.assert_called_once()
            assert result["sample_input"] == {"company_name": "Sony Corporation"}
            assert result["test_data_regeneration_count"] == 1

    @pytest.mark.asyncio
    async def test_test_data_regenerator_max_count_reached(
        self, base_state_needs_regeneration: WorkflowGeneratorState
    ):
        """Test that regenerator stops when max count is reached."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.test_data_regenerator import (
            test_data_regenerator_node,
        )

        state_max_reached = {
            **base_state_needs_regeneration,
            "test_data_regeneration_count": 2,
            "max_test_data_regeneration": 2,
        }

        result = await test_data_regenerator_node(state_max_reached)

        # Should not regenerate, count should stay at 2
        assert result["test_data_regeneration_count"] == 2
        assert result["needs_test_data_regeneration"] is False
        assert result["status"] == "test_data_regeneration_exhausted"

    @pytest.mark.asyncio
    async def test_test_data_regenerator_increments_count(
        self, base_state_needs_regeneration: WorkflowGeneratorState
    ):
        """Test that regeneration count is incremented correctly."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.test_data_regenerator import (
            test_data_regenerator_node,
        )

        # First regeneration
        result1 = await test_data_regenerator_node(base_state_needs_regeneration)
        assert result1["test_data_regeneration_count"] == 1

        # Second regeneration
        state_second = {
            **base_state_needs_regeneration,
            "test_data_regeneration_count": 1,
            "suggested_test_data": {"company_name": "Honda Motor"},
        }
        result2 = await test_data_regenerator_node(state_second)
        assert result2["test_data_regeneration_count"] == 2

    @pytest.mark.asyncio
    async def test_test_data_regenerator_handles_llm_error(
        self, base_state_needs_regeneration: WorkflowGeneratorState
    ):
        """Test that regenerator handles LLM errors gracefully."""
        from aiagent.langgraph.workflowGeneratorAgents.nodes.test_data_regenerator import (
            test_data_regenerator_node,
        )

        state_no_suggestion = {
            **base_state_needs_regeneration,
            "suggested_test_data": None,
        }

        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.test_data_regenerator._call_llm_regenerator"
        ) as mock_call:
            mock_call.side_effect = Exception("LLM API error")

            result = await test_data_regenerator_node(state_no_suggestion)

            # Should handle error gracefully
            assert "status" in result
            # Count should still be incremented to prevent infinite loops
            assert (
                result.get("test_data_regeneration_count", 0)
                >= base_state_needs_regeneration["test_data_regeneration_count"]
            )


class TestRegeneratedTestDataModel:
    """Test RegeneratedTestData model."""

    def test_regenerated_test_data_validation(self):
        """Test RegeneratedTestData field validation."""
        from aiagent.langgraph.workflowGeneratorAgents.models.evaluation import (
            RegeneratedTestData,
        )

        data = RegeneratedTestData(
            sample_input={"company_name": "Toyota"},
            generation_rationale="Used realistic company name: Toyota Motor Corporation",
            expected_behavior="Should return company information",
        )

        assert data.sample_input == {"company_name": "Toyota"}
        assert "Toyota" in data.generation_rationale

    def test_regenerated_test_data_empty_sample_input(self):
        """Test RegeneratedTestData with empty sample input."""
        from aiagent.langgraph.workflowGeneratorAgents.models.evaluation import (
            RegeneratedTestData,
        )

        # Empty sample_input should still be valid (for edge cases)
        data = RegeneratedTestData(
            sample_input={},
            generation_rationale="No input required",
            expected_behavior="Default behavior",
        )

        assert data.sample_input == {}
