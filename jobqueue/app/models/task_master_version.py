"""Task master version history model."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.task_master import TaskMaster


class TaskMasterVersion(Base):
    """Task master version history model - stores all versions of task masters."""

    __tablename__ = "task_master_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    master_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("task_masters.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)

    # Complete configuration snapshot
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    headers: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    body_template: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    timeout_sec: Mapped[int] = mapped_column(Integer, nullable=False)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    change_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationship
    task_master: Mapped["TaskMaster"] = relationship(
        "TaskMaster", back_populates="version_history"
    )

    # Composite unique constraint
    __table_args__ = (
        Index(
            "ix_task_master_versions_master_version",
            "master_id",
            "version",
            unique=True,
        ),
    )
