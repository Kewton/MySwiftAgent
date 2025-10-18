"""Job master version history database models."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class JobMasterVersion(Base):
    """Job master version history model - stores all versions of job masters."""

    __tablename__ = "job_master_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    master_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("job_masters.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    # Master configuration snapshot (all fields)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    headers: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    params: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    body: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    timeout_sec: Mapped[int] = mapped_column(Integer, nullable=False)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    backoff_strategy: Mapped[str] = mapped_column(String(20), nullable=False)
    backoff_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    ttl_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Composite unique constraint on (master_id, version)
    __table_args__ = (
        Index(
            "ix_job_master_versions_master_version", "master_id", "version", unique=True
        ),
    )

    # Relationship
    job_master = relationship("JobMaster", back_populates="version_history")
