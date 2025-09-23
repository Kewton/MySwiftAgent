"""Job Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl

from app.models.job import BackoffStrategy, JobStatus


class JobCreate(BaseModel):
    """Schema for creating a new job."""

    method: str = Field(..., description="HTTP method", pattern="^(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)$")
    url: HttpUrl = Field(..., description="Target URL")
    headers: dict[str, str] | None = Field(None, description="HTTP headers")
    params: dict[str, Any] | None = Field(None, description="Query parameters")
    body: dict[str, Any] | None = Field(None, description="Request body")
    timeout_sec: int = Field(default=30, ge=1, le=300, description="Timeout in seconds")
    priority: int = Field(default=5, ge=1, le=10, description="Priority (1=highest, 10=lowest)")
    max_attempts: int = Field(default=1, ge=1, le=10, description="Maximum retry attempts")
    backoff_strategy: BackoffStrategy = Field(
        default=BackoffStrategy.EXPONENTIAL, description="Backoff strategy for retries"
    )
    backoff_seconds: float = Field(default=5.0, ge=0.1, description="Base backoff time in seconds")
    scheduled_at: datetime | None = Field(None, description="Schedule execution time")
    ttl_seconds: int | None = Field(
        default=604800, ge=0, description="Time to live in seconds (default: 7 days)"
    )
    tags: list[str] | None = Field(None, description="Job tags")


class JobResponse(BaseModel):
    """Schema for job creation response."""

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")


class JobDetail(BaseModel):
    """Schema for detailed job information."""

    id: str
    status: JobStatus
    attempt: int
    max_attempts: int
    priority: int
    method: str
    url: str
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
