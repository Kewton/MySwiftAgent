from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Load environment variables from myscheduler/.env (new policy)
# Note: override=False respects existing environment variables set by quick-start.sh or docker-compose
PROJECT_ROOT = Path(__file__).parent.parent.parent
env_path = PROJECT_ROOT / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=False)
else:
    # Fallback to auto-detection (for docker-compose where env vars are pre-set)
    load_dotenv(override=False)


class Settings(BaseSettings):
    """アプリケーション設定"""

    # アプリケーション
    app_name: str = "MyScheduler API"
    app_version: str = "1.0.0"
    debug: bool = False

    # データベース
    database_url: str = "sqlite:///./data/jobs.db"

    # スケジューラー
    timezone: str = "Asia/Tokyo"
    job_max_instances: int = 1
    job_coalesce: bool = True
    job_misfire_grace_time: int = 30

    # HTTP
    http_timeout: float = 30.0
    max_retries: int = 3
    retry_backoff: float = 1.0

    # サーバー
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1

    # ログ
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_dir: str = "./"

    @property
    def tz(self) -> ZoneInfo:
        """タイムゾーンオブジェクトを返す"""
        return ZoneInfo(self.timezone)

    @property
    def scheduler_config(self) -> dict[str, Any]:
        """APScheduler設定を返す"""
        return {
            "coalesce": self.job_coalesce,
            "max_instances": self.job_max_instances,
            "misfire_grace_time": self.job_misfire_grace_time,
        }


# グローバル設定インスタンス
settings = Settings()
