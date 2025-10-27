"""Requirement analysis node for job task generator.

This module provides the requirement analysis node that decomposes user
requirements into executable tasks following 4 principles:
1. Hierarchical decomposition
2. Clear dependencies
3. Specificity and executability
4. Modularity and reusability
"""

import logging

from ..prompts.task_breakdown import (
    TASK_BREAKDOWN_SYSTEM_PROMPT,
    TaskBreakdownItem,
    TaskBreakdownResponse,
    create_task_breakdown_prompt,
    create_task_breakdown_prompt_with_feedback,
)
from ..state import JobTaskGeneratorState
from ..utils.llm_invocation import StructuredLLMError, invoke_structured_llm

logger = logging.getLogger(__name__)

# Priority constraint constants (Issue #111)
MIN_PRIORITY = 1
MAX_PRIORITY = 10


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

    logger.debug("User requirement: %s", user_requirement)
    if evaluation_feedback:
        logger.debug("Evaluation feedback detected for requirement analysis")

    if evaluation_feedback:
        user_prompt = create_task_breakdown_prompt_with_feedback(
            user_requirement,
            evaluation_feedback,
        )
    else:
        user_prompt = create_task_breakdown_prompt(user_requirement)

    messages = [
        {"role": "system", "content": TASK_BREAKDOWN_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        call_result = await invoke_structured_llm(
            messages=messages,
            response_model=TaskBreakdownResponse,
            context_label="requirement_analysis",
            model_env_var="JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL",
            default_model="claude-haiku-4-5",
            validator=_validate_task_breakdown_response,
        )
    except StructuredLLMError as exc:
        logger.error("Task breakdown failed: %s", exc)
        return {**state, "error_message": str(exc)}

    response = call_result.result
    logger.info(
        "Task breakdown produced %s tasks (model=%s)",
        len(response.tasks),
        call_result.model_name,
    )
    if call_result.recovered_via_json:
        logger.info("Task breakdown succeeded via JSON fallback")

    logger.debug("Tasks: %s", [task.name for task in response.tasks])

    response.tasks = _clip_task_priorities(response.tasks)

    retry_seed = state.get("retry_count", 0)
    updated_retry = retry_seed + 1 if retry_seed > 0 else 0

    return {
        **state,
        "task_breakdown": [task.model_dump() for task in response.tasks],
        "overall_summary": response.overall_summary,
        "evaluator_stage": "after_task_breakdown",
        "retry_count": updated_retry,
    }
