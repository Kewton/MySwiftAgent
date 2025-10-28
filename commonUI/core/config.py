"""Configuration management for the CommonUI Streamlit application."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal, cast

try:  # pragma: no cover - optional dependency during testing
    import streamlit as st  # type: ignore[import-not-found]
except ModuleNotFoundError:
    # pragma: no cover - fallback when Streamlit absent
    st = None  # type: ignore[assignment]
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class SettingsProvider:
    """Retrieve configuration values from secrets and environment variables."""

    _env_loaded: bool = False

    def __init__(self, env_path: Path | None = None) -> None:
        self.env_path = env_path or Path(__file__).parent.parent / ".env"
        self._ensure_env_loaded()

    def _ensure_env_loaded(self) -> None:
        if SettingsProvider._env_loaded:
            return

        if self.env_path.exists():
            load_dotenv(self.env_path, override=True)
        else:
            load_dotenv(override=False)

        SettingsProvider._env_loaded = True

    def get(self, key: str, default: str = "") -> str:
        """Fetch configuration value from Streamlit secrets or environment."""

        try:
            if st is not None and hasattr(st, "secrets") and key in st.secrets:
                return str(st.secrets[key])
        except Exception:  # pragma: no cover - defensive
            pass

        return os.getenv(key, default)

    def reload(self) -> None:
        """Reload environment variables from disk."""

        SettingsProvider._env_loaded = False
        self._ensure_env_loaded()


class APIConfig(BaseModel):
    """API configuration for external services."""

    base_url: str = Field(description="Base URL for the API")
    token: str = Field(description="API authentication token")


class MyVaultConfig(BaseModel):
    """MyVault API configuration with custom authentication."""

    base_url: str = Field(description="Base URL for MyVault API")
    service_name: str = Field(description="Service name for authentication")
    service_token: str = Field(description="Service token for authentication")


class ExpertAgentConfig(BaseModel):
    """ExpertAgent API configuration with admin token."""

    base_url: str = Field(description="Base URL for ExpertAgent API")
    admin_token: str = Field(description="Admin token for cache management")


class GraphAiServerConfig(BaseModel):
    """GraphAiServer API configuration with admin token."""

    base_url: str = Field(description="Base URL for GraphAiServer API")
    admin_token: str = Field(description="Admin token for cache management")


class UIConfig(BaseModel):
    """UI configuration settings."""

    polling_interval: int = Field(
        default=5,
        description="Polling interval in seconds",
    )
    default_service: Literal["JobQueue", "MyScheduler", "MyVault"] = Field(
        default="JobQueue",
        description="Default service to display",
    )
    operation_mode: Literal["full", "readonly"] = Field(
        default="full",
        description="Operation mode",
    )


class Config:
    """Central configuration manager for CommonUI services and endpoints."""

    def __init__(self, provider: SettingsProvider | None = None) -> None:
        """Initialize configuration from environment variables and secrets."""
        self._provider = provider or SettingsProvider()
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from environment and Streamlit secrets."""
        provider = self._provider
        default_log_dir = Path(__file__).resolve().parents[2] / "logs"
        self.log_dir = provider.get("LOG_DIR", str(default_log_dir))
        self.log_level = provider.get("LOG_LEVEL", "INFO")

        self.jobqueue = APIConfig(
            base_url=provider.get(
                "JOBQUEUE_BASE_URL",
                "http://localhost:8101",
            ),
            token=provider.get("JOBQUEUE_API_TOKEN", ""),
        )

        self.myscheduler = APIConfig(
            base_url=provider.get(
                "MYSCHEDULER_BASE_URL",
                "http://localhost:8102",
            ),
            token=provider.get("MYSCHEDULER_API_TOKEN", ""),
        )

        self.myvault = MyVaultConfig(
            base_url=provider.get("MYVAULT_BASE_URL", "http://localhost:8103"),
            service_name=provider.get("MYVAULT_SERVICE_NAME", "commonui"),
            service_token=provider.get("MYVAULT_SERVICE_TOKEN", ""),
        )

        self.expertagent = ExpertAgentConfig(
            base_url=provider.get(
                "EXPERTAGENT_BASE_URL",
                "http://localhost:8104/aiagent-api",
            ),
            admin_token=provider.get("EXPERTAGENT_ADMIN_TOKEN", ""),
        )

        self.graphaiserver = GraphAiServerConfig(
            base_url=provider.get(
                "GRAPHAISERVER_BASE_URL",
                "http://localhost:8105/api",
            ),
            admin_token=provider.get("GRAPHAISERVER_ADMIN_TOKEN", ""),
        )

        self.ui = UIConfig(
            polling_interval=int(provider.get("POLLING_INTERVAL", "5")),
            default_service=cast(
                "Literal['JobQueue', 'MyScheduler', 'MyVault']",
                provider.get("DEFAULT_SERVICE", "JobQueue"),
            ),
            operation_mode=cast(
                "Literal['full', 'readonly']",
                provider.get("OPERATION_MODE", "full"),
            ),
        )

    def reload(self) -> None:
        """Reload configuration values from the underlying provider."""

        self._provider.reload()
        self._load_config()

    def get_api_config(
        self,
        service: str,
    ) -> APIConfig | MyVaultConfig | ExpertAgentConfig | GraphAiServerConfig:
        """Get API configuration for specified service."""
        if service.lower() == "jobqueue":
            return self.jobqueue
        if service.lower() == "myscheduler":
            return self.myscheduler
        if service.lower() == "myvault":
            return self.myvault
        if service.lower() == "expertagent":
            return self.expertagent
        if service.lower() == "graphaiserver":
            return self.graphaiserver
        msg = f"Unknown service: {service}"
        raise ValueError(msg)

    def is_service_configured(self, service: str) -> bool:
        """Check if service is properly configured."""
        try:
            api_config = self.get_api_config(service)
            # For development, only require base_url
            # Token can be empty for services that don't require authentication
            return bool(api_config.base_url)
        except ValueError:
            return False

    def mask_token(self, token: str) -> str:
        """Mask API token for secure logging."""
        if not token:
            return "***EMPTY***"
        if len(token) <= 8:
            return "***"
        return f"{token[:4]}***{token[-4:]}"


# Global configuration instance
config = Config()
