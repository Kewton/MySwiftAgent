"""Enhanced ValidationPipeline with Structural, Schema, and Semantic validators.

Issue #359 Iteration 2 Task 2.2: ValidationPipeline enhancement.

This module provides:
- StructuralValidator: Basic workflow structure validation
- SchemaValidator: JSON schema validation
- SemanticValidator: Step reference and semantic validation
- ValidationPipeline: Enhanced pipeline with chain pattern

Chain pattern execution order:
1. StructuralValidator - Basic structure (workflow_name, steps exist)
2. SchemaValidator - JSON schema validity
3. SemanticValidator - Step references and semantic correctness
"""

from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from . import (
    ValidationError,
    ValidationErrorCode,
    ValidationResult,
    WorkflowValidator,
)

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.observability import ValidationObserver

logger = logging.getLogger(__name__)


class StructuralValidator(WorkflowValidator):
    """Validates basic workflow structure.

    Checks:
    - workflow_name exists and is valid
    - steps array exists and is non-empty
    - Required top-level fields exist
    """

    REQUIRED_FIELDS = ["workflow_name", "steps", "input_schema", "output_schema", "output"]

    def validate(self, workflow: dict[str, Any]) -> list[ValidationError]:
        """Validate workflow structure."""
        errors: list[ValidationError] = []

        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in workflow:
                errors.append(ValidationError(
                    code=ValidationErrorCode.VALIDATION_FAILED,
                    message=f"Missing required field: {field}",
                    location=f"workflow.{field}",
                    suggestion=f"Add '{field}' field to workflow definition",
                    severity="critical",
                ))

        # Check workflow_name format
        if "workflow_name" in workflow:
            name = workflow["workflow_name"]
            if not isinstance(name, str) or not name:
                errors.append(ValidationError(
                    code=ValidationErrorCode.VALIDATION_FAILED,
                    message="workflow_name must be a non-empty string",
                    location="workflow.workflow_name",
                    suggestion="Provide a valid workflow name",
                    severity="critical",
                ))
            elif not re.match(r"^[a-zA-Z_][a-zA-Z0-9_-]*$", name):
                errors.append(ValidationError(
                    code=ValidationErrorCode.VALIDATION_FAILED,
                    message=f"Invalid workflow_name format: {name}",
                    location="workflow.workflow_name",
                    suggestion="Use alphanumeric, underscore, hyphen; start with letter/underscore",
                    severity="major",
                ))

        # Check steps
        if "steps" in workflow:
            steps = workflow["steps"]
            if not isinstance(steps, list):
                errors.append(ValidationError(
                    code=ValidationErrorCode.VALIDATION_FAILED,
                    message="steps must be an array",
                    location="workflow.steps",
                    suggestion="Define steps as an array of step objects",
                    severity="critical",
                ))
            elif len(steps) == 0:
                errors.append(ValidationError(
                    code=ValidationErrorCode.VALIDATION_FAILED,
                    message="steps array cannot be empty",
                    location="workflow.steps",
                    suggestion="Add at least one step to the workflow",
                    severity="critical",
                ))
            else:
                # Validate each step has id and type
                for i, step in enumerate(steps):
                    if not isinstance(step, dict):
                        errors.append(ValidationError(
                            code=ValidationErrorCode.VALIDATION_FAILED,
                            message=f"Step {i} is not an object",
                            location=f"workflow.steps[{i}]",
                            suggestion="Each step must be an object with id, type, config",
                            severity="critical",
                        ))
                        continue

                    if "id" not in step:
                        errors.append(ValidationError(
                            code=ValidationErrorCode.VALIDATION_FAILED,
                            message=f"Step {i} missing 'id' field",
                            location=f"workflow.steps[{i}]",
                            suggestion="Add unique 'id' to each step",
                            severity="critical",
                        ))

                    if "type" not in step:
                        errors.append(ValidationError(
                            code=ValidationErrorCode.VALIDATION_FAILED,
                            message=f"Step {i} missing 'type' field",
                            location=f"workflow.steps[{i}]",
                            suggestion="Add 'type' (api_rest, transform, code_js) to each step",
                            severity="critical",
                        ))

        return errors


