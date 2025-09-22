"""Health check schemas."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response schema."""

    message: str
    status: str = "healthy"
    version: str = "0.1.0"