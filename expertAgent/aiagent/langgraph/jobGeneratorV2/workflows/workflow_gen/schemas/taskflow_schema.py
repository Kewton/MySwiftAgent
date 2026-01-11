"""TaskFlow V2 Pydantic Schema Definitions.

Issue #350 Task 2.1: Pydantic schema definitions for TaskFlow V2.

This module provides:
- IOSchemaType: Input/output schema type enum
- ApiRestConfig: Configuration for api_rest nodes
- TransformConfig: Configuration for transform nodes
- CodeJsConfig: Configuration for code_js nodes
- TaskFlowStep: Step with discriminated union validation
- ParallelBlock: Parallel execution block
- ConditionalBlock: Conditional execution block
- TaskFlowWorkflow: Complete workflow definition

Key features:
- Discriminated Union pattern with model_validator
- HTTPS enforcement for URLs
- mode-specific field validation for transform
- Strict ID pattern matching
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class ApiRestConfig(BaseModel):
    """Configuration for api_rest step type.

    Attributes:
        step_type: Discriminator field for Union type (always "api_rest")
        method: HTTP method (GET, POST, PUT, DELETE, PATCH)
        url: HTTPS URL for the API endpoint
        headers: HTTP headers to send
        body: Request body (for POST, PUT, PATCH)
        timeout_ms: Request timeout in milliseconds (1000-300000)
        verify_ssl: Whether to verify SSL certificates
    """

    model_config = ConfigDict(extra="forbid")

    step_type: Literal["api_rest"] = Field(
        default="api_rest", description="Step type discriminator"
    )
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"]
    url: str = Field(..., description="HTTPS URL for the API endpoint")
    headers: dict[str, str] = Field(default_factory=dict)
    body: dict[str, Any] | None = None
    timeout_ms: int = Field(default=30000, ge=1000, le=300000)
    verify_ssl: bool = True

    @field_validator("url")
    @classmethod
    def validate_https_url(cls, value: str) -> str:
        """Ensure URL uses HTTPS protocol for external URLs.

        Security requirement: All external URLs must use HTTPS.
        HTTP is allowed for localhost/internal development URLs.
        Variable references like ${inputs.url} are allowed.
        """
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


class TransformConfig(BaseModel):
    """Configuration for transform step type.

    Attributes:
        step_type: Discriminator field for Union type (always "transform")
        mode: Transform mode (template, concat, map, merge)
        template: Template string for 'template' mode
        separator: Separator for 'concat' mode
        fields: Field list for 'map' or 'merge' mode
    """

    model_config = ConfigDict(extra="forbid")

    step_type: Literal["transform"] = Field(
        default="transform", description="Step type discriminator"
    )
    mode: Literal["template", "concat", "map", "merge"]
    template: str | None = None
    separator: str | None = None
    fields: list[str] | None = None

    @model_validator(mode="after")
    def validate_mode_specific_fields(self) -> "TransformConfig":
        """Validate required fields based on mode.

        Each mode requires specific fields:
        - template: requires 'template' field
        - concat: requires 'separator' field
        - map, merge: requires 'fields' field
        """
        if self.mode == "template" and not self.template:
            raise ValueError(
                "template is required when mode is 'template'. "
                "Example: template: '${step_001.data}'"
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
        return self


class CodeJsConfig(BaseModel):
    """Configuration for code_js step type.

    Attributes:
        step_type: Discriminator field for Union type (always "code_js")
        path: Path to the JavaScript file
        function_name: Name of the function to execute

    Note:
        Only whitelisted functions are allowed for security.
        See TaskFlowSecurityValidator.ALLOWED_CODE_JS_FUNCTIONS.
    """

    model_config = ConfigDict(extra="forbid")

    step_type: Literal["code_js"] = Field(
        default="code_js", description="Step type discriminator"
    )
    path: str = Field(..., description="Path to JavaScript file")
    function_name: str = Field(..., description="Function name to execute")


# Step ID pattern: must start with letter or underscore,
# followed by letters, numbers, underscores, or hyphens
STEP_ID_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_-]*$")


# Config Union type for discriminated union pattern
StepConfigUnion = Annotated[
    Union[ApiRestConfig, TransformConfig, CodeJsConfig],
    Field(discriminator="step_type"),
]


class TaskFlowStep(BaseModel):
    """TaskFlow step with discriminated union validation.

    The config field uses Pydantic's discriminated union pattern:
    - api_rest: validated as ApiRestConfig (step_type="api_rest")
    - transform: validated as TransformConfig (step_type="transform")
    - code_js: validated as CodeJsConfig (step_type="code_js")

    Attributes:
        id: Unique step identifier (pattern: ^[a-zA-Z_][a-zA-Z0-9_-]*$)
        type: Step type (api_rest, transform, code_js)
        config: Step configuration (discriminated union)
        params: Additional parameters
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique step identifier")
    type: Literal["api_rest", "transform", "code_js"]
    config: StepConfigUnion = Field(..., description="Step configuration")
    params: dict[str, str] = Field(default_factory=dict)

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
        config_step_type = getattr(self.config, "step_type", None)
        if config_step_type and config_step_type != self.type:
            raise ValueError(
                f"Step type mismatch: step.type='{self.type}' but "
                f"config.step_type='{config_step_type}'"
            )
        return self


