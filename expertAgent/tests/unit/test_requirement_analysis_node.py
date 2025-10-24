"""Unit tests for requirement_analysis_node.

These tests verify the requirement analysis node's behavior including:
- Successful task breakdown with valid LLM responses
- Error handling for LLM failures
- Edge cases (empty tasks, invalid responses)
- Evaluation feedback integration
- Retry count management
- Missing required fields

Issue #111: Comprehensive test coverage for all workflow nodes.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis import (
    requirement_analysis_node,
)
from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
    TaskBreakdownItem,
    TaskBreakdownResponse,
)
from tests.utils.mock_helpers import create_mock_workflow_state


@pytest.mark.unit
class TestRequirementAnalysisNode:
    """Unit tests for requirement_analysis_node."""

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.create_llm_with_fallback"
    )
    async def test_requirement_analysis_success(self, mock_create_llm):
        """Test successful task breakdown with valid LLM response.

        Priority: High
        This is the happy path test case.
        """
        # Create mock LLM response
        mock_tasks = [
            TaskBreakdownItem(
                task_id="task_001",
                name="Search Gmail",
                description="Search Gmail for emails from sender X",
                dependencies=[],
                expected_output="List of email IDs matching criteria",
                priority=1,
            ),
            TaskBreakdownItem(
                task_id="task_002",
                name="Extract email content",
                description="Extract text content from each email",
                dependencies=["task_001"],
                expected_output="JSON with email content and metadata",
                priority=2,
            ),
            TaskBreakdownItem(
                task_id="task_003",
                name="Generate podcast script",
                description="Convert email content to podcast script",
                dependencies=["task_002"],
                expected_output="Markdown format podcast script",
                priority=3,
            ),
        ]
        mock_response = TaskBreakdownResponse(
            tasks=mock_tasks,
            overall_summary="3-step workflow: Search Gmail → Extract content → Generate podcast",
        )

        # Setup mock LLM
        mock_llm = AsyncMock()
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        mock_create_llm.return_value = (mock_llm, None, None)

        # Create test state
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Search Gmail and create podcast from emails",
        )

        # Execute node
        result = await requirement_analysis_node(state)

        # Verify results
        assert "task_breakdown" in result
        assert len(result["task_breakdown"]) == 3
        assert result["task_breakdown"][0]["task_id"] == "task_001"
        assert result["task_breakdown"][0]["name"] == "Search Gmail"
        assert result["task_breakdown"][1]["dependencies"] == ["task_001"]

        assert result["overall_summary"] == mock_response.overall_summary
        assert result["evaluator_stage"] == "after_task_breakdown"
        assert result["retry_count"] == 0  # Should remain 0 on first success

        # Verify LLM was called
        mock_structured.ainvoke.assert_called_once()
        call_args = mock_structured.ainvoke.call_args[0][0]
        assert len(call_args) == 2
        assert call_args[0]["role"] == "system"
        assert call_args[1]["role"] == "user"

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.create_llm_with_fallback"
    )
    async def test_requirement_analysis_with_llm_error(self, mock_create_llm):
        """Test error handling when LLM invocation fails.

        Priority: High
        This tests exception handling and error message propagation.
        """
        # Setup mock LLM to raise exception
        mock_llm = AsyncMock()
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(
            side_effect=Exception("LLM API rate limit exceeded")
        )
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        mock_create_llm.return_value = (mock_llm, None, None)

        # Create test state
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Analyze company financial data",
        )

        # Execute node
        result = await requirement_analysis_node(state)

        # Verify error handling
        assert "error_message" in result
        assert "Task breakdown failed" in result["error_message"]
        assert "LLM API rate limit exceeded" in result["error_message"]

        # task_breakdown should not be in result
        assert "task_breakdown" not in result

        # Verify LLM was called
        mock_structured.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.create_llm_with_fallback"
    )
    async def test_requirement_analysis_empty_response(self, mock_create_llm):
        """Test handling of empty task list from LLM.

        Priority: Medium
        This tests edge case where LLM returns no tasks.
        """
        # Create mock LLM response with empty tasks
        mock_response = TaskBreakdownResponse(
            tasks=[],  # Empty task list
            overall_summary="No tasks could be decomposed from requirement",
        )

        # Setup mock LLM
        mock_llm = AsyncMock()
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        mock_create_llm.return_value = (mock_llm, None, None)

        # Create test state
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Unclear or invalid requirement",
        )

        # Execute node
        result = await requirement_analysis_node(state)

        # Verify results
        assert "task_breakdown" in result
        assert len(result["task_breakdown"]) == 0  # Empty list
        assert result["overall_summary"] == mock_response.overall_summary
        assert result["evaluator_stage"] == "after_task_breakdown"

        # This should trigger evaluator to mark as invalid and retry

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.create_llm_with_fallback"
    )
    async def test_requirement_analysis_with_evaluation_feedback(self, mock_create_llm):
        """Test task breakdown with evaluation feedback (retry scenario).

        Priority: Medium
        This tests the feedback-enhanced prompt path.
        """
        # Create mock LLM response
        mock_tasks = [
            TaskBreakdownItem(
                task_id="task_001",
                name="Improved task based on feedback",
                description="This task addresses the feedback issues",
                dependencies=[],
                expected_output="Improved output format",
                priority=1,
            ),
        ]
        mock_response = TaskBreakdownResponse(
            tasks=mock_tasks,
            overall_summary="Improved task breakdown addressing feedback",
        )

        # Setup mock LLM
        mock_llm = AsyncMock()
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        mock_create_llm.return_value = (mock_llm, None, None)

        # Create test state with evaluation feedback
        state = create_mock_workflow_state(
            retry_count=1,  # This is a retry
            user_requirement="Create a workflow for data analysis",
            evaluation_feedback="Previous task breakdown was too vague. "
            "Please add more specific data validation steps.",
        )

        # Execute node
        result = await requirement_analysis_node(state)

        # Verify results
        assert "task_breakdown" in result
        assert len(result["task_breakdown"]) == 1
        assert result["task_breakdown"][0]["name"] == "Improved task based on feedback"

        # Verify LLM was called with feedback prompt
        mock_structured.ainvoke.assert_called_once()
        call_args = mock_structured.ainvoke.call_args[0][0]
        user_prompt = call_args[1]["content"]
        # Prompt contains Japanese "フィードバック" or English "feedback" (case-insensitive)
        assert "フィードバック" in user_prompt or "feedback" in user_prompt.lower(), (
            f"Expected feedback in prompt, but got: {user_prompt[:200]}..."
        )

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.create_llm_with_fallback"
    )
    async def test_requirement_analysis_retry_count_increment(self, mock_create_llm):
        """Test retry_count increment behavior on retry.

        Priority: Medium
        This tests the retry_count logic:
        - If retry_count > 0: increment by 1
        - If retry_count == 0: keep at 0
        """
        # Create mock LLM response
        mock_tasks = [
            TaskBreakdownItem(
                task_id="task_001",
                name="Test task",
                description="Test",
                dependencies=[],
                expected_output="Test output",
                priority=1,
            ),
        ]
        mock_response = TaskBreakdownResponse(
            tasks=mock_tasks,
            overall_summary="Test summary",
        )

        # Setup mock LLM
        mock_llm = AsyncMock()
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(return_value=mock_response)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        mock_create_llm.return_value = (mock_llm, None, None)

        # Test Case 1: retry_count == 0 (first attempt)
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Test requirement",
        )
        result = await requirement_analysis_node(state)
        assert result["retry_count"] == 0, (
            "retry_count should remain 0 on first successful attempt"
        )

        # Test Case 2: retry_count == 1 (first retry)
        state = create_mock_workflow_state(
            retry_count=1,
            user_requirement="Test requirement",
        )
        result = await requirement_analysis_node(state)
        assert result["retry_count"] == 2, (
            "retry_count should increment from 1 to 2 on retry"
        )

        # Test Case 3: retry_count == 3 (third retry)
        state = create_mock_workflow_state(
            retry_count=3,
            user_requirement="Test requirement",
        )
        result = await requirement_analysis_node(state)
        assert result["retry_count"] == 4, (
            "retry_count should increment from 3 to 4 on retry"
        )

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.create_llm_with_fallback"
    )
    async def test_requirement_analysis_missing_user_requirement(self, mock_create_llm):
        """Test error handling when user_requirement is missing.

        Priority: Low
        This tests KeyError handling for missing required field.
        """
        # Setup mock LLM (won't be called due to KeyError)
        mock_llm = AsyncMock()
        mock_create_llm.return_value = (mock_llm, None, None)

        # Create test state WITHOUT user_requirement
        state = create_mock_workflow_state(
            retry_count=0,
            # user_requirement is intentionally missing
        )

        # Execute node - should raise KeyError
        with pytest.raises(KeyError) as exc_info:
            await requirement_analysis_node(state)

        # Verify KeyError for 'user_requirement'
        assert "user_requirement" in str(exc_info.value)
