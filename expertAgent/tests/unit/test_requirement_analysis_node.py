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
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.invoke_structured_llm"
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
        # Setup mock performance and cost trackers
        mock_perf_tracker = MagicMock()
        mock_cost_tracker = MagicMock()
        mock_create_llm.return_value = (mock_llm, mock_perf_tracker, mock_cost_tracker)

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
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.invoke_structured_llm"
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
        # Setup mock performance and cost trackers
        mock_perf_tracker = MagicMock()
        mock_cost_tracker = MagicMock()
        mock_create_llm.return_value = (mock_llm, mock_perf_tracker, mock_cost_tracker)

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
        # Note: Error message may be from recovery attempt rather than original exception
        assert (
            "LLM API rate limit exceeded" in result["error_message"]
            or "Failed to extract JSON block" in result["error_message"]
        )

        # task_breakdown should not be in result
        assert "task_breakdown" not in result

        # Verify LLM was called
        mock_structured.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.invoke_structured_llm"
    )
    async def test_requirement_analysis_empty_response(self, mock_create_llm):
        """Test handling of empty task list from LLM.

        Priority: Medium
        This tests edge case where LLM returns no tasks.
        Issue #111: Empty task list should now be treated as error.
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
        # Setup mock performance and cost trackers
        mock_perf_tracker = MagicMock()
        mock_cost_tracker = MagicMock()
        mock_create_llm.return_value = (mock_llm, mock_perf_tracker, mock_cost_tracker)

        # Create test state
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Unclear or invalid requirement",
        )

        # Execute node
        result = await requirement_analysis_node(state)

        # Verify error handling (changed behavior after Issue #111)
        assert "error_message" in result
        assert "Task breakdown failed" in result["error_message"]
        # Note: Error message may be from recovery attempt rather than original validation
        assert (
            "empty task list" in result["error_message"]
            or "Failed to extract JSON block" in result["error_message"]
        )

        # task_breakdown should NOT be in result (error case)
        assert "task_breakdown" not in result

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.invoke_structured_llm"
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
        # Setup mock performance and cost trackers
        mock_perf_tracker = MagicMock()
        mock_cost_tracker = MagicMock()
        mock_create_llm.return_value = (mock_llm, mock_perf_tracker, mock_cost_tracker)

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
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.invoke_structured_llm"
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
        # Setup mock performance and cost trackers
        mock_perf_tracker = MagicMock()
        mock_cost_tracker = MagicMock()
        mock_create_llm.return_value = (mock_llm, mock_perf_tracker, mock_cost_tracker)

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
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.invoke_structured_llm"
    )
    async def test_requirement_analysis_missing_user_requirement(self, mock_create_llm):
        """Test error handling when user_requirement is missing.

        Priority: Low
        This tests KeyError handling for missing required field.
        """
        # Setup mock LLM (won't be called due to KeyError)
        mock_llm = AsyncMock()
        # Setup mock performance and cost trackers
        mock_perf_tracker = MagicMock()
        mock_cost_tracker = MagicMock()
        mock_create_llm.return_value = (mock_llm, mock_perf_tracker, mock_cost_tracker)

        # Create test state WITHOUT user_requirement
        state = create_mock_workflow_state(
            retry_count=0,
            # user_requirement is intentionally missing
        )

        # Execute node - should return error message (changed behavior after Issue #111)
        result = await requirement_analysis_node(state)

        # Verify error handling
        assert "error_message" in result
        assert "missing user requirement" in result["error_message"]

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.invoke_structured_llm"
    )
    async def test_requirement_analysis_none_response(self, mock_create_llm):
        """Test error handling when LLM returns None response.

        Priority: High
        This tests validation of LLM response structure.
        Issue #111: Fix expertagent.log errors - Task Breakdown Null.
        """
        # Setup mock LLM to return None (structured output parsing failed)
        mock_llm = AsyncMock()
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(return_value=None)
        mock_llm.with_structured_output = MagicMock(return_value=mock_structured)
        # Setup mock performance and cost trackers
        mock_perf_tracker = MagicMock()
        mock_cost_tracker = MagicMock()
        mock_create_llm.return_value = (mock_llm, mock_perf_tracker, mock_cost_tracker)

        # Create test state
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Test requirement",
        )

        # Execute node
        result = await requirement_analysis_node(state)

        # Verify error handling
        assert "error_message" in result
        assert "Task breakdown failed" in result["error_message"]
        # Note: Error message may be from recovery attempt rather than original validation
        assert (
            "LLM returned None response" in result["error_message"]
            or "Failed to extract JSON block" in result["error_message"]
        )

        # task_breakdown should not be in result
        assert "task_breakdown" not in result

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.invoke_structured_llm"
    )
    async def test_requirement_analysis_none_tasks(self, mock_create_llm):
        """Test error handling when LLM response.tasks is None.

        Priority: High
        This tests validation of tasks field in LLM response.
        Issue #111: Fix expertagent.log errors - Task Breakdown Null.
        """

        # Create mock response with tasks=None (simulating AttributeError scenario)
        class MockResponseWithNoneTasks:
            tasks = None
            overall_summary = "Some summary"

        mock_response = MockResponseWithNoneTasks()

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
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Test requirement",
        )

        # Execute node
        result = await requirement_analysis_node(state)

        # Verify error handling
        assert "error_message" in result
        assert "Task breakdown failed" in result["error_message"]
        # Note: Error message may be from recovery attempt rather than original validation
        assert (
            "response missing 'tasks' field" in result["error_message"]
            or "Failed to extract JSON block" in result["error_message"]
        )

        # task_breakdown should not be in result
        assert "task_breakdown" not in result

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.invoke_structured_llm"
    )
    async def test_requirement_analysis_empty_tasks_with_validation(
        self, mock_create_llm
    ):
        """Test error handling when LLM returns empty task list (new validation).

        Priority: Medium
        This tests the new validation logic for empty task lists.
        Issue #111: Fix expertagent.log errors - Task Breakdown Null.
        """
        # Create mock LLM response with empty tasks
        mock_response = TaskBreakdownResponse(
            tasks=[],  # Empty task list
            overall_summary="No tasks could be decomposed",
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
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Unclear requirement",
        )

        # Execute node
        result = await requirement_analysis_node(state)

        # Verify error handling (new validation logic)
        assert "error_message" in result
        assert "Task breakdown failed" in result["error_message"]
        # Note: Error message may be from recovery attempt rather than original validation
        assert (
            "empty task list" in result["error_message"]
            or "Failed to extract JSON block" in result["error_message"]
        )

        # task_breakdown should not be in result
        assert "task_breakdown" not in result