class ParallelBlock(BaseModel):
    """Parallel execution block.

    Steps within a parallel block are executed concurrently.
    All steps must complete before the workflow continues.

    Attributes:
        parallel: List of steps to execute in parallel
    """

    model_config = ConfigDict(extra="forbid")

    parallel: list[TaskFlowStep] = Field(
        ..., min_length=1, description="Steps to execute in parallel"
    )


class ConditionalBlock(BaseModel):
    """Conditional execution block.

    Executes if_true steps when condition is truthy,
    otherwise executes if_false steps.

    Attributes:
        condition: Condition expression (e.g., "${step_id.status} == 'success'")
        if_true: Steps to execute when condition is true
        if_false: Steps to execute when condition is false
    """

    model_config = ConfigDict(extra="forbid")

    condition: str = Field(..., description="Condition expression")
    if_true: list[TaskFlowStep] = Field(
        ..., min_length=1, description="Steps when condition is true"
    )
    if_false: list[TaskFlowStep] = Field(
        default_factory=list, description="Steps when condition is false"
    )


# Workflow name pattern: same as step ID
WORKFLOW_NAME_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_-]*$")

# Step type union for workflow steps
StepType = Union[TaskFlowStep, ParallelBlock, ConditionalBlock]


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
            raise ValueError(
                f"{field_name} is a string but not valid JSON: {e}"
            ) from e

    raise ValueError(
        f"{field_name} must be a dict or JSON string, got {type(value).__name__}"
    )


class TaskFlowWorkflow(BaseModel):
    """Complete TaskFlow V2 workflow definition.

    Attributes:
        workflow_name: Unique workflow name
        description: Optional workflow description
        input_schema: Input field definitions
        output_schema: Output field definitions
        steps: List of steps (sequential, parallel, or conditional)
        output: Output field mappings
    """

    model_config = ConfigDict(extra="forbid")

    workflow_name: str = Field(..., description="Unique workflow name")
    description: str | None = None
    input_schema: dict[str, IOSchemaType | str] = Field(
        default_factory=dict, description="Input field definitions"
    )
    output_schema: dict[str, IOSchemaType | str] = Field(
        default_factory=dict, description="Output field definitions"
    )
    steps: list[StepType] = Field(default_factory=list, description="Workflow steps")
    output: dict[str, str] = Field(
        default_factory=dict, description="Output field mappings"
    )

    @field_validator("input_schema", "output_schema", mode="before")
    @classmethod
    def parse_schema_json_strings(
        cls, value: Any, info: Any
    ) -> dict[str, IOSchemaType | str]:
        """Parse JSON string to dict for schema fields.

        LLMs sometimes return dict fields as JSON strings like
        '{"field": "type"}' instead of {"field": "type"}.
        This validator handles that case automatically.
        """
        return _parse_json_string_to_dict(value, info.field_name)

    @field_validator("output", mode="before")
    @classmethod
    def parse_output_json_string(cls, value: Any) -> dict[str, str]:
        """Parse JSON string to dict for output field.

        LLMs sometimes return dict fields as JSON strings.
        This validator handles that case automatically.
        """
        return _parse_json_string_to_dict(value, "output")

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


__all__ = [
    "IOSchemaType",
    "ApiRestConfig",
    "TransformConfig",
    "CodeJsConfig",
    "StepConfigUnion",
    "TaskFlowStep",
    "ParallelBlock",
    "ConditionalBlock",
    "TaskFlowWorkflow",
    "StepType",
]
