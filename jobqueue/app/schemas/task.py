"""Task schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TaskBase(BaseModel):
    """Base task schema."""

    master_id: str = Field(..., description="Task master ID")
    order: int = Field(..., ge=1, description="Execution order")
    input_data: dict[str, Any] | None = Field(None, description="Input data")


class TaskCreate(TaskBase):
    """Task creation schema."""

    pass


class TaskDetail(BaseModel):
    """Task detail response schema."""

    id: str
    job_id: str
    master_id: str
    master_version: int | None
    order: int
    status: str
    input_data: dict[str, Any] | None
    output_data: dict[str, Any] | None
    attempt: int
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskList(BaseModel):
    """Task list response schema."""

    job_id: str
    tasks: list[TaskDetail]
    total: int


class TaskRetryResponse(BaseModel):
    """Task retry response schema."""

    task_id: str
    status: str
    message: str


class TaskListAll(BaseModel):
    """Task list response schema for all tasks with pagination."""

    tasks: list[TaskDetail]
    total: int
    page: int
    size: int


class TaskStats(BaseModel):
    """Task execution statistics schema."""

    total_tasks: int
    queued_tasks: int
    running_tasks: int
    succeeded_tasks: int
    failed_tasks: int
    skipped_tasks: int
    success_rate: float = Field(..., description="Success rate as percentage")
    average_duration_ms: float | None = Field(
        None, description="Average execution duration in milliseconds"
    )
