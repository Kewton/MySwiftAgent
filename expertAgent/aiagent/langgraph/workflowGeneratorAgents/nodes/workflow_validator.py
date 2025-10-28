"""Workflow schema validator using Pydantic dynamic model generation.

This module validates workflow inputs/outputs against interface schemas before
GraphAI execution, catching schema mismatches early in the generation process.

Key features:
- Dynamic Pydantic model generation from JSON Schema
- Input/output schema validation
- Detailed validation error reporting
- Pre-execution schema verification

Usage:
    validator = WorkflowSchemaValidator(input_schema, output_schema)
    validation_result = validator.validate_input(sample_input)
"""

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError, create_model

logger = logging.getLogger(__name__)


class SchemaValidationResult(BaseModel):
    """Result of schema validation"""

    is_valid: bool = Field(..., description="Whether validation passed")
    errors: List[str] = Field(
        default_factory=list, description="List of validation errors"
    )
    warnings: List[str] = Field(
        default_factory=list, description="List of validation warnings"
    )
    validated_data: Optional[Dict[str, Any]] = Field(
        None, description="Validated and coerced data"
    )


class WorkflowSchemaValidator:
    """Validates workflow inputs/outputs against JSON Schema using Pydantic"""

    def __init__(
        self,
        input_schema: Dict[str, Any],
        output_schema: Dict[str, Any],
    ):
        """Initialize validator with interface schemas.

        Args:
            input_schema: JSON Schema for workflow input
            output_schema: JSON Schema for workflow output
        """
        self.input_schema = input_schema
        self.output_schema = output_schema
        self._input_model: Optional[type[BaseModel]] = None
        self._output_model: Optional[type[BaseModel]] = None

    def _json_schema_type_to_python(self, json_type: str) -> type:
        """Convert JSON Schema type to Python type.

        Args:
            json_type: JSON Schema type string

        Returns:
            Corresponding Python type
        """
        type_mapping = {
            "string": str,
            "integer": int,
            "number": float,
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        return type_mapping.get(json_type, Any)

    def _build_pydantic_model(
        self, schema: Dict[str, Any], model_name: str
    ) -> type[BaseModel]:
        """Build Pydantic model from JSON Schema.

        Args:
            schema: JSON Schema definition
            model_name: Name for the generated Pydantic model

        Returns:
            Dynamically generated Pydantic model class
        """
        if schema.get("type") != "object":
            logger.warning(
                "Schema type is not 'object', using Any type for model %s", model_name
            )
            return create_model(model_name, __root__=(Any, ...))

        properties = schema.get("properties", {})
        required_fields = set(schema.get("required", []))

        # Build field definitions for Pydantic model
        field_definitions: Dict[str, tuple[type, Any]] = {}

        for field_name, field_def in properties.items():
            field_type_str = field_def.get("type", "string")
            field_type = self._json_schema_type_to_python(field_type_str)

            # Handle optional fields
            if field_name not in required_fields:
                field_type = Optional[field_type]  # type: ignore
                default_value = field_def.get("default", None)
            else:
                default_value = ...  # Required field marker

            # Add field description
            field_description = field_def.get("description", f"{field_name} field")
            field_definitions[field_name] = (
                field_type,
                Field(default_value, description=field_description),
            )

        # Create dynamic Pydantic model
        model: type[BaseModel] = create_model(model_name, **field_definitions)  # type: ignore
        logger.debug(
            "Built Pydantic model '%s' with %d fields",
            model_name,
            len(field_definitions),
        )
        return model

    def _get_input_model(self) -> type[BaseModel]:
        """Get or create input validation model.

        Returns:
            Pydantic model for input validation
        """
        if self._input_model is None:
            self._input_model = self._build_pydantic_model(
                self.input_schema, "InputModel"
            )
        return self._input_model

    def _get_output_model(self) -> type[BaseModel]:
        """Get or create output validation model.

        Returns:
            Pydantic model for output validation
        """
        if self._output_model is None:
            self._output_model = self._build_pydantic_model(
                self.output_schema, "OutputModel"
            )
        return self._output_model

    def validate_input(self, data: Dict[str, Any]) -> SchemaValidationResult:
        """Validate input data against input schema.

        Args:
            data: Input data to validate

        Returns:
            SchemaValidationResult with validation status and errors
        """
        logger.info("Validating input data against input schema")

        try:
            input_model = self._get_input_model()
            validated = input_model(**data)
            logger.info("Input validation successful")

            return SchemaValidationResult(
                is_valid=True,
                errors=[],
                warnings=[],
                validated_data=validated.model_dump(),
            )

        except ValidationError as e:
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            logger.warning("Input validation failed: %s", error_messages)

            return SchemaValidationResult(
                is_valid=False,
                errors=error_messages,
                warnings=[],
                validated_data=None,
            )

        except Exception as e:
            logger.error("Unexpected error during input validation: %s", str(e))
            return SchemaValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                validated_data=None,
            )

    def validate_output(self, data: Dict[str, Any]) -> SchemaValidationResult:
        """Validate output data against output schema.

        Args:
            data: Output data to validate

        Returns:
            SchemaValidationResult with validation status and errors
        """
        logger.info("Validating output data against output schema")

        try:
            output_model = self._get_output_model()
            validated = output_model(**data)
            logger.info("Output validation successful")

            return SchemaValidationResult(
                is_valid=True,
                errors=[],
                warnings=[],
                validated_data=validated.model_dump(),
            )

        except ValidationError as e:
            error_messages = [f"{err['loc'][0]}: {err['msg']}" for err in e.errors()]
            logger.warning("Output validation failed: %s", error_messages)

            return SchemaValidationResult(
                is_valid=False,
                errors=error_messages,
                warnings=[],
                validated_data=None,
            )

        except Exception as e:
            logger.error("Unexpected error during output validation: %s", str(e))
            return SchemaValidationResult(
                is_valid=False,
                errors=[f"Validation error: {str(e)}"],
                warnings=[],
                validated_data=None,
            )

    def validate_workflow(
        self,
        input_data: Dict[str, Any],
        output_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, SchemaValidationResult]:
        """Validate both input and output data.

        Args:
            input_data: Input data to validate
            output_data: Output data to validate (optional)

        Returns:
            Dictionary with 'input' and 'output' validation results
        """
        results: Dict[str, SchemaValidationResult] = {}

        # Validate input
        results["input"] = self.validate_input(input_data)

        # Validate output if provided
        if output_data is not None:
            results["output"] = self.validate_output(output_data)

        return results
