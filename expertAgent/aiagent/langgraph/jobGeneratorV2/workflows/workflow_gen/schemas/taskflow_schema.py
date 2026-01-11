"""TaskFlow V2 Pydantic Schema Definitions.

Issue #350 Task 2.1: Pydantic schema definitions for TaskFlow V2.
Issue #350 Fix: OpenAI Structured Output compatible (no Union/oneOf).

This module provides:
- IOSchemaType: Input/output schema type enum
- UnifiedStepConfig: Single config model for all step types (OpenAI compatible)
- TaskFlowStep: Step definition
- TaskFlowWorkflow: Complete workflow definition

Key features:
- OpenAI Structured Output compatible (no oneOf/Union)
- HTTPS enforcement for URLs
- mode-specific field validation for transform
- Strict ID pattern matching
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.variable_patterns import (
    mask_secret_references,
    replace_variables_with_placeholder,
)


class IOSchemaType(str, Enum):
    """Input/output schema type definitions.

    Used in TaskFlow workflow input_schema and output_schema.
    """

    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"
    NULL = "null"


class UnifiedStepConfig(BaseModel):
    """Unified configuration for all step types.

    OpenAI Structured Output does not support Union/oneOf, so all step
    configurations are merged into a single model with optional fields.

    The step_type field determines which fields are required:
    - api_rest: method, url required; headers, body, timeout_ms, verify_ssl optional
    - transform: mode required; template/separator/fields based on mode
    - code_js: path, function_name required

    Attributes:
        step_type: Step type discriminator (api_rest, transform, code_js)

        # api_rest fields
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        url: HTTPS URL for the API endpoint
        headers: HTTP headers to send
        body: Request body as JSON string
        timeout_ms: Request timeout in milliseconds (1000-300000)
        verify_ssl: Whether to verify SSL certificates

        # transform fields
        mode: Transform mode (template, concat, map, merge)
        template: Template string for 'template' mode
        separator: Separator for 'concat' mode
        fields: Field list for 'map' or 'merge' mode

        # code_js fields
        path: Path to the JavaScript file
        function_name: Name of the function to execute
    """

    model_config = ConfigDict(extra="forbid")

    step_type: Literal["api_rest", "transform", "code_js"]

    # api_rest fields
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] | None = Field(
        default=None, description="HTTP method for api_rest"
    )
    url: str | None = Field(default=None, description="HTTPS URL for the API endpoint")
    headers: dict[str, str] | None = Field(
        default=None, description="HTTP headers as key-value pairs"
    )
    body: str | None = Field(
        default=None,
        description='Request body as JSON string. Example: \'{"key": "value"}\'',
    )
    timeout_ms: int | None = Field(
        default=None, ge=1000, le=300000, description="Request timeout in ms"
    )
    verify_ssl: bool | None = Field(
        default=None, description="Whether to verify SSL certificates"
    )

    # transform fields
    mode: Literal["template", "concat", "map", "merge"] | None = Field(
        default=None, description="Transform mode"
    )
    template: str | None = Field(
        default=None, description="Template string for template mode"
    )
    separator: str | None = Field(default=None, description="Separator for concat mode")
    fields: list[str] | None = Field(
        default=None, description="Field list for map/merge mode"
    )

    # code_js fields
    path: str | None = Field(default=None, description="Path to JavaScript file")
    function_name: str | None = Field(
        default=None, description="Function name to execute"
    )

    @field_validator("url")
    @classmethod
    def validate_https_url(cls, value: str | None) -> str | None:
        """Ensure URL uses HTTPS protocol for external URLs.

        Security requirement: All external URLs must use HTTPS.
        HTTP is allowed for localhost/internal development URLs.
        Variable references like ${inputs.url} are allowed.
        """
        if value is None:
            return value

        # Allow variable references
        if value.startswith("${"):
            return value

        # Allow HTTP for localhost/internal development URLs
        if value.startswith("http://"):
            from urllib.parse import urlparse

            parsed = urlparse(value)
            hostname = parsed.hostname or ""
            # Allow HTTP for localhost and internal addresses
            allowed_http_hosts = [
                "localhost",
                "127.0.0.1",
                "0.0.0.0",
            ]
            # Also allow internal Docker network addresses
            if hostname in allowed_http_hosts or hostname.endswith(".local"):
                return value
            # Block HTTP for external URLs
            raise ValueError(
                f"URL must use HTTPS protocol for external URLs. Got: {value[:50]}... "
                "HTTP is only allowed for localhost and internal addresses."
            )

        if not value.startswith("https://"):
            raise ValueError(
                f"URL must use HTTPS or HTTP protocol. Got: {value[:50]}..."
            )
        return value

    @model_validator(mode="after")
    def validate_step_type_fields(self) -> "UnifiedStepConfig":
        """Validate required fields based on step_type.

        Each step_type requires specific fields:
        - api_rest: method, url required
        - transform: mode required; template/separator/fields based on mode
        - code_js: path, function_name required
        """
        if self.step_type == "api_rest":
            if not self.method:
                raise ValueError(
                    "method is required for api_rest step. "
                    "Valid values: GET, POST, PUT, DELETE, PATCH"
                )
            if not self.url:
                raise ValueError(
                    "url is required for api_rest step. "
                    "Example: https://api.example.com/endpoint"
                )

        elif self.step_type == "transform":
            if not self.mode:
                raise ValueError(
                    "mode is required for transform step. "
                    "Valid values: template, concat, map, merge"
                )
            if self.mode == "template" and not self.template:
                raise ValueError(
                    "template is required when mode is 'template'. "
                    "Example: template: '${step_001.output.data}'"
                )
            if self.mode == "concat" and self.separator is None:
                raise ValueError(
                    "separator is required when mode is 'concat'. "
                    "Example: separator: ', '"
                )
            if self.mode in ("map", "merge") and not self.fields:
                raise ValueError(
                    f"fields is required when mode is '{self.mode}'. "
                    "Example: fields: ['name', 'email']"
                )

        elif self.step_type == "code_js":
            if not self.path:
                raise ValueError(
                    "path is required for code_js step. Example: /scripts/utils.js"
                )
            if not self.function_name:
                raise ValueError(
                    "function_name is required for code_js step. Example: parseJson"
                )

        return self


# Step ID pattern: must start with letter or underscore,
# followed by letters, numbers, underscores, or hyphens
STEP_ID_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_-]*$")


class TaskFlowStep(BaseModel):
    """TaskFlow step definition.

    Attributes:
        id: Unique step identifier (pattern: ^[a-zA-Z_][a-zA-Z0-9_-]*$)
        type: Step type (api_rest, transform, code_js)
        config: Step configuration (unified model)
        params: Additional parameters for variable substitution
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique step identifier")
    type: Literal["api_rest", "transform", "code_js"]
    config: UnifiedStepConfig = Field(..., description="Step configuration")
    params: dict[str, str] | None = Field(
        default=None,
        description="Additional parameters for variable substitution",
    )

    @field_validator("id")
    @classmethod
    def validate_step_id(cls, value: str) -> str:
        """Validate step ID format.

        Pattern: ^[a-zA-Z_][a-zA-Z0-9_-]*$
        Must start with letter or underscore.
        """
        if not STEP_ID_PATTERN.match(value):
            raise ValueError(
                f"Step ID '{value}' is invalid. "
                "Must start with a letter or underscore, "
                "followed by letters, numbers, underscores, or hyphens. "
                "Pattern: ^[a-zA-Z_][a-zA-Z0-9_-]*$"
            )
        return value

    @model_validator(mode="after")
    def validate_type_matches_config(self) -> "TaskFlowStep":
        """Validate that step type matches config step_type.

        Ensures consistency between the step's type field and the
        config's step_type discriminator.
        """
        if self.config.step_type != self.type:
            raise ValueError(
                f"Step type mismatch: step.type='{self.type}' but "
                f"config.step_type='{self.config.step_type}'"
            )
        return self


