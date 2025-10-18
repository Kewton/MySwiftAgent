"""Merge utilities for job master parameters."""

from typing import Any


def merge_dict_shallow(
    base: dict[str, Any] | None, override: dict[str, Any] | None
) -> dict[str, Any] | None:
    """
    Merge two dictionaries with shallow merge strategy.

    Override values take precedence over base values.
    Used for headers and query parameters.

    Args:
        base: Base dictionary (from job master)
        override: Override dictionary (from job creation request)

    Returns:
        Merged dictionary, or None if both inputs are None

    Examples:
        >>> merge_dict_shallow({"a": 1}, {"a": 2, "b": 3})
        {"a": 2, "b": 3}
        >>> merge_dict_shallow({"a": 1}, None)
        {"a": 1}
        >>> merge_dict_shallow(None, None)
        None
    """
    if base is None and override is None:
        return None

    result = (base or {}).copy()
    if override:
        result.update(override)

    return result if result else None


def merge_dict_deep(
    base: dict[str, Any] | None, override: dict[str, Any] | None
) -> dict[str, Any] | None:
    """
    Merge two dictionaries with deep merge strategy.

    Recursively merges nested dictionaries.
    Override values take precedence over base values.
    Used for request body.

    Args:
        base: Base dictionary (from job master)
        override: Override dictionary (from job creation request)

    Returns:
        Deeply merged dictionary, or None if both inputs are None

    Examples:
        >>> merge_dict_deep(
        ...     {"user": {"name": "Alice", "age": 30}},
        ...     {"user": {"age": 31}}
        ... )
        {"user": {"name": "Alice", "age": 31}}
        >>> merge_dict_deep({"a": [1, 2]}, {"a": [3]})
        {"a": [3]}  # Arrays are not merged, just replaced
    """
    if base is None and override is None:
        return None

    if base is None:
        return override

    if override is None:
        return base

    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            # Recursive merge for nested dicts
            result[key] = merge_dict_deep(result[key], value)
        else:
            # Override value (including arrays, which are not merged)
            result[key] = value

    return result


def merge_tags(
    base_tags: list[str] | None, override_tags: list[str] | None
) -> list[str] | None:
    """
    Merge two tag lists with union strategy.

    Duplicates are removed and result is sorted.

    Args:
        base_tags: Base tag list (from job master)
        override_tags: Override tag list (from job creation request)

    Returns:
        Merged and deduplicated tag list, or None if both inputs are None

    Examples:
        >>> merge_tags(["a", "b"], ["b", "c"])
        ["a", "b", "c"]
        >>> merge_tags(["z", "a"], None)
        ["a", "z"]
        >>> merge_tags(None, None)
        None
    """
    if base_tags is None and override_tags is None:
        return None

    result = set(base_tags or [])
    if override_tags:
        result.update(override_tags)

    return sorted(result) if result else None
