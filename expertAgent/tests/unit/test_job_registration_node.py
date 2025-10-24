"""Unit tests for job_registration_node.

These tests verify the job registration node's behavior including:
- Successful Job creation from JobMaster
- JobMasterTask retrieval and workflow task order
- Error handling for missing JobMaster ID
- Empty workflow tasks handling
- Exception handling during Job creation
- Job name generation logic

Issue #111: Comprehensive test coverage for all workflow nodes.
"""

from unittest.mock import AsyncMock, patch

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents.nodes.job_registration import (
    job_registration_node,
)
from tests.utils.mock_helpers import create_mock_workflow_state


@pytest.mark.unit
class TestJobRegistrationNode:
    """Unit tests for job_registration_node."""

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.job_registration.JobqueueClient"
    )
    async def test_job_registration_success(self, mock_jobqueue_client):
        """Test successful Job registration with valid JobMaster ID.

        Priority: High
        This is the happy path test case.
        """
        # Setup mock JobqueueClient
        mock_client_instance = AsyncMock()
        mock_client_instance.list_workflow_tasks = AsyncMock(
            return_value=[
                {"id": "jmt_001", "order": 0, "task_master_id": "tm_001"},
                {"id": "jmt_002", "order": 1, "task_master_id": "tm_002"},
            ]
        )
        mock_client_instance.create_job = AsyncMock(
            return_value={
                "id": "job_12345678-abcd-1234-5678-123456789abc",
                "name": "Job: Test requirement",
                "master_id": "jm_001",
            }
        )
        mock_jobqueue_client.return_value = mock_client_instance

        # Create test state
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Test requirement for job creation",
            job_master_id="jm_001",
        )

        # Execute node
        result = await job_registration_node(state)

        # Verify Job creation
        assert "job_id" in result
        assert result["job_id"] == "job_12345678-abcd-1234-5678-123456789abc"

        # Verify status and retry_count
        assert result["status"] == "completed"
        assert result["retry_count"] == 0

        # Verify JobqueueClient methods were called
        mock_client_instance.list_workflow_tasks.assert_called_once_with("jm_001")
        mock_client_instance.create_job.assert_called_once()

        # Verify create_job parameters
        call_args = mock_client_instance.create_job.call_args
        assert call_args.kwargs["master_id"] == "jm_001"
        assert "Test requirement for job creation" in call_args.kwargs["name"]
        assert call_args.kwargs["tasks"] is None  # Auto-generate from JobMasterTasks
        assert call_args.kwargs["priority"] == 5
        assert call_args.kwargs["scheduled_at"] is None  # Immediate execution

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.job_registration.JobqueueClient"
    )
    async def test_job_registration_missing_job_master_id(self, mock_jobqueue_client):
        """Test error handling when job_master_id is missing.

        Priority: Medium
        This tests validation of required JobMaster ID.
        """
        # Create test state without job_master_id
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Some requirement",
            # job_master_id is missing
        )

        # Execute node
        result = await job_registration_node(state)

        # Verify error handling
        assert "error_message" in result
        assert (
            "JobMaster ID is required for job registration" in result["error_message"]
        )

        # Verify JobqueueClient was NOT called (early return)
        mock_jobqueue_client.assert_not_called()

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.job_registration.JobqueueClient"
    )
    async def test_job_registration_empty_workflow_tasks(self, mock_jobqueue_client):
        """Test Job creation when workflow tasks list is empty.

        Priority: Medium
        This tests that Job can still be created even without workflow tasks.
        """
        # Setup mock JobqueueClient with empty workflow tasks
        mock_client_instance = AsyncMock()
        mock_client_instance.list_workflow_tasks = AsyncMock(return_value=[])
        mock_client_instance.create_job = AsyncMock(
            return_value={
                "id": "job_87654321-dcba-4321-8765-987654321abc",
                "name": "Job: Empty workflow",
            }
        )
        mock_jobqueue_client.return_value = mock_client_instance

        # Create test state
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Empty workflow requirement",
            job_master_id="jm_002",
        )

        # Execute node
        result = await job_registration_node(state)

        # Verify Job was created despite empty workflow tasks
        assert "job_id" in result
        assert result["job_id"] == "job_87654321-dcba-4321-8765-987654321abc"
        assert result["status"] == "completed"

        # Verify list_workflow_tasks was called and returned empty list
        mock_client_instance.list_workflow_tasks.assert_called_once_with("jm_002")

        # Verify create_job was still called with tasks=None
        call_args = mock_client_instance.create_job.call_args
        assert call_args.kwargs["tasks"] is None

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.job_registration.JobqueueClient"
    )
    async def test_job_registration_with_multiple_workflow_tasks(
        self, mock_jobqueue_client
    ):
        """Test Job creation with multiple workflow tasks.

        Priority: Medium
        This tests that workflow tasks are retrieved correctly.
        """
        # Setup mock JobqueueClient with 3 workflow tasks
        mock_client_instance = AsyncMock()
        mock_client_instance.list_workflow_tasks = AsyncMock(
            return_value=[
                {"id": "jmt_001", "order": 0, "task_master_id": "tm_001"},
                {"id": "jmt_002", "order": 1, "task_master_id": "tm_002"},
                {"id": "jmt_003", "order": 2, "task_master_id": "tm_003"},
            ]
        )
        mock_client_instance.create_job = AsyncMock(
            return_value={
                "id": "job_11111111-1111-1111-1111-111111111111",
                "name": "Job: Multi-task workflow",
            }
        )
        mock_jobqueue_client.return_value = mock_client_instance

        # Create test state
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Multi-task workflow requirement",
            job_master_id="jm_003",
        )

        # Execute node
        result = await job_registration_node(state)

        # Verify Job creation
        assert result["job_id"] == "job_11111111-1111-1111-1111-111111111111"
        assert result["status"] == "completed"

        # Verify list_workflow_tasks was called
        mock_client_instance.list_workflow_tasks.assert_called_once_with("jm_003")

        # Verify create_job was called
        mock_client_instance.create_job.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.job_registration.JobqueueClient"
    )
    async def test_job_registration_exception(self, mock_jobqueue_client):
        """Test error handling when exception occurs during Job creation.

        Priority: Medium
        This tests exception handling and error message propagation.
        """
        # Setup mock JobqueueClient to raise exception
        mock_client_instance = AsyncMock()
        mock_client_instance.list_workflow_tasks = AsyncMock(return_value=[])
        mock_client_instance.create_job = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        mock_jobqueue_client.return_value = mock_client_instance

        # Create test state
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement="Test exception handling",
            job_master_id="jm_004",
        )

        # Execute node
        result = await job_registration_node(state)

        # Verify error handling
        assert "error_message" in result
        assert "Job registration failed" in result["error_message"]
        assert "Database connection failed" in result["error_message"]

        # job_id and status should not be in result
        assert "job_id" not in result
        assert "status" not in result

        # Verify create_job was called (and raised exception)
        mock_client_instance.create_job.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.job_registration.JobqueueClient"
    )
    async def test_job_registration_job_name_generation(self, mock_jobqueue_client):
        """Test Job name generation logic.

        Priority: Low
        This tests that Job name includes user_requirement and datetime.
        """
        # Setup mock JobqueueClient
        mock_client_instance = AsyncMock()
        mock_client_instance.list_workflow_tasks = AsyncMock(return_value=[])
        mock_client_instance.create_job = AsyncMock(
            return_value={
                "id": "job_22222222-2222-2222-2222-222222222222",
                "name": "Job: Test",
            }
        )
        mock_jobqueue_client.return_value = mock_client_instance

        # Create test state with long user_requirement (>50 chars)
        long_requirement = "A" * 60  # 60 characters
        state = create_mock_workflow_state(
            retry_count=0,
            user_requirement=long_requirement,
            job_master_id="jm_005",
        )

        # Execute node
        result = await job_registration_node(state)

        # Verify Job was created
        assert result["job_id"] == "job_22222222-2222-2222-2222-222222222222"

        # Verify create_job was called and inspect job_name
        call_args = mock_client_instance.create_job.call_args
        job_name = call_args.kwargs["name"]

        # Job name should include first 50 chars of user_requirement
        assert "A" * 50 in job_name  # First 50 chars
        assert "A" * 60 not in job_name  # Not full 60 chars

        # Job name should include "Job:" prefix
        assert job_name.startswith("Job:")

        # Job name should include datetime (ISO format)
        # Example: "Job: AAAA... - 2025-10-24T12:34:56.123456"
        assert " - " in job_name
        assert "T" in job_name  # ISO datetime includes 'T'