# Workflow name pattern: same as step ID
WORKFLOW_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_-]*$")


def _parse_json_string_to_dict(value: Any, field_name: str) -> dict[str, Any]:
    """Parse JSON string to dict if needed.

    LLMs sometimes return dict fields as JSON strings.
    This helper converts them to proper dict objects.

    Args:
        value: Input value (can be str, dict, or other)
        field_name: Name of the field for error messages

    Returns:
        Parsed dict object

    Raises:
        ValueError: If string is not valid JSON or result is not a dict
    """
    import json as json_module

    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        # Try to parse JSON string
        try:
            parsed = json_module.loads(value)
            if isinstance(parsed, dict):
                return parsed
            raise ValueError(
                f"{field_name} must be a dict, got {type(parsed).__name__} "
                f"after parsing JSON string"
            )
        except json_module.JSONDecodeError as e:
            raise ValueError(f"{field_name} is a string but not valid JSON: {e}") from e

    raise ValueError(
        f"{field_name} must be a dict or JSON string, got {type(value).__name__}"
    )


class TaskFlowWorkflow(BaseModel):
    """Complete TaskFlow V2 workflow definition.

    OpenAI Structured Output compatible - uses JSON strings for dict fields.

    Attributes:
        workflow_name: Unique workflow name
        description: Optional workflow description
        input_schema: Input field definitions as JSON string
        output_schema: Output field definitions as JSON string
        steps: List of sequential steps
        output: Output field mappings as JSON string
    """

    model_config = ConfigDict(extra="forbid")

    workflow_name: str = Field(..., description="Unique workflow name")
    description: str | None = Field(default=None)
    input_schema: str = Field(
        ...,
        description='Input field definitions as JSON string. Example: \'{"query": "string"}\'',
    )
    output_schema: str = Field(
        ...,
        description='Output field definitions as JSON string. Example: \'{"result": "string"}\'',
    )
    steps: list[TaskFlowStep] = Field(..., description="Workflow steps", min_length=1)
    output: str = Field(
        ...,
        description='Output field mappings as JSON string. Example: \'{"result": "${step_001.output}"}\'',
    )

    @field_validator("input_schema", "output_schema", "output")
    @classmethod
    def validate_json_string(cls, value: str) -> str:
        """Validate JSON string allowing TaskFlow variable references.

        Variable references like ${step.output} are replaced with placeholder
        strings during validation, then the original value is returned.

        This allows LLM-generated workflows to include dynamic references
        while still validating the JSON structure.

        Args:
            value: JSON string, potentially containing ${...} variable references

        Returns:
            Original value (unmodified) if valid

        Raises:
            ValueError: If JSON structure is invalid
        """
        import json as json_module

        # Replace variable references with valid JSON placeholders
        placeholder_value = replace_variables_with_placeholder(value)

        try:
            parsed = json_module.loads(placeholder_value)
            if not isinstance(parsed, dict):
                raise ValueError(f"Must be a JSON object, got {type(parsed).__name__}")
            return value  # Return original with variables intact
        except json_module.JSONDecodeError as e:
            # SF-2: Improved error message with original value (masked for security)
            masked_value = mask_secret_references(value)
            raise ValueError(
                f"Invalid JSON structure (variable references like ${{step.output}} are allowed): {e}. "
                f"Input: {masked_value[:200]}{'...' if len(masked_value) > 200 else ''}"
            ) from e

    @field_validator("workflow_name")
    @classmethod
    def validate_workflow_name(cls, value: str) -> str:
        """Validate workflow name format.

        Pattern: ^[a-zA-Z_][a-zA-Z0-9_-]*$
        """
        if not WORKFLOW_NAME_PATTERN.match(value):
            raise ValueError(
                f"Workflow name '{value}' is invalid. "
                "Must start with a letter or underscore. "
                "Pattern: ^[a-zA-Z_][a-zA-Z0-9_-]*$"
            )
        return value

    def to_json(self) -> str:
        """Serialize workflow to JSON string.

        Returns:
            JSON string representation of the workflow
        """
        import json

        return json.dumps(self.model_dump(), indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> "TaskFlowWorkflow":
        """Parse workflow from JSON string.

        Args:
            json_str: JSON string to parse

        Returns:
            TaskFlowWorkflow instance
        """
        import json

        data = json.loads(json_str)
        return cls.model_validate(data)


# Legacy exports for backward compatibility
# These are deprecated - use UnifiedStepConfig instead
ApiRestConfig = UnifiedStepConfig
TransformConfig = UnifiedStepConfig
CodeJsConfig = UnifiedStepConfig
StepConfigUnion = UnifiedStepConfig

# Removed: ParallelBlock, ConditionalBlock (OpenAI Structured Output incompatible)
# These can be added back when using non-OpenAI models

__all__ = [
    "IOSchemaType",
    "UnifiedStepConfig",
    "TaskFlowStep",
    "TaskFlowWorkflow",
    # Legacy exports (deprecated)
    "ApiRestConfig",
    "TransformConfig",
    "CodeJsConfig",
    "StepConfigUnion",
]
