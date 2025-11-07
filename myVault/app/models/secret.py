"""Secret model for storing encrypted secrets."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Secret(Base):
    """Secret model for encrypted data storage."""

    __tablename__ = "secrets"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    project: Mapped[str] = mapped_column(
        String(255), ForeignKey("projects.name"), index=True, nullable=False
    )
    path: Mapped[str] = mapped_column(String(500), index=True, nullable=False)
    encrypted_value: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    encryption_iv: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    encryption_tag: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    updated_by: Mapped[str] = mapped_column(String(100), nullable=False)

    # Relationship to project
    project_rel: Mapped["Project"] = relationship("Project", back_populates="secrets")

    def __repr__(self) -> str:
        """String representation."""
        return f"<Secret(id={self.id}, project={self.project}, path={self.path})>"
