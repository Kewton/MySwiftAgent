"""Job result Pydantic schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.job import JobStatus


class JobResultResponse(BaseModel):
    """Schema for job result response."""

    job_id: str = Field(..., description="Job identifier")
    status: JobStatus = Field(..., description="Job status")
    attempt: int = Field(1, description="Attempt number")
    response_status: int | None = Field(None, description="HTTP response status code")
    response_headers: dict[str, Any] | None = Field(
        None, description="HTTP response headers"
    )
    response_body: dict[str, Any] | None = Field(None, description="HTTP response body")
    error: str | None = Field(None, description="Error message if failed")
    duration_ms: int | None = Field(
        None, description="Execution duration in milliseconds"
    )

    model_config = {"from_attributes": True}


class JobResultHistoryItem(BaseModel):
    """Schema for a single job result history entry."""

    id: int = Field(..., description="History entry ID")
    job_id: str = Field(..., description="Job identifier")
    attempt: int = Field(..., description="Attempt number")
    response_status: int | None = Field(None, description="HTTP response status code")
    response_headers: dict[str, Any] | None = Field(
        None, description="HTTP response headers"
    )
    response_body: dict[str, Any] | None = Field(None, description="HTTP response body")
    error: str | None = Field(None, description="Error message if failed")
    duration_ms: int | None = Field(
        None, description="Execution duration in milliseconds"
    )
    executed_at: datetime = Field(..., description="Execution timestamp")

    model_config = {"from_attributes": True}


class JobResultHistoryList(BaseModel):
    """Schema for list of job result history entries."""

    job_id: str = Field(..., description="Job identifier")
    total: int = Field(..., description="Total number of history entries")
    items: list[JobResultHistoryItem] = Field(..., description="History entries")

    model_config = {"from_attributes": True}
