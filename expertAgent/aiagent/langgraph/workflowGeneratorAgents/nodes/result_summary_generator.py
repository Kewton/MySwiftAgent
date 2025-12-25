"""Result Summary Generator node for creating validation summaries.

This module provides the Result Summary Generator node that creates
comprehensive Markdown summaries of validation and evaluation results.
"""

import logging
from datetime import datetime
from typing import Literal

from ..models.summary import (
    LLMEvaluationSummary,
    RuleBasedValidationSummary,
    TestDataEvaluationSummary,
    ValidationSummary,
)
from ..state import WorkflowGeneratorState

logger = logging.getLogger(__name__)


def _create_rule_based_summary(
    state: WorkflowGeneratorState,
) -> RuleBasedValidationSummary:
    """Create rule-based validation summary from state.

    Args:
        state: Current workflow generator state

    Returns:
        RuleBasedValidationSummary
    """
    validation_errors = state.get("validation_errors", [])
    http_status = state.get("test_http_status")

    # Determine individual validation statuses
    yaml_valid = not any("yaml" in err.lower() for err in validation_errors)
    http_valid = http_status == 200
    graphai_valid = not any(
        "graphai" in err.lower() or "node" in err.lower() for err in validation_errors
    )
    output_valid = not any("output" in err.lower() for err in validation_errors)

    return RuleBasedValidationSummary(
        yaml_syntax_valid=yaml_valid,
        http_status_valid=http_valid,
        graphai_execution_valid=graphai_valid,
        output_schema_valid=output_valid,
        issues=validation_errors,
    )


def _create_llm_evaluation_summary(
    state: WorkflowGeneratorState,
) -> LLMEvaluationSummary:
    """Create LLM evaluation summary from state.

    Args:
        state: Current workflow generator state

    Returns:
        LLMEvaluationSummary
    """
    llm_result = state.get("llm_evaluation_result") or {}

    return LLMEvaluationSummary(
        overall_score=llm_result.get("overall_score", 0),
        structural_score=llm_result.get("structural_score", 0),
        requirement_score=llm_result.get("requirement_score", 0),
        output_quality_score=llm_result.get("output_quality_score", 0),
        error_handling_score=llm_result.get("error_handling_score", 0),
        test_data_quality_score=llm_result.get("test_data_quality_score", 0),
        strengths=llm_result.get("strengths", []),
        weaknesses=llm_result.get("weaknesses", []),
        suggestions=llm_result.get("suggestions", []),
    )


def _create_test_data_summary(
    state: WorkflowGeneratorState,
) -> TestDataEvaluationSummary:
    """Create test data evaluation summary from state.

    Args:
        state: Current workflow generator state

    Returns:
        TestDataEvaluationSummary
    """
    regen_count = state.get("test_data_regeneration_count", 0)
    source: Literal["auto_generated", "llm_regenerated"] = (
        "llm_regenerated" if regen_count > 0 else "auto_generated"
    )

    # Build regeneration history
    repair_history = state.get("repair_history", [])
    regen_history = [
        entry
        for entry in repair_history
        if entry.get("type") == "test_data_regeneration"
    ]

    # Handle optional test_data_quality_score
    quality_score = state.get("test_data_quality_score")
    if quality_score is None:
        quality_score = 0

    return TestDataEvaluationSummary(
        quality_score=quality_score,
        source=source,
        issues=state.get("test_data_issues", []),
        regeneration_history=regen_history,
    )


def _determine_overall_status(
    state: WorkflowGeneratorState,
) -> Literal["success", "partial", "failed"]:
    """Determine overall validation status.

    Args:
        state: Current workflow generator state

    Returns:
        "success", "partial", or "failed"
    """
    is_valid = state.get("is_valid", False)
    retry_count = state.get("retry_count", 0)
    regen_count = state.get("test_data_regeneration_count", 0)

    if not is_valid:
        return "failed"
    elif retry_count > 0 or regen_count > 0:
        return "partial"
    else:
        return "success"


