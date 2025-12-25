"""Input conversion utilities for workflow generator agents.

This module provides common utility functions for converting input data
between different formats used in the workflow generator pipeline.
"""

from typing import Any


def convert_sample_input_to_dict_or_str(
    sample_input: dict[str, Any] | str | int | float | bool | list[Any] | None,
) -> dict[str, Any] | str:
    """Convert sample_input to dict or str for prompt generation.

    Handles various input types by converting them to a format suitable
    for LLM prompt generation.

    Args:
        sample_input: Raw sample input from state. Can be:
            - None: Returns empty dict
            - dict: Returns as-is
            - Other types (str, int, float, bool, list): Converted to string

    Returns:
        Sample input as dict (if input was dict or None) or str (for other types)

    Examples:
        >>> convert_sample_input_to_dict_or_str(None)
        {}
        >>> convert_sample_input_to_dict_or_str({"key": "value"})
        {'key': 'value'}
        >>> convert_sample_input_to_dict_or_str("test string")
        'test string'
        >>> convert_sample_input_to_dict_or_str(42)
        '42'
        >>> convert_sample_input_to_dict_or_str([1, 2, 3])
        '[1, 2, 3]'
    """
    if sample_input is None:
        return {}
    if isinstance(sample_input, dict):
        return sample_input
    return str(sample_input)
