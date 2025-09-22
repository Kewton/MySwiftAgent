from datetime import datetime
from typing import Any

from apscheduler.triggers.base import BaseTrigger  # type: ignore
from pydantic import BaseModel


class JobConfig(BaseModel):
    """ジョブ設定モデル"""

    job_id: str
    target_url: str
    method: str
    headers: dict[str, str] | None = None
    body: dict[str, Any] | None = None
    timeout_sec: float = 30.0
    max_retries: int = 0
    retry_backoff_sec: float = 1.0
    replace_existing: bool = False


class JobState(BaseModel):
    """ジョブ状態モデル"""

    job_id: str
    next_run_time: datetime | None
    trigger: BaseTrigger
    is_paused: bool = False

    class Config:
        arbitrary_types_allowed = True
