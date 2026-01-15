"""Validators for Job Generator V2 workflow validation.

Issue #342 Task 1.1: Abstract interface definitions.
Issue #343: Added sanitize_error_message and improved to_prompt_feedback.

This module provides:
- WorkflowValidator: Base class for all validators
- PromptInjector: Protocol for prompt injection
- PatternProvider: Protocol for pattern provision
- sanitize_error_message: Security function for error message sanitization

All validators implement the WorkflowValidator interface.
"""

import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# Issue #343: Sensitive information patterns for sanitization
SENSITIVE_PATTERNS: list[tuple[str, str]] = [
    (r"/Users/[^/\s]+", "[USER_PATH]"),  # macOS user paths
    (r"/home/[^/\s]+", "[USER_PATH]"),  # Linux user paths
    (r"C:\\Users\\[^\\\s]+", "[USER_PATH]"),  # Windows user paths
    (r"[a-zA-Z0-9_-]{32,}", "[TOKEN]"),  # Long token-like strings
    (r"password\s*[:=]\s*\S+", "password=[MASKED]"),  # Password values
    (r"api[_-]?key\s*[:=]\s*\S+", "api_key=[MASKED]"),  # API keys
    (r"secret\s*[:=]\s*\S+", "secret=[MASKED]"),  # Secret values
]


def sanitize_error_message(message: str, max_length: int = 500) -> str:
    """Sanitize error message for safe LLM inclusion.

    Issue #343: Security feature to prevent prompt injection and info leakage.

    This function:
    1. Masks sensitive information (paths, tokens, passwords)
    2. Removes control characters
    3. Escapes template braces to prevent LLM confusion
    4. Truncates long messages

    Args:
        message: Original error message
        max_length: Maximum message length (default: 500)

    Returns:
        Sanitized error message safe for LLM prompts
    """
    if not message:
        return ""

    # 1. Mask sensitive information
    for pattern, replacement in SENSITIVE_PATTERNS:
        message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)

    # 2. Remove control characters (0x00-0x1f and 0x7f-0x9f)
    message = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", message)

    # 3. Escape template braces to prevent LLM interpretation issues
    message = message.replace("{{", "{ {").replace("}}", "} }")

    # 4. Truncate if too long
    if len(message) > max_length:
        message = message[: max_length - 3] + "..."

    return message


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

    # API schema errors (Issue #344)
    UNKNOWN_API_PARAMETER = "UNKNOWN_API_PARAMETER"
    MISSING_REQUIRED_PARAMETER = "MISSING_REQUIRED_PARAMETER"
    PARAMETER_TYPE_MISMATCH = "PARAMETER_TYPE_MISMATCH"
    PARAMETER_NAME_MISMATCH = "PARAMETER_NAME_MISMATCH"

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

    def to_prompt_feedback(
        self,
        max_errors: int = 5,
        max_total_length: int = 2000,
    ) -> str:
        """Generate prompt feedback section from errors.

        Issue #343: Enhanced with max_errors, max_total_length, sanitization,
        and severity-based sorting.

        Args:
            max_errors: Maximum number of errors to include (default: 5)
            max_total_length: Maximum total feedback length (default: 2000)

        Returns:
            Formatted string for retry prompts, sanitized for security.
        """
        if self.is_valid or not self.errors:
            return ""

        # Sort errors by severity (critical > major > minor)
        severity_order = {"critical": 0, "major": 1, "minor": 2}
        sorted_errors = sorted(
            self.errors,
            key=lambda e: severity_order.get(e.severity, 3),
        )

        # Limit to max_errors
        limited_errors = sorted_errors[:max_errors]

        lines = [
            "",
            "## Previous Generation Errors (MUST FIX)",
            "",
        ]

        for error in limited_errors:
            # Sanitize error message and suggestion for security
            safe_message = sanitize_error_message(error.message)
            safe_suggestion = sanitize_error_message(error.suggestion or "")

            lines.append(f"- **{error.code.value}** at `{error.location}`")
            lines.append(f"  - Error: {safe_message}")
            if safe_suggestion:
                lines.append(f"  - Fix: {safe_suggestion}")
            lines.append("")

        lines.append("Please generate corrected YAML fixing the above errors.")

        feedback = "\n".join(lines)

        # Truncate if too long
        if len(feedback) > max_total_length:
            truncate_at = max_total_length - 50
            feedback = feedback[:truncate_at]
            feedback += "\n\n... (additional errors truncated)"

        return feedback


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
    # Constants (Issue #343)
    "SENSITIVE_PATTERNS",
    # Functions (Issue #343)
    "sanitize_error_message",
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
    # Issue #344: APISchemaValidator - imported from submodule
    # Use: from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import APISchemaValidator
    # Issue #353: PendingWorkflowValidator - imported from submodule
    # Use: from aiagent.langgraph.jobGeneratorV2.validators.pending_workflow import PendingWorkflowValidator
    # Issue #358: BodyTemplateValidator - imported from submodule
    # Use: from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import BodyTemplateValidator
    # Use: from aiagent.langgraph.jobGeneratorV2.validators.template_variable_extractor import extract_template_variables
    # Use: from aiagent.langgraph.jobGeneratorV2.validators.schema_comparator import compare_schemas
    # Issue #359: Security constants - imported from submodule
    # Use: from aiagent.langgraph.jobGeneratorV2.validators.security_constants import ALLOWED_LOCAL_HOSTS, is_local_host
]
