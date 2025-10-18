"""JobMasterTask model for workflow task associations."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.job_master import JobMaster
    from app.models.task_master import TaskMaster


class JobMasterTask(Base):
    """JobMasterTask model - associates TaskMasters with JobMasters to define workflows.

    This table stores the configuration of tasks within a workflow, including:
    - Which TaskMasters are part of which JobMasters
    - Execution order of tasks
    - Input data templates for dynamic task configuration
    - Retry and required flags

    Example:
        A "Company Research Workflow" JobMaster might have:
        1. company_search (order=0, required=True)
        2. company_analysis (order=1, required=True)
        3. report_generation (order=2, required=False)
    """

    __tablename__ = "job_master_tasks"
    __table_args__ = (
        UniqueConstraint("job_master_id", "order", name="uq_job_master_order"),
        UniqueConstraint("job_master_id", "task_master_id", name="uq_job_master_task"),
    )

    # Primary identifier
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)

    # Foreign keys
    job_master_id: Mapped[str] = mapped_column(
        String, ForeignKey("job_masters.id", ondelete="CASCADE"), index=True
    )
    task_master_id: Mapped[str] = mapped_column(
        String, ForeignKey("task_masters.id"), index=True
    )

    # Task configuration
    order: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Execution order within the workflow (0-based)"
    )
    input_data_template: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Template for generating Task input_data from Job input_data",
    )
    is_required: Mapped[bool] = mapped_column(
        Boolean, default=True, comment="Whether this task is required for Job success"
    )
    retry_on_failure: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Whether to automatically retry failed tasks",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    job_master: Mapped["JobMaster"] = relationship(
        "JobMaster", back_populates="task_associations"
    )
    task_master: Mapped["TaskMaster"] = relationship(
        "TaskMaster", back_populates="job_associations"
    )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<JobMasterTask(id={self.id}, "
            f"job_master_id={self.job_master_id}, "
            f"task_master_id={self.task_master_id}, "
            f"order={self.order})>"
        )
