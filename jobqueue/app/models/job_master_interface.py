"""Job master interface association model."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.interface_master import InterfaceMaster
    from app.models.job_master import JobMaster


class JobMasterInterface(Base):
    """Job master to interface master association model."""

    __tablename__ = "job_master_interfaces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_master_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("job_masters.id", ondelete="CASCADE"), index=True
    )
    interface_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("interface_masters.id"), index=True
    )
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    job_master: Mapped["JobMaster"] = relationship(
        "JobMaster", back_populates="interfaces"
    )
    interface_master: Mapped["InterfaceMaster"] = relationship(
        "InterfaceMaster", back_populates="job_master_interfaces"
    )

    # Composite unique constraint
    __table_args__ = (
        Index(
            "ix_job_master_interface_unique",
            "job_master_id",
            "interface_id",
            unique=True,
        ),
    )
