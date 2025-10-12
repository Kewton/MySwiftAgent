"""Background worker for job execution."""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import AsyncSessionLocal
from app.models.job import BackoffStrategy, Job, JobStatus
from app.models.result import JobResult

logger = logging.getLogger(__name__)


class JobExecutor:
    """Executes individual jobs."""

    def __init__(self, session: AsyncSession, settings: Any) -> None:
        self.session = session
        self.settings = settings

    async def execute_job(self, job: Job) -> None:
        """Execute a single job.

        Note: Job status is already set to RUNNING by _get_next_job,
        so we don't need to update it again here.
        """
        logger.info(
            f"[EXECUTE_JOB] Starting job execution: job_id={job.id}, name={job.name}, method={job.method}, url={job.url}"
        )
        logger.info(
            f"[EXECUTE_JOB] Job details: attempt={job.attempt}/{job.max_attempts}, priority={job.priority}, status={job.status}"
        )

        # Ensure started_at is set (defensive programming for tests/manual execution)
        if job.started_at is None:
            job.started_at = datetime.utcnow()

        logger.info(f"[EXECUTE_JOB] Job {job.id} started at {job.started_at}")

        start_time = datetime.utcnow()
        error_message = None

        try:
            # Log request details
            logger.info(f"[EXECUTE_JOB] Preparing HTTP request for job {job.id}")
            logger.info(f"[EXECUTE_JOB] Request: {job.method} {job.url}")
            logger.info(f"[EXECUTE_JOB] Headers: {job.headers}")
            logger.info(f"[EXECUTE_JOB] Params: {job.params}")
            logger.info(f"[EXECUTE_JOB] Body: {job.body}")
            logger.info(f"[EXECUTE_JOB] Timeout: {job.timeout_sec}s")

            # Execute HTTP request
            async with httpx.AsyncClient() as client:
                logger.info(f"[EXECUTE_JOB] Sending HTTP request for job {job.id}...")
                response = await client.request(
                    method=job.method,
                    url=job.url,
                    headers=job.headers or {},
                    params=job.params or {},
                    json=job.body if job.body else None,
                    timeout=job.timeout_sec,
                )
                logger.info(
                    f"[EXECUTE_JOB] HTTP request completed for job {job.id}: status={response.status_code}"
                )

                # Limit response body size
                response_body = None
                if response.content:
                    content_bytes = response.content
                    if len(content_bytes) <= self.settings.result_max_bytes:
                        try:
                            response_body = response.json()
                        except json.JSONDecodeError:
                            response_body = {"text": response.text}
                    else:
                        response_body = {"truncated": True, "size": len(content_bytes)}

                # Store result using unified method
                await self._store_job_result(
                    job.id,
                    start_time,
                    response_status=response.status_code,
                    response_headers=dict(response.headers),
                    response_body=response_body,
                    error=None
                    if response.is_success
                    else f"HTTP {response.status_code}: {response.text}",
                )

                # Update job status
                if response.is_success:
                    job.status = JobStatus.SUCCEEDED
                    job.finished_at = datetime.utcnow()
                    logger.info(f"Job {job.id} completed successfully")
                else:
                    # HTTP error - consider this a failure
                    job.status = JobStatus.FAILED
                    job.finished_at = datetime.utcnow()
                    error_message = f"HTTP {response.status_code}: {response.text}"
                    logger.warning(
                        f"Job {job.id} failed with HTTP {response.status_code}"
                    )

        except Exception as e:
            error_message = str(e)
            logger.error(f"Job {job.id} failed with exception: {error_message}")

            # Store error result using unified method
            await self._store_job_result(job.id, start_time, error=error_message)

            # Determine if we should retry
            if job.attempt < job.max_attempts:
                await self._schedule_retry(job)
            else:
                job.status = JobStatus.FAILED
                job.finished_at = datetime.utcnow()

        await self.session.commit()

    async def _store_job_result(
        self,
        job_id: str,
        start_time: datetime,
        response_status: int | None = None,
        response_headers: dict[str, Any] | None = None,
        response_body: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        """Store or update job result safely using upsert pattern."""
        duration_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Try to get existing result first
        result = await self.session.scalar(
            select(JobResult).where(JobResult.job_id == job_id)
        )

        if result:
            # Update existing result
            result.response_status = response_status
            result.response_headers = response_headers
            result.response_body = response_body
            result.error = error
            result.duration_ms = duration_ms
            result.updated_at = datetime.utcnow()
        else:
            # Create new result
            try:
                result = JobResult(
                    job_id=job_id,
                    response_status=response_status,
                    response_headers=response_headers,
                    response_body=response_body,
                    error=error,
                    duration_ms=duration_ms,
                )
                self.session.add(result)
                await self.session.flush()  # Flush to catch constraint violations
            except Exception as e:
                # Handle race condition: another process created the result
                if "UNIQUE constraint failed" in str(e):
                    await self.session.rollback()
                    # Retry with update approach
                    result = await self.session.scalar(
                        select(JobResult).where(JobResult.job_id == job_id)
                    )
                    if result:
                        result.response_status = response_status
                        result.response_headers = response_headers
                        result.response_body = response_body
                        result.error = error
                        result.duration_ms = duration_ms
                        result.updated_at = datetime.utcnow()
                else:
                    raise  # Re-raise if not a constraint violation

    async def _schedule_retry(self, job: Job) -> None:
        """Schedule a job retry."""
        job.attempt += 1

        # Calculate backoff delay
        backoff_delay = self._calculate_backoff(job)
        job.next_attempt_at = datetime.utcnow() + timedelta(seconds=backoff_delay)
        job.status = JobStatus.QUEUED

        logger.info(
            f"Scheduling retry {job.attempt}/{job.max_attempts} for job {job.id} at {job.next_attempt_at}"
        )

    def _calculate_backoff(self, job: Job) -> float:
        """Calculate backoff delay based on strategy."""
        base_delay = job.backoff_seconds
        attempt = job.attempt - 1  # Current attempt number (0-based)

        if job.backoff_strategy == BackoffStrategy.FIXED:
            return base_delay
        elif job.backoff_strategy == BackoffStrategy.LINEAR:
            return base_delay * attempt
        elif job.backoff_strategy == BackoffStrategy.EXPONENTIAL:
            return float(base_delay * (2**attempt))
        else:
            return float(base_delay)


class WorkerManager:
    """Manages background workers for job execution."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.running = False
        self.workers: list[asyncio.Task[None]] = []

    async def start(self) -> None:
        """Start the worker manager."""
        self.running = True
        logger.info(f"Starting {self.settings.concurrency} workers")

        # Start worker tasks
        for i in range(self.settings.concurrency):
            worker = asyncio.create_task(self._worker_loop(f"worker-{i}"))
            self.workers.append(worker)

        # Wait for all workers to complete
        try:
            await asyncio.gather(*self.workers)
        except asyncio.CancelledError:
            logger.info("Worker manager cancelled")
        finally:
            self.running = False

    async def stop(self) -> None:
        """Stop the worker manager."""
        self.running = False

        # Cancel all worker tasks
        for worker in self.workers:
            worker.cancel()

        # Wait for cancellation
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

    async def _worker_loop(self, worker_name: str) -> None:
        """Main worker loop."""
        logger.info(f"[WORKER] Starting worker: {worker_name}")

        while self.running:
            try:
                async with AsyncSessionLocal() as session:
                    # Get next available job
                    logger.debug(f"[WORKER] {worker_name} polling for next job...")
                    job = await self._get_next_job(session)

                    if job:
                        logger.info(
                            f"[WORKER] {worker_name} picked up job: {job.id} (name={job.name})"
                        )
                        executor = JobExecutor(session, self.settings)
                        await executor.execute_job(job)
                        logger.info(
                            f"[WORKER] {worker_name} finished executing job: {job.id}"
                        )
                    else:
                        # No jobs available, wait before polling again
                        logger.debug(
                            f"[WORKER] {worker_name} found no jobs, sleeping for {self.settings.poll_interval}s"
                        )
                        await asyncio.sleep(self.settings.poll_interval)

            except asyncio.CancelledError:
                logger.info(f"Worker {worker_name} cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_name} error: {e}")
                await asyncio.sleep(1)  # Brief pause before retrying

        logger.info(f"Worker {worker_name} stopped")

    async def _get_next_job(self, session: AsyncSession) -> Job | None:
        """Get the next job to execute with optimistic locking.

        This method ensures that only one worker can claim a job, even with
        multiple concurrent workers, by using an atomic UPDATE operation.
        """
        now = datetime.utcnow()

        # Find candidate job ID (not the full job object)
        candidate_id = await session.scalar(
            select(Job.id)
            .where(
                and_(
                    Job.status == JobStatus.QUEUED,
                    or_(Job.next_attempt_at.is_(None), Job.next_attempt_at <= now),
                )
            )
            .order_by(
                Job.priority.asc(), Job.created_at.asc()
            )  # Higher priority first (lower number)
            .limit(1)
        )

        if not candidate_id:
            return None

        # Try to atomically claim this job by updating its status
        # This will only succeed for one worker if multiple workers try simultaneously
        from sqlalchemy import update

        result = await session.execute(
            update(Job)
            .where(
                and_(
                    Job.id == candidate_id,
                    Job.status
                    == JobStatus.QUEUED,  # Only if still queued (not claimed by another worker)
                )
            )
            .values(status=JobStatus.RUNNING, started_at=now)
            .returning(Job)
        )

        job = result.scalar_one_or_none()

        if job:
            # Successfully claimed the job
            await session.commit()
            logger.debug(f"[WORKER] Successfully claimed job {job.id}")
            return job
        else:
            # Another worker claimed it first, rollback and try again
            await session.rollback()
            logger.debug(f"[WORKER] Job {candidate_id} was claimed by another worker")
            return None
