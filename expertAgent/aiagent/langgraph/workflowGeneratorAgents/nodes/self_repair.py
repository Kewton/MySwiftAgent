"""Self-repair node for workflow error feedback and retry preparation.

This module provides the self-repair node that analyzes validation errors,
creates error feedback for LLM, and prepares for workflow regeneration.
"""

import logging

from ..state import WorkflowGeneratorState

logger = logging.getLogger(__name__)


async def self_repair_node(
    state: WorkflowGeneratorState,
) -> WorkflowGeneratorState:
    """Analyze validation errors and prepare error feedback for LLM.

    This node:
    1. Extracts validation errors from state (including schema validation - Issue #333)
    2. Creates detailed error feedback for LLM regeneration
    3. Increments retry_count
    4. Records repair attempt in repair_history

    Args:
        state: Current workflow generator state

    Returns:
        Updated state with error_feedback and incremented retry_count
    """
    logger.info("Starting self-repair node")

    validation_errors = state.get("validation_errors", [])
    validation_result = state.get("validation_result") or {}
    issues = (
        validation_result.get("issues") if isinstance(validation_result, dict) else []
    )
    if not validation_errors and isinstance(issues, list):
        validation_errors = [
            f"[{item.get('category', 'unknown')}] {item.get('message', '')}"
            for item in issues
            if isinstance(item, dict)
        ]

    # Issue #333: Include schema validation issues
    schema_validation_issues = state.get("schema_validation_issues", [])
    if isinstance(schema_validation_issues, list):
        for issue in schema_validation_issues:
            if isinstance(issue, dict) and issue.get("severity") == "error":
                issue_type = issue.get("issue_type", "unknown")
                message = issue.get("message", "")
                suggestion = issue.get("suggestion", "")
                error_text = f"[schema:{issue_type}] {message}"
                if suggestion:
                    error_text += f" (Suggestion: {suggestion})"
                validation_errors.append(error_text)

    retry_count = state.get("retry_count", 0)
    workflow_name = state.get("workflow_name", "unknown")

    logger.debug(f"Validation errors count: {len(validation_errors)}")
    logger.debug(f"Current retry count: {retry_count}")

    # Create error feedback message for LLM
    last_model = state.get("generation_model")

    error_feedback_lines = [
        f"Workflow '{workflow_name}' failed validation with these errors:",
        "",
    ]

    if last_model:
        error_feedback_lines.append(f"Last generation model: {last_model}")
        error_feedback_lines.append("")

    for i, error in enumerate(validation_errors, 1):
        error_feedback_lines.append(f"{i}. {error}")

    # Issue #333: Add schema validation guidance if schema errors exist
    has_schema_errors = state.get("has_schema_errors", False)
    schema_guidance = []
    if has_schema_errors:
        schema_guidance = [
            "",
            "SCHEMA VALIDATION ERRORS DETECTED (Issue #333):",
            "- Type mismatch: user_input expects String, not Object reference",
            "- Use stringTemplateAgent to convert Object to String before passing to API",
            "- Use correct field names: 'system_prompt' (not 'system_imput')",
            "- Access specific fields with :node.field syntax instead of :node",
        ]

    error_feedback_lines.extend(
        [
            "",
            "Please regenerate the workflow and resolve every issue listed.",
            "Ensure:",
            "- YAML syntax is 100% correct",
            "- All agent names exist in available_agents list",
            "- Data flow (:references) are correct",
            "- HTTP API calls use fetchAgent with correct URL/method/body",
            "- Final output node has isResult: true",
        ]
        + schema_guidance
    )

    error_feedback = "\n".join(error_feedback_lines)

    logger.info("Created error feedback for LLM regeneration")
    logger.debug(f"Error feedback:\n{error_feedback}")

    # Record repair attempt in history
    repair_history = state.get("repair_history", [])
    if not isinstance(repair_history, list):
        repair_history = []
    history_entry = {
        "retry_count": retry_count + 1,
        "errors": validation_errors,
        "workflow_name": workflow_name,
    }
    if isinstance(issues, list):
        history_entry["issues"] = issues
    if last_model:
        history_entry["generation_model"] = last_model

    repair_history.append(history_entry)

    # Determine status based on retry count
    max_retry = state.get("max_retry", 3)
    new_retry_count = retry_count + 1

    if new_retry_count >= max_retry:
        status = "max_retries_exceeded"
        logger.warning(f"Max retries reached: {new_retry_count}/{max_retry}")
    else:
        status = "ready_for_retry"
        logger.info(f"Preparing for retry {new_retry_count}/{max_retry}")

    # Update state
    return {
        **state,
        "error_feedback": error_feedback,
        "retry_count": new_retry_count,
        "repair_history": repair_history,
        "status": status,
    }
