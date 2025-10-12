"""Application configuration."""

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load environment variables from jobqueue/.env (new policy)
# Note: override=False respects existing environment variables set by quick-start.sh or docker-compose
PROJECT_ROOT = Path(__file__).parent.parent.parent
env_path = PROJECT_ROOT / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=False)
else:
    # Fallback to auto-detection (for docker-compose where env vars are pre-set)
    load_dotenv(override=False)


class Settings(BaseSettings):
    """Application settings."""

    # Database
    database_url: str = Field(default="sqlite+aiosqlite:///./data/jobqueue.db")

    # Worker
    concurrency: int = Field(
        default=4
    )  # Number of concurrent workers (safe with optimistic locking)
    poll_interval: float = Field(default=0.3)

    # HTTP
    default_timeout: int = Field(default=30)
    result_max_bytes: int = Field(default=1048576)

    # Logging
    LOG_LEVEL: str = Field(default="INFO")
    LOG_DIR: str = Field(default="./")


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
