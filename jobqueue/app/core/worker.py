"""Background worker for job execution."""

import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import httpx
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.database import get_session_maker
from app.models.job import BackoffStrategy, Job, JobStatus
from app.models.result import JobResult
from app.models.task import Task, TaskStatus
from app.models.task_master import TaskMaster
from app.models.task_master_interface import TaskMasterInterface
from app.services.interface_validator import (
    InterfaceValidationError,
    InterfaceValidator,
)
from app.services.template_resolver import TemplateResolver, TemplateResolverError

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
            job.started_at = datetime.now(UTC)

        logger.info(f"[EXECUTE_JOB] Job {job.id} started at {job.started_at}")

        # Check interface validation results (Phase 2.2.3)
        if job.tags:
            for tag in job.tags:
                if isinstance(tag, dict) and tag.get("type") == "interface_validation":
                    if not tag.get("is_valid", True):
                        # Validation failed - block execution
                        error_msg = (
                            f"Job execution blocked due to failed interface validation. "
                            f"Errors: {'; '.join(tag.get('errors', []))}"
                        )
                        logger.error(f"[EXECUTE_JOB] {error_msg}")
                        job.status = JobStatus.FAILED
                        job.finished_at = datetime.now(UTC)
                        await self.session.commit()
                        raise ValueError(error_msg)
                    else:
                        logger.info(
                            f"[EXECUTE_JOB] Job {job.id} passed interface validation check"
                        )
                    break  # Only check first validation tag

        # Check if job has tasks
        tasks_result = await self.session.scalars(
            select(Task).where(Task.job_id == job.id).order_by(Task.order)
        )
        tasks = list(tasks_result.all())

        if tasks:
            # Execute tasks in order
            logger.info(
                f"[EXECUTE_JOB] Job {job.id} has {len(tasks)} tasks, executing in order"
            )
            await self._execute_tasks(job, tasks)
        else:
            # Execute job directly (legacy behavior)
            logger.info(f"[EXECUTE_JOB] Job {job.id} has no tasks, executing directly")
            await self._execute_single_job(job)

    async def _execute_tasks(self, job: Job, tasks: list[Task]) -> None:
        """Execute tasks in order."""
        for task in tasks:
            logger.info(f"[TASK] Executing task {task.id} (order={task.order})")

            # Update task status
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now(UTC)
            await self.session.commit()

            start_time = datetime.now(UTC)

            try:
                # Get task master for configuration
                task_master = await self.session.get(TaskMaster, task.master_id)
                if not task_master:
                    raise Exception(f"Task master {task.master_id} not found")

                # Resolve template variables in body_template
                resolved_body: dict[str, Any] | None = task_master.body_template
                if resolved_body and TemplateResolver.has_template_variables(
                    resolved_body
                ):
                    # Log template resolution context
                    job_body_fields = list(job.body.keys()) if job.body else []
                    logger.info(
                        f"[TASK] Template resolution context:\n"
                        f"  TaskMaster: {task_master.id} ({task_master.name})\n"
                        f"  Task: {task.id}\n"
                        f"  Job: {job.id}\n"
                        f"  Job body fields: {job_body_fields}"
                    )

                    # Build log context for enhanced logging
                    log_context = {
                        "task_id": task.id,
                        "task_master_id": task_master.id,
                        "task_master_name": task_master.name,
                        "job_id": job.id,
                    }

                    try:
                        # Pass job and current_task for {{job.body.*}} and {{task.input_data}}
                        result = TemplateResolver.resolve_template(
                            resolved_body,
                            tasks,
                            job=job,
                            current_task=task,
                            log_context=log_context,
                        )
                        # Template resolver can return str/list/None, but we expect dict
                        if isinstance(result, dict):
                            resolved_body = result

                            # Detect null fields after template resolution
                            null_fields = _find_null_fields(resolved_body)
                            if null_fields:
                                logger.warning(
                                    f"[TASK] Null fields detected after template resolution:\n"
                                    f"  Task: {task.id}\n"
                                    f"  TaskMaster: {task_master.name}\n"
                                    f"  Null fields: {null_fields}"
                                )
                        else:
                            resolved_body = None
                    except TemplateResolverError as e:
                        raise Exception(f"Template resolution failed: {e}") from e

                # Validate input data against interfaces
                if task.input_data:
                    interfaces = await self.session.scalars(
                        select(TaskMasterInterface)
                        .where(TaskMasterInterface.task_master_id == task_master.id)
                        .options(selectinload(TaskMasterInterface.interface_master))
                    )
                    for assoc in interfaces.all():
                        if assoc.required and assoc.interface_master.input_schema:
                            try:
                                InterfaceValidator.validate_input(
                                    task.input_data,
                                    assoc.interface_master.input_schema,
                                )
                            except InterfaceValidationError as e:
                                raise Exception(
                                    f"Input validation failed: {'; '.join(e.errors)}"
                                ) from e

                # Execute HTTP request
                async with httpx.AsyncClient() as client:
                    logger.info(
                        f"[TASK] Sending {task_master.method} request to {task_master.url}"
                    )
                    response = await client.request(
                        method=task_master.method,
                        url=task_master.url,
                        headers=task_master.headers or {},
                        json=resolved_body,
                        timeout=task_master.timeout_sec,
                    )
                    logger.info(f"[TASK] Response status: {response.status_code}")

                    # Parse response
                    output_data = None
                    if response.content:
                        try:
                            output_data = response.json()
                        except json.JSONDecodeError:
                            output_data = {"text": response.text}

                    # Validate output data against interfaces
                    if output_data:
                        interfaces = await self.session.scalars(
                            select(TaskMasterInterface)
                            .where(TaskMasterInterface.task_master_id == task_master.id)
                            .options(selectinload(TaskMasterInterface.interface_master))
                        )
                        for assoc in interfaces.all():
                            if assoc.required and assoc.interface_master.output_schema:
                                try:
                                    InterfaceValidator.validate_output(
                                        output_data,
                                        assoc.interface_master.output_schema,
                                    )
                                except InterfaceValidationError as e:
                                    raise Exception(
                                        f"Output validation failed: {'; '.join(e.errors)}"
                                    ) from e

                    # Store output (extract GraphAI output node result for task chains)
                    task.output_data = (
                        _extract_graphai_output(output_data)
                        if output_data
                        else output_data
                    )
                    task.status = (
                        TaskStatus.SUCCEEDED
                        if response.is_success
                        else TaskStatus.FAILED
                    )
                    task.finished_at = datetime.now(UTC)
                    task.duration_ms = int(
                        (task.finished_at - start_time).total_seconds() * 1000
                    )

                    if not response.is_success:
                        task.error = f"HTTP {response.status_code}: {response.text}"
                        logger.warning(
                            f"[TASK] Task {task.id} failed with HTTP {response.status_code}"
                        )
                        # Task failed, skip remaining tasks
                        await self._skip_remaining_tasks(tasks, task.order)
                        job.status = JobStatus.FAILED
                        job.finished_at = datetime.now(UTC)
                        await self.session.commit()
                        return

                    logger.info(f"[TASK] Task {task.id} completed successfully")
                    await self.session.commit()

            except Exception as e:
                error_message = str(e)
                logger.error(
                    f"[TASK] Task {task.id} failed with exception: {error_message}"
                )
                task.status = TaskStatus.FAILED
                task.error = error_message
                task.finished_at = datetime.now(UTC)
                task.duration_ms = int(
                    (datetime.now(UTC) - start_time).total_seconds() * 1000
                )

                # Skip remaining tasks
                await self._skip_remaining_tasks(tasks, task.order)
                job.status = JobStatus.FAILED
                job.finished_at = datetime.now(UTC)
                await self.session.commit()
                return

        # All tasks succeeded
        job.status = JobStatus.SUCCEEDED
        job.finished_at = datetime.now(UTC)
        logger.info(f"[EXECUTE_JOB] All tasks completed successfully for job {job.id}")
        await self.session.commit()

    async def _skip_remaining_tasks(self, tasks: list[Task], failed_order: int) -> None:
        """Mark all tasks after the failed task as SKIPPED."""
        for task in tasks:
            if task.order > failed_order and task.status == TaskStatus.QUEUED:
                task.status = TaskStatus.SKIPPED
                logger.info(f"[TASK] Skipping task {task.id} (order={task.order})")

    async def _execute_single_job(self, job: Job) -> None:
        """Execute a job without tasks (legacy behavior)."""
        start_time = datetime.now(UTC)
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
                    job.finished_at = datetime.now(UTC)
                    logger.info(f"Job {job.id} completed successfully")
                else:
                    # HTTP error - consider this a failure
                    job.status = JobStatus.FAILED
                    job.finished_at = datetime.now(UTC)
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
                job.finished_at = datetime.now(UTC)

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
        duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

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
            result.updated_at = datetime.now(UTC)
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
                        result.updated_at = datetime.now(UTC)
                else:
                    raise  # Re-raise if not a constraint violation

    async def _schedule_retry(self, job: Job) -> None:
        """Schedule a job retry."""
        job.attempt += 1

        # Calculate backoff delay
        backoff_delay = self._calculate_backoff(job)
        job.next_attempt_at = datetime.now(UTC) + timedelta(seconds=backoff_delay)
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
        session_maker = get_session_maker()

        while self.running:
            try:
                async with session_maker() as session:
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
        now = datetime.now(UTC)

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


