import uuid
from datetime import datetime, timedelta

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

from ..core.config import settings
from ..core.logging import get_logger
from ..models.execution import Base, JobExecutionORM

logger = get_logger(__name__)


class ExecutionRepository:
    """実行履歴リポジトリ"""

    def __init__(self):
        self.engine = create_engine(settings.database_url)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_execution(
        self,
        job_id: str,
        status: str = "running",
    ) -> str:
        """実行履歴を作成"""
        execution_id = str(uuid.uuid4())

        with self.SessionLocal() as db:
            execution = JobExecutionORM(
                execution_id=execution_id,
                job_id=job_id,
                started_at=datetime.now(),
                status=status,
            )
            db.add(execution)
            db.commit()

        return execution_id

    def update_execution(
        self,
        execution_id: str,
        status: str | None = None,
        result: dict | None = None,
        error_message: str | None = None,
        http_status_code: int | None = None,
        response_size: int | None = None,
    ) -> bool:
        """実行履歴を更新"""
        with self.SessionLocal() as db:
            execution = db.query(JobExecutionORM).filter(
                JobExecutionORM.execution_id == execution_id
            ).first()

            if not execution:
                return False

            if status:
                execution.status = status  # type: ignore
            if status in ["completed", "failed"]:
                execution.completed_at = datetime.now()  # type: ignore
                if execution.started_at:
                    delta = execution.completed_at - execution.started_at
                    execution.execution_time_ms = int(delta.total_seconds() * 1000)  # type: ignore

            if result is not None:
                execution.result = result  # type: ignore
            if error_message is not None:
                execution.error_message = error_message  # type: ignore
            if http_status_code is not None:
                execution.http_status_code = http_status_code  # type: ignore
            if response_size is not None:
                execution.response_size = response_size  # type: ignore

            db.commit()
            return True

    def get_executions_by_job_id(self, job_id: str, limit: int = 50) -> list[dict]:
        """ジョブIDで実行履歴を取得"""
        with self.SessionLocal() as db:
            executions = (
                db.query(JobExecutionORM)
                .filter(JobExecutionORM.job_id == job_id)
                .order_by(desc(JobExecutionORM.started_at))
                .limit(limit)
                .all()
            )

            return [execution.to_dict() for execution in executions]

    def get_recent_executions(self, limit: int = 100) -> list[dict]:
        """最近の実行履歴を取得"""
        with self.SessionLocal() as db:
            executions = (
                db.query(JobExecutionORM)
                .order_by(desc(JobExecutionORM.started_at))
                .limit(limit)
                .all()
            )

            return [execution.to_dict() for execution in executions]

    def get_execution_count_by_job_id(self, job_id: str) -> int:
        """指定されたジョブIDの実行回数を取得"""
        try:
            with self.SessionLocal() as session:
                count = session.query(JobExecutionORM).filter(
                    JobExecutionORM.job_id == job_id
                ).count()
                logger.info(f"Found {count} executions for job {job_id}")
                return count
        except Exception as e:
            logger.error(f"Failed to get execution count for job {job_id}: {e}")
            return 0

    def cleanup_old_executions(self, days: int = 30) -> int:
        """古い実行履歴を削除"""
        cutoff_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        cutoff_date = cutoff_date - timedelta(days=days)

        with self.SessionLocal() as db:
            deleted_count = db.query(JobExecutionORM).filter(
                JobExecutionORM.started_at < cutoff_date
            ).delete()

            db.commit()
            return deleted_count


# グローバル実行履歴リポジトリ
execution_repository = ExecutionRepository()
