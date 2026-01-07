"""Error definitions for Workflow Generator V2.

This module defines validation errors and error codes for the
workflow generation process.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ErrorCode(str, Enum):
    """Error codes for workflow validation.

    Each error code corresponds to a specific validation failure type.
    """

    # Structure errors
    MISSING_SOURCE = "MISSING_SOURCE"
    MISSING_RESULT = "MISSING_RESULT"
    INVALID_VERSION = "INVALID_VERSION"

    # Agent errors
    INVALID_AGENT = "INVALID_AGENT"
    UNKNOWN_AGENT = "UNKNOWN_AGENT"

    # Reference errors
    INVALID_REFERENCE = "INVALID_REFERENCE"
    CIRCULAR_REFERENCE = "CIRCULAR_REFERENCE"
    UNDEFINED_NODE_REFERENCE = "UNDEFINED_NODE_REFERENCE"

    # Syntax errors
    YAML_SYNTAX = "YAML_SYNTAX"
    INVALID_YAML_STRUCTURE = "INVALID_YAML_STRUCTURE"

    # Node errors
    EMPTY_NODES = "EMPTY_NODES"
    INVALID_NODE_DEFINITION = "INVALID_NODE_DEFINITION"

    # General errors
    VALIDATION_FAILED = "VALIDATION_FAILED"


# Error code to suggestion mapping
ERROR_SUGGESTIONS: dict[ErrorCode, str] = {
    ErrorCode.MISSING_SOURCE: "Add 'source: {}' as the first node in your workflow.",
    ErrorCode.MISSING_RESULT: "Add 'isResult: true' to at least one output node.",
    ErrorCode.INVALID_VERSION: "Set version to '0.5' (current GraphAI version).",
    ErrorCode.INVALID_AGENT: "Check the agent name against AVAILABLE_AGENTS.md.",
    ErrorCode.UNKNOWN_AGENT: "Verify the agent exists in @graphai/agents package.",
    ErrorCode.INVALID_REFERENCE: "Check the reference path format (':node.path').",
    ErrorCode.CIRCULAR_REFERENCE: "Reorganize node dependencies to break the cycle.",
    ErrorCode.UNDEFINED_NODE_REFERENCE: "Ensure the referenced node is defined in 'nodes'.",
    ErrorCode.YAML_SYNTAX: "Check YAML indentation and syntax.",
    ErrorCode.INVALID_YAML_STRUCTURE: "Ensure the YAML follows GraphAI workflow structure.",
    ErrorCode.EMPTY_NODES: "Add at least one node besides 'source'.",
    ErrorCode.INVALID_NODE_DEFINITION: "Check node structure (agent, inputs, params).",
    ErrorCode.VALIDATION_FAILED: "Review the error details and fix the issues.",
}


@dataclass
class ValidationError:
    """Validation error with details for LLM feedback.

    Attributes:
        code: Error code enum value
        message: Human-readable error message
        location: Error location (e.g., 'nodes.search.agent')
        suggestion: Correction suggestion for LLM retry
    """

    code: ErrorCode
    message: str
    location: str
    suggestion: str = ""

    def __post_init__(self):
        """Set default suggestion from ERROR_SUGGESTIONS if not provided."""
        if not self.suggestion and self.code in ERROR_SUGGESTIONS:
            self.suggestion = ERROR_SUGGESTIONS[self.code]

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
        }


@dataclass
class ValidationResult:
    """Result of YAML validation.

    Attributes:
        is_valid: Whether the YAML is valid
        errors: List of validation errors (empty if valid)
    """

    is_valid: bool
    errors: list[ValidationError]

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
