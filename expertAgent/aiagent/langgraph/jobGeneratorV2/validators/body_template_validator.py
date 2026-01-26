"""Body template validator for body_template integrity checking.

Issue #358: Validate body_template references against schemas.
Issue #408: Validate user_input field names against user_input_schema.

This module provides:
- BodyTemplateValidator: Main validator class
- BodyTemplateValidationResult: Validation result with errors/warnings
- ValidationStrategy: Protocol for engine-specific validation
- TaskFlowValidationStrategy: Validation for TaskFlow engine
- GraphAIValidationStrategy: Validation for GraphAI engine

Validation checks:
1. job.body.X references exist in input_schema
2. tasks[N].output_data references have valid N < task_count
3. tasks[N].output_data.field references exist in task's output_schema
4. user_input.X field references exist in user_input_schema (Issue #408)
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from .schema_comparator import field_in_schema
from .template_variable_extractor import (
    TemplateVariableResult,
    extract_template_variables,
)

logger = logging.getLogger(__name__)

# Issue #395: System-injected fields that should be excluded from validation
# These fields are automatically injected by the system during JobMaster creation
# and are not part of user input. They should not be validated against the task's
# input_schema as they are managed separately by the system.
SYSTEM_INJECTED_FIELDS: frozenset[str] = frozenset(
    {
        "project",  # Issue #391: Used for secrets resolution, injected in JobMaster.body
        "user_input",  # Issue #396: User input object passed from job.body
    }
)


def _is_system_injected_field(field_path: str) -> bool:
    """Check if field_path is a system-injected field or its sub-field.

    Issue #407: Supports prefix matching for nested fields like 'user_input.query'.

    This function checks if the given field_path is either an exact match for
    a system-injected field or starts with a system-injected field followed
    by a dot (indicating a nested field access).

    Args:
        field_path: The field path to check (e.g., "user_input", "user_input.query")

    Returns:
        True if field_path is a system-injected field or its sub-field, False otherwise

    Examples:
        >>> _is_system_injected_field("user_input")
        True
        >>> _is_system_injected_field("user_input.query")
        True
        >>> _is_system_injected_field("project.name")
        True
        >>> _is_system_injected_field("query")
        False
        >>> _is_system_injected_field("user_input_extra")
        False
    """
    return any(
        field_path == f or field_path.startswith(f + ".")
        for f in SYSTEM_INJECTED_FIELDS
    )


@dataclass
class BodyTemplateValidationError:
    """Validation error for body_template.

    Attributes:
        error_type: Type of error (MISSING_REFERENCE, INVALID_INDEX, SCHEMA_MISMATCH)
        message: Human-readable error message
        location: Location of the error (e.g., "job.body.field")
    """

    error_type: str
    message: str
    location: str


@dataclass
class BodyTemplateValidationWarning:
    """Validation warning for body_template.

    Attributes:
        warning_type: Type of warning (e.g., UNUSED_FIELD)
        message: Human-readable warning message
        location: Location of the warning
    """

    warning_type: str
    message: str
    location: str


@dataclass
class BodyTemplateValidationResult:
    """Result of body_template validation.

    Attributes:
        errors: List of validation errors
        warnings: List of validation warnings
        required_job_body_fields: Set of required job body fields
    """

    errors: list[BodyTemplateValidationError] = field(default_factory=list)
    warnings: list[BodyTemplateValidationWarning] = field(default_factory=list)
    required_job_body_fields: set[str] = field(default_factory=set)

    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors).

        Returns:
            True if no errors, False otherwise
        """
        return len(self.errors) == 0


class ValidationStrategy(Protocol):
    """Protocol for engine-specific validation strategies.

    Different engines (TaskFlow, GraphAI) may have different valid patterns
    for body_template references.
    """

    def validate_job_body_reference(
        self,
        reference: str,
        input_schema: dict[str, Any],
    ) -> list[BodyTemplateValidationError]:
        """Validate a job.body reference.

        Args:
            reference: The job.body reference (e.g., "job.body.field")
            input_schema: The input schema to validate against

        Returns:
            List of validation errors (empty if valid)
        """
        ...

    def validate_task_reference(
        self,
        task_index: int,
        field_path: str,
        task_count: int,
        task_output_schemas: list[dict[str, Any]],
    ) -> list[BodyTemplateValidationError]:
        """Validate a task output reference.

        Args:
            task_index: Index of referenced task
            field_path: Field path within output_data
            task_count: Number of existing tasks
            task_output_schemas: Output schemas for each task

        Returns:
            List of validation errors (empty if valid)
        """
        ...


