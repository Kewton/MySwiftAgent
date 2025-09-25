"""Configuration management for CommonUI Streamlit application."""

import os
from typing import Literal

import streamlit as st
from pydantic import BaseModel, Field


class APIConfig(BaseModel):
    """API configuration for external services."""

    base_url: str = Field(..., description="Base URL for the API")
    token: str = Field(..., description="API authentication token")


class UIConfig(BaseModel):
    """UI configuration settings."""

    polling_interval: int = Field(default=5, description="Polling interval in seconds")
    default_service: Literal["JobQueue", "MyScheduler"] = Field(
        default="JobQueue", description="Default service to display"
    )
    operation_mode: Literal["full", "readonly"] = Field(
        default="full", description="Operation mode"
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
            token=self._get_setting("JOBQUEUE_API_TOKEN", "")
        )

        self.myscheduler = APIConfig(
            base_url=self._get_setting("MYSCHEDULER_BASE_URL", "http://localhost:8002"),
            token=self._get_setting("MYSCHEDULER_API_TOKEN", "")
        )

        self.ui = UIConfig(
            polling_interval=int(self._get_setting("POLLING_INTERVAL", "5")),
            default_service=self._get_setting("DEFAULT_SERVICE", "JobQueue"),
            operation_mode=self._get_setting("OPERATION_MODE", "full")
        )

    def _get_setting(self, key: str, default: str = "") -> str:
        """Get setting from Streamlit secrets or environment variables."""
        # Try Streamlit secrets first
        try:
            if hasattr(st, 'secrets') and key in st.secrets:
                return st.secrets[key]
        except Exception:
            pass

        # Fall back to environment variables
        return os.getenv(key, default)

    def get_api_config(self, service: str) -> APIConfig:
        """Get API configuration for specified service."""
        if service.lower() == "jobqueue":
            return self.jobqueue
        elif service.lower() == "myscheduler":
            return self.myscheduler
        else:
            raise ValueError(f"Unknown service: {service}")

    def is_service_configured(self, service: str) -> bool:
        """Check if service is properly configured."""
        try:
            api_config = self.get_api_config(service)
            return bool(api_config.base_url and api_config.token)
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