"""LLM Evaluator node for semantic workflow quality assessment.

This module provides the LLM Evaluator node that performs semantic
evaluation of generated workflows including test data quality assessment.
"""

import logging
from datetime import datetime

from ..models.evaluation import LLMEvaluationResult
from ..prompts.llm_evaluation import (
    LLM_EVALUATION_SYSTEM_PROMPT,
    create_llm_evaluation_prompt,
)
from ..state import WorkflowGeneratorState
from ..utils import convert_sample_input_to_dict_or_str

logger = logging.getLogger(__name__)


async def _call_llm_evaluator(
    prompt: str,
    model_name: str = "gpt-4o-mini",
) -> LLMEvaluationResult | None:
    """Call LLM to evaluate workflow.

    Args:
        prompt: Evaluation prompt
        model_name: Model to use for evaluation

    Returns:
        LLMEvaluationResult or None on failure
    """
    try:
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
            invoke_structured_llm,
        )

        messages = [
            {"role": "system", "content": LLM_EVALUATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        result: StructuredCallResult[LLMEvaluationResult] = await invoke_structured_llm(
            messages=messages,
            response_model=LLMEvaluationResult,
            context_label="llm_evaluator",
            model_env_var="LLM_EVALUATOR_MODEL",
            default_model=model_name,
        )

        if result and result.result:
            evaluation = result.result
            evaluation.evaluation_model = result.model_name or model_name
            evaluation.evaluation_timestamp = datetime.now().isoformat()
            return evaluation
        return None
    except Exception as e:
        logger.warning(f"LLM evaluation failed: {e}")
        return None


def _create_fallback_evaluation(
    state: WorkflowGeneratorState,
) -> LLMEvaluationResult:
    """Create fallback evaluation when LLM call fails.

    Uses rule-based validation results to generate a conservative evaluation.

    Args:
        state: Current workflow generator state

    Returns:
        Fallback LLMEvaluationResult
    """
    is_valid = state.get("is_valid", False)
    validation_errors = state.get("validation_errors", [])

    # Conservative scoring based on rule-based validation
    base_score = 70 if is_valid else 40

    return LLMEvaluationResult(
        overall_score=base_score,
        structural_score=base_score + 5 if is_valid else 50,
        requirement_score=base_score if is_valid else 40,
        output_quality_score=base_score - 5 if is_valid else 35,
        error_handling_score=50,  # Conservative default
        test_data_quality_score=60,  # Conservative default
        test_data_issues=[],
        needs_test_data_regeneration=False,
        suggested_test_data=None,
        strengths=["Rule-based validation passed"] if is_valid else [],
        weaknesses=validation_errors[:3] if validation_errors else [],
        suggestions=["Manual review recommended due to LLM evaluation failure"],
        is_acceptable=is_valid,
        failure_reason="none" if is_valid else "workflow_quality",
        confidence=0.5,  # Low confidence for fallback
        evaluation_model="fallback",
        evaluation_timestamp=datetime.now().isoformat(),
    )


def _format_feedback(evaluation: LLMEvaluationResult) -> str:
    """Format evaluation result into human-readable feedback.

    Args:
        evaluation: LLM evaluation result

    Returns:
        Formatted feedback string
    """
    lines = [
        f"Overall Score: {evaluation.overall_score}/100",
        f"- Structural: {evaluation.structural_score}",
        f"- Requirements: {evaluation.requirement_score}",
        f"- Output Quality: {evaluation.output_quality_score}",
        f"- Error Handling: {evaluation.error_handling_score}",
        f"- Test Data Quality: {evaluation.test_data_quality_score}",
        "",
    ]

    if evaluation.strengths:
        lines.append("Strengths:")
        for strength in evaluation.strengths:
            lines.append(f"  - {strength}")

    if evaluation.weaknesses:
        lines.append("Weaknesses:")
        for weakness in evaluation.weaknesses:
            lines.append(f"  - {weakness}")

    if evaluation.suggestions:
        lines.append("Suggestions:")
        for suggestion in evaluation.suggestions:
            lines.append(f"  - {suggestion}")

    return "\n".join(lines)


async def llm_evaluator_node(
    state: WorkflowGeneratorState,
) -> WorkflowGeneratorState:
    """LLM-based workflow quality evaluation node.

    Evaluates the generated workflow across multiple dimensions:
    - Structural validity
    - Requirement fulfillment
    - Output quality
    - Error handling
    - Test data quality

    Issue #340: Also checks for object_array_issues and triggers
    test data regeneration if object array errors are detected.

    Args:
        state: Current workflow generator state

    Returns:
        Updated state with LLM evaluation results
    """
    logger.info("Starting LLM evaluator node")

    # Issue #340: Check for object array issues before LLM evaluation
    object_array_issues = state.get("object_array_issues", [])
    has_object_array_errors = state.get("has_object_array_errors", False)

    if has_object_array_errors and object_array_issues:
        logger.warning(
            f"Issue #340: {len(object_array_issues)} object array issues detected, "
            "triggering test data regeneration"
        )
        return {
            **state,
            "needs_test_data_regeneration": True,
            "llm_evaluation_result": {
                "failure_reason": "test_data_quality",
                "details": f"{len(object_array_issues)} object array issues detected",
                "object_array_issues": object_array_issues,
            },
        }

    # Extract required data
    task_data = state.get("task_data", {})
    yaml_content = state.get("yaml_content", "")
    raw_sample_input = state.get("sample_input")
    sample_input = convert_sample_input_to_dict_or_str(raw_sample_input)
    execution_result = state.get("test_execution_result")
    validation_result = state.get("validation_result") or {}

    # Build evaluation prompt
    input_interface = task_data.get("input_interface", {})
    output_interface = task_data.get("output_interface", {})

    prompt = create_llm_evaluation_prompt(
        task_name=task_data.get("name", "Unknown"),
        task_description=task_data.get("description", ""),
        input_schema=input_interface.get("schema", {}),
        output_schema=output_interface.get("schema", {}),
        recommended_apis=task_data.get("recommended_apis", []),
        yaml_content=yaml_content,
        sample_input=sample_input,
        execution_result=execution_result,
        rule_based_issues=validation_result.get("issues", []),
        is_regenerated_test_data=state.get("test_data_regeneration_count", 0) > 0,
        test_data_regeneration_count=state.get("test_data_regeneration_count", 0),
    )

    # Call LLM evaluator
    evaluation_result: LLMEvaluationResult | None = None
    try:
        evaluation_result = await _call_llm_evaluator(prompt)
    except Exception as e:
        logger.warning(f"LLM evaluator error: {e}")

    # Use fallback if LLM call failed
    if evaluation_result is None:
        logger.warning("LLM evaluation failed, using fallback")
        evaluation_result = _create_fallback_evaluation(state)

    # Determine if test data regeneration is needed
    max_regen = state.get("max_test_data_regeneration", 2)
    current_regen_count = state.get("test_data_regeneration_count", 0)
    needs_regeneration = (
        evaluation_result.needs_test_data_regeneration
        and current_regen_count < max_regen
    )

    # Determine acceptability (considering test data quality)
    is_acceptable = (
        evaluation_result.overall_score >= 70
        and evaluation_result.requirement_score >= 60
        and evaluation_result.test_data_quality_score >= 50
        and not needs_regeneration
    )

    # Combine with existing is_valid status
    final_is_valid = state.get("is_valid", False) and is_acceptable

    logger.info(
        f"LLM evaluation complete: score={evaluation_result.overall_score}, "
        f"is_acceptable={is_acceptable}, needs_regeneration={needs_regeneration}"
    )

    return {
        **state,
        "llm_evaluation_result": evaluation_result.model_dump(),
        "evaluation_score": evaluation_result.overall_score,
        "evaluation_feedback": _format_feedback(evaluation_result),
        "evaluation_suggestions": evaluation_result.suggestions,
        "test_data_quality_score": evaluation_result.test_data_quality_score,
        "test_data_issues": evaluation_result.test_data_issues,
        "needs_test_data_regeneration": needs_regeneration,
        "suggested_test_data": evaluation_result.suggested_test_data,
        "is_valid": final_is_valid,
    }
