"""JobMasterTask API endpoints for workflow task management."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from ulid import new as ulid_new

from app.core.database import get_db
from app.models.job_master import JobMaster
from app.models.job_master_task import JobMasterTask
from app.models.task_master import TaskMaster
from app.schemas.job_master_task import (
    JobMasterTaskCreate,
    JobMasterTaskDetail,
    JobMasterTaskList,
    JobMasterTaskResponse,
    JobMasterTaskUpdate,
)

router = APIRouter()


@router.post(
    "/job-masters/{master_id}/tasks",
    response_model=JobMasterTaskResponse,
    status_code=201,
)
async def add_task_to_workflow(
    master_id: str,
    task_data: JobMasterTaskCreate,
    db: AsyncSession = Depends(get_db),
) -> JobMasterTaskResponse:
    """Add a TaskMaster to a JobMaster workflow.

    This endpoint associates a TaskMaster with a JobMaster, defining:
    - Execution order within the workflow
    - Input data template for dynamic configuration
    - Whether the task is required for Job success
    - Retry behavior on failure

    Args:
        master_id: JobMaster ID
        task_data: Task association configuration
        db: Database session

    Returns:
        JobMasterTaskResponse with created association details

    Raises:
        HTTPException 404: JobMaster or TaskMaster not found
        HTTPException 400: Duplicate order or task association
    """
    # Verify JobMaster exists
    job_master = await db.get(JobMaster, master_id)
    if not job_master:
        raise HTTPException(status_code=404, detail="Job master not found")

    # Verify TaskMaster exists
    task_master = await db.get(TaskMaster, task_data.task_master_id)
    if not task_master:
        raise HTTPException(status_code=404, detail="Task master not found")

    # Check for duplicate order
    existing_order = await db.execute(
        select(JobMasterTask).where(
            JobMasterTask.job_master_id == master_id,
            JobMasterTask.order == task_data.order,
        )
    )
    if existing_order.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Task with order {task_data.order} already exists in this workflow",
        )

    # Check for duplicate task association
    existing_task = await db.execute(
        select(JobMasterTask).where(
            JobMasterTask.job_master_id == master_id,
            JobMasterTask.task_master_id == task_data.task_master_id,
        )
    )
    if existing_task.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"TaskMaster {task_data.task_master_id} is already associated with this workflow",
        )

    # Create association
    association_id = f"jmt_{ulid_new()}"
    association = JobMasterTask(
        id=association_id,
        job_master_id=master_id,
        task_master_id=task_data.task_master_id,
        order=task_data.order,
        input_data_template=task_data.input_data_template,
        is_required=task_data.is_required,
        retry_on_failure=task_data.retry_on_failure,
    )

    db.add(association)
    await db.commit()
    await db.refresh(association)

    return JobMasterTaskResponse(
        id=association.id,
        task_master_id=association.task_master_id,
        order=association.order,
        job_master_id=association.job_master_id,
    )


@router.get("/job-masters/{master_id}/tasks", response_model=JobMasterTaskList)
async def list_workflow_tasks(
    master_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobMasterTaskList:
    """List all tasks in a JobMaster workflow.

    Returns tasks ordered by execution order (ascending).

    Args:
        master_id: JobMaster ID
        db: Database session

    Returns:
        JobMasterTaskList with all workflow tasks

    Raises:
        HTTPException 404: JobMaster not found
    """
    # Verify JobMaster exists
    job_master = await db.get(JobMaster, master_id)
    if not job_master:
        raise HTTPException(status_code=404, detail="Job master not found")

    # Fetch tasks with TaskMaster data for enrichment
    query = (
        select(JobMasterTask)
        .where(JobMasterTask.job_master_id == master_id)
        .options(selectinload(JobMasterTask.task_master))
        .order_by(JobMasterTask.order)
    )
    result = await db.execute(query)
    tasks = result.scalars().all()

    # Enrich with TaskMaster details
    task_details = []
    for task in tasks:
        task_dict = {
            "id": task.id,
            "job_master_id": task.job_master_id,
            "task_master_id": task.task_master_id,
            "order": task.order,
            "input_data_template": task.input_data_template,
            "is_required": task.is_required,
            "retry_on_failure": task.retry_on_failure,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "task_name": task.task_master.name if task.task_master else None,
            "task_description": task.task_master.description
            if task.task_master
            else None,
        }
        task_details.append(JobMasterTaskDetail.model_validate(task_dict))

    return JobMasterTaskList(tasks=task_details, total=len(task_details))


@router.put(
    "/job-masters/{master_id}/tasks/{task_master_id}",
    response_model=JobMasterTaskResponse,
)
async def update_workflow_task(
    master_id: str,
    task_master_id: str,
    task_data: JobMasterTaskUpdate,
    db: AsyncSession = Depends(get_db),
) -> JobMasterTaskResponse:
    """Update a task configuration in a JobMaster workflow.

    Supports partial updates - only provided fields will be updated.

    Args:
        master_id: JobMaster ID
        task_master_id: TaskMaster ID
        task_data: Updated task configuration
        db: Database session

    Returns:
        JobMasterTaskResponse with updated association details

    Raises:
        HTTPException 404: JobMaster or task association not found
        HTTPException 400: Duplicate order conflict
    """
    # Find existing association
    query = select(JobMasterTask).where(
        JobMasterTask.job_master_id == master_id,
        JobMasterTask.task_master_id == task_master_id,
    )
    result = await db.execute(query)
    association = result.scalar_one_or_none()

    if not association:
        raise HTTPException(
            status_code=404,
            detail=f"Task association not found in workflow {master_id}",
        )

    # Check for order conflict if order is being updated
    if task_data.order is not None and task_data.order != association.order:
        existing_order = await db.execute(
            select(JobMasterTask).where(
                JobMasterTask.job_master_id == master_id,
                JobMasterTask.order == task_data.order,
            )
        )
        if existing_order.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail=f"Task with order {task_data.order} already exists in this workflow",
            )

    # Apply updates
    if task_data.order is not None:
        association.order = task_data.order
    if task_data.input_data_template is not None:
        association.input_data_template = task_data.input_data_template
    if task_data.is_required is not None:
        association.is_required = task_data.is_required
    if task_data.retry_on_failure is not None:
        association.retry_on_failure = task_data.retry_on_failure

    await db.commit()
    await db.refresh(association)

    return JobMasterTaskResponse(
        id=association.id,
        task_master_id=association.task_master_id,
        order=association.order,
        job_master_id=association.job_master_id,
    )


@router.delete(
    "/job-masters/{master_id}/tasks/{task_master_id}",
    response_model=JobMasterTaskResponse,
)
async def remove_task_from_workflow(
    master_id: str,
    task_master_id: str,
    db: AsyncSession = Depends(get_db),
) -> JobMasterTaskResponse:
    """Remove a task from a JobMaster workflow.

    Args:
        master_id: JobMaster ID
        task_master_id: TaskMaster ID
        db: Database session

    Returns:
        JobMasterTaskResponse with deleted association details

    Raises:
        HTTPException 404: JobMaster or task association not found
    """
    # Find existing association
    query = select(JobMasterTask).where(
        JobMasterTask.job_master_id == master_id,
        JobMasterTask.task_master_id == task_master_id,
    )
    result = await db.execute(query)
    association = result.scalar_one_or_none()

    if not association:
        raise HTTPException(
            status_code=404,
            detail=f"Task association not found in workflow {master_id}",
        )

    # Store response data before deletion
    response_data = JobMasterTaskResponse(
        id=association.id,
        task_master_id=association.task_master_id,
        order=association.order,
        job_master_id=association.job_master_id,
    )

    # Delete association
    await db.delete(association)
    await db.commit()

    return response_data
