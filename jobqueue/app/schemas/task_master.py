"""Task master schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class TaskMasterCreate(BaseModel):
    """Task master creation schema."""

    name: str = Field(..., min_length=1, max_length=255, description="Task name")
    description: str | None = Field(None, description="Task description")
    method: str = Field(
        ..., pattern="^(GET|POST|PUT|DELETE|PATCH)$", description="HTTP method"
    )
    url: HttpUrl = Field(..., description="Endpoint URL")
    headers: dict[str, Any] | None = Field(None, description="HTTP headers")
    body_template: dict[str, Any] | None = Field(
        None, description="Request body template"
    )
    timeout_sec: int = Field(30, ge=1, le=3600, description="Timeout in seconds")
    input_interface_id: str | None = Field(
        None,
        description="Input interface ID (if_XXXXX format)",
        pattern="^if_[0-9A-HJKMNP-TV-Z]{26}$",
    )
    output_interface_id: str | None = Field(
        None,
        description="Output interface ID (if_XXXXX format)",
        pattern="^if_[0-9A-HJKMNP-TV-Z]{26}$",
    )
    created_by: str | None = Field(None, max_length=100, description="Creator")


class TaskMasterUpdate(BaseModel):
    """Task master update schema."""

    name: str | None = Field(
        None, min_length=1, max_length=255, description="Task name"
    )
    description: str | None = Field(None, description="Task description")
    method: str | None = Field(
        None, pattern="^(GET|POST|PUT|DELETE|PATCH)$", description="HTTP method"
    )
    url: HttpUrl | None = Field(None, description="Endpoint URL")
    headers: dict[str, Any] | None = Field(None, description="HTTP headers")
    body_template: dict[str, Any] | None = Field(
        None, description="Request body template"
    )
    timeout_sec: int | None = Field(
        None, ge=1, le=3600, description="Timeout in seconds"
    )
    input_interface_id: str | None = Field(
        None,
        description="Input interface ID (if_XXXXX format)",
        pattern="^if_[0-9A-HJKMNP-TV-Z]{26}$",
    )
    output_interface_id: str | None = Field(
        None,
        description="Output interface ID (if_XXXXX format)",
        pattern="^if_[0-9A-HJKMNP-TV-Z]{26}$",
    )
    change_reason: str | None = Field(None, description="Reason for change")
    updated_by: str | None = Field(None, max_length=100, description="Updater")


class TaskMasterResponse(BaseModel):
    """Task master response schema."""

    master_id: str
    name: str
    current_version: int


class TaskMasterDetail(BaseModel):
    """Task master detail schema."""

    id: str
    name: str
    description: str | None
    method: str
    url: str
    headers: dict[str, Any] | None
    body_template: dict[str, Any] | None
    timeout_sec: int
    input_interface_id: str | None
    output_interface_id: str | None
    current_version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    updated_by: str | None

    model_config = {"from_attributes": True}


class TaskMasterList(BaseModel):
    """Task master list schema."""

    masters: list[TaskMasterDetail]
    total: int
    page: int
    size: int


class TaskMasterUpdateResponse(BaseModel):
    """Task master update response schema."""

    master_id: str
    previous_version: int
    current_version: int
    auto_versioned: bool
    version_reason: str
