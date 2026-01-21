"""Log sanitization utilities for capability data.

Issue #385: Sanitize sensitive information from capabilities before logging.

This module provides:
- SENSITIVE_KEYS: Set of keys that should be removed from log output
- sanitize_capability_for_log: Remove sensitive data from single capability
- sanitize_capabilities_for_log: Remove sensitive data from capability list
- create_capability_log_summary: Create safe log summary
"""

from typing import Any

# Keys that should be removed from log output
SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        "_internal",
        "secret_key",
        "api_key",
        "token",
        "password",
        "credential",
        "auth",
    }
)


def sanitize_capability_for_log(capability: dict[str, Any]) -> dict[str, Any]:
    """Remove sensitive information from a single capability dict.

    Recursively removes keys that match SENSITIVE_KEYS from the capability
    dictionary and all nested dictionaries.

    Args:
        capability: Capability dictionary that may contain sensitive data

    Returns:
        New dictionary with sensitive keys removed. Original is not modified.

    Example:
        >>> cap = {"name": "agent", "api_key": "secret"}
        >>> sanitize_capability_for_log(cap)
        {"name": "agent"}
    """
    return _sanitize_dict(capability)


def _sanitize_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Recursively sanitize a dictionary by removing sensitive keys.

    Args:
        data: Dictionary to sanitize

    Returns:
        New sanitized dictionary
    """
    result: dict[str, Any] = {}

    for key, value in data.items():
        # Skip sensitive keys
        if key in SENSITIVE_KEYS:
            continue

        # Recursively sanitize nested dicts
        if isinstance(value, dict):
            result[key] = _sanitize_dict(value)
        else:
            result[key] = value

    return result


def sanitize_capabilities_for_log(
    capabilities: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remove sensitive information from a list of capabilities.

    Args:
        capabilities: List of capability dictionaries

    Returns:
        New list with sanitized capability dictionaries. Original is not modified.

    Example:
        >>> caps = [{"name": "agent1", "api_key": "key1"}]
        >>> sanitize_capabilities_for_log(caps)
        [{"name": "agent1"}]
    """
    return [sanitize_capability_for_log(cap) for cap in capabilities]


def create_capability_log_summary(capabilities: list[dict[str, Any]]) -> str:
    """Create a safe log summary of capabilities.

    Generates a human-readable summary of capabilities that is safe to log,
    without including any sensitive information.

    Args:
        capabilities: List of capability dictionaries

    Returns:
        String summary suitable for logging

    Example:
        >>> caps = [{"name": "fetchAgent"}, {"name": "searchAgent"}]
        >>> create_capability_log_summary(caps)
        "2 capabilities: [fetchAgent, searchAgent]"
    """
    count = len(capabilities)

    if count == 0:
        return "0 capabilities: []"

    # Extract names safely
    names: list[str] = []
    for cap in capabilities:
        name = cap.get("name")
        if name:
            names.append(str(name))
        else:
            names.append("<unnamed>")

    return f"{count} capabilities: [{', '.join(names)}]"


__all__ = [
    "SENSITIVE_KEYS",
    "create_capability_log_summary",
    "sanitize_capabilities_for_log",
    "sanitize_capability_for_log",
]
