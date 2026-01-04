"""Evaluator node for job task generator.

This node evaluates task breakdown quality and feasibility. When the primary
structured output call fails, it attempts JSON recovery using shared
utilities so we can stay on the same LLM.
"""

from __future__ import annotations

import logging

from ..prompts.evaluation import (
    API_SPECIFICITY_CHECK_SYSTEM_PROMPT,
    EVALUATION_SYSTEM_PROMPT,
    APISpecificityCheckResult,
    EvaluationResult,
    create_api_specificity_check_prompt,
    create_evaluation_prompt,
)
from ..state import JobTaskGeneratorState
from ..utils.llm_invocation import StructuredLLMError, invoke_structured_llm

logger = logging.getLogger(__name__)

# Maximum number of retries before giving up on API specificity improvements
# Must match the value in agent.py
MAX_RETRY_COUNT = 5


def check_interface_compatibility(tasks: list[dict]) -> list[str]:
    """Check output/input interface compatibility across task chain.

    Issue #338 Phase 4: This function validates that the output_interface
    of task N provides all required fields for input_interface of task N+1.

    Args:
        tasks: List of task definitions with input_interface and output_interface

    Returns:
        List of warnings about missing required fields
    """
    warnings: list[str] = []

    if len(tasks) < 2:
        return warnings

    for i in range(len(tasks) - 1):
        current_task = tasks[i]
        next_task = tasks[i + 1]

        # Get output_interface from current task
        output_interface = current_task.get("output_interface", {})
        output_properties = output_interface.get("properties", {})
        output_fields = set(output_properties.keys())

        # Get input_interface from next task
        input_interface = next_task.get("input_interface", {})
        required_fields = input_interface.get("required", [])

        # Check if all required fields from next task input are provided
        # by current task output
        missing_fields = [
            field for field in required_fields if field not in output_fields
        ]

        if missing_fields:
            current_id = current_task.get("task_id", f"task_{i + 1}")
            next_id = next_task.get("task_id", f"task_{i + 2}")
            current_name = current_task.get("name", current_id)
            next_name = next_task.get("name", next_id)

            for field in missing_fields:
                warnings.append(
                    f"Task {i + 1} ({current_name}) output does not provide "
                    f"required field '{field}' for task {i + 2} ({next_name}) input"
                )
                logger.warning(
                    f"Interface compatibility issue: {current_id} -> {next_id} "
                    f"missing field '{field}'"
                )

    return warnings


def check_derived_fields_for_downstream_tasks(
    tasks: list[dict],
    interface_definitions: dict[str, dict],
) -> list[str]:
    """Check if derived_fields are defined for downstream tasks that need them.

    When a downstream task requires pre-formatted data (e.g., email subject/body),
    the preceding task should define appropriate derived_fields in its output_schema.

    This function checks for common patterns:
    - Email/mail tasks need email_subject and email_body from preceding task
    - Slack tasks need slack_title and slack_message
    - File save tasks need filename and file_description

    Args:
        tasks: List of task breakdown items
        interface_definitions: Dict mapping task_id to interface definitions

    Returns:
        List of issues found (empty if all derived_fields are properly defined)

    Example:
        >>> tasks = [
        ...     {"task_id": "summarize", "task_type": "summarization"},
        ...     {"task_id": "send_email", "task_type": "email_send"},
        ... ]
        >>> interfaces = {
        ...     "summarize": {
        ...         "output_schema": {
        ...             "properties": {"summary": {"type": "string"}},
        ...             # Missing x-derived-fields!
        ...         }
        ...     }
        ... }
        >>> check_derived_fields_for_downstream_tasks(tasks, interfaces)
        ['Task summarize is missing email_subject for downstream email task',
         'Task summarize is missing email_body for downstream email task']
    """
    issues: list[str] = []

    for i, task in enumerate(tasks):
        task_type = task.get("task_type", "").lower()
        task_name = task.get("task_name", task.get("task_id", f"task_{i}"))

        # Check for email sending tasks
        if "email" in task_type or "mail" in task_type:
            if i > 0:
                prev_task = tasks[i - 1]
                prev_task_id = prev_task.get("task_id", "")
                prev_task_name = prev_task.get(
                    "task_name", prev_task.get("task_id", f"task_{i - 1}")
                )
                prev_interface = interface_definitions.get(prev_task_id, {})
                output_schema = prev_interface.get("output_schema", {})
                derived = output_schema.get("x-derived-fields", {})

                if "email_subject" not in derived:
                    issues.append(
                        f"Task {prev_task_name} is missing email_subject "
                        f"for downstream email task {task_name}"
                    )
                if "email_body" not in derived:
                    issues.append(
                        f"Task {prev_task_name} is missing email_body "
                        f"for downstream email task {task_name}"
                    )

        # Check for Slack notification tasks
        if "slack" in task_type:
            if i > 0:
                prev_task = tasks[i - 1]
                prev_task_id = prev_task.get("task_id", "")
                prev_task_name = prev_task.get(
                    "task_name", prev_task.get("task_id", f"task_{i - 1}")
                )
                prev_interface = interface_definitions.get(prev_task_id, {})
                output_schema = prev_interface.get("output_schema", {})
                derived = output_schema.get("x-derived-fields", {})

                if "slack_title" not in derived and "slack_message" not in derived:
                    issues.append(
                        f"Task {prev_task_name} is missing slack_title/slack_message "
                        f"for downstream Slack task {task_name}"
                    )

    return issues


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


