"""Template validator for derived fields (Issue #337).

This module provides utilities for validating template strings used in
derived fields, including variable extraction and source resolution.

Template Variable Resolution Rules:
1. If variable exists in same task's output_schema.properties -> use task output
2. If variable not in properties -> assumed from source.user_input
3. If source_mapping is provided -> use explicit mapping
"""

import re
from typing import Any


def get_template_variables(template: str) -> list[str]:
    """Extract variable names from a template string.

    Variables are identified by {variable_name} patterns.

    Args:
        template: Template string with {variable} placeholders

    Returns:
        List of variable names found in the template

    Example:
        >>> get_template_variables("Hello {name}, your score is {score}")
        ['name', 'score']
    """
    return re.findall(r"\{([^}]+)\}", template)


def validate_template(
    template: str,
    properties: dict[str, Any],
    source_mapping: dict[str, str] | None = None,
) -> list[str]:
    """Validate a template and return unresolved variables.

    A variable is considered resolved if:
    1. It exists in source_mapping (explicit resolution)
    2. It exists in properties (from same task's output)

    Variables not resolved by the above are assumed to come from
    source.user_input, which is a warning (not error) case.

    Args:
        template: Template string with {variable} placeholders
        properties: The output_schema.properties dict
        source_mapping: Optional explicit variable-to-path mapping

    Returns:
        List of unresolved variable names (from source.user_input)

    Example:
        >>> validate_template(
        ...     "{summary} for {query}",
        ...     {"summary": {"type": "string"}},
        ...     None
        ... )
        ['query']  # query is not in properties, assumed from source.user_input
    """
    variables = get_template_variables(template)
    unresolved: list[str] = []

    for var in variables:
        # Check if explicitly mapped
        if source_mapping and var in source_mapping:
            continue

        # Check if exists in properties
        if var in properties:
            continue

        # Variable will be resolved from source.user_input (warning case)
        unresolved.append(var)

    return unresolved


def validate_derived_fields(output_schema: dict[str, Any]) -> list[dict[str, Any]]:
    """Validate all x-derived-fields in an output schema.

    Checks each derived field's template for unresolved variables.
    Unresolved variables are not errors - they are assumed to come from
    source.user_input - but a warning is generated.

    Args:
        output_schema: The output_schema dict containing x-derived-fields

    Returns:
        List of validation results for fields with unresolved variables.
        Each result is a dict with:
        - field: The derived field name
        - unresolved_variables: List of unresolved variable names
        - message: Human-readable warning message

    Example:
        >>> validate_derived_fields({
        ...     "properties": {"summary": {"type": "string"}},
        ...     "x-derived-fields": {
        ...         "email_subject": {"template": "Results for {query}"}
        ...     }
        ... })
        [{'field': 'email_subject', 'unresolved_variables': ['query'],
          'message': "Variables ['query'] are not in properties..."}]
    """
    errors: list[dict[str, Any]] = []
    derived_fields = output_schema.get("x-derived-fields", {})
    properties = output_schema.get("properties", {})

    for field_name, field_def in derived_fields.items():
        template = field_def.get("template", "")
        source_mapping = field_def.get("source_mapping")

        unresolved = validate_template(template, properties, source_mapping)

        if unresolved:
            errors.append(
                {
                    "field": field_name,
                    "unresolved_variables": unresolved,
                    "message": (
                        f"Variables {unresolved} are not in properties "
                        f"and will be retrieved from source.user_input"
                    ),
                }
            )

    return errors
