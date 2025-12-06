"""Integration tests for Marp report persistence.

Tests for Issue #242: Integration and acceptance tests for server restart
and page reload behavior verification.

This module tests job state persistence scenarios:
- Job creation -> Valkey persistence -> In-memory clear -> Valkey restore
- Multi-instance simulation (different manager instances)
- Valkey down fallback behavior
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.job_creation_state import (
    JobCreationStateManager,
)
from app.services.valkey_client import ValkeyClient, ValkeyConnectionError

# ============================================================================
# Test Constants
# ============================================================================
DEFAULT_TTL_SECONDS = 3600
TEST_KEY_PREFIX = "test:job:"


# ============================================================================
# Helper Functions / Context Managers
# ============================================================================
@asynccontextmanager
async def create_test_manager(
    valkey_client: ValkeyClient,
    key_prefix: str = TEST_KEY_PREFIX,
    ttl_seconds: int = DEFAULT_TTL_SECONDS,
) -> AsyncGenerator[JobCreationStateManager, None]:
    """Create a JobCreationStateManager for testing with automatic cleanup.

    This context manager handles connection and disconnection automatically,
    reducing boilerplate in tests and ensuring proper cleanup.

    Args:
        valkey_client: ValkeyClient instance for L2 cache.
        key_prefix: Redis key prefix for test isolation.
        ttl_seconds: TTL for cached entries.

    Yields:
        JobCreationStateManager: Configured and connected manager instance.
    """
    manager = JobCreationStateManager(
        valkey_client=valkey_client,
        ttl_seconds=ttl_seconds,
        key_prefix=key_prefix,
    )
    await manager.connect_valkey()
    try:
        yield manager
    finally:
        await manager.disconnect_valkey()


# ============================================================================
# Test Classes
# ============================================================================
@pytest.mark.integration
class TestJobStatePersistence:
    """Test job state persistence with Valkey (L1/L2 cache)."""

    async def test_job_creation_persisted_to_valkey(
        self,
        valkey_test_client: ValkeyClient,
    ) -> None:
        """Test job creation is persisted to Valkey (L2 cache)."""
        # Arrange
        job_id = "persistence-test-001"

        async with create_test_manager(valkey_test_client) as manager:
            # Act: Create job using async method
            await manager.create_job_async(job_id)

            # Assert: Job exists in L1 cache
            assert job_id in manager._storage
            l1_status = manager._storage[job_id]
            assert l1_status.status == "creating"
            assert l1_status.progress == 0

            # Assert: Job exists in L2 cache (Valkey)
            valkey_data = await valkey_test_client.get(f"{TEST_KEY_PREFIX}{job_id}")
            assert valkey_data is not None
            assert valkey_data["job_id"] == job_id
            assert valkey_data["status"] == "creating"

    async def test_job_restore_from_valkey_after_memory_clear(
        self,
        valkey_test_client: ValkeyClient,
    ) -> None:
        """Test job state can be restored from Valkey after in-memory cache is cleared.

        Simulates server restart scenario:
        1. Create job -> persisted to both L1 and L2
        2. Clear L1 (in-memory) cache
        3. Retrieve job -> should restore from L2 (Valkey)
        """
        # Arrange
        job_id = "restore-test-001"
        expected_result = {"workflow_id": "wf-test-456"}
        expected_job_master_id = "jm-test-123"

        async with create_test_manager(valkey_test_client) as manager:
            # Setup: Create and complete job
            await manager.create_job_async(job_id)
            await manager.update_progress_async(job_id, 50)
            await manager.mark_completed_async(
                job_id,
                job_master_id=expected_job_master_id,
                result=expected_result,
            )

            # Verify L1 cache has the data
            assert job_id in manager._storage
            assert manager._storage[job_id].status == "completed"

            # Act: Simulate server restart by clearing L1 cache
            manager._storage.clear()
            assert job_id not in manager._storage

            # Act: Retrieve job (should fetch from L2)
            restored_status = await manager.get_status_async(job_id)

            # Assert: Job was restored from Valkey
            assert restored_status is not None
            assert restored_status.job_id == job_id
            assert restored_status.status == "completed"
            assert restored_status.progress == 100
            assert restored_status.job_master_id == expected_job_master_id
            assert restored_status.result == expected_result

            # Assert: L1 cache was repopulated
            assert job_id in manager._storage

    async def test_multi_instance_access_via_valkey(
        self,
        valkey_test_client: ValkeyClient,
    ) -> None:
        """Test multiple manager instances can access job state via Valkey.

        Simulates multi-instance (horizontal scaling) scenario:
        - Instance A creates a job
        - Instance B retrieves the job via Valkey
        """
        # Arrange
        key_prefix = "test:multi:"
        job_id = "multi-instance-001"
        expected_result = {"slides": ["slide1.html", "slide2.html"]}
        expected_job_master_id = "jm-multi-123"

        # Use nested context managers for both instances
        async with create_test_manager(
            valkey_test_client, key_prefix=key_prefix
        ) as manager_a:
            async with create_test_manager(
                valkey_test_client, key_prefix=key_prefix
            ) as manager_b:
                # Act: Instance A creates and completes a job
                await manager_a.create_job_async(job_id)
                await manager_a.update_progress_async(job_id, 75)
                await manager_a.mark_completed_async(
                    job_id,
                    job_master_id=expected_job_master_id,
                    result=expected_result,
                )

                # Verify: Instance B has no L1 cache for this job
                assert job_id not in manager_b._storage

                # Act: Instance B retrieves the job
                status_from_b = await manager_b.get_status_async(job_id)

                # Assert: Instance B got the job from Valkey
                assert status_from_b is not None
                assert status_from_b.job_id == job_id
                assert status_from_b.status == "completed"
                assert status_from_b.job_master_id == expected_job_master_id
                assert status_from_b.result == expected_result

                # Assert: Instance B's L1 cache was populated
                assert job_id in manager_b._storage


@pytest.mark.integration
class TestValkeyFallbackBehavior:
    """Test graceful degradation when Valkey is unavailable."""

    async def test_create_job_without_valkey(self) -> None:
        """Test job creation works without Valkey (L1 only mode)."""
        # Arrange
        manager = JobCreationStateManager()
        job_id = "no-valkey-001"

        # Act
        await manager.create_job_async(job_id)

        # Assert: Job exists in L1 cache only
        assert job_id in manager._storage
        assert manager._storage[job_id].status == "creating"

        # Assert: Status retrieval works
        retrieved = await manager.get_status_async(job_id)
        assert retrieved is not None
        assert retrieved.job_id == job_id

    async def test_valkey_connection_failure_graceful_degradation(self) -> None:
        """Test graceful degradation when Valkey connection fails."""
        # Arrange
        mock_client = _create_mock_valkey_client_with_connection_failure()
        manager = JobCreationStateManager(valkey_client=mock_client)
        job_id = "fallback-001"

        # Act: Try to connect (should not raise)
        await manager.connect_valkey()

        # Assert: Valkey is marked as disconnected
        assert manager._valkey_connected is False

        # Act: Operations should still work with L1 only
        await manager.create_job_async(job_id)

        # Assert: Job is in L1 cache
        assert job_id in manager._storage
        status = await manager.get_status_async(job_id)
        assert status is not None
        assert status.job_id == job_id

    async def test_valkey_write_failure_continues_operation(self) -> None:
        """Test operations continue even when Valkey write fails."""
        # Arrange
        mock_client = _create_mock_valkey_client_with_write_failure()
        manager = JobCreationStateManager(valkey_client=mock_client)
        await manager.connect_valkey()
        manager._valkey_connected = True  # Force connected state for test
        job_id = "write-fail-001"

        # Act: Create job (Valkey write will fail, but operation should complete)
        await manager.create_job_async(job_id)

        # Assert: Job is still in L1 cache
        assert job_id in manager._storage
        assert manager._storage[job_id].status == "creating"

        # Act: Complete job (Valkey write will fail again)
        await manager.mark_completed_async(job_id, job_master_id="jm-123")

        # Assert: L1 cache was updated
        assert manager._storage[job_id].status == "completed"

    async def test_valkey_read_failure_returns_none(self) -> None:
        """Test L2 read failure returns None gracefully."""
        # Arrange
        mock_client = _create_mock_valkey_client_with_read_failure()
        manager = JobCreationStateManager(valkey_client=mock_client)
        await manager.connect_valkey()
        manager._valkey_connected = True

        # Act: Try to get non-existent job (L1 miss, L2 fails)
        status = await manager.get_status_async("nonexistent-job")

        # Assert: Returns None without raising
        assert status is None


# ============================================================================
# Mock Factory Functions for Valkey Fallback Tests
# ============================================================================
def _create_mock_valkey_client_with_connection_failure() -> MagicMock:
    """Create a mock ValkeyClient that fails to connect."""
    mock_client = MagicMock(spec=ValkeyClient)
    mock_client.connect = AsyncMock(
        side_effect=ValkeyConnectionError("Connection refused")
    )
    return mock_client


def _create_mock_valkey_client_with_write_failure() -> MagicMock:
    """Create a mock ValkeyClient that fails on write operations."""
    mock_client = MagicMock(spec=ValkeyClient)
    mock_client.connect = AsyncMock()
    mock_client.set = AsyncMock(side_effect=Exception("Write failed"))
    mock_client.get = AsyncMock(return_value=None)
    return mock_client


def _create_mock_valkey_client_with_read_failure() -> MagicMock:
    """Create a mock ValkeyClient that fails on read operations."""
    mock_client = MagicMock(spec=ValkeyClient)
    mock_client.connect = AsyncMock()
    mock_client.get = AsyncMock(side_effect=Exception("Read failed"))
    return mock_client


@pytest.mark.integration
class TestJobStateLifecycle:
    """Test complete job state lifecycle with persistence."""

    # Test data for lifecycle tests
    PROGRESS_STEPS = [25, 50, 75]

    async def test_full_lifecycle_with_persistence(
        self,
        valkey_test_client: ValkeyClient,
    ) -> None:
        """Test full job lifecycle: creating -> progress updates -> completed."""
        # Arrange
        key_prefix = "test:lifecycle:"
        job_id = "lifecycle-001"
        result_data = {
            "job_master_id": "jm-lifecycle-123",
            "slides_count": 10,
            "output_path": "/tmp/slides/output.html",
        }

        async with create_test_manager(
            valkey_test_client, key_prefix=key_prefix
        ) as manager:
            # Step 1: Create job
            await manager.create_job_async(job_id)
            status = await manager.get_status_async(job_id)
            assert status is not None
            assert status.status == "creating"
            assert status.progress == 0

            # Step 2: Update progress multiple times
            for progress in self.PROGRESS_STEPS:
                await manager.update_progress_async(job_id, progress)
                status = await manager.get_status_async(job_id)
                assert status is not None
                assert status.progress == progress

            # Step 3: Complete job
            await manager.mark_completed_async(
                job_id,
                job_master_id="jm-lifecycle-123",
                result=result_data,
            )

            # Assert: Final status is completed
            status = await manager.get_status_async(job_id)
            assert status is not None
            assert status.status == "completed"
            assert status.progress == 100
            assert status.end_time is not None
            assert status.result == result_data

    async def test_failed_job_persisted(
        self,
        valkey_test_client: ValkeyClient,
    ) -> None:
        """Test failed job state is persisted to Valkey."""
        # Arrange
        key_prefix = "test:failed:"
        job_id = "failed-job-001"
        error_message = "Marp conversion failed: Invalid markdown syntax"

        async with create_test_manager(
            valkey_test_client, key_prefix=key_prefix
        ) as manager:
            # Act: Create and fail job
            await manager.create_job_async(job_id)
            await manager.update_progress_async(job_id, 30)
            await manager.mark_failed_async(job_id, error_message)

            # Assert: L1 cache has failed status
            status = manager._storage[job_id]
            assert status.status == "failed"
            assert status.error_message == error_message

            # Assert: Verify in Valkey (L2 cache)
            valkey_data = await valkey_test_client.get(f"{key_prefix}{job_id}")
            assert valkey_data is not None
            assert valkey_data["status"] == "failed"
            assert valkey_data["error_message"] == error_message

            # Act: Simulate server restart by clearing L1 cache
            manager._storage.clear()
            restored = await manager.get_status_async(job_id)

            # Assert: Job was restored from L2 with failed status
            assert restored is not None
            assert restored.status == "failed"
            assert restored.error_message == error_message


@pytest.mark.integration
class TestTTLBehavior:
    """Test TTL expiration behavior for job state."""

    # TTL tolerance for test execution time variance
    TTL_TOLERANCE_SECONDS = 5

    async def test_job_ttl_is_set(
        self,
        valkey_test_client: ValkeyClient,
    ) -> None:
        """Test that job entries have TTL set in Valkey."""
        # Arrange
        key_prefix = "test:ttl:"
        job_id = "ttl-test-001"

        async with create_test_manager(
            valkey_test_client, key_prefix=key_prefix
        ) as manager:
            # Act: Create job
            await manager.create_job_async(job_id)

            # Assert: TTL is set correctly (with tolerance for test execution time)
            ttl = await valkey_test_client.get_ttl(f"{key_prefix}{job_id}")
            min_expected_ttl = DEFAULT_TTL_SECONDS - self.TTL_TOLERANCE_SECONDS
            assert min_expected_ttl <= ttl <= DEFAULT_TTL_SECONDS
