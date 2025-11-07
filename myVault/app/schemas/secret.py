"""Pydantic schemas for Secret model."""

from datetime import datetime

from pydantic import BaseModel, Field


class SecretCreate(BaseModel):
    """Schema for creating a new secret."""

    project: str = Field(
        ..., min_length=1, max_length=255, description="Project name"
    )
    path: str = Field(..., min_length=1, max_length=500, description="Secret path")
    value: str = Field(..., min_length=1, description="Secret value (plaintext)")


class SecretUpdate(BaseModel):
    """Schema for updating a secret."""

    value: str = Field(..., min_length=1, description="New secret value (plaintext)")


class SecretResponse(BaseModel):
    """Schema for secret response (with decrypted value)."""

    id: int
    project: str
    path: str
    value: str
    version: int
    updated_at: datetime
    updated_by: str

    model_config = {"from_attributes": True}


class SecretListItem(BaseModel):
    """Schema for secret list item (value redacted)."""

    id: int
    project: str
    path: str
    version: int
    updated_at: datetime
    updated_by: str

    model_config = {"from_attributes": True}
