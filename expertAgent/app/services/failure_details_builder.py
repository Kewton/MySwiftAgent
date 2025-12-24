"""FailureDetails Builder for workflow generation summary.

Issue #305 Extension: Task Workflow Traces Summary feature.

This module provides functions to build FailureDetails from workflow
generation state data. It transforms raw state data into structured
failure information for UI display without requiring additional LLM calls.

Design principles:
- Rule-based failure stage determination (no LLM needed)
- Reuse existing data from validator_node, workflow_tester, llm_evaluator
- Low latency (<10ms) transformation
- Graceful handling of missing fields
"""

import logging
import re
from typing import Any, Optional

from app.services.job_creation_state import FailureDetails

logger = logging.getLogger(__name__)

# Failure stage priority order (top = highest priority)
FAILURE_STAGE_PRIORITY = [
    "yaml_generation",
    "schema_validation",
    "workflow_registration",
    "workflow_execution",
    "node_error",
    "output_validation",
    "quality_evaluation",
]

# Error HTTP status codes that indicate workflow execution failure
HTTP_ERROR_STATUS_CODES = {400, 401, 403, 404, 422, 500, 502, 503, 504}

# Quality evaluation threshold
QUALITY_SCORE_THRESHOLD = 70


def determine_failure_stage(state: dict[str, Any]) -> str:
    """Determine the failure stage from state data.

    Evaluates conditions in priority order and returns the first matching stage.

    Priority order:
    1. yaml_generation - YAML content is empty or None
    2. schema_validation - Input validation failed
    3. workflow_registration - Registration HTTP error (not implemented)
    4. workflow_execution - Test HTTP status indicates error
    5. node_error - [graphai] category in validation_errors
    6. output_validation - [output] category in validation_errors
    7. quality_evaluation - Score below threshold or is_acceptable is False

    Args:
        state: Workflow generation state dictionary

    Returns:
        Failure stage string matching FailureDetails.failure_stage values
    """
    # 1. Check yaml_generation failure
    yaml_content = state.get("yaml_content")
    if not yaml_content or (
        isinstance(yaml_content, str) and yaml_content.strip() == ""
    ):
        return "yaml_generation"

    # 2. Check schema_validation failure
    validation_result = state.get("validation_result", {})
    if isinstance(validation_result, dict):
        input_validation = validation_result.get("input_validation", {})
        if (
            isinstance(input_validation, dict)
            and input_validation.get("is_valid") is False
        ):
            return "schema_validation"

    # 3. Check workflow_execution failure (HTTP error status)
    test_http_status = state.get("test_http_status")
    if test_http_status and test_http_status in HTTP_ERROR_STATUS_CODES:
        return "workflow_execution"

    # 4. Check node_error from validation_errors
    validation_errors = state.get("validation_errors", []) or []
    for error in validation_errors:
        if isinstance(error, str) and "[graphai]" in error.lower():
            return "node_error"

    # 5. Check output_validation from validation_errors
    for error in validation_errors:
        if isinstance(error, str) and "[output]" in error.lower():
            return "output_validation"

    # 6. Check quality_evaluation failure
    evaluation_score = state.get("evaluation_score")
    is_acceptable = state.get("is_acceptable")

    if evaluation_score is not None and evaluation_score < QUALITY_SCORE_THRESHOLD:
        return "quality_evaluation"

    if is_acceptable is False:
        return "quality_evaluation"

    # Default to workflow_execution for unknown failures
    return "workflow_execution"


def extract_error_code(error_message: Optional[str]) -> Optional[str]:
    """Extract error code from error message.

    Supports various error code formats:
    - HTTP status with code: "HTTP 400: INVALID_PARAMETER - ..."
    - Bracketed code: "Error: [ERR_001] Something..."
    - Colon-separated: "INVALID_PARAM: Description..."

    Args:
        error_message: Error message string

    Returns:
        Extracted error code or None if not found
    """
    if not error_message:
        return None

    # Pattern 1: HTTP status with code (e.g., "HTTP 400: INVALID_PARAMETER - ...")
    http_match = re.search(r"HTTP\s*\d+:\s*(\w+)\s*-", error_message, re.IGNORECASE)
    if http_match:
        return http_match.group(1)

    # Pattern 2: Bracketed code (e.g., "[ERR_001]")
    bracket_match = re.search(r"\[([A-Z_0-9]+)\]", error_message)
    if bracket_match:
        return bracket_match.group(1)

    # Pattern 3: Error code at start (e.g., "INVALID_PARAM: Description")
    code_match = re.match(r"^([A-Z][A-Z_0-9]+):", error_message)
    if code_match:
        return code_match.group(1)

    return None


def extract_error_detail(
    validation_errors: Optional[list[str]],
) -> Optional[str]:
    """Extract detailed error information from validation errors.

    Combines all validation error messages into a single detail string.

    Args:
        validation_errors: List of validation error strings

    Returns:
        Combined error detail string or None if empty
    """
    if not validation_errors:
        return None

    # Filter out empty strings and combine
    details = [e for e in validation_errors if e and isinstance(e, str)]
    if not details:
        return None

    return "; ".join(details)


