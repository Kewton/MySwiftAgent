"""Job result Pydantic schemas."""

from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.job import JobStatus


class JobResultResponse(BaseModel):
    """Schema for job result response."""

    job_id: str = Field(..., description="Job identifier")
    status: JobStatus = Field(..., description="Job status")
    response_status: Optional[int] = Field(None, description="HTTP response status code")
    response_headers: Optional[dict[str, Any]] = Field(None, description="HTTP response headers")
    response_body: Optional[dict[str, Any]] = Field(None, description="HTTP response body")
    error: Optional[str] = Field(None, description="Error message if failed")
    duration_ms: Optional[int] = Field(None, description="Execution duration in milliseconds")

    model_config = {"from_attributes": True}
