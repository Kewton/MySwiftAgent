import uuid
from datetime import datetime

from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ..core.config import settings
from ..core.logging import get_logger
from ..db.session import scheduler_manager
from ..repositories.execution_repository import execution_repository
from ..schemas.job import JobCreateRequest, JobDetail, JobInfo, JobResponse
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
            
            # ジョブ名の設定（指定されていない場合はジョブIDを使用）
            job_name = job_request.name or job_id

            # トリガーの作成
            trigger = self._create_trigger(job_request)

            # ジョブの追加（job_idを最後の引数として追加）
            self.scheduler.add_job(
                func=execute_http_job,
                trigger=trigger,
                id=job_id,
                name=job_name,  # APSchedulerのname属性を使用
                args=[
                    job_request.target_url,
                    job_request.method,
                    job_request.headers,
                    job_request.body,
                    job_request.timeout_sec,
                    job_request.max_retries,
                    job_request.retry_backoff_sec,
                    job_id,  # 実行履歴記録用のjob_id
                ],
                replace_existing=job_request.replace_existing,
            )

            logger.info(f"Job {job_id} (name: {job_name}) created successfully")
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

                # ジョブステータスの判定
                status = "running"
                if not hasattr(job, "next_run_time") or job.next_run_time is None:
                    status = "paused"

                # ジョブの引数からHTTP設定を取得 (execute_http_job用)
                target_url = None
                method = None
                if job.args and len(job.args) >= 2:
                    target_url = job.args[0]
                    method = job.args[1]

                # ジョブ名を取得（APSchedulerのname属性またはjob_idをフォールバック）
                job_name = getattr(job, 'name', job.id)

                # データベースから実際の実行回数を取得
                execution_count = execution_repository.get_execution_count_by_job_id(job.id)

                jobs.append(
                    JobInfo(
                        job_id=job.id,
                        id=job.id,  # CommonUI互換性のため追加
                        name=job_name,  # APSchedulerのname属性を使用
                        next_run_time=next_run_time,
                        trigger=str(job.trigger),
                        status=status,
                        target_url=target_url,
                        method=method,
                        execution_count=execution_count,  # データベースから取得した実行回数
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

    async def trigger_job(self, job_id: str) -> JobResponse:
        """ジョブを即座に実行"""
        try:
            # ジョブが存在するかチェック
            job = self.scheduler.get_job(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            # ジョブを即座に実行（既存のスケジュールを維持）
            from datetime import datetime
            self.scheduler.modify_job(job_id, next_run_time=datetime.now())
            logger.info(f"Job {job_id} triggered successfully")
            return JobResponse(job_id=job_id, status="triggered")

        except Exception as e:
            logger.error(f"Failed to trigger job {job_id}: {str(e)}")
            raise

    async def get_job(self, job_id: str) -> JobDetail:
        """ジョブ詳細を取得"""
        try:
            job = self.scheduler.get_job(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            # ジョブの状態を判定
            status = "running"
            try:
                # ジョブが一時停止されているかチェック
                if hasattr(job, 'paused') and job.paused:
                    status = "paused"
                elif job.next_run_time is None:
                    status = "completed"
            except Exception:
                # APSchedulerの仕様によって属性が異なる場合があるためエラーハンドリング
                pass

            # 次回実行時刻の取得
            next_run_time = None
            if hasattr(job, "next_run_time") and job.next_run_time:
                next_run_time = job.next_run_time.isoformat()

            # トリガー情報の取得
            trigger_info = {}
            trigger_type = str(job.trigger.__class__.__name__).lower()
            if "cron" in trigger_type:
                trigger_info["type"] = "cron"
                if hasattr(job.trigger, 'fields'):
                    cron_fields = {}
                    for field in ['year', 'month', 'day', 'week', 'day_of_week', 'hour', 'minute', 'second']:
                        if hasattr(job.trigger.fields, field):
                            field_obj = getattr(job.trigger.fields, field)
                            cron_fields[field] = str(field_obj)
                    trigger_info["cron"] = cron_fields
            elif "interval" in trigger_type:
                trigger_info["type"] = "interval"
                if hasattr(job.trigger, 'interval'):
                    interval_seconds = job.trigger.interval.total_seconds()
                    trigger_info["interval_seconds"] = interval_seconds
            elif "date" in trigger_type:
                trigger_info["type"] = "date"
                if hasattr(job.trigger, 'run_date'):
                    trigger_info["run_date"] = job.trigger.run_date.isoformat()

            # ジョブの引数からHTTP設定を取得 (execute_http_job用)
            target_url = None
            method = None
            headers = None
            body = None
            timeout_sec = None
            max_retries = None
            retry_backoff_sec = None

            if job.args and len(job.args) >= 2:
                target_url = job.args[0]
                method = job.args[1]
                if len(job.args) > 2:
                    headers = job.args[2]
                if len(job.args) > 3:
                    body = job.args[3]
                if len(job.args) > 4:
                    timeout_sec = job.args[4]
                if len(job.args) > 5:
                    max_retries = job.args[5]
                if len(job.args) > 6:
                    retry_backoff_sec = job.args[6]
                # job.args[7] is job_id for execution history tracking

            # 実行履歴を取得
            executions = []
            try:
                executions = execution_repository.get_executions_by_job_id(job.id, limit=50)
            except Exception as e:
                logger.warning(f"Failed to get execution history for job {job.id}: {e}")

            # ジョブ名を取得（APSchedulerのname属性またはjob_idをフォールバック）
            job_name = getattr(job, 'name', job.id)

            # データベースから実際の実行回数を取得
            execution_count = execution_repository.get_execution_count_by_job_id(job.id)

            return JobDetail(
                job_id=job.id,
                name=job_name,  # APSchedulerのname属性を使用
                func=str(job.func.__name__ if hasattr(job, 'func') and job.func else 'execute_http_job'),
                status=status,
                trigger=str(job.trigger),
                next_run_time=next_run_time,
                execution_count=execution_count,  # データベースから取得した実行回数
                trigger_info=trigger_info,
                target_url=target_url,
                method=method,
                headers=headers,
                body=body,
                timeout_sec=timeout_sec,
                max_retries=max_retries,
                retry_backoff_sec=retry_backoff_sec,
                executions=executions,  # 実行履歴を追加
            )

        except ValueError:
            # ジョブが見つからない場合は再発生させる
            raise
        except Exception as e:
            logger.error(f"Failed to get job {job_id}: {str(e)}")
            raise


# グローバルジョブサービス
job_service = JobService()
