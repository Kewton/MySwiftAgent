"""Validators for Job Generator V2 workflow validation.

Issue #342 Task 1.1: Abstract interface definitions.

This module provides:
- WorkflowValidator: Base class for all validators
- PromptInjector: Protocol for prompt injection
- PatternProvider: Protocol for pattern provision

All validators implement the WorkflowValidator interface.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


class ValidationErrorCode(str, Enum):
    """Error codes for workflow validation.

    Each error code corresponds to a specific validation failure type.
    """

    # Source path errors
    INVALID_SOURCE_PATH = "INVALID_SOURCE_PATH"
    LEGACY_PATH_PATTERN = "LEGACY_PATH_PATTERN"
    MISSING_USER_INPUT_PREFIX = "MISSING_USER_INPUT_PREFIX"

    # Agent constraint errors
    JS_IN_TEMPLATE = "JS_IN_TEMPLATE"
    INVALID_TIMEOUT = "INVALID_TIMEOUT"
    ENV_VAR_IN_URL = "ENV_VAR_IN_URL"

    # General errors
    VALIDATION_FAILED = "VALIDATION_FAILED"


@dataclass
class ValidationError:
    """Validation error with details for LLM feedback.

    Attributes:
        code: Error code enum value
        message: Human-readable error message
        location: Error location (e.g., 'nodes.search.agent')
        suggestion: Correction suggestion for LLM retry
        severity: Error severity (critical, major, minor)
    """

    code: ValidationErrorCode
    message: str
    location: str
    suggestion: str = ""
    severity: str = "major"

    def to_prompt_section(self) -> str:
        """Convert to prompt-friendly format for LLM retry.

        Returns:
            Formatted string for inclusion in retry prompts.
        """
        return f"""- Error: {self.message}
  - Location: {self.location}
  - Fix: {self.suggestion}
"""

    def to_dict(self) -> dict:
        """Convert to dictionary representation.

        Returns:
            Dictionary with error details.
        """
        return {
            "code": self.code.value,
            "message": self.message,
            "location": self.location,
            "suggestion": self.suggestion,
            "severity": self.severity,
        }


@dataclass
class ValidationResult:
    """Result of workflow validation.

    Attributes:
        is_valid: Whether the workflow is valid
        errors: List of validation errors (empty if valid)
    """

    is_valid: bool
    errors: list[ValidationError] = field(default_factory=list)

    @classmethod
    def success(cls) -> "ValidationResult":
        """Create a successful validation result."""
        return cls(is_valid=True, errors=[])

    @classmethod
    def failure(cls, errors: list[ValidationError]) -> "ValidationResult":
        """Create a failed validation result."""
        return cls(is_valid=False, errors=errors)

    def to_prompt_feedback(self) -> str:
        """Generate prompt feedback section from errors.

        Returns:
            Formatted string for retry prompts.
        """
        if self.is_valid:
            return ""

        lines = [
            "",
            "## Previous Generation Errors (MUST FIX)",
            "",
        ]
        for error in self.errors:
            lines.append(error.to_prompt_section())

        lines.append("")
        lines.append("Please generate corrected YAML fixing the above errors.")

        return "\n".join(lines)


class WorkflowValidator(ABC):
    """Base class for workflow validators.

    All validators must implement the validate method which takes a workflow
    dictionary and returns a list of ValidationError objects.
    """

    @abstractmethod
    def validate(self, workflow: dict[str, Any]) -> list[ValidationError]:
        """Validate a workflow.

        Args:
            workflow: The workflow dictionary to validate

        Returns:
            List of validation errors (empty if valid)
        """
        pass

    def log_errors(self, errors: list[ValidationError], workflow_id: str = "") -> None:
        """Log validation errors.

        Args:
            errors: List of validation errors
            workflow_id: Optional workflow identifier
        """
        if errors:
            logger.warning(
                f"Workflow validation errors [{workflow_id}]: {len(errors)} errors found",
                extra={
                    "errors": [e.to_dict() for e in errors],
                    "workflow_id": workflow_id,
                },
            )


@runtime_checkable
class PromptInjector(Protocol):
    """Protocol for prompt injection.

    Implementations inject additional context (API specs, rules, etc.)
    into prompts for LLM workflow generation.
    """

    def inject(self, prompt: str, context: list[str] | dict) -> str:
        """Inject context information into a prompt.

        Args:
            prompt: The original prompt
            context: Context to inject (API list or context dict)

        Returns:
            The enhanced prompt with injected context
        """
        ...


@runtime_checkable
class PatternProvider(Protocol):
    """Protocol for workflow pattern provision.

    Implementations provide standard workflow patterns that can be used
    as templates for workflow generation.
    """

    def get_pattern(self, pattern_name: str) -> dict | None:
        """Get a workflow pattern by name.

        Args:
            pattern_name: Name of the pattern

        Returns:
            Pattern dictionary or None if not found
        """
        ...

    def suggest_pattern(self, requirements: str) -> str:
        """Suggest a pattern based on requirements.

        Args:
            requirements: User requirements text

        Returns:
            Suggested pattern name
        """
        ...


__all__ = [
    # Enums
    "ValidationErrorCode",
    # Data classes
    "ValidationError",
    "ValidationResult",
    # Abstract classes
    "WorkflowValidator",
    # Protocols
    "PromptInjector",
    "PatternProvider",
]
