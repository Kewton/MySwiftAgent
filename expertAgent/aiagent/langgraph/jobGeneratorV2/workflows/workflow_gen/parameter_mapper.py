"""ParameterMapper for Workflow Generator V2.

This module provides functions and classes to map interface parameters
to GraphAI workflow parameters following the GraphAI specification.

Issue #342 V2 Workflow Quality Improvement

Key responsibilities:
- Convert interface schemas to GraphAI inputs block format
- Generate :source.nodeId.fieldName references
- Build fetchAgent inputs with url, method, body structure
"""

from __future__ import annotations

from typing import Any

from .agent_selector import AgentSelector


def map_input_params(
    interface_inputs: dict[str, Any],
    source_node: str,
) -> dict[str, str]:
    """Map interface input parameters to GraphAI source references.

    Args:
        interface_inputs: Dictionary of input field definitions
            (field_name -> schema definition)
        source_node: Source node name for reference (e.g., 'user_input')

    Returns:
        Dictionary of field names to :source references
    """
    if not interface_inputs:
        return {}

    result: dict[str, str] = {}
    for field_name in interface_inputs:
        result[field_name] = f":source.{source_node}.{field_name}"

    return result


def map_api_params(
    api_name: str,
    interface_inputs: dict[str, Any],
    source_node: str,
) -> dict[str, Any]:
    """Map API parameters to GraphAI fetchAgent inputs block.

    This function generates the inputs block for fetchAgent following
    the GraphAI specification:
    - url: ${EXPERTAGENT_BASE_URL}/path
    - method: POST/GET/etc.
    - body: mapped parameters with :source references

    Args:
        api_name: API name (e.g., 'gmail_send')
        interface_inputs: Dictionary of input field definitions
        source_node: Source node name for reference

    Returns:
        Dictionary with url, method, body keys (GraphAI inputs block)
    """
    selector = AgentSelector()
    mapping = selector.select_agent(api_name)

    # Build URL
    if mapping:
        url = f"${{EXPERTAGENT_BASE_URL}}{mapping.endpoint_path}"
        method = mapping.http_method
    else:
        # Generic fallback for unknown APIs
        url = f"${{EXPERTAGENT_BASE_URL}}/aiagent-api/v1/utility/{api_name}"
        method = "POST"

    # Build body with mapped parameters
    body = map_input_params(interface_inputs, source_node)

    return {
        "url": url,
        "method": method,
        "body": body,
    }


class ParameterMapper:
    """Mapper for converting interface parameters to GraphAI format.

    This class provides methods to create GraphAI-compliant inputs blocks
    for fetchAgent and other agents.

    Example:
        mapper = ParameterMapper()
        inputs = mapper.create_fetchagent_inputs(
            api_name="gmail_send",
            input_params={"to": "test@example.com"},
            source_node="user_input"
        )
    """

    def __init__(self) -> None:
        """Initialize ParameterMapper."""
        self._selector = AgentSelector()

    def create_fetchagent_inputs(
        self,
        api_name: str,
        input_params: dict[str, Any],
        source_node: str,
    ) -> dict[str, Any]:
        """Create fetchAgent inputs block for an API call.

        Args:
            api_name: API name
            input_params: Input parameters (field_name -> value or schema)
            source_node: Source node name

        Returns:
            GraphAI-compliant inputs block with url, method, body
        """
        return map_api_params(
            api_name=api_name,
            interface_inputs=input_params,
            source_node=source_node,
        )

    def create_inputs_block(
        self,
        url: str,
        method: str,
        body: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a GraphAI inputs block with explicit values.

        Args:
            url: Full URL with ${EXPERTAGENT_BASE_URL}
            method: HTTP method
            body: Body parameters

        Returns:
            GraphAI inputs block dictionary
        """
        return {
            "url": url,
            "method": method,
            "body": body,
        }

    def map_interface_to_body(
        self,
        interface_schema: dict[str, Any],
        source_node: str,
    ) -> dict[str, str]:
        """Map interface schema to body with :source references.

        Args:
            interface_schema: Interface input schema
            source_node: Source node name

        Returns:
            Dictionary with :source references for each field
        """
        return map_input_params(interface_schema, source_node)