def extract_cause_from_validation_errors(
    validation_errors: Optional[list[str]],
) -> Optional[dict[str, Any]]:
    """Extract cause analysis from categorized validation errors.

    Parses validation errors that follow the format:
    [category] Error description with optional field info

    Supported categories: input, output, graphai, api

    Args:
        validation_errors: List of validation error strings

    Returns:
        Cause analysis dict or None if no categorized errors found
    """
    if not validation_errors:
        return None

    # Category detection pattern
    category_pattern = re.compile(r"^\[(\w+)\]\s*(.+)$", re.IGNORECASE)

    for error in validation_errors:
        if not isinstance(error, str):
            continue

        match = category_pattern.match(error)
        if match:
            category = match.group(1).lower()
            description = match.group(2)

            cause: dict[str, Any] = {
                "category": category,
            }

            # Try to extract field information
            field_match = re.search(
                r"(?:field|parameter|property)[\s:]+([a-zA-Z0-9_.]+)",
                description,
                re.IGNORECASE,
            )
            if field_match:
                cause["problem_field"] = field_match.group(1)

            # Try to extract actual/expected values
            actual_match = re.search(
                r"(?:got|received|actual)[\s:]+['\"]?([^'\"]+)['\"]?",
                description,
                re.IGNORECASE,
            )
            if actual_match:
                cause["actual_value"] = actual_match.group(1).strip()

            expected_match = re.search(
                r"(?:expected|should be)[\s:]+['\"]?([^'\"]+)['\"]?",
                description,
                re.IGNORECASE,
            )
            if expected_match:
                cause["expected_value"] = expected_match.group(1).strip()

            # Try to extract location (node name, line number)
            location_match = re.search(
                r"(?:node|at|in)[\s:]+['\"]?([a-zA-Z0-9_]+)['\"]?",
                description,
                re.IGNORECASE,
            )
            if location_match:
                cause["problem_location"] = location_match.group(1)

            return cause

    return None


def format_repair_history(
    repair_history: Optional[list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Format repair history for UI display.

    Standardizes the repair history format to match FailureDetails schema.

    Args:
        repair_history: Raw repair history from state

    Returns:
        Formatted list of retry history entries
    """
    if not repair_history:
        return []

    formatted: list[dict[str, Any]] = []
    for entry in repair_history:
        if not isinstance(entry, dict):
            continue

        formatted_entry: dict[str, Any] = {
            "attempt": entry.get("attempt", len(formatted) + 1),
            "error_message": entry.get(
                "error", entry.get("error_message", "Unknown error")
            ),
            "model_used": entry.get("model", entry.get("model_used")),
            "timestamp": entry.get("timestamp"),
        }
        formatted.append(formatted_entry)

    return formatted


def generate_default_recommendations(failure_stage: str) -> list[str]:
    """Generate default recommendations for a failure stage.

    Provides stage-specific guidance when no LLM suggestions are available.

    Args:
        failure_stage: The determined failure stage

    Returns:
        List of recommendation strings
    """
    recommendations_map: dict[str, list[str]] = {
        "yaml_generation": [
            "Review the task description for clarity",
            "Try regenerating the workflow with a different model",
            "Check if the task requirements are well-defined",
        ],
        "schema_validation": [
            "Verify the test data matches the input schema",
            "Check for missing required fields in test data",
            "Review the interface definition for type constraints",
        ],
        "workflow_registration": [
            "Check graphAiServer connectivity",
            "Verify the workflow YAML syntax",
            "Retry registration after server is available",
        ],
        "workflow_execution": [
            "Check API parameters and authentication",
            "Verify external service availability",
            "Review the error message for specific fixes",
        ],
        "node_error": [
            "Check individual node configurations",
            "Increase timeout settings if needed",
            "Verify node agent availability",
        ],
        "output_validation": [
            "Review the output schema requirements",
            "Check if the workflow produces expected output format",
            "Adjust node configurations for correct output",
        ],
        "quality_evaluation": [
            "Review the workflow structure for improvements",
            "Enhance error handling in the workflow",
            "Consider adding more comprehensive test data",
        ],
    }

    return recommendations_map.get(
        failure_stage,
        ["Review the error details and try again"],
    )


def build_failure_details(state: dict[str, Any]) -> Optional[FailureDetails]:
    """Build FailureDetails from workflow generation state.

    This is the main entry point that transforms raw state data into
    structured FailureDetails for UI display.

    Args:
        state: Workflow generation state dictionary containing:
            - status: Job status ('success' | 'failed')
            - yaml_content: Generated YAML content
            - test_http_status: HTTP status from test execution
            - error_message: Error message if failed
            - validation_errors: List of validation errors
            - validation_result: Validation result with input_validation
            - evaluation_score: LLM evaluation score (0-100)
            - is_acceptable: Whether quality is acceptable
            - evaluation_suggestions: LLM suggestions
            - repair_history: History of repair attempts

    Returns:
        FailureDetails instance or None if status is 'success'
    """
    # Return None for successful workflows
    if state.get("status") == "success":
        return None

    # 1. Determine failure stage
    failure_stage = determine_failure_stage(state)

    # 2. Build error summary
    error_message = state.get("error_message", "Unknown error")
    error_summary: dict[str, Any] = {
        "http_status": state.get("test_http_status"),
        "error_code": extract_error_code(error_message),
        "error_message": error_message if error_message else "Unknown error",
        "error_detail": extract_error_detail(state.get("validation_errors")),
    }

    # 3. Extract cause analysis from validation errors
    cause_analysis = extract_cause_from_validation_errors(
        state.get("validation_errors", [])
    )

    # 4. Get recommendations (prefer LLM suggestions, fallback to defaults)
    evaluation_suggestions = state.get("evaluation_suggestions", [])
    if evaluation_suggestions:
        recommendations = evaluation_suggestions
    else:
        recommendations = generate_default_recommendations(failure_stage)

    # 5. Format retry history
    retry_history = format_repair_history(state.get("repair_history"))

    return FailureDetails(
        failure_stage=failure_stage,
        error_summary=error_summary,
        cause_analysis=cause_analysis,
        recommendations=recommendations,
        retry_history=retry_history,
    )