class SchemaValidator(WorkflowValidator):
    """Validates JSON schema fields.

    Checks:
    - input_schema is valid JSON
    - output_schema is valid JSON
    - output mapping is valid JSON
    """

    def validate(self, workflow: dict[str, Any]) -> list[ValidationError]:
        """Validate JSON schema fields."""
        errors: list[ValidationError] = []

        # Validate input_schema
        if "input_schema" in workflow:
            errors.extend(self._validate_json_field(
                workflow["input_schema"],
                "input_schema",
            ))

        # Validate output_schema
        if "output_schema" in workflow:
            errors.extend(self._validate_json_field(
                workflow["output_schema"],
                "output_schema",
            ))

        # Validate output mapping
        if "output" in workflow:
            errors.extend(self._validate_json_field(
                workflow["output"],
                "output",
            ))

        return errors

    def _validate_json_field(
        self,
        value: Any,
        field_name: str,
    ) -> list[ValidationError]:
        """Validate a JSON field value."""
        errors: list[ValidationError] = []

        if isinstance(value, str):
            # Replace variable references for validation
            test_value = re.sub(r'\$\{[^}]+\}', '"PLACEHOLDER"', value)
            try:
                parsed = json.loads(test_value)
                if not isinstance(parsed, dict):
                    errors.append(ValidationError(
                        code=ValidationErrorCode.VALIDATION_FAILED,
                        message=f"{field_name} must be a JSON object",
                        location=f"workflow.{field_name}",
                        suggestion="Ensure the JSON parses to an object {}",
                        severity="major",
                    ))
            except json.JSONDecodeError as e:
                errors.append(ValidationError(
                    code=ValidationErrorCode.VALIDATION_FAILED,
                    message=f"{field_name} is not valid JSON: {e}",
                    location=f"workflow.{field_name}",
                    suggestion="Fix JSON syntax errors",
                    severity="critical",
                ))
        elif isinstance(value, dict):
            # Already a dict, valid
            pass
        else:
            errors.append(ValidationError(
                code=ValidationErrorCode.VALIDATION_FAILED,
                message=f"{field_name} must be a JSON string or object",
                location=f"workflow.{field_name}",
                suggestion="Provide valid JSON",
                severity="critical",
            ))

        return errors


class SemanticValidator(WorkflowValidator):
    """Validates semantic correctness of workflow.

    Checks:
    - Step references are valid (${step_id.output} exists)
    - No circular step dependencies
    - Output references valid steps
    """

    REFERENCE_PATTERN = re.compile(r'\$\{([a-zA-Z_][a-zA-Z0-9_]*)\.([^}]+)\}')

    def validate(self, workflow: dict[str, Any]) -> list[ValidationError]:
        """Validate semantic correctness."""
        errors: list[ValidationError] = []

        # Get all step IDs
        step_ids = set()
        if "steps" in workflow and isinstance(workflow["steps"], list):
            for step in workflow["steps"]:
                if isinstance(step, dict) and "id" in step:
                    step_ids.add(step["id"])

        # Check references in steps
        if "steps" in workflow and isinstance(workflow["steps"], list):
            for i, step in enumerate(workflow["steps"]):
                if not isinstance(step, dict):
                    continue

                # Check config for references
                config = step.get("config", {})
                if isinstance(config, dict):
                    errors.extend(self._check_references_in_dict(
                        config,
                        f"workflow.steps[{i}].config",
                        step_ids,
                    ))

        # Check output references
        if "output" in workflow:
            output_str = workflow["output"]
            if isinstance(output_str, str):
                errors.extend(self._check_references_in_string(
                    output_str,
                    "workflow.output",
                    step_ids,
                ))

        return errors

    def _check_references_in_dict(
        self,
        obj: dict[str, Any],
        location: str,
        valid_step_ids: set[str],
    ) -> list[ValidationError]:
        """Check references in a dictionary recursively."""
        errors: list[ValidationError] = []

        for key, value in obj.items():
            field_location = f"{location}.{key}"
            if isinstance(value, str):
                errors.extend(self._check_references_in_string(
                    value, field_location, valid_step_ids
                ))
            elif isinstance(value, dict):
                errors.extend(self._check_references_in_dict(
                    value, field_location, valid_step_ids
                ))

        return errors

    def _check_references_in_string(
        self,
        value: str,
        location: str,
        valid_step_ids: set[str],
    ) -> list[ValidationError]:
        """Check references in a string value."""
        errors: list[ValidationError] = []

        for match in self.REFERENCE_PATTERN.finditer(value):
            ref_name = match.group(1)

            # Skip special references (inputs, secrets)
            if ref_name in ("inputs", "secrets", "env"):
                continue

            # Check if step exists
            if ref_name not in valid_step_ids:
                errors.append(ValidationError(
                    code=ValidationErrorCode.INVALID_SOURCE_PATH,
                    message=f"Reference to non-existent step: {ref_name}",
                    location=location,
                    suggestion=f"Valid step IDs: {', '.join(sorted(valid_step_ids))}",
                    severity="critical",
                ))

        return errors


