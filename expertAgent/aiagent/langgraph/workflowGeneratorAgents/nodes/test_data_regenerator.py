"""Test Data Regenerator node for regenerating low-quality test data.

This module provides the Test Data Regenerator node that uses LLM
to regenerate test data when quality issues are detected.
"""

import logging
from typing import Any

from ..models.evaluation import RegeneratedTestData
from ..prompts.test_data_regeneration import (
    TEST_DATA_REGENERATION_SYSTEM_PROMPT,
    create_test_data_regeneration_prompt,
)
from ..state import WorkflowGeneratorState
from ..utils import convert_sample_input_to_dict_or_str

logger = logging.getLogger(__name__)


async def _call_llm_regenerator(
    prompt: str,
    model_name: str = "gpt-4o-mini",
) -> RegeneratedTestData | None:
    """Call LLM to regenerate test data.

    Args:
        prompt: Regeneration prompt
        model_name: Model to use for regeneration

    Returns:
        RegeneratedTestData or None on failure
    """
    try:
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
            invoke_structured_llm,
        )

        messages = [
            {"role": "system", "content": TEST_DATA_REGENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        result: StructuredCallResult[RegeneratedTestData] = await invoke_structured_llm(
            messages=messages,
            response_model=RegeneratedTestData,
            context_label="test_data_regenerator",
            model_env_var="TEST_DATA_REGENERATOR_MODEL",
            default_model=model_name,
        )

        if result and result.result:
            return result.result
        return None
    except Exception as e:
        logger.warning(f"LLM test data regeneration failed: {e}")
        return None


def _build_regenerator_input(
    state: WorkflowGeneratorState,
) -> str:
    """Build the regeneration prompt from state.

    Args:
        state: Current workflow generator state

    Returns:
        Formatted prompt string
    """
    task_data = state.get("task_data", {})
    input_interface = task_data.get("input_interface", {})
    raw_sample_input = state.get("sample_input")
    sample_input = convert_sample_input_to_dict_or_str(raw_sample_input)

    # Issue #340: Include object_array_issues in regeneration feedback
    # Merge test_data_issues with object_array_issues for comprehensive feedback
    base_test_data_issues = state.get("test_data_issues", [])
    object_array_issues = state.get("object_array_issues", [])

    # Convert object_array_issues to string messages for the prompt
    object_array_messages = [
        f"[object_array:{issue.get('issue_type', 'unknown')}] "
        f"{issue.get('message', '')} - Suggestion: {issue.get('suggestion', '')}"
        for issue in object_array_issues
        if isinstance(issue, dict)
    ]

    merged_test_data_issues = base_test_data_issues + object_array_messages

    return create_test_data_regeneration_prompt(
        task_name=task_data.get("name", "Unknown"),
        task_description=task_data.get("description", ""),
        input_schema=input_interface.get("schema", {}),
        recommended_apis=task_data.get("recommended_apis", []),
        previous_sample_input=sample_input,
        test_data_issues=merged_test_data_issues,
        suggested_test_data=state.get("suggested_test_data"),
    )


async def test_data_regenerator_node(
    state: WorkflowGeneratorState,
) -> WorkflowGeneratorState:
    """Test data regeneration node.

    Regenerates test data when the LLM Evaluator detects quality issues.
    Uses LLM suggested data if available, otherwise calls LLM for new data.

    Issue #340: Also handles object array regeneration with separate counter.
    MF-1: Increment object_array_regeneration_count to prevent infinite loops.

    Args:
        state: Current workflow generator state

    Returns:
        Updated state with regenerated test data
    """
    logger.info("Starting test data regenerator node")

    current_count = state.get("test_data_regeneration_count", 0)
    max_count = state.get("max_test_data_regeneration", 2)

    # Issue #340 MF-1: Track object array regeneration count
    object_array_regen_count = state.get("object_array_regeneration_count", 0)

    # Check if max regeneration count reached
    if current_count >= max_count:
        logger.warning(f"Max test data regeneration count ({max_count}) reached")
        return {
            **state,
            "needs_test_data_regeneration": False,
            "status": "test_data_regeneration_exhausted",
        }

    # Use LLM suggested data if available
    suggested_data = state.get("suggested_test_data")
    new_sample_input: dict[str, Any] | None = None

    if suggested_data:
        logger.info("Using LLM suggested test data")
        new_sample_input = suggested_data
    else:
        # Call LLM for new test data
        logger.info("Calling LLM for test data regeneration")
        prompt = _build_regenerator_input(state)

        try:
            regenerated = await _call_llm_regenerator(prompt)
            if regenerated:
                new_sample_input = regenerated.sample_input
                logger.info(
                    f"LLM generated test data: {regenerated.generation_rationale}"
                )
            else:
                logger.warning("LLM regeneration returned None")
        except Exception as e:
            logger.error(f"Test data regeneration failed: {e}")

    # If regeneration failed, increment count to prevent infinite loops
    if new_sample_input is None:
        logger.warning("Test data regeneration failed, using previous data")
        return {
            **state,
            "test_data_regeneration_count": current_count + 1,
            # Issue #340 MF-1: Increment object array regeneration count
            "object_array_regeneration_count": object_array_regen_count + 1,
            "needs_test_data_regeneration": False,
            # Issue #340: Clear object array errors after regeneration attempt
            "has_object_array_errors": False,
            "status": "test_data_regeneration_failed",
        }

    logger.info(f"Regenerated test data: {new_sample_input}")

    return {
        **state,
        "sample_input": new_sample_input,
        "regenerated_sample_input": new_sample_input,
        "test_data_regeneration_count": current_count + 1,
        # Issue #340 MF-1: Increment object array regeneration count
        "object_array_regeneration_count": object_array_regen_count + 1,
        "needs_test_data_regeneration": False,
        # Issue #340: Clear object array errors after successful regeneration
        "has_object_array_errors": False,
        "object_array_issues": [],
        "status": "test_data_regenerated",
    }
