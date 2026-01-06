"""Integration tests for Issue #338 Phase 4 - Critical Weakness Routing.

These tests verify that critical weakness detection is properly integrated
into the workflow generator routing flow.

Issue #338: Evaluation routing improvements (真因2-A, 2-B).
"""

from unittest.mock import patch

import pytest

from aiagent.langgraph.workflowGeneratorAgents.agent import llm_evaluator_router
from aiagent.langgraph.workflowGeneratorAgents.models.evaluation import (
    LLMEvaluationResult,
)
from aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator import (
    _has_critical_weakness,
    llm_evaluator_node,
)
from aiagent.langgraph.workflowGeneratorAgents.state import WorkflowGeneratorState


@pytest.fixture
def base_workflow_state() -> WorkflowGeneratorState:
    """Create base state for workflow generator testing."""
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
        "fast_mode": False,
        # Issue #338: New fields
        "is_acceptable": True,
        "has_critical_weakness": False,
        "critical_issues": [],
    }


@pytest.mark.integration
class TestCriticalWeaknessIntegration:
    """Integration tests verifying critical weakness detection flows through routing."""

    @pytest.mark.asyncio
    async def test_critical_weakness_detected_and_routed_to_self_repair(
        self, base_workflow_state: WorkflowGeneratorState
    ):
        """Test full flow: LLM returns critical weakness -> routing to self_repair.

        This test simulates Issue #338 root cause 2-A:
        - LLM evaluation returns weaknesses containing 'Critical'
        - failure_reason is 'none' (LLM didn't set it)
        - overall_score is 72 (above threshold)
        - Result: should still route to self_repair due to critical detection
        """
        # LLM evaluation result simulating root cause 2-A
        llm_response = LLMEvaluationResult(
            overall_score=72,  # Above 70 threshold
            structural_score=75,
            requirement_score=70,
            output_quality_score=70,
            error_handling_score=70,
            test_data_quality_score=60,
            test_data_issues=[],
            needs_test_data_regeneration=False,
            suggested_test_data=None,
            strengths=["Good basic structure"],
            weaknesses=["Critical: Output node missing search_results field"],
            suggestions=["Add search_results to output"],
            is_acceptable=True,  # LLM says acceptable
            failure_reason="none",  # LLM didn't set failure
            confidence=0.75,
        )

        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator._call_llm_evaluator"
        ) as mock_llm:
            mock_llm.return_value = llm_response

            # Step 1: Execute llm_evaluator_node
            result_state = await llm_evaluator_node(base_workflow_state)

            # Verify critical weakness was detected
            assert result_state["has_critical_weakness"] is True
            assert "Critical" in result_state["critical_issues"][0]
            assert result_state["is_acceptable"] is False  # Due to critical

            # Step 2: Execute router with updated state
            routing_result = llm_evaluator_router(result_state)

            # Should route to self_repair due to critical weakness
            assert routing_result == "self_repair"

    @pytest.mark.asyncio
    async def test_is_acceptable_false_routed_to_self_repair(
        self, base_workflow_state: WorkflowGeneratorState
    ):
        """Test full flow: is_acceptable=False -> routing to self_repair.

        This test simulates Issue #338 root cause 2-B:
        - LLM evaluation returns test_data_quality_score=25 (below 50)
        - is_acceptable is calculated as False
        - overall_score is 72 (above threshold)
        - Result: should route to self_repair due to is_acceptable=False
        """
        # LLM evaluation result simulating root cause 2-B
        llm_response = LLMEvaluationResult(
            overall_score=72,  # Above 70 threshold
            structural_score=80,
            requirement_score=75,
            output_quality_score=70,
            error_handling_score=70,
            test_data_quality_score=25,  # Below 50 threshold
            test_data_issues=["Test data uses placeholder 'sample_text'"],
            needs_test_data_regeneration=False,  # Already max retries
            suggested_test_data=None,
            strengths=["Good structure"],
            weaknesses=["Low quality test data"],  # No 'Critical' keyword
            suggestions=["Use realistic test data"],
            is_acceptable=False,  # LLM says not acceptable
            failure_reason="test_data_quality",
            confidence=0.70,
        )

        state_at_max_regen = {
            **base_workflow_state,
            "test_data_regeneration_count": 2,  # At max
            "max_test_data_regeneration": 2,
        }

        with patch(
            "aiagent.langgraph.workflowGeneratorAgents.nodes.llm_evaluator._call_llm_evaluator"
        ) as mock_llm:
            mock_llm.return_value = llm_response

            # Step 1: Execute llm_evaluator_node
            result_state = await llm_evaluator_node(state_at_max_regen)

            # Verify is_acceptable was set correctly
            assert result_state["is_acceptable"] is False
            assert result_state["has_critical_weakness"] is False  # No critical keyword

            # Step 2: Execute router with updated state
            routing_result = llm_evaluator_router(result_state)

            # Should route to self_repair due to is_acceptable=False
            assert routing_result == "self_repair"


