"""Evaluator node for job task generator.

This module provides the evaluator node that evaluates task breakdown quality
according to 6 principles:
1-4. Four principles (hierarchical, dependencies, specificity, modularity)
5. Overall consistency
6. Feasibility (implementable with GraphAI + expertAgent Direct API)

The node also detects infeasible tasks, proposes alternatives, and suggests
API extensions when necessary.
"""

import logging
from typing import cast

from langchain_anthropic import ChatAnthropic

from ..prompts.evaluation import (
    EVALUATION_SYSTEM_PROMPT,
    EvaluationResult,
    create_evaluation_prompt,
)
from ..state import JobTaskGeneratorState

logger = logging.getLogger(__name__)


async def evaluator_node(
    state: JobTaskGeneratorState,
) -> JobTaskGeneratorState:
    """Evaluate task breakdown quality and feasibility.

    This node evaluates the task breakdown result according to 6 principles:
    1. Hierarchical decomposition (1-10 points)
    2. Dependency clarity (1-10 points)
    3. Specificity and executability (1-10 points)
    4. Modularity and reusability (1-10 points)
    5. Overall consistency (1-10 points)
    6. Feasibility with GraphAI + expertAgent Direct API

    For infeasible tasks, the node:
    - Proposes alternatives using existing APIs
    - Suggests API extensions with priority (high/medium/low)

    Args:
        state: Current job task generator state

    Returns:
        Updated state with evaluation results
    """
    logger.info("Starting evaluator node")

    user_requirement = state["user_requirement"]
    task_breakdown = state.get("task_breakdown", [])
    evaluator_stage = state.get("evaluator_stage", "after_task_breakdown")

    logger.debug(f"Evaluator stage: {evaluator_stage}")
    logger.debug(f"Task breakdown count: {len(task_breakdown)}")

    if not task_breakdown:
        logger.error("Task breakdown is empty")
        return {
            **state,
            "evaluation_result": None,
            "error_message": "Task breakdown is required for evaluation",
        }

    # Initialize LLM (claude-haiku-4-5)
    model = ChatAnthropic(
        model="claude-haiku-4-5",
        temperature=0.0,
    )

    # Create structured output model
    structured_model = model.with_structured_output(EvaluationResult)

    # Create evaluation prompt
    user_prompt = create_evaluation_prompt(user_requirement, task_breakdown)
    logger.debug(f"Created evaluation prompt (length: {len(user_prompt)})")

    try:
        # Invoke LLM
        messages = [
            {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        logger.info("Invoking LLM for evaluation")
        response = await structured_model.ainvoke(messages)

        logger.info(f"Evaluation completed: is_valid={response.is_valid}")
        logger.info(
            f"Scores: hierarchical={response.hierarchical_score}, "
            f"dependency={response.dependency_score}, "
            f"specificity={response.specificity_score}, "
            f"modularity={response.modularity_score}, "
            f"consistency={response.consistency_score}"
        )
        logger.info(
            f"Feasibility: all_tasks_feasible={response.all_tasks_feasible}, "
            f"infeasible_tasks={len(response.infeasible_tasks)}, "
            f"alternative_proposals={len(response.alternative_proposals)}, "
            f"api_extension_proposals={len(response.api_extension_proposals)}"
        )

        # Log infeasible tasks and proposals
        if response.infeasible_tasks:
            logger.warning(
                f"Found {len(response.infeasible_tasks)} infeasible tasks:"
            )
            for task in response.infeasible_tasks:
                logger.warning(
                    f"  - {task.task_name} ({task.task_id}): {task.reason}"
                )

        if response.alternative_proposals:
            logger.info(
                f"Found {len(response.alternative_proposals)} alternative proposals:"
            )
            for proposal in response.alternative_proposals:
                logger.info(
                    f"  - {proposal.task_id}: Use {proposal.api_to_use} instead"
                )

        if response.api_extension_proposals:
            logger.info(
                f"Found {len(response.api_extension_proposals)} API extension proposals:"
            )
            for proposal in response.api_extension_proposals:
                logger.info(
                    f"  - {proposal.proposed_api_name} ({proposal.priority} priority)"
                )

        # Update state
        return {
            **state,
            "evaluation_result": response.model_dump(),
            "retry_count": 0,
        }

    except Exception as e:
        logger.error(f"Failed to invoke LLM for evaluation: {e}")
        return {
            **state,
            "error_message": f"Evaluation failed: {str(e)}",
        }
