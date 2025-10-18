"""Interface Master API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import new as ulid_new

from app.core.database import get_db
from app.models.interface_master import InterfaceMaster
from app.models.task_master import TaskMaster
from app.models.task_master_interface import TaskMasterInterface
from app.schemas.interface_master import (
    InterfaceAssociationCreate,
    InterfaceAssociationResponse,
    InterfaceMasterCreate,
    InterfaceMasterDetail,
    InterfaceMasterList,
    InterfaceMasterResponse,
    InterfaceMasterUpdate,
)
from app.services.interface_validator import (
    InterfaceValidationError,
    InterfaceValidator,
)

router = APIRouter()


@router.post(
    "/interface-masters", response_model=InterfaceMasterResponse, status_code=201
)
async def create_interface_master(
    interface_data: InterfaceMasterCreate,
    db: AsyncSession = Depends(get_db),
) -> InterfaceMasterResponse:
    """Create a new interface master with JSON Schema V7 validation."""
    # Validate input schema if provided
    if interface_data.input_schema:
        try:
            InterfaceValidator.validate_json_schema_v7(interface_data.input_schema)
        except InterfaceValidationError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid input_schema: {'; '.join(e.errors)}",
            ) from e

    # Validate output schema if provided
    if interface_data.output_schema:
        try:
            InterfaceValidator.validate_json_schema_v7(interface_data.output_schema)
        except InterfaceValidationError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid output_schema: {'; '.join(e.errors)}",
            ) from e

    # Generate ULID for interface ID
    interface_id = f"if_{ulid_new()}"

    # Create interface instance
    interface = InterfaceMaster(
        id=interface_id,
        name=interface_data.name,
        description=interface_data.description,
        input_schema=interface_data.input_schema,
        output_schema=interface_data.output_schema,
        is_active=True,
    )

    db.add(interface)
    await db.commit()
    await db.refresh(interface)

    return InterfaceMasterResponse(interface_id=interface.id, name=interface.name)


@router.get("/interface-masters", response_model=InterfaceMasterList)
async def list_interface_masters(
    is_active: bool | None = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
) -> InterfaceMasterList:
    """List interface masters with filtering and pagination."""
    # Build query conditions
    conditions = []
    if is_active is not None:
        # SQLite stores bool as int
        conditions.append(InterfaceMaster.is_active == (1 if is_active else 0))

    # Build base query
    query = select(InterfaceMaster)
    if conditions:
        query = query.where(and_(*conditions))

    # Get total count
    count_query = select(func.count(InterfaceMaster.id))
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = await db.scalar(count_query)

    # Apply pagination and ordering
    interfaces_query = (
        query.order_by(desc(InterfaceMaster.created_at))
        .offset((page - 1) * size)
        .limit(size)
    )
    interfaces_result = await db.scalars(interfaces_query)
    interfaces_list = interfaces_result.all()

    return InterfaceMasterList(
        interfaces=[
            InterfaceMasterDetail.model_validate(interface)
            for interface in interfaces_list
        ],
        total=total or 0,
        page=page,
        size=size,
    )


@router.get("/interface-masters/{interface_id}", response_model=InterfaceMasterDetail)
async def get_interface_master(
    interface_id: str,
    db: AsyncSession = Depends(get_db),
) -> InterfaceMasterDetail:
    """Get interface master details."""
    result = await db.get(InterfaceMaster, interface_id)
    if not result:
        raise HTTPException(status_code=404, detail="Interface master not found")

    return InterfaceMasterDetail.model_validate(result)


@router.put("/interface-masters/{interface_id}", response_model=InterfaceMasterResponse)
async def update_interface_master(
    interface_id: str,
    interface_data: InterfaceMasterUpdate,
    db: AsyncSession = Depends(get_db),
) -> InterfaceMasterResponse:
    """Update an interface master with JSON Schema V7 validation."""
    interface = await db.get(InterfaceMaster, interface_id)
    if not interface:
        raise HTTPException(status_code=404, detail="Interface master not found")

    # Validate input schema if provided
    if interface_data.input_schema is not None:
        try:
            InterfaceValidator.validate_json_schema_v7(interface_data.input_schema)
        except InterfaceValidationError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid input_schema: {'; '.join(e.errors)}",
            ) from e

    # Validate output schema if provided
    if interface_data.output_schema is not None:
        try:
            InterfaceValidator.validate_json_schema_v7(interface_data.output_schema)
        except InterfaceValidationError as e:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid output_schema: {'; '.join(e.errors)}",
            ) from e

    # Apply updates
    if interface_data.name is not None:
        interface.name = interface_data.name
    if interface_data.description is not None:
        interface.description = interface_data.description
    if interface_data.input_schema is not None:
        interface.input_schema = interface_data.input_schema
    if interface_data.output_schema is not None:
        interface.output_schema = interface_data.output_schema
    if interface_data.is_active is not None:
        interface.is_active = interface_data.is_active

    await db.commit()
    await db.refresh(interface)

    return InterfaceMasterResponse(interface_id=interface.id, name=interface.name)


@router.delete(
    "/interface-masters/{interface_id}", response_model=InterfaceMasterResponse
)
async def delete_interface_master(
    interface_id: str,
    db: AsyncSession = Depends(get_db),
) -> InterfaceMasterResponse:
    """Delete an interface master (logical deletion)."""
    interface = await db.get(InterfaceMaster, interface_id)
    if not interface:
        raise HTTPException(status_code=404, detail="Interface master not found")

    # Logical delete
    interface.is_active = False

    await db.commit()
    await db.refresh(interface)

    return InterfaceMasterResponse(interface_id=interface.id, name=interface.name)


@router.post(
    "/task-masters/{master_id}/interfaces",
    response_model=InterfaceAssociationResponse,
    status_code=201,
)
async def associate_interface_to_task_master(
    master_id: str,
    association_data: InterfaceAssociationCreate,
    db: AsyncSession = Depends(get_db),
) -> InterfaceAssociationResponse:
    """Associate an interface master to a task master."""
    # Check if task master exists
    task_master = await db.get(TaskMaster, master_id)
    if not task_master:
        raise HTTPException(status_code=404, detail="Task master not found")

    # Check if interface master exists
    interface = await db.get(InterfaceMaster, association_data.interface_id)
    if not interface:
        raise HTTPException(status_code=404, detail="Interface master not found")

    # Check if association already exists
    existing = await db.scalar(
        select(TaskMasterInterface).where(
            TaskMasterInterface.task_master_id == master_id,
            TaskMasterInterface.interface_id == association_data.interface_id,
        )
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="Interface already associated with this task master"
        )

    # Create association
    association = TaskMasterInterface(
        task_master_id=master_id,
        interface_id=association_data.interface_id,
        required=association_data.required,
    )

    db.add(association)
    await db.commit()
    await db.refresh(association)

    return InterfaceAssociationResponse.model_validate(association)


@router.get(
    "/task-masters/{master_id}/interfaces",
    response_model=list[InterfaceAssociationResponse],
)
async def list_task_master_interfaces(
    master_id: str,
    db: AsyncSession = Depends(get_db),
) -> list[InterfaceAssociationResponse]:
    """List all interfaces associated with a task master."""
    # Check if task master exists
    task_master = await db.get(TaskMaster, master_id)
    if not task_master:
        raise HTTPException(status_code=404, detail="Task master not found")

    # Get all associations
    result = await db.scalars(
        select(TaskMasterInterface).where(
            TaskMasterInterface.task_master_id == master_id
        )
    )
    associations = result.all()

    return [
        InterfaceAssociationResponse.model_validate(assoc) for assoc in associations
    ]
