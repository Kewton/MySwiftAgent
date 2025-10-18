"""Interface master model."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.job_master_interface import JobMasterInterface
    from app.models.task_master_interface import TaskMasterInterface


class InterfaceMaster(Base):
    """Interface master model for input/output type definitions."""

    __tablename__ = "interface_masters"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_schema: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="JSON Schema V7 for input validation"
    )
    output_schema: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="JSON Schema V7 for output validation"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    job_master_interfaces: Mapped[list["JobMasterInterface"]] = relationship(
        "JobMasterInterface",
        back_populates="interface_master",
        cascade="all, delete-orphan",
    )
    task_master_interfaces: Mapped[list["TaskMasterInterface"]] = relationship(
        "TaskMasterInterface",
        back_populates="interface_master",
        cascade="all, delete-orphan",
    )
