"""Unit tests for ConversationService.

Issue #171: Diagnostic Information Retrieval API Implementation.
Tests for conversation service data access layer.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.conversation_metadata import ConversationMetadata
from app.schemas.diagnostic import (
    DiagnosticInfo,
    DiagnosticListQuery,
    DiagnosticListResponse,
)
from app.services.conversation_service import ConversationService


@pytest.fixture
def mock_store():
    """Create a mock ConversationStoreValkey."""
    store = MagicMock()
    store.get_conversation = AsyncMock(return_value=None)
    store.save_conversation = AsyncMock(return_value=True)
    store.list_conversations = AsyncMock(return_value=[])
    store.key_prefix = "conversation:"
    store._client = MagicMock()
    store._client._client = MagicMock()
    store._client._client.scan = AsyncMock(return_value=(0, []))
    return store


@pytest.fixture
def mock_index_manager():
    """Create a mock IndexManager."""
    manager = MagicMock()
    manager.add_to_indexes = AsyncMock(return_value=0)
    manager.remove_from_indexes = AsyncMock(return_value=0)
    manager.get_by_job_id = AsyncMock(return_value=set())
    manager.get_by_user_id = AsyncMock(return_value=set())
    manager.get_by_project_id = AsyncMock(return_value=set())
    manager.get_by_workflow_id = AsyncMock(return_value=set())
    manager.intersect_indexes = AsyncMock(return_value=set())
    return manager


@pytest.fixture
def conversation_service(mock_store, mock_index_manager):
    """Create a ConversationService instance with mocks."""
    return ConversationService(
        store=mock_store,
        index_manager=mock_index_manager,
        langfuse_host="http://localhost:3000",
    )


@pytest.fixture
def sample_conversation_data():
    """Create sample conversation data."""
    return {
        "conversation_id": "conv-123",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "Hi there!"},
        ],
        "metadata": {
            "trace_id": "trace-456",
            "prompt_version": "v1.0",
            "job_id": "job-789",
            "user_id": "user-101",
            "project_id": "project-202",
            "workflow_id": "workflow-303",
            "system_prompt": "You are a helpful assistant.",
            "total_tokens": 100,
            "input_tokens": 40,
            "output_tokens": 60,
            "created_at": "2025-01-15T10:30:00+00:00",
            "updated_at": "2025-01-15T10:35:00+00:00",
        },
    }


class TestConversationServiceInit:
    """Tests for ConversationService initialization."""

    @pytest.mark.unit
    def test_init_with_all_params(self, mock_store, mock_index_manager):
        """Test initialization with all parameters."""
        service = ConversationService(
            store=mock_store,
            index_manager=mock_index_manager,
            langfuse_host="http://langfuse.example.com",
        )

        assert service._store == mock_store
        assert service._index_manager == mock_index_manager
        assert service._langfuse_host == "http://langfuse.example.com"

    @pytest.mark.unit
    def test_init_minimal(self, mock_store):
        """Test initialization with minimal parameters."""
        service = ConversationService(store=mock_store)

        assert service._store == mock_store
        assert service._index_manager is None


class TestConversationServiceGetDiagnosticInfo:
    """Tests for getting diagnostic info for a single conversation."""

    @pytest.mark.unit
    async def test_get_diagnostic_info_success(
        self, conversation_service, mock_store, sample_conversation_data
    ):
        """Test successful retrieval of diagnostic info."""
        mock_store.get_conversation = AsyncMock(return_value=sample_conversation_data)

        result = await conversation_service.get_diagnostic_info("conv-123")

        assert result is not None
        assert result.conversation_id == "conv-123"
        assert result.job_id == "job-789"
        assert result.user_id == "user-101"
        assert result.project_id == "project-202"
        assert result.workflow_id == "workflow-303"
        assert len(result.messages) == 3
        assert result.token_usage.total_tokens == 100
        assert result.langfuse_link.trace_id == "trace-456"

    @pytest.mark.unit
    async def test_get_diagnostic_info_not_found(
        self, conversation_service, mock_store
    ):
        """Test retrieval when conversation not found."""
        mock_store.get_conversation = AsyncMock(return_value=None)

        result = await conversation_service.get_diagnostic_info("nonexistent")

        assert result is None

    @pytest.mark.unit
    async def test_get_diagnostic_info_langfuse_url(
        self, conversation_service, mock_store, sample_conversation_data
    ):
        """Test that Langfuse URL is correctly generated."""
        mock_store.get_conversation = AsyncMock(return_value=sample_conversation_data)

        result = await conversation_service.get_diagnostic_info("conv-123")

        assert result.langfuse_link.trace_url == "http://localhost:3000/trace/trace-456"

    @pytest.mark.unit
    async def test_get_diagnostic_info_minimal_data(
        self, conversation_service, mock_store
    ):
        """Test retrieval with minimal conversation data."""
        minimal_data = {
            "conversation_id": "conv-minimal",
            "messages": [],
            "metadata": {},
        }
        mock_store.get_conversation = AsyncMock(return_value=minimal_data)

        result = await conversation_service.get_diagnostic_info("conv-minimal")

        assert result is not None
        assert result.conversation_id == "conv-minimal"
        assert result.job_id is None
        assert result.user_id is None
        assert len(result.messages) == 0
        assert result.token_usage.total_tokens == 0


class TestConversationServiceListDiagnostics:
    """Tests for listing diagnostic info with filtering."""

    @pytest.mark.unit
    async def test_list_diagnostics_empty(
        self, conversation_service, mock_index_manager
    ):
        """Test listing when no conversations match."""
        query = DiagnosticListQuery(job_id="job-nonexistent")
        mock_index_manager.intersect_indexes = AsyncMock(return_value=set())

        result = await conversation_service.list_diagnostics(query)

        assert result.total == 0
        assert len(result.items) == 0
        assert result.has_more is False

    @pytest.mark.unit
    async def test_list_diagnostics_with_results(
        self, conversation_service, mock_store, mock_index_manager, sample_conversation_data
    ):
        """Test listing with matching conversations."""
        query = DiagnosticListQuery(job_id="job-789")
        mock_index_manager.intersect_indexes = AsyncMock(
            return_value={"conv-123", "conv-456"}
        )
        mock_store.get_conversation = AsyncMock(return_value=sample_conversation_data)

        result = await conversation_service.list_diagnostics(query)

        assert result.total == 2
        assert len(result.items) == 2

    @pytest.mark.unit
    async def test_list_diagnostics_pagination(
        self, conversation_service, mock_store, mock_index_manager, sample_conversation_data
    ):
        """Test pagination of results."""
        query = DiagnosticListQuery(limit=1, offset=0, job_id="job-789")
        mock_index_manager.intersect_indexes = AsyncMock(
            return_value={"conv-1", "conv-2", "conv-3"}
        )
        mock_store.get_conversation = AsyncMock(return_value=sample_conversation_data)

        result = await conversation_service.list_diagnostics(query)

        assert result.total == 3
        assert result.limit == 1
        assert result.offset == 0
        assert result.has_more is True

    @pytest.mark.unit
    async def test_list_diagnostics_with_offset(
        self, conversation_service, mock_store, mock_index_manager, sample_conversation_data
    ):
        """Test pagination with offset."""
        query = DiagnosticListQuery(limit=10, offset=2, job_id="job-789")
        mock_index_manager.intersect_indexes = AsyncMock(
            return_value={"conv-1", "conv-2", "conv-3", "conv-4", "conv-5"}
        )
        mock_store.get_conversation = AsyncMock(return_value=sample_conversation_data)

        result = await conversation_service.list_diagnostics(query)

        assert result.total == 5
        assert result.offset == 2
        assert len(result.items) == 3


class TestConversationServiceSaveWithMetadata:
    """Tests for saving conversations with metadata."""

    @pytest.mark.unit
    async def test_save_with_metadata_success(
        self, conversation_service, mock_store, mock_index_manager
    ):
        """Test successful save with metadata."""
        metadata = ConversationMetadata(
            trace_id="trace-123",
            prompt_version="v1.0",
            job_id="job-456",
            user_id="user-789",
            project_id="project-101",
            workflow_id="workflow-202",
            created_at=datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        )
        messages = [{"role": "user", "content": "Hello"}]

        result = await conversation_service.save_with_metadata(
            conversation_id="conv-new",
            messages=messages,
            metadata=metadata,
        )

        assert result is True
        mock_store.save_conversation.assert_awaited_once()
        mock_index_manager.add_to_indexes.assert_awaited_once()

    @pytest.mark.unit
    async def test_save_with_metadata_no_index_manager(self, mock_store):
        """Test save without index manager."""
        service = ConversationService(store=mock_store)
        metadata = ConversationMetadata(
            job_id="job-456",
        )
        messages = [{"role": "user", "content": "Hello"}]

        result = await service.save_with_metadata(
            conversation_id="conv-new",
            messages=messages,
            metadata=metadata,
        )

        assert result is True
        mock_store.save_conversation.assert_awaited_once()

    @pytest.mark.unit
    async def test_save_with_metadata_store_failure(
        self, conversation_service, mock_store, mock_index_manager
    ):
        """Test when store save fails."""
        mock_store.save_conversation = AsyncMock(return_value=False)
        metadata = ConversationMetadata(job_id="job-456")
        messages = [{"role": "user", "content": "Hello"}]

        result = await conversation_service.save_with_metadata(
            conversation_id="conv-new",
            messages=messages,
            metadata=metadata,
        )

        assert result is False
        mock_index_manager.add_to_indexes.assert_not_awaited()


class TestConversationServiceDatetimeParsing:
    """Tests for datetime parsing."""

    @pytest.mark.unit
    def test_parse_datetime_none(self, conversation_service):
        """Test parsing None returns None."""
        result = conversation_service._parse_datetime(None)
        assert result is None

    @pytest.mark.unit
    def test_parse_datetime_datetime_object(self, conversation_service):
        """Test parsing datetime object returns same object."""
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        result = conversation_service._parse_datetime(dt)
        assert result == dt

    @pytest.mark.unit
    def test_parse_datetime_iso_string(self, conversation_service):
        """Test parsing ISO format string."""
        result = conversation_service._parse_datetime("2025-01-15T10:30:00+00:00")
        assert result is not None
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15

    @pytest.mark.unit
    def test_parse_datetime_iso_string_z(self, conversation_service):
        """Test parsing ISO format string with Z suffix."""
        result = conversation_service._parse_datetime("2025-01-15T10:30:00Z")
        assert result is not None
        assert result.year == 2025

    @pytest.mark.unit
    def test_parse_datetime_invalid_string(self, conversation_service):
        """Test parsing invalid string returns None."""
        result = conversation_service._parse_datetime("not-a-date")
        assert result is None


class TestConversationServiceDateFilter:
    """Tests for date filtering."""

    @pytest.mark.unit
    def test_matches_date_filter_no_filter(self, conversation_service):
        """Test matching when no date filter specified."""
        query = DiagnosticListQuery()
        info = DiagnosticInfo(
            conversation_id="conv-123",
            created_at=datetime(2025, 1, 15, tzinfo=timezone.utc),
        )

        result = conversation_service._matches_date_filter(info, query)

        assert result is True

    @pytest.mark.unit
    def test_matches_date_filter_no_created_at(self, conversation_service):
        """Test matching when conversation has no created_at."""
        query = DiagnosticListQuery(
            start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        info = DiagnosticInfo(conversation_id="conv-123")

        result = conversation_service._matches_date_filter(info, query)

        assert result is True

    @pytest.mark.unit
    def test_matches_date_filter_in_range(self, conversation_service):
        """Test matching when date is in range."""
        query = DiagnosticListQuery(
            start_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2025, 1, 31, tzinfo=timezone.utc),
        )
        info = DiagnosticInfo(
            conversation_id="conv-123",
            created_at=datetime(2025, 1, 15, tzinfo=timezone.utc),
        )

        result = conversation_service._matches_date_filter(info, query)

        assert result is True

    @pytest.mark.unit
    def test_matches_date_filter_before_start(self, conversation_service):
        """Test not matching when date is before start."""
        query = DiagnosticListQuery(
            start_date=datetime(2025, 2, 1, tzinfo=timezone.utc),
        )
        info = DiagnosticInfo(
            conversation_id="conv-123",
            created_at=datetime(2025, 1, 15, tzinfo=timezone.utc),
        )

        result = conversation_service._matches_date_filter(info, query)

        assert result is False

    @pytest.mark.unit
    def test_matches_date_filter_after_end(self, conversation_service):
        """Test not matching when date is after end."""
        query = DiagnosticListQuery(
            end_date=datetime(2025, 1, 1, tzinfo=timezone.utc),
        )
        info = DiagnosticInfo(
            conversation_id="conv-123",
            created_at=datetime(2025, 1, 15, tzinfo=timezone.utc),
        )

        result = conversation_service._matches_date_filter(info, query)

        assert result is False


class TestConversationServiceBuildDiagnosticInfo:
    """Tests for building diagnostic info from raw data."""

    @pytest.mark.unit
    def test_build_diagnostic_info_full(
        self, conversation_service, sample_conversation_data
    ):
        """Test building diagnostic info with full data."""
        result = conversation_service._build_diagnostic_info(
            "conv-123", sample_conversation_data
        )

        assert result.conversation_id == "conv-123"
        assert result.job_id == "job-789"
        assert result.user_id == "user-101"
        assert result.project_id == "project-202"
        assert result.workflow_id == "workflow-303"
        assert result.system_prompt == "You are a helpful assistant."
        assert result.token_usage.total_tokens == 100
        assert result.token_usage.input_tokens == 40
        assert result.token_usage.output_tokens == 60
        assert result.langfuse_link.trace_id == "trace-456"
        assert result.prompt_version == "v1.0"

    @pytest.mark.unit
    def test_build_diagnostic_info_minimal(self, conversation_service):
        """Test building diagnostic info with minimal data."""
        data = {
            "conversation_id": "conv-minimal",
            "messages": [],
            "metadata": {},
        }

        result = conversation_service._build_diagnostic_info("conv-minimal", data)

        assert result.conversation_id == "conv-minimal"
        assert result.job_id is None
        assert result.token_usage.total_tokens == 0
        assert result.langfuse_link.trace_id is None
        assert result.langfuse_link.trace_url is None

    @pytest.mark.unit
    def test_build_diagnostic_info_extra_metadata(self, conversation_service):
        """Test that extra metadata is preserved."""
        data = {
            "conversation_id": "conv-123",
            "messages": [],
            "metadata": {
                "custom_field": "custom_value",
                "another_field": 123,
            },
        }

        result = conversation_service._build_diagnostic_info("conv-123", data)

        assert result.metadata["custom_field"] == "custom_value"
        assert result.metadata["another_field"] == 123
