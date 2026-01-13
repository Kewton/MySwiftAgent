"""Schema comparator for body_template validation.

Issue #358: Compare required fields against JSON Schema definitions.

This module provides:
- compare_schemas(): Compare required fields against a schema
- field_in_schema(): Check if a field exists in a schema
- SchemaComparisonResult: Container for comparison results
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from . import ValidationError, ValidationErrorCode

logger = logging.getLogger(__name__)


@dataclass
class SchemaComparisonResult:
    """Result of comparing required fields against a schema.

    Attributes:
        is_valid: Whether all required fields exist in schema
        missing_fields: Set of fields not found in schema
        matched_fields: Set of fields found in schema
    """

    is_valid: bool
    missing_fields: set[str] = field(default_factory=set)
    matched_fields: set[str] = field(default_factory=set)

    def to_validation_errors(self, location: str) -> list[ValidationError]:
        """Convert missing fields to ValidationError list.

        Args:
            location: Base location string for errors (e.g., "input_schema")

        Returns:
            List of ValidationError for each missing field
        """
        errors: list[ValidationError] = []
        for field_name in self.missing_fields:
            errors.append(
                ValidationError(
                    code=ValidationErrorCode.VALIDATION_FAILED,
                    message=f"Required field '{field_name}' not found in schema",
                    location=location,
                    suggestion=f"Add '{field_name}' to the schema or update the body_template",
                    severity="major",
                )
            )
        return errors


def compare_schemas(
    required_fields: set[str],
    schema: dict[str, Any],
) -> SchemaComparisonResult:
    """Compare required fields against a JSON Schema.

    Checks if all required fields exist in the schema's properties.
    Supports nested field paths (e.g., "config.api_key").

    Args:
        required_fields: Set of field names/paths to check
        schema: JSON Schema to check against

    Returns:
        SchemaComparisonResult with validation details

    Example:
        >>> schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        >>> result = compare_schemas({"name", "age"}, schema)
        >>> result.is_valid
        False
        >>> "age" in result.missing_fields
        True
    """
    if not required_fields:
        return SchemaComparisonResult(is_valid=True)

    missing: set[str] = set()
    matched: set[str] = set()

    for field_path in required_fields:
        if field_in_schema(field_path, schema):
            matched.add(field_path)
        else:
            missing.add(field_path)

    return SchemaComparisonResult(
        is_valid=len(missing) == 0,
        missing_fields=missing,
        matched_fields=matched,
    )


def field_in_schema(field_path: str, schema: dict[str, Any]) -> bool:
    """Check if a field path exists in a JSON Schema.

    Supports nested paths like "config.api_key" and handles JSON Schema
    structures with "properties" and "type" keys.

    Args:
        field_path: Field path to check (e.g., "user.profile.name")
        schema: JSON Schema to check

    Returns:
        True if the field exists in the schema
    """
    if not schema:
        return False

    parts = field_path.split(".")
    current = schema

    for part in parts:
        # Navigate into properties if present
        if "properties" in current:
            props = current["properties"]
            if part in props:
                current = props[part]
            else:
                return False
        elif part in current:
            current = current[part]
        else:
            return False

    return True


__all__ = [
    "compare_schemas",
    "field_in_schema",
    "SchemaComparisonResult",
]
