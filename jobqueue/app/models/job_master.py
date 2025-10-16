"""Job Master database model."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.job import BackoffStrategy


class JobMaster(Base):
    """Job master template model."""

    __tablename__ = "job_masters"

    # Primary key
    id: Mapped[str] = mapped_column(String(32), primary_key=True)

    # Basic info
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # HTTP request defaults
    method: Mapped[str] = mapped_column(String(10))
    url: Mapped[str] = mapped_column(Text)
    headers: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    params: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    body: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    timeout_sec: Mapped[int] = mapped_column(Integer, default=30)

    # Retry defaults
    max_attempts: Mapped[int] = mapped_column(Integer, default=1)
    backoff_strategy: Mapped[BackoffStrategy] = mapped_column(
        String(20), default=BackoffStrategy.EXPONENTIAL
    )
    backoff_seconds: Mapped[float] = mapped_column(Float, default=5.0)

    # Scheduling defaults
    ttl_seconds: Mapped[int | None] = mapped_column(Integer, default=604800)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Version management
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Metadata
    is_active: Mapped[bool] = mapped_column(Integer, default=1)  # SQLite用
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Audit
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    version_history = relationship(
        "JobMasterVersion", back_populates="job_master", cascade="all, delete-orphan"
    )