def _find_null_fields(data: dict[str, Any], prefix: str = "") -> list[str]:
    """Recursively find null fields in a dictionary.

    Args:
        data: Dictionary to check for null fields
        prefix: Current path prefix for nested fields

    Returns:
        List of field paths that have null values
    """
    null_fields: list[str] = []

    for key, value in data.items():
        path = f"{prefix}.{key}" if prefix else key
        if value is None:
            null_fields.append(path)
        elif isinstance(value, dict):
            null_fields.extend(_find_null_fields(value, path))

    return null_fields


def _transform_to_interface(
    raw_output: Any,
    output_interface: dict[str, Any] | None,
) -> dict[str, Any]:
    """Transform raw output to match output_interface definition.

    Issue #338: This function extracts fields defined in output_interface
    from the raw GraphAI output, normalizing the data structure for
    downstream tasks in the chain.

    Args:
        raw_output: Raw output from GraphAI (can be nested)
        output_interface: Interface definition with properties and required fields

    Returns:
        Transformed output matching the interface schema
    """
    # If no output_interface defined, return raw output as-is
    if output_interface is None:
        return raw_output if isinstance(raw_output, dict) else {"value": raw_output}

    # Handle non-dict input gracefully
    if not isinstance(raw_output, dict):
        logger.warning(
            f"[TRANSFORM] raw_output is not a dict: {type(raw_output).__name__}"
        )
        return raw_output  # type: ignore

    try:
        result: dict[str, Any] = {}
        properties = output_interface.get("properties", {})

        for field_name, field_def in properties.items():
            # Determine search strategy based on field definition
            strategy = _determine_search_strategy(field_name, field_def)
            value = _find_field_value(raw_output, field_name, strategy)
            result[field_name] = value

            # Log field extraction (with masking for sensitive fields)
            _log_transformation(field_name, value, value is not None)

        # Validate required fields
        required_fields = output_interface.get("required", [])
        missing = [f for f in required_fields if result.get(f) is None]
        if missing:
            logger.warning(
                f"[TRANSFORM] Missing required fields after transformation: {missing}"
            )

        return result

    except RecursionError:
        logger.error("[TRANSFORM] Max recursion depth exceeded")
        return raw_output
    except (TypeError, KeyError) as e:
        logger.error(f"[TRANSFORM] Data structure error: {e}")
        return raw_output