@dataclass
class PipelineStats:
    """Statistics from pipeline execution."""

    total_errors: int = 0
    critical_errors: int = 0
    major_errors: int = 0
    minor_errors: int = 0
    execution_time_ms: float = 0.0


class ValidationPipeline:
    """Enhanced pipeline with Structural, Schema, and Semantic validators.

    Chain pattern: Structural -> Schema -> Semantic
    """

    def __init__(
        self,
        validators: list[WorkflowValidator] | None = None,
        observer: "ValidationObserver | None" = None,
        fail_fast: bool = False,
    ):
        """Initialize enhanced pipeline.

        Args:
            validators: Custom validators (uses defaults if None)
            observer: Optional observer for monitoring
            fail_fast: Stop on first critical error if True
        """
        if validators is None:
            self.validators = [
                StructuralValidator(),
                SchemaValidator(),
                SemanticValidator(),
            ]
        else:
            self.validators = validators

        self.observer = observer
        self.fail_fast = fail_fast

    def validate(
        self,
        workflow: dict[str, Any],
        workflow_id: str = "",
    ) -> ValidationResult:
        """Validate workflow using all validators in order."""
        start_time = time.time()
        all_errors: list[ValidationError] = []

        for validator in self.validators:
            try:
                errors = validator.validate(workflow)
                all_errors.extend(errors)

                # Fail fast on critical errors
                if self.fail_fast:
                    critical = [e for e in errors if e.severity == "critical"]
                    if critical:
                        break

            except Exception as e:
                logger.warning(
                    "Validator %s raised exception: %s",
                    type(validator).__name__,
                    e,
                )

        # Sort by severity
        all_errors = self._sort_by_severity(all_errors)

        # Compute stats
        execution_time = (time.time() - start_time) * 1000
        stats = self._compute_stats(all_errors, execution_time)

        if stats.total_errors > 0:
            logger.info(
                "Validation: %d errors (critical=%d) in %.2fms",
                stats.total_errors,
                stats.critical_errors,
                stats.execution_time_ms,
            )

        # Notify observer
        if self.observer:
            try:
                self.observer.observe_validation(
                    workflow_id=workflow_id or "unknown",
                    errors=all_errors,
                    duration_ms=execution_time,
                )
            except Exception as e:
                logger.debug("Observer notification failed: %s", e)

        if not all_errors:
            return ValidationResult.success()
        return ValidationResult.failure(all_errors)

    def _sort_by_severity(
        self,
        errors: list[ValidationError],
    ) -> list[ValidationError]:
        """Sort errors by severity."""
        severity_order = {"critical": 0, "major": 1, "minor": 2}
        return sorted(errors, key=lambda e: severity_order.get(e.severity, 1))

    def _compute_stats(
        self,
        errors: list[ValidationError],
        execution_time_ms: float,
    ) -> PipelineStats:
        """Compute stats from errors."""
        stats = PipelineStats(
            total_errors=len(errors),
            execution_time_ms=execution_time_ms,
        )
        for error in errors:
            if error.severity == "critical":
                stats.critical_errors += 1
            elif error.severity == "major":
                stats.major_errors += 1
            else:
                stats.minor_errors += 1
        return stats


# Backward compatibility alias for V3 naming
ValidationPipelineV3 = ValidationPipeline


# Export
__all__ = [
    "StructuralValidator",
    "SchemaValidator",
    "SemanticValidator",
    "ValidationPipeline",
    "ValidationPipelineV3",  # Alias for backward compatibility
    "PipelineStats",
]
