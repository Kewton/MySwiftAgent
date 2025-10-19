"""Tests for job generator endpoints."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.job_generator_endpoints import (
    _build_response_from_state,
    generate_job_and_tasks,
)
from app.schemas.job_generator import (
    JobGeneratorRequest,
)


class TestBuildResponseFromState:
    """Test _build_response_from_state function."""

    def test_success_case(self):
        """Test successful job generation with no infeasible tasks."""
        state: dict[str, Any] = {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "job_master_id": 123,
            "task_breakdown": [
                {"task_id": "task_1", "name": "PDF Upload"},
                {"task_id": "task_2", "name": "Email Notification"},
            ],
            "evaluation_result": {
                "is_valid": True,
                "all_tasks_feasible": True,
                "infeasible_tasks": [],
                "alternative_proposals": [],
                "api_extension_proposals": [],
            },
            "validation_result": {"is_valid": True, "errors": []},
        }

        result = _build_response_from_state(state)

        assert result.status == "success"
        assert result.job_id == "550e8400-e29b-41d4-a716-446655440000"
        assert result.job_master_id == 123
        assert len(result.task_breakdown) == 2
        assert result.infeasible_tasks == []
        assert result.alternative_proposals == []
        assert result.api_extension_proposals == []
        assert result.validation_errors == []
        assert result.error_message is None

    def test_partial_success_case(self):
        """Test partial success with infeasible tasks."""
        state: dict[str, Any] = {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "job_master_id": 123,
            "task_breakdown": [
                {"task_id": "task_1", "name": "PDF Upload"},
                {"task_id": "task_2", "name": "Slack Notification"},
            ],
            "evaluation_result": {
                "is_valid": True,
                "all_tasks_feasible": False,
                "infeasible_tasks": [
                    {
                        "task_name": "Slack Notification",
                        "reason": "Slack API not available",
                    }
                ],
                "alternative_proposals": [
                    {
                        "original_task": "Slack Notification",
                        "alternative": "Gmail Notification",
                        "confidence": 0.9,
                    }
                ],
                "api_extension_proposals": [],
            },
            "validation_result": {"is_valid": True, "errors": []},
        }

        result = _build_response_from_state(state)

        assert result.status == "partial_success"
        assert result.job_id == "550e8400-e29b-41d4-a716-446655440000"
        assert result.job_master_id == 123
        assert len(result.infeasible_tasks) == 1
        assert result.infeasible_tasks[0]["task_name"] == "Slack Notification"
        assert len(result.alternative_proposals) == 1
        assert result.alternative_proposals[0]["alternative"] == "Gmail Notification"
        assert result.error_message is None

    def test_partial_success_with_api_proposals(self):
        """Test partial success with API extension proposals."""
        state: dict[str, Any] = {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "job_master_id": 123,
            "task_breakdown": [{"task_id": "task_1", "name": "Custom Task"}],
            "evaluation_result": {
                "is_valid": True,
                "all_tasks_feasible": False,
                "infeasible_tasks": [],
                "alternative_proposals": [],
                "api_extension_proposals": [
                    {
                        "api_name": "Custom API",
                        "description": "New API for custom task",
                        "priority": "high",
                    }
                ],
            },
            "validation_result": {"is_valid": True, "errors": []},
        }

        result = _build_response_from_state(state)

        assert result.status == "partial_success"
        assert len(result.api_extension_proposals) == 1
        assert result.api_extension_proposals[0]["api_name"] == "Custom API"

    def test_failed_case_with_error_message(self):
        """Test failed case with error message."""
        state: dict[str, Any] = {
            "error_message": "Task breakdown failed: LLM timeout",
            "task_breakdown": [],
            "evaluation_result": None,
            "validation_result": None,
        }

        result = _build_response_from_state(state)

        assert result.status == "failed"
        assert result.job_id is None
        assert result.job_master_id is None
        assert result.error_message == "Task breakdown failed: LLM timeout"

    def test_failed_case_without_job_id(self):
        """Test failed case without job_id (workflow ended early)."""
        state: dict[str, Any] = {
            "task_breakdown": [{"task_id": "task_1", "name": "Test"}],
            "evaluation_result": {"is_valid": False},
            "validation_result": None,
        }

        result = _build_response_from_state(state)

        assert result.status == "failed"
        assert result.job_id is None
        assert (
            result.error_message
            == "Job generation did not complete. Check validation_errors or infeasible_tasks for details."
        )

    def test_validation_errors_case(self):
        """Test case with validation errors."""
        state: dict[str, Any] = {
            "job_id": None,
            "job_master_id": 123,
            "task_breakdown": [{"task_id": "task_1", "name": "Test"}],
            "evaluation_result": {"is_valid": True},
            "validation_result": {
                "is_valid": False,
                "errors": [
                    "Interface mismatch between task_1 and task_2",
                    "Missing required field in task_2",
                ],
            },
        }

        result = _build_response_from_state(state)

        assert result.status == "failed"
        assert len(result.validation_errors) == 2
        assert "Interface mismatch" in result.validation_errors[0]

    def test_empty_state(self):
        """Test with minimal/empty state."""
        state: dict[str, Any] = {}

        result = _build_response_from_state(state)

        assert result.status == "failed"
        assert result.job_id is None
        assert (
            result.error_message
            == "Job generation did not complete. Check validation_errors or infeasible_tasks for details."
        )


class TestGenerateJobAndTasks:
    """Test generate_job_and_tasks endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.job_generator_endpoints.create_job_task_generator_agent")
    @patch("app.api.v1.job_generator_endpoints.create_initial_state")
    async def test_generate_job_and_tasks_success(
        self, mock_create_state, mock_create_agent
    ):
        """Test successful job generation."""
        # Mock initial state
        mock_create_state.return_value = {
            "user_requirement": "Upload PDF and send email"
        }

        # Mock agent and ainvoke
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(
            return_value={
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "job_master_id": 123,
                "task_breakdown": [
                    {"task_id": "task_1", "name": "PDF Upload"},
                    {"task_id": "task_2", "name": "Email Notification"},
                ],
                "evaluation_result": {
                    "is_valid": True,
                    "all_tasks_feasible": True,
                    "infeasible_tasks": [],
                    "alternative_proposals": [],
                    "api_extension_proposals": [],
                },
                "validation_result": {"is_valid": True, "errors": []},
            }
        )
        mock_create_agent.return_value = mock_agent

        # Create request
        request = JobGeneratorRequest(
            user_requirement="Upload PDF and send email", max_retry=5
        )

        # Execute
        result = await generate_job_and_tasks(request)

        # Assert
        assert result.status == "success"
        assert result.job_id == "550e8400-e29b-41d4-a716-446655440000"
        assert result.job_master_id == 123
        mock_create_state.assert_called_once_with(
            user_requirement="Upload PDF and send email"
        )
        mock_create_agent.assert_called_once()
        mock_agent.ainvoke.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.api.v1.job_generator_endpoints.create_job_task_generator_agent")
    @patch("app.api.v1.job_generator_endpoints.create_initial_state")
    async def test_generate_job_and_tasks_failure(
        self, mock_create_state, mock_create_agent
    ):
        """Test job generation failure."""
        # Mock initial state
        mock_create_state.return_value = {"user_requirement": "Invalid requirement"}

        # Mock agent to raise exception
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(side_effect=Exception("LLM API timeout"))
        mock_create_agent.return_value = mock_agent

        # Create request
        request = JobGeneratorRequest(
            user_requirement="Invalid requirement", max_retry=5
        )

        # Execute and expect HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await generate_job_and_tasks(request)

        assert exc_info.value.status_code == 500
        assert "Job generation failed" in exc_info.value.detail
        assert "LLM API timeout" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.api.v1.job_generator_endpoints.create_job_task_generator_agent")
    @patch("app.api.v1.job_generator_endpoints.create_initial_state")
    async def test_generate_job_and_tasks_partial_success(
        self, mock_create_state, mock_create_agent
    ):
        """Test partial success with infeasible tasks."""
        # Mock initial state
        mock_create_state.return_value = {
            "user_requirement": "Upload PDF and send Slack notification"
        }

        # Mock agent
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(
            return_value={
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "job_master_id": 123,
                "task_breakdown": [
                    {"task_id": "task_1", "name": "PDF Upload"},
                    {"task_id": "task_2", "name": "Slack Notification"},
                ],
                "evaluation_result": {
                    "is_valid": True,
                    "all_tasks_feasible": False,
                    "infeasible_tasks": [
                        {
                            "task_name": "Slack Notification",
                            "reason": "Slack API not available",
                        }
                    ],
                    "alternative_proposals": [
                        {
                            "original_task": "Slack Notification",
                            "alternative": "Gmail Notification",
                        }
                    ],
                    "api_extension_proposals": [],
                },
                "validation_result": {"is_valid": True, "errors": []},
            }
        )
        mock_create_agent.return_value = mock_agent

        # Create request
        request = JobGeneratorRequest(
            user_requirement="Upload PDF and send Slack notification", max_retry=5
        )

        # Execute
        result = await generate_job_and_tasks(request)

        # Assert
        assert result.status == "partial_success"
        assert result.job_id == "550e8400-e29b-41d4-a716-446655440000"
        assert len(result.infeasible_tasks) == 1
        assert len(result.alternative_proposals) == 1
