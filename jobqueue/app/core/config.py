"""Application configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # Database
    database_url: str = "sqlite+aiosqlite:///./data/jobqueue.db"

    # Worker
    concurrency: int = 4  # Number of concurrent workers (safe with optimistic locking)
    poll_interval: float = 0.3

    # HTTP
    default_timeout: int = 30
    result_max_bytes: int = 1048576

    # Logging
    log_level: str = "INFO"

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "env_prefix": "JOBQUEUE_",
    }


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
