"""Unit tests for JobCreationStateManager Valkey integration.

Tests for Issue #239: JobCreationStateManager Valkey integration.
This test module verifies the 2-layer cache (L1: Memory, L2: Valkey) implementation
with 90% coverage target.
"""

import warnings
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.job_creation_state import JobCreationStateManager, JobCreationStatus
from app.services.valkey_client import ValkeyConnectionError


@pytest.fixture
def mock_valkey_client() -> MagicMock:
    """Mock ValkeyClient for testing."""
    client = MagicMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.ping = AsyncMock(return_value=True)
    return client


@pytest.fixture
def sample_job_status() -> dict[str, Any]:
    """Sample job status data for testing."""
    return {
        "job_id": "test-job-123",
        "status": "completed",
        "progress": 100,
        "start_time": "2025-12-05T10:00:00",
        "end_time": "2025-12-05T10:05:00",
        "job_master_id": "master-456",
        "error_message": None,
        "result": {"workflow_id": "wf-789"},
    }


class TestJobCreationStateManagerInit:
    """Test JobCreationStateManager initialization with Valkey."""

    @pytest.mark.unit
    def test_init_without_valkey_client(self) -> None:
        """Test initialization without ValkeyClient (backward compatible)."""
        manager = JobCreationStateManager()
        assert manager._storage == {}
        assert manager._valkey_client is None

    @pytest.mark.unit
    def test_init_with_valkey_client(self, mock_valkey_client: MagicMock) -> None:
        """Test initialization with ValkeyClient."""
        manager = JobCreationStateManager(valkey_client=mock_valkey_client)
        assert manager._valkey_client is mock_valkey_client
        assert manager._ttl_seconds == 86400  # Default 24 hours

    @pytest.mark.unit
    def test_init_with_custom_ttl(self, mock_valkey_client: MagicMock) -> None:
        """Test initialization with custom TTL."""
        manager = JobCreationStateManager(
            valkey_client=mock_valkey_client, ttl_seconds=3600
        )
        assert manager._ttl_seconds == 3600


class TestValkeyConnection:
    """Test Valkey connection management."""

    @pytest.mark.unit
    async def test_connect_valkey_success(self, mock_valkey_client: MagicMock) -> None:
        """Test successful Valkey connection."""
        manager = JobCreationStateManager(valkey_client=mock_valkey_client)
        await manager.connect_valkey()

        mock_valkey_client.connect.assert_awaited_once()
        assert manager._valkey_connected is True

    @pytest.mark.unit
    async def test_connect_valkey_without_client(self) -> None:
        """Test connect_valkey when no client is configured."""
        manager = JobCreationStateManager()
        await manager.connect_valkey()
        # Should not raise, just skip connection
        assert manager._valkey_connected is False

    @pytest.mark.unit
    async def test_disconnect_valkey_success(
        self, mock_valkey_client: MagicMock
    ) -> None:
        """Test successful Valkey disconnection."""
        manager = JobCreationStateManager(valkey_client=mock_valkey_client)
        await manager.connect_valkey()
        await manager.disconnect_valkey()

        mock_valkey_client.disconnect.assert_awaited_once()
        assert manager._valkey_connected is False


