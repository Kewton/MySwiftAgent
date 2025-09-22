"""Job result Pydantic schemas."""

from typing import Any

from pydantic import BaseModel, Field

from app.models.job import JobStatus


class JobResultResponse(BaseModel):
    """Schema for job result response."""

    job_id: str = Field(..., description="Job identifier")
    status: JobStatus = Field(..., description="Job status")
    response_status: int | None = Field(None, description="HTTP response status code")
    response_headers: dict[str, Any] | None = Field(None, description="HTTP response headers")
    response_body: dict[str, Any] | None = Field(None, description="HTTP response body")
    error: str | None = Field(None, description="Error message if failed")
    duration_ms: int | None = Field(None, description="Execution duration in milliseconds")

    model_config = {"from_attributes": True}
