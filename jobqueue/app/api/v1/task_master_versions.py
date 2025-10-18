"""Task master version API endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from ulid import new as ulid_new

from app.core.database import get_db
from app.models.task_master import TaskMaster
from app.schemas.task_master_version import (
    CreateFromVersionRequest,
    CreateFromVersionResponse,
    TaskMasterVersionList,
    TaskMasterVersionListItem,
    TaskMasterVersionResponse,
)
from app.services.task_version_manager import TaskVersionManager

router = APIRouter()


@router.get("/task-masters/{master_id}/versions", response_model=TaskMasterVersionList)
async def list_versions(
    master_id: str,
    db: AsyncSession = Depends(get_db),
) -> TaskMasterVersionList:
    """Get version history for a task master."""
    # Check if master exists
    master = await db.get(TaskMaster, master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Task master not found")

    # Get version history
    versions = await TaskVersionManager.get_version_history(db, master_id)

    # Build response with change detection
    version_items = []
    for i, version in enumerate(versions):
        prev_version = versions[i + 1] if i + 1 < len(versions) else None
        changed_fields = TaskVersionManager.compare_versions(prev_version, version)

        version_items.append(
            TaskMasterVersionListItem(
                version=version.version,
                name=version.name,
                created_at=version.created_at,
                created_by=version.created_by,
                change_reason=version.change_reason,
                has_changes=len(changed_fields) > 0,
                changed_fields=changed_fields,
            )
        )

    return TaskMasterVersionList(
        master_id=master_id,
        current_version=master.current_version,
        total_versions=len(versions),
        versions=version_items,
    )


@router.get(
    "/task-masters/{master_id}/versions/{version}",
    response_model=TaskMasterVersionResponse,
)
async def get_version(
    master_id: str,
    version: int,
    db: AsyncSession = Depends(get_db),
) -> TaskMasterVersionResponse:
    """Get specific version details of a task master."""
    # Check if master exists
    master = await db.get(TaskMaster, master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Task master not found")

    # Get version
    version_entry = await TaskVersionManager.get_version(db, master_id, version)
    if not version_entry:
        raise HTTPException(status_code=404, detail="Version not found")

    return TaskMasterVersionResponse.model_validate(version_entry)


@router.post(
    "/task-masters/{master_id}/versions/{version}/create-from",
    response_model=CreateFromVersionResponse,
    status_code=201,
)
async def create_from_version(
    master_id: str,
    version: int,
    request: CreateFromVersionRequest,
    db: AsyncSession = Depends(get_db),
) -> CreateFromVersionResponse:
    """Create a new task master from a specific version."""
    # Check if master exists
    master = await db.get(TaskMaster, master_id)
    if not master:
        raise HTTPException(status_code=404, detail="Task master not found")

    # Get version
    version_entry = await TaskVersionManager.get_version(db, master_id, version)
    if not version_entry:
        raise HTTPException(status_code=404, detail="Version not found")

    # Create new master with version settings
    new_master_id = f"tm_{ulid_new()}"
    new_master = TaskMaster(
        id=new_master_id,
        name=request.name,
        description=version_entry.description,
        method=version_entry.method,
        url=version_entry.url,
        headers=version_entry.headers,
        body_template=version_entry.body_template,
        timeout_sec=version_entry.timeout_sec,
        is_active=request.is_active,
        current_version=1,  # Start with version 1
        created_at=datetime.now(UTC),
    )

    db.add(new_master)
    await db.flush()

    # Save initial version
    await TaskVersionManager.save_current_version(
        db,
        new_master,
        change_reason=f"Version {version} から作成",
    )
    await db.commit()
    await db.refresh(new_master)

    return CreateFromVersionResponse(
        master_id=new_master.id,
        name=new_master.name,
        current_version=1,
        source_master_id=master_id,
        source_version=version,
        created_at=new_master.created_at,
    )
