"""JobMasterTask schemas for workflow task associations."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class JobMasterTaskBase(BaseModel):
    """Base schema for JobMasterTask."""

    task_master_id: str = Field(..., description="TaskMaster ID to associate")
    order: int = Field(..., ge=0, description="Execution order (0-based)")
    input_data_template: dict[str, Any] | None = Field(
        None,
        description="Template for generating Task input_data from Job input_data",
    )
    is_required: bool = Field(
        True, description="Whether this task is required for Job success"
    )
    retry_on_failure: bool = Field(
        False, description="Whether to automatically retry failed tasks"
    )


class JobMasterTaskCreate(JobMasterTaskBase):
    """Schema for creating a new JobMasterTask association."""

    pass


class JobMasterTaskUpdate(BaseModel):
    """Schema for updating a JobMasterTask association.

    All fields are optional to support partial updates.
    """

    order: int | None = Field(None, ge=0, description="Execution order (0-based)")
    input_data_template: dict[str, Any] | None = Field(
        None,
        description="Template for generating Task input_data from Job input_data",
    )
    is_required: bool | None = Field(
        None, description="Whether this task is required for Job success"
    )
    retry_on_failure: bool | None = Field(
        None, description="Whether to automatically retry failed tasks"
    )


class JobMasterTaskDetail(JobMasterTaskBase):
    """Schema for JobMasterTask detail response.

    Includes additional fields for display purposes.
    """

    id: str = Field(..., description="JobMasterTask ID")
    job_master_id: str = Field(..., description="JobMaster ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Optional enrichment fields (from joined data)
    task_name: str | None = Field(None, description="TaskMaster name")
    task_description: str | None = Field(None, description="TaskMaster description")

    class Config:
        """Pydantic config."""

        from_attributes = True


class JobMasterTaskList(BaseModel):
    """Schema for paginated JobMasterTask list response."""

    tasks: list[JobMasterTaskDetail] = Field(
        default_factory=list, description="List of workflow tasks"
    )
    total: int = Field(..., description="Total count of tasks in workflow")


class JobMasterTaskResponse(BaseModel):
    """Schema for JobMasterTask operation response."""

    task_master_id: str = Field(..., description="TaskMaster ID")
    order: int = Field(..., description="Execution order")
    job_master_id: str = Field(..., description="JobMaster ID")
