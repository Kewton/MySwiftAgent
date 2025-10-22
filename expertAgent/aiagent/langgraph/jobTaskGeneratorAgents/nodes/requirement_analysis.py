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

from ..prompts.task_breakdown import (
    TASK_BREAKDOWN_SYSTEM_PROMPT,
    TaskBreakdownResponse,
    create_task_breakdown_prompt,
    create_task_breakdown_prompt_with_feedback,
)
from ..state import JobTaskGeneratorState
from ..utils.llm_factory import create_llm_with_fallback

logger = logging.getLogger(__name__)


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
        response = await structured_model.ainvoke(messages)

        logger.info(f"Task breakdown completed: {len(response.tasks)} tasks")
        logger.debug(f"Tasks: {[task.name for task in response.tasks]}")

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
