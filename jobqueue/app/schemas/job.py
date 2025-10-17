"""Job Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.models.job import BackoffStrategy, JobStatus


class JobCreate(BaseModel):
    """Schema for creating a new job."""

    name: str | None = Field(None, description="Job name", max_length=255)
    method: str = Field(
        ...,
        description="HTTP method",
        pattern="^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)$",
    )
    url: HttpUrl = Field(..., description="Target URL")
    headers: dict[str, str] | None = Field(None, description="HTTP headers")
    params: dict[str, Any] | None = Field(None, description="Query parameters")
    body: dict[str, Any] | None = Field(None, description="Request body")
    timeout_sec: int = Field(
        default=30, ge=1, le=3600, description="Timeout in seconds (max: 1 hour)"
    )
    priority: int = Field(
        default=5, ge=1, le=10, description="Priority (1=highest, 10=lowest)"
    )
    max_attempts: int = Field(
        default=1, ge=1, le=10, description="Maximum retry attempts"
    )
    backoff_strategy: BackoffStrategy = Field(
        default=BackoffStrategy.EXPONENTIAL, description="Backoff strategy for retries"
    )
    backoff_seconds: float = Field(
        default=5.0, ge=0.1, description="Base backoff time in seconds"
    )
    scheduled_at: datetime | None = Field(None, description="Schedule execution time")
    ttl_seconds: int | None = Field(
        default=604800, ge=0, description="Time to live in seconds (default: 7 days)"
    )
    tags: list[str] | None = Field(None, description="Job tags")

    @field_validator("timeout_sec")
    @classmethod
    def validate_timeout_sec(cls, v: int) -> int:
        """Validate timeout_sec is within allowed range."""
        if v < 1:
            raise ValueError("timeout_sec must be at least 1 second")
        if v > 3600:
            raise ValueError("timeout_sec must not exceed 3600 seconds (1 hour)")
        return v

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, v: int) -> int:
        """Validate priority is within allowed range."""
        if v < 1 or v > 10:
            raise ValueError("priority must be between 1 (highest) and 10 (lowest)")
        return v

    @field_validator("max_attempts")
    @classmethod
    def validate_max_attempts(cls, v: int) -> int:
        """Validate max_attempts is within allowed range."""
        if v < 1 or v > 10:
            raise ValueError("max_attempts must be between 1 and 10")
        return v


class JobResponse(BaseModel):
    """Schema for job creation response."""

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")


class JobDetail(BaseModel):
    """Schema for detailed job information."""

    id: str
    name: str | None = None
    status: JobStatus
    master_id: str | None = None
    master_version: int | None = Field(None, description="Master version at creation")
    attempt: int
    max_attempts: int
    priority: int
    method: str
    url: str
    headers: dict[str, Any] | None = None
    params: dict[str, Any] | None = None
    body: dict[str, Any] | None = None
    timeout_sec: int
    scheduled_at: datetime | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    tags: list[str] | None = None

    model_config = {"from_attributes": True}


class JobList(BaseModel):
    """Schema for job list response."""

    jobs: list[JobDetail]
    total: int
    page: int
    size: int


class JobTaskCreate(BaseModel):
    """Schema for creating a task within a job."""

    master_id: str = Field(..., description="Task master ID")
    order: int = Field(..., ge=1, description="Execution order")
    input_data: dict[str, Any] | None = Field(
        None, description="Input data for the task"
    )


class JobCreateFromMaster(BaseModel):
    """Schema for creating a job from a master template."""

    name: str | None = Field(None, description="Job name override", max_length=255)

    # Override options (all optional)
    headers: dict[str, str] | None = Field(
        None, description="Additional/override headers"
    )
    params: dict[str, Any] | None = Field(
        None, description="Additional/override query params"
    )
    body: dict[str, Any] | None = Field(
        None, description="Override request body (deep merge)"
    )
    timeout_sec: int | None = Field(None, ge=1, le=3600, description="Timeout override")

    # Scheduling overrides
    priority: int | None = Field(
        None, ge=1, le=10, description="Priority (1=highest, 10=lowest)"
    )
    scheduled_at: datetime | None = Field(None, description="Schedule execution time")

    # Retry overrides
    max_attempts: int | None = Field(
        None, ge=1, le=10, description="Max retry attempts"
    )
    backoff_strategy: BackoffStrategy | None = Field(
        None, description="Backoff strategy for retries"
    )
    backoff_seconds: float | None = Field(None, ge=0.1, description="Backoff time")

    # Additional tags (merged with master tags)
    tags: list[str] | None = Field(None, description="Additional tags")

    # Tasks to create with the job
    tasks: list[JobTaskCreate] | None = Field(
        None, description="Tasks to create with this job"
    )
