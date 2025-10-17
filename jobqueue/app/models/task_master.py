"""Task master model."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.task import Task
    from app.models.task_master_interface import TaskMasterInterface
    from app.models.task_master_version import TaskMasterVersion


class TaskMaster(Base):
    """Task master definition model."""

    __tablename__ = "task_masters"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    headers: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    body_template: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    timeout_sec: Mapped[int] = mapped_column(Integer, default=30)
    current_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    created_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Relationships
    tasks: Mapped[list["Task"]] = relationship(
        "Task", back_populates="task_master", cascade="all, delete-orphan"
    )
    version_history: Mapped[list["TaskMasterVersion"]] = relationship(
        "TaskMasterVersion", back_populates="task_master", cascade="all, delete-orphan"
    )
    interfaces: Mapped[list["TaskMasterInterface"]] = relationship(
        "TaskMasterInterface",
        back_populates="task_master",
        cascade="all, delete-orphan",
    )
