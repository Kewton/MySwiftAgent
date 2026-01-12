"""Unit tests for taskflow_schema.py - TaskFlow V2 Pydantic schemas.

Issue #350 Task 2.1: Pydantic schema definitions.

Tests verify:
- UnifiedStepConfig validation for api_rest, transform, code_js
- TaskFlowStep validation
- TaskFlowWorkflow validation (JSON string fields)

Note: The schema was restructured to use UnifiedStepConfig instead of
separate ApiRestConfig/TransformConfig/CodeJsConfig classes to ensure
OpenAI Structured Output compatibility (no Union/oneOf).

TaskFlowWorkflow uses JSON strings for input_schema, output_schema, and output
fields to support OpenAI Structured Output format.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.taskflow_schema import (
    IOSchemaType,
    TaskFlowStep,
    TaskFlowWorkflow,
    UnifiedStepConfig,
)


class TestIOSchemaType:
    """Tests for IOSchemaType enum."""

    def test_string_type(self) -> None:
        """Test string type value."""
        assert IOSchemaType.STRING.value == "string"

    def test_number_type(self) -> None:
        """Test number type value."""
        assert IOSchemaType.NUMBER.value == "number"

    def test_object_type(self) -> None:
        """Test object type value."""
        assert IOSchemaType.OBJECT.value == "object"


class TestUnifiedStepConfigApiRest:
    """Tests for UnifiedStepConfig with step_type='api_rest'."""

    def test_valid_api_rest_config(self) -> None:
        """Test valid api_rest configuration."""
        config = UnifiedStepConfig(
            step_type="api_rest",
            method="POST",
            url="https://api.example.com/endpoint",
            headers={"Content-Type": "application/json"},
            body='{"key": "value"}',
        )
        assert config.step_type == "api_rest"
        assert config.method == "POST"
        assert config.url == "https://api.example.com/endpoint"

    def test_invalid_url_http(self) -> None:
        """HTTP URLs should be rejected (HTTPS required)."""
        with pytest.raises(ValidationError) as exc_info:
            UnifiedStepConfig(
                step_type="api_rest",
                method="GET",
                url="http://api.example.com/endpoint",
            )
        error = exc_info.value
        assert "url" in str(error).lower() or "https" in str(error).lower()

    def test_invalid_method(self) -> None:
        """Invalid HTTP method should be rejected."""
        with pytest.raises(ValidationError):
            UnifiedStepConfig(
                step_type="api_rest",
                method="INVALID",  # type: ignore[arg-type]
                url="https://api.example.com/endpoint",
            )

    def test_timeout_range(self) -> None:
        """Timeout should be within valid range."""
        # Valid timeout
        config = UnifiedStepConfig(
            step_type="api_rest",
            method="GET",
            url="https://api.example.com",
            timeout_ms=60000,
        )
        assert config.timeout_ms == 60000

        # Too low
        with pytest.raises(ValidationError):
            UnifiedStepConfig(
                step_type="api_rest",
                method="GET",
                url="https://api.example.com",
                timeout_ms=500,  # Below 1000
            )

        # Too high
        with pytest.raises(ValidationError):
            UnifiedStepConfig(
                step_type="api_rest",
                method="GET",
                url="https://api.example.com",
                timeout_ms=500000,  # Above 300000
            )


class TestUnifiedStepConfigTransform:
    """Tests for UnifiedStepConfig with step_type='transform'."""

    def test_valid_transform_template(self) -> None:
        """Test valid transform with template mode."""
        config = UnifiedStepConfig(
            step_type="transform",
            mode="template",
            template="Result: ${step_001.data}",
        )
        assert config.step_type == "transform"
        assert config.mode == "template"
        assert config.template == "Result: ${step_001.data}"

    def test_valid_transform_concat(self) -> None:
        """Test valid transform with concat mode."""
        config = UnifiedStepConfig(
            step_type="transform",
            mode="concat",
            separator=", ",
        )
        assert config.step_type == "transform"
        assert config.mode == "concat"
        assert config.separator == ", "

    def test_transform_mode_template_requires_template(self) -> None:
        """Template mode requires template field."""
        with pytest.raises(ValidationError) as exc_info:
            UnifiedStepConfig(step_type="transform", mode="template")
        assert "template" in str(exc_info.value).lower()

    def test_transform_mode_concat_requires_separator(self) -> None:
        """Concat mode requires separator field."""
        with pytest.raises(ValidationError) as exc_info:
            UnifiedStepConfig(step_type="transform", mode="concat")
        assert "separator" in str(exc_info.value).lower()

    def test_transform_mode_map_requires_fields(self) -> None:
        """Map mode requires fields list."""
        with pytest.raises(ValidationError) as exc_info:
            UnifiedStepConfig(step_type="transform", mode="map")
        assert "fields" in str(exc_info.value).lower()


class TestUnifiedStepConfigCodeJs:
    """Tests for UnifiedStepConfig with step_type='code_js'."""

    def test_valid_code_js_config(self) -> None:
        """Test valid code_js configuration."""
        config = UnifiedStepConfig(
            step_type="code_js",
            path="/scripts/format.js",
            function_name="formatDate",
        )
        assert config.step_type == "code_js"
        assert config.path == "/scripts/format.js"
        assert config.function_name == "formatDate"


class TestTaskFlowStep:
    """Tests for TaskFlowStep with discriminated union."""

    def test_valid_api_rest_step(self) -> None:
        """Test valid api_rest step."""
        step = TaskFlowStep(
            id="fetch_data",
            type="api_rest",
            config={
                "step_type": "api_rest",
                "method": "GET",
                "url": "https://api.example.com/data",
            },
        )
        assert step.id == "fetch_data"
        assert step.type == "api_rest"

    def test_valid_transform_step(self) -> None:
        """Test valid transform step."""
        step = TaskFlowStep(
            id="format_output",
            type="transform",
            config={
                "step_type": "transform",
                "mode": "template",
                "template": "${fetch_data.result}",
            },
        )
        assert step.id == "format_output"
        assert step.type == "transform"

    def test_valid_code_js_step(self) -> None:
        """Test valid code_js step."""
        step = TaskFlowStep(
            id="process_data",
            type="code_js",
            config={
                "step_type": "code_js",
                "path": "/scripts/process.js",
                "function_name": "parseJson",
            },
        )
        assert step.id == "process_data"
        assert step.type == "code_js"

    def test_invalid_step_id_format(self) -> None:
        """Step ID must match pattern ^[a-zA-Z_][a-zA-Z0-9_-]*$."""
        # Starting with number should fail
        with pytest.raises(ValidationError) as exc_info:
            TaskFlowStep(
                id="123_invalid",
                type="api_rest",
                config={
                    "step_type": "api_rest",
                    "method": "GET",
                    "url": "https://api.example.com",
                },
            )
        assert "id" in str(exc_info.value).lower()

        # Special characters should fail
        with pytest.raises(ValidationError):
            TaskFlowStep(
                id="invalid@step",
                type="api_rest",
                config={
                    "step_type": "api_rest",
                    "method": "GET",
                    "url": "https://api.example.com",
                },
            )

    def test_discriminated_union_api_rest(self) -> None:
        """Config should be validated as UnifiedStepConfig for api_rest type."""
        step = TaskFlowStep(
            id="test_step",
            type="api_rest",
            config={
                "step_type": "api_rest",
                "method": "POST",
                "url": "https://api.example.com",
                "headers": {"Content-Type": "application/json"},
            },
        )
        assert step.type == "api_rest"

    def test_discriminated_union_transform(self) -> None:
        """Config should be validated as UnifiedStepConfig for transform type."""
        step = TaskFlowStep(
            id="test_step",
            type="transform",
            config={
                "step_type": "transform",
                "mode": "template",
                "template": "Hello ${name}",
            },
        )
        assert step.type == "transform"

    def test_discriminated_union_invalid_config(self) -> None:
        """Invalid config for type should raise validation error."""
        # Missing step_type
        with pytest.raises(ValidationError):
            TaskFlowStep(
                id="test_step",
                type="api_rest",
                config={},  # Missing step_type
            )


class TestTaskFlowWorkflow:
    """Tests for TaskFlowWorkflow model.

    Note: input_schema, output_schema, and output are JSON strings (not dicts)
    in the current schema for OpenAI Structured Output compatibility.
    """

    def test_workflow_complete_validation(self) -> None:
        """Test complete workflow validation with JSON string fields."""
        workflow = TaskFlowWorkflow(
            workflow_name="example_workflow",
            description="An example workflow",
            input_schema='{"user_input": "string"}',
            output_schema='{"result": "string"}',
            steps=[
                TaskFlowStep(
                    id="fetch",
                    type="api_rest",
                    config={
                        "step_type": "api_rest",
                        "method": "GET",
                        "url": "https://api.example.com",
                    },
                ),
                TaskFlowStep(
                    id="format",
                    type="transform",
                    config={
                        "step_type": "transform",
                        "mode": "template",
                        "template": "${fetch.data}",
                    },
                ),
            ],
            output='{"result": "${format}"}',
        )
        assert workflow.workflow_name == "example_workflow"
        assert len(workflow.steps) == 2

    def test_workflow_name_pattern(self) -> None:
        """Workflow name must match pattern."""
        # Valid names
        TaskFlowWorkflow(
            workflow_name="my_workflow",
            input_schema='{}',
            output_schema='{}',
            steps=[
                TaskFlowStep(
                    id="step1",
                    type="transform",
                    config={
                        "step_type": "transform",
                        "mode": "template",
                        "template": "hello",
                    },
                )
            ],
            output='{}',
        )
        TaskFlowWorkflow(
            workflow_name="workflow123",
            input_schema='{}',
            output_schema='{}',
            steps=[
                TaskFlowStep(
                    id="step1",
                    type="transform",
                    config={
                        "step_type": "transform",
                        "mode": "template",
                        "template": "hello",
                    },
                )
            ],
            output='{}',
        )

        # Invalid name (starts with number)
        with pytest.raises(ValidationError):
            TaskFlowWorkflow(
                workflow_name="123workflow",
                input_schema='{}',
                output_schema='{}',
                steps=[
                    TaskFlowStep(
                        id="step1",
                        type="transform",
                        config={
                            "step_type": "transform",
                            "mode": "template",
                            "template": "hello",
                        },
                    )
                ],
                output='{}',
            )


class TestJsonStringValidation:
    """Tests for JSON string validation in TaskFlowWorkflow.

    The schema uses JSON strings for input_schema, output_schema, and output
    to support OpenAI Structured Output format.
    """

    def test_valid_json_string_accepted(self) -> None:
        """Valid JSON strings should be accepted."""
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema='{"query": "string"}',
            output_schema='{"result": "string"}',
            steps=[
                TaskFlowStep(
                    id="step1",
                    type="transform",
                    config={
                        "step_type": "transform",
                        "mode": "template",
                        "template": "${inputs.query}",
                    },
                )
            ],
            output='{"result": "${step1}"}',
        )
        assert workflow.input_schema == '{"query": "string"}'
        assert workflow.output_schema == '{"result": "string"}'

    def test_json_with_variable_references(self) -> None:
        """JSON strings with ${...} variable references should be accepted.

        This is the key use case for TaskFlow workflows where output mappings
        reference step outputs.
        """
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema='{}',
            output_schema='{"search_results": "array"}',
            steps=[
                TaskFlowStep(
                    id="google_search",
                    type="api_rest",
                    config={
                        "step_type": "api_rest",
                        "method": "GET",
                        "url": "https://www.googleapis.com/customsearch/v1",
                    },
                )
            ],
            output='{"search_results": "${google_search.data.items}"}',
        )
        assert "${google_search.data.items}" in workflow.output

    def test_invalid_json_string_raises_error(self) -> None:
        """Invalid JSON strings should raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TaskFlowWorkflow(
                workflow_name="test_workflow",
                input_schema='{}',
                output_schema='{"invalid json',  # Invalid JSON
                steps=[
                    TaskFlowStep(
                        id="step1",
                        type="transform",
                        config={
                            "step_type": "transform",
                            "mode": "template",
                            "template": "hello",
                        },
                    )
                ],
                output='{}',
            )
        error_str = str(exc_info.value).lower()
        assert "json" in error_str or "invalid" in error_str

    def test_non_object_json_raises_error(self) -> None:
        """JSON strings that parse to non-objects should raise error."""
        with pytest.raises(ValidationError) as exc_info:
            TaskFlowWorkflow(
                workflow_name="test_workflow",
                input_schema='{}',
                output_schema='["array", "not", "object"]',  # JSON array
                steps=[
                    TaskFlowStep(
                        id="step1",
                        type="transform",
                        config={
                            "step_type": "transform",
                            "mode": "template",
                            "template": "hello",
                        },
                    )
                ],
                output='{}',
            )
        # Error should indicate object type expected
        error_str = str(exc_info.value).lower()
        assert "object" in error_str or "dict" in error_str

    def test_realistic_llm_response(self) -> None:
        """Test with realistic LLM response pattern.

        This simulates the actual use case where LLM generates a complete
        workflow with variable references in the output field.
        """
        workflow = TaskFlowWorkflow(
            workflow_name="google_search_workflow",
            description="Search and format results",
            input_schema='{"query": "string"}',
            output_schema='{"search_results": "array"}',
            steps=[
                TaskFlowStep(
                    id="google_search",
                    type="api_rest",
                    config={
                        "step_type": "api_rest",
                        "method": "GET",
                        "url": "https://www.googleapis.com/customsearch/v1",
                    },
                ),
            ],
            output='{"search_results": "${google_search.data.items}"}',
        )

        # Verify workflow is created correctly
        assert workflow.workflow_name == "google_search_workflow"
        assert workflow.input_schema == '{"query": "string"}'
        assert workflow.output_schema == '{"search_results": "array"}'
        assert workflow.output == '{"search_results": "${google_search.data.items}"}'
