"""Job creation state management service.

This module provides in-memory state management for async job creation.
Tracks job creation progress, status, and results.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


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
    """In-memory job creation state manager.

    Stores job creation status for tracking progress.
    Thread-safe for concurrent access.
    """

    def __init__(self) -> None:
        """Initialize state manager with empty storage."""
        self._storage: dict[str, JobCreationStatus] = {}

    def create_job(self, job_id: str) -> None:
        """Create new job creation tracking entry.

        Args:
            job_id: Unique job ID
        """
        self._storage[job_id] = JobCreationStatus(
            job_id=job_id,
            status="creating",
            progress=0,
            start_time=datetime.now(),
        )
        logger.info(f"Created job creation tracking for job_id={job_id}")

    def update_progress(self, job_id: str, progress: int) -> None:
        """Update job creation progress.

        Args:
            job_id: Job ID
            progress: Progress percentage (0-100)
        """
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

    def mark_failed(self, job_id: str, error_message: str) -> None:
        """Mark job creation as failed.

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

    def get_status(self, job_id: str) -> Optional[JobCreationStatus]:
        """Get job creation status.

        Args:
            job_id: Job ID

        Returns:
            JobCreationStatus if found, None otherwise
        """
        return self._storage.get(job_id)

    def cleanup_old_jobs(self, max_age_seconds: int = 3600) -> None:
        """Remove old completed/failed jobs from storage.

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
