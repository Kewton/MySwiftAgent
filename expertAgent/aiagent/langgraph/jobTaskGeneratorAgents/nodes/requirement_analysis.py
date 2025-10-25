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
from typing import cast

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
                f"Task {task.task_id} priority {original_priority} < {min_priority}, "
                f"clipped to {min_priority}"
            )
        elif task.priority > max_priority:
            task.priority = max_priority
            logger.warning(
                f"Task {task.task_id} priority {original_priority} > {max_priority}, "
                f"clipped to {max_priority}"
            )
    return tasks


async def requirement_analysis_node(
    state: JobTaskGeneratorState,
) -> JobTaskGeneratorState:
    """Analyze user requirements and decompose into tasks.

    Args:
        state: Current job task generator state

    Returns:
        Updated state with task breakdown
    """
    logger.info("Starting requirement analysis node")

    user_requirement = state["user_requirement"]
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
    model, perf_tracker, cost_tracker = create_llm_with_fallback(
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

    try:
        # Invoke LLM
        messages = [
            {"role": "system", "content": TASK_BREAKDOWN_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        logger.info("Invoking LLM for task breakdown")
        response = cast(
            TaskBreakdownResponse | None, await structured_model.ainvoke(messages)
        )

        # Validate LLM response: check if tasks is not None and not empty
        if response is None:
            logger.error("LLM response is None - structured output parsing failed")
            raise ValueError(
                "Task breakdown failed: LLM returned None response. "
                "This may indicate structured output parsing failure."
            )

        if response.tasks is None:
            logger.error(
                "LLM response.tasks is None - structured output missing 'tasks' field"
            )
            raise ValueError(
                "Task breakdown failed: LLM response missing 'tasks' field. "
                "This may indicate LLM did not follow the structured output schema."
            )

        if not response.tasks:
            logger.error("LLM response.tasks is empty - no tasks generated")
            raise ValueError(
                "Task breakdown failed: LLM returned empty task list. "
                "User requirement may be too vague or ambiguous."
            )

        logger.info(f"Task breakdown completed: {len(response.tasks)} tasks")
        logger.debug(f"Tasks: {[task.name for task in response.tasks]}")

        # Post-processing: Clip priorities to valid range (Issue #111)
        # This prevents validation errors when LLM violates priority constraints
        response.tasks = _clip_task_priorities(response.tasks)

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

    except Exception as e:
        logger.error(f"Failed to invoke LLM for task breakdown: {e}")
        return {
            **state,
            "error_message": f"Task breakdown failed: {str(e)}",
        }
