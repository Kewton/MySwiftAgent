"""Error message catalog for TaskFlow validation.

Issue #350 Task 3.3: Internationalized error messages.

This module provides:
- ERROR_MESSAGES: Localized error message templates
- get_error_message: Function to get localized error message
"""

from __future__ import annotations

from typing import Any

from ..error_codes import TaskFlowValidationErrorCode

# Error message templates by locale
ERROR_MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        # Schema errors
        TaskFlowValidationErrorCode.INVALID_STEP_ID.value: (
            "Invalid step ID format: '{step_id}'. "
            "Must match pattern: ^[a-zA-Z_][a-zA-Z0-9_-]*$"
        ),
        TaskFlowValidationErrorCode.INVALID_WORKFLOW_NAME.value: (
            "Invalid workflow name: '{workflow_name}'. "
            "Must match pattern: ^[a-zA-Z_][a-zA-Z0-9_-]*$"
        ),
        TaskFlowValidationErrorCode.MISSING_REQUIRED_FIELD.value: (
            "Missing required field: '{field}' in {location}"
        ),
        TaskFlowValidationErrorCode.INVALID_STEP_TYPE.value: (
            "Invalid step type: '{step_type}'. "
            "Must be one of: api_rest, transform, code_js"
        ),
        TaskFlowValidationErrorCode.INVALID_CONFIG_FOR_TYPE.value: (
            "Invalid config for step type '{step_type}': {details}"
        ),
        TaskFlowValidationErrorCode.MISSING_STEPS.value: (
            "Workflow must have at least one step"
        ),
        TaskFlowValidationErrorCode.INVALID_TIMEOUT_RANGE.value: (
            "Timeout must be between 1000ms and 300000ms. Got: {timeout_ms}ms"
        ),
        TaskFlowValidationErrorCode.INVALID_HTTP_METHOD.value: (
            "Invalid HTTP method: '{method}'. "
            "Must be one of: GET, POST, PUT, DELETE, PATCH"
        ),
        TaskFlowValidationErrorCode.MISSING_TRANSFORM_FIELD.value: (
            "Missing required field for transform mode '{mode}': {field}"
        ),
        # Security errors
        TaskFlowValidationErrorCode.HTTP_NOT_ALLOWED.value: (
            "HTTP protocol is not allowed. Use HTTPS instead: {url}"
        ),
        TaskFlowValidationErrorCode.PRIVATE_IP_NOT_ALLOWED.value: (
            "Private IP addresses are not allowed (SSRF protection): {url}"
        ),
        TaskFlowValidationErrorCode.PATH_TRAVERSAL_DETECTED.value: (
            "Path traversal detected in path: {path}"
        ),
        TaskFlowValidationErrorCode.CODE_JS_FUNCTION_NOT_ALLOWED.value: (
            "Function '{function_name}' is not in the allowed list. "
            "Allowed: {allowed_list}"
        ),
        TaskFlowValidationErrorCode.LOCALHOST_NOT_ALLOWED.value: (
            "Localhost URLs are not allowed (SSRF protection): {url}"
        ),
        # Reference errors
        TaskFlowValidationErrorCode.INVALID_VARIABLE_REFERENCE.value: (
            "Invalid variable reference: '{reference}'"
        ),
        TaskFlowValidationErrorCode.CIRCULAR_REFERENCE_DETECTED.value: (
            "Circular reference detected: {chain}"
        ),
        TaskFlowValidationErrorCode.UNDEFINED_STEP_REFERENCE.value: (
            "Reference to undefined step: '{step_id}'"
        ),
        TaskFlowValidationErrorCode.INVALID_OUTPUT_MAPPING.value: (
            "Invalid output mapping: '{mapping}'"
        ),
    },
    "ja": {
        # Schema errors
        TaskFlowValidationErrorCode.INVALID_STEP_ID.value: (
            "ステップIDの形式が不正です: '{step_id}'。"
            "パターン: ^[a-zA-Z_][a-zA-Z0-9_-]*$"
        ),
        TaskFlowValidationErrorCode.INVALID_WORKFLOW_NAME.value: (
            "ワークフロー名が不正です: '{workflow_name}'。"
            "パターン: ^[a-zA-Z_][a-zA-Z0-9_-]*$"
        ),
        TaskFlowValidationErrorCode.MISSING_REQUIRED_FIELD.value: (
            "必須フィールドがありません: '{field}' ({location})"
        ),
        TaskFlowValidationErrorCode.MISSING_STEPS.value: (
            "ワークフローには少なくとも1つのステップが必要です"
        ),
        # Security errors
        TaskFlowValidationErrorCode.HTTP_NOT_ALLOWED.value: (
            "HTTPプロトコルは許可されていません。HTTPSを使用してください: {url}"
        ),
        TaskFlowValidationErrorCode.PRIVATE_IP_NOT_ALLOWED.value: (
            "プライベートIPアドレスは許可されていません(SSRF対策): {url}"
        ),
        TaskFlowValidationErrorCode.PATH_TRAVERSAL_DETECTED.value: (
            "パストラバーサルが検出されました: {path}"
        ),
        TaskFlowValidationErrorCode.CODE_JS_FUNCTION_NOT_ALLOWED.value: (
            "関数 '{function_name}' は許可リストにありません。許可: {allowed_list}"
        ),
    },
}


def get_error_message(
    code: TaskFlowValidationErrorCode | str,
    locale: str = "en",
    **params: Any,
) -> str:
    """Get localized error message for an error code.

    Args:
        code: Error code (enum or string value)
        locale: Locale code ('en', 'ja')
        **params: Parameters to format into the message template

    Returns:
        Formatted error message string
    """
    code_value = code.value if isinstance(code, TaskFlowValidationErrorCode) else code
    messages = ERROR_MESSAGES.get(locale, ERROR_MESSAGES["en"])
    template = messages.get(code_value, f"Unknown error: {code_value}")

    try:
        return template.format(**params)
    except KeyError:
        # If formatting fails, return template as-is
        return template


__all__ = ["ERROR_MESSAGES", "get_error_message"]