class TestGetStatusAsync:
    """Test get_status_async method with 2-layer cache."""

    @pytest.mark.unit
    async def test_get_status_async_l1_hit(self, mock_valkey_client: MagicMock) -> None:
        """Test L1 cache hit - Valkey not accessed."""
        manager = JobCreationStateManager(valkey_client=mock_valkey_client)
        await manager.connect_valkey()

        # Create job in L1 cache
        manager.create_job("test-job-123")

        result = await manager.get_status_async("test-job-123")

        assert result is not None
        assert result.job_id == "test-job-123"
        assert result.status == "creating"
        # Valkey get should NOT be called for L1 hit
        mock_valkey_client.get.assert_not_awaited()

    @pytest.mark.unit
    async def test_get_status_async_l1_miss_l2_hit(
        self, mock_valkey_client: MagicMock, sample_job_status: dict[str, Any]
    ) -> None:
        """Test L1 miss, L2 hit - populate L1 from L2."""
        mock_valkey_client.get = AsyncMock(return_value=sample_job_status)

        manager = JobCreationStateManager(valkey_client=mock_valkey_client)
        await manager.connect_valkey()

        result = await manager.get_status_async("test-job-123")

        assert result is not None
        assert result.job_id == "test-job-123"
        assert result.status == "completed"
        mock_valkey_client.get.assert_awaited_once_with("job:creation:test-job-123")

        # Verify L1 cache is now populated
        assert "test-job-123" in manager._storage

    @pytest.mark.unit
    async def test_get_status_async_not_found(
        self, mock_valkey_client: MagicMock
    ) -> None:
        """Test job not found in both L1 and L2."""
        mock_valkey_client.get = AsyncMock(return_value=None)

        manager = JobCreationStateManager(valkey_client=mock_valkey_client)
        await manager.connect_valkey()

        result = await manager.get_status_async("nonexistent-job")

        assert result is None
        mock_valkey_client.get.assert_awaited_once_with("job:creation:nonexistent-job")

    @pytest.mark.unit
    async def test_get_status_async_without_valkey(self) -> None:
        """Test get_status_async without Valkey configured."""
        manager = JobCreationStateManager()

        # Create job in L1
        manager.create_job("test-job-123")

        result = await manager.get_status_async("test-job-123")

        assert result is not None
        assert result.job_id == "test-job-123"


class TestMarkCompletedAsync:
    """Test mark_completed_async method with dual write."""

    @pytest.mark.unit
    async def test_mark_completed_async_writes_to_both_layers(
        self, mock_valkey_client: MagicMock
    ) -> None:
        """Test mark_completed_async writes to both L1 and L2."""
        manager = JobCreationStateManager(valkey_client=mock_valkey_client)
        await manager.connect_valkey()

        # Create job first
        manager.create_job("test-job-123")

        # Mark as completed
        await manager.mark_completed_async(
            job_id="test-job-123",
            job_master_id="master-456",
            result={"workflow_id": "wf-789"},
        )

        # Verify L1 cache updated
        l1_status = manager._storage.get("test-job-123")
        assert l1_status is not None
        assert l1_status.status == "completed"
        assert l1_status.progress == 100
        assert l1_status.job_master_id == "master-456"

        # Verify L2 (Valkey) was written
        mock_valkey_client.set.assert_awaited_once()
        call_args = mock_valkey_client.set.call_args
        assert call_args[0][0] == "job:creation:test-job-123"
        assert call_args.kwargs.get("ttl") == 86400

    @pytest.mark.unit
    async def test_mark_completed_async_job_not_found(
        self, mock_valkey_client: MagicMock
    ) -> None:
        """Test mark_completed_async for non-existent job."""
        manager = JobCreationStateManager(valkey_client=mock_valkey_client)
        await manager.connect_valkey()

        # Should not raise, just log warning
        await manager.mark_completed_async(job_id="nonexistent-job")

        # Valkey should NOT be written for non-existent job
        mock_valkey_client.set.assert_not_awaited()


class TestMarkFailedAsync:
    """Test mark_failed_async method."""

    @pytest.mark.unit
    async def test_mark_failed_async_writes_to_both_layers(
        self, mock_valkey_client: MagicMock
    ) -> None:
        """Test mark_failed_async writes to both L1 and L2."""
        manager = JobCreationStateManager(valkey_client=mock_valkey_client)
        await manager.connect_valkey()

        # Create job first
        manager.create_job("test-job-123")

        # Mark as failed
        await manager.mark_failed_async(
            job_id="test-job-123", error_message="Something went wrong"
        )

        # Verify L1 cache updated
        l1_status = manager._storage.get("test-job-123")
        assert l1_status is not None
        assert l1_status.status == "failed"
        assert l1_status.error_message == "Something went wrong"

        # Verify L2 (Valkey) was written
        mock_valkey_client.set.assert_awaited_once()


