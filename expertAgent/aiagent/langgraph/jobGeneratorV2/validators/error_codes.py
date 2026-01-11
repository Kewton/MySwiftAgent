"""Error codes for TaskFlow validation.

Issue #350 Task 3.2: Error code taxonomy.

This module provides:
- ValidationErrorCode enum with error codes
- Error code categories:
  - E1xxx: Schema errors
  - E2xxx: Security errors
  - E3xxx: Reference errors
"""

from __future__ import annotations

from enum import Enum


class TaskFlowValidationErrorCode(str, Enum):
    """Validation error codes for TaskFlow V2.

    Error code categories:
    - E1xxx: Schema errors (structure, type, format)
    - E2xxx: Security errors (HTTPS, SSRF, code_js)
    - E3xxx: Reference errors (variable refs, step refs)
    """

    # Schema errors (E1xxx)
    INVALID_STEP_ID = "E1001"
    INVALID_WORKFLOW_NAME = "E1002"
    MISSING_REQUIRED_FIELD = "E1003"
    INVALID_STEP_TYPE = "E1004"
    INVALID_CONFIG_FOR_TYPE = "E1005"
    MISSING_STEPS = "E1006"
    INVALID_TIMEOUT_RANGE = "E1007"
    INVALID_HTTP_METHOD = "E1008"
    MISSING_TRANSFORM_FIELD = "E1009"

    # Security errors (E2xxx)
    HTTP_NOT_ALLOWED = "E2001"
    PRIVATE_IP_NOT_ALLOWED = "E2002"
    PATH_TRAVERSAL_DETECTED = "E2003"
    CODE_JS_FUNCTION_NOT_ALLOWED = "E2004"
    LOCALHOST_NOT_ALLOWED = "E2005"

    # Reference errors (E3xxx)
    INVALID_VARIABLE_REFERENCE = "E3001"
    CIRCULAR_REFERENCE_DETECTED = "E3002"
    UNDEFINED_STEP_REFERENCE = "E3003"
    INVALID_OUTPUT_MAPPING = "E3004"


__all__ = ["TaskFlowValidationErrorCode"]
