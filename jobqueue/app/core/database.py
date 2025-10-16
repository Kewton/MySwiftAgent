"""Database configuration and management."""

import logging
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


settings = get_settings()

# Create database directory if it doesn't exist
if settings.database_url.startswith("sqlite"):
    db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(
    settings.database_url,
    echo=False,
    future=True,
)

# Enable WAL mode for SQLite
if settings.database_url.startswith("sqlite"):

    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        """Set SQLite pragma for WAL mode and foreign keys."""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    event.listen(engine.sync_engine, "connect", set_sqlite_pragma)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    async with engine.begin() as conn:
        # Import all models to ensure they are registered
        from app.models.job import Job  # noqa: F401
        from app.models.job_master import JobMaster  # noqa: F401
        from app.models.result import JobResult, JobResultHistory  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized")
