"""Pydantic schemas for Marp Report Generation API."""

from typing import Any

from pydantic import BaseModel, Field, model_validator


class MarpReportRequest(BaseModel):
    """Request schema for Marp report generation.

    Attributes:
        job_result: Job Generator execution result JSON
        json_file_path: Path to Job Generator result JSON file
        theme: Marp theme (default, gaia, uncover)
        include_implementation_steps: Whether to include implementation steps
    """

    job_result: dict[str, Any] | None = Field(
        default=None,
        description="Job Generator execution result JSON",
    )

    json_file_path: str | None = Field(
        default=None,
        description="Path to Job Generator result JSON file",
    )

    theme: str = Field(
        default="default",
        description="Marp theme (default, gaia, uncover)",
        pattern="^(default|gaia|uncover)$",
    )

    include_implementation_steps: bool = Field(
        default=True,
        description="Whether to include implementation steps in slides",
    )

    @model_validator(mode="after")
    def validate_input_source(self) -> "MarpReportRequest":
        """Validate that exactly one input source is provided."""
        if self.job_result is None and self.json_file_path is None:
            msg = "Either job_result or json_file_path must be provided"
            raise ValueError(msg)

        if self.job_result is not None and self.json_file_path is not None:
            msg = "Only one of job_result or json_file_path should be provided"
            raise ValueError(msg)

        return self


class MarpReportResponse(BaseModel):
    """Response schema for Marp report generation.

    Attributes:
        marp_markdown: Generated Marp Markdown text
        slide_count: Number of generated slides
        suggestions_count: Number of requirement relaxation suggestions
        generation_time_ms: Generation time in milliseconds
    """

    marp_markdown: str = Field(
        ...,
        description="Generated Marp Markdown text",
    )

    slide_count: int = Field(
        ...,
        description="Number of generated slides",
        ge=1,
    )

    suggestions_count: int = Field(
        ...,
        description="Number of requirement relaxation suggestions included",
        ge=0,
    )

    generation_time_ms: float = Field(
        ...,
        description="Generation time in milliseconds",
        ge=0,
    )
