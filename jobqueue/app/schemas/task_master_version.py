"""Task master version schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskMasterVersionResponse(BaseModel):
    """Task master version detail response schema."""

    id: int
    master_id: str
    version: int
    name: str
    description: str | None
    method: str
    url: str
    headers: dict[str, Any] | None
    body_template: dict[str, Any] | None
    timeout_sec: int
    created_at: datetime
    created_by: str | None
    change_reason: str | None

    model_config = {"from_attributes": True}


class TaskMasterVersionListItem(BaseModel):
    """Task master version list item schema."""

    version: int
    name: str
    created_at: datetime
    created_by: str | None
    change_reason: str | None
    has_changes: bool
    changed_fields: list[str]


class TaskMasterVersionList(BaseModel):
    """Task master version list schema."""

    master_id: str
    current_version: int
    total_versions: int
    versions: list[TaskMasterVersionListItem]


class CreateFromVersionRequest(BaseModel):
    """Create task master from version request schema."""

    name: str = Field(
        ..., min_length=1, max_length=255, description="New task master name"
    )
    tags: list[str] | None = Field(None, description="Tags for the new master")
    is_active: bool = Field(True, description="Active status")


class CreateFromVersionResponse(BaseModel):
    """Create task master from version response schema."""

    master_id: str
    name: str
    current_version: int
    source_master_id: str
    source_version: int
    created_at: datetime
