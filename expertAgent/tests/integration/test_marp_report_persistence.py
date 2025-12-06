"""Integration tests for Marp report persistence.

Tests for Issue #242: Integration and acceptance tests for server restart
and page reload behavior verification.

This module tests job state persistence scenarios:
- Job creation -> Valkey persistence -> In-memory clear -> Valkey restore
- Multi-instance simulation (different manager instances)
- Valkey down fallback behavior
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.job_creation_state import (
    JobCreationStateManager,
)
from app.services.valkey_client import ValkeyClient, ValkeyConnectionError


@pytest.mark.integration
class TestJobStatePersistence:
    """Test job state persistence with Valkey (L1/L2 cache)."""

    async def test_job_creation_persisted_to_valkey(
        self,
        valkey_test_client: ValkeyClient,
    ) -> None:
        """Test job creation is persisted to Valkey (L2 cache)."""
        # Arrange: Create manager with Valkey client
        manager = JobCreationStateManager(
            valkey_client=valkey_test_client,
            ttl_seconds=3600,
            key_prefix="test:job:",
        )
        await manager.connect_valkey()

        job_id = "persistence-test-001"

        # Act: Create job using async method
        await manager.create_job_async(job_id)

        # Assert: Job exists in L1 cache
        assert job_id in manager._storage
        l1_status = manager._storage[job_id]
        assert l1_status.status == "creating"
        assert l1_status.progress == 0

        # Assert: Job exists in L2 cache (Valkey)
        valkey_data = await valkey_test_client.get(f"test:job:{job_id}")
        assert valkey_data is not None
        assert valkey_data["job_id"] == job_id
        assert valkey_data["status"] == "creating"

        # Cleanup
        await manager.disconnect_valkey()

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
        # Arrange: Create manager and job
        manager = JobCreationStateManager(
            valkey_client=valkey_test_client,
            ttl_seconds=3600,
            key_prefix="test:job:",
        )
        await manager.connect_valkey()

        job_id = "restore-test-001"
        await manager.create_job_async(job_id)

        # Act: Update progress and mark completed
        await manager.update_progress_async(job_id, 50)
        await manager.mark_completed_async(
            job_id,
            job_master_id="jm-test-123",
            result={"workflow_id": "wf-test-456"},
        )

        # Verify L1 cache has the data
        assert job_id in manager._storage
        assert manager._storage[job_id].status == "completed"

        # Simulate server restart: Clear L1 cache
        manager._storage.clear()
        assert job_id not in manager._storage

        # Act: Retrieve job (should fetch from L2)
        restored_status = await manager.get_status_async(job_id)

        # Assert: Job was restored from Valkey
        assert restored_status is not None
        assert restored_status.job_id == job_id
        assert restored_status.status == "completed"
        assert restored_status.progress == 100
        assert restored_status.job_master_id == "jm-test-123"
        assert restored_status.result == {"workflow_id": "wf-test-456"}

        # Assert: L1 cache was populated
        assert job_id in manager._storage

        # Cleanup
        await manager.disconnect_valkey()

    async def test_multi_instance_access_via_valkey(
        self,
        valkey_test_client: ValkeyClient,
    ) -> None:
        """Test multiple manager instances can access job state via Valkey.

        Simulates multi-instance (horizontal scaling) scenario:
        - Instance A creates a job
        - Instance B retrieves the job via Valkey
        """
        # Arrange: Create two separate manager instances (simulating different servers)
        key_prefix = "test:multi:"

        # Instance A
        manager_a = JobCreationStateManager(
            valkey_client=valkey_test_client,
            ttl_seconds=3600,
            key_prefix=key_prefix,
        )
        await manager_a.connect_valkey()

        # Instance B (same Valkey client for test, different manager instance)
        manager_b = JobCreationStateManager(
            valkey_client=valkey_test_client,
            ttl_seconds=3600,
            key_prefix=key_prefix,
        )
        await manager_b.connect_valkey()

        job_id = "multi-instance-001"

        # Act: Instance A creates and completes a job
        await manager_a.create_job_async(job_id)
        await manager_a.update_progress_async(job_id, 75)
        await manager_a.mark_completed_async(
            job_id,
            job_master_id="jm-multi-123",
            result={"slides": ["slide1.html", "slide2.html"]},
        )

        # Instance B has no L1 cache for this job
        assert job_id not in manager_b._storage

        # Act: Instance B retrieves the job
        status_from_b = await manager_b.get_status_async(job_id)

        # Assert: Instance B got the job from Valkey
        assert status_from_b is not None
        assert status_from_b.job_id == job_id
        assert status_from_b.status == "completed"
        assert status_from_b.job_master_id == "jm-multi-123"
        assert status_from_b.result == {"slides": ["slide1.html", "slide2.html"]}

        # Assert: Instance B's L1 cache was populated
        assert job_id in manager_b._storage

        # Cleanup
        await manager_a.disconnect_valkey()
        await manager_b.disconnect_valkey()


@pytest.mark.integration
class TestValkeyFallbackBehavior:
    """Test graceful degradation when Valkey is unavailable."""

    async def test_create_job_without_valkey(self) -> None:
        """Test job creation works without Valkey (L1 only mode)."""
        # Arrange: Manager without Valkey client
        manager = JobCreationStateManager()
        job_id = "no-valkey-001"

        # Act: Create job
        await manager.create_job_async(job_id)

        # Assert: Job exists in L1 cache only
        assert job_id in manager._storage
        status = manager._storage[job_id]
        assert status.status == "creating"

        # Get status should work
        retrieved = await manager.get_status_async(job_id)
        assert retrieved is not None
        assert retrieved.job_id == job_id

    async def test_valkey_connection_failure_graceful_degradation(self) -> None:
        """Test graceful degradation when Valkey connection fails."""
        # Arrange: Mock Valkey client that fails to connect
        mock_client = MagicMock(spec=ValkeyClient)
        mock_client.connect = AsyncMock(
            side_effect=ValkeyConnectionError("Connection refused")
        )

        manager = JobCreationStateManager(valkey_client=mock_client)

        # Act: Try to connect (should not raise)
        await manager.connect_valkey()

        # Assert: Valkey is marked as disconnected
        assert manager._valkey_connected is False

        # Act: Operations should still work with L1 only
        job_id = "fallback-001"
        await manager.create_job_async(job_id)

        # Assert: Job is in L1 cache
        assert job_id in manager._storage
        status = await manager.get_status_async(job_id)
        assert status is not None
        assert status.job_id == job_id

    async def test_valkey_write_failure_continues_operation(self) -> None:
        """Test operations continue even when Valkey write fails."""
        # Arrange: Mock Valkey client that fails on set
        mock_client = MagicMock(spec=ValkeyClient)
        mock_client.connect = AsyncMock()
        mock_client.set = AsyncMock(side_effect=Exception("Write failed"))
        mock_client.get = AsyncMock(return_value=None)

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
        # Arrange: Mock Valkey client that fails on get
        mock_client = MagicMock(spec=ValkeyClient)
        mock_client.connect = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Read failed"))

        manager = JobCreationStateManager(valkey_client=mock_client)
        await manager.connect_valkey()
        manager._valkey_connected = True

        # Act: Try to get non-existent job (L1 miss, L2 fails)
        status = await manager.get_status_async("nonexistent-job")

        # Assert: Returns None without raising
        assert status is None


@pytest.mark.integration
class TestJobStateLifecycle:
    """Test complete job state lifecycle with persistence."""

    async def test_full_lifecycle_with_persistence(
        self,
        valkey_test_client: ValkeyClient,
    ) -> None:
        """Test full job lifecycle: creating -> progress updates -> completed."""
        # Arrange
        manager = JobCreationStateManager(
            valkey_client=valkey_test_client,
            ttl_seconds=3600,
            key_prefix="test:lifecycle:",
        )
        await manager.connect_valkey()

        job_id = "lifecycle-001"

        # Step 1: Create job
        await manager.create_job_async(job_id)
        status = await manager.get_status_async(job_id)
        assert status is not None
        assert status.status == "creating"
        assert status.progress == 0

        # Step 2: Update progress multiple times
        for progress in [25, 50, 75]:
            await manager.update_progress_async(job_id, progress)
            status = await manager.get_status_async(job_id)
            assert status is not None
            assert status.progress == progress

        # Step 3: Complete job
        result_data = {
            "job_master_id": "jm-lifecycle-123",
            "slides_count": 10,
            "output_path": "/tmp/slides/output.html",
        }
        await manager.mark_completed_async(
            job_id,
            job_master_id="jm-lifecycle-123",
            result=result_data,
        )

        status = await manager.get_status_async(job_id)
        assert status is not None
        assert status.status == "completed"
        assert status.progress == 100
        assert status.end_time is not None
        assert status.result == result_data

        # Cleanup
        await manager.disconnect_valkey()

    async def test_failed_job_persisted(
        self,
        valkey_test_client: ValkeyClient,
    ) -> None:
        """Test failed job state is persisted to Valkey."""
        # Arrange
        manager = JobCreationStateManager(
            valkey_client=valkey_test_client,
            ttl_seconds=3600,
            key_prefix="test:failed:",
        )
        await manager.connect_valkey()

        job_id = "failed-job-001"
        error_message = "Marp conversion failed: Invalid markdown syntax"

        # Act: Create and fail job
        await manager.create_job_async(job_id)
        await manager.update_progress_async(job_id, 30)
        await manager.mark_failed_async(job_id, error_message)

        # Assert: L1 cache has failed status
        status = manager._storage[job_id]
        assert status.status == "failed"
        assert status.error_message == error_message

        # Verify in Valkey
        valkey_data = await valkey_test_client.get(f"test:failed:{job_id}")
        assert valkey_data is not None
        assert valkey_data["status"] == "failed"
        assert valkey_data["error_message"] == error_message

        # Simulate server restart: Clear L1, restore from L2
        manager._storage.clear()
        restored = await manager.get_status_async(job_id)

        assert restored is not None
        assert restored.status == "failed"
        assert restored.error_message == error_message

        # Cleanup
        await manager.disconnect_valkey()


@pytest.mark.integration
class TestTTLBehavior:
    """Test TTL expiration behavior for job state."""

    async def test_job_ttl_is_set(
        self,
        valkey_test_client: ValkeyClient,
    ) -> None:
        """Test that job entries have TTL set in Valkey."""
        # Arrange: Manager with 1 hour TTL
        ttl_seconds = 3600
        manager = JobCreationStateManager(
            valkey_client=valkey_test_client,
            ttl_seconds=ttl_seconds,
            key_prefix="test:ttl:",
        )
        await manager.connect_valkey()

        job_id = "ttl-test-001"

        # Act: Create job
        await manager.create_job_async(job_id)

        # Assert: TTL is set correctly
        ttl = await valkey_test_client.get_ttl(f"test:ttl:{job_id}")
        # Allow 5 second variance for test execution time
        assert ttl_seconds - 5 <= ttl <= ttl_seconds

        # Cleanup
        await manager.disconnect_valkey()
