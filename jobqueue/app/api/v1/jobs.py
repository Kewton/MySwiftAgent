"""Job API endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import new as ulid_new

from app.core.database import get_db
from app.core.merge import merge_dict_deep, merge_dict_shallow, merge_tags
from app.models.job import Job, JobStatus
from app.models.job_master import JobMaster
from app.models.result import JobResult
from app.schemas.job import (
    JobCreate,
    JobCreateFromMaster,
    JobDetail,
    JobList,
    JobResponse,
)
from app.schemas.result import JobResultResponse

router = APIRouter()


@router.post("/jobs", response_model=JobResponse, status_code=201)
async def create_job(
    job_data: JobCreate,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Create a new job."""
    # Generate ULID for job ID
    job_id = f"j_{ulid_new()}"

    # Create job instance
    job = Job(
        id=job_id,
        name=job_data.name,
        method=job_data.method,
        url=str(job_data.url),
        headers=job_data.headers,
        params=job_data.params,
        body=job_data.body,
        timeout_sec=job_data.timeout_sec,
        priority=job_data.priority,
        max_attempts=job_data.max_attempts,
        backoff_strategy=job_data.backoff_strategy,
        backoff_seconds=job_data.backoff_seconds,
        scheduled_at=job_data.scheduled_at,
        ttl_seconds=job_data.ttl_seconds,
        tags=job_data.tags,
        next_attempt_at=job_data.scheduled_at or datetime.now(UTC),
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)

    return JobResponse(job_id=job.id, status=job.status)


@router.get("/jobs/{job_id}", response_model=JobDetail)
async def get_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobDetail:
    """Get job details."""
    result = await db.get(Job, job_id)
    if not result:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobDetail.model_validate(result)


@router.get("/jobs/{job_id}/result", response_model=JobResultResponse)
async def get_job_result(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobResultResponse:
    """Get job result."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get result if exists
    result = await db.scalar(select(JobResult).where(JobResult.job_id == job_id))

    return JobResultResponse(
        job_id=job.id,
        status=job.status,
        response_status=result.response_status if result else None,
        response_headers=result.response_headers if result else None,
        response_body=result.response_body if result else None,
        error=result.error if result else None,
        duration_ms=result.duration_ms if result else None,
    )


@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Cancel a job."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in [JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status: {job.status}",
        )

    job.status = JobStatus.CANCELED
    job.finished_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(job)

    return JobResponse(job_id=job.id, status=job.status)


@router.post("/jobs/{job_id}/retry", response_model=JobResponse)
async def retry_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Retry a failed job."""
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status != JobStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail=f"Only failed jobs can be retried. Current status: {job.status}",
        )

    # Reset job status for retry
    job.status = JobStatus.QUEUED
    job.attempt = 0
    job.started_at = None
    job.finished_at = None
    job.next_attempt_at = datetime.now(UTC)

    await db.commit()
    await db.refresh(job)

    return JobResponse(job_id=job.id, status=job.status)


@router.post(
    "/jobs/from-master/{master_id}", response_model=JobResponse, status_code=201
)
async def create_job_from_master(
    master_id: str,
    job_data: JobCreateFromMaster,
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    """Create a job from a master template."""
    # Get master
    master = await db.get(JobMaster, master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Job master not found")

    # Check if master is active
    if not master.is_active:
        raise HTTPException(status_code=400, detail="Job master is inactive")

    # Merge parameters
    merged_headers = merge_dict_shallow(master.headers, job_data.headers)
    merged_params = merge_dict_shallow(master.params, job_data.params)
    merged_body = merge_dict_deep(master.body, job_data.body)
    merged_tags = merge_tags(master.tags, job_data.tags)

    # Use override values or master defaults
    timeout_sec = job_data.timeout_sec or master.timeout_sec
    max_attempts = job_data.max_attempts or master.max_attempts
    backoff_strategy = job_data.backoff_strategy or master.backoff_strategy
    backoff_seconds = job_data.backoff_seconds or master.backoff_seconds
    priority = job_data.priority or 5  # Default priority

    # Generate ULID for job ID
    job_id = f"j_{ulid_new()}"

    # Create job instance
    job = Job(
        id=job_id,
        name=job_data.name or master.name,
        master_id=master_id,
        method=master.method,
        url=master.url,
        headers=merged_headers,
        params=merged_params,
        body=merged_body,
        timeout_sec=timeout_sec,
        priority=priority,
        max_attempts=max_attempts,
        backoff_strategy=backoff_strategy,
        backoff_seconds=backoff_seconds,
        scheduled_at=job_data.scheduled_at,
        ttl_seconds=master.ttl_seconds,
        tags=merged_tags,
        next_attempt_at=job_data.scheduled_at or datetime.now(UTC),
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)

    return JobResponse(job_id=job.id, status=job.status)


@router.get("/jobs", response_model=JobList)
async def list_jobs(
    status: JobStatus | None = Query(None, description="Filter by job status"),
    tags: list[str] | None = Query(None, description="Filter by tags"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
) -> JobList:
    """List jobs with filtering and pagination."""
    # Build query conditions
    conditions = []
    if status:
        conditions.append(Job.status == status)
    if tags:
        # Filter jobs that have any of the specified tags
        tag_conditions = [
            Job.tags.op("JSON_EXTRACT")("$[*]").op("LIKE")(f"%{tag}%") for tag in tags
        ]
        conditions.append(or_(*tag_conditions))

    # Build base query
    query = select(Job)
    if conditions:
        query = query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count(Job.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = await db.scalar(count_query)

    # Apply pagination and ordering
    jobs_query = (
        query.order_by(desc(Job.created_at)).offset((page - 1) * size).limit(size)
    )
    jobs_result = await db.scalars(jobs_query)
    jobs_list = jobs_result.all()

    return JobList(
        jobs=[JobDetail.model_validate(job) for job in jobs_list],
        total=total or 0,
        page=page,
        size=size,
    )
