"""Unit tests for diagnostic API endpoints.

Issue #171: Diagnostic Information Retrieval API Implementation.
Tests for REST API endpoints.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.v1.diagnostic_endpoints import (
    get_conversation_service,
    get_diagnostic_info,
    list_diagnostics,
    router,
)
from app.schemas.diagnostic import (
    DiagnosticInfo,
    DiagnosticListQuery,
    DiagnosticListResponse,
)
from app.services.conversation_service import ConversationService


@pytest.fixture
def mock_conversation_service():
    """Create a mock ConversationService."""
    service = MagicMock(spec=ConversationService)
    service.get_diagnostic_info = AsyncMock(return_value=None)
    service.list_diagnostics = AsyncMock(return_value=DiagnosticListResponse())
    return service


@pytest.fixture
def sample_diagnostic_info():
    """Create sample diagnostic info."""
    return DiagnosticInfo(
        conversation_id="conv-123",
        job_id="job-456",
        user_id="user-789",
        project_id="project-101",
        workflow_id="workflow-202",
    )


class TestGetDiagnosticInfo:
    """Tests for get_diagnostic_info endpoint."""

    @pytest.mark.unit
    async def test_get_diagnostic_info_success(
        self, mock_conversation_service, sample_diagnostic_info
    ):
        """Test successful retrieval of diagnostic info."""
        mock_conversation_service.get_diagnostic_info = AsyncMock(
            return_value=sample_diagnostic_info
        )

        result = await get_diagnostic_info(
            conversation_id="conv-123",
            service=mock_conversation_service,
        )

        assert result.conversation_id == "conv-123"
        assert result.job_id == "job-456"

    @pytest.mark.unit
    async def test_get_diagnostic_info_not_found(self, mock_conversation_service):
        """Test 404 when conversation not found."""
        mock_conversation_service.get_diagnostic_info = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_diagnostic_info(
                conversation_id="nonexistent",
                service=mock_conversation_service,
            )

        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail

    @pytest.mark.unit
    async def test_get_diagnostic_info_internal_error(self, mock_conversation_service):
        """Test 500 on internal error."""
        mock_conversation_service.get_diagnostic_info = AsyncMock(
            side_effect=Exception("Database error")
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_diagnostic_info(
                conversation_id="conv-123",
                service=mock_conversation_service,
            )

        assert exc_info.value.status_code == 500


class TestListDiagnostics:
    """Tests for list_diagnostics endpoint."""

    @pytest.mark.unit
    async def test_list_diagnostics_success(self, mock_conversation_service):
        """Test successful listing of diagnostics."""
        expected = DiagnosticListResponse(
            items=[DiagnosticInfo(conversation_id="conv-1")],
            total=1,
        )
        mock_conversation_service.list_diagnostics = AsyncMock(return_value=expected)

        result = await list_diagnostics(
            job_id=None,
            user_id=None,
            project_id=None,
            workflow_id=None,
            start_date=None,
            end_date=None,
            limit=100,
            offset=0,
            service=mock_conversation_service,
        )

        assert result.total == 1
        assert len(result.items) == 1

    @pytest.mark.unit
    async def test_list_diagnostics_with_job_filter(self, mock_conversation_service):
        """Test listing with job_id filter."""
        expected = DiagnosticListResponse(
            items=[DiagnosticInfo(conversation_id="conv-1", job_id="job-123")],
            total=1,
        )
        mock_conversation_service.list_diagnostics = AsyncMock(return_value=expected)

        result = await list_diagnostics(
            job_id="job-123",
            user_id=None,
            project_id=None,
            workflow_id=None,
            start_date=None,
            end_date=None,
            limit=100,
            offset=0,
            service=mock_conversation_service,
        )

        mock_conversation_service.list_diagnostics.assert_awaited_once()
        call_args = mock_conversation_service.list_diagnostics.call_args
        query = call_args[0][0]
        assert query.job_id == "job-123"

    @pytest.mark.unit
    async def test_list_diagnostics_with_user_filter(self, mock_conversation_service):
        """Test listing with user_id filter."""
        expected = DiagnosticListResponse(items=[], total=0)
        mock_conversation_service.list_diagnostics = AsyncMock(return_value=expected)

        await list_diagnostics(
            job_id=None,
            user_id="user-456",
            project_id=None,
            workflow_id=None,
            start_date=None,
            end_date=None,
            limit=100,
            offset=0,
            service=mock_conversation_service,
        )

        call_args = mock_conversation_service.list_diagnostics.call_args
        query = call_args[0][0]
        assert query.user_id == "user-456"

    @pytest.mark.unit
    async def test_list_diagnostics_with_date_range(self, mock_conversation_service):
        """Test listing with date range filter."""
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 31, tzinfo=timezone.utc)
        expected = DiagnosticListResponse(items=[], total=0)
        mock_conversation_service.list_diagnostics = AsyncMock(return_value=expected)

        await list_diagnostics(
            job_id=None,
            user_id=None,
            project_id=None,
            workflow_id=None,
            start_date=start,
            end_date=end,
            limit=100,
            offset=0,
            service=mock_conversation_service,
        )

        call_args = mock_conversation_service.list_diagnostics.call_args
        query = call_args[0][0]
        assert query.start_date == start
        assert query.end_date == end

    @pytest.mark.unit
    async def test_list_diagnostics_invalid_date_range(self, mock_conversation_service):
        """Test 400 when start_date is after end_date."""
        start = datetime(2025, 2, 1, tzinfo=timezone.utc)
        end = datetime(2025, 1, 1, tzinfo=timezone.utc)

        with pytest.raises(HTTPException) as exc_info:
            await list_diagnostics(
                job_id=None,
                user_id=None,
                project_id=None,
                workflow_id=None,
                start_date=start,
                end_date=end,
                limit=100,
                offset=0,
                service=mock_conversation_service,
            )

        assert exc_info.value.status_code == 400
        assert "start_date must be before" in exc_info.value.detail

    @pytest.mark.unit
    async def test_list_diagnostics_pagination(self, mock_conversation_service):
        """Test listing with pagination."""
        expected = DiagnosticListResponse(
            items=[],
            total=100,
            limit=10,
            offset=20,
            has_more=True,
        )
        mock_conversation_service.list_diagnostics = AsyncMock(return_value=expected)

        result = await list_diagnostics(
            job_id=None,
            user_id=None,
            project_id=None,
            workflow_id=None,
            start_date=None,
            end_date=None,
            limit=10,
            offset=20,
            service=mock_conversation_service,
        )

        assert result.limit == 10
        assert result.offset == 20
        assert result.has_more is True

    @pytest.mark.unit
    async def test_list_diagnostics_internal_error(self, mock_conversation_service):
        """Test 500 on internal error."""
        mock_conversation_service.list_diagnostics = AsyncMock(
            side_effect=Exception("Database error")
        )

        with pytest.raises(HTTPException) as exc_info:
            await list_diagnostics(
                job_id=None,
                user_id=None,
                project_id=None,
                workflow_id=None,
                start_date=None,
                end_date=None,
                limit=100,
                offset=0,
                service=mock_conversation_service,
            )

        assert exc_info.value.status_code == 500


class TestGetConversationService:
    """Tests for get_conversation_service dependency."""

    @pytest.mark.unit
    async def test_get_conversation_service_connection_error(self):
        """Test 503 when Valkey connection fails."""
        # Import ValkeyConnectionError for the test
        from app.services.valkey_client import ValkeyConnectionError

        with patch(
            "app.api.v1.diagnostic_endpoints.ConversationStoreValkey"
        ) as mock_store_class:
            mock_store = MagicMock()
            mock_store.connect = AsyncMock(
                side_effect=ValkeyConnectionError("Connection refused")
            )
            mock_store_class.return_value = mock_store

            with pytest.raises(HTTPException) as exc_info:
                await get_conversation_service()

            # Should raise 503 due to connection error
            assert exc_info.value.status_code == 503


class TestRouterConfiguration:
    """Tests for router configuration."""

    @pytest.mark.unit
    def test_router_prefix(self):
        """Test router has correct prefix."""
        assert router.prefix == "/chat/diagnostics"

    @pytest.mark.unit
    def test_router_tags(self):
        """Test router has correct tags."""
        assert "Diagnostics" in router.tags