def _validate_api_specificity_response(
    response: APISpecificityCheckResult | None,
) -> APISpecificityCheckResult:
    """Validate API specificity check response."""
    if response is None:
        logger.error("API specificity check returned None")
        raise ValueError("API specificity check failed: LLM returned None response")
    return response


async def _check_api_specificity(
    task_breakdown: list[dict],
) -> APISpecificityCheckResult | None:
    """Check if recommended_apis in task breakdown are specific enough.

    This uses LLM to evaluate whether the API specifications are concrete
    (e.g., "/v1/utility/gmail/send") rather than abstract (e.g., "fetchAgent").

    Args:
        task_breakdown: List of task breakdown items to check

    Returns:
        APISpecificityCheckResult or None if check fails
    """
    if not task_breakdown:
        return None

    user_prompt = create_api_specificity_check_prompt(task_breakdown)

    messages = [
        {"role": "system", "content": API_SPECIFICITY_CHECK_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        call_result = await invoke_structured_llm(
            messages=messages,
            response_model=APISpecificityCheckResult,
            context_label="api_specificity_check",
            model_env_var="JOB_GENERATOR_EVALUATOR_MODEL",
            default_model="claude-haiku-4-5",
            validator=_validate_api_specificity_response,
        )
        logger.info(
            "API specificity check complete (model=%s all_specific=%s issues=%d)",
            call_result.model_name,
            call_result.result.all_apis_specific,
            len(call_result.result.issues),
        )
        return call_result.result
    except StructuredLLMError as exc:
        logger.warning("API specificity check failed: %s", exc)
        return None
    except Exception as exc:
        logger.warning(
            "Unexpected error in API specificity check: %s",
            exc,
            exc_info=True,
        )
        return None


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

    # Run API specificity check for after_task_breakdown stage
    # This ensures recommended_apis are concrete (e.g., "/v1/utility/gmail/send")
    # rather than abstract (e.g., "fetchAgent")
    # Skip at max retry to allow graceful degradation - if structure is valid,
    # proceed even with abstract API names
    api_specificity_result = None
    at_max_retry = retry_count >= MAX_RETRY_COUNT
    if evaluator_stage == "after_task_breakdown" and response.is_valid:
        if at_max_retry:
            logger.warning(
                "Skipping API specificity check at max retry (%d). "
                "Proceeding with current API specifications.",
                retry_count,
            )
        else:
            logger.info("Running API specificity check for task breakdown")
            api_specificity_result = await _check_api_specificity(task_breakdown)

        if api_specificity_result and not api_specificity_result.all_apis_specific:
            logger.warning(
                "API specificity issues found: %d issues",
                len(api_specificity_result.issues),
            )
            for issue in api_specificity_result.issues:
                logger.warning(
                    "API specificity issue in %s (%s): %s → %s",
                    issue.task_name,
                    issue.task_id,
                    issue.current_api,
                    issue.recommended_api,
                )

    # Generate feedback if structure is invalid OR if there are infeasible tasks
    # OR if API specificity issues were found
    # This ensures requirement_analysis receives feedback for improvement
    evaluation_feedback = None
    has_api_specificity_issues = (
        api_specificity_result is not None
        and not api_specificity_result.all_apis_specific
    )
    needs_feedback = (
        not response.is_valid
        or not response.all_tasks_feasible
        or has_api_specificity_issues
    )
    if needs_feedback:
        feedback_parts: list[str] = []
        feedback_parts.append("## 品質スコア")
        feedback_parts.append(f"- 階層的分解: {response.hierarchical_score}/10")
        feedback_parts.append(f"- 依存関係の明確性: {response.dependency_score}/10")
        feedback_parts.append(f"- 具体性と実行可能性: {response.specificity_score}/10")
        feedback_parts.append(
            f"- モジュール性と再利用性: {response.modularity_score}/10"
        )
        feedback_parts.append(f"- 全体的一貫性: {response.consistency_score}/10")

        if response.issues:
            feedback_parts.append("\n## 検出された問題")
            for eval_issue in response.issues:
                feedback_parts.append(f"- {eval_issue}")

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

        if response.api_extension_proposals:
            feedback_parts.append("\n## API拡張提案")
            for api_proposal in response.api_extension_proposals:
                feedback_parts.append(
                    f"- {api_proposal.proposed_api_name} (優先度: {api_proposal.priority}): "
                    f"{api_proposal.functionality}"
                )

        # Add API specificity issues to feedback
        if has_api_specificity_issues and api_specificity_result:
            feedback_parts.append("\n## API具体性の問題")
            feedback_parts.append(
                "以下のタスクでAPI指定が抽象的すぎます。"
                "具体的なエンドポイントを使用してください："
            )
            for issue in api_specificity_result.issues:
                feedback_parts.append(
                    f"- **{issue.task_name}** ({issue.task_id}): "
                    f"`{issue.current_api}` → `{issue.recommended_api}`"
                )
                feedback_parts.append(f"  - 理由: {issue.recommendation_reason}")

        evaluation_feedback = "\n".join(feedback_parts)
        logger.debug("Generated evaluation feedback:\n%s", evaluation_feedback)

    # Build evaluation result with API specificity flag
    evaluation_result = response.model_dump()

    # Mark as invalid if API specificity issues were found
    # This triggers re-analysis in requirement_analysis node
    if has_api_specificity_issues:
        evaluation_result["all_apis_specific"] = False
        logger.info(
            "Marking evaluation as needing re-analysis due to API specificity issues"
        )
    else:
        evaluation_result["all_apis_specific"] = True

    # Issue #338 Phase 4: Interface compatibility check
    # Merge interface_definitions into task_breakdown and check compatibility
    interface_warnings: list[str] = []

    if len(task_breakdown) >= 2 and interface_definitions:
        try:
            # Merge interface info from interface_definitions into task_breakdown
            tasks_with_interfaces: list[dict] = []
            for task_dict in task_breakdown:
                task_id = task_dict.get("task_id")
                task_with_interface = dict(task_dict)  # Create a copy

                if task_id and task_id in interface_definitions:
                    interface_bundle = interface_definitions[task_id]
                    task_with_interface["input_interface"] = interface_bundle.get(
                        "input_schema", {}
                    )
                    task_with_interface["output_interface"] = interface_bundle.get(
                        "output_schema", {}
                    )

                tasks_with_interfaces.append(task_with_interface)

            # Run interface compatibility check
            interface_warnings = check_interface_compatibility(tasks_with_interfaces)

            if interface_warnings:
                logger.warning(
                    "Interface compatibility issues detected (%d warnings): %s",
                    len(interface_warnings),
                    interface_warnings,
                )
        except Exception as compat_error:
            logger.error(f"Interface compatibility check failed: {compat_error}")
            interface_warnings = [f"Compatibility check error: {compat_error}"]

    # NOTE: Do not modify retry_count here - it's managed by requirement_analysis/interface_definition nodes
    return {
        **state,
        "evaluation_result": evaluation_result,
        "evaluation_feedback": evaluation_feedback,
        "interface_warnings": interface_warnings,
    }
