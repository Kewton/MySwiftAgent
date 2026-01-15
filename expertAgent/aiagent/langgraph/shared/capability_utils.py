"""Shared utilities for capability handling across V1 and V2.

This module provides common functions for loading and formatting
capabilities from YAML configuration.

Issue #342: V2 タスク分割 API情報注入メカニズム実装
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# YAML config path (shared between V1 and V2)
_CONFIG_PATH = Path(__file__).parent.parent / "jobTaskGeneratorAgents/utils/config"


def load_capabilities_from_yaml() -> list[dict[str, Any]]:
    """Load capabilities from expert_agent_capabilities.yaml.

    Returns:
        List of capability dictionaries with all fields from YAML.
        Each dict contains: name, endpoint, description, use_cases, method,
        request_schema, response_schema
    """
    yaml_path = _CONFIG_PATH / "expert_agent_capabilities.yaml"
    if not yaml_path.exists():
        logger.warning("Capabilities YAML not found at %s", yaml_path)
        return []

    try:
        with open(yaml_path, encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
    except Exception as e:
        logger.error("Failed to load capabilities YAML: %s", e)
        return []

    capabilities: list[dict[str, Any]] = []

    # Utility APIs
    for api in config.get("utility_apis", []):
        capabilities.append(
            {
                "name": api.get("name", ""),
                "endpoint": api.get("endpoint", ""),
                "description": api.get("description", ""),
                "use_cases": api.get("use_cases", []),
                "method": api.get("method", "POST"),
                "request_schema": api.get("request_schema", {}),
                "response_schema": api.get("response_schema", {}),
            }
        )

    # AI Agent APIs
    for api in config.get("ai_agent_apis", []):
        capabilities.append(
            {
                "name": api.get("name", ""),
                "endpoint": api.get("endpoint", ""),
                "description": api.get("description", ""),
                "use_cases": api.get("use_cases", []),
                "method": api.get("method", "POST"),
                "request_schema": api.get("request_schema", {}),
                "response_schema": api.get("response_schema", {}),
            }
        )

    logger.info("Loaded %d capabilities from YAML", len(capabilities))
    return capabilities


def format_capabilities_for_prompt(capabilities: list[dict[str, Any]]) -> str:
    """Format capabilities for LLM prompt injection.

    Args:
        capabilities: List of capability dictionaries

    Returns:
        Formatted string for prompt injection (Markdown format)
    """
    if not capabilities:
        return ""

    lines = ["## 利用可能なAPI", ""]

    # Group by type based on endpoint prefix
    utility_apis = [
        c for c in capabilities if c.get("endpoint", "").startswith("/v1/utility/")
    ]
    ai_apis = [
        c for c in capabilities if not c.get("endpoint", "").startswith("/v1/utility/")
    ]

    if utility_apis:
        lines.append("### Utility API (Direct API)")
        for api in utility_apis:
            use_cases = "、".join(api.get("use_cases", []))
            use_cases_str = f" - {use_cases}" if use_cases else ""
            lines.append(
                f"- **{api['name']}** (`{api['endpoint']}`): "
                f"{api['description']}{use_cases_str}"
            )
        lines.append("")

    if ai_apis:
        lines.append("### AI Agent API")
        for api in ai_apis:
            use_cases = "、".join(api.get("use_cases", []))
            use_cases_str = f" - {use_cases}" if use_cases else ""
            lines.append(
                f"- **{api['name']}** (`{api['endpoint']}`): "
                f"{api['description']}{use_cases_str}"
            )
        lines.append("")

    return "\n".join(lines)
