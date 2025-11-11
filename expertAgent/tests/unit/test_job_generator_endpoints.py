"""Tests for job generator endpoints."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import BackgroundTasks, HTTPException

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
            "job_master_id": "123",
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
        assert result.job_master_id == "123"
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
            "job_master_id": "123",
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
        assert result.job_master_id == "123"
        assert len(result.infeasible_tasks) == 1
        assert result.infeasible_tasks[0]["task_name"] == "Slack Notification"
        assert len(result.alternative_proposals) == 1
        assert result.alternative_proposals[0]["alternative"] == "Gmail Notification"
        # Phase 1 improvement: partial_success provides user-friendly feedback in error_message
        assert result.error_message is not None
        assert "Job successfully created" in result.error_message
        assert "infeasible" in result.error_message.lower()

    def test_partial_success_with_api_proposals(self):
        """Test partial success with API extension proposals."""
        state: dict[str, Any] = {
            "job_id": "550e8400-e29b-41d4-a716-446655440000",
            "job_master_id": "123",
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
        # Phase 1 improvement: failed state provides user-friendly feedback in error_message
        assert result.error_message is not None
        assert "Job generation did not complete successfully" in result.error_message
        assert "retry" in result.error_message.lower()

    def test_validation_errors_case(self):
        """Test case with validation errors."""
        state: dict[str, Any] = {
            "job_id": None,
            "job_master_id": "123",
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
        # Phase 1 improvement: failed state provides user-friendly feedback in error_message
        assert result.error_message is not None
        assert "Job generation did not complete successfully" in result.error_message
        assert "retry" in result.error_message.lower()


class TestGenerateJobAndTasks:
    """Test generate_job_and_tasks endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.job_generator_endpoints.create_job_task_generator_agent")
    @patch("app.api.v1.job_generator_endpoints.create_initial_state")
    @patch("app.api.v1.job_generator_endpoints.secrets_manager.get_secret")
    async def test_generate_job_and_tasks_success(
        self, mock_get_secret, mock_create_state, mock_create_agent
    ):
        """Test successful job generation."""
        # Mock secrets manager
        mock_get_secret.return_value = "test-anthropic-api-key"

        # Mock initial state
        mock_create_state.return_value = {
            "user_requirement": "Upload PDF and send email"
        }

        # Mock agent and ainvoke
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(
            return_value={
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "job_master_id": "123",
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

        # Create mock BackgroundTasks
        background_tasks = BackgroundTasks()

        # Execute
        result = await generate_job_and_tasks(request, background_tasks)

        # Assert - with background tasks, it returns immediately with status="creating"
        assert result.status == "creating"
        assert result.job_id is not None  # job_id is generated upfront
        assert result.job_master_id is None  # Not set until background task completes
        assert "Job creation started" in result.error_message

    @pytest.mark.asyncio
    @patch("app.api.v1.job_generator_endpoints.secrets_manager.get_secret")
    async def test_generate_job_and_tasks_failure(self, mock_get_secret):
        """Test job generation failure when ANTHROPIC_API_KEY is missing."""
        # Mock secrets manager to raise error (ANTHROPIC_API_KEY not found)
        mock_get_secret.side_effect = ValueError("Secret not found: ANTHROPIC_API_KEY")

        # Create request
        request = JobGeneratorRequest(user_requirement="Test requirement", max_retry=5)

        # Create mock BackgroundTasks
        background_tasks = BackgroundTasks()

        # Execute and expect HTTPException (initial setup failure)
        with pytest.raises(HTTPException) as exc_info:
            await generate_job_and_tasks(request, background_tasks)

        assert exc_info.value.status_code == 500
        assert "ANTHROPIC_API_KEY not configured" in exc_info.value.detail

    @pytest.mark.asyncio
    @patch("app.api.v1.job_generator_endpoints.create_job_task_generator_agent")
    @patch("app.api.v1.job_generator_endpoints.create_initial_state")
    @patch("app.api.v1.job_generator_endpoints.secrets_manager.get_secret")
    async def test_generate_job_and_tasks_partial_success(
        self, mock_get_secret, mock_create_state, mock_create_agent
    ):
        """Test partial success with infeasible tasks."""
        # Mock secrets manager
        mock_get_secret.return_value = "test-anthropic-api-key"

        # Mock initial state
        mock_create_state.return_value = {
            "user_requirement": "Upload PDF and send Slack notification"
        }

        # Mock agent
        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(
            return_value={
                "job_id": "550e8400-e29b-41d4-a716-446655440000",
                "job_master_id": "123",
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

        # Create mock BackgroundTasks
        background_tasks = BackgroundTasks()

        # Execute
        result = await generate_job_and_tasks(request, background_tasks)

        # Assert - with background tasks, it returns immediately with status="creating"
        assert result.status == "creating"
        assert result.job_id is not None  # job_id is generated upfront
        assert result.job_master_id is None  # Not set until background task completes
        assert "Job creation started" in result.error_message
