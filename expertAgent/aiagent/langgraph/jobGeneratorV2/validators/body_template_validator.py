"""Body template validator for body_template integrity checking.

Issue #358: Validate body_template references against schemas.

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
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Protocol

from .schema_comparator import field_in_schema
from .template_variable_extractor import (
    TemplateVariableResult,
    extract_template_variables,
)

logger = logging.getLogger(__name__)


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
    ) -> BodyTemplateValidationResult:
        """Validate body_template against schemas.

        Args:
            body_template: Body template dictionary to validate
            input_schema: Input schema for job.body validation
            task_count: Number of preceding tasks
            task_output_schemas: Output schemas for each preceding task

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

        # Get required job body fields
        required_fields = extracted.get_required_job_body_fields()

        return BodyTemplateValidationResult(
            errors=errors,
            warnings=warnings,
            required_job_body_fields=required_fields,
        )

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
]