@pytest.mark.integration
class TestCriticalWeaknessDetectionPatterns:
    """Integration tests for critical weakness pattern detection."""

    def test_critical_patterns_in_real_evaluation_scenarios(self):
        """Test detection of various critical weakness patterns."""
        # Real-world weakness messages from Issue #338
        test_cases = [
            (
                ["Critical: Missing output node with search_results"],
                True,
                "English Critical pattern",
            ),
            (
                ["致命的: 出力ノードにsearch_resultsがありません"],
                True,
                "Japanese critical pattern",
            ),
            (
                ["重大な問題: インターフェース契約違反"],
                True,
                "Japanese severe pattern",
            ),
            (
                ["CRITICAL: Schema validation failed"],
                True,
                "Uppercase CRITICAL pattern",
            ),
            (
                ["Warning: Consider adding error handling"],
                False,
                "Warning only - not critical",
            ),
            (
                [
                    "Minor: Improve naming conventions",
                    "Info: Documentation could be better",
                ],
                False,
                "Minor/Info only - not critical",
            ),
            (
                [
                    "Warning: Output format could be improved",
                    "Critical: Required field missing",
                    "Suggestion: Add validation",
                ],
                True,
                "Mixed with critical",
            ),
        ]

        for weaknesses, expected_critical, description in test_cases:
            has_critical, issues = _has_critical_weakness(weaknesses)
            assert has_critical == expected_critical, (
                f"Failed for {description}: "
                f"expected {expected_critical}, got {has_critical}"
            )


@pytest.mark.integration
class TestRouterPriorityOrder:
    """Integration tests verifying router priority order."""

    def test_test_data_regeneration_takes_priority_over_critical(
        self, base_workflow_state: WorkflowGeneratorState
    ):
        """Test that test data regeneration takes priority over critical weakness."""
        state_needs_regen = {
            **base_workflow_state,
            "needs_test_data_regeneration": True,
            "test_data_regeneration_count": 0,  # Not at max
            "has_critical_weakness": True,  # Also has critical
            "critical_issues": ["Critical: Something wrong"],
        }

        result = llm_evaluator_router(state_needs_regen)

        # Should prioritize test data regeneration
        assert result == "test_data_regenerator"

    def test_rule_validation_takes_priority_over_critical(
        self, base_workflow_state: WorkflowGeneratorState
    ):
        """Test that rule-based validation failure takes priority over critical."""
        state_rule_failure = {
            **base_workflow_state,
            "is_valid": False,  # Rule validation failed
            "needs_test_data_regeneration": False,
            "has_critical_weakness": True,  # Also has critical
            "is_acceptable": True,
        }

        result = llm_evaluator_router(state_rule_failure)

        # Should route to self_repair due to is_valid=False
        assert result == "self_repair"

    def test_is_acceptable_checked_before_critical_weakness(
        self, base_workflow_state: WorkflowGeneratorState
    ):
        """Test that is_acceptable is checked before has_critical_weakness."""
        state_not_acceptable = {
            **base_workflow_state,
            "is_valid": True,
            "needs_test_data_regeneration": False,
            "is_acceptable": False,  # Not acceptable
            "has_critical_weakness": False,  # No critical
            "evaluation_score": 72,
        }

        result = llm_evaluator_router(state_not_acceptable)

        # Should route to self_repair due to is_acceptable=False
        assert result == "self_repair"

    def test_success_path_all_checks_pass(
        self, base_workflow_state: WorkflowGeneratorState
    ):
        """Test successful routing when all checks pass."""
        state_success = {
            **base_workflow_state,
            "is_valid": True,
            "needs_test_data_regeneration": False,
            "is_acceptable": True,
            "has_critical_weakness": False,
            "critical_issues": [],
            "evaluation_score": 85,
            "llm_evaluation_result": {
                "overall_score": 85,
                "failure_reason": "none",
            },
        }

        result = llm_evaluator_router(state_success)

        # Should route to success
        assert result == "result_summary_generator"
