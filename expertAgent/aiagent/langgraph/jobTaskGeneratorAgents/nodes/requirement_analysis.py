"""Requirement analysis node for job task generator.

This module provides the requirement analysis node that decomposes user
requirements into executable tasks following 4 principles:
1. Hierarchical decomposition
2. Clear dependencies
3. Specificity and executability
4. Modularity and reusability
"""

import logging
import os
from typing import Any, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from pydantic import ValidationError

from app.utils.json_converter import force_to_json_response, to_parse_json

from ..prompts.task_breakdown import (
    TASK_BREAKDOWN_SYSTEM_PROMPT,
    TaskBreakdownItem,
    TaskBreakdownResponse,
    create_task_breakdown_prompt,
    create_task_breakdown_prompt_with_feedback,
)
from ..state import JobTaskGeneratorState
from ..utils.llm_factory import create_llm_with_fallback

logger = logging.getLogger(__name__)

# Priority constraint constants (Issue #111)
MIN_PRIORITY = 1
MAX_PRIORITY = 10

# Truncate raw LLM preview to avoid flooding logs on failure investigations
RAW_LOG_PREVIEW_CHARS = 2000


def _extract_message_text(message: Any) -> str | None:
    """Safely extract human-readable text from various LLM message shapes."""

    if message is None:
        return None

    if isinstance(message, str):
        return message

    content: Any = None
    if isinstance(message, BaseMessage):
        content = message.content
        if isinstance(content, str):
            return content
    else:
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
            else:
                text_attr = getattr(item, "text", None)
                if text_attr:
                    parts.append(str(text_attr))
        if parts:
            return "\n".join(parts)

    additional_kwargs = getattr(message, "additional_kwargs", None)
    if isinstance(additional_kwargs, dict):
        # Capture tool/function call payloads when available
        for key in ("tool_calls", "function_call"):
            payload = additional_kwargs.get(key)
            if payload:
                return str(payload)

    return str(message)


def _log_raw_text_preview(
    raw_text: str,
    context: str,
    max_chars: int = RAW_LOG_PREVIEW_CHARS,
) -> None:
    """Log a truncated preview of captured raw LLM response text."""

    preview = raw_text[:max_chars]
    truncated = "yes" if len(raw_text) > max_chars else "no"
    logger.error(
        "Raw LLM response preview for %s (len=%d, truncated=%s): %s",
        context,
        len(raw_text),
        truncated,
        preview,
    )


async def _attempt_task_breakdown_recovery(
    model: BaseChatModel,
    messages: list[dict[str, str]],
) -> tuple[TaskBreakdownResponse | None, str | None, Exception | None]:
    """Attempt to recover structured output via JSON utilities."""

    try:
        raw_response = await model.ainvoke(messages)
    except Exception as raw_error:  # pragma: no cover - diagnostic helper
        logger.exception(
            "Failed to fetch raw LLM response for requirement_analysis recovery: %s",
            raw_error,
        )
        return None, None, raw_error

    raw_text = _extract_message_text(raw_response)
    if raw_text is None:
        logger.warning(
            "Raw LLM response for requirement_analysis recovery is empty or"
            " unsupported type: %s",
            type(raw_response).__name__,
        )
        return None, None, ValueError("Empty raw LLM response")

    try:
        parsed_json = to_parse_json(raw_text)
    except ValueError as parse_error:
        logger.error(
            "JSON extraction failed during requirement_analysis recovery: %s",
            parse_error,
        )
        return None, raw_text, parse_error

    try:
        recovered = TaskBreakdownResponse.model_validate(parsed_json)
    except ValidationError as validation_error:
        logger.error(
            "Validation failed for requirement_analysis recovery JSON: %s",
            validation_error,
        )
        return None, raw_text, validation_error

    usage_metadata = getattr(raw_response, "usage_metadata", None)
    if usage_metadata:
        logger.info(
            "LLM usage metadata for requirement_analysis recovery: %s",
            usage_metadata,
        )

    logger.info(
        "Recovered task breakdown via JSON fallback: %s tasks",
        len(recovered.tasks),
    )
    return recovered, raw_text, None


def _clip_task_priorities(
    tasks: list[TaskBreakdownItem],
    min_priority: int = MIN_PRIORITY,
    max_priority: int = MAX_PRIORITY,
) -> list[TaskBreakdownItem]:
    """Clip task priorities to valid range.

    This is a safety mechanism to ensure LLM-generated priorities stay within
    the valid range [min_priority, max_priority]. LLMs may occasionally violate
    Pydantic constraints in the prompt.

    Args:
        tasks: List of TaskBreakdownItem from LLM response
        min_priority: Minimum valid priority (default: 1)
        max_priority: Maximum valid priority (default: 10)

    Returns:
        Tasks with clipped priorities
    """
    for task in tasks:
        original_priority = task.priority
        if task.priority < min_priority:
            task.priority = min_priority
            logger.warning(
                "Task %s priority %s < %s, clipped to %s",
                task.task_id,
                original_priority,
                min_priority,
                min_priority,
            )
        elif task.priority > max_priority:
            task.priority = max_priority
            logger.warning(
                "Task %s priority %s > %s, clipped to %s",
                task.task_id,
                original_priority,
                max_priority,
                max_priority,
            )
    return tasks


