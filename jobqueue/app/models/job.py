"""Job database model."""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.task import Task


class JobStatus(str, Enum):
    """Job status enumeration."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class BackoffStrategy(str, Enum):
    """Backoff strategy enumeration."""

    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"


class Job(Base):
    """Job database model."""

    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[JobStatus] = mapped_column(String(20), default=JobStatus.QUEUED)

    # Master reference
    master_id: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    master_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    max_attempts: Mapped[int] = mapped_column(Integer, default=1)
    priority: Mapped[int] = mapped_column(Integer, default=5)

    # HTTP request parameters
    method: Mapped[str] = mapped_column(String(10))
    url: Mapped[str] = mapped_column(Text)
    headers: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    params: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    body: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    timeout_sec: Mapped[int] = mapped_column(Integer, default=30)

    # Retry configuration
    backoff_strategy: Mapped[BackoffStrategy] = mapped_column(
        String(20), default=BackoffStrategy.EXPONENTIAL
    )
    backoff_seconds: Mapped[float] = mapped_column(Float, default=5.0)

    # Scheduling and lifecycle
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ttl_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Relationships
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="job", cascade="all, delete-orphan"
    )
