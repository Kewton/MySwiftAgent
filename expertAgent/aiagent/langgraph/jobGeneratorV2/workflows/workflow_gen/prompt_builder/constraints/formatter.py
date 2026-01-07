"""Constraints formatter for Workflow Generator V2.

This module formats API constraints for LLM prompts.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

from __future__ import annotations

from typing import Any

from .loader import get_api_capabilities, get_recommended_timeout


def format_api_constraint(api_name: str) -> str:
    """Format API constraint for LLM prompt.

    Args:
        api_name: Name of the API

    Returns:
        Formatted constraint string
    """
    api = get_api_capabilities(api_name)
    if not api:
        return f"No constraints found for API: {api_name}"

    lines = [
        f"### {api.get('name', api_name)}",
        f"- Endpoint: {api.get('endpoint', 'N/A')}",
        f"- Method: {api.get('method', 'POST')}",
    ]

    if desc := api.get("description"):
        lines.append(f"- Description: {desc}")

    timeout = get_recommended_timeout(api_name)
    if timeout:
        lines.append(f"- Recommended Timeout: {timeout}s")

    # Format request schema
    req_schema = api.get("request_schema", {})
    if req_schema:
        lines.append("- Request Parameters:")
        for name, spec in req_schema.items():
            req_type = spec.get("type", "any")
            required = "required" if spec.get("required") else "optional"
            desc = spec.get("description", "")
            default = spec.get("default")
            default_str = f" (default: {default})" if default is not None else ""
            lines.append(f"  - {name}: {req_type} ({required}){default_str}")
            if desc:
                lines.append(f"    Description: {desc}")

    # Format response schema
    resp_schema = api.get("response_schema", {})
    if resp_schema:
        lines.append("- Response Fields:")
        for name, spec in resp_schema.items():
            resp_type = spec.get("type", "any")
            desc = spec.get("description", "")
            lines.append(f"  - {name}: {resp_type}")
            if desc:
                lines.append(f"    Description: {desc}")

    return "\n".join(lines)


def format_multiple_api_constraints(api_names: list[str]) -> str:
    """Format constraints for multiple APIs.

    Args:
        api_names: List of API names

    Returns:
        Formatted constraints string
    """
    if not api_names:
        return ""

    lines = ["## API Constraints\n"]
    for api_name in api_names:
        constraint = format_api_constraint(api_name)
        lines.append(constraint)
        lines.append("")

    return "\n".join(lines)


def format_schema_to_yaml_example(schema: dict[str, Any], indent: int = 2) -> str:
    """Format a schema as YAML example.

    Args:
        schema: JSON Schema dictionary
        indent: Indentation spaces

    Returns:
        YAML example string
    """
    indent_str = " " * indent

    if not schema:
        return "{}"

    properties = schema.get("properties", {})
    if not properties:
        return "{}"

    lines = []
    for name, spec in properties.items():
        prop_type = spec.get("type", "string")
        if prop_type == "string":
            lines.append(f"{indent_str}{name}: \"example\"")
        elif prop_type == "integer":
            lines.append(f"{indent_str}{name}: 10")
        elif prop_type == "number":
            lines.append(f"{indent_str}{name}: 10.5")
        elif prop_type == "boolean":
            lines.append(f"{indent_str}{name}: true")
        elif prop_type == "array":
            lines.append(f"{indent_str}{name}:")
            lines.append(f"{indent_str}  - item")
        elif prop_type == "object":
            lines.append(f"{indent_str}{name}:")
            lines.append(f"{indent_str}  key: value")

    return "\n".join(lines)