class TestCreateJobAsync:
    """Test create_job_async method."""

    @pytest.mark.unit
    async def test_create_job_async_writes_to_both_layers(
        self, mock_valkey_client: MagicMock
    ) -> None:
        """Test create_job_async writes to both L1 and L2."""
        manager = JobCreationStateManager(valkey_client=mock_valkey_client)
        await manager.connect_valkey()

        await manager.create_job_async("test-job-123")

        # Verify L1 cache
        l1_status = manager._storage.get("test-job-123")
        assert l1_status is not None
        assert l1_status.status == "creating"
        assert l1_status.progress == 0

        # Verify L2 (Valkey) was written
        mock_valkey_client.set.assert_awaited_once()
        call_args = mock_valkey_client.set.call_args
        assert call_args[0][0] == "job:creation:test-job-123"


class TestUpdateProgressAsync:
    """Test update_progress_async method."""

    @pytest.mark.unit
    async def test_update_progress_async_writes_to_both_layers(
        self, mock_valkey_client: MagicMock
    ) -> None:
        """Test update_progress_async writes to both L1 and L2."""
        manager = JobCreationStateManager(valkey_client=mock_valkey_client)
        await manager.connect_valkey()

        # Create job first
        manager.create_job("test-job-123")

        # Update progress
        await manager.update_progress_async("test-job-123", 50)

        # Verify L1 cache
        l1_status = manager._storage.get("test-job-123")
        assert l1_status is not None
        assert l1_status.progress == 50

        # Verify L2 (Valkey) was written
        mock_valkey_client.set.assert_awaited_once()

    @pytest.mark.unit
    async def test_update_progress_async_job_not_found(
        self, mock_valkey_client: MagicMock
    ) -> None:
        """Test update_progress_async for non-existent job."""
        manager = JobCreationStateManager(valkey_client=mock_valkey_client)
        await manager.connect_valkey()

        # Should not raise
        await manager.update_progress_async("nonexistent-job", 50)

        # Valkey should NOT be written
        mock_valkey_client.set.assert_not_awaited()


class TestGracefulDegradation:
    """Test graceful degradation when Valkey is unavailable."""

    @pytest.mark.unit
    async def test_valkey_connection_failure_graceful_degradation(
        self, mock_valkey_client: MagicMock
    ) -> None:
        """Test graceful degradation when Valkey connection fails."""
        mock_valkey_client.connect = AsyncMock(
            side_effect=ValkeyConnectionError("Connection failed")
        )

        manager = JobCreationStateManager(valkey_client=mock_valkey_client)

        # Connection failure should not raise, should degrade gracefully
        await manager.connect_valkey()
        assert manager._valkey_connected is False

        # Operations should still work with L1 cache only
        manager.create_job("test-job-123")
        result = await manager.get_status_async("test-job-123")

        assert result is not None
        assert result.job_id == "test-job-123"

    @pytest.mark.unit
    async def test_valkey_get_failure_graceful_degradation(
        self, mock_valkey_client: MagicMock
    ) -> None:
        """Test graceful degradation when Valkey get fails."""
        mock_valkey_client.get = AsyncMock(side_effect=Exception("Get failed"))

        manager = JobCreationStateManager(valkey_client=mock_valkey_client)
        await manager.connect_valkey()

        # Should return None without raising
        result = await manager.get_status_async("test-job-123")
        assert result is None

    @pytest.mark.unit
    async def test_valkey_set_failure_graceful_degradation(
        self, mock_valkey_client: MagicMock
    ) -> None:
        """Test graceful degradation when Valkey set fails."""
        mock_valkey_client.set = AsyncMock(side_effect=Exception("Set failed"))

        manager = JobCreationStateManager(valkey_client=mock_valkey_client)
        await manager.connect_valkey()

        # Create job first
        manager.create_job("test-job-123")

        # Should complete without raising, L1 cache still works
        await manager.mark_completed_async(job_id="test-job-123")

        # Verify L1 cache was still updated
        l1_status = manager._storage.get("test-job-123")
        assert l1_status is not None
        assert l1_status.status == "completed"


