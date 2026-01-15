"""TaskFlow V2 Validator.

Issue #350 Task 3.1: TaskFlow validator implementation.
Issue #359 Fix: Allow localhost HTTP for local development.
Issue #359 Unified: Use shared security_constants for localhost hosts.

This module provides:
- TaskFlowSecurityValidator: URL, path, and code_js security checks
- TaskFlowSchemaValidator: Pydantic schema validation

Security features:
- HTTPS enforcement for external URLs (localhost HTTP allowed)
- SSRF protection (block private IPs, localhost allowed for internal APIs)
- Path traversal protection
- code_js function whitelist
"""

from __future__ import annotations

import logging
import re
from typing import Any

from . import ValidationError, ValidationErrorCode, ValidationResult, WorkflowValidator
from .error_codes import TaskFlowValidationErrorCode
from .messages import get_error_message
from .security_constants import ALLOWED_LOCAL_HOSTS

logger = logging.getLogger(__name__)


class TaskFlowSecurityValidator:
    """Security validator for TaskFlow V2 workflows.

    Implements security checks:
    - HTTPS enforcement (localhost HTTP allowed for local development)
    - SSRF protection (private IP blocking, localhost allowed)
    - Path traversal protection
    - code_js function whitelist

    Issue #359 Fix: localhost/127.0.0.1 are allowed for internal API calls.
    Issue #359 Unified: Use shared ALLOWED_LOCAL_HOSTS from security_constants.
    """

    # Issue #359: Use unified local host definitions from security_constants
    ALLOWED_LOCALHOST_HOSTS = list(ALLOWED_LOCAL_HOSTS)

    # Private IP patterns for SSRF protection (excludes localhost)
    PRIVATE_IP_PATTERNS = [
        re.compile(r"^https?://10\."),
        re.compile(r"^https?://192\.168\."),
        re.compile(r"^https?://169\.254\."),
        re.compile(r"^https?://172\.(1[6-9]|2[0-9]|3[0-1])\."),
    ]

    # Allowed code_js functions (whitelist)
    ALLOWED_CODE_JS_FUNCTIONS = [
        "formatDate",
        "parseJson",
        "stringConcat",
        "arrayFilter",
        "objectMerge",
    ]

    # Path traversal pattern
    PATH_TRAVERSAL_PATTERN = re.compile(r"\.\./|\.\.\\")

    def validate_url(self, url: str) -> ValidationResult:
        """Validate URL for security requirements.

        Checks:
        1. HTTPS protocol required for external URLs
        2. HTTP allowed for localhost/127.0.0.1 (internal APIs)
        3. No private IP addresses (except localhost)

        Issue #359 Fix: Allow localhost HTTP for local development.

        Args:
            url: URL to validate

        Returns:
            ValidationResult with any security errors
        """
        errors: list[ValidationError] = []

        # Skip variable references (e.g., ${env.EXPERTAGENT_BASE_URL})
        if url.startswith("${"):
            return ValidationResult.success()

        # Check if URL is localhost (allowed for HTTP)
        is_localhost = self._is_localhost_url(url)

        # Check HTTPS (required for non-localhost URLs)
        if url.startswith("http://") and not is_localhost:
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.VALIDATION_FAILED,
                    message=f"[{TaskFlowValidationErrorCode.HTTP_NOT_ALLOWED.value}] "
                    + get_error_message(
                        TaskFlowValidationErrorCode.HTTP_NOT_ALLOWED,
                        url=url[:100],
                    ),
                    location="url",
                    suggestion="Change http:// to https:// for external URLs. "
                    "HTTP is only allowed for localhost.",
                    severity="critical",
                )
            )
            return ValidationResult.failure(errors)

        # Check for private IPs (SSRF protection) - localhost is already allowed
        for pattern in self.PRIVATE_IP_PATTERNS:
            if pattern.match(url):
                code = TaskFlowValidationErrorCode.PRIVATE_IP_NOT_ALLOWED
                errors.append(
                    ValidationError(
                        code=ValidationErrorCode.VALIDATION_FAILED,
                        message=f"[{code.value}] " + get_error_message(code, url=url[:100]),
                        location="url",
                        suggestion="Use a public URL instead of private network addresses",
                        severity="critical",
                    )
                )
                break

        if errors:
            return ValidationResult.failure(errors)

        return ValidationResult.success()

    def _is_localhost_url(self, url: str) -> bool:
        """Check if URL is a localhost URL.

        Args:
            url: URL to check

        Returns:
            True if URL points to localhost
        """
        url_lower = url.lower()
        for host in self.ALLOWED_LOCALHOST_HOSTS:
            if f"://{host}" in url_lower or f"://{host}:" in url_lower:
                return True
        return False

    def validate_code_js_function(self, function_name: str) -> ValidationResult:
        """Validate code_js function is in whitelist.

        Only pre-approved functions are allowed for security.

        Args:
            function_name: Name of the function to validate

        Returns:
            ValidationResult with any security errors
        """
        if function_name in self.ALLOWED_CODE_JS_FUNCTIONS:
            return ValidationResult.success()

        return ValidationResult.failure(
            [
                ValidationError(
                    code=ValidationErrorCode.VALIDATION_FAILED,
                    message=f"[{TaskFlowValidationErrorCode.CODE_JS_FUNCTION_NOT_ALLOWED.value}] "
                    + get_error_message(
                        TaskFlowValidationErrorCode.CODE_JS_FUNCTION_NOT_ALLOWED,
                        function_name=function_name,
                        allowed_list=", ".join(self.ALLOWED_CODE_JS_FUNCTIONS),
                    ),
                    location="code_js.function_name",
                    suggestion=f"Use one of: {', '.join(self.ALLOWED_CODE_JS_FUNCTIONS)}",
                    severity="critical",
                )
            ]
        )

    def validate_path(self, path: str) -> ValidationResult:
        """Validate path for path traversal attacks.

        Args:
            path: File path to validate

        Returns:
            ValidationResult with any security errors
        """
        if self.PATH_TRAVERSAL_PATTERN.search(path):
            return ValidationResult.failure(
                [
                    ValidationError(
                        code=ValidationErrorCode.VALIDATION_FAILED,
                        message=f"[{TaskFlowValidationErrorCode.PATH_TRAVERSAL_DETECTED.value}] "
                        + get_error_message(
                            TaskFlowValidationErrorCode.PATH_TRAVERSAL_DETECTED,
                            path=path[:100],
                        ),
                        location="path",
                        suggestion="Remove '..' from path",
                        severity="critical",
                    )
                ]
            )

        return ValidationResult.success()


