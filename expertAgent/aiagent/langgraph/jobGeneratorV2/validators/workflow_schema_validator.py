"""WorkflowSchemaValidator for integrated workflow validation.

Issue #342 Task 1.4: WorkflowSchemaValidator implementation.

This module integrates multiple validators:
- SourcePathRuleEngine: Validates source path references
- AgentConstraintValidator: Validates agent-specific constraints

It aggregates errors from all validators and provides a unified interface.
"""

from __future__ import annotations

from typing import Any

from aiagent.langgraph.jobGeneratorV2.validators import (
    ValidationError,
    ValidationResult,
    WorkflowValidator,
)
from aiagent.langgraph.jobGeneratorV2.validators.agent_constraint_validator import (
    AgentConstraintValidator,
)
from aiagent.langgraph.jobGeneratorV2.validators.source_path_rule_engine import (
    SourcePathRuleEngine,
)


class WorkflowSchemaValidator(WorkflowValidator):
    """Integrated validator that combines multiple validation strategies.

    This validator orchestrates:
    - Source path validation (SourcePathRuleEngine)
    - Agent constraint validation (AgentConstraintValidator)

    All errors are aggregated and returned in a unified format.
    """

    def __init__(self):
        """Initialize with all sub-validators."""
        self.source_path_validator = SourcePathRuleEngine()
        self.agent_constraint_validator = AgentConstraintValidator()

    def validate(
        self,
        workflow: dict[str, Any],
    ) -> list[ValidationError]:
        """Validate workflow using all sub-validators.

        Args:
            workflow: Workflow dictionary to validate

        Returns:
            List of ValidationError objects from all validators
        """
        all_errors: list[ValidationError] = []

        # Run source path validation
        source_errors = self.source_path_validator.validate(workflow)
        all_errors.extend(source_errors)

        # Run agent constraint validation
        agent_errors = self.agent_constraint_validator.validate(workflow)
        all_errors.extend(agent_errors)

        return all_errors

    def validate_with_result(
        self,
        workflow: dict[str, Any],
    ) -> ValidationResult:
        """Validate workflow and return ValidationResult.

        Args:
            workflow: Workflow dictionary to validate

        Returns:
            ValidationResult with is_valid flag and errors list
        """
        errors = self.validate(workflow)

        if not errors:
            return ValidationResult.success()

        return ValidationResult.failure(errors)

    def to_prompt_feedback(
        self,
        errors: list[ValidationError],
    ) -> str:
        """Generate prompt feedback from errors.

        Args:
            errors: List of ValidationError objects

        Returns:
            Formatted string for LLM retry prompts
        """
        if not errors:
            return ""

        lines = [
            "",
            "## Previous Generation Errors (MUST FIX)",
            "",
        ]

        # Group errors by severity
        critical_errors = [e for e in errors if e.severity == "critical"]
        major_errors = [e for e in errors if e.severity == "major"]
        minor_errors = [e for e in errors if e.severity == "minor"]

        if critical_errors:
            lines.append("### Critical Errors")
            for error in critical_errors:
                lines.append(error.to_prompt_section())

        if major_errors:
            lines.append("### Major Errors")
            for error in major_errors:
                lines.append(error.to_prompt_section())

        if minor_errors:
            lines.append("### Minor Errors")
            for error in minor_errors:
                lines.append(error.to_prompt_section())

        lines.append("")
        lines.append("Please generate corrected YAML fixing the above errors.")

        return "\n".join(lines)


# Export
__all__ = ["WorkflowSchemaValidator"]
