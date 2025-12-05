"""Job creation state management service.

This module provides 2-layer cache state management for async job creation.
L1: In-memory cache for fast access
L2: Valkey (Redis-compatible) for persistence

Issue #239: JobCreationStateManager Valkey integration.

Refactored for:
- DRY: Extracted common patterns (job lookup, Valkey availability check)
- Single Responsibility: Separated status update logic
- Consistent Logging: Cache hit/miss and connection status logging
"""

import logging
import warnings
from datetime import datetime
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Optional, TypeVar

from pydantic import BaseModel

if TYPE_CHECKING:
    from app.services.valkey_client import ValkeyClient

logger = logging.getLogger(__name__)

# Default TTL for Valkey cache: 24 hours
DEFAULT_TTL_SECONDS = 86400
DEFAULT_KEY_PREFIX = "job:creation:"

# Type variable for generic return types in decorators
T = TypeVar("T")


def deprecated_sync_method(async_method_name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator to mark sync methods as deprecated with consistent warnings.

    Args:
        async_method_name: Name of the async method to recommend instead.

    Returns:
        Decorator function that adds deprecation warning.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            warnings.warn(
                f"{func.__name__}() is deprecated, use {async_method_name}() instead",
                DeprecationWarning,
                stacklevel=2,
            )
            return func(*args, **kwargs)

        return wrapper

    return decorator


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

    # ----- Private Helper Methods (DRY principle) -----

    def _get_valkey_key(self, job_id: str) -> str:
        """Get Valkey key for job ID.

        Args:
            job_id: Job ID

        Returns:
            Valkey key with prefix
        """
        return f"{self._key_prefix}{job_id}"

    def _is_valkey_available(self) -> bool:
        """Check if Valkey is available for operations.

        Returns:
            True if Valkey client is configured and connected
        """
        return self._valkey_connected and self._valkey_client is not None

    def _get_job_or_log_warning(self, job_id: str) -> Optional[JobCreationStatus]:
        """Get job from L1 cache or log warning if not found.

        Args:
            job_id: Job ID

        Returns:
            JobCreationStatus if found, None otherwise (with warning logged)
        """
        if job_id not in self._storage:
            logger.warning(f"Job ID {job_id} not found in state manager")
            return None
        return self._storage[job_id]

    def _create_initial_status(self, job_id: str) -> JobCreationStatus:
        """Create initial job creation status.

        Args:
            job_id: Job ID

        Returns:
            New JobCreationStatus with 'creating' status
        """
        return JobCreationStatus(
            job_id=job_id,
            status="creating",
            progress=0,
            start_time=datetime.now(),
        )

    def _update_status_completed(
        self,
        status: JobCreationStatus,
        job_master_id: Optional[str] = None,
        result: Optional[dict[str, Any]] = None,
    ) -> None:
        """Update status to completed (mutates in place).

        Args:
            status: Status to update
            job_master_id: Optional job master ID
            result: Optional result data
        """
        status.status = "completed"
        status.progress = 100
        status.end_time = datetime.now()
        status.job_master_id = job_master_id
        status.result = result

    def _update_status_failed(
        self, status: JobCreationStatus, error_message: str
    ) -> None:
        """Update status to failed (mutates in place).

        Args:
            status: Status to update
            error_message: Error message
        """
        status.status = "failed"
        status.end_time = datetime.now()
        status.error_message = error_message

    # ----- Connection Management -----

    async def connect_valkey(self) -> None:
        """Connect to Valkey server.

        Handles connection failure gracefully (degradation to L1 only).
        Logs connection status for observability.
        """
        if self._valkey_client is None:
            logger.debug(
                "Valkey connection: skipped (no client configured, L1 cache only)"
            )
            self._valkey_connected = False
            return

        try:
            await self._valkey_client.connect()
            self._valkey_connected = True
            logger.info(
                "Valkey connection: success - L2 cache enabled for job state persistence"
            )
        except Exception as e:
            logger.warning(
                f"Valkey connection: failed - degrading to L1 only. Error: {e}"
            )
            self._valkey_connected = False

    async def disconnect_valkey(self) -> None:
        """Disconnect from Valkey server."""
        if self._valkey_client is not None and self._valkey_connected:
            try:
                await self._valkey_client.disconnect()
                logger.info("Valkey connection: disconnected")
            except Exception as e:
                logger.warning(f"Valkey disconnect: error occurred - {e}")
            finally:
                self._valkey_connected = False

    # ----- L2 Cache Operations -----

    async def _write_to_valkey(self, job_id: str, status: JobCreationStatus) -> None:
        """Write status to Valkey (L2 cache).

        Handles write failure gracefully with consistent logging.

        Args:
            job_id: Job ID
            status: Job creation status
        """
        if not self._is_valkey_available():
            logger.debug(f"L2 write: skipped for job {job_id} (Valkey unavailable)")
            return

        try:
            key = self._get_valkey_key(job_id)
            data = status.model_dump(mode="json")
            # _is_valkey_available check above guarantees client is not None
            await self._valkey_client.set(key, data, ttl=self._ttl_seconds)  # type: ignore[union-attr]
            logger.debug(f"L2 write: success for job {job_id}")
        except Exception as e:
            logger.warning(f"L2 write: failed for job {job_id} - {e}")

    async def _read_from_valkey(self, job_id: str) -> Optional[JobCreationStatus]:
        """Read status from Valkey (L2 cache).

        Handles read failure gracefully with cache hit/miss logging.

        Args:
            job_id: Job ID

        Returns:
            JobCreationStatus if found, None otherwise
        """
        if not self._is_valkey_available():
            logger.debug(f"L2 read: skipped for job {job_id} (Valkey unavailable)")
            return None

        try:
            key = self._get_valkey_key(job_id)
            # _is_valkey_available check above guarantees client is not None
            data = await self._valkey_client.get(key)  # type: ignore[union-attr]
            if data is None:
                logger.debug(f"L2 cache miss: job {job_id} not found in Valkey")
                return None

            # Deserialize and populate L1 cache
            status = JobCreationStatus.model_validate(data)
            self._storage[job_id] = status
            logger.debug(f"L2 cache hit: loaded job {job_id} from Valkey to L1")
            return status
        except Exception as e:
            logger.warning(f"L2 read: failed for job {job_id} - {e}")
            return None

    # ----- Async Public API (Primary) -----

    async def get_status_async(self, job_id: str) -> Optional[JobCreationStatus]:
        """Get job creation status with 2-layer cache lookup.

        Checks L1 (memory) first, then L2 (Valkey) if not found.
        Logs cache hit/miss for observability.

        Args:
            job_id: Job ID

        Returns:
            JobCreationStatus if found, None otherwise
        """
        # L1 cache hit
        if job_id in self._storage:
            logger.debug(f"L1 cache hit: job {job_id}")
            return self._storage[job_id]

        # L1 miss, try L2 (Valkey)
        logger.debug(f"L1 cache miss: job {job_id}, checking L2")
        return await self._read_from_valkey(job_id)

    async def create_job_async(self, job_id: str) -> None:
        """Create new job creation tracking entry (async version).

        Writes to both L1 and L2 cache.

        Args:
            job_id: Unique job ID
        """
        status = self._create_initial_status(job_id)
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
        status = self._get_job_or_log_warning(job_id)
        if status is None:
            return

        status.progress = progress
        logger.debug(f"Updated job {job_id} progress to {progress}%")

        # Write to L2 (Valkey)
        await self._write_to_valkey(job_id, status)

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
        status = self._get_job_or_log_warning(job_id)
        if status is None:
            return

        self._update_status_completed(status, job_master_id, result)
        logger.info(f"Marked job {job_id} as completed")

        # Write to L2 (Valkey)
        await self._write_to_valkey(job_id, status)

    async def mark_failed_async(self, job_id: str, error_message: str) -> None:
        """Mark job creation as failed (async version).

        Writes to both L1 and L2 cache.

        Args:
            job_id: Job ID
            error_message: Error message
        """
        status = self._get_job_or_log_warning(job_id)
        if status is None:
            return

        self._update_status_failed(status, error_message)
        logger.error(f"Marked job {job_id} as failed: {error_message}")

        # Write to L2 (Valkey)
        await self._write_to_valkey(job_id, status)

    # ----- Backward compatible sync methods (deprecated) -----
    # These methods use the decorator and helper functions to reduce duplication

    def _create_job_impl(self, job_id: str) -> None:
        """Implementation of create_job without deprecation warning.

        Args:
            job_id: Unique job ID
        """
        status = self._create_initial_status(job_id)
        self._storage[job_id] = status
        logger.info(f"Created job creation tracking for job_id={job_id}")

    @deprecated_sync_method("create_job_async")
    def create_job(self, job_id: str) -> None:
        """Create new job creation tracking entry.

        .. deprecated::
            Use :meth:`create_job_async` instead for 2-layer cache support.

        Args:
            job_id: Unique job ID
        """
        self._create_job_impl(job_id)

    @deprecated_sync_method("update_progress_async")
    def update_progress(self, job_id: str, progress: int) -> None:
        """Update job creation progress.

        .. deprecated::
            Use :meth:`update_progress_async` instead for 2-layer cache support.

        Args:
            job_id: Job ID
            progress: Progress percentage (0-100)
        """
        status = self._get_job_or_log_warning(job_id)
        if status is None:
            return

        status.progress = progress
        logger.debug(f"Updated job {job_id} progress to {progress}%")

    @deprecated_sync_method("mark_completed_async")
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
        status = self._get_job_or_log_warning(job_id)
        if status is None:
            return

        self._update_status_completed(status, job_master_id, result)
        logger.info(f"Marked job {job_id} as completed")

    @deprecated_sync_method("mark_failed_async")
    def mark_failed(self, job_id: str, error_message: str) -> None:
        """Mark job creation as failed.

        .. deprecated::
            Use :meth:`mark_failed_async` instead for 2-layer cache support.

        Args:
            job_id: Job ID
            error_message: Error message
        """
        status = self._get_job_or_log_warning(job_id)
        if status is None:
            return

        self._update_status_failed(status, error_message)
        logger.error(f"Marked job {job_id} as failed: {error_message}")

    @deprecated_sync_method("get_status_async")
    def get_status(self, job_id: str) -> Optional[JobCreationStatus]:
        """Get job creation status.

        .. deprecated::
            Use :meth:`get_status_async` instead for 2-layer cache support.

        Args:
            job_id: Job ID

        Returns:
            JobCreationStatus if found, None otherwise
        """
        return self._storage.get(job_id)

    # ----- Utility Methods -----

    def cleanup_old_jobs(self, max_age_seconds: int = 3600) -> None:
        """Remove old completed/failed jobs from storage.

        Note: This only cleans L1 cache. Valkey entries expire via TTL.

        Args:
            max_age_seconds: Maximum age in seconds (default: 1 hour)
        """
        current_time = datetime.now()
        to_remove: list[str] = []

        for job_id, status in self._storage.items():
            if (
                status.end_time
                and (current_time - status.end_time).total_seconds() > max_age_seconds
            ):
                to_remove.append(job_id)

        removed_count = len(to_remove)
        for job_id in to_remove:
            del self._storage[job_id]

        if removed_count > 0:
            logger.info(f"Cleaned up {removed_count} old job(s) from L1 cache")


# Global singleton instance
job_state_manager = JobCreationStateManager()
