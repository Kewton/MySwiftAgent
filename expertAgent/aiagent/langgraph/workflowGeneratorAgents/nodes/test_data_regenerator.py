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


def _convert_sample_input_to_dict_or_str(
    sample_input: dict[str, Any] | str | int | float | bool | list[Any] | None,
) -> dict[str, Any] | str:
    """Convert sample_input to dict or str for prompt generation.

    Args:
        sample_input: Raw sample input from state

    Returns:
        Sample input as dict or str
    """
    if sample_input is None:
        return {}
    if isinstance(sample_input, dict):
        return sample_input
    return str(sample_input)


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
    sample_input = _convert_sample_input_to_dict_or_str(raw_sample_input)

    return create_test_data_regeneration_prompt(
        task_name=task_data.get("name", "Unknown"),
        task_description=task_data.get("description", ""),
        input_schema=input_interface.get("schema", {}),
        recommended_apis=task_data.get("recommended_apis", []),
        previous_sample_input=sample_input,
        test_data_issues=state.get("test_data_issues", []),
        suggested_test_data=state.get("suggested_test_data"),
    )


async def test_data_regenerator_node(
    state: WorkflowGeneratorState,
) -> WorkflowGeneratorState:
    """Test data regeneration node.

    Regenerates test data when the LLM Evaluator detects quality issues.
    Uses LLM suggested data if available, otherwise calls LLM for new data.

    Args:
        state: Current workflow generator state

    Returns:
        Updated state with regenerated test data
    """
    logger.info("Starting test data regenerator node")

    current_count = state.get("test_data_regeneration_count", 0)
    max_count = state.get("max_test_data_regeneration", 2)

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
            "needs_test_data_regeneration": False,
            "status": "test_data_regeneration_failed",
        }

    logger.info(f"Regenerated test data: {new_sample_input}")

    return {
        **state,
        "sample_input": new_sample_input,
        "regenerated_sample_input": new_sample_input,
        "test_data_regeneration_count": current_count + 1,
        "needs_test_data_regeneration": False,
        "status": "test_data_regenerated",
    }
