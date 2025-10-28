"""Unit tests for TaskDataFetcher."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from aiagent.langgraph.workflowGeneratorAgents.utils.task_data_fetcher import (
    TaskDataFetcher,
)


@pytest.fixture
def mock_jobqueue_client():
    """Create mock JobqueueClient."""
    client = MagicMock()
    client.get_job_master = AsyncMock()
    client.list_workflow_tasks = AsyncMock()
    client.get_task_master = AsyncMock()
    client.get_interface_master = AsyncMock()
    return client


@pytest.fixture
def task_data_fetcher(mock_jobqueue_client):
    """Create TaskDataFetcher with mock client."""
    return TaskDataFetcher(jobqueue_client=mock_jobqueue_client)


class TestTaskDataFetcher:
    """Test TaskDataFetcher class."""

    @pytest.mark.asyncio
    async def test_fetch_task_master_by_id(
        self, task_data_fetcher, mock_jobqueue_client
    ):
        """Test fetch_task_master_by_id with single task."""
        # Setup mocks
        mock_jobqueue_client.get_task_master.return_value = {
            "id": "456",
            "name": "Send email notification",
            "description": "Send email notification with report",
            "method": "POST",
            "url": "http://localhost:8104/api/v1/utility/gmail_send",
            "input_interface_id": "input_123",
            "output_interface_id": "output_123",
            "timeout_sec": 30,
        }

        mock_jobqueue_client.get_interface_master.side_effect = [
            # Input interface
            {
                "id": "input_123",
                "name": "EmailInput",
                "description": "Email input schema",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string"},
                        "subject": {"type": "string"},
                        "body": {"type": "string"},
                    },
                },
                "output_schema": {},
            },
            # Output interface
            {
                "id": "output_123",
                "name": "EmailOutput",
                "description": "Email output schema",
                "input_schema": {},
                "output_schema": {
                    "type": "object",
                    "properties": {
                        "message_id": {"type": "string"},
                        "status": {"type": "string"},
                    },
                },
            },
        ]

        # Execute
        result = await task_data_fetcher.fetch_task_master_by_id(456)

        # Verify
        assert result["task_master_id"] == "456"
        assert result["name"] == "Send email notification"
        assert result["description"] == "Send email notification with report"
        assert result["input_interface"]["id"] == "input_123"
        assert result["input_interface"]["name"] == "EmailInput"
        assert result["output_interface"]["id"] == "output_123"
        assert result["output_interface"]["name"] == "EmailOutput"

        # Verify mock calls
        mock_jobqueue_client.get_task_master.assert_called_once_with(456)
        assert mock_jobqueue_client.get_interface_master.call_count == 2

    @pytest.mark.asyncio
    async def test_fetch_task_masters_by_job_master_id(
        self, task_data_fetcher, mock_jobqueue_client
    ):
        """Test fetch_task_masters_by_job_master_id with multiple tasks."""
        # Setup mocks
        mock_jobqueue_client.get_job_master.return_value = {
            "id": "123",
            "name": "Email Report Job",
            "description": "Generate and send email report",
        }

        mock_jobqueue_client.list_workflow_tasks.return_value = [
            {
                "task_master_id": "task_1",
                "order": 0,
                "is_required": True,
                "max_retries": 3,
            },
            {
                "task_master_id": "task_2",
                "order": 1,
                "is_required": True,
                "max_retries": 3,
            },
        ]

        # Mock get_task_master for task_1
        async def get_task_master_side_effect(task_id):
            if task_id == "task_1":
                return {
                    "id": "task_1",
                    "name": "Generate report",
                    "description": "Generate PDF report",
                    "method": "POST",
                    "url": "http://localhost:8104/api/v1/report/generate",
                    "input_interface_id": "input_1",
                    "output_interface_id": "output_1",
                    "timeout_sec": 60,
                }
            elif task_id == "task_2":
                return {
                    "id": "task_2",
                    "name": "Send email",
                    "description": "Send email with report",
                    "method": "POST",
                    "url": "http://localhost:8104/api/v1/utility/gmail_send",
                    "input_interface_id": "input_2",
                    "output_interface_id": "output_2",
                    "timeout_sec": 30,
                }

        mock_jobqueue_client.get_task_master.side_effect = get_task_master_side_effect

        # Mock get_interface_master
        async def get_interface_master_side_effect(interface_id):
            interfaces = {
                "input_1": {
                    "id": "input_1",
                    "name": "ReportInput",
                    "description": "Report input",
                    "input_schema": {"type": "object", "properties": {}},
                    "output_schema": {},
                },
                "output_1": {
                    "id": "output_1",
                    "name": "ReportOutput",
                    "description": "Report output",
                    "input_schema": {},
                    "output_schema": {
                        "type": "object",
                        "properties": {"pdf_url": {"type": "string"}},
                    },
                },
                "input_2": {
                    "id": "input_2",
                    "name": "EmailInput",
                    "description": "Email input",
                    "input_schema": {"type": "object", "properties": {}},
                    "output_schema": {},
                },
                "output_2": {
                    "id": "output_2",
                    "name": "EmailOutput",
                    "description": "Email output",
                    "input_schema": {},
                    "output_schema": {
                        "type": "object",
                        "properties": {"message_id": {"type": "string"}},
                    },
                },
            }
            return interfaces[interface_id]

        mock_jobqueue_client.get_interface_master.side_effect = (
            get_interface_master_side_effect
        )

        # Execute
        result = await task_data_fetcher.fetch_task_masters_by_job_master_id(123)

        # Verify
        assert len(result) == 2
        assert result[0]["task_master_id"] == "task_1"
        assert result[0]["name"] == "Generate report"
        assert result[0]["order"] == 0
        assert result[1]["task_master_id"] == "task_2"
        assert result[1]["name"] == "Send email"
        assert result[1]["order"] == 1

        # Verify mock calls
        mock_jobqueue_client.get_job_master.assert_called_once_with(123)
        mock_jobqueue_client.list_workflow_tasks.assert_called_once_with(123)
        assert mock_jobqueue_client.get_task_master.call_count == 2
        assert mock_jobqueue_client.get_interface_master.call_count == 4

    @pytest.mark.asyncio
    async def test_fetch_task_masters_sorted_by_order(
        self, task_data_fetcher, mock_jobqueue_client
    ):
        """Test that tasks are sorted by execution order."""
        # Setup mocks
        mock_jobqueue_client.get_job_master.return_value = {
            "id": "123",
            "name": "Test Job",
        }

        # Return tasks in reverse order to test sorting
        mock_jobqueue_client.list_workflow_tasks.return_value = [
            {"task_master_id": "task_2", "order": 2, "is_required": True},
            {"task_master_id": "task_1", "order": 1, "is_required": True},
            {"task_master_id": "task_0", "order": 0, "is_required": True},
        ]

        async def get_task_master_side_effect(task_id):
            return {
                "id": task_id,
                "name": f"Task {task_id}",
                "description": f"Description {task_id}",
                "method": "POST",
                "url": "http://localhost:8104/api/v1/test",
                "input_interface_id": f"input_{task_id}",
                "output_interface_id": f"output_{task_id}",
            }

        mock_jobqueue_client.get_task_master.side_effect = get_task_master_side_effect

        async def get_interface_master_side_effect(interface_id):
            return {
                "id": interface_id,
                "name": f"Interface {interface_id}",
                "description": "",
                "input_schema": {},
                "output_schema": {},
            }

        mock_jobqueue_client.get_interface_master.side_effect = (
            get_interface_master_side_effect
        )

        # Execute
        result = await task_data_fetcher.fetch_task_masters_by_job_master_id(123)

        # Verify sorting (should be task_0, task_1, task_2)
        assert len(result) == 3
        assert result[0]["task_master_id"] == "task_0"
        assert result[0]["order"] == 0
        assert result[1]["task_master_id"] == "task_1"
        assert result[1]["order"] == 1
        assert result[2]["task_master_id"] == "task_2"
        assert result[2]["order"] == 2
