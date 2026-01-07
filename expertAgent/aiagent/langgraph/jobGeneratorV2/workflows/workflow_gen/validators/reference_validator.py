"""Reference Validator for Workflow Generator V2.

This module validates node references (:node.path format).

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

from __future__ import annotations

import re
from typing import Any

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.errors import (
    ErrorCode,
    ValidationError,
)

# Pattern to match references like :source, :node.path, :node.result.field
# The node name must start with a letter (not a number like in :8004 from URLs)
REFERENCE_PATTERN = re.compile(r":([a-zA-Z_]\w*)(?:\.[\w\[\]]+)*")


def validate_references(nodes: dict[str, Any]) -> list[ValidationError]:
    """Validate all node references in the workflow.

    Args:
        nodes: Nodes dictionary from parsed YAML

    Returns:
        List of validation errors for invalid references
    """
    errors: list[ValidationError] = []
    defined_nodes = set(nodes.keys())

    for node_name, node_def in nodes.items():
        if node_name == "source":
            continue

        if not isinstance(node_def, dict):
            continue

        # Validate references in inputs
        inputs = node_def.get("inputs")
        if inputs:
            ref_errors = _validate_references_in_dict(
                inputs,
                defined_nodes,
                f"nodes.{node_name}.inputs",
            )
            errors.extend(ref_errors)

        # Validate references in params
        params = node_def.get("params")
        if params:
            ref_errors = _validate_references_in_dict(
                params,
                defined_nodes,
                f"nodes.{node_name}.params",
            )
            errors.extend(ref_errors)

        # Validate references in nested graph
        graph = node_def.get("graph")
        if graph and isinstance(graph, dict):
            nested_nodes = graph.get("nodes", {})
            # Add special nested source nodes to defined set
            nested_defined = defined_nodes.copy()
            for nested_name in nested_nodes:
                nested_defined.add(nested_name)
            # Also add common nested source aliases
            nested_defined.update(["row", "item", "item_source"])

            nested_errors = _validate_nested_references(
                nested_nodes,
                nested_defined,
                f"nodes.{node_name}.graph",
            )
            errors.extend(nested_errors)

    return errors


def _validate_references_in_dict(
    data: dict[str, Any] | Any,
    defined_nodes: set[str],
    location_prefix: str,
) -> list[ValidationError]:
    """Validate references in a dictionary structure.

    Args:
        data: Dictionary or value to scan for references
        defined_nodes: Set of defined node names
        location_prefix: Prefix for error location

    Returns:
        List of validation errors
    """
    errors: list[ValidationError] = []

    if isinstance(data, dict):
        for key, value in data.items():
            sub_errors = _validate_references_in_dict(
                value,
                defined_nodes,
                f"{location_prefix}.{key}",
            )
            errors.extend(sub_errors)

    elif isinstance(data, list):
        for i, item in enumerate(data):
            sub_errors = _validate_references_in_dict(
                item,
                defined_nodes,
                f"{location_prefix}[{i}]",
            )
            errors.extend(sub_errors)

    elif isinstance(data, str):
        # Find all references in the string
        matches = REFERENCE_PATTERN.findall(data)
        for ref_node in matches:
            if ref_node not in defined_nodes:
                errors.append(
                    ValidationError(
                        code=ErrorCode.UNDEFINED_NODE_REFERENCE,
                        message=f"Reference to undefined node ':{ref_node}'",
                        location=location_prefix,
                        suggestion=f"Ensure node '{ref_node}' is defined in 'nodes'. "
                        f"Defined nodes: {', '.join(sorted(defined_nodes))}",
                    )
                )

    return errors


def _validate_nested_references(
    nested_nodes: dict[str, Any],
    defined_nodes: set[str],
    location_prefix: str,
) -> list[ValidationError]:
    """Validate references in nested graph nodes.

    Args:
        nested_nodes: Nested nodes dictionary
        defined_nodes: Set of defined node names (including parent nodes)
        location_prefix: Prefix for error location

    Returns:
        List of validation errors
    """
    errors: list[ValidationError] = []

    for node_name, node_def in nested_nodes.items():
        if node_name in ("source", "item_source") or node_name.endswith("_source"):
            continue

        if not isinstance(node_def, dict):
            continue

        # Validate references in inputs
        inputs = node_def.get("inputs")
        if inputs:
            ref_errors = _validate_references_in_dict(
                inputs,
                defined_nodes,
                f"{location_prefix}.nodes.{node_name}.inputs",
            )
            errors.extend(ref_errors)

        # Validate references in params
        params = node_def.get("params")
        if params:
            ref_errors = _validate_references_in_dict(
                params,
                defined_nodes,
                f"{location_prefix}.nodes.{node_name}.params",
            )
            errors.extend(ref_errors)

    return errors


def extract_references(yaml_content: str) -> list[str]:
    """Extract all node references from YAML content.

    Args:
        yaml_content: YAML string

    Returns:
        List of referenced node names
    """
    matches = REFERENCE_PATTERN.findall(yaml_content)
    return list(set(matches))


def check_circular_references(nodes: dict[str, Any]) -> list[ValidationError]:
    """Check for circular references in node dependencies.

    Args:
        nodes: Nodes dictionary from parsed YAML

    Returns:
        List of validation errors for circular references
    """
    errors: list[ValidationError] = []

    # Build dependency graph
    dependencies: dict[str, set[str]] = {}
    for node_name, node_def in nodes.items():
        if node_name == "source":
            dependencies[node_name] = set()
            continue

        if not isinstance(node_def, dict):
            dependencies[node_name] = set()
            continue

        deps: set[str] = set()

        # Extract dependencies from inputs
        inputs = node_def.get("inputs", {})
        if isinstance(inputs, dict):
            for value in _extract_string_values(inputs):
                refs = REFERENCE_PATTERN.findall(value)
                deps.update(refs)

        # Extract dependencies from params
        params = node_def.get("params", {})
        if isinstance(params, dict):
            for value in _extract_string_values(params):
                refs = REFERENCE_PATTERN.findall(value)
                deps.update(refs)

        dependencies[node_name] = deps

    # Check for cycles using DFS
    visited: set[str] = set()
    rec_stack: set[str] = set()

    def has_cycle(node: str, path: list[str]) -> list[str] | None:
        """Check if there's a cycle starting from node."""
        if node in rec_stack:
            return path + [node]
        if node in visited:
            return None

        visited.add(node)
        rec_stack.add(node)

        for dep in dependencies.get(node, set()):
            if dep in dependencies:
                cycle = has_cycle(dep, path + [node])
                if cycle:
                    return cycle

        rec_stack.remove(node)
        return None

    for node_name in dependencies:
        if node_name not in visited:
            cycle = has_cycle(node_name, [])
            if cycle:
                cycle_str = " -> ".join(cycle)
                errors.append(
                    ValidationError(
                        code=ErrorCode.CIRCULAR_REFERENCE,
                        message=f"Circular reference detected: {cycle_str}",
                        location="nodes",
                        suggestion="Reorganize node dependencies to break the cycle",
                    )
                )
                break  # Only report first cycle

    return errors


def _extract_string_values(data: Any) -> list[str]:
    """Extract all string values from a nested structure.

    Args:
        data: Data structure to extract from

    Returns:
        List of string values
    """
    strings: list[str] = []

    if isinstance(data, str):
        strings.append(data)
    elif isinstance(data, dict):
        for value in data.values():
            strings.extend(_extract_string_values(value))
    elif isinstance(data, list):
        for item in data:
            strings.extend(_extract_string_values(item))

    return strings