class TaskFlowValidationStrategy:
    """Validation strategy for TaskFlow engine.

    TaskFlow uses:
    - {{job.body}} for entire body passthrough
    - {{job.project}} for project reference
    - {{tasks[N].output_data}} for task chaining
    """

    def validate_job_body_reference(
        self,
        reference: str,
        input_schema: dict[str, Any],
    ) -> list[BodyTemplateValidationError]:
        """Validate job.body reference for TaskFlow.

        For TaskFlow, {{job.body}} (entire body) is always valid.
        Specific field references like {{job.body.field}} must exist in schema.
        """
        errors: list[BodyTemplateValidationError] = []

        # {{job.body}} without field path is always valid (entire body)
        if reference == "job.body":
            return errors

        # Extract field path from job.body.field
        if reference.startswith("job.body."):
            field_path = reference[9:]  # Remove "job.body."

            # Issue #395, #407: Skip validation for system-injected fields
            # and their sub-fields (e.g., user_input.query)
            if _is_system_injected_field(field_path):
                logger.debug(
                    "Skipping validation for system-injected field: %s",
                    field_path,
                )
                return errors

            if not field_in_schema(field_path, input_schema):
                errors.append(
                    BodyTemplateValidationError(
                        error_type="MISSING_REFERENCE",
                        message=f"Field '{field_path}' not found in input_schema",
                        location=reference,
                    )
                )

        return errors

    def validate_task_reference(
        self,
        task_index: int,
        field_path: str,
        task_count: int,
        task_output_schemas: list[dict[str, Any]],
    ) -> list[BodyTemplateValidationError]:
        """Validate task output reference for TaskFlow."""
        errors: list[BodyTemplateValidationError] = []

        # Check task index is valid
        if task_index >= task_count:
            errors.append(
                BodyTemplateValidationError(
                    error_type="INVALID_INDEX",
                    message=f"Task index {task_index} is invalid. "
                    f"Valid range: 0 to {task_count - 1}",
                    location=f"tasks[{task_index}].output_data",
                )
            )
            return errors

        # Check field path if specified
        if field_path and task_output_schemas:
            if task_index < len(task_output_schemas):
                output_schema = task_output_schemas[task_index]
                if not field_in_schema(field_path, output_schema):
                    errors.append(
                        BodyTemplateValidationError(
                            error_type="MISSING_REFERENCE",
                            message=f"Field '{field_path}' not found in "
                            f"tasks[{task_index}].output_data schema",
                            location=f"tasks[{task_index}].output_data.{field_path}",
                        )
                    )

        return errors


