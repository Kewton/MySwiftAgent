"""Unit tests for LLM Evaluator Routers.

This module tests the routing logic for the LLM Evaluator flow,
including the 3-way routing from llm_evaluator_node.
"""

import pytest

from aiagent.langgraph.workflowGeneratorAgents.state import WorkflowGeneratorState


@pytest.fixture
def base_state() -> WorkflowGeneratorState:
    """Create base state for testing."""
    return {
        "task_master_id": "tm_01ABC123",
        "task_data": {
            "name": "Test Task",
            "description": "Test description",
            "input_interface": {"type": "json_schema", "schema": {}},
            "output_interface": {"type": "json_schema", "schema": {}},
        },
        "max_retry": 3,
        "retry_count": 0,
        "yaml_content": "version: 0.5\nnodes: {}",
        "workflow_name": "test_workflow",
        "sample_input": {"test": "data"},
        "test_http_status": 200,
        "test_execution_result": {"results": {"output": {}}, "errors": {}, "logs": []},
        "validation_result": {"is_valid": True, "issues": []},
        "validation_errors": [],
        "is_valid": True,
        "status": "validated",
        "max_test_data_regeneration": 2,
        "test_data_regeneration_count": 0,
        "needs_test_data_regeneration": False,
        "evaluation_score": 85,
        "llm_evaluation_result": {
            "overall_score": 85,
            "failure_reason": "none",
        },
    }


class TestLLMEvaluatorRouter:
    """Test llm_evaluator_router."""

    def test_router_to_result_summary_on_success(
        self, base_state: WorkflowGeneratorState
    ):
        """Test routing to result_summary_generator on success."""
        from aiagent.langgraph.workflowGeneratorAgents.agent import llm_evaluator_router

        result = llm_evaluator_router(base_state)
        assert result == "result_summary_generator"

    def test_router_to_test_data_regenerator_on_low_test_quality(
        self, base_state: WorkflowGeneratorState
    ):
        """Test routing to test_data_regenerator on low test data quality."""
        from aiagent.langgraph.workflowGeneratorAgents.agent import llm_evaluator_router

        state_low_test_quality = {
            **base_state,
            "needs_test_data_regeneration": True,
            "test_data_regeneration_count": 0,
            "max_test_data_regeneration": 2,
            "llm_evaluation_result": {
                "overall_score": 60,
                "failure_reason": "test_data_quality",
            },
        }

        result = llm_evaluator_router(state_low_test_quality)
        assert result == "test_data_regenerator"

    def test_router_to_self_repair_on_workflow_quality_issue(
        self, base_state: WorkflowGeneratorState
    ):
        """Test routing to self_repair on workflow quality issue."""
        from aiagent.langgraph.workflowGeneratorAgents.agent import llm_evaluator_router

        state_workflow_issue = {
            **base_state,
            "is_valid": False,
            "needs_test_data_regeneration": False,
            "evaluation_score": 50,
            "llm_evaluation_result": {
                "overall_score": 50,
                "failure_reason": "workflow_quality",
            },
        }

        result = llm_evaluator_router(state_workflow_issue)
        assert result == "self_repair"

    def test_router_to_self_repair_on_rule_validation_failure(
        self, base_state: WorkflowGeneratorState
    ):
        """Test routing to self_repair on rule-based validation failure."""
        from aiagent.langgraph.workflowGeneratorAgents.agent import llm_evaluator_router

        state_rule_failure = {
            **base_state,
            "is_valid": False,
            "validation_errors": ["YAML syntax error"],
            "needs_test_data_regeneration": False,
        }

        result = llm_evaluator_router(state_rule_failure)
        assert result == "self_repair"

    def test_router_skips_regeneration_at_max_count(
        self, base_state: WorkflowGeneratorState
    ):
        """Test that router skips regeneration when max count reached."""
        from aiagent.langgraph.workflowGeneratorAgents.agent import llm_evaluator_router

        state_max_regen = {
            **base_state,
            "needs_test_data_regeneration": True,
            "test_data_regeneration_count": 2,
            "max_test_data_regeneration": 2,
            "is_valid": True,
            "evaluation_score": 85,
            "llm_evaluation_result": {
                "overall_score": 85,
                "failure_reason": "none",
            },
        }

        result = llm_evaluator_router(state_max_regen)
        # Should go to result_summary since regeneration count is at max
        assert result == "result_summary_generator"

    def test_router_to_self_repair_on_low_evaluation_score(
        self, base_state: WorkflowGeneratorState
    ):
        """Test routing to self_repair when evaluation score is below threshold."""
        from aiagent.langgraph.workflowGeneratorAgents.agent import llm_evaluator_router

        state_low_score = {
            **base_state,
            "is_valid": True,  # Rule-based validation passed
            "needs_test_data_regeneration": False,
            "evaluation_score": 50,  # Below 70 threshold
            "llm_evaluation_result": {
                "overall_score": 50,
                "failure_reason": "workflow_quality",
            },
        }

        result = llm_evaluator_router(state_low_score)
        assert result == "self_repair"

    def test_router_handles_both_failure_reason(
        self, base_state: WorkflowGeneratorState
    ):
        """Test routing when failure_reason is 'both'."""
        from aiagent.langgraph.workflowGeneratorAgents.agent import llm_evaluator_router

        state_both_issues = {
            **base_state,
            "is_valid": True,
            "needs_test_data_regeneration": True,
            "test_data_regeneration_count": 0,
            "evaluation_score": 40,
            "llm_evaluation_result": {
                "overall_score": 40,
                "failure_reason": "both",
            },
        }

        result = llm_evaluator_router(state_both_issues)
        # Should prioritize test data regeneration first
        assert result == "test_data_regenerator"


