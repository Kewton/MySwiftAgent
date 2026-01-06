"""Type guard utilities for workflow generator agents.

Issue #338: This module provides type guard functions to handle mixed type
inputs (str | dict) for recommended_apis and similar fields.
"""

from typing import Any


def normalize_api_item(api: str | dict[str, Any]) -> dict[str, str]:
    """Normalize API item to dict format.

    Issue #338: Handles both str and dict inputs for API items,
    providing a consistent dict format for downstream processing.

    Args:
        api: API specification as string or dict

    Returns:
        Normalized dict with api_name and endpoint keys

    Raises:
        TypeError: If api is neither str nor dict
    """
    if isinstance(api, str):
        return {"api_name": api, "endpoint": api}
    if isinstance(api, dict):
        return {
            "api_name": api.get("api_name") or api.get("name") or "",
            "endpoint": api.get("endpoint") or "",
        }
    raise TypeError(f"Expected str or dict, got {type(api).__name__}")


def normalize_recommended_apis(
    apis: list[str | dict[str, Any]] | None,
) -> list[dict[str, str]]:
    """Normalize list of API items to consistent dict format.

    Issue #338: This function ensures all items in recommended_apis
    are converted to dict format before processing.

    Args:
        apis: List of API specifications (str or dict), or None

    Returns:
        List of normalized dicts with api_name and endpoint keys
    """
    if apis is None:
        return []
    return [normalize_api_item(api) for api in apis]


def get_api_name(api: str | dict[str, Any]) -> str:
    """Extract API name from str or dict format.

    Issue #338: Safe accessor for API name regardless of input type.

    Args:
        api: API specification as string or dict

    Returns:
        API name string
    """
    if isinstance(api, str):
        return api
    if isinstance(api, dict):
        return api.get("api_name") or api.get("name") or ""
    return ""


def get_api_endpoint(api: str | dict[str, Any]) -> str:
    """Extract API endpoint from str or dict format.

    Issue #338: Safe accessor for API endpoint regardless of input type.

    Args:
        api: API specification as string or dict

    Returns:
        API endpoint string
    """
    if isinstance(api, str):
        return api
    if isinstance(api, dict):
        return api.get("endpoint") or ""
    return ""


def format_apis_for_prompt(apis: list[str | dict[str, Any]] | None) -> str:
    """Format recommended APIs for inclusion in LLM prompts (detailed).

    Issue #338: Provides consistent string formatting for API lists
    regardless of whether items are str or dict.

    Args:
        apis: List of API specifications (str or dict), or None

    Returns:
        Formatted string representation of APIs with bullet points
    """
    if not apis:
        return "None specified"

    lines = []
    for api in apis:
        name = get_api_name(api)
        endpoint = get_api_endpoint(api)
        if name and endpoint and name != endpoint:
            lines.append(f"- {name} (endpoint: {endpoint})")
        elif name:
            lines.append(f"- {name}")
        elif endpoint:
            lines.append(f"- {endpoint}")

    return "\n".join(lines) if lines else "None specified"


def format_apis_comma_separated(apis: list[str | dict[str, Any]] | None) -> str:
    """Format recommended APIs as comma-separated string.

    Issue #338: Simple comma-separated format for prompts,
    matching the existing _format_recommended_apis behavior.

    Args:
        apis: List of API specifications (str or dict), or None

    Returns:
        Comma-separated string of API names
    """
    if not apis:
        return "None specified"

    names = []
    for api in apis:
        name = get_api_name(api)
        if name:
            names.append(name)

    return ", ".join(names) if names else "None specified"
