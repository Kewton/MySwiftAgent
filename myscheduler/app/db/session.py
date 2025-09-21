from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class SchedulerManager:
    """スケジューラー管理クラス"""

    def __init__(self):
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