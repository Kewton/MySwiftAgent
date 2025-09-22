"""Job result database model."""

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base


class JobResult(Base):
    """Job result database model."""

    __tablename__ = "results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("jobs.id"), unique=True, index=True
    )

    # HTTP response data
    response_status: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    response_headers: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSON, nullable=True
    )
    response_body: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Error information
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Execution metrics
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, onupdate=func.now(), nullable=True
    )

    # Relationship
    job = relationship("Job", backref="result")
