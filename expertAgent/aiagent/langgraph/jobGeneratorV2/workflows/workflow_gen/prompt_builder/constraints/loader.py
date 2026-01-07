"""Constraints loader for Workflow Generator V2.

This module loads API constraints from expert_agent_capabilities.yaml.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# Path to capabilities YAML file
CAPABILITIES_FILE = (
    Path(__file__).parents[5]
    / "jobTaskGeneratorAgents"
    / "utils"
    / "config"
    / "expert_agent_capabilities.yaml"
)


def load_capabilities() -> dict[str, Any]:
    """Load capabilities from YAML file.

    Returns:
        Dictionary of capabilities
    """
    if not CAPABILITIES_FILE.exists():
        logger.warning(
            "Capabilities file not found: %s", CAPABILITIES_FILE
        )
        return {}

    try:
        with open(CAPABILITIES_FILE, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        logger.error("Error loading capabilities: %s", e)
        return {}


def get_api_capabilities(api_name: str) -> dict[str, Any] | None:
    """Get capabilities for a specific API.

    Args:
        api_name: Name of the API

    Returns:
        API capabilities dictionary or None
    """
    caps = load_capabilities()

    # Search in utility_apis
    for api in caps.get("utility_apis", []):
        if isinstance(api, dict):
            if api.get("name", "").lower() == api_name.lower():
                return dict(api)
            if api.get("endpoint", "").lower().endswith(api_name.lower()):
                return dict(api)

    # Search in ai_agent_apis
    for api in caps.get("ai_agent_apis", []):
        if isinstance(api, dict):
            if api.get("name", "").lower() == api_name.lower():
                return dict(api)
            if api.get("endpoint", "").lower().endswith(api_name.lower()):
                return dict(api)

    return None


def get_request_schema(api_name: str) -> dict[str, Any]:
    """Get request schema for an API.

    Args:
        api_name: Name of the API

    Returns:
        Request schema dictionary
    """
    api = get_api_capabilities(api_name)
    if api:
        schema = api.get("request_schema", {})
        return dict(schema) if isinstance(schema, dict) else {}
    return {}


def get_response_schema(api_name: str) -> dict[str, Any]:
    """Get response schema for an API.

    Args:
        api_name: Name of the API

    Returns:
        Response schema dictionary
    """
    api = get_api_capabilities(api_name)
    if api:
        schema = api.get("response_schema", {})
        return dict(schema) if isinstance(schema, dict) else {}
    return {}


def get_recommended_timeout(api_name: str) -> int | None:
    """Get recommended timeout for an API.

    Args:
        api_name: Name of the API

    Returns:
        Recommended timeout in seconds or None
    """
    api = get_api_capabilities(api_name)
    if api:
        return api.get("recommended_timeout")
    return None


def get_all_api_names() -> list[str]:
    """Get list of all available API names.

    Returns:
        List of API names
    """
    caps = load_capabilities()
    names = []

    for api in caps.get("utility_apis", []):
        if name := api.get("name"):
            names.append(name)

    for api in caps.get("ai_agent_apis", []):
        if name := api.get("name"):
            names.append(name)

    return names
