"""Schema conversion utilities for interface format transformation.

Issue #388: Extract schema conversion logic to dedicated module.

This module provides bidirectional conversion between:
- JSON Schema format: {"type": "object", "properties": {"email": {"type": "string"}}}
- Simple Mapping format: {"email": "string"}

Note: Conversion from JSON Schema to Simple Mapping is lossy.
      Information such as required fields, descriptions, formats,
      nested structures, and array item types are lost.
"""

import logging
from typing import Any, TypeAlias

logger = logging.getLogger(__name__)

# Type aliases for clarity
JsonSchema: TypeAlias = dict[str, Any]
SimpleMapping: TypeAlias = dict[str, str]


def json_schema_to_simple_mapping(schema: JsonSchema) -> SimpleMapping:
    """Convert JSON Schema to simple {field_name: type} mapping.

    Args:
        schema: JSON Schema object
            Example: {"type": "object", "properties": {"email": {"type": "string"}}}

    Returns:
        Simple mapping
            Example: {"email": "string"}

    Note:
        Information loss occurs for: required, description, format,
        nested structures, array item types. These are logged at DEBUG level.
    """
    if not schema:
        return {}

    # If it's already a simple mapping (no "properties" key), return as-is
    if "properties" not in schema:
        # Check if it looks like a simple mapping
        if all(isinstance(v, str) for v in schema.values()):
            return schema
        logger.debug(
            "Schema has no 'properties' key and mixed value types, returning empty"
        )
        return {}

    # Log information loss at debug level
    _log_information_loss(schema)

    # Extract types from properties
    properties = schema.get("properties", {})
    simple_mapping: SimpleMapping = {}
    for field_name, field_def in properties.items():
        if isinstance(field_def, dict):
            field_type = field_def.get("type", "string")
            simple_mapping[field_name] = field_type

            # Log nested structure loss
            if field_type == "object" and "properties" in field_def:
                logger.debug(
                    "Nested structure lost for field '%s': %s",
                    field_name,
                    list(field_def.get("properties", {}).keys()),
                )
            # Log array item type loss
            if field_type == "array" and "items" in field_def:
                logger.debug(
                    "Array item type lost for field '%s': %s",
                    field_name,
                    field_def.get("items"),
                )
        elif isinstance(field_def, str):
            simple_mapping[field_name] = field_def

    return simple_mapping


def simple_mapping_to_json_schema(mapping: SimpleMapping) -> JsonSchema:
    """Convert simple mapping back to minimal JSON Schema.

    Args:
        mapping: Simple field:type mapping
            Example: {"email": "string"}

    Returns:
        Minimal JSON Schema
            Example: {"type": "object", "properties": {"email": {"type": "string"}}}

    Note:
        This is a lossy reconstruction - original metadata cannot be recovered.
    """
    if not mapping:
        return {}

    properties: dict[str, dict[str, str]] = {}
    for field_name, field_type in mapping.items():
        properties[field_name] = {"type": field_type}

    return {
        "type": "object",
        "properties": properties,
    }


def _log_information_loss(schema: JsonSchema) -> None:
    """Log information that will be lost during conversion.

    Args:
        schema: JSON Schema to analyze for information loss
    """
    # Log required fields loss
    if "required" in schema:
        logger.debug(
            "Information loss: required fields will not be preserved: %s",
            schema["required"],
        )

    # Log description loss at schema level
    if "description" in schema:
        logger.debug(
            "Information loss: schema description will not be preserved: %s",
            schema["description"][:50] + "..."
            if len(schema.get("description", "")) > 50
            else schema["description"],
        )

    # Log property-level information loss
    properties = schema.get("properties", {})
    for field_name, field_def in properties.items():
        if isinstance(field_def, dict):
            if "description" in field_def:
                logger.debug(
                    "Information loss: description for field '%s' will not be preserved",
                    field_name,
                )
            if "format" in field_def:
                logger.debug(
                    "Information loss: format '%s' for field '%s' will not be preserved",
                    field_def["format"],
                    field_name,
                )
            if "enum" in field_def:
                logger.debug(
                    "Information loss: enum values for field '%s' will not be preserved: %s",
                    field_name,
                    field_def["enum"],
                )


# Re-export for convenient imports
__all__ = [
    "JsonSchema",
    "SimpleMapping",
    "json_schema_to_simple_mapping",
    "simple_mapping_to_json_schema",
]