def _generate_markdown_summary(
    summary: ValidationSummary,
    state: WorkflowGeneratorState,
) -> str:
    """Generate Markdown formatted summary.

    Args:
        summary: ValidationSummary object
        state: Current workflow generator state

    Returns:
        Markdown formatted string
    """
    status_emoji = {"success": "Pass", "partial": "Partial", "failed": "Fail"}
    status_text = status_emoji.get(summary.overall_status, "Unknown")

    # Rule-based validation table
    rb = summary.rule_based_validation
    rule_based_rows = [
        f"| YAML Syntax | {'Pass' if rb.yaml_syntax_valid else 'Fail'} |",
        f"| HTTP Status | {'Pass' if rb.http_status_valid else 'Fail'} |",
        f"| GraphAI Execution | {'Pass' if rb.graphai_execution_valid else 'Fail'} |",
        f"| Output Schema | {'Pass' if rb.output_schema_valid else 'Fail'} |",
    ]

    # LLM evaluation table
    le = summary.llm_evaluation
    llm_eval_rows = [
        f"| Structural | {le.structural_score}/100 |",
        f"| Requirements | {le.requirement_score}/100 |",
        f"| Output Quality | {le.output_quality_score}/100 |",
        f"| Error Handling | {le.error_handling_score}/100 |",
        f"| Test Data Quality | {le.test_data_quality_score}/100 |",
    ]

    # Test data info
    td = summary.test_data_evaluation
    test_data_info = [
        f"| Quality Score | {td.quality_score}/100 |",
        f"| Data Source | {td.source.replace('_', ' ').title()} |",
        f"| Regeneration Count | {summary.test_data_regeneration_count} |",
    ]

    # Strengths and weaknesses
    strengths_list = (
        "\n".join([f"- {s}" for s in le.strengths]) if le.strengths else "None"
    )
    weaknesses_list = (
        "\n".join([f"- {w}" for w in le.weaknesses]) if le.weaknesses else "None"
    )

    # Recommendations
    recommendations_list = (
        "\n".join([f"1. {r}" for r in summary.recommended_actions])
        if summary.recommended_actions
        else "None"
    )

    markdown = f"""# Workflow Validation Summary

## Basic Information
| Item | Value |
|------|-------|
| TaskMaster ID | {summary.task_master_id} |
| Task Name | {summary.task_name} |
| Workflow Name | {summary.workflow_name} |
| Generated At | {summary.generated_at} |

## Validation Result Summary

### Overall: {status_text} (Score: {summary.final_score}/100)

### Rule-Based Validation
| Check | Result |
|-------|--------|
{chr(10).join(rule_based_rows)}

### LLM Evaluation
| Aspect | Score |
|--------|-------|
{chr(10).join(llm_eval_rows)}

### Test Data Evaluation
| Item | Value |
|------|-------|
{chr(10).join(test_data_info)}

### Strengths
{strengths_list}

### Weaknesses
{weaknesses_list}

### Recommendations
{recommendations_list}

## Retry History
| Type | Count | Max |
|------|-------|-----|
| Workflow Regeneration | {summary.retry_count} | {summary.max_retry} |
| Test Data Regeneration | {summary.test_data_regeneration_count} | {summary.max_test_data_regeneration} |

---
*Generated by Workflow Generator v2.0*
"""

    return markdown


async def result_summary_generator_node(
    state: WorkflowGeneratorState,
) -> WorkflowGeneratorState:
    """Generate comprehensive validation summary.

    Creates a ValidationSummary object and Markdown formatted summary
    from the current state.

    Args:
        state: Current workflow generator state

    Returns:
        Updated state with validation summary
    """
    logger.info("Starting result summary generator node")

    # Create component summaries
    rule_based = _create_rule_based_summary(state)
    llm_eval = _create_llm_evaluation_summary(state)
    test_data = _create_test_data_summary(state)

    # Determine overall status
    overall_status = _determine_overall_status(state)

    # Calculate final score
    llm_result = state.get("llm_evaluation_result") or {}
    final_score = llm_result.get("overall_score", 0)

    # Build recommendations
    recommendations = llm_result.get("suggestions", [])

    # Create ValidationSummary
    task_data = state.get("task_data", {})
    summary = ValidationSummary(
        task_master_id=str(state.get("task_master_id", "")),
        task_name=task_data.get("name", "Unknown"),
        workflow_name=state.get("workflow_name", "unknown"),
        generated_at=datetime.now().isoformat(),
        overall_status=overall_status,
        rule_based_validation=rule_based,
        llm_evaluation=llm_eval,
        test_data_evaluation=test_data,
        final_score=final_score,
        recommended_actions=recommendations,
        retry_count=state.get("retry_count", 0),
        max_retry=state.get("max_retry", 3),
        test_data_regeneration_count=state.get("test_data_regeneration_count", 0),
        max_test_data_regeneration=state.get("max_test_data_regeneration", 2),
    )

    # Generate Markdown summary
    markdown = _generate_markdown_summary(summary, state)

    logger.info(f"Summary generated: status={overall_status}, score={final_score}")

    return {
        **state,
        "validation_summary": summary.model_dump(),
        "summary_markdown": markdown,
        "status": "success",
    }
