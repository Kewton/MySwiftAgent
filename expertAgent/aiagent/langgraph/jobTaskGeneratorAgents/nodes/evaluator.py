"""Evaluator node for job task generator.

This node evaluates task breakdown quality and feasibility. When the primary
structured output call fails, it attempts JSON recovery using shared
utilities so we can stay on the same LLM.
"""

from __future__ import annotations

import logging

from ..prompts.evaluation import (
    EVALUATION_SYSTEM_PROMPT,
    EvaluationResult,
    create_evaluation_prompt,
)
from ..state import JobTaskGeneratorState
from ..utils.llm_invocation import StructuredLLMError, invoke_structured_llm

logger = logging.getLogger(__name__)


def _validate_evaluation_response(
    response: EvaluationResult | None,
) -> EvaluationResult:
    """Validate that the LLM response contains a usable evaluation result."""

    if response is None:
        logger.error("LLM structured output returned None for evaluator")
        raise ValueError(
            "Evaluation failed: LLM returned None response. "
            "This may indicate structured output parsing failure."
        )

    if response.evaluation_summary is None:
        logger.error(
            "LLM structured output missing 'evaluation_summary' field",
        )
        raise ValueError(
            "Evaluation failed: LLM response missing 'evaluation_summary'. "
            "This may indicate the structured schema was not followed."
        )

    return response


async def evaluator_node(
    state: JobTaskGeneratorState,
) -> JobTaskGeneratorState:
    """Evaluate task breakdown quality and feasibility."""

    job_id = state.get("job_id") or state.get("jobId")
    if job_id:
        logger.info("Starting evaluator node (job_id=%s)", job_id)
    else:
        logger.info("Starting evaluator node")

    user_requirement = state.get("user_requirement")
    task_breakdown = state.get("task_breakdown", [])
    raw_interface_defs = state.get("interface_definitions", {})
    interface_definitions = (
        raw_interface_defs if isinstance(raw_interface_defs, dict) else {}
    )
    evaluator_stage = state.get("evaluator_stage", "after_task_breakdown")
    retry_count = state.get("retry_count", 0)

    logger.info(
        "Evaluator context: stage=%s retry=%s tasks=%s interfaces=%s",
        evaluator_stage,
        retry_count,
        len(task_breakdown),
        len(interface_definitions),
    )

    if not user_requirement:
        message = "Evaluation failed: missing user requirement in state"
        logger.error(message)
        return {**state, "error_message": message}

    if not task_breakdown:
        message = "Evaluation requires a task breakdown"
        logger.error(message)
        return {**state, "evaluation_result": None, "error_message": message}

    if evaluator_stage == "after_interface_definition" and not interface_definitions:
        logger.warning("Evaluator running without interface definitions")

    user_prompt = create_evaluation_prompt(user_requirement, task_breakdown)

    messages = [
        {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        call_result = await invoke_structured_llm(
            messages=messages,
            response_model=EvaluationResult,
            context_label="evaluator",
            model_env_var="JOB_GENERATOR_EVALUATOR_MODEL",
            default_model="claude-haiku-4-5",
            validator=_validate_evaluation_response,
        )
    except StructuredLLMError as exc:
        logger.error("Evaluation failed: %s", exc)
        return {**state, "error_message": str(exc)}
    except Exception as exc:
        logger.error("Unexpected evaluation error: %s", exc, exc_info=True)
        return {**state, "error_message": f"Evaluation failed: {exc}"}

    response = call_result.result
    logger.info(
        "Evaluation complete (model=%s is_valid=%s)",
        call_result.model_name,
        response.is_valid,
    )
    if call_result.recovered_via_json:
        logger.info("Evaluation succeeded via JSON fallback")

    logger.debug(
        "Evaluation scores: hierarchy=%s dependency=%s specificity=%s "
        "modularity=%s consistency=%s",
        response.hierarchical_score,
        response.dependency_score,
        response.specificity_score,
        response.modularity_score,
        response.consistency_score,
    )
    logger.debug(
        "Evaluation feasibility summary: feasible=%s infeasible=%s "
        "alternative=%s api_extension=%s",
        response.all_tasks_feasible,
        len(response.infeasible_tasks),
        len(response.alternative_proposals),
        len(response.api_extension_proposals),
    )

    if response.infeasible_tasks:
        logger.warning(
            "Infeasible tasks detected: %s",
            len(response.infeasible_tasks),
        )
        for task in response.infeasible_tasks:
            logger.warning(
                "Infeasible task %s (%s): %s",
                task.task_name,
                task.task_id,
                task.reason,
            )

    if response.alternative_proposals:
        logger.info(
            "Alternative proposals detected: %s",
            len(response.alternative_proposals),
        )
        for proposal in response.alternative_proposals:
            logger.info(
                "Alternative proposal %s → %s",
                proposal.task_id,
                proposal.api_to_use,
            )

    if response.api_extension_proposals:
        logger.info(
            "API extension proposals detected: %s",
            len(response.api_extension_proposals),
        )
        for api_proposal in response.api_extension_proposals:
            logger.info(
                "API extension proposal %s (priority=%s)",
                api_proposal.proposed_api_name,
                api_proposal.priority,
            )

    evaluation_feedback = None
    if not response.is_valid:
        feedback_parts: list[str] = []
        feedback_parts.append("## 品質スコア")
        feedback_parts.append(f"- 階層的分解: {response.hierarchical_score}/10")
        feedback_parts.append(f"- 依存関係の明確性: {response.dependency_score}/10")
        feedback_parts.append(f"- 具体性と実行可能性: {response.specificity_score}/10")
        feedback_parts.append(
            f"- モジュール性と再利用性: {response.modularity_score}/10"
        )
        feedback_parts.append(f"- 全体的一貫性: {response.consistency_score}/10")

        if response.improvement_suggestions:
            feedback_parts.append("\n## 改善提案")
            for suggestion in response.improvement_suggestions:
                feedback_parts.append(f"- {suggestion}")

        if response.infeasible_tasks:
            feedback_parts.append("\n## 実現不可能なタスク")
            for task in response.infeasible_tasks:
                feedback_parts.append(
                    f"- {task.task_name} ({task.task_id}): {task.reason}"
                )

        if response.alternative_proposals:
            feedback_parts.append("\n## 代替案の提案")
            for proposal in response.alternative_proposals:
                feedback_parts.append(
                    f"- {proposal.task_id}: {proposal.api_to_use}を使用 - "
                    f"{proposal.implementation_note}"
                )

        evaluation_feedback = "\n".join(feedback_parts)
        logger.debug("Generated evaluation feedback:\n%s", evaluation_feedback)

    # NOTE: Do not modify retry_count here - it's managed by requirement_analysis/interface_definition nodes
    return {
        **state,
        "evaluation_result": response.model_dump(),
        "evaluation_feedback": evaluation_feedback,
    }