def _determine_search_strategy(
    field_name: str,
    field_def: dict[str, Any],
) -> Literal["direct", "recursive", "path"]:
    """Determine the search strategy for a field.

    Args:
        field_name: Name of the field to search
        field_def: Field definition from output_interface

    Returns:
        Search strategy: "direct", "recursive", or "path"
    """
    # If source_mapping is defined, use path-based search
    if "source_mapping" in field_def:
        return "path"

    # Default to recursive strategy for flexibility
    return "recursive"


def _find_field_value(
    data: dict[str, Any],
    field_name: str,
    search_strategy: Literal["direct", "recursive", "path"] = "recursive",
) -> Any:
    """Find a field value in the data using the specified strategy.

    Issue #338: This function supports multiple search strategies to handle
    various GraphAI output structures.

    Args:
        data: Data dictionary to search
        field_name: Field name to find
        search_strategy:
            - "direct": Only check direct key access
            - "recursive": Depth-first search through nested dicts
            - "path": Dot-separated path access (e.g., "node.field.subfield")

    Returns:
        Found value or None
    """
    if search_strategy == "direct":
        return data.get(field_name)

    if search_strategy == "recursive":
        return _recursive_search(data, field_name)

    if search_strategy == "path":
        return _path_based_search(data, field_name)

    return None


