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
    1. Extracts validation errors from state
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
    retry_count = state.get("retry_count", 0)
    workflow_name = state.get("workflow_name", "unknown")

    logger.debug(f"Validation errors count: {len(validation_errors)}")
    logger.debug(f"Current retry count: {retry_count}")

    # Create error feedback message for LLM
    error_feedback_lines = [
        f"Workflow '{workflow_name}' failed validation with the following errors:",
        "",
    ]

    for i, error in enumerate(validation_errors, 1):
        error_feedback_lines.append(f"{i}. {error}")

    error_feedback_lines.extend(
        [
            "",
            "Please regenerate the workflow addressing ALL of the above errors.",
            "Ensure:",
            "- YAML syntax is 100% correct",
            "- All agent names exist in available_agents list",
            "- Data flow (:references) are correct",
            "- HTTP API calls use fetchAgent with correct URL/method/body",
            "- Final output node has isResult: true",
        ]
    )

    error_feedback = "\n".join(error_feedback_lines)

    logger.info("Created error feedback for LLM regeneration")
    logger.debug(f"Error feedback:\n{error_feedback}")

    # Record repair attempt in history
    repair_history = state.get("repair_history", [])
    repair_history.append(
        {
            "retry_count": retry_count + 1,
            "errors": validation_errors,
            "workflow_name": workflow_name,
        }
    )

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
