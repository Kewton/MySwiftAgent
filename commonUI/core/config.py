"""Configuration management for CommonUI Streamlit application."""

import os
from pathlib import Path
from typing import Literal, cast

import streamlit as st
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from .env file
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)


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

    polling_interval: int = Field(default=5, description="Polling interval in seconds")
    default_service: Literal["JobQueue", "MyScheduler", "MyVault"] = Field(
        default="JobQueue", description="Default service to display",
    )
    operation_mode: Literal["full", "readonly"] = Field(
        default="full", description="Operation mode",
    )


class Config:
    """Central configuration manager using environment variables and Streamlit secrets."""

    def __init__(self) -> None:
        """Initialize configuration from environment variables and secrets."""
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from environment and Streamlit secrets."""
        # Try Streamlit secrets first, then environment variables
        self.jobqueue = APIConfig(
            base_url=self._get_setting("JOBQUEUE_BASE_URL", "http://localhost:8001"),
            token=self._get_setting("JOBQUEUE_API_TOKEN", ""),
        )

        self.myscheduler = APIConfig(
            base_url=self._get_setting("MYSCHEDULER_BASE_URL", "http://localhost:8002"),
            token=self._get_setting("MYSCHEDULER_API_TOKEN", ""),
        )

        self.myvault = MyVaultConfig(
            base_url=self._get_setting("MYVAULT_BASE_URL", "http://localhost:8000"),
            service_name=self._get_setting("MYVAULT_SERVICE_NAME", "commonui-service"),
            service_token=self._get_setting("MYVAULT_SERVICE_TOKEN", ""),
        )

        self.expertagent = ExpertAgentConfig(
            base_url=self._get_setting(
                "EXPERTAGENT_BASE_URL", "http://localhost:8103/aiagent-api",
            ),
            admin_token=self._get_setting("EXPERTAGENT_ADMIN_TOKEN", ""),
        )

        self.graphaiserver = GraphAiServerConfig(
            base_url=self._get_setting(
                "GRAPHAISERVER_BASE_URL", "http://localhost:8104/api",
            ),
            admin_token=self._get_setting("GRAPHAISERVER_ADMIN_TOKEN", ""),
        )

        self.ui = UIConfig(
            polling_interval=int(self._get_setting("POLLING_INTERVAL", "5")),
            default_service=cast(
                Literal["JobQueue", "MyScheduler", "MyVault"],
                self._get_setting("DEFAULT_SERVICE", "JobQueue"),
            ),
            operation_mode=cast(
                Literal["full", "readonly"],
                self._get_setting("OPERATION_MODE", "full"),
            ),
        )

    def _get_setting(self, key: str, default: str = "") -> str:
        """Get setting from Streamlit secrets or environment variables."""
        # Try Streamlit secrets first
        try:
            if hasattr(st, "secrets") and key in st.secrets:
                return str(st.secrets[key])
        except Exception:
            pass

        # Fall back to environment variables
        return os.getenv(key, default)

    def get_api_config(
        self, service: str,
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
        raise ValueError(f"Unknown service: {service}")

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
