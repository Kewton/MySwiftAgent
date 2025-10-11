"""Pydantic schemas for Project model."""

from datetime import datetime

from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Schema for creating a new project."""

    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    description: str | None = Field(None, max_length=500, description="Project description")


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    description: str | None = Field(None, max_length=500, description="Project description")


class ProjectResponse(BaseModel):
    """Schema for project response."""

    id: int
    name: str
    description: str | None
    is_default: bool
    created_at: datetime
    created_by: str

    model_config = {"from_attributes": True}
