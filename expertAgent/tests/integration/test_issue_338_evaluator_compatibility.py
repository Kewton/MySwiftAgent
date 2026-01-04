"""Integration tests for Issue #338 - evaluator.py compatibility check integration.

These tests verify that check_interface_compatibility is actually CALLED
in the evaluator node flow, not just that it exists.

Issue #338: Dead code detection - check_interface_compatibility must be called.
"""

from unittest.mock import patch

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator import (
    check_interface_compatibility,
    evaluator_node,
)
from aiagent.langgraph.jobTaskGeneratorAgents.prompts.evaluation import (
    EvaluationResult,
)
from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
    StructuredCallResult,
)


@pytest.mark.integration
class TestEvaluatorCompatibilityIntegration:
    """Integration tests verifying check_interface_compatibility is called in evaluator."""

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.invoke_structured_llm"
    )
    async def test_check_interface_compatibility_is_called_in_evaluator(
        self, mock_invoke_llm
    ):
        """Verify that check_interface_compatibility is called when interface_definitions exist.

        This test ensures the function is not dead code but actually integrated
        into the evaluator node's execution flow.
        """
        # Setup mock LLM response
        mock_eval_response = EvaluationResult(
            is_valid=True,
            evaluation_summary="Valid task breakdown.",
            hierarchical_score=9,
            dependency_score=9,
            specificity_score=9,
            modularity_score=8,
            consistency_score=9,
            all_tasks_feasible=True,
            infeasible_tasks=[],
            alternative_proposals=[],
            api_extension_proposals=[],
            issues=[],
            improvement_suggestions=[],
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=mock_eval_response,
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

        # Create test state with interface_definitions
        state = {
            "user_requirement": "Test workflow requirement",
            "task_breakdown": [
                {"task_id": "task_0", "name": "Search"},
                {"task_id": "task_1", "name": "Analyze"},
            ],
            "interface_definitions": {
                "task_0": {
                    "output_schema": {
                        "properties": {"results": {"type": "array"}},
                        "required": ["results"],
                    }
                },
                "task_1": {
                    "input_schema": {
                        "properties": {"results": {"type": "array"}},
                        "required": ["results"],
                    }
                },
            },
            "evaluator_stage": "after_interface_definition",
            "retry_count": 0,
        }

        # Execute evaluator node
        with patch(
            "aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.check_interface_compatibility"
        ) as mock_check:
            mock_check.return_value = []  # No warnings

            await evaluator_node(state)

            # Verify check_interface_compatibility was called
            mock_check.assert_called_once()

            # Verify the call arguments contain merged interface info
            call_args = mock_check.call_args[0][0]  # First positional arg
            assert len(call_args) == 2
            # Tasks should have interface info merged
            assert (
                "output_interface" in call_args[0] or "input_interface" in call_args[0]
            )

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.invoke_structured_llm"
    )
    async def test_interface_warnings_returned_in_state(self, mock_invoke_llm):
        """Verify that interface_warnings are included in returned state."""
        mock_eval_response = EvaluationResult(
            is_valid=True,
            evaluation_summary="Valid task breakdown.",
            hierarchical_score=9,
            dependency_score=9,
            specificity_score=9,
            modularity_score=8,
            consistency_score=9,
            all_tasks_feasible=True,
            infeasible_tasks=[],
            alternative_proposals=[],
            api_extension_proposals=[],
            issues=[],
            improvement_suggestions=[],
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=mock_eval_response,
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

        # Create state with incompatible interfaces
        state = {
            "user_requirement": "Test workflow requirement",
            "task_breakdown": [
                {"task_id": "task_0", "name": "Search"},
                {"task_id": "task_1", "name": "Analyze"},
            ],
            "interface_definitions": {
                "task_0": {
                    "output_schema": {
                        "properties": {"results": {"type": "array"}},
                        "required": ["results"],
                    }
                },
                "task_1": {
                    "input_schema": {
                        "properties": {"search_data": {"type": "array"}},  # Mismatch!
                        "required": ["search_data"],
                    }
                },
            },
            "evaluator_stage": "after_interface_definition",
            "retry_count": 0,
        }

        result = await evaluator_node(state)

        # Verify interface_warnings is in the returned state
        assert "interface_warnings" in result


@pytest.mark.integration
class TestCheckInterfaceCompatibilityFunction:
    """Direct tests for check_interface_compatibility function."""

    def test_detects_missing_required_field(self):
        """Test that missing required fields are detected."""
        tasks = [
            {
                "task_id": "task_0",
                "name": "Search",
                "output_interface": {
                    "properties": {"results": {"type": "array"}},
                },
            },
            {
                "task_id": "task_1",
                "name": "Analyze",
                "input_interface": {
                    "properties": {"data": {"type": "array"}},
                    "required": ["data"],  # Required but not in task_0's output
                },
            },
        ]

        warnings = check_interface_compatibility(tasks)

        assert len(warnings) > 0
        assert any("data" in w for w in warnings)

    def test_passes_compatible_interfaces(self):
        """Test that compatible interfaces produce no warnings."""
        tasks = [
            {
                "task_id": "task_0",
                "name": "Search",
                "output_interface": {
                    "properties": {
                        "results": {"type": "array"},
                        "count": {"type": "integer"},
                    },
                },
            },
            {
                "task_id": "task_1",
                "name": "Analyze",
                "input_interface": {
                    "properties": {"results": {"type": "array"}},
                    "required": ["results"],  # Provided by task_0
                },
            },
        ]

        warnings = check_interface_compatibility(tasks)

        assert len(warnings) == 0

    def test_handles_empty_task_list(self):
        """Test handling of empty or single-task lists."""
        assert check_interface_compatibility([]) == []
        assert check_interface_compatibility([{"task_id": "task_0"}]) == []
