"""Requirement analysis node for job task generator.

This module provides the requirement analysis node that decomposes user
requirements into executable tasks following 4 principles:
1. Hierarchical decomposition
2. Clear dependencies
3. Specificity and executability
4. Modularity and reusability
"""

import logging

from langchain_anthropic import ChatAnthropic

from ..prompts.task_breakdown import (
    TASK_BREAKDOWN_SYSTEM_PROMPT,
    TaskBreakdownResponse,
    create_task_breakdown_prompt,
)
from ..state import JobTaskGeneratorState

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
    logger.debug(f"User requirement: {user_requirement}")

    # Initialize LLM (claude-haiku-4-5)
    model = ChatAnthropic(
        model="claude-haiku-4-5",
        temperature=0.0,
        max_tokens=4096,  # Increased from default 1024 to handle complex task breakdowns
    )

    # Create structured output model
    structured_model = model.with_structured_output(TaskBreakdownResponse)

    # Create prompt
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
