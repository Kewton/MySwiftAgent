import uuid
from datetime import datetime

from apscheduler.triggers.cron import CronTrigger  # type: ignore
from apscheduler.triggers.date import DateTrigger  # type: ignore
from apscheduler.triggers.interval import IntervalTrigger  # type: ignore

from ..core.config import settings
from ..core.logging import get_logger
from ..db.session import scheduler_manager
from ..schemas.job import JobCreateRequest, JobInfo, JobResponse
from .job_executor import execute_http_job

logger = get_logger(__name__)


class JobService:
    """ジョブサービス"""

    def __init__(self) -> None:
        self.scheduler = scheduler_manager.get_scheduler()

    def _create_trigger(self, job_request: JobCreateRequest):
        """スケジュール設定からAPSchedulerトリガーを作成"""

        if job_request.schedule_type == "cron":
            if not job_request.cron:
                raise ValueError("cron schedule is required for cron type")

            cron_kwargs = {
                k: v for k, v in job_request.cron.model_dump().items() if v is not None
            }
            return CronTrigger(timezone=settings.tz, **cron_kwargs)

        elif job_request.schedule_type == "interval":
            if not job_request.interval:
                raise ValueError("interval schedule is required for interval type")

            interval_kwargs = {
                k: v
                for k, v in job_request.interval.model_dump().items()
                if v is not None
            }
            return IntervalTrigger(timezone=settings.tz, **interval_kwargs)

        elif job_request.schedule_type == "date":
            if not job_request.run_at:
                raise ValueError("run_at is required for date type")

            run_datetime = datetime.fromisoformat(
                job_request.run_at.replace("Z", "+00:00")
            )
            if run_datetime.tzinfo is None:
                run_datetime = run_datetime.replace(tzinfo=settings.tz)

            return DateTrigger(run_date=run_datetime, timezone=settings.tz)

        else:
            raise ValueError(f"Unknown schedule type: {job_request.schedule_type}")

    async def create_job(self, job_request: JobCreateRequest) -> JobResponse:
        """ジョブを作成"""
        try:
            # ジョブIDの生成
            job_id = job_request.job_id or str(uuid.uuid4())

            # トリガーの作成
            trigger = self._create_trigger(job_request)

            # ジョブの追加
            self.scheduler.add_job(
                func=execute_http_job,
                trigger=trigger,
                id=job_id,
                args=[
                    job_request.target_url,
                    job_request.method,
                    job_request.headers,
                    job_request.body,
                    job_request.timeout_sec,
                    job_request.max_retries,
                    job_request.retry_backoff_sec,
                ],
                replace_existing=job_request.replace_existing,
            )

            logger.info(f"Job {job_id} created successfully")
            return JobResponse(job_id=job_id, status="scheduled")

        except Exception as e:
            logger.error(f"Failed to create job: {str(e)}")
            raise

    async def list_jobs(self) -> list[JobInfo]:
        """ジョブ一覧を取得"""
        try:
            jobs = []
            for job in self.scheduler.get_jobs():
                next_run_time = None
                if hasattr(job, "next_run_time") and job.next_run_time:
                    next_run_time = job.next_run_time.isoformat()

                jobs.append(
                    JobInfo(
                        job_id=job.id,
                        next_run_time=next_run_time,
                        trigger=str(job.trigger),
                    )
                )

            return jobs

        except Exception as e:
            logger.error(f"Failed to list jobs: {str(e)}")
            raise

    async def delete_job(self, job_id: str) -> JobResponse:
        """ジョブを削除"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"Job {job_id} deleted successfully")
            return JobResponse(job_id=job_id, status="deleted")

        except Exception as e:
            logger.error(f"Failed to delete job {job_id}: {str(e)}")
            raise

    async def pause_job(self, job_id: str) -> JobResponse:
        """ジョブを一時停止"""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"Job {job_id} paused successfully")
            return JobResponse(job_id=job_id, status="paused")

        except Exception as e:
            logger.error(f"Failed to pause job {job_id}: {str(e)}")
            raise

    async def resume_job(self, job_id: str) -> JobResponse:
        """ジョブを再開"""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"Job {job_id} resumed successfully")
            return JobResponse(job_id=job_id, status="resumed")

        except Exception as e:
            logger.error(f"Failed to resume job {job_id}: {str(e)}")
            raise


# グローバルジョブサービス
job_service = JobService()
