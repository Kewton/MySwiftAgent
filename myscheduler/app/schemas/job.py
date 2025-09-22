from typing import Any

from pydantic import BaseModel, Field


class CronSchedule(BaseModel):
    """Cronスケジュール設定"""

    year: str | None = None
    month: str | None = None
    day: str | None = None
    week: str | None = None
    day_of_week: str | None = None
    hour: str | None = None
    minute: str | None = None
    second: str | None = "0"


class IntervalSchedule(BaseModel):
    """Intervalスケジュール設定"""

    weeks: int | None = None
    days: int | None = None
    hours: int | None = None
    minutes: int | None = None
    seconds: int | None = None


class JobCreateRequest(BaseModel):
    """ジョブ作成リクエスト"""

    job_id: str | None = None
    schedule_type: str = Field(..., pattern=r"^(cron|interval|date)$")
    target_url: str
    method: str = Field(default="GET", pattern=r"^(GET|POST|PUT|PATCH|DELETE)$")
    headers: dict[str, str] | None = None
    body: dict[str, Any] | None = None
    timeout_sec: float = 30.0
    max_retries: int = 0
    retry_backoff_sec: float = 1.0

    # スケジュール設定
    cron: CronSchedule | None = None
    interval: IntervalSchedule | None = None
    run_at: str | None = None  # ISO 8601 format

    replace_existing: bool = False


class JobResponse(BaseModel):
    """ジョブレスポンス"""

    job_id: str
    status: str


class JobInfo(BaseModel):
    """ジョブ情報"""

    job_id: str
    next_run_time: str | None
    trigger: str


class JobListResponse(BaseModel):
    """ジョブリストレスポンス"""

    jobs: list[JobInfo]


class HealthResponse(BaseModel):
    """ヘルスチェックレスポンス"""

    message: str
    timezone: str
    version: str
