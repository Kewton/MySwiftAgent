"""Configuration management for myVault."""

import base64
import os

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="allow"
    )

    # Service configuration
    allowed_services: str = Field(
        default="",
        description="Comma-separated list of allowed service names",
    )

    # Master encryption key (Base64-encoded 32 bytes)
    msa_master_key: str = Field(
        default="base64:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=",
        description="Master key for AES-256-GCM encryption (base64:...)",
    )

    # Database configuration
    database_url: str = Field(
        default="sqlite:///./myvault.db",
        description="Database connection URL",
    )

    @field_validator("msa_master_key")
    @classmethod
    def validate_master_key(cls, v: str) -> str:
        """Validate that master key is properly formatted and decoded."""
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
        """Get list of allowed service names."""
        if not self.allowed_services:
            return []
        return [s.strip() for s in self.allowed_services.split(",")]

    def get_service_token(self, service: str) -> str | None:
        """Get token for a specific service from environment."""
        token_key = f"TOKEN_{service}"
        return os.getenv(token_key)

    def get_service_prefixes(self, service: str) -> list[str]:
        """Get allowed prefixes for a specific service from environment."""
        allow_key = f"ALLOW_{service}"
        allow_value = os.getenv(allow_key)
        if not allow_value:
            return []
        return [p.strip() for p in allow_value.split(",")]

    def get_master_key_bytes(self) -> bytes:
        """Get decoded master key bytes."""
        return base64.b64decode(self.msa_master_key[7:])


# Global settings instance
settings = Settings()
