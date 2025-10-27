"""Unit tests for validation node.

These tests verify that the validation node correctly increments retry_count
when validation fails or exceptions occur, preventing infinite retry loops.

Issue #111: Recursion limit bug - validation node didn't increment retry_count.
"""

from unittest.mock import AsyncMock, patch

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation import validation_node
from aiagent.langgraph.jobTaskGeneratorAgents.prompts.validation_fix import (
    ValidationFixResponse,
)
from tests.utils.mock_helpers import create_mock_workflow_state


@pytest.mark.unit
class TestValidationNode:
    """Unit tests for validation node retry logic."""

    @pytest.mark.asyncio
    @patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation.JobqueueClient")
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation.create_llm_with_fallback"
    )
    async def test_validation_success_resets_retry_count(
        self,
        mock_create_llm,
        mock_client_class,
    ):
        """Test that validation success resets retry_count to 0."""
        # Setup
        mock_client = AsyncMock()
        mock_client.validate_workflow = AsyncMock(
            return_value={
                "is_valid": True,
                "errors": [],
                "warnings": [],
            }
        )
        mock_client_class.return_value = mock_client

        state = create_mock_workflow_state(
            retry_count=3,  # Non-zero retry count
            job_master_id="jm_test123",
        )

        # Execute
        result = await validation_node(state)

        # Verify
        assert result["validation_result"]["is_valid"] is True
        assert result["retry_count"] == 0  # Should reset to 0 on success

    @pytest.mark.asyncio
    @patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation.JobqueueClient")
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation.create_llm_with_fallback"
    )
    async def test_validation_failure_increments_retry_count(
        self,
        mock_create_llm,
        mock_client_class,
    ):
        """Test that validation failure increments retry_count.

        This test WILL FAIL with the current buggy implementation (Line 146)
        where retry_count is not incremented. It will PASS after the fix.
        """
        # Setup
        mock_client = AsyncMock()
        mock_client.validate_workflow = AsyncMock(
            return_value={
                "is_valid": False,
                "errors": ["Interface mismatch error"],
                "warnings": [],
            }
        )
        mock_client_class.return_value = mock_client

        # Mock LLM response for fix proposals
        mock_llm = AsyncMock()
        mock_structured = AsyncMock()
        mock_structured.ainvoke = AsyncMock(
            return_value=ValidationFixResponse(
                can_fix=True,
                fix_summary="Fix proposal generated",
                interface_fixes=[],
                manual_action_required=None,
            )
        )
        mock_llm.with_structured_output = lambda x: mock_structured
        mock_create_llm.return_value = (mock_llm, None, None)

        state = create_mock_workflow_state(
            retry_count=2,
            job_master_id="jm_test123",
            interface_definitions={},
        )

        # Execute
        result = await validation_node(state)

        # Verify
        assert result["validation_result"]["is_valid"] is False
        # ❌ Current implementation: retry_count remains 2
        # ✅ Expected after fix: retry_count should be 3
        assert result["retry_count"] == 3, (
            f"retry_count should increment from 2 to 3, "
            f"but got {result['retry_count']}. "
            "This indicates the bug (Line 146) is still present."
        )

    @pytest.mark.asyncio
    @patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation.JobqueueClient")
    async def test_validation_exception_increments_retry_count(
        self,
        mock_client_class,
    ):
        """Test that validation exception increments retry_count.

        This test WILL FAIL with the current buggy implementation (Line 151-154)
        where retry_count is not returned. It will PASS after the fix.
        """
        # Setup
        mock_client = AsyncMock()
        mock_client.validate_workflow = AsyncMock(
            side_effect=Exception("JobQueue API connection failed")
        )
        mock_client_class.return_value = mock_client

        state = create_mock_workflow_state(
            retry_count=1,
            job_master_id="jm_test123",
        )

        # Execute
        result = await validation_node(state)

        # Verify
        assert "error_message" in result
        assert "Validation failed" in result["error_message"]
        # ❌ Current implementation: retry_count not returned
        # ✅ Expected after fix: retry_count should be 2
        assert result.get("retry_count") == 2, (
            f"retry_count should increment from 1 to 2, "
            f"but got {result.get('retry_count')}. "
            "This indicates the exception handler bug (Line 151-154) is still present."
        )

    @pytest.mark.asyncio
    @patch("aiagent.langgraph.jobTaskGeneratorAgents.nodes.validation.JobqueueClient")
    async def test_validation_missing_job_master_id(
        self,
        mock_client_class,
    ):
        """Test that missing job_master_id returns error without calling API."""
        state = create_mock_workflow_state(
            retry_count=0,
            # job_master_id is missing
        )

        # Execute
        result = await validation_node(state)

        # Verify
        assert "error_message" in result
        assert "JobMaster ID is required" in result["error_message"]
        # Should not call validation API
        mock_client_class.assert_not_called()
