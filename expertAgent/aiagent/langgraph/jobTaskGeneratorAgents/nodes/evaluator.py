"""Evaluator node for job task generator.

This node evaluates task breakdown quality and feasibility. When the primary
structured output call fails, it attempts JSON recovery using shared
utilities so we can stay on the same LLM.
"""

from __future__ import annotations

import logging
import os
from typing import Any, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from pydantic import ValidationError

from app.utils.json_converter import force_to_json_response, to_parse_json

from ..prompts.evaluation import (
    EVALUATION_SYSTEM_PROMPT,
    EvaluationResult,
    create_evaluation_prompt,
)
from ..state import JobTaskGeneratorState
from ..utils.llm_factory import create_llm_with_fallback

logger = logging.getLogger(__name__)

# Truncate raw LLM preview to avoid flooding logs on failure investigations
RAW_LOG_PREVIEW_CHARS = 2000


def _extract_message_text(message: Any) -> str | None:
    """Safely extract human-readable text from various LLM message shapes."""

    if message is None:
        return None

    if isinstance(message, str):
        return message

    if isinstance(message, BaseMessage):
        content = message.content
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


async def _attempt_evaluation_recovery(
    model: BaseChatModel,
    messages: list[dict[str, str]],
) -> tuple[EvaluationResult | None, str | None, Exception | None]:
    """Attempt to recover structured output via JSON utilities."""

    try:
        raw_response = await model.ainvoke(messages)
    except Exception as raw_error:  # pragma: no cover - diagnostic helper
        logger.exception(
            "Failed to fetch raw LLM response for evaluator recovery: %s",
            raw_error,
        )
        return None, None, raw_error

    raw_text = _extract_message_text(raw_response)
    if raw_text is None:
        logger.warning(
            "Raw LLM response for evaluator recovery is empty or unsupported type: %s",
            type(raw_response).__name__,
        )
        return None, None, ValueError("Empty raw LLM response")

    try:
        parsed_json = to_parse_json(raw_text)
    except ValueError as parse_error:
        logger.error(
            "JSON extraction failed during evaluator recovery: %s",
            parse_error,
        )
        return None, raw_text, parse_error

    try:
        recovered = EvaluationResult.model_validate(parsed_json)
    except ValidationError as validation_error:
        logger.error(
            "Validation failed for evaluator recovery JSON: %s",
            validation_error,
        )
        return None, raw_text, validation_error

    usage_metadata = getattr(raw_response, "usage_metadata", None)
    if usage_metadata:
        logger.info(
            "LLM usage metadata for evaluator recovery: %s",
            usage_metadata,
        )

    logger.info("Recovered evaluation via JSON fallback")
    return recovered, raw_text, None


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
        logger.error("LLM structured output missing 'evaluation_summary' field")
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
    interface_definitions = state.get("interface_definitions", [])
    evaluator_stage = state.get("evaluator_stage", "after_task_breakdown")
    retry_count = state.get("retry_count", 0)

    logger.info(f"📍 Evaluator stage: {evaluator_stage}")
    logger.info(f"📊 Task breakdown count: {len(task_breakdown)}")
    logger.info(f"📋 Interface definitions count: {len(interface_definitions)}")
    logger.info(f"🔄 Retry count: {retry_count}")
    logger.debug(f"State keys present: {list(state.keys())}")

    if not user_requirement:
        message = "Evaluation failed: missing user requirement in state"
        logger.error(message)
        return {**state, "error_message": message}

    if not task_breakdown:
        message = "Task breakdown is required for evaluation"
        logger.error(message)
        return {
            **state,
            "evaluation_result": None,
            "error_message": message,
        }

    # Initialize LLM with fallback mechanism (Issue #111)
    max_tokens = int(os.getenv("JOB_GENERATOR_MAX_TOKENS", "8192"))
    model_name = os.getenv("JOB_GENERATOR_EVALUATOR_MODEL", "claude-haiku-4-5")
    model, perf_tracker, _cost_tracker = create_llm_with_fallback(
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

    messages = [
        {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    perf_tracker.start()

    response: EvaluationResult | None = None
    primary_error: Exception | None = None

    try:
        logger.info("Invoking LLM for evaluation")
        structured_response = cast(
            EvaluationResult | None,
            await structured_model.ainvoke(messages),
        )
        response = _validate_evaluation_response(structured_response)
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
        ) = await _attempt_evaluation_recovery(model, messages)
        if recovered_response is not None:
            try:
                response = _validate_evaluation_response(recovered_response)
                recovered_via_json = True
            except Exception as validation_error:
                recovery_error = validation_error
                response = None

    if response is None:
        failure_context = (
            f"evaluator failure (job_id={job_id})" if job_id else "evaluator failure"
        )
        failure_error = (
            recovery_error or primary_error or ValueError("Unknown evaluation failure")
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
            logger.debug("Sanitized evaluation failure payload: %s", sanitized)

        logger.error("Failed to invoke LLM for evaluation: %s", failure_error)
        return {
            **state,
            "error_message": f"Evaluation failed: {str(failure_error)}",
        }

    logger.info("Evaluation completed: is_valid=%s", response.is_valid)
    if recovered_via_json:
        logger.info("Evaluation completed via JSON fallback")

    logger.info(
        "Scores: hierarchical=%s, dependency=%s, specificity=%s, "
        "modularity=%s, consistency=%s",
        response.hierarchical_score,
        response.dependency_score,
        response.specificity_score,
        response.modularity_score,
        response.consistency_score,
    )
    logger.info(
        "Feasibility: all_tasks_feasible=%s, infeasible_tasks=%s, "
        "alternative_proposals=%s, api_extension_proposals=%s",
        response.all_tasks_feasible,
        len(response.infeasible_tasks),
        len(response.alternative_proposals),
        len(response.api_extension_proposals),
    )

    if response.infeasible_tasks:
        logger.warning("Found %s infeasible tasks:", len(response.infeasible_tasks))
        for task in response.infeasible_tasks:
            logger.warning("  - %s (%s): %s", task.task_name, task.task_id, task.reason)

    if response.alternative_proposals:
        logger.info(
            "Found %s alternative proposals:", len(response.alternative_proposals)
        )
        for proposal in response.alternative_proposals:
            logger.info(
                "  - %s: Use %s instead",
                proposal.task_id,
                proposal.api_to_use,
            )

    if response.api_extension_proposals:
        logger.info(
            "Found %s API extension proposals:", len(response.api_extension_proposals)
        )
        for proposal in response.api_extension_proposals:
            logger.info(
                "  - %s (%s priority)",
                proposal.proposed_api_name,
                proposal.priority,
            )

    evaluation_feedback = None
    if not response.is_valid:
        feedback_parts = []

        # Add quality scores feedback
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

    perf_tracker.end(success=True)
    perf_tracker.log_metrics()

    logger.info("✅ Evaluator node completed successfully")
    logger.info("📊 Returning evaluation result: is_valid=%s", response.is_valid)
    logger.info("🔄 Retry count reset to: 0")
    logger.info("📍 Evaluator stage unchanged: %s", evaluator_stage)

    return {
        **state,
        "evaluation_result": response.model_dump(),
        "evaluation_feedback": evaluation_feedback,
        "retry_count": 0,
    }
