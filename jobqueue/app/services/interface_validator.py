"""Interface validation service using JSON Schema."""

import logging
from typing import Any

import jsonschema
from jsonschema import Draft7Validator

logger = logging.getLogger(__name__)


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
            # Create validator and validate
            validator = Draft7Validator(schema)
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
