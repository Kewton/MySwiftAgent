"""Job master version Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class JobMasterVersionResponse(BaseModel):
    """Schema for job master version detail response."""

    id: int = Field(..., description="Version record ID")
    master_id: str = Field(..., description="Job master identifier")
    version: int = Field(..., description="Version number")
    name: str = Field(..., description="Master name")
    method: str = Field(..., description="HTTP method")
    url: str = Field(..., description="Endpoint URL")
    headers: dict[str, Any] | None = Field(None, description="HTTP headers")
    params: dict[str, Any] | None = Field(None, description="Query parameters")
    body: dict[str, Any] | None = Field(None, description="Request body")
    timeout_sec: int = Field(..., description="Timeout in seconds")
    max_attempts: int = Field(..., description="Maximum retry attempts")
    backoff_strategy: str = Field(..., description="Backoff strategy")
    backoff_seconds: float = Field(..., description="Backoff seconds")
    ttl_seconds: int | None = Field(None, description="TTL in seconds")
    tags: list[str] | None = Field(None, description="Tags")
    created_at: datetime = Field(..., description="Version created at")
    created_by: str | None = Field(None, description="Created by user")
    change_reason: str | None = Field(None, description="Reason for change")

    model_config = {"from_attributes": True}


class JobMasterVersionListItem(BaseModel):
    """Schema for job master version list item."""

    version: int = Field(..., description="Version number")
    name: str = Field(..., description="Master name")
    created_at: datetime = Field(..., description="Version created at")
    created_by: str | None = Field(None, description="Created by user")
    change_reason: str | None = Field(None, description="Reason for change")
    has_changes: bool = Field(..., description="Has configuration changes")
    changed_fields: list[str] = Field(..., description="List of changed fields")

    model_config = {"from_attributes": True}


class JobMasterVersionList(BaseModel):
    """Schema for job master version list response."""

    master_id: str = Field(..., description="Job master identifier")
    current_version: int = Field(..., description="Current version number")
    total_versions: int = Field(..., description="Total number of versions")
    versions: list[JobMasterVersionListItem] = Field(..., description="Version list")


class CreateFromVersionRequest(BaseModel):
    """Schema for creating a new master from a version."""

    name: str = Field(..., description="New master name")
    tags: list[str] | None = Field(None, description="Tags")
    is_active: bool = Field(True, description="Active status")


class CreateFromVersionResponse(BaseModel):
    """Schema for create from version response."""

    master_id: str = Field(..., description="New master identifier")
    name: str = Field(..., description="New master name")
    current_version: int = Field(..., description="Current version (always 1)")
    source_master_id: str = Field(..., description="Source master identifier")
    source_version: int = Field(..., description="Source version number")
    created_at: datetime = Field(..., description="Created at")


class JobMasterUpdateResponse(BaseModel):
    """Schema for job master update response."""

    master_id: str = Field(..., description="Master identifier")
    previous_version: int = Field(..., description="Previous version number")
    current_version: int = Field(..., description="Current version number")
    auto_versioned: bool = Field(..., description="Whether auto-versioned")
    version_reason: str = Field(..., description="Reason for versioning decision")
