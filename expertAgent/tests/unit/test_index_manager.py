"""Unit tests for IndexManager.

Issue #171: Diagnostic Information Retrieval API Implementation.
Tests for secondary index management functionality.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.index_manager import IndexManager


@pytest.fixture
def mock_valkey_client():
    """Create a mock ValkeyClient."""
    client = MagicMock()
    client._client = MagicMock()
    client._client.sadd = AsyncMock(return_value=1)
    client._client.srem = AsyncMock(return_value=1)
    client._client.smembers = AsyncMock(return_value=set())
    client._client.expire = AsyncMock(return_value=True)
    client._client.keys = AsyncMock(return_value=[])
    return client


@pytest.fixture
def index_manager(mock_valkey_client):
    """Create an IndexManager instance with mock client."""
    return IndexManager(mock_valkey_client)


class TestIndexManagerInit:
    """Tests for IndexManager initialization."""

    @pytest.mark.unit
    def test_init_default_values(self, mock_valkey_client):
        """Test initialization with default values."""
        manager = IndexManager(mock_valkey_client)

        assert manager.index_prefix == "idx:"
        assert manager.index_ttl == 604800  # 7 days

    @pytest.mark.unit
    def test_init_custom_values(self, mock_valkey_client):
        """Test initialization with custom values."""
        manager = IndexManager(
            mock_valkey_client,
            index_prefix="custom:",
            index_ttl=3600,
        )

        assert manager.index_prefix == "custom:"
        assert manager.index_ttl == 3600


class TestIndexManagerKeys:
    """Tests for index key generation."""

    @pytest.mark.unit
    def test_get_index_key_job(self, index_manager):
        """Test job index key generation."""
        key = index_manager._get_index_key("job", "job-123")
        assert key == "idx:job:job-123"

    @pytest.mark.unit
    def test_get_index_key_user(self, index_manager):
        """Test user index key generation."""
        key = index_manager._get_index_key("user", "user-456")
        assert key == "idx:user:user-456"

    @pytest.mark.unit
    def test_get_index_key_project(self, index_manager):
        """Test project index key generation."""
        key = index_manager._get_index_key("project", "project-789")
        assert key == "idx:project:project-789"

    @pytest.mark.unit
    def test_get_index_key_workflow(self, index_manager):
        """Test workflow index key generation."""
        key = index_manager._get_index_key("workflow", "workflow-321")
        assert key == "idx:workflow:workflow-321"

    @pytest.mark.unit
    def test_get_index_key_date(self, index_manager):
        """Test date index key generation."""
        key = index_manager._get_index_key("date", "2025-01-15")
        assert key == "idx:date:2025-01-15"


class TestIndexManagerAddToIndexes:
    """Tests for adding conversations to indexes."""

    @pytest.mark.unit
    async def test_add_to_indexes_job_only(self, index_manager, mock_valkey_client):
        """Test adding to job index only."""
        result = await index_manager.add_to_indexes(
            conversation_id="conv-123",
            job_id="job-456",
        )

        assert result == 1
        mock_valkey_client._client.sadd.assert_awaited_once()

    @pytest.mark.unit
    async def test_add_to_indexes_multiple(self, index_manager, mock_valkey_client):
        """Test adding to multiple indexes."""
        result = await index_manager.add_to_indexes(
            conversation_id="conv-123",
            job_id="job-456",
            user_id="user-789",
            project_id="project-101",
        )

        assert result == 3
        assert mock_valkey_client._client.sadd.await_count == 3

    @pytest.mark.unit
    async def test_add_to_indexes_with_date(self, index_manager, mock_valkey_client):
        """Test adding to indexes with date."""
        created_at = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        result = await index_manager.add_to_indexes(
            conversation_id="conv-123",
            job_id="job-456",
            created_at=created_at,
        )

        assert result == 2
        assert mock_valkey_client._client.sadd.await_count == 2

    @pytest.mark.unit
    async def test_add_to_indexes_all_filters(self, index_manager, mock_valkey_client):
        """Test adding to all index types."""
        created_at = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        result = await index_manager.add_to_indexes(
            conversation_id="conv-123",
            job_id="job-456",
            user_id="user-789",
            project_id="project-101",
            workflow_id="workflow-202",
            created_at=created_at,
        )

        assert result == 5
        assert mock_valkey_client._client.sadd.await_count == 5

    @pytest.mark.unit
    async def test_add_to_indexes_no_filters(self, index_manager, mock_valkey_client):
        """Test adding with no filters returns 0."""
        result = await index_manager.add_to_indexes(
            conversation_id="conv-123",
        )

        assert result == 0
        mock_valkey_client._client.sadd.assert_not_awaited()


class TestIndexManagerRemoveFromIndexes:
    """Tests for removing conversations from indexes."""

    @pytest.mark.unit
    async def test_remove_from_indexes(self, index_manager, mock_valkey_client):
        """Test removing from indexes."""
        result = await index_manager.remove_from_indexes(
            conversation_id="conv-123",
            job_id="job-456",
            user_id="user-789",
        )

        assert result == 2
        assert mock_valkey_client._client.srem.await_count == 2


class TestIndexManagerGetByFilters:
    """Tests for getting conversations by various filters."""

    @pytest.mark.unit
    async def test_get_by_job_id(self, index_manager, mock_valkey_client):
        """Test getting conversations by job ID."""
        mock_valkey_client._client.smembers = AsyncMock(
            return_value={b"conv-1", b"conv-2", b"conv-3"}
        )

        result = await index_manager.get_by_job_id("job-456")

        assert result == {"conv-1", "conv-2", "conv-3"}

    @pytest.mark.unit
    async def test_get_by_user_id(self, index_manager, mock_valkey_client):
        """Test getting conversations by user ID."""
        mock_valkey_client._client.smembers = AsyncMock(
            return_value={b"conv-1", b"conv-2"}
        )

        result = await index_manager.get_by_user_id("user-789")

        assert result == {"conv-1", "conv-2"}

    @pytest.mark.unit
    async def test_get_by_project_id(self, index_manager, mock_valkey_client):
        """Test getting conversations by project ID."""
        mock_valkey_client._client.smembers = AsyncMock(
            return_value={b"conv-1"}
        )

        result = await index_manager.get_by_project_id("project-101")

        assert result == {"conv-1"}

    @pytest.mark.unit
    async def test_get_by_workflow_id(self, index_manager, mock_valkey_client):
        """Test getting conversations by workflow ID."""
        mock_valkey_client._client.smembers = AsyncMock(
            return_value={b"conv-4", b"conv-5"}
        )

        result = await index_manager.get_by_workflow_id("workflow-202")

        assert result == {"conv-4", "conv-5"}

    @pytest.mark.unit
    async def test_get_by_date(self, index_manager, mock_valkey_client):
        """Test getting conversations by date."""
        mock_valkey_client._client.smembers = AsyncMock(
            return_value={b"conv-1", b"conv-2"}
        )

        date = datetime(2025, 1, 15, tzinfo=timezone.utc)
        result = await index_manager.get_by_date(date)

        assert result == {"conv-1", "conv-2"}

    @pytest.mark.unit
    async def test_get_by_empty_set(self, index_manager, mock_valkey_client):
        """Test getting from empty index returns empty set."""
        mock_valkey_client._client.smembers = AsyncMock(return_value=set())

        result = await index_manager.get_by_job_id("nonexistent-job")

        assert result == set()


class TestIndexManagerIntersect:
    """Tests for intersection operations."""

    @pytest.mark.unit
    async def test_intersect_indexes_single_filter(
        self, index_manager, mock_valkey_client
    ):
        """Test intersection with single filter."""
        mock_valkey_client._client.smembers = AsyncMock(
            return_value={b"conv-1", b"conv-2"}
        )

        result = await index_manager.intersect_indexes(job_id="job-456")

        assert result == {"conv-1", "conv-2"}

    @pytest.mark.unit
    async def test_intersect_indexes_multiple_filters(
        self, index_manager, mock_valkey_client
    ):
        """Test intersection with multiple filters."""
        # Mock smembers to return different sets for different calls
        call_count = 0
        async def mock_smembers(key):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {b"conv-1", b"conv-2", b"conv-3"}
            else:
                return {b"conv-2", b"conv-3", b"conv-4"}

        mock_valkey_client._client.smembers = mock_smembers

        result = await index_manager.intersect_indexes(
            job_id="job-456",
            user_id="user-789",
        )

        assert result == {"conv-2", "conv-3"}

    @pytest.mark.unit
    async def test_intersect_indexes_no_filters(
        self, index_manager, mock_valkey_client
    ):
        """Test intersection with no filters returns empty set."""
        result = await index_manager.intersect_indexes()

        assert result == set()


class TestIndexManagerStats:
    """Tests for index statistics."""

    @pytest.mark.unit
    async def test_get_index_stats(self, index_manager, mock_valkey_client):
        """Test getting index statistics."""
        mock_valkey_client._client.keys = AsyncMock(
            return_value=[
                b"idx:job:job-1",
                b"idx:job:job-2",
                b"idx:user:user-1",
                b"idx:project:proj-1",
                b"idx:workflow:wf-1",
                b"idx:date:2025-01-15",
            ]
        )

        stats = await index_manager.get_index_stats()

        assert stats["total_indexes"] == 6
        assert stats["job_indexes"] == 2
        assert stats["user_indexes"] == 1
        assert stats["project_indexes"] == 1
        assert stats["workflow_indexes"] == 1
        assert stats["date_indexes"] == 1

    @pytest.mark.unit
    async def test_get_index_stats_empty(self, index_manager, mock_valkey_client):
        """Test getting index statistics when empty."""
        mock_valkey_client._client.keys = AsyncMock(return_value=[])

        stats = await index_manager.get_index_stats()

        assert stats["total_indexes"] == 0

    @pytest.mark.unit
    async def test_get_index_stats_client_not_connected(
        self, index_manager, mock_valkey_client
    ):
        """Test stats when client not connected."""
        mock_valkey_client._client = None

        stats = await index_manager.get_index_stats()

        assert "error" in stats


class TestIndexManagerErrorHandling:
    """Tests for error handling."""

    @pytest.mark.unit
    async def test_add_to_set_error(self, index_manager, mock_valkey_client):
        """Test error handling in _add_to_set."""
        mock_valkey_client._client.sadd = AsyncMock(
            side_effect=Exception("Connection error")
        )

        result = await index_manager._add_to_set("idx:test:key", "member")

        assert result is False

    @pytest.mark.unit
    async def test_remove_from_set_error(self, index_manager, mock_valkey_client):
        """Test error handling in _remove_from_set."""
        mock_valkey_client._client.srem = AsyncMock(
            side_effect=Exception("Connection error")
        )

        result = await index_manager._remove_from_set("idx:test:key", "member")

        assert result is False

    @pytest.mark.unit
    async def test_get_set_members_error(self, index_manager, mock_valkey_client):
        """Test error handling in _get_set_members."""
        mock_valkey_client._client.smembers = AsyncMock(
            side_effect=Exception("Connection error")
        )

        result = await index_manager._get_set_members("idx:test:key")

        assert result == set()

    @pytest.mark.unit
    async def test_add_to_set_client_not_connected(
        self, index_manager, mock_valkey_client
    ):
        """Test _add_to_set when client not connected."""
        mock_valkey_client._client = None

        result = await index_manager._add_to_set("idx:test:key", "member")

        assert result is False

    @pytest.mark.unit
    async def test_get_set_members_client_not_connected(
        self, index_manager, mock_valkey_client
    ):
        """Test _get_set_members when client not connected."""
        mock_valkey_client._client = None

        result = await index_manager._get_set_members("idx:test:key")

        assert result == set()

    @pytest.mark.unit
    async def test_remove_from_set_client_not_connected(
        self, index_manager, mock_valkey_client
    ):
        """Test _remove_from_set when client not connected."""
        mock_valkey_client._client = None

        result = await index_manager._remove_from_set("idx:test:key", "member")

        assert result is False


class TestIndexManagerDateRange:
    """Tests for date range operations."""

    @pytest.mark.unit
    async def test_get_by_date_range_single_day(
        self, index_manager, mock_valkey_client
    ):
        """Test getting conversations for a single day range."""
        mock_valkey_client._client.smembers = AsyncMock(
            return_value={b"conv-1", b"conv-2"}
        )

        start = datetime(2025, 1, 15, tzinfo=timezone.utc)
        end = datetime(2025, 1, 15, tzinfo=timezone.utc)

        result = await index_manager.get_by_date_range(start, end)

        assert result == {"conv-1", "conv-2"}

    @pytest.mark.unit
    async def test_get_by_date_range_multiple_days(
        self, index_manager, mock_valkey_client
    ):
        """Test getting conversations for multiple days."""
        call_count = 0

        async def mock_smembers(key):
            nonlocal call_count
            call_count += 1
            if "2025-01-15" in key:
                return {b"conv-1", b"conv-2"}
            elif "2025-01-16" in key:
                return {b"conv-2", b"conv-3"}
            elif "2025-01-17" in key:
                return {b"conv-4"}
            return set()

        mock_valkey_client._client.smembers = mock_smembers

        start = datetime(2025, 1, 15, tzinfo=timezone.utc)
        end = datetime(2025, 1, 17, tzinfo=timezone.utc)

        result = await index_manager.get_by_date_range(start, end)

        assert result == {"conv-1", "conv-2", "conv-3", "conv-4"}

    @pytest.mark.unit
    async def test_get_by_date_range_month_overflow(
        self, index_manager, mock_valkey_client
    ):
        """Test date range across month boundary."""
        mock_valkey_client._client.smembers = AsyncMock(return_value=set())

        start = datetime(2025, 1, 30, tzinfo=timezone.utc)
        end = datetime(2025, 2, 2, tzinfo=timezone.utc)

        result = await index_manager.get_by_date_range(start, end)

        # Should have made 4 calls (Jan 30, 31, Feb 1, 2)
        assert mock_valkey_client._client.smembers.await_count == 4

    @pytest.mark.unit
    async def test_get_by_date_range_year_overflow(
        self, index_manager, mock_valkey_client
    ):
        """Test date range across year boundary."""
        mock_valkey_client._client.smembers = AsyncMock(return_value=set())

        start = datetime(2024, 12, 30, tzinfo=timezone.utc)
        end = datetime(2025, 1, 2, tzinfo=timezone.utc)

        result = await index_manager.get_by_date_range(start, end)

        # Should have made 4 calls (Dec 30, 31, Jan 1, 2)
        assert mock_valkey_client._client.smembers.await_count == 4


class TestIndexManagerRemoveFromIndexesExtended:
    """Extended tests for remove_from_indexes method."""

    @pytest.mark.unit
    async def test_remove_from_indexes_all_filters(
        self, index_manager, mock_valkey_client
    ):
        """Test removing from all index types."""
        created_at = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        result = await index_manager.remove_from_indexes(
            conversation_id="conv-123",
            job_id="job-456",
            user_id="user-789",
            project_id="project-101",
            workflow_id="workflow-202",
            created_at=created_at,
        )

        assert result == 5
        assert mock_valkey_client._client.srem.await_count == 5

    @pytest.mark.unit
    async def test_remove_from_indexes_no_filters(
        self, index_manager, mock_valkey_client
    ):
        """Test removing with no filters returns 0."""
        result = await index_manager.remove_from_indexes(
            conversation_id="conv-123",
        )

        assert result == 0
        mock_valkey_client._client.srem.assert_not_awaited()

    @pytest.mark.unit
    async def test_remove_from_indexes_with_date(
        self, index_manager, mock_valkey_client
    ):
        """Test removing from date index."""
        created_at = datetime(2025, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

        result = await index_manager.remove_from_indexes(
            conversation_id="conv-123",
            created_at=created_at,
        )

        assert result == 1
        mock_valkey_client._client.srem.assert_awaited_once()


class TestIndexManagerIntersectExtended:
    """Extended tests for intersect_indexes method."""

    @pytest.mark.unit
    async def test_intersect_indexes_with_date_range(
        self, index_manager, mock_valkey_client
    ):
        """Test intersection with date range filter."""
        call_count = 0

        async def mock_smembers(key):
            nonlocal call_count
            call_count += 1
            if "job" in key:
                return {b"conv-1", b"conv-2", b"conv-3"}
            else:
                return {b"conv-1", b"conv-2"}

        mock_valkey_client._client.smembers = mock_smembers

        start = datetime(2025, 1, 15, tzinfo=timezone.utc)
        end = datetime(2025, 1, 15, tzinfo=timezone.utc)

        result = await index_manager.intersect_indexes(
            job_id="job-456",
            start_date=start,
            end_date=end,
        )

        assert result == {"conv-1", "conv-2"}

    @pytest.mark.unit
    async def test_intersect_indexes_all_filters(
        self, index_manager, mock_valkey_client
    ):
        """Test intersection with all filters."""
        mock_valkey_client._client.smembers = AsyncMock(
            return_value={b"conv-1"}
        )

        start = datetime(2025, 1, 15, tzinfo=timezone.utc)
        end = datetime(2025, 1, 15, tzinfo=timezone.utc)

        result = await index_manager.intersect_indexes(
            job_id="job-456",
            user_id="user-789",
            project_id="project-101",
            workflow_id="workflow-202",
            start_date=start,
            end_date=end,
        )

        assert result == {"conv-1"}


class TestIndexManagerStatsError:
    """Tests for index stats error handling."""

    @pytest.mark.unit
    async def test_get_index_stats_exception(
        self, index_manager, mock_valkey_client
    ):
        """Test getting index stats when keys() raises an exception."""
        mock_valkey_client._client.keys = AsyncMock(
            side_effect=Exception("Connection error")
        )

        stats = await index_manager.get_index_stats()

        assert "error" in stats
        assert stats["error"] == "Connection error"
