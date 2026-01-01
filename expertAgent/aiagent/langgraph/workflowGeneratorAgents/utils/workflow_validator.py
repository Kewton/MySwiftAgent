"""Workflow output node validation for Issue #338.

This module provides validation functions to ensure generated workflow YAML
follows the output node naming convention:
- Output node MUST be named 'output'
- Output node MUST have isResult: true

This enforces interface contracts in task chains.
"""

import logging
from dataclasses import dataclass, field

import yaml

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of workflow output node validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_output_node_convention(yaml_content: str) -> ValidationResult:
    """Validate that workflow YAML follows output node naming convention.

    This function checks:
    1. YAML syntax is valid
    2. 'nodes' section exists
    3. 'output' node exists
    4. 'output' node has isResult: true

    Args:
        yaml_content: GraphAI workflow YAML content

    Returns:
        ValidationResult with is_valid, errors, and warnings
    """
    errors: list[str] = []
    warnings: list[str] = []

    # Check for empty content
    if not yaml_content or not yaml_content.strip():
        return ValidationResult(
            is_valid=False,
            errors=["Empty YAML content provided"],
            warnings=[],
        )

    # Parse YAML
    try:
        workflow = yaml.safe_load(yaml_content)
    except yaml.YAMLError as e:
        return ValidationResult(
            is_valid=False,
            errors=[f"Invalid YAML syntax: {e}"],
            warnings=[],
        )

    # Check for valid structure
    if not isinstance(workflow, dict):
        return ValidationResult(
            is_valid=False,
            errors=["YAML content is not a valid dictionary structure"],
            warnings=[],
        )

    # Check for nodes section
    nodes = workflow.get("nodes")
    if not nodes:
        return ValidationResult(
            is_valid=False,
            errors=["No 'nodes' section found in workflow YAML"],
            warnings=[],
        )

    if not isinstance(nodes, dict):
        return ValidationResult(
            is_valid=False,
            errors=["'nodes' section is not a dictionary"],
            warnings=[],
        )

    # Check for output node
    if "output" not in nodes:
        # Find any node with isResult: true for the error message
        is_result_nodes = []
        for node_name, node_def in nodes.items():
            if isinstance(node_def, dict) and node_def.get("isResult") is True:
                is_result_nodes.append(node_name)

        error_msg = (
            "Missing required 'output' node. "
            "Workflow must have a node named 'output' with isResult: true."
        )
        if is_result_nodes:
            error_msg += (
                f" Found isResult: true on node(s): {', '.join(is_result_nodes)}. "
            )
            error_msg += "Please rename to 'output'."

        return ValidationResult(
            is_valid=False,
            errors=[error_msg],
            warnings=[],
        )

    # Check output node has isResult: true
    output_node = nodes.get("output")
    if not isinstance(output_node, dict):
        return ValidationResult(
            is_valid=False,
            errors=["'output' node is not a valid dictionary"],
            warnings=[],
        )

    is_result = output_node.get("isResult")
    if is_result is not True:
        if is_result is False:
            errors.append(
                "Output node has isResult: false. "
                "The 'output' node must have isResult: true."
            )
        elif is_result is None:
            errors.append(
                "Output node is missing isResult attribute. "
                "The 'output' node must have isResult: true."
            )
        else:
            errors.append(
                f"Output node has invalid isResult value: {is_result}. "
                "Must be 'true' (boolean)."
            )

    if errors:
        return ValidationResult(
            is_valid=False,
            errors=errors,
            warnings=warnings,
        )

    # Check for multiple isResult: true nodes (warning only)
    is_result_count = 0
    is_result_nodes = []
    for node_name, node_def in nodes.items():
        if isinstance(node_def, dict) and node_def.get("isResult") is True:
            is_result_count += 1
            is_result_nodes.append(node_name)

    if is_result_count > 1:
        warnings.append(
            f"Multiple nodes have isResult: true ({', '.join(is_result_nodes)}). "
            "Only the 'output' node should have isResult: true for clear data flow."
        )

    logger.info(
        f"Workflow validation passed: output node found with isResult: true. "
        f"Warnings: {len(warnings)}"
    )

    return ValidationResult(
        is_valid=True,
        errors=[],
        warnings=warnings,
    )
