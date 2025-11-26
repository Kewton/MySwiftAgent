"""Integration tests for Diagnostic API.

Issue #171: Diagnostic Information Retrieval API Implementation.
Tests for end-to-end API functionality.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.api.v1.diagnostic_endpoints import get_conversation_service
from app.main import app
from app.schemas.diagnostic import (
    DiagnosticInfo,
    DiagnosticListResponse,
)


@pytest.fixture
def mock_service():
    """Create a mock ConversationService for dependency injection."""
    from app.services.conversation_service import ConversationService

    service = MagicMock(spec=ConversationService)
    service.get_diagnostic_info = AsyncMock(return_value=None)
    service.list_diagnostics = AsyncMock(return_value=DiagnosticListResponse())
    return service


@pytest.fixture
def client_with_mock_service(mock_service):
    """Create test client with mocked service dependency."""
    app.dependency_overrides[get_conversation_service] = lambda: mock_service
    client = TestClient(app)
    yield client, mock_service
    app.dependency_overrides.clear()


class TestDiagnosticAPIEndpoints:
    """Integration tests for diagnostic API endpoints."""

    @pytest.mark.integration
    def test_get_diagnostic_info_not_found(self, client_with_mock_service):
        """Test GET /v1/chat/diagnostics/{conversation_id} returns 404 when not found."""
        client, mock_service = client_with_mock_service
        mock_service.get_diagnostic_info = AsyncMock(return_value=None)

        response = client.get("/v1/chat/diagnostics/nonexistent-conv")

        assert response.status_code == 404

    @pytest.mark.integration
    def test_get_diagnostic_info_success(self, client_with_mock_service):
        """Test GET /v1/chat/diagnostics/{conversation_id} returns info."""
        client, mock_service = client_with_mock_service
        expected_info = DiagnosticInfo(
            conversation_id="conv-123",
            job_id="job-456",
            user_id="user-789",
        )
        mock_service.get_diagnostic_info = AsyncMock(return_value=expected_info)

        response = client.get("/v1/chat/diagnostics/conv-123")

        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == "conv-123"
        assert data["job_id"] == "job-456"

    @pytest.mark.integration
    def test_list_diagnostics_empty(self, client_with_mock_service):
        """Test GET /v1/chat/diagnostics returns empty list."""
        client, mock_service = client_with_mock_service
        mock_service.list_diagnostics = AsyncMock(
            return_value=DiagnosticListResponse(items=[], total=0)
        )

        response = client.get("/v1/chat/diagnostics")

        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.integration
    def test_list_diagnostics_with_items(self, client_with_mock_service):
        """Test GET /v1/chat/diagnostics returns items."""
        client, mock_service = client_with_mock_service
        items = [
            DiagnosticInfo(conversation_id="conv-1"),
            DiagnosticInfo(conversation_id="conv-2"),
        ]
        mock_service.list_diagnostics = AsyncMock(
            return_value=DiagnosticListResponse(items=items, total=2)
        )

        response = client.get("/v1/chat/diagnostics")

        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 2

    @pytest.mark.integration
    def test_list_diagnostics_with_job_filter(self, client_with_mock_service):
        """Test GET /v1/chat/diagnostics?job_id=xxx filters by job."""
        client, mock_service = client_with_mock_service
        mock_service.list_diagnostics = AsyncMock(
            return_value=DiagnosticListResponse(items=[], total=0)
        )

        response = client.get("/v1/chat/diagnostics?job_id=job-123")

        assert response.status_code == 200
        # Verify the query was passed correctly
        call_args = mock_service.list_diagnostics.call_args
        query = call_args[0][0]
        assert query.job_id == "job-123"

    @pytest.mark.integration
    def test_list_diagnostics_with_user_filter(self, client_with_mock_service):
        """Test GET /v1/chat/diagnostics?user_id=xxx filters by user."""
        client, mock_service = client_with_mock_service
        mock_service.list_diagnostics = AsyncMock(
            return_value=DiagnosticListResponse(items=[], total=0)
        )

        response = client.get("/v1/chat/diagnostics?user_id=user-456")

        assert response.status_code == 200
        call_args = mock_service.list_diagnostics.call_args
        query = call_args[0][0]
        assert query.user_id == "user-456"

    @pytest.mark.integration
    def test_list_diagnostics_with_project_filter(self, client_with_mock_service):
        """Test GET /v1/chat/diagnostics?project_id=xxx filters by project."""
        client, mock_service = client_with_mock_service
        mock_service.list_diagnostics = AsyncMock(
            return_value=DiagnosticListResponse(items=[], total=0)
        )

        response = client.get("/v1/chat/diagnostics?project_id=project-789")

        assert response.status_code == 200
        call_args = mock_service.list_diagnostics.call_args
        query = call_args[0][0]
        assert query.project_id == "project-789"

    @pytest.mark.integration
    def test_list_diagnostics_with_workflow_filter(self, client_with_mock_service):
        """Test GET /v1/chat/diagnostics?workflow_id=xxx filters by workflow."""
        client, mock_service = client_with_mock_service
        mock_service.list_diagnostics = AsyncMock(
            return_value=DiagnosticListResponse(items=[], total=0)
        )

        response = client.get("/v1/chat/diagnostics?workflow_id=workflow-101")

        assert response.status_code == 200
        call_args = mock_service.list_diagnostics.call_args
        query = call_args[0][0]
        assert query.workflow_id == "workflow-101"

    @pytest.mark.integration
    def test_list_diagnostics_with_date_range(self, client_with_mock_service):
        """Test GET /v1/chat/diagnostics with date range filters."""
        client, mock_service = client_with_mock_service
        mock_service.list_diagnostics = AsyncMock(
            return_value=DiagnosticListResponse(items=[], total=0)
        )

        response = client.get(
            "/v1/chat/diagnostics"
            "?start_date=2025-01-01T00:00:00Z"
            "&end_date=2025-01-31T23:59:59Z"
        )

        assert response.status_code == 200
        call_args = mock_service.list_diagnostics.call_args
        query = call_args[0][0]
        assert query.start_date is not None
        assert query.end_date is not None

    @pytest.mark.integration
    def test_list_diagnostics_invalid_date_range(self, client_with_mock_service):
        """Test GET /v1/chat/diagnostics returns 400 for invalid date range."""
        client, mock_service = client_with_mock_service

        response = client.get(
            "/v1/chat/diagnostics"
            "?start_date=2025-02-01T00:00:00Z"
            "&end_date=2025-01-01T00:00:00Z"
        )

        assert response.status_code == 400

    @pytest.mark.integration
    def test_list_diagnostics_pagination(self, client_with_mock_service):
        """Test GET /v1/chat/diagnostics with pagination."""
        client, mock_service = client_with_mock_service
        mock_service.list_diagnostics = AsyncMock(
            return_value=DiagnosticListResponse(
                items=[],
                total=100,
                limit=10,
                offset=20,
                has_more=True,
            )
        )

        response = client.get("/v1/chat/diagnostics?limit=10&offset=20")

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 10
        assert data["offset"] == 20
        assert data["has_more"] is True

    @pytest.mark.integration
    def test_list_diagnostics_multiple_filters(self, client_with_mock_service):
        """Test GET /v1/chat/diagnostics with multiple filters."""
        client, mock_service = client_with_mock_service
        mock_service.list_diagnostics = AsyncMock(
            return_value=DiagnosticListResponse(items=[], total=0)
        )

        response = client.get(
            "/v1/chat/diagnostics"
            "?job_id=job-123"
            "&user_id=user-456"
            "&project_id=project-789"
        )

        assert response.status_code == 200
        call_args = mock_service.list_diagnostics.call_args
        query = call_args[0][0]
        assert query.job_id == "job-123"
        assert query.user_id == "user-456"
        assert query.project_id == "project-789"


class TestDiagnosticAPIResponseFormat:
    """Tests for API response format."""

    @pytest.mark.integration
    def test_diagnostic_info_response_format(self, client_with_mock_service):
        """Test that diagnostic info response has correct format."""
        client, mock_service = client_with_mock_service
        expected_info = DiagnosticInfo(
            conversation_id="conv-123",
            job_id="job-456",
            user_id="user-789",
            project_id="project-101",
            workflow_id="workflow-202",
            system_prompt="You are an assistant.",
            messages=[],
        )
        mock_service.get_diagnostic_info = AsyncMock(return_value=expected_info)

        response = client.get("/v1/chat/diagnostics/conv-123")

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "conversation_id" in data
        assert "messages" in data
        assert "token_usage" in data
        assert "langfuse_link" in data

        # Check optional fields
        assert "job_id" in data
        assert "user_id" in data
        assert "project_id" in data
        assert "workflow_id" in data
        assert "system_prompt" in data

    @pytest.mark.integration
    def test_diagnostic_list_response_format(self, client_with_mock_service):
        """Test that diagnostic list response has correct format."""
        client, mock_service = client_with_mock_service
        mock_service.list_diagnostics = AsyncMock(
            return_value=DiagnosticListResponse(
                items=[DiagnosticInfo(conversation_id="conv-1")],
                total=1,
                limit=100,
                offset=0,
                has_more=False,
            )
        )

        response = client.get("/v1/chat/diagnostics")

        assert response.status_code == 200
        data = response.json()

        # Check required fields
        assert "items" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "has_more" in data

        # Check types
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["limit"], int)
        assert isinstance(data["offset"], int)
        assert isinstance(data["has_more"], bool)


class TestDiagnosticAPIErrorHandling:
    """Tests for error handling."""

    @pytest.mark.integration
    def test_internal_server_error_handling(self, client_with_mock_service):
        """Test that internal errors are handled gracefully."""
        client, mock_service = client_with_mock_service
        mock_service.get_diagnostic_info = AsyncMock(
            side_effect=Exception("Database error")
        )

        response = client.get("/v1/chat/diagnostics/conv-123")

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data

    @pytest.mark.integration
    def test_list_internal_server_error(self, client_with_mock_service):
        """Test that list endpoint handles internal errors."""
        client, mock_service = client_with_mock_service
        mock_service.list_diagnostics = AsyncMock(
            side_effect=Exception("Database error")
        )

        response = client.get("/v1/chat/diagnostics")

        assert response.status_code == 500


class TestDiagnosticAPIBackwardCompatibility:
    """Tests for backward compatibility with existing operations."""

    @pytest.mark.integration
    def test_diagnostic_endpoint_registered(self, client_with_mock_service):
        """Test that diagnostic endpoints are properly registered."""
        client, mock_service = client_with_mock_service
        mock_service.list_diagnostics = AsyncMock(
            return_value=DiagnosticListResponse(items=[], total=0)
        )

        response = client.get("/v1/chat/diagnostics")

        # Endpoint should be accessible and return 200
        assert response.status_code == 200


class TestDiagnosticAPIPerformance:
    """Tests for performance requirements."""

    @pytest.mark.integration
    def test_single_retrieval_response_time(self, client_with_mock_service):
        """Test that single retrieval responds within 1 second."""
        import time

        client, mock_service = client_with_mock_service
        expected_info = DiagnosticInfo(conversation_id="conv-123")
        mock_service.get_diagnostic_info = AsyncMock(return_value=expected_info)

        start = time.time()
        response = client.get("/v1/chat/diagnostics/conv-123")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 1.0, f"Response time {elapsed}s exceeds 1 second limit"

    @pytest.mark.integration
    def test_list_retrieval_response_time(self, client_with_mock_service):
        """Test that list retrieval responds within 2 seconds."""
        import time

        client, mock_service = client_with_mock_service
        # Create 100 items to simulate a larger response
        items = [DiagnosticInfo(conversation_id=f"conv-{i}") for i in range(100)]
        mock_service.list_diagnostics = AsyncMock(
            return_value=DiagnosticListResponse(items=items, total=100)
        )

        start = time.time()
        response = client.get("/v1/chat/diagnostics")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 2.0, f"Response time {elapsed}s exceeds 2 second limit"
