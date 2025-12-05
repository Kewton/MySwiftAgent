"""Job creation state management service.

This module provides 2-layer cache state management for async job creation.
L1: In-memory cache for fast access
L2: Valkey (Redis-compatible) for persistence

Issue #239: JobCreationStateManager Valkey integration.
"""

import logging
import warnings
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.services.valkey_client import ValkeyClient

logger = logging.getLogger(__name__)

# Default TTL for Valkey cache: 24 hours
DEFAULT_TTL_SECONDS = 86400
DEFAULT_KEY_PREFIX = "job:creation:"


class JobCreationStatus(BaseModel):
    """Job creation status model."""

    job_id: str
    status: str  # 'creating' | 'completed' | 'failed'
    progress: int  # 0-100
    start_time: datetime
    end_time: Optional[datetime] = None
    job_master_id: Optional[str] = None
    error_message: Optional[str] = None
    result: Optional[dict[str, Any]] = None


class JobCreationStateManager:
    """2-layer cache job creation state manager.

    L1: In-memory cache for fast access
    L2: Valkey (Redis-compatible) for persistence

    Supports graceful degradation when Valkey is unavailable.
    Thread-safe for concurrent access.

    Args:
        valkey_client: Optional ValkeyClient for L2 cache
        ttl_seconds: TTL for Valkey cache in seconds (default: 24 hours)
        key_prefix: Prefix for Valkey keys (default: "job:creation:")
    """

    def __init__(
        self,
        valkey_client: Optional["ValkeyClient"] = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
        key_prefix: str = DEFAULT_KEY_PREFIX,
    ) -> None:
        """Initialize state manager with optional Valkey client.

        Args:
            valkey_client: Optional ValkeyClient for L2 cache
            ttl_seconds: TTL for Valkey cache in seconds
            key_prefix: Prefix for Valkey keys
        """
        self._storage: dict[str, JobCreationStatus] = {}
        self._valkey_client: Optional["ValkeyClient"] = valkey_client
        self._valkey_connected: bool = False
        self._ttl_seconds: int = ttl_seconds
        self._key_prefix: str = key_prefix

    def _get_valkey_key(self, job_id: str) -> str:
        """Get Valkey key for job ID.

        Args:
            job_id: Job ID

        Returns:
            Valkey key with prefix
        """
        return f"{self._key_prefix}{job_id}"

    async def connect_valkey(self) -> None:
        """Connect to Valkey server.

        Handles connection failure gracefully (degradation to L1 only).
        """
        if self._valkey_client is None:
            logger.debug("No Valkey client configured, using L1 cache only")
            self._valkey_connected = False
            return

        try:
            await self._valkey_client.connect()
            self._valkey_connected = True
            logger.info("Connected to Valkey for job creation state persistence")
        except Exception as e:
            logger.warning(f"Failed to connect to Valkey, degrading to L1 only: {e}")
            self._valkey_connected = False

    async def disconnect_valkey(self) -> None:
        """Disconnect from Valkey server."""
        if self._valkey_client is not None and self._valkey_connected:
            try:
                await self._valkey_client.disconnect()
                logger.info("Disconnected from Valkey")
            except Exception as e:
                logger.warning(f"Error disconnecting from Valkey: {e}")
            finally:
                self._valkey_connected = False

    async def _write_to_valkey(self, job_id: str, status: JobCreationStatus) -> None:
        """Write status to Valkey (L2 cache).

        Handles write failure gracefully.

        Args:
            job_id: Job ID
            status: Job creation status
        """
        if not self._valkey_connected or self._valkey_client is None:
            return

        try:
            key = self._get_valkey_key(job_id)
            data = status.model_dump(mode="json")
            await self._valkey_client.set(key, data, ttl=self._ttl_seconds)
            logger.debug(f"Wrote job {job_id} status to Valkey")
        except Exception as e:
            logger.warning(f"Failed to write job {job_id} to Valkey: {e}")

    async def _read_from_valkey(self, job_id: str) -> Optional[JobCreationStatus]:
        """Read status from Valkey (L2 cache).

        Handles read failure gracefully.

        Args:
            job_id: Job ID

        Returns:
            JobCreationStatus if found, None otherwise
        """
        if not self._valkey_connected or self._valkey_client is None:
            return None

        try:
            key = self._get_valkey_key(job_id)
            data = await self._valkey_client.get(key)
            if data is None:
                return None

            # Deserialize and populate L1 cache
            status = JobCreationStatus.model_validate(data)
            self._storage[job_id] = status
            logger.debug(f"Loaded job {job_id} status from Valkey to L1 cache")
            return status
        except Exception as e:
            logger.warning(f"Failed to read job {job_id} from Valkey: {e}")
            return None

    async def get_status_async(self, job_id: str) -> Optional[JobCreationStatus]:
        """Get job creation status with 2-layer cache lookup.

        Checks L1 (memory) first, then L2 (Valkey) if not found.

        Args:
            job_id: Job ID

        Returns:
            JobCreationStatus if found, None otherwise
        """
        # L1 cache hit
        if job_id in self._storage:
            return self._storage[job_id]

        # L1 miss, try L2 (Valkey)
        return await self._read_from_valkey(job_id)

    async def create_job_async(self, job_id: str) -> None:
        """Create new job creation tracking entry (async version).

        Writes to both L1 and L2 cache.

        Args:
            job_id: Unique job ID
        """
        status = JobCreationStatus(
            job_id=job_id,
            status="creating",
            progress=0,
            start_time=datetime.now(),
        )
        self._storage[job_id] = status
        logger.info(f"Created job creation tracking for job_id={job_id}")

        # Write to L2 (Valkey)
        await self._write_to_valkey(job_id, status)

    async def update_progress_async(self, job_id: str, progress: int) -> None:
        """Update job creation progress (async version).

        Writes to both L1 and L2 cache.

        Args:
            job_id: Job ID
            progress: Progress percentage (0-100)
        """
        if job_id not in self._storage:
            logger.warning(f"Job ID {job_id} not found in state manager")
            return

        self._storage[job_id].progress = progress
        logger.debug(f"Updated job {job_id} progress to {progress}%")

        # Write to L2 (Valkey)
        await self._write_to_valkey(job_id, self._storage[job_id])

    async def mark_completed_async(
        self,
        job_id: str,
        job_master_id: Optional[str] = None,
        result: Optional[dict[str, Any]] = None,
    ) -> None:
        """Mark job creation as completed (async version).

        Writes to both L1 and L2 cache.

        Args:
            job_id: Job ID
            job_master_id: Optional job master ID
            result: Optional result data
        """
        if job_id not in self._storage:
            logger.warning(f"Job ID {job_id} not found in state manager")
            return

        self._storage[job_id].status = "completed"
        self._storage[job_id].progress = 100
        self._storage[job_id].end_time = datetime.now()
        self._storage[job_id].job_master_id = job_master_id
        self._storage[job_id].result = result
        logger.info(f"Marked job {job_id} as completed")

        # Write to L2 (Valkey)
        await self._write_to_valkey(job_id, self._storage[job_id])

    async def mark_failed_async(self, job_id: str, error_message: str) -> None:
        """Mark job creation as failed (async version).

        Writes to both L1 and L2 cache.

        Args:
            job_id: Job ID
            error_message: Error message
        """
        if job_id not in self._storage:
            logger.warning(f"Job ID {job_id} not found in state manager")
            return

        self._storage[job_id].status = "failed"
        self._storage[job_id].end_time = datetime.now()
        self._storage[job_id].error_message = error_message
        logger.error(f"Marked job {job_id} as failed: {error_message}")

        # Write to L2 (Valkey)
        await self._write_to_valkey(job_id, self._storage[job_id])

    # ----- Backward compatible sync methods (deprecated) -----

    def create_job(self, job_id: str) -> None:
        """Create new job creation tracking entry.

        .. deprecated::
            Use :meth:`create_job_async` instead for 2-layer cache support.

        Args:
            job_id: Unique job ID
        """
        warnings.warn(
            "create_job() is deprecated, use create_job_async() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        self._storage[job_id] = JobCreationStatus(
            job_id=job_id,
            status="creating",
            progress=0,
            start_time=datetime.now(),
        )
        logger.info(f"Created job creation tracking for job_id={job_id}")

    def update_progress(self, job_id: str, progress: int) -> None:
        """Update job creation progress.

        .. deprecated::
            Use :meth:`update_progress_async` instead for 2-layer cache support.

        Args:
            job_id: Job ID
            progress: Progress percentage (0-100)
        """
        warnings.warn(
            "update_progress() is deprecated, use update_progress_async() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        if job_id not in self._storage:
            logger.warning(f"Job ID {job_id} not found in state manager")
            return

        self._storage[job_id].progress = progress
        logger.debug(f"Updated job {job_id} progress to {progress}%")

    def mark_completed(
        self,
        job_id: str,
        job_master_id: Optional[str] = None,
        result: Optional[dict[str, Any]] = None,
    ) -> None:
        """Mark job creation as completed.

        .. deprecated::
            Use :meth:`mark_completed_async` instead for 2-layer cache support.

        Args:
            job_id: Job ID
            job_master_id: Optional job master ID
            result: Optional result data
        """
        warnings.warn(
            "mark_completed() is deprecated, use mark_completed_async() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        if job_id not in self._storage:
            logger.warning(f"Job ID {job_id} not found in state manager")
            return

        self._storage[job_id].status = "completed"
        self._storage[job_id].progress = 100
        self._storage[job_id].end_time = datetime.now()
        self._storage[job_id].job_master_id = job_master_id
        self._storage[job_id].result = result
        logger.info(f"Marked job {job_id} as completed")

    def mark_failed(self, job_id: str, error_message: str) -> None:
        """Mark job creation as failed.

        .. deprecated::
            Use :meth:`mark_failed_async` instead for 2-layer cache support.

        Args:
            job_id: Job ID
            error_message: Error message
        """
        warnings.warn(
            "mark_failed() is deprecated, use mark_failed_async() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        if job_id not in self._storage:
            logger.warning(f"Job ID {job_id} not found in state manager")
            return

        self._storage[job_id].status = "failed"
        self._storage[job_id].end_time = datetime.now()
        self._storage[job_id].error_message = error_message
        logger.error(f"Marked job {job_id} as failed: {error_message}")

    def get_status(self, job_id: str) -> Optional[JobCreationStatus]:
        """Get job creation status.

        .. deprecated::
            Use :meth:`get_status_async` instead for 2-layer cache support.

        Args:
            job_id: Job ID

        Returns:
            JobCreationStatus if found, None otherwise
        """
        warnings.warn(
            "get_status() is deprecated, use get_status_async() instead",
            DeprecationWarning,
            stacklevel=2,
        )
        return self._storage.get(job_id)

    def cleanup_old_jobs(self, max_age_seconds: int = 3600) -> None:
        """Remove old completed/failed jobs from storage.

        Note: This only cleans L1 cache. Valkey entries expire via TTL.

        Args:
            max_age_seconds: Maximum age in seconds (default: 1 hour)
        """
        current_time = datetime.now()
        to_remove = []

        for job_id, status in self._storage.items():
            if (
                status.end_time
                and (current_time - status.end_time).total_seconds() > max_age_seconds
            ):
                to_remove.append(job_id)

        for job_id in to_remove:
            del self._storage[job_id]
            logger.info(f"Cleaned up old job {job_id}")


# Global singleton instance
job_state_manager = JobCreationStateManager()
