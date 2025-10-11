"""Configuration management for myVault."""

import base64
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables from myVault/.env (new policy)
# Note: override=False respects existing environment variables set by quick-start.sh or docker-compose
PROJECT_ROOT = Path(__file__).parent.parent.parent
env_path = PROJECT_ROOT / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=False)
else:
    # Fallback to auto-detection (for docker-compose where env vars are pre-set)
    load_dotenv(override=False)


def load_config_yaml() -> dict[str, Any]:
    """Load configuration from config.yaml file."""
    config_path = Path(__file__).parent.parent.parent / "config.yaml"

    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found: {config_path}\n"
            "Please create config.yaml based on config.yaml.example"
        )

    with open(config_path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    if not config:
        raise ValueError("Configuration file is empty")

    return config


class Settings(BaseSettings):
    """Application settings loaded from YAML config and environment variables.

    YAML file (config.yaml) contains:
    - Application settings (title, version, port, etc.)
    - Service definitions and access policies
    - Audit configuration
    - CORS settings

    Environment variables contain sensitive data:
    - MSA_MASTER_KEY: Master encryption key (base64:...)
    - TOKEN_<service-name>: Service authentication tokens
    - DATABASE_URL (optional): Override database URL from config.yaml
    """

    model_config = SettingsConfigDict(extra="allow")

    # Master encryption key (Base64-encoded 32 bytes) - MUST be in environment
    msa_master_key: str = Field(
        default="",
        description="Master key for AES-256-GCM encryption (base64:...)",
    )

    # Database configuration (can be overridden by DATABASE_URL env var)
    database_url: str | None = Field(
        default=None,
        description="Database connection URL (overrides config.yaml if set)",
    )

    # Logging configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_dir: str = Field(default="./", description="Log directory path")

    def __init__(self, **kwargs: Any) -> None:
        """Initialize settings and load YAML configuration."""
        super().__init__(**kwargs)
        self._yaml_config = load_config_yaml()

        # Override database_url from YAML if not set in environment
        if not self.database_url:
            self.database_url = self._yaml_config.get("database", {}).get(
                "url", "sqlite:///./data/myvault.db"
            )

    @field_validator("msa_master_key")
    @classmethod
    def validate_master_key(cls, v: str) -> str:
        """Validate that master key is properly formatted and decoded."""
        if not v:
            raise ValueError(
                "MSA_MASTER_KEY environment variable is required.\n"
                "Generate one with: python -c \"import secrets, base64; "
                'print(\'base64:\' + base64.b64encode(secrets.token_bytes(32)).decode())"'
            )

        if not v.startswith("base64:"):
            raise ValueError("Master key must start with 'base64:'")

        try:
            key_bytes = base64.b64decode(v[7:])
            if len(key_bytes) != 32:
                raise ValueError("Master key must be exactly 32 bytes when decoded")
        except Exception as e:
            raise ValueError(f"Invalid base64 encoding: {e}") from e

        return v

    def get_allowed_services(self) -> list[str]:
        """Get list of allowed service names from config.yaml."""
        services = self._yaml_config.get("services", [])
        return [
            svc["name"]
            for svc in services
            if isinstance(svc, dict) and svc.get("enabled", True)
        ]

    def get_service_token(self, service: str) -> str | None:
        """Get token for a specific service from environment variable.

        Token must be set as environment variable: TOKEN_<service-name>
        """
        token_key = f"TOKEN_{service}"
        return os.getenv(token_key)

    def get_service_prefixes(self, service: str) -> list[str]:
        """Get allowed access rule prefixes for a specific service from config.yaml.

        DEPRECATED: Use get_service_roles() with RBAC policies instead.
        This method is kept for backward compatibility.
        """
        services = self._yaml_config.get("services", [])
        for svc in services:
            if isinstance(svc, dict) and svc.get("name") == service:
                return svc.get("access_rules", [])
        return []

    def get_service_roles(self, service: str) -> list[str]:
        """Get list of role names assigned to a specific service."""
        services = self._yaml_config.get("services", [])
        for svc in services:
            if isinstance(svc, dict) and svc.get("name") == service:
                return svc.get("roles", [])
        return []

    def get_policies(self) -> list[dict[str, Any]]:
        """Get all RBAC policies from config.yaml."""
        return self._yaml_config.get("policies", [])

    def get_master_key_bytes(self) -> bytes:
        """Get decoded master key bytes."""
        return base64.b64decode(self.msa_master_key[7:])

    def get_app_config(self) -> dict[str, Any]:
        """Get application configuration section from YAML."""
        return self._yaml_config.get("application", {})

    def get_audit_config(self) -> dict[str, Any]:
        """Get audit configuration section from YAML."""
        return self._yaml_config.get("audit", {})

    def get_cors_config(self) -> dict[str, Any]:
        """Get CORS configuration section from YAML."""
        return self._yaml_config.get("cors", {})


# Global settings instance
settings = Settings()
