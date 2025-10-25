"""Unit tests for evaluator_node.

These tests verify the evaluator node's behavior including:
- Valid task breakdown evaluation (all quality scores high)
- Invalid task breakdown (low quality scores)
- Infeasible tasks detection and proposals
- Alternative solutions using existing APIs
- API extension proposals
- Empty task breakdown error handling
- LLM error handling
- Retry count reset behavior

Issue #111: Comprehensive test coverage for all workflow nodes.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator import evaluator_node
from aiagent.langgraph.jobTaskGeneratorAgents.prompts.evaluation import (
    AlternativeProposal,
    APIExtensionProposal,
    EvaluationResult,
    InfeasibleTask,
)
from tests.utils.mock_helpers import (
    create_mock_task_breakdown,
    create_mock_workflow_state,
)


@pytest.mark.unit
class TestEvaluatorNode:
    """Unit tests for evaluator_node."""

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.create_llm_with_fallback"
    )
    async def test_evaluator_valid_task_breakdown(self, mock_create_llm):
        """Test evaluation with valid task breakdown (high quality scores).

        Priority: High
        This is the happy path where all quality criteria are met.
        """
        # Create mock evaluation result (all valid)
        mock_response = EvaluationResult(
            is_valid=True,
            evaluation_summary="All quality criteria met. Tasks are well-structured and feasible.",
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

        # Setup mock LLM
        mock_llm = AsyncMock()
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        # Setup mock performance and cost trackers
        mock_perf_tracker = MagicMock()
        mock_cost_tracker = MagicMock()
        mock_create_llm.return_value = (mock_llm, mock_perf_tracker, mock_cost_tracker)

        # Create test state
        task_breakdown = create_mock_task_breakdown(3)
        state = create_mock_workflow_state(
            retry_count=2,  # Should be reset to 0
            user_requirement="Create a data analysis workflow",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )

        # Execute node
        result = await evaluator_node(state)

        # Verify results
        assert "evaluation_result" in result
        assert result["evaluation_result"]["is_valid"] is True
        assert result["evaluation_result"]["hierarchical_score"] == 9
        assert result["evaluation_result"]["dependency_score"] == 9
        assert result["evaluation_result"]["all_tasks_feasible"] is True
        assert len(result["evaluation_result"]["infeasible_tasks"]) == 0

        # Verify retry_count is reset to 0 on success
        assert result["retry_count"] == 0, (
            "retry_count should be reset to 0 after successful evaluation"
        )

        # evaluation_feedback should be None for valid results
        assert result.get("evaluation_feedback") is None

        # Verify LLM was called
        mock_structured.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.create_llm_with_fallback"
    )
    async def test_evaluator_invalid_with_low_scores(self, mock_create_llm):
        """Test evaluation with invalid task breakdown (low quality scores).

        Priority: High
        This tests when quality scores are below threshold.
        """
        # Create mock evaluation result (invalid - low scores)
        mock_response = EvaluationResult(
            is_valid=False,
            evaluation_summary="Quality scores are below threshold. Tasks need improvement.",
            hierarchical_score=4,
            dependency_score=5,
            specificity_score=3,
            modularity_score=4,
            consistency_score=5,
            all_tasks_feasible=True,
            infeasible_tasks=[],
            alternative_proposals=[],
            api_extension_proposals=[],
            issues=[
                "Task descriptions are too vague",
                "Dependencies are not clearly defined",
            ],
            improvement_suggestions=[
                "Add more specific input/output definitions",
                "Clarify task dependencies",
            ],
        )

        # Setup mock LLM
        mock_llm = AsyncMock()
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        # Setup mock performance and cost trackers
        mock_perf_tracker = MagicMock()
        mock_cost_tracker = MagicMock()
        mock_create_llm.return_value = (mock_llm, mock_perf_tracker, mock_cost_tracker)

        # Create test state
        task_breakdown = create_mock_task_breakdown(3)
        state = create_mock_workflow_state(
            retry_count=1,
            user_requirement="Analyze sales data",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )

        # Execute node
        result = await evaluator_node(state)

        # Verify results
        assert result["evaluation_result"]["is_valid"] is False
        assert result["evaluation_result"]["hierarchical_score"] == 4
        assert result["evaluation_result"]["specificity_score"] == 3
        assert len(result["evaluation_result"]["issues"]) == 2
        assert len(result["evaluation_result"]["improvement_suggestions"]) == 2

        # Verify evaluation_feedback is generated for invalid results
        assert "evaluation_feedback" in result
        assert result["evaluation_feedback"] is not None
        assert "品質スコア" in result["evaluation_feedback"]
        assert "改善提案" in result["evaluation_feedback"]

        # Verify retry_count is reset to 0
        assert result["retry_count"] == 0

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.create_llm_with_fallback"
    )
    async def test_evaluator_with_infeasible_tasks(self, mock_create_llm):
        """Test evaluation with infeasible tasks detected.

        Priority: High
        This tests when some tasks cannot be implemented with current APIs.
        """
        # Create mock infeasible tasks
        infeasible_task = InfeasibleTask(
            task_id="task_002",
            task_name="Send SMS notification",
            reason="SMS API is not available in current expertAgent capabilities",
            required_functionality="SMS sending capability via direct API",
        )

        # Create mock evaluation result (with infeasible tasks)
        mock_response = EvaluationResult(
            is_valid=False,
            evaluation_summary="Some tasks are infeasible with current capabilities.",
            hierarchical_score=8,
            dependency_score=8,
            specificity_score=7,
            modularity_score=8,
            consistency_score=8,
            all_tasks_feasible=False,
            infeasible_tasks=[infeasible_task],
            alternative_proposals=[],
            api_extension_proposals=[],
            issues=["task_002 (Send SMS notification) is not feasible"],
            improvement_suggestions=["Consider using email instead of SMS"],
        )

        # Setup mock LLM
        mock_llm = AsyncMock()
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        # Setup mock performance and cost trackers
        mock_perf_tracker = MagicMock()
        mock_cost_tracker = MagicMock()
        mock_create_llm.return_value = (mock_llm, mock_perf_tracker, mock_cost_tracker)

        # Create test state
        task_breakdown = create_mock_task_breakdown(3)
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Send notifications via SMS",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )

        # Execute node
        result = await evaluator_node(state)

        # Verify infeasible tasks detection
        assert result["evaluation_result"]["is_valid"] is False
        assert result["evaluation_result"]["all_tasks_feasible"] is False
        assert len(result["evaluation_result"]["infeasible_tasks"]) == 1
        assert (
            result["evaluation_result"]["infeasible_tasks"][0]["task_id"] == "task_002"
        )
        assert (
            result["evaluation_result"]["infeasible_tasks"][0]["task_name"]
            == "Send SMS notification"
        )

        # Verify evaluation_feedback includes infeasible tasks
        assert "実現不可能なタスク" in result["evaluation_feedback"]
        assert "Send SMS notification" in result["evaluation_feedback"]

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.create_llm_with_fallback"
    )
    async def test_evaluator_with_alternative_proposals(self, mock_create_llm):
        """Test evaluation with alternative proposals using existing APIs.

        Priority: Medium
        This tests when alternative solutions are proposed.
        """
        # Create mock alternative proposal
        alternative = AlternativeProposal(
            task_id="task_002",
            alternative_approach="Use Gmail API to send email instead of SMS",
            api_to_use="gmail_send_email",
            implementation_note="Use Gmail API to send email notifications instead of SMS",
        )

        # Create mock evaluation result (with alternatives)
        mock_response = EvaluationResult(
            is_valid=False,
            evaluation_summary="Alternative approaches proposed using existing APIs.",
            hierarchical_score=8,
            dependency_score=8,
            specificity_score=7,
            modularity_score=8,
            consistency_score=8,
            all_tasks_feasible=False,
            infeasible_tasks=[],
            alternative_proposals=[alternative],
            api_extension_proposals=[],
            issues=["SMS API not available"],
            improvement_suggestions=["Use email instead"],
        )

        # Setup mock LLM
        mock_llm = AsyncMock()
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        # Setup mock performance and cost trackers
        mock_perf_tracker = MagicMock()
        mock_cost_tracker = MagicMock()
        mock_create_llm.return_value = (mock_llm, mock_perf_tracker, mock_cost_tracker)

        # Create test state
        task_breakdown = create_mock_task_breakdown(3)
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Send notifications",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )

        # Execute node
        result = await evaluator_node(state)

        # Verify alternative proposals
        assert len(result["evaluation_result"]["alternative_proposals"]) == 1
        assert (
            result["evaluation_result"]["alternative_proposals"][0]["task_id"]
            == "task_002"
        )
        assert (
            result["evaluation_result"]["alternative_proposals"][0]["api_to_use"]
            == "gmail_send_email"
        )

        # Verify evaluation_feedback includes alternatives
        assert "代替案の提案" in result["evaluation_feedback"]
        assert "gmail_send_email" in result["evaluation_feedback"]

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.create_llm_with_fallback"
    )
    async def test_evaluator_with_api_extension_proposals(self, mock_create_llm):
        """Test evaluation with API extension proposals.

        Priority: Medium
        This tests when new API features are proposed.
        """
        # Create mock API extension proposal
        api_extension = APIExtensionProposal(
            task_id="task_002",
            proposed_api_name="sms_send",
            functionality="Send SMS notifications to phone numbers",
            priority="high",
            rationale="Many users need SMS notifications for urgent alerts, which email cannot provide",
        )

        # Create mock evaluation result (with API extensions)
        mock_response = EvaluationResult(
            is_valid=False,
            evaluation_summary="API extensions proposed for missing functionality.",
            hierarchical_score=8,
            dependency_score=8,
            specificity_score=7,
            modularity_score=8,
            consistency_score=8,
            all_tasks_feasible=False,
            infeasible_tasks=[],
            alternative_proposals=[],
            api_extension_proposals=[api_extension],
            issues=["SMS functionality not available"],
            improvement_suggestions=["Add SMS API support"],
        )

        # Setup mock LLM
        mock_llm = AsyncMock()
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        # Setup mock performance and cost trackers
        mock_perf_tracker = MagicMock()
        mock_cost_tracker = MagicMock()
        mock_create_llm.return_value = (mock_llm, mock_perf_tracker, mock_cost_tracker)

        # Create test state
        task_breakdown = create_mock_task_breakdown(3)
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Send SMS notifications",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )

        # Execute node
        result = await evaluator_node(state)

        # Verify API extension proposals
        assert len(result["evaluation_result"]["api_extension_proposals"]) == 1
        assert (
            result["evaluation_result"]["api_extension_proposals"][0][
                "proposed_api_name"
            ]
            == "sms_send"
        )
        assert (
            result["evaluation_result"]["api_extension_proposals"][0]["priority"]
            == "high"
        )

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.create_llm_with_fallback"
    )
    async def test_evaluator_empty_task_breakdown(self, mock_create_llm):
        """Test error handling when task_breakdown is empty.

        Priority: Medium
        This tests edge case where no tasks are provided.
        """
        # Setup mock LLM (won't be called due to empty check)
        mock_llm = AsyncMock()
        # Setup mock performance and cost trackers
        mock_perf_tracker = MagicMock()
        mock_cost_tracker = MagicMock()
        mock_create_llm.return_value = (mock_llm, mock_perf_tracker, mock_cost_tracker)

        # Create test state with empty task_breakdown
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Some requirement",
            task_breakdown=[],  # Empty
            evaluator_stage="after_task_breakdown",
        )

        # Execute node
        result = await evaluator_node(state)

        # Verify error handling
        assert "error_message" in result
        assert "Task breakdown is required for evaluation" in result["error_message"]
        assert result["evaluation_result"] is None

        # Verify LLM was NOT called (early return)
        mock_llm.with_structured_output.assert_not_called()

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.create_llm_with_fallback"
    )
    async def test_evaluator_llm_error(self, mock_create_llm):
        """Test error handling when LLM invocation fails.

        Priority: Medium
        This tests exception handling.
        """
        # Setup mock LLM to raise exception
        mock_llm = AsyncMock()
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(side_effect=Exception("LLM API timeout"))
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        # Setup mock performance and cost trackers
        mock_perf_tracker = MagicMock()
        mock_cost_tracker = MagicMock()
        mock_create_llm.return_value = (mock_llm, mock_perf_tracker, mock_cost_tracker)

        # Create test state
        task_breakdown = create_mock_task_breakdown(3)
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Analyze data",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )

        # Execute node
        result = await evaluator_node(state)

        # Verify error handling
        assert "error_message" in result
        assert "Evaluation failed" in result["error_message"]
        # Note: Error message may be from recovery attempt rather than original exception
        assert (
            "LLM API timeout" in result["error_message"]
            or "Failed to extract JSON block" in result["error_message"]
        )

        # evaluation_result should not be in result
        assert "evaluation_result" not in result

        # Verify LLM was called
        mock_structured.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.evaluator.create_llm_with_fallback"
    )
    async def test_evaluator_retry_count_reset(self, mock_create_llm):
        """Test that retry_count is always reset to 0 after evaluation.

        Priority: Low
        This verifies the retry_count reset behavior.
        """
        # Create mock evaluation result
        mock_response = EvaluationResult(
            is_valid=True,
            evaluation_summary="Valid",
            hierarchical_score=8,
            dependency_score=8,
            specificity_score=8,
            modularity_score=8,
            consistency_score=8,
            all_tasks_feasible=True,
            infeasible_tasks=[],
            alternative_proposals=[],
            api_extension_proposals=[],
            issues=[],
            improvement_suggestions=[],
        )

        # Setup mock LLM
        mock_llm = AsyncMock()
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        # Setup mock performance and cost trackers
        mock_perf_tracker = MagicMock()
        mock_cost_tracker = MagicMock()
        mock_create_llm.return_value = (mock_llm, mock_perf_tracker, mock_cost_tracker)

        # Test Case 1: retry_count=3 should be reset to 0
        task_breakdown = create_mock_task_breakdown(2)
        state = create_mock_workflow_state(
            retry_count=3,
            user_requirement="Test requirement",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )
        result = await evaluator_node(state)
        assert result["retry_count"] == 0, (
            "retry_count should be reset to 0 regardless of previous value"
        )

        # Test Case 2: retry_count=0 should remain 0
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Test requirement",
            task_breakdown=task_breakdown,
            evaluator_stage="after_task_breakdown",
        )
        result = await evaluator_node(state)
        assert result["retry_count"] == 0