class GraphAIValidationStrategy:
    """Validation strategy for GraphAI engine.

    GraphAI uses:
    - {{job.body.user_input}} for user input extraction
    - {{job.body}} for job parameters
    - {{tasks[N].output_data}} for task chaining
    """

    def validate_job_body_reference(
        self,
        reference: str,
        input_schema: dict[str, Any],
    ) -> list[BodyTemplateValidationError]:
        """Validate job.body reference for GraphAI.

        GraphAI typically references specific fields like job.body.user_input.
        """
        errors: list[BodyTemplateValidationError] = []

        # {{job.body}} (entire body) is valid for job_params
        if reference == "job.body":
            return errors

        # Extract field path from job.body.field
        if reference.startswith("job.body."):
            field_path = reference[9:]  # Remove "job.body."

            # Issue #395, #407: Skip validation for system-injected fields
            # and their sub-fields (e.g., user_input.query)
            if _is_system_injected_field(field_path):
                logger.debug(
                    "Skipping validation for system-injected field: %s",
                    field_path,
                )
                return errors

            if not field_in_schema(field_path, input_schema):
                errors.append(
                    BodyTemplateValidationError(
                        error_type="MISSING_REFERENCE",
                        message=f"Field '{field_path}' not found in input_schema",
                        location=reference,
                    )
                )

        return errors

    def validate_task_reference(
        self,
        task_index: int,
        field_path: str,
        task_count: int,
        task_output_schemas: list[dict[str, Any]],
    ) -> list[BodyTemplateValidationError]:
        """Validate task output reference for GraphAI."""
        errors: list[BodyTemplateValidationError] = []

        # Check task index is valid
        if task_index >= task_count:
            errors.append(
                BodyTemplateValidationError(
                    error_type="INVALID_INDEX",
                    message=f"Task index {task_index} is invalid. "
                    f"Valid range: 0 to {task_count - 1}",
                    location=f"tasks[{task_index}].output_data",
                )
            )
            return errors

        # Check field path if specified
        if field_path and task_output_schemas:
            if task_index < len(task_output_schemas):
                output_schema = task_output_schemas[task_index]
                if not field_in_schema(field_path, output_schema):
                    errors.append(
                        BodyTemplateValidationError(
                            error_type="MISSING_REFERENCE",
                            message=f"Field '{field_path}' not found in "
                            f"tasks[{task_index}].output_data schema",
                            location=f"tasks[{task_index}].output_data.{field_path}",
                        )
                    )

        return errors


