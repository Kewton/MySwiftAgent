"""Structure Validator for Workflow Generator V2.

This module validates GraphAI workflow structure requirements:
- version field
- source node
- isResult node

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

from __future__ import annotations

from typing import Any

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.errors import (
    ErrorCode,
    ValidationError,
)


def validate_structure(parsed_yaml: dict[str, Any]) -> list[ValidationError]:
    """Validate GraphAI workflow structure.

    Args:
        parsed_yaml: Parsed YAML dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    errors: list[ValidationError] = []

    # Validate version
    version = parsed_yaml.get("version")
    if version is None:
        errors.append(
            ValidationError(
                code=ErrorCode.INVALID_VERSION,
                message="Missing 'version' field",
                location="root",
                suggestion="Add 'version: \"0.5\"' to the workflow",
            )
        )
    elif str(version) != "0.5":
        errors.append(
            ValidationError(
                code=ErrorCode.INVALID_VERSION,
                message=f"Invalid version: {version}. Expected '0.5'",
                location="version",
                suggestion="Change version to '0.5'",
            )
        )

    # Validate nodes exists
    nodes = parsed_yaml.get("nodes")
    if nodes is None:
        errors.append(
            ValidationError(
                code=ErrorCode.EMPTY_NODES,
                message="Missing 'nodes' field",
                location="root",
                suggestion="Add 'nodes:' section with at least source and output nodes",
            )
        )
        return errors  # Can't validate further without nodes

    if not isinstance(nodes, dict):
        errors.append(
            ValidationError(
                code=ErrorCode.INVALID_YAML_STRUCTURE,
                message=f"'nodes' must be a dictionary, got {type(nodes).__name__}",
                location="nodes",
                suggestion="Define nodes as key-value pairs",
            )
        )
        return errors

    if len(nodes) == 0:
        errors.append(
            ValidationError(
                code=ErrorCode.EMPTY_NODES,
                message="'nodes' is empty",
                location="nodes",
                suggestion="Add at least source and output nodes",
            )
        )
        return errors

    # Validate source node
    if "source" not in nodes:
        errors.append(
            ValidationError(
                code=ErrorCode.MISSING_SOURCE,
                message="Missing 'source' node",
                location="nodes",
                suggestion="Add 'source: {}' as the first node",
            )
        )

    # Validate isResult exists
    has_result = False
    for node_name, node_def in nodes.items():
        if node_name == "source":
            continue
        if isinstance(node_def, dict) and node_def.get("isResult"):
            has_result = True
            break

    if not has_result:
        errors.append(
            ValidationError(
                code=ErrorCode.MISSING_RESULT,
                message="No node with 'isResult: true'",
                location="nodes",
                suggestion="Add 'isResult: true' to the final output node",
            )
        )

    return errors


def validate_node_structure(
    node_name: str, node_def: dict[str, Any]
) -> list[ValidationError]:
    """Validate individual node structure.

    Args:
        node_name: Name of the node
        node_def: Node definition dictionary

    Returns:
        List of validation errors (empty if valid)
    """
    errors: list[ValidationError] = []

    # Skip source node
    if node_name == "source":
        return errors

    # Non-source nodes must have an agent
    if "agent" not in node_def:
        errors.append(
            ValidationError(
                code=ErrorCode.INVALID_NODE_DEFINITION,
                message=f"Node '{node_name}' is missing 'agent' field",
                location=f"nodes.{node_name}",
                suggestion=f"Add 'agent: agentType' to node '{node_name}'",
            )
        )
        return errors

    agent = node_def.get("agent")
    if not agent or not isinstance(agent, str):
        errors.append(
            ValidationError(
                code=ErrorCode.INVALID_NODE_DEFINITION,
                message=f"Node '{node_name}' has invalid 'agent' value",
                location=f"nodes.{node_name}.agent",
                suggestion="Agent must be a non-empty string",
            )
        )

    return errors
