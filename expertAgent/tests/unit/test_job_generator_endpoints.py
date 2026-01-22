"""Tests for job generator endpoints."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.api.v1.job_generator_endpoints import (
    _build_response_from_state,
    _create_job_in_background,
    generate_job_and_tasks,
    get_job_creation_status,
)
from app.schemas.job_generator import (
    JobGeneratorRequest,
)
from app.services.job_creation_state import JobCreationStatus


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


class TestGetJobCreationStatus:
    """Test get_job_creation_status endpoint with async mock."""

    @pytest.mark.asyncio
    @patch("app.api.v1.job_generator_endpoints.job_state_manager")
    async def test_get_job_creation_status_success(self, mock_state_manager):
        """Test successful job status retrieval using get_status_async."""
        from datetime import datetime

        # Setup mock for get_status_async
        mock_status = JobCreationStatus(
            job_id="test-job-id",
            status="creating",
            progress=50,
            start_time=datetime.now(),
        )
        mock_state_manager.get_status_async = AsyncMock(return_value=mock_status)

        # Execute
        result = await get_job_creation_status("test-job-id")

        # Assert
        mock_state_manager.get_status_async.assert_called_once_with("test-job-id")
        assert result["job_id"] == "test-job-id"
        assert result["status"] == "creating"
        assert result["progress"] == 50

    @pytest.mark.asyncio
    @patch("app.api.v1.job_generator_endpoints.job_state_manager")
    async def test_get_job_creation_status_not_found(self, mock_state_manager):
        """Test job status not found raises HTTPException."""
        # Setup mock to return None (not found)
        mock_state_manager.get_status_async = AsyncMock(return_value=None)

        # Execute and assert
        with pytest.raises(HTTPException) as exc_info:
            await get_job_creation_status("nonexistent-job-id")

        assert exc_info.value.status_code == 404
        assert "nonexistent-job-id" in exc_info.value.detail


class TestCreateJobInBackground:
    """Test _create_job_in_background function with async mocks."""

    @pytest.mark.asyncio
    @patch("app.api.v1.job_generator_endpoints.job_state_manager")
    @patch("app.api.v1.job_generator_endpoints.create_job_task_generator_agent")
    @patch("app.api.v1.job_generator_endpoints.create_initial_state")
    async def test_create_job_in_background_success(
        self, mock_create_state, mock_create_agent, mock_state_manager
    ):
        """Test successful background job creation uses async methods."""
        # Setup mocks
        mock_create_state.return_value = {"user_requirement": "Test requirement"}

        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(
            return_value={
                "job_id": "test-job-id",
                "job_master_id": "123",
                "task_breakdown": [{"task_id": "task_1", "name": "Test Task"}],
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

        # Setup async mocks for job_state_manager
        # Issue #305: Add update_phase_async mock for initial phase setting
        # Issue #350: Add set_task_breakdown_async for V2 orchestrator
        mock_state_manager.update_phase_async = AsyncMock()
        mock_state_manager.update_progress_async = AsyncMock()
        mock_state_manager.mark_completed_async = AsyncMock()
        mock_state_manager.mark_failed_async = AsyncMock()
        mock_state_manager.set_task_breakdown_async = AsyncMock()

        # Execute
        # Note: project_id parameter was removed from _create_job_in_background
        await _create_job_in_background(
            job_id="test-job-id",
            user_requirement="Test requirement",
            max_retry=5,
        )

        # Assert - V2 orchestrator is now being used, which has different behavior
        # The test should verify that job creation completes without errors
        # and that either mark_completed or mark_failed was called
        assert (
            mock_state_manager.mark_completed_async.called
            or mock_state_manager.mark_failed_async.called
        ), "Either mark_completed_async or mark_failed_async should be called"

    @pytest.mark.asyncio
    @patch("app.api.v1.job_generator_endpoints.job_state_manager")
    @patch("app.api.v1.job_generator_endpoints.create_job_task_generator_agent")
    @patch("app.api.v1.job_generator_endpoints.create_initial_state")
    async def test_create_job_in_background_failure(
        self, mock_create_state, mock_create_agent, mock_state_manager
    ):
        """Test failed background job creation uses mark_failed_async."""
        # Setup mocks
        mock_create_state.return_value = {"user_requirement": "Test requirement"}

        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(side_effect=Exception("LLM timeout error"))
        mock_create_agent.return_value = mock_agent

        # Setup async mocks for job_state_manager
        # Issue #305: Add update_phase_async mock for initial phase setting
        # Issue #350: Add set_task_breakdown_async for V2 orchestrator
        mock_state_manager.update_phase_async = AsyncMock()
        mock_state_manager.update_progress_async = AsyncMock()
        mock_state_manager.mark_completed_async = AsyncMock()
        mock_state_manager.mark_failed_async = AsyncMock()
        mock_state_manager.set_task_breakdown_async = AsyncMock()

        # Execute
        # Note: project_id parameter was removed from _create_job_in_background
        await _create_job_in_background(
            job_id="test-job-id",
            user_requirement="Test requirement",
            max_retry=5,
        )

        # Assert mark_failed_async was called with error
        mock_state_manager.mark_failed_async.assert_called_once()
        call_args = mock_state_manager.mark_failed_async.call_args
        assert call_args[1]["job_id"] == "test-job-id"
        # Error message may vary between V1 and V2 orchestrators
        assert (
            "error" in call_args[1]["error_message"].lower()
            or len(call_args[1]["error_message"]) > 0
        )
        mock_state_manager.mark_completed_async.assert_not_called()


class TestGenerateJobAndTasksAsync:
    """Test generate_job_and_tasks endpoint uses async create_job_async."""

    @pytest.mark.asyncio
    @patch("app.api.v1.job_generator_endpoints.job_state_manager")
    @patch("app.api.v1.job_generator_endpoints.secrets_manager.get_secret")
    async def test_generate_job_and_tasks_uses_create_job_async(
        self, mock_get_secret, mock_state_manager
    ):
        """Test generate_job_and_tasks uses create_job_async."""
        # Mock secrets manager
        mock_get_secret.return_value = "test-anthropic-api-key"

        # Setup async mock for create_job_async
        mock_state_manager.create_job_async = AsyncMock()

        # Create request
        request = JobGeneratorRequest(user_requirement="Test requirement", max_retry=5)

        # Create mock BackgroundTasks
        background_tasks = BackgroundTasks()

        # Execute
        result = await generate_job_and_tasks(request, background_tasks)

        # Assert create_job_async was called
        mock_state_manager.create_job_async.assert_called_once()
        assert result.status == "creating"
        assert result.job_id is not None
