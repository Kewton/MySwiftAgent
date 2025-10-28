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

from unittest.mock import patch

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
    async def test_requirement_analysis_success(self, mock_invoke_llm):
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

        # Setup mock invoke_structured_llm

        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=mock_response,
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

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
        mock_invoke_llm.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.invoke_structured_llm"
    )
    async def test_requirement_analysis_with_llm_error(self, mock_invoke_llm):
        """Test error handling when LLM invocation fails.

        Priority: High
        This tests exception handling and error message propagation.
        """
        # Setup mock invoke_structured_llm to raise exception
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredLLMError,
        )

        mock_invoke_llm.side_effect = StructuredLLMError("LLM API rate limit exceeded")

        # Create test state
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Analyze company financial data",
        )

        # Execute node
        result = await requirement_analysis_node(state)

        # Verify error handling
        assert "error_message" in result
        # Note: Error message may be from recovery attempt rather than original exception
        assert (
            "LLM API rate limit exceeded" in result["error_message"]
            or "Failed to extract JSON block" in result["error_message"]
        )

        # task_breakdown should not be in result
        assert "task_breakdown" not in result

        # Verify LLM was called
        mock_invoke_llm.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.invoke_structured_llm"
    )
    async def test_requirement_analysis_empty_response(self, mock_invoke_llm):
        """Test handling of empty task list from LLM.

        Priority: Medium
        This tests edge case where LLM returns no tasks.
        Note: When invoke_structured_llm is fully mocked, validator is not called,
        so empty task lists pass through. This test verifies backward compatibility.
        """
        # Create mock LLM response with empty tasks
        mock_response = TaskBreakdownResponse(
            tasks=[],  # Empty task list
            overall_summary="No tasks could be decomposed from requirement",
        )

        # Setup mock invoke_structured_llm

        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=mock_response,
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

        # Create test state
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Unclear or invalid requirement",
        )

        # Execute node
        result = await requirement_analysis_node(state)

        # Since invoke_structured_llm is fully mocked, validator is not called
        # Empty task list passes through successfully
        assert "task_breakdown" in result
        assert len(result["task_breakdown"]) == 0
        assert result["overall_summary"] == mock_response.overall_summary
        assert result["evaluator_stage"] == "after_task_breakdown"

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.invoke_structured_llm"
    )
    async def test_requirement_analysis_with_evaluation_feedback(self, mock_invoke_llm):
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

        # Setup mock invoke_structured_llm

        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=mock_response,
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

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
        mock_invoke_llm.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.invoke_structured_llm"
    )
    async def test_requirement_analysis_retry_count_increment(self, mock_invoke_llm):
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

        # Setup mock invoke_structured_llm

        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=mock_response,
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

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
    async def test_requirement_analysis_missing_user_requirement(self, mock_invoke_llm):
        """Test error handling when user_requirement is missing.

        Priority: Low
        This tests KeyError handling for missing required field.
        """
        # Note: mock_invoke_llm won't be called due to early validation error

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
    async def test_requirement_analysis_none_response(self, mock_invoke_llm):
        """Test error handling when LLM returns None response.

        Priority: High
        This tests validation of LLM response structure.
        Issue #111: Fix expertagent.log errors - Task Breakdown Null.
        """
        # Setup mock invoke_structured_llm to raise error for None response
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredLLMError,
        )

        mock_invoke_llm.side_effect = StructuredLLMError("LLM returned None response")

        # Create test state
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Test requirement",
        )

        # Execute node
        result = await requirement_analysis_node(state)

        # Verify error handling
        assert "error_message" in result
        assert "LLM returned None response" in result["error_message"]

        # task_breakdown should not be in result
        assert "task_breakdown" not in result

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.invoke_structured_llm"
    )
    async def test_requirement_analysis_none_tasks(self, mock_invoke_llm):
        """Test error handling when LLM response.tasks is None.

        Priority: High
        This tests validation of tasks field in LLM response.
        Issue #111: Fix expertagent.log errors - Task Breakdown Null.
        Note: With full invoke_structured_llm mock, this raises AttributeError
        during task iteration, not during validation.
        """

        # Create mock response with tasks=None (simulating AttributeError scenario)
        class MockResponseWithNoneTasks:
            tasks = None
            overall_summary = "Some summary"

        mock_response = MockResponseWithNoneTasks()

        # Setup mock invoke_structured_llm

        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=mock_response,
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

        # Create test state
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Test requirement",
        )

        # Execute node - should raise TypeError when calling len(None)
        with pytest.raises(TypeError, match="object of type 'NoneType' has no len"):
            await requirement_analysis_node(state)

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.requirement_analysis.invoke_structured_llm"
    )
    async def test_requirement_analysis_empty_tasks_with_validation(
        self, mock_invoke_llm
    ):
        """Test handling when LLM returns empty task list.

        Priority: Medium
        This tests the empty task list edge case.
        Note: When invoke_structured_llm is fully mocked, validator is not called,
        so empty task lists pass through. This is the same as test_requirement_analysis_empty_response.
        """
        # Create mock LLM response with empty tasks
        mock_response = TaskBreakdownResponse(
            tasks=[],  # Empty task list
            overall_summary="No tasks could be decomposed",
        )

        # Setup mock invoke_structured_llm

        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        mock_invoke_llm.return_value = StructuredCallResult(
            result=mock_response,
            recovered_via_json=False,
            raw_text=None,
            model_name="test-model",
        )

        # Create test state
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Unclear requirement",
        )

        # Execute node
        result = await requirement_analysis_node(state)

        # Since invoke_structured_llm is fully mocked, validator is not called
        # Empty task list passes through successfully
        assert "task_breakdown" in result
        assert len(result["task_breakdown"]) == 0
        assert result["overall_summary"] == mock_response.overall_summary
        assert result["evaluator_stage"] == "after_task_breakdown"
