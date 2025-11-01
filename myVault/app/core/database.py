"""Database configuration and session management."""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

# Create database engine with optimized SQLite settings
engine = create_engine(
    settings.database_url,
    connect_args={
        "check_same_thread": False,
        "timeout": 30,  # 30 second lock timeout for concurrent access
    }
    if "sqlite" in settings.database_url
    else {},
)


# Enable WAL mode for SQLite to support concurrent access in git worktree environment
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Configure SQLite for optimal concurrent access.

    WAL (Write-Ahead Logging) mode benefits:
    - Readers don't block writers and writers don't block readers
    - Multiple processes can safely access the database
    - 2-3x performance improvement for concurrent workloads

    Note: WAL mode requires local filesystem (not NFS).
    This is fine for git worktree parallel development.
    """
    if "sqlite" in settings.database_url:
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")  # Balance safety and performance
        cursor.execute("PRAGMA busy_timeout=30000")  # 30 second busy timeout
        cursor.close()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
