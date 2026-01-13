"""TaskFlow Adapter for converting ExpertAgent output to GraphAiServer format.

Issue #355: TaskFlow Adapter Layer implementation.

This module provides the TaskFlowAdapter class that implements the Adapter Pattern
to convert ExpertAgent workflow definitions (which may contain JSON strings)
to GraphAiServer format (which expects objects).

Key conversions:
1. JSON string fields to objects (input_schema, output_schema, output)
2. Full JSON Schema to simplified IOSchema ({"$schema":..., "properties":...} -> {"field": "type"})
3. Remove null fields from step configs
4. Remove fields that don't belong to the step type
5. Convert boolean output values to string references

Design reference: dev-reports/investigation/issue-353-pending-workflow/schema-unification-proposal.md
"""

from __future__ import annotations

import copy
import json
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# Valid IOSchema type values
VALID_IO_SCHEMA_TYPES = {"string", "number", "boolean", "array", "object", "null"}


@dataclass
class ConversionResult:
    """Result of workflow conversion.

    Attributes:
        success: Whether conversion succeeded
        data: Converted workflow data (None if failed)
        errors: List of error messages
        warnings: List of warning messages
    """

    success: bool
    data: dict[str, Any] | None
    errors: list[str]
    warnings: list[str]


class TaskFlowAdapter:
    """Adapter for converting ExpertAgent output to GraphAiServer format.

    Implements the Adapter Pattern to absorb schema differences between
    ExpertAgent (which may output JSON strings for dict fields) and
    GraphAiServer (which expects proper objects).

    Responsibilities:
    1. Convert JSON string fields to objects
    2. Convert full JSON Schema to simplified IOSchema format
    3. Remove null fields from config (GraphAiServer Zod schema doesn't accept extra null fields)
    4. Remove fields that don't belong to the step type
    5. Convert boolean/non-string output values to string representations
    6. Report detailed errors for invalid conversions

    Usage:
        adapter = TaskFlowAdapter()
        result = adapter.convert(workflow_from_llm)
        if result.success:
            await register_workflow(result.data)
        else:
            handle_errors(result.errors)

    Attributes:
        WORKFLOW_JSON_STRING_FIELDS: Fields at workflow level that may be JSON strings
        STEP_JSON_STRING_FIELDS: Fields at step config level that may be JSON strings
        STEP_TYPE_ALLOWED_FIELDS: Allowed fields per step type (matching GraphAiServer Zod schema)
        IO_SCHEMA_FIELDS: Fields that should be IOSchema format
    """

    # Fields at workflow level that may be JSON strings
    WORKFLOW_JSON_STRING_FIELDS = ["input_schema", "output_schema", "output"]

    # Fields that should be IOSchema format (field -> type mapping)
    IO_SCHEMA_FIELDS = {"input_schema", "output_schema"}

    # Fields at step config level that may be JSON strings
    STEP_JSON_STRING_FIELDS = ["body"]

    # Allowed fields per step type (matching GraphAiServer Zod schema)
    # See: graphAiServer/src/engine/schemas/workflow-schema.ts
    STEP_TYPE_ALLOWED_FIELDS: dict[str, set[str]] = {
        "api_rest": {"step_type", "method", "url", "headers", "body", "timeout_ms", "verify_ssl"},
        "code_js": {"step_type", "path", "function_name"},
        "transform": {
            "step_type",
            "mode",
            "template",
            "separator",
            "fields",
            "source_field",
            "strategy",
        },
    }

    def convert(self, workflow: dict[str, Any]) -> ConversionResult:
        """Convert workflow to GraphAiServer format.

        Args:
            workflow: ExpertAgent/LLM-generated workflow definition

        Returns:
            ConversionResult with converted data or errors
        """
        errors: list[str] = []
        warnings: list[str] = []

        try:
            # Deep copy to avoid modifying original data
            result = self._deep_copy(workflow)

            # Step 1: Convert workflow-level JSON string fields
            for field in self.WORKFLOW_JSON_STRING_FIELDS:
                if field in result:
                    converted, error = self._convert_json_string(result[field], field)
                    if error:
                        errors.append(error)
                    else:
                        result[field] = converted

            # Step 2: Convert IOSchema fields (full JSON Schema -> simplified format)
            for field in self.IO_SCHEMA_FIELDS:
                if field in result and isinstance(result[field], dict):
                    converted, field_warnings = self._convert_io_schema(result[field], field)
                    result[field] = converted
                    warnings.extend(field_warnings)

            # Step 3: Clean output field (ensure all values are strings)
            if "output" in result and isinstance(result["output"], dict):
                result["output"], output_warnings = self._clean_output_field(result["output"])
                warnings.extend(output_warnings)

            # Step 4: Convert step-level fields
            if "steps" in result and isinstance(result["steps"], list):
                for i, step in enumerate(result["steps"]):
                    step_errors = self._convert_step(step, i)
                    errors.extend(step_errors)

            # Return result based on errors
            if errors:
                return ConversionResult(
                    success=False,
                    data=None,
                    errors=errors,
                    warnings=warnings,
                )

            return ConversionResult(
                success=True,
                data=result,
                errors=[],
                warnings=warnings,
            )

        except Exception as e:
            logger.exception("Unexpected error during conversion")
            return ConversionResult(
                success=False,
                data=None,
                errors=[f"Unexpected conversion error: {e}"],
                warnings=warnings,
            )

    def _convert_json_string(
        self, value: Any, field_name: str
    ) -> tuple[Any, str | None]:
        """Convert JSON string to object if needed.

        Args:
            value: Value to convert (may be str, dict, or None)
            field_name: Name of the field for error messages

        Returns:
            Tuple of (converted value, error message or None)
        """
        if value is None:
            return None, None

        if isinstance(value, dict):
            # Already an object, return as-is
            return value, None

        if isinstance(value, str):
            try:
                return json.loads(value), None
            except json.JSONDecodeError as e:
                return None, f"{field_name}: Invalid JSON string - {e}"

        # Not a string or dict
        return (
            None,
            f"{field_name}: Expected dict or JSON string, got {type(value).__name__}",
        )

    # Step-level fields that should be removed if null
    # GraphAiServer's Zod schema uses .default({}) which expects undefined, not null
    STEP_NULLABLE_FIELDS = {"params", "description", "input_schema", "output_schema"}

    def _convert_step(self, step: dict[str, Any], index: int) -> list[str]:
        """Convert step-level fields.

        Performs the following conversions:
        1. Convert JSON string fields (body) to objects
        2. Remove null fields from config
        3. Remove fields that don't belong to the step type
        4. Remove null values from step-level fields (params, description, etc.)

        Args:
            step: Step definition
            index: Step index for error messages

        Returns:
            List of error messages (empty if successful)
        """
        errors: list[str] = []
        step_id = step.get("id", f"step_{index}")

        # Step 1: Remove null values from step-level fields
        # GraphAiServer's Zod schema uses .default({}) which expects undefined, not null
        null_step_fields = [k for k, v in step.items() if k in self.STEP_NULLABLE_FIELDS and v is None]
        for field in null_step_fields:
            del step[field]
        if null_step_fields:
            logger.debug(
                "Removed null step-level fields from step %s: %s",
                step_id,
                null_step_fields,
            )

        if "config" not in step:
            return errors

        config = step["config"]
        if not isinstance(config, dict):
            return errors

        # Step 2a: Convert JSON string fields
        for field in self.STEP_JSON_STRING_FIELDS:
            if field in config:
                converted, error = self._convert_json_string(
                    config[field], f"steps[{step_id}].config.{field}"
                )
                if error:
                    # For body field, we log warning but don't fail
                    # GraphAiServer accepts both string and object for body
                    logger.warning(
                        "Step body conversion warning: %s - keeping original value",
                        error,
                    )
                elif converted is not None:
                    config[field] = converted

        # Step 2b: Clean up config - remove null values and step-type-specific fields
        step["config"] = self._clean_config(config, step.get("type"))

        return errors

    def _clean_config(self, config: dict[str, Any], step_type: str | None) -> dict[str, Any]:
        """Clean up step config by removing null values and invalid fields.

        GraphAiServer's Zod schema uses discriminatedUnion for step types.
        Each step type has a specific set of allowed fields, and extra fields
        (including null values for fields from other step types) will cause
        validation errors.

        Args:
            config: Step configuration dict
            step_type: Step type (api_rest, code_js, transform)

        Returns:
            Cleaned config with only valid, non-null fields
        """
        if step_type is None:
            # If step_type is unknown, just remove null values
            return {k: v for k, v in config.items() if v is not None}

        allowed_fields = self.STEP_TYPE_ALLOWED_FIELDS.get(step_type, set())

        # Only keep fields that are:
        # 1. Allowed for this step type
        # 2. Not null
        cleaned = {}
        for key, value in config.items():
            if key in allowed_fields and value is not None:
                cleaned[key] = value

        # Log if fields were removed for debugging
        removed_fields = set(config.keys()) - set(cleaned.keys())
        if removed_fields:
            logger.debug(
                "Removed fields from %s config: %s (null or not allowed for step type)",
                step_type,
                removed_fields,
            )

        return cleaned

    def _deep_copy(self, obj: Any) -> Any:
        """Create a deep copy of the object.

        Args:
            obj: Object to copy

        Returns:
            Deep copy of the object
        """
        return copy.deepcopy(obj)

    def _convert_io_schema(
        self, schema: dict[str, Any], field_name: str
    ) -> tuple[dict[str, str], list[str]]:
        """Convert full JSON Schema format to simplified IOSchema format.

        LLMs may generate full JSON Schema like:
        {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "type": "object",
            "properties": {
                "field1": {"type": "string"},
                "field2": {"type": "number"}
            },
            "required": ["field1"]
        }

        This method converts it to simplified IOSchema:
        {
            "field1": "string",
            "field2": "number"
        }

        If the schema is already in simplified format, it validates and returns as-is.

        Args:
            schema: Input schema (may be full JSON Schema or simplified IOSchema)
            field_name: Name of the field for logging

        Returns:
            Tuple of (converted schema, list of warnings)
        """
        warnings: list[str] = []

        # Check if this is a full JSON Schema (has $schema or properties)
        is_full_json_schema = "$schema" in schema or "properties" in schema

        if is_full_json_schema:
            logger.info(
                "Converting %s from full JSON Schema to IOSchema format",
                field_name,
            )
            return self._extract_io_schema_from_json_schema(schema, field_name)

        # Already in simplified format - validate and normalize
        return self._validate_io_schema(schema, field_name)

    def _extract_io_schema_from_json_schema(
        self, schema: dict[str, Any], field_name: str
    ) -> tuple[dict[str, str], list[str]]:
        """Extract IOSchema from full JSON Schema format.

        Args:
            schema: Full JSON Schema with properties
            field_name: Name of the field for logging

        Returns:
            Tuple of (extracted IOSchema, list of warnings)
        """
        warnings: list[str] = []
        io_schema: dict[str, str] = {}

        # Get properties from JSON Schema
        properties = schema.get("properties", {})

        if not properties:
            # No properties - check if there are direct field->type mappings
            # (excluding JSON Schema keywords)
            json_schema_keywords = {
                "$schema", "$id", "type", "properties", "required",
                "additionalProperties", "description", "title"
            }
            for key, value in schema.items():
                if key not in json_schema_keywords:
                    if isinstance(value, str) and value in VALID_IO_SCHEMA_TYPES:
                        io_schema[key] = value
                    elif isinstance(value, dict) and "type" in value:
                        io_schema[key] = self._extract_type_from_property(value, key)

            if not io_schema:
                warnings.append(
                    f"{field_name}: No properties found in JSON Schema, "
                    "defaulting to empty IOSchema"
                )
            return io_schema, warnings

        # Extract type from each property
        for prop_name, prop_def in properties.items():
            if isinstance(prop_def, dict):
                io_schema[prop_name] = self._extract_type_from_property(prop_def, prop_name)
            elif isinstance(prop_def, str) and prop_def in VALID_IO_SCHEMA_TYPES:
                io_schema[prop_name] = prop_def
            else:
                # Default to string for unknown types
                io_schema[prop_name] = "string"
                warnings.append(
                    f"{field_name}.{prop_name}: Unknown property definition, "
                    f"defaulting to 'string'"
                )

        logger.debug(
            "Converted %s from JSON Schema with %d properties to IOSchema: %s",
            field_name,
            len(properties),
            io_schema,
        )

        return io_schema, warnings

    def _extract_type_from_property(
        self, prop_def: dict[str, Any], prop_name: str
    ) -> str:
        """Extract simple type from JSON Schema property definition.

        Args:
            prop_def: Property definition (e.g., {"type": "string", "description": "..."})
            prop_name: Property name for logging

        Returns:
            Simple type string (string, number, boolean, array, object, null)
        """
        prop_type = prop_def.get("type", "string")

        # Handle array type (JSON Schema may use ["string", "null"])
        if isinstance(prop_type, list):
            # Pick the first non-null type
            for t in prop_type:
                if t != "null" and t in VALID_IO_SCHEMA_TYPES:
                    return t
            return "string"

        # Normalize integer to number
        if prop_type == "integer":
            return "number"

        # Validate and return
        if prop_type in VALID_IO_SCHEMA_TYPES:
            return prop_type

        # Default to string for unknown types
        logger.debug(
            "Property '%s' has unknown type '%s', defaulting to 'string'",
            prop_name,
            prop_type,
        )
        return "string"

    def _validate_io_schema(
        self, schema: dict[str, Any], field_name: str
    ) -> tuple[dict[str, Any], list[str]]:
        """Validate an IOSchema that's already in simplified format.

        This method is conservative - it only validates without modifying
        existing data that doesn't look like JSON Schema.

        Args:
            schema: Simplified IOSchema (field -> type mapping)
            field_name: Name of the field for logging

        Returns:
            Tuple of (validated schema, list of warnings)
        """
        warnings: list[str] = []

        # Check if any value looks like it needs conversion
        needs_conversion = False
        for key, value in schema.items():
            if isinstance(value, dict) and "type" in value:
                # This looks like a JSON Schema property definition
                needs_conversion = True
                break

        if not needs_conversion:
            # Return as-is if it doesn't look like JSON Schema
            return schema, warnings

        # Only convert fields that look like JSON Schema property definitions
        validated: dict[str, Any] = {}
        for key, value in schema.items():
            if isinstance(value, str):
                validated[key] = value
            elif isinstance(value, dict) and "type" in value:
                # This looks like a JSON Schema property definition
                validated[key] = self._extract_type_from_property(value, key)
                warnings.append(
                    f"{field_name}.{key}: Converted JSON Schema property to type"
                )
            else:
                # Keep as-is for unknown structures
                validated[key] = value

        return validated, warnings

    def _clean_output_field(
        self, output: dict[str, Any]
    ) -> tuple[dict[str, str], list[str]]:
        """Clean output field to ensure all values are strings.

        GraphAiServer expects output to be {string: string} mapping.
        LLMs may generate boolean or other types for output values.

        Args:
            output: Output field mapping

        Returns:
            Tuple of (cleaned output, list of warnings)
        """
        warnings: list[str] = []
        cleaned: dict[str, str] = {}

        for key, value in output.items():
            if isinstance(value, str):
                cleaned[key] = value
            elif isinstance(value, bool):
                # Convert boolean to string representation
                cleaned[key] = str(value).lower()
                warnings.append(
                    f"output.{key}: Converted boolean {value} to string '{cleaned[key]}'"
                )
            elif value is None:
                # Skip null values
                warnings.append(f"output.{key}: Skipping null value")
            else:
                # Convert other types to string
                cleaned[key] = str(value)
                warnings.append(
                    f"output.{key}: Converted {type(value).__name__} to string '{cleaned[key]}'"
                )

        return cleaned, warnings
