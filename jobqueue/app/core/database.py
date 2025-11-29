"""Database configuration and management."""

import logging
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import env_path, get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# Lazy initialization to ensure .env is loaded before creating engine
_engine = None
_session_maker = None


def _init_engine() -> None:
    """Initialize database engine and session maker (lazy initialization)."""
    global _engine, _session_maker

    if _engine is not None:
        return

    settings = get_settings()

    # Debug logging
    logger.info("[DATABASE] Loading database configuration...")
    logger.info(f"[DATABASE] DATABASE_URL from settings: {settings.database_url}")
    logger.info(
        f"[DATABASE] Config file path: {env_path if env_path.exists() else 'N/A'}"
    )

    # Create database directory if it doesn't exist
    if settings.database_url.startswith("sqlite"):
        db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    _engine = create_async_engine(
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

        event.listen(_engine.sync_engine, "connect", set_sqlite_pragma)

    _session_maker = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    logger.info(f"Database engine initialized with URL: {settings.database_url}")


def get_engine() -> Any:
    """Get database engine (creates it if not initialized)."""
    _init_engine()
    return _engine


def get_session_maker() -> Any:
    """Get session maker (creates it if not initialized)."""
    _init_engine()
    return _session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session.

    Note: This function yields a session without auto-commit/rollback.
    Endpoints must explicitly call await session.commit() to persist changes.
    If an exception occurs, the session will be rolled back automatically.
    """
    session_maker = get_session_maker()
    session = session_maker()
    try:
        yield session
    except Exception:
        # Rollback on exception
        await session.rollback()
        raise
    finally:
        # Close session (this does NOT rollback committed transactions)
        await session.close()


async def init_db() -> None:
    """Initialize database tables."""
    engine = get_engine()
    async with engine.begin() as conn:
        # Import all models to ensure they are registered
        from app.models.interface_master import InterfaceMaster  # noqa: F401
        from app.models.job import Job  # noqa: F401
        from app.models.job_master import JobMaster  # noqa: F401
        from app.models.job_master_interface import JobMasterInterface  # noqa: F401
        from app.models.job_master_version import JobMasterVersion  # noqa: F401
        from app.models.result import JobResult, JobResultHistory  # noqa: F401
        from app.models.task import Task  # noqa: F401
        from app.models.task_master import TaskMaster  # noqa: F401
        from app.models.task_master_interface import TaskMasterInterface  # noqa: F401
        from app.models.task_master_version import TaskMasterVersion  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database initialized")