def _recursive_search(
    data: dict[str, Any],
    field_name: str,
    max_depth: int = 5,
) -> Any:
    """Recursively search for a field in nested dictionaries.

    Args:
        data: Dictionary to search
        field_name: Field name to find
        max_depth: Maximum recursion depth to prevent infinite loops

    Returns:
        Found value or None
    """
    if max_depth <= 0:
        return None

    # Direct access first (priority)
    if field_name in data:
        return data[field_name]

    # Search nested dictionaries
    for _key, value in data.items():
        if isinstance(value, dict):
            result = _recursive_search(value, field_name, max_depth - 1)
            if result is not None:
                return result

    return None


def _path_based_search(
    data: dict[str, Any],
    field_path: str,
) -> Any:
    """Search for a field using dot-separated path.

    Args:
        data: Dictionary to search
        field_path: Dot-separated path (e.g., "execute_search.search_results")

    Returns:
        Found value or None
    """
    if not field_path:
        return data

    parts = field_path.split(".")
    current = data

    for part in parts:
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None

    return current


# Sensitive field patterns for log masking
_SENSITIVE_FIELD_PATTERNS = {
    "api_key", "password", "token", "secret", "credential",
    "private_key", "access_key", "auth", "bearer",
}


def _is_sensitive_field(field_name: str) -> bool:
    """Check if a field name indicates sensitive data."""
    field_lower = field_name.lower()
    return any(pattern in field_lower for pattern in _SENSITIVE_FIELD_PATTERNS)


def _log_transformation(field_name: str, value: Any, found: bool) -> None:
    """Log transformation result with sensitive data masking."""
    if _is_sensitive_field(field_name):
        log_value = "[MASKED]" if found else "[NOT FOUND]"
    else:
        if found:
            str_value = str(value)
            log_value = str_value[:100] + "..." if len(str_value) > 100 else str_value
        else:
            log_value = "[NOT FOUND]"

    logger.debug(f"[TRANSFORM] {field_name}: {log_value}")


def _extract_graphai_output(response_data: Any) -> Any:
    """Extract output node result from GraphAI response.

    GraphAI returns a response in the format:
    {
        "results": {
            "output": { "result": { ... } },  # or just the result directly
            ...other_nodes...
        },
        "errors": {},
        "logs": [...]
    }

    For task chains, we need to extract `results.output.result` (or `results.output`)
    to pass to the next task as `user_input`.

    Args:
        response_data: Raw response from GraphAI server

    Returns:
        Extracted output data suitable for task chain consumption
    """
    # Check if this is a GraphAI response (has "results" key)
    if not isinstance(response_data, dict):
        return response_data

    if "results" not in response_data:
        # Not a GraphAI response, return as-is
        return response_data

    results = response_data.get("results", {})
    if not isinstance(results, dict):
        return response_data

    # Extract output node
    output_node = results.get("output")
    if output_node is None:
        # No output node, return full results
        logger.debug("[GRAPHAI_EXTRACT] No 'output' node found, returning full results")
        return results

    # Check if output has a nested "result" field
    if isinstance(output_node, dict) and "result" in output_node:
        extracted = output_node["result"]
        logger.info(
            f"[GRAPHAI_EXTRACT] Extracted results.output.result: "
            f"keys={list(extracted.keys()) if isinstance(extracted, dict) else type(extracted).__name__}"
        )
        return extracted

    # Return output node directly
    logger.info(
        f"[GRAPHAI_EXTRACT] Extracted results.output: "
        f"keys={list(output_node.keys()) if isinstance(output_node, dict) else type(output_node).__name__}"
    )
    return output_node
