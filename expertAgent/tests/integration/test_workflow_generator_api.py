"""Integration tests for Workflow Generator API."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_task_data_fetcher():
    """Create mock TaskDataFetcher."""
    fetcher = MagicMock()
    fetcher.fetch_task_master_by_id = AsyncMock()
    fetcher.fetch_task_masters_by_job_master_id = AsyncMock()
    return fetcher


class TestWorkflowGeneratorAPI:
    """Test Workflow Generator API endpoints."""

    def test_workflow_generator_with_task_master_id(
        self, client, mock_task_data_fetcher
    ):
        """Test /v1/workflow-generator with task_master_id."""
        # Setup mock
        mock_task_data_fetcher.fetch_task_master_by_id.return_value = {
            "task_master_id": "456",
            "name": "Send email notification",
            "description": "Send email notification with report",
            "method": "POST",
            "url": "http://localhost:8104/api/v1/utility/gmail_send",
            "input_interface": {
                "id": "input_123",
                "name": "EmailInput",
                "description": "Email input schema",
                "schema": {"type": "object", "properties": {}},
            },
            "output_interface": {
                "id": "output_123",
                "name": "EmailOutput",
                "description": "Email output schema",
                "schema": {"type": "object", "properties": {}},
            },
        }

        with patch(
            "app.api.v1.workflow_generator_endpoints.TaskDataFetcher",
            return_value=mock_task_data_fetcher,
        ):
            # Execute
            response = client.post(
                "/aiagent-api/v1/workflow-generator",
                json={"task_master_id": 456},
            )

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["total_tasks"] == 1
            assert data["successful_tasks"] == 1
            assert data["failed_tasks"] == 0
            assert len(data["workflows"]) == 1
            assert data["workflows"][0]["task_master_id"] == 456
            assert data["workflows"][0]["task_name"] == "Send email notification"
            assert data["workflows"][0]["status"] == "success"
            assert "yaml_content" in data["workflows"][0]

    def test_workflow_generator_with_job_master_id(
        self, client, mock_task_data_fetcher
    ):
        """Test /v1/workflow-generator with job_master_id."""
        # Setup mock
        mock_task_data_fetcher.fetch_task_masters_by_job_master_id.return_value = [
            {
                "task_master_id": "task_1",
                "name": "Generate report",
                "description": "Generate PDF report",
                "method": "POST",
                "url": "http://localhost:8104/api/v1/report/generate",
                "order": 0,
                "input_interface": {
                    "id": "input_1",
                    "name": "ReportInput",
                    "description": "Report input",
                    "schema": {"type": "object"},
                },
                "output_interface": {
                    "id": "output_1",
                    "name": "ReportOutput",
                    "description": "Report output",
                    "schema": {"type": "object"},
                },
            },
            {
                "task_master_id": "task_2",
                "name": "Send email",
                "description": "Send email with report",
                "method": "POST",
                "url": "http://localhost:8104/api/v1/utility/gmail_send",
                "order": 1,
                "input_interface": {
                    "id": "input_2",
                    "name": "EmailInput",
                    "description": "Email input",
                    "schema": {"type": "object"},
                },
                "output_interface": {
                    "id": "output_2",
                    "name": "EmailOutput",
                    "description": "Email output",
                    "schema": {"type": "object"},
                },
            },
        ]

        with patch(
            "app.api.v1.workflow_generator_endpoints.TaskDataFetcher",
            return_value=mock_task_data_fetcher,
        ):
            # Execute
            response = client.post(
                "/aiagent-api/v1/workflow-generator",
                json={"job_master_id": 123},
            )

            # Verify
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert data["total_tasks"] == 2
            assert data["successful_tasks"] == 2
            assert data["failed_tasks"] == 0
            assert len(data["workflows"]) == 2
            assert data["workflows"][0]["task_name"] == "Generate report"
            assert data["workflows"][1]["task_name"] == "Send email"

    def test_workflow_generator_missing_both_ids(self, client):
        """Test /v1/workflow-generator with both IDs missing (422 error)."""
        # Execute
        response = client.post(
            "/aiagent-api/v1/workflow-generator",
            json={},
        )

        # Verify
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_workflow_generator_both_ids_provided(self, client):
        """Test /v1/workflow-generator with both IDs provided (422 error)."""
        # Execute
        response = client.post(
            "/aiagent-api/v1/workflow-generator",
            json={"job_master_id": 123, "task_master_id": 456},
        )

        # Verify
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data

    def test_workflow_generator_task_not_found(self, client, mock_task_data_fetcher):
        """Test /v1/workflow-generator with non-existent task (404 error)."""
        # Setup mock to raise JobqueueAPIError
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.jobqueue_client import (
            JobqueueAPIError,
        )

        mock_task_data_fetcher.fetch_task_master_by_id.side_effect = JobqueueAPIError(
            status_code=404,
            message="TaskMaster not found",
        )

        with patch(
            "app.api.v1.workflow_generator_endpoints.TaskDataFetcher",
            return_value=mock_task_data_fetcher,
        ):
            # Execute
            response = client.post(
                "/aiagent-api/v1/workflow-generator",
                json={"task_master_id": 999},
            )

            # Verify
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data
            assert "not found" in data["detail"].lower()

    def test_workflow_generator_jobqueue_api_error(
        self, client, mock_task_data_fetcher
    ):
        """Test /v1/workflow-generator with Jobqueue API error (500 error)."""
        # Setup mock to raise JobqueueAPIError
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.jobqueue_client import (
            JobqueueAPIError,
        )

        mock_task_data_fetcher.fetch_task_master_by_id.side_effect = JobqueueAPIError(
            status_code=500,
            message="Internal server error",
        )

        with patch(
            "app.api.v1.workflow_generator_endpoints.TaskDataFetcher",
            return_value=mock_task_data_fetcher,
        ):
            # Execute
            response = client.post(
                "/aiagent-api/v1/workflow-generator",
                json={"task_master_id": 456},
            )

            # Verify
            assert response.status_code == 500
            data = response.json()
            assert "detail" in data
            assert "Jobqueue API error" in data["detail"]