class BodyTemplateValidator:
    """Validator for body_template integrity.

    Validates that body_template references are consistent with:
    - input_schema: Fields referenced via {{job.body.X}}
    - task_count: Valid task indices for {{tasks[N].output_data}}
    - task_output_schemas: Fields in task output data

    Example:
        >>> validator = BodyTemplateValidator()
        >>> result = validator.validate(
        ...     body_template={"inputs": "{{job.body.user_input}}"},
        ...     input_schema={"type": "object", "properties": {"user_input": {}}},
        ...     task_count=0,
        ...     task_output_schemas=[],
        ... )
        >>> result.is_valid
        True
    """

    def __init__(
        self,
        strategy: ValidationStrategy | None = None,
    ) -> None:
        """Initialize BodyTemplateValidator.

        Args:
            strategy: Validation strategy (default: TaskFlowValidationStrategy)
        """
        self._strategy: ValidationStrategy = strategy or TaskFlowValidationStrategy()

    def validate(
        self,
        body_template: dict[str, Any],
        input_schema: dict[str, Any],
        task_count: int,
        task_output_schemas: list[dict[str, Any]],
        user_input_schema: dict[str, Any] | None = None,
    ) -> BodyTemplateValidationResult:
        """Validate body_template against schemas.

        Issue #408: Added user_input_schema parameter for user input field validation.

        Args:
            body_template: Body template dictionary to validate
            input_schema: Input schema for job.body validation
            task_count: Number of preceding tasks
            task_output_schemas: Output schemas for each preceding task
            user_input_schema: Optional user input schema for validating user_input.X
                references. When provided, validates that references to
                job.body.user_input.X match fields in user_input_schema.

        Returns:
            BodyTemplateValidationResult with errors and warnings
        """
        logger.debug("Validating body_template: %s", body_template)

        errors: list[BodyTemplateValidationError] = []
        warnings: list[BodyTemplateValidationWarning] = []

        # Extract template variables
        extracted = extract_template_variables(body_template)

        # Validate job.body references
        errors.extend(self._validate_job_body_references(extracted, input_schema))

        # Validate task output references
        errors.extend(
            self._validate_task_references(extracted, task_count, task_output_schemas)
        )

        # Issue #408: Validate user_input field references
        user_input_warnings = self._validate_user_input_fields(
            body_template=body_template,
            user_input_schema=user_input_schema,
        )

        # Issue #408: Check if strict validation is enabled
        strict_validation = os.environ.get(
            "BODY_TEMPLATE_STRICT_VALIDATION", "false"
        ).lower() in ("true", "1", "yes")

        if strict_validation:
            # Convert warnings to errors in strict mode
            for warning in user_input_warnings:
                errors.append(
                    BodyTemplateValidationError(
                        error_type="USER_INPUT_FIELD_MISMATCH",
                        message=warning.message,
                        location=warning.location,
                    )
                )
        else:
            warnings.extend(user_input_warnings)

        # Get required job body fields
        required_fields = extracted.get_required_job_body_fields()

        return BodyTemplateValidationResult(
            errors=errors,
            warnings=warnings,
            required_job_body_fields=required_fields,
        )

    def _validate_user_input_fields(
        self,
        body_template: dict[str, Any],
        user_input_schema: dict[str, Any] | None,
    ) -> list[BodyTemplateValidationWarning]:
        """Validate user_input.X field references against user_input_schema.

        Issue #408: Check that references to job.body.user_input.X exist in user_input_schema.
        This helps detect when LLM changes field names (e.g., email -> recipient_email).

        Args:
            body_template: Body template dictionary to validate
            user_input_schema: User input schema with properties to check against.
                If None, validation is skipped for backward compatibility.

        Returns:
            List of warnings for mismatched field names
        """
        warnings: list[BodyTemplateValidationWarning] = []

        # Skip validation if no user_input_schema provided (backward compatibility)
        if user_input_schema is None:
            return warnings

        # Get valid field names from user_input_schema
        valid_fields = set(user_input_schema.get("properties", {}).keys())

        # Pattern to match user_input.X references
        # Matches: {{job.body.user_input.field_name}}
        user_input_pattern = re.compile(
            r"\{\{job\.body\.user_input\.([a-zA-Z_][a-zA-Z0-9_]*)\}\}"
        )

        # Convert body_template to string for pattern matching
        template_str = str(body_template)

        # Find all user_input.X references
        matches = user_input_pattern.findall(template_str)

        for field_name in matches:
            if field_name not in valid_fields:
                warnings.append(
                    BodyTemplateValidationWarning(
                        warning_type="USER_INPUT_FIELD_MISMATCH",
                        message=f"Field '{field_name}' not found in user_input_schema. "
                        f"Available fields: {sorted(valid_fields)}. "
                        "The LLM may have changed the field name.",
                        location=f"job.body.user_input.{field_name}",
                    )
                )
                logger.warning(
                    "Issue #408: User input field mismatch - '%s' not in schema. "
                    "Available: %s",
                    field_name,
                    sorted(valid_fields),
                )

        return warnings

    def _validate_job_body_references(
        self,
        extracted: TemplateVariableResult,
        input_schema: dict[str, Any],
    ) -> list[BodyTemplateValidationError]:
        """Validate all job.body references.

        Args:
            extracted: Extracted template variables
            input_schema: Schema to validate against

        Returns:
            List of validation errors
        """
        errors: list[BodyTemplateValidationError] = []

        for ref in extracted.job_body_refs:
            errors.extend(self._strategy.validate_job_body_reference(ref, input_schema))

        return errors

    def _validate_task_references(
        self,
        extracted: TemplateVariableResult,
        task_count: int,
        task_output_schemas: list[dict[str, Any]],
    ) -> list[BodyTemplateValidationError]:
        """Validate all task output references.

        Args:
            extracted: Extracted template variables
            task_count: Number of preceding tasks
            task_output_schemas: Output schemas for each task

        Returns:
            List of validation errors
        """
        errors: list[BodyTemplateValidationError] = []

        for ref in extracted.task_output_refs:
            errors.extend(
                self._strategy.validate_task_reference(
                    task_index=ref.task_index,
                    field_path=ref.field_path,
                    task_count=task_count,
                    task_output_schemas=task_output_schemas,
                )
            )

        return errors


__all__ = [
    "BodyTemplateValidator",
    "BodyTemplateValidationResult",
    "BodyTemplateValidationError",
    "BodyTemplateValidationWarning",
    "ValidationStrategy",
    "TaskFlowValidationStrategy",
    "GraphAIValidationStrategy",
    "SYSTEM_INJECTED_FIELDS",
    "_is_system_injected_field",
]
