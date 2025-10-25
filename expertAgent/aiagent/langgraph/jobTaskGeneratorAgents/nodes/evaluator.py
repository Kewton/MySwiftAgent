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
import os

from ..prompts.evaluation import (
    EVALUATION_SYSTEM_PROMPT,
    EvaluationResult,
    create_evaluation_prompt,
)
from ..state import JobTaskGeneratorState
from ..utils.llm_factory import create_llm_with_fallback

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
    logger.info("=" * 80)
    logger.info("Starting evaluator node")
    logger.info("=" * 80)

    user_requirement = state["user_requirement"]
    task_breakdown = state.get("task_breakdown", [])
    interface_definitions = state.get("interface_definitions", [])
    evaluator_stage = state.get("evaluator_stage", "after_task_breakdown")
    retry_count = state.get("retry_count", 0)

    logger.info(f"📍 Evaluator stage: {evaluator_stage}")
    logger.info(f"📊 Task breakdown count: {len(task_breakdown)}")
    logger.info(f"📋 Interface definitions count: {len(interface_definitions)}")
    logger.info(f"🔄 Retry count: {retry_count}")
    logger.debug(f"State keys present: {list(state.keys())}")

    if not task_breakdown:
        logger.error("Task breakdown is empty")
        return {
            **state,
            "evaluation_result": None,
            "error_message": "Task breakdown is required for evaluation",
        }

    # Initialize LLM with fallback mechanism (Issue #111)
    max_tokens = int(os.getenv("JOB_GENERATOR_MAX_TOKENS", "8192"))
    model_name = os.getenv("JOB_GENERATOR_EVALUATOR_MODEL", "claude-haiku-4-5")
    model, perf_tracker, cost_tracker = create_llm_with_fallback(
        model_name=model_name,
        temperature=0.0,
        max_tokens=max_tokens,
    )
    logger.debug(f"Using model={model_name}, max_tokens={max_tokens}")

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
            logger.warning(f"Found {len(response.infeasible_tasks)} infeasible tasks:")
            for task in response.infeasible_tasks:
                logger.warning(f"  - {task.task_name} ({task.task_id}): {task.reason}")

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

        # Generate evaluation feedback for retry improvement
        evaluation_feedback = None
        if not response.is_valid:
            feedback_parts = []

            # Add quality scores feedback
            feedback_parts.append("## 品質スコア")
            feedback_parts.append(f"- 階層的分解: {response.hierarchical_score}/10")
            feedback_parts.append(f"- 依存関係の明確性: {response.dependency_score}/10")
            feedback_parts.append(
                f"- 具体性と実行可能性: {response.specificity_score}/10"
            )
            feedback_parts.append(
                f"- モジュール性と再利用性: {response.modularity_score}/10"
            )
            feedback_parts.append(f"- 全体的一貫性: {response.consistency_score}/10")

            # Add improvement suggestions
            if response.improvement_suggestions:
                feedback_parts.append("\n## 改善提案")
                for suggestion in response.improvement_suggestions:
                    feedback_parts.append(f"- {suggestion}")

            # Add infeasible tasks information
            if response.infeasible_tasks:
                feedback_parts.append("\n## 実現不可能なタスク")
                for task in response.infeasible_tasks:
                    feedback_parts.append(
                        f"- {task.task_name} ({task.task_id}): {task.reason}"
                    )

            # Add alternative proposals
            if response.alternative_proposals:
                feedback_parts.append("\n## 代替案の提案")
                for proposal in response.alternative_proposals:
                    feedback_parts.append(
                        f"- {proposal.task_id}: {proposal.api_to_use}を使用 - {proposal.implementation_note}"
                    )

            evaluation_feedback = "\n".join(feedback_parts)
            logger.debug(f"Generated evaluation feedback:\n{evaluation_feedback}")

        # Update state
        logger.info("=" * 80)
        logger.info("✅ Evaluator node completed successfully")
        logger.info(f"📊 Returning evaluation result: is_valid={response.is_valid}")
        logger.info("🔄 Retry count reset to: 0")
        logger.info(f"📍 Evaluator stage unchanged: {evaluator_stage}")
        logger.info("=" * 80)

        return {
            **state,
            "evaluation_result": response.model_dump(),
            "evaluation_feedback": evaluation_feedback,
            "retry_count": 0,
        }

    except Exception as e:
        logger.error(f"Failed to invoke LLM for evaluation: {e}")
        return {
            **state,
            "error_message": f"Evaluation failed: {str(e)}",
        }
