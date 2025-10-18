"""Task Master API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import new as ulid_new

from app.core.database import get_db
from app.models.interface_master import InterfaceMaster
from app.models.task import Task
from app.models.task_master import TaskMaster
from app.schemas.task import TaskDetail, TaskListAll
from app.schemas.task_master import (
    TaskMasterCreate,
    TaskMasterDetail,
    TaskMasterList,
    TaskMasterResponse,
    TaskMasterUpdate,
    TaskMasterUpdateResponse,
)
from app.services.task_version_manager import TaskVersionManager

router = APIRouter()


@router.post("/task-masters", response_model=TaskMasterResponse, status_code=201)
async def create_task_master(
    master_data: TaskMasterCreate,
    db: AsyncSession = Depends(get_db),
) -> TaskMasterResponse:
    """Create a new task master with interface validation."""
    # Validate input interface exists if provided
    if master_data.input_interface_id:
        input_interface = await db.get(InterfaceMaster, master_data.input_interface_id)
        if not input_interface:
            raise HTTPException(
                status_code=404,
                detail=f"Input interface not found: {master_data.input_interface_id}",
            )
        if not input_interface.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Input interface is not active: {master_data.input_interface_id}",
            )

    # Validate output interface exists if provided
    if master_data.output_interface_id:
        output_interface = await db.get(
            InterfaceMaster, master_data.output_interface_id
        )
        if not output_interface:
            raise HTTPException(
                status_code=404,
                detail=f"Output interface not found: {master_data.output_interface_id}",
            )
        if not output_interface.is_active:
            raise HTTPException(
                status_code=400,
                detail=f"Output interface is not active: {master_data.output_interface_id}",
            )

    # Generate ULID for master ID
    master_id = f"tm_{ulid_new()}"

    # Create master instance
    master = TaskMaster(
        id=master_id,
        name=master_data.name,
        description=master_data.description,
        method=master_data.method,
        url=str(master_data.url),
        headers=master_data.headers,
        body_template=master_data.body_template,
        timeout_sec=master_data.timeout_sec,
        input_interface_id=master_data.input_interface_id,
        output_interface_id=master_data.output_interface_id,
        is_active=True,
        current_version=1,
        created_by=master_data.created_by,
        updated_by=master_data.created_by,
    )

    db.add(master)
    await db.commit()
    await db.refresh(master)

    return TaskMasterResponse(
        master_id=master.id, name=master.name, current_version=master.current_version
    )


@router.get("/task-masters", response_model=TaskMasterList)
async def list_task_masters(
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
) -> TaskMasterList:
    """List task masters with filtering and pagination."""
    # Build query conditions
    conditions = []
    if is_active is not None:
        # SQLite stores bool as int
        conditions.append(TaskMaster.is_active == (1 if is_active else 0))

    # Build base query
    query = select(TaskMaster)
    if conditions:
        query = query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count(TaskMaster.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = await db.scalar(count_query)

    # Apply pagination and ordering
    masters_query = (
        query.order_by(desc(TaskMaster.created_at))
        .offset((page - 1) * size)
        .limit(size)
    )
    masters_result = await db.scalars(masters_query)
    masters_list = masters_result.all()

    return TaskMasterList(
        masters=[TaskMasterDetail.model_validate(master) for master in masters_list],
        total=total or 0,
        page=page,
        size=size,
    )


@router.get("/task-masters/{master_id}", response_model=TaskMasterDetail)
async def get_task_master(
    master_id: str,
    db: AsyncSession = Depends(get_db),
) -> TaskMasterDetail:
    """Get task master details."""
    result = await db.get(TaskMaster, master_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task master not found")

    return TaskMasterDetail.model_validate(result)


@router.put("/task-masters/{master_id}", response_model=TaskMasterUpdateResponse)
async def update_task_master(
    master_id: str,
    master_data: TaskMasterUpdate,
    db: AsyncSession = Depends(get_db),
) -> TaskMasterUpdateResponse:
    """Update a task master with automatic versioning and interface validation."""
    master = await db.get(TaskMaster, master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Task master not found")

    # Validate input interface if being updated
    if master_data.input_interface_id is not None:
        if master_data.input_interface_id:
            input_interface = await db.get(
                InterfaceMaster, master_data.input_interface_id
            )
            if not input_interface:
                raise HTTPException(
                    status_code=404,
                    detail=f"Input interface not found: {master_data.input_interface_id}",
                )
            if not input_interface.is_active:
                raise HTTPException(
                    status_code=400,
                    detail=f"Input interface is not active: {master_data.input_interface_id}",
                )

    # Validate output interface if being updated
    if master_data.output_interface_id is not None:
        if master_data.output_interface_id:
            output_interface = await db.get(
                InterfaceMaster, master_data.output_interface_id
            )
            if not output_interface:
                raise HTTPException(
                    status_code=404,
                    detail=f"Output interface not found: {master_data.output_interface_id}",
                )
            if not output_interface.is_active:
                raise HTTPException(
                    status_code=400,
                    detail=f"Output interface is not active: {master_data.output_interface_id}",
                )

    # Prepare update data
    update_dict = master_data.model_dump(
        exclude_unset=True, exclude={"change_reason", "updated_by"}
    )

    # Check if versioning needed
    should_version, reason = await TaskVersionManager.should_create_new_version(
        db, master, update_dict
    )

    previous_version = master.current_version

    if should_version:
        # Save current version to history
        await TaskVersionManager.save_current_version(
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
    if master_data.body_template is not None:
        master.body_template = master_data.body_template
    if master_data.timeout_sec is not None:
        master.timeout_sec = master_data.timeout_sec
    if master_data.input_interface_id is not None:
        master.input_interface_id = master_data.input_interface_id
    if master_data.output_interface_id is not None:
        master.output_interface_id = master_data.output_interface_id
    if master_data.updated_by is not None:
        master.updated_by = master_data.updated_by

    await db.commit()
    await db.refresh(master)

    return TaskMasterUpdateResponse(
        master_id=master.id,
        previous_version=previous_version,
        current_version=master.current_version,
        auto_versioned=should_version,
        version_reason=reason,
    )


@router.delete("/task-masters/{master_id}", response_model=TaskMasterResponse)
async def delete_task_master(
    master_id: str,
    db: AsyncSession = Depends(get_db),
) -> TaskMasterResponse:
    """Delete a task master (logical deletion)."""
    master = await db.get(TaskMaster, master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Task master not found")

    # Logical delete
    master.is_active = False

    await db.commit()
    await db.refresh(master)

    return TaskMasterResponse(
        master_id=master.id, name=master.name, current_version=master.current_version
    )


@router.get("/task-masters/{master_id}/tasks", response_model=TaskListAll)
async def list_task_master_tasks(
    master_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
) -> TaskListAll:
    """Get all tasks created from a specific task master."""
    # Check if master exists
    master = await db.get(TaskMaster, master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Task master not found")

    # Build query
    query = select(Task).where(Task.master_id == master_id)

    # Get total count
    count_query = select(func.count(Task.id)).where(Task.master_id == master_id)
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
