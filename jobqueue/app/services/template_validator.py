"""Template validation service for body_template fields."""

import json
from typing import Any

from app.schemas.template_validation import (
    TemplateValidationResult,
    TemplateValidationWarning,
)
from app.services.template_patterns import TemplatePatterns


class TemplateValidator:
    """Validates body_template structure and variables.

    Used during TaskMaster creation/update to detect potential issues
    with template variables before runtime.
    """

    # Security limits (DoS prevention)
    MAX_TEMPLATE_SIZE = 64 * 1024  # 64KB
    MAX_VARIABLES_COUNT = 100
    MAX_PATH_DEPTH = 10

    # Use patterns from shared module
    VARIABLE_PATTERN = TemplatePatterns.TASK_VARIABLE
    JOB_VARIABLE_PATTERN = TemplatePatterns.JOB_VARIABLE
    CURRENT_TASK_PATTERN = TemplatePatterns.CURRENT_TASK_VARIABLE

    @classmethod
    def validate(
        cls,
        body_template: dict[str, Any] | None,
        job_body_schema: dict[str, Any] | None = None,
    ) -> TemplateValidationResult:
        """Validate body_template structure and variables.

        Args:
            body_template: Template to validate (from TaskMaster)
            job_body_schema: Optional Job body JSON schema for reference validation

        Returns:
            Validation result with is_valid, warnings, and extracted_variables
        """
        if body_template is None:
            return TemplateValidationResult(is_valid=True)

        warnings: list[TemplateValidationWarning] = []
        extracted_variables: list[str] = []

        # 0. Size check (DoS prevention)
        try:
            template_str = json.dumps(body_template, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            return TemplateValidationResult(
                is_valid=False,
                warnings=[
                    TemplateValidationWarning(
                        variable="",
                        message=f"Invalid template structure: {e}",
                        severity="error",
                    )
                ],
            )

        if len(template_str.encode("utf-8")) > cls.MAX_TEMPLATE_SIZE:
            return TemplateValidationResult(
                is_valid=False,
                warnings=[
                    TemplateValidationWarning(
                        variable="",
                        message=f"Template size exceeds maximum ({cls.MAX_TEMPLATE_SIZE} bytes)",
                        severity="error",
                    )
                ],
            )

        # 1. Extract template variables
        cls._extract_variables(body_template, extracted_variables)

        # 1.1. Variable count check (DoS prevention)
        if len(extracted_variables) > cls.MAX_VARIABLES_COUNT:
            warnings.append(
                TemplateValidationWarning(
                    variable="",
                    message=f"Too many template variables ({len(extracted_variables)} > {cls.MAX_VARIABLES_COUNT})",
                    severity="error",
                )
            )

        # 2. Syntax validation
        syntax_warnings = cls._validate_syntax(extracted_variables)
        warnings.extend(syntax_warnings)

        # 3. Path depth validation
        depth_warnings = cls._validate_path_depth(extracted_variables)
        warnings.extend(depth_warnings)

        # 4. Reference validation
        if job_body_schema:
            ref_warnings = cls._validate_job_body_references(
                extracted_variables, job_body_schema
            )
            warnings.extend(ref_warnings)
        else:
            # No schema - generate informational warnings for job.body references
            for var in extracted_variables:
                if var.startswith("{{job.body."):
                    # Extract field path for clearer message
                    match = cls.JOB_VARIABLE_PATTERN.match(var)
                    if match:
                        path = match.group(2) or ""
                        field_info = path.strip(".") if path else "body"
                        warnings.append(
                            TemplateValidationWarning(
                                variable=var,
                                message=f"Template references 'job.body.{field_info}'. "
                                "Ensure Job body contains this field at runtime.",
                                severity="warning",
                            )
                        )

        # Determine overall validity
        has_errors = any(w.severity == "error" for w in warnings)

        return TemplateValidationResult(
            is_valid=not has_errors,
            warnings=warnings,
            extracted_variables=extracted_variables,
        )

    @classmethod
    def _extract_variables(
        cls,
        template: dict[str, Any] | str | list[Any] | None,
        result: list[str],
    ) -> None:
        """Recursively extract template variables from structure.

        DRY principle: Delegates to TemplatePatterns.extract_all_variables
        for string extraction, maintaining recursive structure traversal here.

        Args:
            template: Template structure to scan
            result: List to append found variables
        """
        if template is None:
            return

        if isinstance(template, dict):
            for value in template.values():
                cls._extract_variables(value, result)
        elif isinstance(template, list):
            for item in template:
                cls._extract_variables(item, result)
        elif isinstance(template, str):
            # DRY: Use shared extraction from TemplatePatterns
            result.extend(TemplatePatterns.extract_all_variables(template))

    @classmethod
    def _validate_syntax(
        cls,
        variables: list[str],
    ) -> list[TemplateValidationWarning]:
        """Validate template variable syntax.

        Args:
            variables: List of extracted variables

        Returns:
            List of syntax-related warnings
        """
        warnings: list[TemplateValidationWarning] = []

        for var in variables:
            # Check for unusually large task indices
            task_match = cls.VARIABLE_PATTERN.match(var)
            if task_match:
                task_index = int(task_match.group(1))
                if task_index > 100:
                    warnings.append(
                        TemplateValidationWarning(
                            variable=var,
                            message=f"Task index {task_index} seems unusually large. "
                            "Verify task order.",
                            severity="warning",
                        )
                    )

        return warnings

    @classmethod
    def _validate_path_depth(
        cls,
        variables: list[str],
    ) -> list[TemplateValidationWarning]:
        """Validate path depth for all variables.

        Args:
            variables: List of extracted variables

        Returns:
            List of path depth warnings/errors
        """
        warnings: list[TemplateValidationWarning] = []

        for var in variables:
            depth = TemplatePatterns.get_path_depth(var)
            if depth > cls.MAX_PATH_DEPTH:
                warnings.append(
                    TemplateValidationWarning(
                        variable=var,
                        message=f"Path depth {depth} exceeds maximum {cls.MAX_PATH_DEPTH}",
                        severity="error",
                    )
                )

        return warnings

    @classmethod
    def _validate_job_body_references(
        cls,
        variables: list[str],
        job_body_schema: dict[str, Any],
    ) -> list[TemplateValidationWarning]:
        """Validate job.body references against provided schema.

        Args:
            variables: List of extracted variables
            job_body_schema: JSON Schema for Job body

        Returns:
            List of reference validation warnings
        """
        warnings: list[TemplateValidationWarning] = []
        schema_properties = job_body_schema.get("properties", {})

        for var in variables:
            job_match = cls.JOB_VARIABLE_PATTERN.match(var)
            if job_match and job_match.group(1) == "body":
                path = job_match.group(2)
                if path:
                    # Get first-level field name
                    field_name = path.strip(".").split(".")[0]
                    if field_name not in schema_properties:
                        available = list(schema_properties.keys())
                        warnings.append(
                            TemplateValidationWarning(
                                variable=var,
                                message=f"Field '{field_name}' not found in Job body schema. "
                                f"Available fields: {available}",
                                severity="warning",
                            )
                        )

        return warnings