class TestDatetimeSerialization:
    """Test datetime serialization/deserialization."""

    @pytest.mark.unit
    async def test_datetime_serialization_deserialization(
        self, mock_valkey_client: MagicMock
    ) -> None:
        """Test datetime fields are properly serialized and deserialized."""
        # Simulate Valkey returning serialized data with datetime strings
        valkey_data = {
            "job_id": "test-job-123",
            "status": "completed",
            "progress": 100,
            "start_time": "2025-12-05T10:00:00",
            "end_time": "2025-12-05T10:05:00",
            "job_master_id": None,
            "error_message": None,
            "result": None,
        }
        mock_valkey_client.get = AsyncMock(return_value=valkey_data)

        manager = JobCreationStateManager(valkey_client=mock_valkey_client)
        await manager.connect_valkey()

        result = await manager.get_status_async("test-job-123")

        assert result is not None
        assert isinstance(result.start_time, datetime)
        assert isinstance(result.end_time, datetime)
        assert result.start_time.year == 2025
        assert result.start_time.month == 12
        assert result.start_time.day == 5


class TestSyncMethodsBackwardCompatibility:
    """Test backward compatibility of sync methods."""

    @pytest.mark.unit
    def test_sync_methods_backward_compatible(self) -> None:
        """Test that existing sync methods still work and show deprecation warning."""
        manager = JobCreationStateManager()

        # Test create_job
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            manager.create_job("test-job-123")
            # Deprecation warning should be issued
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "deprecated" in str(w[0].message).lower()

        # Test update_progress
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            manager.update_progress("test-job-123", 50)
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)

        # Test mark_completed
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            manager.mark_completed("test-job-123")
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)

        # Verify the operations actually worked
        status = manager.get_status("test-job-123")
        assert status is not None
        assert status.status == "completed"

    @pytest.mark.unit
    def test_get_status_sync_backward_compatible(self) -> None:
        """Test get_status sync method works with deprecation warning."""
        manager = JobCreationStateManager()
        manager._storage["test-job-123"] = JobCreationStatus(
            job_id="test-job-123",
            status="creating",
            progress=0,
            start_time=datetime.now(),
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = manager.get_status("test-job-123")
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)

        assert result is not None
        assert result.job_id == "test-job-123"

    @pytest.mark.unit
    def test_mark_failed_sync_backward_compatible(self) -> None:
        """Test mark_failed sync method works with deprecation warning."""
        manager = JobCreationStateManager()
        manager._storage["test-job-123"] = JobCreationStatus(
            job_id="test-job-123",
            status="creating",
            progress=0,
            start_time=datetime.now(),
        )

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            manager.mark_failed("test-job-123", "Test error")
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)

        status = manager._storage.get("test-job-123")
        assert status is not None
        assert status.status == "failed"
        assert status.error_message == "Test error"

    @pytest.mark.unit
    def test_cleanup_old_jobs_backward_compatible(self) -> None:
        """Test cleanup_old_jobs sync method works."""
        manager = JobCreationStateManager()

        # This method doesn't need deprecation warning as it's utility
        manager.cleanup_old_jobs()
        # Should not raise


class TestKeyPrefix:
    """Test Valkey key prefix configuration."""

    @pytest.mark.unit
    async def test_default_key_prefix(self, mock_valkey_client: MagicMock) -> None:
        """Test default key prefix is job:creation:."""
        manager = JobCreationStateManager(valkey_client=mock_valkey_client)
        await manager.connect_valkey()

        manager.create_job("test-job-123")
        await manager.mark_completed_async("test-job-123")

        call_args = mock_valkey_client.set.call_args
        assert call_args[0][0] == "job:creation:test-job-123"

    @pytest.mark.unit
    async def test_custom_key_prefix(self, mock_valkey_client: MagicMock) -> None:
        """Test custom key prefix."""
        manager = JobCreationStateManager(
            valkey_client=mock_valkey_client, key_prefix="custom:prefix:"
        )
        await manager.connect_valkey()

        manager.create_job("test-job-123")
        await manager.mark_completed_async("test-job-123")

        call_args = mock_valkey_client.set.call_args
        assert call_args[0][0] == "custom:prefix:test-job-123"


