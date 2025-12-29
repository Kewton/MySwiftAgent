"""Template validation result schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class TemplateValidationWarning(BaseModel):
    """Template validation warning or error."""

    variable: str = Field(
        description="The problematic template variable (e.g., {{job.body.email}})"
    )
    message: str = Field(description="Warning or error message")
    severity: Literal["warning", "error"] = Field(
        default="warning", description="Severity level"
    )


class TemplateValidationResult(BaseModel):
    """Template validation result.

    Returned by TemplateValidator.validate() and included in
    TaskMasterResponse for POST/PUT operations.
    """

    is_valid: bool = Field(
        description="True if template is syntactically valid (no errors)"
    )
    warnings: list[TemplateValidationWarning] = Field(
        default_factory=list, description="List of warnings and errors"
    )
    extracted_variables: list[str] = Field(
        default_factory=list, description="List of extracted template variables"
    )

    @property
    def has_errors(self) -> bool:
        """Check if there are any errors (severity='error')."""
        return any(w.severity == "error" for w in self.warnings)

    @property
    def has_warnings(self) -> bool:
        """Check if there are any warnings (severity='warning')."""
        return any(w.severity == "warning" for w in self.warnings)

    @property
    def error_count(self) -> int:
        """Count of errors."""
        return sum(1 for w in self.warnings if w.severity == "error")

    @property
    def warning_count(self) -> int:
        """Count of warnings."""
        return sum(1 for w in self.warnings if w.severity == "warning")