def _validate_task_breakdown_response(
    response: TaskBreakdownResponse | None,
) -> TaskBreakdownResponse:
    """Validate that the LLM response contains a usable task list."""

    if response is None:
        logger.error("LLM structured output returned None")
        raise ValueError(
            "Task breakdown failed: LLM returned None response. "
            "This may indicate structured output parsing failure."
        )

    if response.tasks is None:
        logger.error("LLM structured output missing 'tasks' field")
        raise ValueError(
            "Task breakdown failed: LLM response missing 'tasks' field. "
            "This may indicate the structured schema was not followed."
        )

    if not response.tasks:
        logger.error("LLM response.tasks is empty - no tasks generated")
        raise ValueError(
            "Task breakdown failed: LLM returned empty task list. "
            "User requirement may be too vague or ambiguous."
        )

    return response


async def requirement_analysis_node(
    state: JobTaskGeneratorState,
) -> JobTaskGeneratorState:
    """Analyze user requirements and decompose into tasks.

    Args:
        state: Current job task generator state

    Returns:
        Updated state with task breakdown
    """
    job_id = state.get("job_id") or state.get("jobId")
    if job_id:
        logger.info("Starting requirement analysis node (job_id=%s)", job_id)
    else:
        logger.info("Starting requirement analysis node")

    user_requirement = state.get("user_requirement")
    if not user_requirement:
        message = "Task breakdown failed: missing user requirement in state"
        logger.error(message)
        return {**state, "error_message": message}
    evaluation_feedback = state.get("evaluation_feedback")

    logger.debug(f"User requirement: {user_requirement}")
    if evaluation_feedback:
        logger.info("Evaluation feedback detected - using feedback-enhanced prompt")
        logger.debug(f"Feedback: {evaluation_feedback}")

    # Initialize LLM with fallback mechanism (Issue #111)
    max_tokens = int(os.getenv("JOB_GENERATOR_MAX_TOKENS", "8192"))
    model_name = os.getenv(
        "JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL", "claude-haiku-4-5"
    )
    model, perf_tracker, _cost_tracker = create_llm_with_fallback(
        model_name=model_name,
        temperature=0.0,
        max_tokens=max_tokens,
    )
    logger.debug(f"Using model={model_name}, max_tokens={max_tokens}")

    # Create structured output model
    structured_model = model.with_structured_output(TaskBreakdownResponse)

    # Create prompt (with feedback if available)
    if evaluation_feedback:
        user_prompt = create_task_breakdown_prompt_with_feedback(
            user_requirement, evaluation_feedback
        )
    else:
        user_prompt = create_task_breakdown_prompt(user_requirement)

    logger.debug(f"Created task breakdown prompt (length: {len(user_prompt)})")

    messages = [
        {"role": "system", "content": TASK_BREAKDOWN_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    perf_tracker.start()

    response: TaskBreakdownResponse | None = None
    primary_error: Exception | None = None

    try:
        # Invoke LLM and validate structured output
        logger.info("Invoking LLM for task breakdown")
        structured_response = cast(
            TaskBreakdownResponse | None,
            await structured_model.ainvoke(messages),
        )
        response = _validate_task_breakdown_response(structured_response)
    except Exception as err:
        primary_error = err
        response = None

    recovered_via_json = False
    raw_text: str | None = None
    recovery_error: Exception | None = None

    if response is None:
        (
            recovered_response,
            raw_text,
            recovery_error,
        ) = await _attempt_task_breakdown_recovery(model, messages)
        if recovered_response is not None:
            try:
                response = _validate_task_breakdown_response(recovered_response)
                recovered_via_json = True
            except Exception as validation_error:
                recovery_error = validation_error
                response = None

    if response is None:
        failure_context = (
            f"requirement_analysis failure (job_id={job_id})"
            if job_id
            else "requirement_analysis failure"
        )
        failure_error = (
            recovery_error
            or primary_error
            or ValueError("Unknown task breakdown failure")
        )

        perf_tracker.end(success=False, error=str(failure_error))
        perf_tracker.log_metrics()

        if raw_text:
            _log_raw_text_preview(raw_text, failure_context)
            sanitized = force_to_json_response(
                raw_text,
                error_context=failure_context,
                error_detail=str(failure_error),
            )
            logger.debug(
                "Sanitized task breakdown failure payload: %s",
                sanitized,
            )

        logger.error(
            "Failed to invoke LLM for task breakdown: %s",
            failure_error,
        )
        return {
            **state,
            "error_message": f"Task breakdown failed: {str(failure_error)}",
        }

    logger.info(
        "Task breakdown completed: %s tasks",
        len(response.tasks),
    )
    if recovered_via_json:
        logger.info("Task breakdown completed via JSON fallback")

    logger.debug(f"Tasks: {[task.name for task in response.tasks]}")

    # Post-processing: Clip priorities to valid range (Issue #111)
    # This guards against LLM priority values outside the supported range
    response.tasks = _clip_task_priorities(response.tasks)

    perf_tracker.end(success=True)
    perf_tracker.log_metrics()

    # Update state
    return {
        **state,
        "task_breakdown": [task.model_dump() for task in response.tasks],
        "overall_summary": response.overall_summary,
        "evaluator_stage": "after_task_breakdown",
        "retry_count": state.get("retry_count", 0) + 1
        if state.get("retry_count", 0) > 0
        else 0,
    }