class TaskFlowSchemaValidator(WorkflowValidator):
    """Schema validator for TaskFlow V2 workflows.

    Validates:
    - Workflow structure against Pydantic schema
    - Security requirements via TaskFlowSecurityValidator
    """

    def __init__(self) -> None:
        """Initialize with security validator."""
        self.security_validator = TaskFlowSecurityValidator()

    def validate(self, workflow: dict[str, Any]) -> list[ValidationError]:
        """Validate TaskFlow workflow.

        Args:
            workflow: Workflow dictionary to validate

        Returns:
            List of validation errors (empty if valid)
        """
        errors: list[ValidationError] = []

        # Check for required fields
        if "steps" not in workflow:
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.VALIDATION_FAILED,
                    message=f"[{TaskFlowValidationErrorCode.MISSING_STEPS.value}] "
                    + get_error_message(TaskFlowValidationErrorCode.MISSING_STEPS),
                    location="workflow",
                    suggestion="Add at least one step to the workflow",
                    severity="critical",
                )
            )
            return errors

        if not workflow.get("steps"):
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.VALIDATION_FAILED,
                    message=f"[{TaskFlowValidationErrorCode.MISSING_STEPS.value}] "
                    + get_error_message(TaskFlowValidationErrorCode.MISSING_STEPS),
                    location="workflow.steps",
                    suggestion="Add at least one step to the workflow",
                    severity="critical",
                )
            )
            return errors

        # Validate each step
        for i, step in enumerate(workflow.get("steps", [])):
            step_errors = self._validate_step(step, f"steps[{i}]")
            errors.extend(step_errors)

        return errors

    def _validate_step(
        self,
        step: dict[str, Any],
        location: str,
    ) -> list[ValidationError]:
        """Validate a single step.

        Args:
            step: Step dictionary
            location: Location string for error messages

        Returns:
            List of validation errors
        """
        errors: list[ValidationError] = []

        # Handle parallel blocks
        if "parallel" in step:
            for j, parallel_step in enumerate(step.get("parallel", [])):
                errors.extend(
                    self._validate_step(parallel_step, f"{location}.parallel[{j}]")
                )
            return errors

        # Handle conditional blocks
        if "condition" in step:
            for j, true_step in enumerate(step.get("if_true", [])):
                errors.extend(
                    self._validate_step(true_step, f"{location}.if_true[{j}]")
                )
            for j, false_step in enumerate(step.get("if_false", [])):
                errors.extend(
                    self._validate_step(false_step, f"{location}.if_false[{j}]")
                )
            return errors

        step_type = step.get("type")
        config = step.get("config", {})

        # Validate api_rest steps
        if step_type == "api_rest":
            url = config.get("url", "")
            if url:
                url_result = self.security_validator.validate_url(url)
                if not url_result.is_valid:
                    for err in url_result.errors:
                        err.location = f"{location}.config.url"
                        errors.append(err)

        # Validate code_js steps
        elif step_type == "code_js":
            function_name = config.get("function_name", "")
            if function_name:
                func_result = self.security_validator.validate_code_js_function(
                    function_name
                )
                if not func_result.is_valid:
                    for err in func_result.errors:
                        err.location = f"{location}.config.function_name"
                        errors.append(err)

            path = config.get("path", "")
            if path:
                path_result = self.security_validator.validate_path(path)
                if not path_result.is_valid:
                    for err in path_result.errors:
                        err.location = f"{location}.config.path"
                        errors.append(err)

        return errors


__all__ = [
    "TaskFlowSecurityValidator",
    "TaskFlowSchemaValidator",
]
