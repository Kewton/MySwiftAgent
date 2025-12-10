"""Prompts Management API schemas.

Issue #191: Prompts Management API Implementation
Pydantic schemas for prompt templates and versions.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PromptVersion(BaseModel):
    """Schema for a single prompt version.

    Represents one version of a prompt template with its content and metadata.
    """

    id: str = Field(..., description="Version identifier (e.g., 'default', 'v2')")
    version: int = Field(..., ge=1, description="Version number")
    content: str = Field(..., description="Full prompt content from YAML")
    description: str | None = Field(None, description="Version description")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    is_active: bool = Field(True, description="Whether this version is active")


class PromptTemplate(BaseModel):
    """Schema for a prompt template.

    Represents a complete prompt template with all its versions.
    """

    id: str = Field(..., description="Prompt identifier (directory name)")
    name: str = Field(..., description="Display name for the prompt")
    description: str | None = Field(default=None, description="Prompt description")
    category: str | None = Field(
        default=None, description="Prompt category (e.g., 'system', 'workflow')"
    )
    current_version: int = Field(..., description="Current active version number")
    versions: list[PromptVersion] = Field(
        default_factory=list, description="List of all available versions"
    )
    created_at: datetime | None = Field(default=None, description="Creation timestamp")
    updated_at: datetime | None = Field(
        default=None, description="Last update timestamp"
    )
    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional metadata from YAML"
    )


class PromptListResponse(BaseModel):
    """Response schema for listing prompts.

    Contains a list of prompt templates and the total count.
    """

    items: list[PromptTemplate] = Field(..., description="List of prompt templates")
    total: int = Field(..., description="Total number of prompts")
