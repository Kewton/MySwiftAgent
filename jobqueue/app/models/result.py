"""Job result database models."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class JobResult(Base):
    """Job result database model - stores latest result for each job."""

    __tablename__ = "results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("jobs.id"), unique=True, index=True
    )

    # Attempt number (1, 2, 3, ...)
    attempt: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # HTTP response data
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_headers: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    response_body: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Error information
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Execution metrics
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, onupdate=func.now(), nullable=True
    )

    # Relationship
    job = relationship("Job", backref="result")


class JobResultHistory(Base):
    """Job result history - stores all execution attempts."""

    __tablename__ = "result_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(32), ForeignKey("jobs.id"), index=True)

    # Attempt number (1, 2, 3, ...)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)

    # HTTP response data
    response_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_headers: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    response_body: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    # Error information
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Execution metrics
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Execution timestamp
    executed_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Composite unique constraint on (job_id, attempt)
    __table_args__ = (
        Index("ix_result_history_job_attempt", "job_id", "attempt", unique=True),
    )

    # Relationship
    job = relationship("Job", backref="result_history")
