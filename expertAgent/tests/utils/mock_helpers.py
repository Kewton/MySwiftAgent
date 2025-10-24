"""Mock helper functions for workflow node testing.

This module provides reusable mock creation functions to reduce code duplication
in test files and ensure consistent mock behavior across all tests.
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock


def create_mock_llm(response_data: dict[str, Any] | None = None) -> AsyncMock:
    """Create a mocked LLM instance with predefined response data.

    Args:
        response_data: The data that the LLM should return when invoked.
                      If None, returns an empty dict.

    Returns:
        AsyncMock: A mocked LLM instance that can be used in tests.

    Example:
        >>> from tests.integration.fixtures.llm_responses import VALIDATION_SUCCESS_RESPONSE
        >>> mock_llm = create_mock_llm(VALIDATION_SUCCESS_RESPONSE)
        >>> result = await mock_llm.ainvoke(...)
        >>> assert result["has_errors"] is False
    """
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=response_data or {})
    return mock_llm


def create_mock_llm_with_structured_output(
    response_data: dict[str, Any] | None = None,
) -> MagicMock:
    """Create a mocked LLM with structured output capability.

    This is specifically for testing code that uses `model.with_structured_output()`.

    Args:
        response_data: The data that the LLM should return when invoked.

    Returns:
        MagicMock: A mocked LLM instance with with_structured_output method.

    Example:
        >>> mock_llm = create_mock_llm_with_structured_output({"field": "value"})
        >>> structured_model = mock_llm.with_structured_output(SomeSchema)
        >>> result = await structured_model.ainvoke(...)
        >>> assert result["field"] == "value"
    """
    mock_structured = AsyncMock()
    mock_structured.ainvoke = AsyncMock(return_value=response_data or {})

    mock_llm = MagicMock()
    mock_llm.with_structured_output = MagicMock(return_value=mock_structured)

    return mock_llm


def create_mock_workflow_state(
    retry_count: int = 0,
    **additional_fields: Any,
) -> dict[str, Any]:
    """Create a mock workflow state dict for testing.

    Args:
        retry_count: The retry count value (default: 0).
        **additional_fields: Additional fields to include in the state.

    Returns:
        dict: A mock workflow state dict.

    Example:
        >>> state = create_mock_workflow_state(
        ...     retry_count=2,
        ...     task_breakdown=[{"task_id": "task_1"}],
        ...     validation_result={"is_valid": False}
        ... )
        >>> assert state["retry_count"] == 2
    """
    state: dict[str, Any] = {"retry_count": retry_count}
    state.update(additional_fields)
    return state


def create_mock_task_breakdown(num_tasks: int = 3) -> list[dict[str, Any]]:
    """Create a mock task breakdown with the specified number of tasks.

    Args:
        num_tasks: Number of tasks to create (default: 3).

    Returns:
        list: A list of mock task dicts.

    Example:
        >>> tasks = create_mock_task_breakdown(2)
        >>> assert len(tasks) == 2
        >>> assert tasks[0]["task_id"] == "task_1"
    """
    return [
        {
            "task_id": f"task_{i}",
            "name": f"Task {i}",  # Changed from "task_name" to "name"
            "description": f"Description for task {i}",
            "priority": "high" if i == 1 else "medium",
            "dependencies": [] if i == 1 else [f"task_{i - 1}"],
        }
        for i in range(1, num_tasks + 1)
    ]


def create_mock_interface_schemas(num_schemas: int = 3) -> list[dict[str, Any]]:
    """Create mock interface schemas for testing.

    Args:
        num_schemas: Number of interface schemas to create (default: 3).

    Returns:
        list: A list of mock interface schema dicts.

    Example:
        >>> schemas = create_mock_interface_schemas(2)
        >>> assert len(schemas) == 2
        >>> assert schemas[0]["interface_name"] == "Interface_1"
    """
    return [
        {
            "task_id": f"task_{i}",
            "interface_name": f"Interface_{i}",
            "description": f"Interface for task {i}",
            "input_schema": {
                "type": "object",
                "properties": {
                    f"input_{i}": {"type": "string"},
                },
                "required": [f"input_{i}"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    f"output_{i}": {"type": "string"},
                },
                "required": [f"output_{i}"],
            },
        }
        for i in range(1, num_schemas + 1)
    ]


def create_mock_validation_result(
    is_valid: bool = True,
    errors: list[str] | None = None,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Create a mock validation result for testing.

    Args:
        is_valid: Whether the validation passed (default: True).
        errors: List of error messages (default: []).
        warnings: List of warning messages (default: []).

    Returns:
        dict: A mock validation result dict.

    Example:
        >>> result = create_mock_validation_result(
        ...     is_valid=False,
        ...     errors=["Schema mismatch"]
        ... )
        >>> assert result["is_valid"] is False
        >>> assert len(result["errors"]) == 1
    """
    return {
        "is_valid": is_valid,
        "errors": errors or [],
        "warnings": warnings or [],
    }


def create_mock_evaluation_result(
    is_valid: bool = True,
    quality_score: float = 0.9,
    feasibility_score: float = 0.85,
) -> dict[str, Any]:
    """Create a mock evaluation result for testing.

    Args:
        is_valid: Whether the evaluation passed (default: True).
        quality_score: Quality score (default: 0.9).
        feasibility_score: Feasibility score (default: 0.85).

    Returns:
        dict: A mock evaluation result dict.

    Example:
        >>> result = create_mock_evaluation_result(is_valid=False, quality_score=0.5)
        >>> assert result["is_valid"] is False
        >>> assert result["quality_score"] == 0.5
    """
    return {
        "is_valid": is_valid,
        "quality_score": quality_score,
        "feasibility_score": feasibility_score,
        "evaluation_summary": "Test evaluation summary",
    }
