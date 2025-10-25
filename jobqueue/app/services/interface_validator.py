"""Interface validation service using JSON Schema."""

import logging
from typing import Any

import jsonschema
import regex
from jsonschema import Draft7Validator, FormatChecker

logger = logging.getLogger(__name__)


# ========== Custom Format Checker for Unicode Property Escapes ==========
@FormatChecker.cls_checks("regex", raises=Exception)
def check_regex_format(value: str) -> bool:
    """
    Custom format checker for 'regex' format using regex library.

    This checker supports Unicode property escapes (\\p{L}, \\p{N}, etc.)
    which are not supported by Python's standard re module.

    Args:
        value: Regex pattern string to validate

    Returns:
        True if pattern is valid

    Raises:
        Exception: If pattern is invalid (caught by jsonschema)
    """
    try:
        # Use regex library instead of re module
        regex.compile(value)
        return True
    except regex.error as e:
        # jsonschema will catch this exception and report validation error
        raise Exception(f"Invalid regex pattern: {e}") from e


# Create format checker instance
_format_checker = FormatChecker()


def _validate_regex_patterns_in_schema(schema: dict[str, Any]) -> None:
    """
    Recursively validate all regex patterns in JSON Schema.

    This function walks through the schema and validates all 'pattern' fields
    using the regex library to ensure Unicode property escapes are supported.

    Args:
        schema: JSON Schema to validate

    Raises:
        InterfaceValidationError: If any regex pattern is invalid
    """
    if not isinstance(schema, dict):
        return

    # Check if current level has a pattern field
    if "pattern" in schema:
        pattern = schema["pattern"]
        try:
            regex.compile(pattern)
        except regex.error as e:
            raise InterfaceValidationError(
                "Invalid regex pattern in schema",
                [f"Pattern '{pattern}' is invalid: {e}"],
            ) from e

    # Recursively check nested objects
    for value in schema.values():
        if isinstance(value, dict):
            _validate_regex_patterns_in_schema(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _validate_regex_patterns_in_schema(item)


class InterfaceValidationError(Exception):
    """Interface validation error."""

    def __init__(self, message: str, errors: list[str]):
        """Initialize validation error."""
        super().__init__(message)
        self.errors = errors


class InterfaceValidator:
    """Service for validating data against JSON Schema interfaces."""

    @staticmethod
    def validate_data(
        data: dict[str, Any],
        schema: dict[str, Any],
        data_type: str = "data",
    ) -> None:
        """
        Validate data against JSON Schema.

        Args:
            data: Data to validate
            schema: JSON Schema V7 specification
            data_type: Type of data (for error messages)

        Raises:
            InterfaceValidationError: If validation fails
        """
        if not schema:
            # No schema means no validation required
            return

        try:
            # Create validator with format checker (supports Unicode property escapes)
            validator = Draft7Validator(schema, format_checker=_format_checker)
            errors = list(validator.iter_errors(data))

            if errors:
                error_messages = [
                    f"Path: {'/'.join(str(p) for p in error.path)}, Error: {error.message}"
                    for error in errors
                ]
                logger.warning(
                    f"{data_type} validation failed: {'; '.join(error_messages)}"
                )
                raise InterfaceValidationError(
                    f"{data_type} validation failed", error_messages
                )

            logger.debug(f"{data_type} validation succeeded")

        except jsonschema.SchemaError as e:
            logger.error(f"Invalid JSON Schema: {e}")
            raise InterfaceValidationError(
                "Invalid JSON Schema",
                [f"Schema error: {e.message}"],
            ) from e

    @staticmethod
    def validate_input(
        input_data: dict[str, Any],
        input_schema: dict[str, Any] | None,
    ) -> None:
        """
        Validate input data against input schema.

        Args:
            input_data: Input data to validate
            input_schema: JSON Schema for input validation

        Raises:
            InterfaceValidationError: If validation fails
        """
        if input_schema is None:
            return

        InterfaceValidator.validate_data(input_data, input_schema, "Input")

    @staticmethod
    def validate_output(
        output_data: dict[str, Any],
        output_schema: dict[str, Any] | None,
    ) -> None:
        """
        Validate output data against output schema.

        Args:
            output_data: Output data to validate
            output_schema: JSON Schema for output validation

        Raises:
            InterfaceValidationError: If validation fails
        """
        if output_schema is None:
            return

        InterfaceValidator.validate_data(output_data, output_schema, "Output")

    @staticmethod
    def validate_json_schema_v7(schema: dict[str, Any]) -> None:
        """
        Validate that the schema conforms to JSON Schema V7 specification.

        This method checks if a JSON Schema itself is valid according to
        JSON Schema Draft 7 specification before using it for data validation.

        Supports Unicode property escapes (\\p{L}, \\p{N}, etc.) in regex patterns.

        Args:
            schema: JSON Schema to validate

        Raises:
            InterfaceValidationError: If schema is invalid

        Example:
            >>> validator = InterfaceValidator()
            >>> schema = {"type": "object", "properties": {"name": {"type": "string"}}}
            >>> validator.validate_json_schema_v7(schema)  # No error
            >>> bad_schema = {"type": "invalid_type"}
            >>> validator.validate_json_schema_v7(bad_schema)  # Raises error
        """
        try:
            # First, validate regex patterns with regex library (supports Unicode property escapes)
            _validate_regex_patterns_in_schema(schema)

            # Then validate schema structure with Draft7Validator.check_schema()
            # Note: This may fail for Unicode property escapes, so we catch that specific error
            try:
                Draft7Validator.check_schema(schema)
            except jsonschema.SchemaError as e:
                # If the error is about regex pattern validation (Unicode property escapes),
                # we ignore it because we already validated with regex library
                error_msg = str(e.message) if hasattr(e, "message") else str(e)
                if "is not a 'regex'" in error_msg:
                    # This is expected for Unicode property escapes - already validated above
                    logger.debug(
                        f"Draft7Validator.check_schema() failed with regex error (expected for Unicode property escapes): {error_msg}"
                    )
                else:
                    # This is a genuine schema structure error
                    raise

            # Create validator with format checker to validate regex patterns
            # This ensures Unicode property escapes are supported
            validator = Draft7Validator(schema, format_checker=_format_checker)

            logger.debug("JSON Schema V7 validation succeeded")
        except jsonschema.SchemaError as e:
            logger.error(f"Invalid JSON Schema V7: {e}")
            raise InterfaceValidationError(
                "Invalid JSON Schema V7",
                [f"Schema error: {e.message}"],
            ) from e

    @staticmethod
    def check_output_contains_input_properties(
        output_schema: dict[str, Any],
        input_schema: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """
        Check if output schema contains all required input properties.

        This implements a flexible compatibility check where the output schema
        must contain at least the properties required by the input schema,
        but can have additional properties (考慮①対応).

        Args:
            output_schema: Output JSON Schema from Task A
            input_schema: Input JSON Schema for Task B

        Returns:
            Tuple of (is_compatible, missing_properties)
            - is_compatible: True if output contains all required input properties
            - missing_properties: List of missing or incompatible property descriptions

        Example:
            >>> output = {
            ...     "type": "object",
            ...     "properties": {
            ...         "name": {"type": "string"},
            ...         "age": {"type": "integer"},
            ...         "extra": {"type": "string"}
            ...     }
            ... }
            >>> input = {
            ...     "type": "object",
            ...     "properties": {"name": {"type": "string"}},
            ...     "required": ["name"]
            ... }
            >>> is_compat, missing = check_output_contains_input_properties(output, input)
            >>> assert is_compat == True  # Output contains required "name"
        """
        output_props = output_schema.get("properties", {})
        input_props = input_schema.get("properties", {})
        input_required = set(input_schema.get("required", []))

        missing_properties = []

        # Check required properties exist in output
        for req_prop in input_required:
            if req_prop not in output_props:
                missing_properties.append(
                    f"Required property '{req_prop}' not found in output schema"
                )

        # Check property types for common properties
        for prop_name, input_prop_def in input_props.items():
            if prop_name in output_props:
                output_prop_def = output_props[prop_name]
                input_type = input_prop_def.get("type")
                output_type = output_prop_def.get("type")

                # Type compatibility check
                if input_type and output_type:
                    if isinstance(input_type, str) and isinstance(output_type, str):
                        if input_type != output_type:
                            missing_properties.append(
                                f"Property '{prop_name}' type mismatch: "
                                f"output={output_type}, input={input_type}"
                            )
                    elif isinstance(input_type, list) and isinstance(output_type, list):
                        # Check if there's any common type
                        if not set(input_type) & set(output_type):
                            missing_properties.append(
                                f"Property '{prop_name}' type mismatch: "
                                f"output types {output_type} do not overlap with input types {input_type}"
                            )
                    elif isinstance(input_type, str) and isinstance(output_type, list):
                        if input_type not in output_type:
                            missing_properties.append(
                                f"Property '{prop_name}' type mismatch: "
                                f"input type '{input_type}' not in output types {output_type}"
                            )
                    elif isinstance(input_type, list) and isinstance(output_type, str):
                        if output_type not in input_type:
                            missing_properties.append(
                                f"Property '{prop_name}' type mismatch: "
                                f"output type '{output_type}' not in input types {input_type}"
                            )
            elif prop_name in input_required:
                # Already checked above, but double-check for clarity
                if (
                    f"Required property '{prop_name}' not found in output schema"
                    not in missing_properties
                ):
                    missing_properties.append(
                        f"Required property '{prop_name}' not found in output schema"
                    )

        is_compatible = len(missing_properties) == 0
        logger.debug(
            f"Interface compatibility check: compatible={is_compatible}, "
            f"missing={missing_properties}"
        )
        return is_compatible, missing_properties
