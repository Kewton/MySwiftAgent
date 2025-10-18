"""Job Master API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, case, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import new as ulid_new

from app.core.database import get_db
from app.models.job import Job, JobStatus
from app.models.job_master import JobMaster
from app.models.task import Task, TaskStatus
from app.models.task_master import TaskMaster
from app.schemas.job import JobDetail, JobList
from app.schemas.job_master import (
    JobMasterCreate,
    JobMasterDetail,
    JobMasterList,
    JobMasterResponse,
    JobMasterStats,
    JobMasterUpdate,
    TaskMasterStats,
)
from app.schemas.job_master_version import JobMasterUpdateResponse
from app.services.version_manager import VersionManager
from app.services.workflow_validator import WorkflowValidationError, WorkflowValidator

router = APIRouter()


@router.post("/job-masters", response_model=JobMasterResponse, status_code=201)
async def create_job_master(
    master_data: JobMasterCreate,
    db: AsyncSession = Depends(get_db),
) -> JobMasterResponse:
    """Create a new job master."""
    # Generate ULID for master ID
    master_id = f"jm_{ulid_new()}"

    # Create master instance
    master = JobMaster(
        id=master_id,
        name=master_data.name,
        description=master_data.description,
        method=master_data.method,
        url=str(master_data.url),
        headers=master_data.headers,
        params=master_data.params,
        body=master_data.body,
        timeout_sec=master_data.timeout_sec,
        max_attempts=master_data.max_attempts,
        backoff_strategy=master_data.backoff_strategy,
        backoff_seconds=master_data.backoff_seconds,
        ttl_seconds=master_data.ttl_seconds,
        tags=master_data.tags,
        is_active=True,
        current_version=1,
        created_by=master_data.created_by,
        updated_by=master_data.created_by,
    )

    db.add(master)
    await db.flush()

    # Save initial version
    await VersionManager.save_current_version(db, master, change_reason="初回作成")

    await db.commit()
    await db.refresh(master)

    return JobMasterResponse(
        master_id=master.id, name=master.name, is_active=bool(master.is_active)
    )


@router.get("/job-masters", response_model=JobMasterList)
async def list_job_masters(
    tags: list[str] | None = Query(None, description="Filter by tags"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
) -> JobMasterList:
    """List job masters with filtering and pagination."""
    # Build query conditions
    conditions = []
    if is_active is not None:
        # SQLite stores bool as int
        conditions.append(JobMaster.is_active == (1 if is_active else 0))
    if tags:
        # Filter masters that have any of the specified tags
        tag_conditions = [
            JobMaster.tags.op("JSON_EXTRACT")("$[*]").op("LIKE")(f"%{tag}%")
            for tag in tags
        ]
        conditions.append(or_(*tag_conditions))

    # Build base query
    query = select(JobMaster)
    if conditions:
        query = query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count(JobMaster.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = await db.scalar(count_query)

    # Apply pagination and ordering
    masters_query = (
        query.order_by(desc(JobMaster.created_at)).offset((page - 1) * size).limit(size)
    )
    masters_result = await db.scalars(masters_query)
    masters_list = masters_result.all()

    return JobMasterList(
        masters=[JobMasterDetail.model_validate(master) for master in masters_list],
        total=total or 0,
        page=page,
        size=size,
    )


@router.get("/job-masters/{master_id}", response_model=JobMasterDetail)
async def get_job_master(
    master_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobMasterDetail:
    """Get job master details."""
    result = await db.get(JobMaster, master_id)
    if not result:
        raise HTTPException(status_code=404, detail="Job master not found")

    return JobMasterDetail.model_validate(result)


@router.put("/job-masters/{master_id}", response_model=JobMasterUpdateResponse)
async def update_job_master(
    master_id: str,
    master_data: JobMasterUpdate,
    db: AsyncSession = Depends(get_db),
) -> JobMasterUpdateResponse:
    """Update a job master with automatic versioning."""
    master = await db.get(JobMaster, master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Job master not found")

    # Prepare update data
    update_dict = master_data.model_dump(
        exclude_unset=True, exclude={"change_reason", "updated_by"}
    )

    # Check if versioning needed
    should_version, reason = await VersionManager.should_create_new_version(
        db, master, update_dict
    )

    previous_version = master.current_version

    if should_version:
        # Save current version to history
        await VersionManager.save_current_version(
            db, master, change_reason=master_data.change_reason
        )
        # Increment version
        master.current_version += 1

    # Apply updates
    if master_data.name is not None:
        master.name = master_data.name
    if master_data.description is not None:
        master.description = master_data.description
    if master_data.method is not None:
        master.method = master_data.method
    if master_data.url is not None:
        master.url = str(master_data.url)
    if master_data.headers is not None:
        master.headers = master_data.headers
    if master_data.params is not None:
        master.params = master_data.params
    if master_data.body is not None:
        master.body = master_data.body
    if master_data.timeout_sec is not None:
        master.timeout_sec = master_data.timeout_sec
    if master_data.max_attempts is not None:
        master.max_attempts = master_data.max_attempts
    if master_data.backoff_strategy is not None:
        master.backoff_strategy = master_data.backoff_strategy
    if master_data.backoff_seconds is not None:
        master.backoff_seconds = master_data.backoff_seconds
    if master_data.ttl_seconds is not None:
        master.ttl_seconds = master_data.ttl_seconds
    if master_data.tags is not None:
        master.tags = master_data.tags
    if master_data.updated_by is not None:
        master.updated_by = master_data.updated_by

    await db.commit()
    await db.refresh(master)

    return JobMasterUpdateResponse(
        master_id=master.id,
        previous_version=previous_version,
        current_version=master.current_version,
        auto_versioned=should_version,
        version_reason=reason,
    )


@router.delete("/job-masters/{master_id}", response_model=JobMasterResponse)
async def delete_job_master(
    master_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobMasterResponse:
    """Delete a job master (logical deletion)."""
    master = await db.get(JobMaster, master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Job master not found")

    # Logical delete
    master.is_active = False

    await db.commit()
    await db.refresh(master)

    return JobMasterResponse(
        master_id=master.id, name=master.name, is_active=bool(master.is_active)
    )


@router.get("/job-masters/{master_id}/jobs", response_model=JobList)
async def list_jobs_from_master(
    master_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
) -> JobList:
    """List jobs created from a specific master."""
    # Check if master exists
    master = await db.get(JobMaster, master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Job master not found")

    # Build query
    query = select(Job).where(Job.master_id == master_id)

    # Get total count
    count_query = select(func.count(Job.id)).where(Job.master_id == master_id)
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


@router.get("/job-masters/{master_id}/stats", response_model=JobMasterStats)
async def get_job_master_stats(
    master_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobMasterStats:
    """Get JobMaster execution statistics.

    Returns real-time statistics for:
    - Overall Job execution metrics (total, success, failure, canceled counts)
    - Success rate percentage
    - Task-level statistics with success rates and average duration

    All statistics are calculated in real-time from the database.
    """
    # Check if master exists
    master = await db.get(JobMaster, master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Job master not found")

    # Get Job statistics (real-time aggregation)
    job_stats_query = select(
        func.count(Job.id).label("total_executions"),
        func.sum(case((Job.status == JobStatus.SUCCEEDED, 1), else_=0)).label(
            "success_count"
        ),
        func.sum(case((Job.status == JobStatus.FAILED, 1), else_=0)).label(
            "failure_count"
        ),
        func.sum(case((Job.status == JobStatus.CANCELED, 1), else_=0)).label(
            "canceled_count"
        ),
        func.max(Job.finished_at).label("last_executed_at"),
    ).where(Job.master_id == master_id)

    job_stats = await db.execute(job_stats_query)
    stats_row = job_stats.first()

    # Get Task-level statistics
    # NOTE: In Phase 3, when job_master_tasks table is created,
    #       this query will be updated to use that table for proper ordering
    task_stats_query = (
        select(
            TaskMaster.id,
            TaskMaster.name,
            Task.order,
            func.count(Task.id).label("total_executions"),
            func.sum(case((Task.status == TaskStatus.SUCCEEDED, 1), else_=0)).label(
                "success_count"
            ),
            func.sum(case((Task.status == TaskStatus.FAILED, 1), else_=0)).label(
                "failure_count"
            ),
            func.avg(Task.duration_ms).label("avg_duration_ms"),
        )
        .join(Task, TaskMaster.id == Task.master_id)
        .join(Job, Job.id == Task.job_id)
        .where(Job.master_id == master_id)
        .group_by(TaskMaster.id, TaskMaster.name, Task.order)
        .order_by(Task.order)
    )

    task_stats_result = await db.execute(task_stats_query)
    task_stats = task_stats_result.all()

    # Calculate success rate
    total = stats_row.total_executions or 0
    success_rate = (stats_row.success_count / total * 100) if total > 0 else 0.0

    return JobMasterStats(
        master_id=master.id,
        name=master.name,
        total_executions=total,
        success_count=stats_row.success_count or 0,
        failure_count=stats_row.failure_count or 0,
        canceled_count=stats_row.canceled_count or 0,
        success_rate=round(success_rate, 2),
        last_executed_at=stats_row.last_executed_at,
        task_stats=[
            TaskMasterStats(
                task_master_id=ts.id,
                task_name=ts.name,
                order=ts.order,
                total_executions=ts.total_executions or 0,
                success_count=ts.success_count or 0,
                failure_count=ts.failure_count or 0,
                success_rate=round(
                    (ts.success_count / ts.total_executions * 100),
                    2,
                )
                if ts.total_executions > 0
                else 0.0,
                avg_duration_ms=round(ts.avg_duration_ms, 2)
                if ts.avg_duration_ms
                else None,
            )
            for ts in task_stats
        ],
    )


@router.get("/job-masters/{master_id}/validate-workflow")
async def validate_workflow(
    master_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Validate workflow interface compatibility.

    Returns a detailed validation report including:
    - is_valid: Whether the workflow passes all validation checks
    - errors: List of validation errors
    - warnings: List of validation warnings
    - task_chain: Visualization of task interfaces in execution order

    This endpoint is useful for debugging interface mismatches before
    attempting to publish a workflow version.

    Args:
        master_id: JobMaster ID
        db: Database session

    Returns:
        Validation report dict

    Raises:
        HTTPException 404: JobMaster not found
    """
    # Check if master exists
    master = await db.get(JobMaster, master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Job master not found")

    # Get validation report
    report = await WorkflowValidator.get_workflow_validation_report(db, master)

    return report


@router.post("/job-masters/{master_id}/publish-version")
async def publish_workflow_version(
    master_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobMasterUpdateResponse:
    """Publish a new workflow version with interface validation.

    This endpoint performs the following steps:
    1. Validates workflow interface compatibility
    2. Saves current version to history
    3. Increments version number
    4. Returns new version details

    If interface validation fails, the version will not be published and
    an HTTP 400 error will be returned with details about the validation error.

    Args:
        master_id: JobMaster ID
        db: Database session

    Returns:
        JobMasterUpdateResponse with new version details

    Raises:
        HTTPException 404: JobMaster not found
        HTTPException 400: Workflow validation failed
    """
    # Check if master exists
    master = await db.get(JobMaster, master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Job master not found")

    # Validate workflow interfaces
    try:
        await WorkflowValidator.validate_workflow_interfaces(db, master)
    except WorkflowValidationError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Workflow validation failed",
                "message": e.message,
                "details": e.details,
            },
        ) from e

    # Save current version to history
    previous_version = master.current_version
    await VersionManager.save_current_version(
        db, master, change_reason="Workflow version published with interface validation"
    )

    # Increment version
    master.current_version += 1

    await db.commit()
    await db.refresh(master)

    return JobMasterUpdateResponse(
        master_id=master.id,
        previous_version=previous_version,
        current_version=master.current_version,
        auto_versioned=True,
        version_reason="Workflow version published (interface validated)",
    )
