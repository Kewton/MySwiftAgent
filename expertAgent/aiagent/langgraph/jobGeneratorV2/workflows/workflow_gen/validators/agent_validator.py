"""Agent Validator for Workflow Generator V2.

This module validates that agents used in the workflow exist.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

from __future__ import annotations

from typing import Any

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.errors import (
    ErrorCode,
    ValidationError,
)
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas import (
    AVAILABLE_AGENTS,
)


def validate_agents(nodes: dict[str, Any]) -> list[ValidationError]:
    """Validate all agents in the workflow exist.

    Args:
        nodes: Nodes dictionary from parsed YAML

    Returns:
        List of validation errors for unknown agents
    """
    errors: list[ValidationError] = []

    for node_name, node_def in nodes.items():
        # Skip source node
        if node_name == "source":
            continue

        if not isinstance(node_def, dict):
            continue

        agent = node_def.get("agent")
        if not agent:
            continue

        if agent not in AVAILABLE_AGENTS:
            # Get similar agent suggestions
            suggestions = _get_similar_agents(agent)
            suggestion_text = (
                f"Did you mean: {', '.join(suggestions)}"
                if suggestions
                else f"Available agents: {', '.join(AVAILABLE_AGENTS[:10])}..."
            )

            errors.append(
                ValidationError(
                    code=ErrorCode.UNKNOWN_AGENT,
                    message=f"Unknown agent '{agent}' in node '{node_name}'",
                    location=f"nodes.{node_name}.agent",
                    suggestion=suggestion_text,
                )
            )

        # Validate nested graph agents (for mapAgent, nestedAgent)
        nested_errors = _validate_nested_agents(node_name, node_def)
        errors.extend(nested_errors)

    return errors


def _get_similar_agents(agent_name: str, max_suggestions: int = 3) -> list[str]:
    """Get similar agent names for suggestions.

    Args:
        agent_name: The unknown agent name
        max_suggestions: Maximum number of suggestions

    Returns:
        List of similar agent names
    """
    agent_lower = agent_name.lower()
    suggestions = []

    for available in AVAILABLE_AGENTS:
        # Check for substring match
        if agent_lower in available.lower() or available.lower() in agent_lower:
            suggestions.append(available)
            if len(suggestions) >= max_suggestions:
                break

    # If no substring matches, check for common prefix
    if not suggestions:
        for available in AVAILABLE_AGENTS:
            if available.lower().startswith(agent_lower[:3]):
                suggestions.append(available)
                if len(suggestions) >= max_suggestions:
                    break

    return suggestions


def _validate_nested_agents(
    parent_name: str, node_def: dict[str, Any]
) -> list[ValidationError]:
    """Validate agents in nested graphs (mapAgent, nestedAgent).

    Args:
        parent_name: Name of the parent node
        node_def: Node definition dictionary

    Returns:
        List of validation errors for nested agents
    """
    errors: list[ValidationError] = []

    # Check for nested graph
    graph = node_def.get("graph")
    if not graph or not isinstance(graph, dict):
        return errors

    nested_nodes = graph.get("nodes")
    if not nested_nodes or not isinstance(nested_nodes, dict):
        return errors

    for nested_name, nested_def in nested_nodes.items():
        if nested_name == "source" or nested_name.endswith("_source"):
            continue

        if not isinstance(nested_def, dict):
            continue

        agent = nested_def.get("agent")
        if not agent:
            continue

        if agent not in AVAILABLE_AGENTS:
            suggestions = _get_similar_agents(agent)
            suggestion_text = (
                f"Did you mean: {', '.join(suggestions)}"
                if suggestions
                else "Check AVAILABLE_AGENTS.md for valid agents"
            )

            errors.append(
                ValidationError(
                    code=ErrorCode.UNKNOWN_AGENT,
                    message=f"Unknown agent '{agent}' in nested node '{parent_name}.graph.nodes.{nested_name}'",
                    location=f"nodes.{parent_name}.graph.nodes.{nested_name}.agent",
                    suggestion=suggestion_text,
                )
            )

    return errors
