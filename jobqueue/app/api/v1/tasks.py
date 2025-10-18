"""Task API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.job import Job, JobStatus
from app.models.task import Task, TaskStatus
from app.schemas.task import (
    TaskDetail,
    TaskList,
    TaskListAll,
    TaskRetryResponse,
    TaskStats,
)

router = APIRouter()


@router.get("/jobs/{job_id}/tasks", response_model=TaskList)
async def list_job_tasks(
    job_id: str,
    db: AsyncSession = Depends(get_db),
) -> TaskList:
    """Get all tasks for a job."""
    # Check if job exists
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Get all tasks ordered by execution order
    result = await db.scalars(
        select(Task).where(Task.job_id == job_id).order_by(Task.order)
    )
    tasks = result.all()

    return TaskList(
        job_id=job_id,
        tasks=[TaskDetail.model_validate(task) for task in tasks],
        total=len(tasks),
    )


@router.get("/tasks/stats", response_model=TaskStats)
async def get_task_stats(
    job_id: str | None = Query(None, description="Filter by job ID"),
    master_id: str | None = Query(None, description="Filter by task master ID"),
    db: AsyncSession = Depends(get_db),
) -> TaskStats:
    """Get task execution statistics."""
    # Build query conditions
    conditions = []
    if job_id:
        conditions.append(Task.job_id == job_id)
    if master_id:
        conditions.append(Task.master_id == master_id)

    # Base query
    base_query = select(Task)
    if conditions:
        base_query = base_query.where(and_(*conditions))

    # Total tasks
    total_query = select(func.count(Task.id))
    if conditions:
        total_query = total_query.where(and_(*conditions))
    total_tasks = await db.scalar(total_query) or 0

    # Count by status
    queued_query = select(func.count(Task.id)).where(Task.status == TaskStatus.QUEUED)
    running_query = select(func.count(Task.id)).where(Task.status == TaskStatus.RUNNING)
    succeeded_query = select(func.count(Task.id)).where(
        Task.status == TaskStatus.SUCCEEDED
    )
    failed_query = select(func.count(Task.id)).where(Task.status == TaskStatus.FAILED)
    skipped_query = select(func.count(Task.id)).where(Task.status == TaskStatus.SKIPPED)

    if conditions:
        queued_query = queued_query.where(and_(*conditions))
        running_query = running_query.where(and_(*conditions))
        succeeded_query = succeeded_query.where(and_(*conditions))
        failed_query = failed_query.where(and_(*conditions))
        skipped_query = skipped_query.where(and_(*conditions))

    queued_tasks = await db.scalar(queued_query) or 0
    running_tasks = await db.scalar(running_query) or 0
    succeeded_tasks = await db.scalar(succeeded_query) or 0
    failed_tasks = await db.scalar(failed_query) or 0
    skipped_tasks = await db.scalar(skipped_query) or 0

    # Calculate success rate
    completed_tasks = succeeded_tasks + failed_tasks
    success_rate = (
        (succeeded_tasks / completed_tasks * 100) if completed_tasks > 0 else 0.0
    )

    # Average duration (only for succeeded tasks)
    avg_duration_query = select(func.avg(Task.duration_ms)).where(
        Task.status == TaskStatus.SUCCEEDED, Task.duration_ms.isnot(None)
    )
    if conditions:
        avg_duration_query = avg_duration_query.where(and_(*conditions))
    avg_duration = await db.scalar(avg_duration_query)

    return TaskStats(
        total_tasks=total_tasks,
        queued_tasks=queued_tasks,
        running_tasks=running_tasks,
        succeeded_tasks=succeeded_tasks,
        failed_tasks=failed_tasks,
        skipped_tasks=skipped_tasks,
        success_rate=round(success_rate, 2),
        average_duration_ms=round(avg_duration, 2) if avg_duration else None,
    )


@router.get("/tasks/{task_id}", response_model=TaskDetail)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> TaskDetail:
    """Get task details."""
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskDetail.model_validate(task)


@router.post("/tasks/{task_id}/retry", response_model=TaskRetryResponse)
async def retry_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
) -> TaskRetryResponse:
    """Retry a failed task and all subsequent tasks."""
    # Get the task
    task = await db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != TaskStatus.FAILED:
        raise HTTPException(
            status_code=400,
            detail=f"Only failed tasks can be retried. Current status: {task.status}",
        )

    # Get all tasks from this task onwards (same job, order >= this task's order)
    result = await db.scalars(
        select(Task)
        .where(Task.job_id == task.job_id, Task.order >= task.order)
        .order_by(Task.order)
    )
    tasks_to_retry = result.all()

    # Reset all tasks to QUEUED
    for t in tasks_to_retry:
        t.status = TaskStatus.QUEUED
        t.output_data = None
        t.error = None
        t.started_at = None
        t.finished_at = None
        t.duration_ms = None
        t.attempt += 1

    # Reset job status
    job = await db.get(Job, task.job_id)
    if job:
        job.status = JobStatus.QUEUED
        job.started_at = None
        job.finished_at = None

    await db.commit()
    await db.refresh(task)

    return TaskRetryResponse(
        task_id=task.id,
        status=task.status,
        message=f"Task and {len(tasks_to_retry) - 1} subsequent tasks have been queued for retry",
    )


@router.get("/tasks", response_model=TaskListAll)
async def list_all_tasks(
    status: str | None = Query(None, description="Filter by task status"),
    job_id: str | None = Query(None, description="Filter by job ID"),
    master_id: str | None = Query(None, description="Filter by task master ID"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
) -> TaskListAll:
    """Get all tasks with filtering and pagination."""
    # Build query conditions
    conditions = []
    if status:
        conditions.append(Task.status == status)
    if job_id:
        conditions.append(Task.job_id == job_id)
    if master_id:
        conditions.append(Task.master_id == master_id)

    # Build base query
    query = select(Task)
    if conditions:
        query = query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count(Task.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = await db.scalar(count_query)

    # Apply pagination and ordering
    tasks_query = (
        query.order_by(desc(Task.created_at)).offset((page - 1) * size).limit(size)
    )
    tasks_result = await db.scalars(tasks_query)
    tasks_list = tasks_result.all()

    return TaskListAll(
        tasks=[TaskDetail.model_validate(task) for task in tasks_list],
        total=total or 0,
        page=page,
        size=size,
    )
