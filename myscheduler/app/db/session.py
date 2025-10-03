from pathlib import Path

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.engine import make_url

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


def _ensure_sqlite_directory(database_url: str) -> None:
    """Ensure the directory for a SQLite database exists."""

    try:
        url = make_url(database_url)
    except Exception:  # pragma: no cover - misconfiguration guard
        logger.warning("Failed to parse database URL '%s'", database_url)
        return

    if not url.drivername.startswith("sqlite"):
        return

    database = url.database
    if not database:
        return

    path = Path(database)
    if not path.is_absolute():
        path = Path.cwd() / path

    path.parent.mkdir(parents=True, exist_ok=True)


class SchedulerManager:
    """スケジューラー管理クラス"""

    def __init__(self) -> None:
        _ensure_sqlite_directory(settings.database_url)
        self.jobstore = SQLAlchemyJobStore(url=settings.database_url)
        self.scheduler = AsyncIOScheduler(
            jobstores={"default": self.jobstore},
            timezone=settings.tz,
            job_defaults=settings.scheduler_config,
        )

    def start(self) -> None:
        """スケジューラーを開始"""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    def shutdown(self) -> None:
        """スケジューラーを停止"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")

    def get_scheduler(self) -> AsyncIOScheduler:
        """スケジューラーインスタンスを取得"""
        return self.scheduler


# グローバルスケジューラーマネージャー
scheduler_manager = SchedulerManager()