class TestDisconnectErrorHandling:
    """Test disconnect error handling."""

    @pytest.mark.unit
    async def test_disconnect_valkey_error_handling(
        self, mock_valkey_client: MagicMock
    ) -> None:
        """Test disconnect handles errors gracefully."""
        mock_valkey_client.disconnect = AsyncMock(
            side_effect=Exception("Disconnect error")
        )

        manager = JobCreationStateManager(valkey_client=mock_valkey_client)
        await manager.connect_valkey()

        # Should not raise
        await manager.disconnect_valkey()
        assert manager._valkey_connected is False

    @pytest.mark.unit
    async def test_disconnect_valkey_when_not_connected(
        self, mock_valkey_client: MagicMock
    ) -> None:
        """Test disconnect when not connected does nothing."""
        manager = JobCreationStateManager(valkey_client=mock_valkey_client)
        # Don't connect

        # Should not raise
        await manager.disconnect_valkey()
        mock_valkey_client.disconnect.assert_not_awaited()


class TestSyncMethodsNotFound:
    """Test sync methods when job is not found."""

    @pytest.mark.unit
    def test_update_progress_sync_job_not_found(self) -> None:
        """Test update_progress sync for non-existent job."""
        manager = JobCreationStateManager()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            manager.update_progress("nonexistent-job", 50)
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)

        # Should not raise, job not in storage
        assert "nonexistent-job" not in manager._storage

    @pytest.mark.unit
    def test_mark_completed_sync_job_not_found(self) -> None:
        """Test mark_completed sync for non-existent job."""
        manager = JobCreationStateManager()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            manager.mark_completed("nonexistent-job")
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)

        # Should not raise, job not in storage
        assert "nonexistent-job" not in manager._storage

    @pytest.mark.unit
    def test_mark_failed_sync_job_not_found(self) -> None:
        """Test mark_failed sync for non-existent job."""
        manager = JobCreationStateManager()

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            manager.mark_failed("nonexistent-job", "Error")
            assert len(w) >= 1
            assert issubclass(w[0].category, DeprecationWarning)

        # Should not raise, job not in storage
        assert "nonexistent-job" not in manager._storage


class TestCleanupOldJobs:
    """Test cleanup_old_jobs functionality."""

    @pytest.mark.unit
    def test_cleanup_old_jobs_removes_old_completed_jobs(self) -> None:
        """Test cleanup removes old completed jobs."""
        from datetime import timedelta

        manager = JobCreationStateManager()

        # Create a job with old end_time
        old_time = datetime.now() - timedelta(seconds=7200)  # 2 hours ago
        manager._storage["old-job"] = JobCreationStatus(
            job_id="old-job",
            status="completed",
            progress=100,
            start_time=old_time - timedelta(seconds=60),
            end_time=old_time,
        )

        # Create a recent job
        manager._storage["recent-job"] = JobCreationStatus(
            job_id="recent-job",
            status="completed",
            progress=100,
            start_time=datetime.now() - timedelta(seconds=60),
            end_time=datetime.now(),
        )

        # Cleanup with 1 hour max age
        manager.cleanup_old_jobs(max_age_seconds=3600)

        # Old job should be removed
        assert "old-job" not in manager._storage
        # Recent job should remain
        assert "recent-job" in manager._storage

    @pytest.mark.unit
    def test_cleanup_old_jobs_keeps_jobs_without_end_time(self) -> None:
        """Test cleanup keeps jobs that haven't ended."""
        manager = JobCreationStateManager()

        # Create a job without end_time (still in progress)
        manager._storage["in-progress-job"] = JobCreationStatus(
            job_id="in-progress-job",
            status="creating",
            progress=50,
            start_time=datetime.now(),
        )

        manager.cleanup_old_jobs(max_age_seconds=0)  # Very aggressive cleanup

        # Job should remain (no end_time)
        assert "in-progress-job" in manager._storage


class TestMarkFailedAsyncNotFound:
    """Test mark_failed_async when job is not found."""

    @pytest.mark.unit
    async def test_mark_failed_async_job_not_found(
        self, mock_valkey_client: MagicMock
    ) -> None:
        """Test mark_failed_async for non-existent job."""
        manager = JobCreationStateManager(valkey_client=mock_valkey_client)
        await manager.connect_valkey()

        # Should not raise, just log warning
        await manager.mark_failed_async(job_id="nonexistent-job", error_message="Error")

        # Valkey should NOT be written for non-existent job
        mock_valkey_client.set.assert_not_awaited()