class TestTestDataRegeneratorRouter:
    """Test test_data_regenerator_router."""

    def test_router_always_to_workflow_tester(self, base_state: WorkflowGeneratorState):
        """Test that router always goes to workflow_tester."""
        from aiagent.langgraph.workflowGeneratorAgents.agent import (
            test_data_regenerator_router,
        )

        # After regenerating test data, should always go back to workflow_tester
        result = test_data_regenerator_router(base_state)
        assert result == "workflow_tester"

    def test_router_to_workflow_tester_after_regeneration(
        self, base_state: WorkflowGeneratorState
    ):
        """Test routing to workflow_tester after test data regeneration."""
        from aiagent.langgraph.workflowGeneratorAgents.agent import (
            test_data_regenerator_router,
        )

        state_regenerated = {
            **base_state,
            "test_data_regeneration_count": 1,
            "regenerated_sample_input": {"test": "new_data"},
            "status": "test_data_regenerated",
        }

        result = test_data_regenerator_router(state_regenerated)
        assert result == "workflow_tester"


class TestValidatorRouterUpdate:
    """Test updated validator_router for LLM Evaluator integration."""

    def test_validator_router_to_llm_evaluator(
        self, base_state: WorkflowGeneratorState
    ):
        """Test that validator routes to llm_evaluator instead of END."""
        from aiagent.langgraph.workflowGeneratorAgents.agent import validator_router

        state_valid = {
            **base_state,
            "is_valid": True,
            "validation_errors": [],
        }

        result = validator_router(state_valid)
        # Should now route to llm_evaluator instead of END
        assert result == "llm_evaluator"

    def test_validator_router_to_llm_evaluator_on_failure(
        self, base_state: WorkflowGeneratorState
    ):
        """Test that validator routes to llm_evaluator even on failure for evaluation."""
        from aiagent.langgraph.workflowGeneratorAgents.agent import validator_router

        state_invalid = {
            **base_state,
            "is_valid": False,
            "validation_errors": ["Some error"],
        }

        result = validator_router(state_invalid)
        # Should route to llm_evaluator for comprehensive evaluation
        assert result == "llm_evaluator"
