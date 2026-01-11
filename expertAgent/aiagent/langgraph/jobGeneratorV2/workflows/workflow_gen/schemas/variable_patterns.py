"""TaskFlow V2 Variable Pattern Definitions.

Issue #351: Centralized variable pattern definitions for TaskFlow V2.

This module provides:
- TASKFLOW_VARIABLE_PATTERN: Compiled regex for variable references
- contains_variable_reference(): Check if value contains variables
- replace_variables_with_placeholder(): Replace variables for validation
- mask_secret_references(): Mask ${secrets.*} for logging
- validate_variable_syntax(): Validate variable syntax
"""

from __future__ import annotations

import re

# TaskFlow V2 variable reference pattern (MF-1: Unified pattern with hyphen support)
# Matches: ${inputs.query}, ${step_001.output}, ${step-001.output.data.name}, ${secrets.API_KEY}
# Pattern breakdown:
#   \$\{                           - Literal ${
#   [a-zA-Z_][a-zA-Z0-9_-]*        - Identifier (starts with letter/underscore, allows hyphen)
#   (?:\.[a-zA-Z_][a-zA-Z0-9_-]*)* - Optional dot-separated nested identifiers
#   \}                             - Literal }
TASKFLOW_VARIABLE_PATTERN = re.compile(
    r"\$\{[a-zA-Z_][a-zA-Z0-9_-]*(?:\.[a-zA-Z_][a-zA-Z0-9_-]*)*\}"
)

# Placeholder used during JSON validation (without quotes since variable refs are inside strings)
_VALIDATION_PLACEHOLDER = "__TASKFLOW_VAR_PLACEHOLDER__"


def contains_variable_reference(value: str) -> bool:
    """Check if value contains TaskFlow variable references.

    Args:
        value: String to check

    Returns:
        True if value contains ${...} variable references

    Example:
        >>> contains_variable_reference('{"result": "${step.output}"}')
        True
        >>> contains_variable_reference('{"result": "static"}')
        False
    """
    return bool(TASKFLOW_VARIABLE_PATTERN.search(value))


def replace_variables_with_placeholder(value: str) -> str:
    """Replace variable references with valid JSON placeholder.

    Used during validation to check JSON structure while allowing variables.

    Args:
        value: JSON string potentially containing variable references

    Returns:
        String with variables replaced by placeholder

    Example:
        >>> replace_variables_with_placeholder('{"result": "${step.output}"}')
        '{"result": "__TASKFLOW_VAR_PLACEHOLDER__"}'
    """
    return TASKFLOW_VARIABLE_PATTERN.sub(_VALIDATION_PLACEHOLDER, value)


def mask_secret_references(value: str) -> str:
    """Mask secret references for safe logging.

    Replaces ${secrets.KEY_NAME} with ${secrets.***} to prevent
    secret key names from appearing in logs.

    Args:
        value: String potentially containing secret references

    Returns:
        String with secret references masked

    Example:
        >>> mask_secret_references('Bearer ${secrets.API_TOKEN}')
        'Bearer ${secrets.***}'
    """
    return re.sub(r"\$\{secrets\.[^}]+\}", "${secrets.***}", value)


def validate_variable_syntax(value: str) -> list[str]:
    """Validate that all ${...} patterns have valid variable syntax.

    Returns list of invalid variable references found. Empty list means
    all variable references are valid.

    Args:
        value: String to validate

    Returns:
        List of invalid variable reference strings

    Example:
        >>> validate_variable_syntax('${valid.ref} and ${123invalid}')
        ['${123invalid}']
    """
    # Find all ${...} patterns (including potentially invalid ones)
    all_refs = re.findall(r"\$\{([^}]*)\}", value)
    invalid = []
    valid_pattern = re.compile(
        r"^[a-zA-Z_][a-zA-Z0-9_-]*(?:\.[a-zA-Z_][a-zA-Z0-9_-]*)*$"
    )
    for ref in all_refs:
        if not valid_pattern.match(ref):
            invalid.append(f"${{{ref}}}")
    return invalid


__all__ = [
    "TASKFLOW_VARIABLE_PATTERN",
    "contains_variable_reference",
    "replace_variables_with_placeholder",
    "mask_secret_references",
    "validate_variable_syntax",
]
