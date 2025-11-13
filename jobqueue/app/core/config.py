"""Application configuration."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Calculate path to jobqueue/.env
PROJECT_ROOT = Path(__file__).parent.parent.parent
env_path = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=str(env_path) if env_path.exists() else None,
        env_file_encoding='utf-8',
        case_sensitive=False,
        extra='ignore'
    )

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


# Singleton instance - created once on first import
_settings_instance: Settings | None = None


def get_settings() -> Settings:
    """Get settings instance."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
