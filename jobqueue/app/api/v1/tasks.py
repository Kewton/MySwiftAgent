"""Task API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.job import Job, JobStatus
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskDetail, TaskList, TaskRetryResponse

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
