"""Job Master Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.models.job import BackoffStrategy


class JobMasterCreate(BaseModel):
    """Schema for creating a job master."""

    name: str = Field(..., description="Master name", max_length=255)
    description: str | None = Field(None, description="Master description")

    # HTTP defaults
    method: str = Field(
        ...,
        description="HTTP method",
        pattern="^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)$",
    )
    url: HttpUrl = Field(..., description="Target URL")
    headers: dict[str, str] | None = Field(None, description="Default headers")
    params: dict[str, Any] | None = Field(None, description="Default query params")
    body: dict[str, Any] | None = Field(None, description="Default request body")
    timeout_sec: int = Field(
        default=30, ge=1, le=3600, description="Timeout in seconds (max: 1 hour)"
    )

    # Retry defaults
    max_attempts: int = Field(
        default=1, ge=1, le=10, description="Maximum retry attempts"
    )
    backoff_strategy: BackoffStrategy = Field(
        default=BackoffStrategy.EXPONENTIAL, description="Backoff strategy for retries"
    )
    backoff_seconds: float = Field(
        default=5.0, ge=0.1, description="Base backoff time in seconds"
    )

    # Scheduling defaults
    ttl_seconds: int | None = Field(
        default=604800, ge=0, description="Time to live in seconds (default: 7 days)"
    )
    tags: list[str] | None = Field(None, description="Default tags")

    # Audit
    created_by: str | None = Field(None, description="Creator user ID", max_length=255)

    @field_validator("timeout_sec")
    @classmethod
    def validate_timeout_sec(cls, v: int) -> int:
        """Validate timeout_sec is within allowed range."""
        if v < 1:
            raise ValueError("timeout_sec must be at least 1 second")
        if v > 3600:
            raise ValueError("timeout_sec must not exceed 3600 seconds (1 hour)")
        return v

    @field_validator("max_attempts")
    @classmethod
    def validate_max_attempts(cls, v: int) -> int:
        """Validate max_attempts is within allowed range."""
        if v < 1 or v > 10:
            raise ValueError("max_attempts must be between 1 and 10")
        return v


class JobMasterUpdate(BaseModel):
    """Schema for updating a job master."""

    name: str | None = Field(None, description="Master name", max_length=255)
    description: str | None = Field(None, description="Master description")

    # HTTP defaults
    method: str | None = Field(
        None,
        description="HTTP method",
        pattern="^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)$",
    )
    url: HttpUrl | None = Field(None, description="Target URL")
    headers: dict[str, str] | None = Field(None, description="Default headers")
    params: dict[str, Any] | None = Field(None, description="Default query params")
    body: dict[str, Any] | None = Field(None, description="Default request body")
    timeout_sec: int | None = Field(None, ge=1, le=3600)

    # Retry defaults
    max_attempts: int | None = Field(None, ge=1, le=10)
    backoff_strategy: BackoffStrategy | None = Field(None)
    backoff_seconds: float | None = Field(None, ge=0.1)

    # Scheduling defaults
    ttl_seconds: int | None = Field(None, ge=0)
    tags: list[str] | None = Field(None, description="Default tags")

    # Audit
    updated_by: str | None = Field(None, description="Updater user ID", max_length=255)


class JobMasterResponse(BaseModel):
    """Schema for job master creation/update response."""

    master_id: str = Field(..., description="Unique master identifier")
    name: str
    is_active: bool


class JobMasterDetail(BaseModel):
    """Schema for detailed job master information."""

    id: str
    name: str
    description: str | None

    # HTTP defaults
    method: str
    url: str
    headers: dict[str, Any] | None
    params: dict[str, Any] | None
    body: dict[str, Any] | None
    timeout_sec: int

    # Retry defaults
    max_attempts: int
    backoff_strategy: BackoffStrategy
    backoff_seconds: float

    # Scheduling defaults
    ttl_seconds: int | None
    tags: list[str] | None

    # Metadata
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: str | None
    updated_by: str | None

    model_config = {"from_attributes": True}


class JobMasterList(BaseModel):
    """Schema for job master list response."""

    masters: list[JobMasterDetail]
    total: int
    page: int
    size: int
