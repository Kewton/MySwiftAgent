"""Unit tests for taskflow_schema.py - TaskFlow V2 Pydantic schemas.

Issue #350 Task 2.1: Pydantic schema definitions.

Test cases (13 total):
- test_valid_api_rest_step
- test_valid_transform_step
- test_valid_code_js_step
- test_invalid_url_http
- test_invalid_step_id_format
- test_discriminated_union_api_rest
- test_discriminated_union_transform
- test_discriminated_union_invalid_config
- test_transform_mode_template_requires_template
- test_transform_mode_concat_requires_separator
- test_parallel_block_validation
- test_conditional_block_validation
- test_workflow_complete_validation
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.taskflow_schema import (
    ApiRestConfig,
    CodeJsConfig,
    ConditionalBlock,
    IOSchemaType,
    ParallelBlock,
    TaskFlowStep,
    TaskFlowWorkflow,
    TransformConfig,
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


class TestApiRestConfig:
    """Tests for ApiRestConfig model."""

    def test_valid_api_rest_config(self) -> None:
        """Test valid api_rest configuration."""
        config = ApiRestConfig(
            method="POST",
            url="https://api.example.com/endpoint",
            headers={"Content-Type": "application/json"},
            body={"key": "value"},
        )
        assert config.method == "POST"
        assert config.url == "https://api.example.com/endpoint"
        assert config.timeout_ms == 30000  # default
        assert config.verify_ssl is True  # default

    def test_invalid_url_http(self) -> None:
        """HTTP URLs should be rejected (HTTPS required)."""
        with pytest.raises(ValidationError) as exc_info:
            ApiRestConfig(
                method="GET",
                url="http://api.example.com/endpoint",
            )
        error = exc_info.value
        assert "url" in str(error).lower() or "https" in str(error).lower()

    def test_invalid_method(self) -> None:
        """Invalid HTTP method should be rejected."""
        with pytest.raises(ValidationError):
            ApiRestConfig(
                method="INVALID",  # type: ignore[arg-type]
                url="https://api.example.com/endpoint",
            )

    def test_timeout_range(self) -> None:
        """Timeout should be within valid range."""
        # Valid timeout
        config = ApiRestConfig(
            method="GET",
            url="https://api.example.com",
            timeout_ms=60000,
        )
        assert config.timeout_ms == 60000

        # Too low
        with pytest.raises(ValidationError):
            ApiRestConfig(
                method="GET",
                url="https://api.example.com",
                timeout_ms=500,  # Below 1000
            )

        # Too high
        with pytest.raises(ValidationError):
            ApiRestConfig(
                method="GET",
                url="https://api.example.com",
                timeout_ms=500000,  # Above 300000
            )


class TestTransformConfig:
    """Tests for TransformConfig model."""

    def test_valid_transform_template(self) -> None:
        """Test valid transform with template mode."""
        config = TransformConfig(
            mode="template",
            template="Result: ${step_001.data}",
        )
        assert config.mode == "template"
        assert config.template == "Result: ${step_001.data}"

    def test_valid_transform_concat(self) -> None:
        """Test valid transform with concat mode."""
        config = TransformConfig(
            mode="concat",
            separator=", ",
        )
        assert config.mode == "concat"
        assert config.separator == ", "

    def test_transform_mode_template_requires_template(self) -> None:
        """Template mode requires template field."""
        with pytest.raises(ValidationError) as exc_info:
            TransformConfig(mode="template")
        assert "template" in str(exc_info.value).lower()

    def test_transform_mode_concat_requires_separator(self) -> None:
        """Concat mode requires separator field."""
        with pytest.raises(ValidationError) as exc_info:
            TransformConfig(mode="concat")
        assert "separator" in str(exc_info.value).lower()

    def test_transform_mode_map_requires_fields(self) -> None:
        """Map mode requires fields list."""
        with pytest.raises(ValidationError) as exc_info:
            TransformConfig(mode="map")
        assert "fields" in str(exc_info.value).lower()


class TestCodeJsConfig:
    """Tests for CodeJsConfig model."""

    def test_valid_code_js_config(self) -> None:
        """Test valid code_js configuration."""
        config = CodeJsConfig(
            path="/scripts/format.js",
            function_name="formatDate",
        )
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
                config={"method": "GET", "url": "https://api.example.com"},
            )
        assert "id" in str(exc_info.value).lower()

        # Special characters should fail
        with pytest.raises(ValidationError):
            TaskFlowStep(
                id="invalid@step",
                type="api_rest",
                config={"method": "GET", "url": "https://api.example.com"},
            )

    def test_discriminated_union_api_rest(self) -> None:
        """Config should be validated as ApiRestConfig for api_rest type."""
        # Valid api_rest config
        step = TaskFlowStep(
            id="test_step",
            type="api_rest",
            config={
                "method": "POST",
                "url": "https://api.example.com",
                "headers": {"Content-Type": "application/json"},
            },
        )
        assert step.type == "api_rest"

    def test_discriminated_union_transform(self) -> None:
        """Config should be validated as TransformConfig for transform type."""
        step = TaskFlowStep(
            id="test_step",
            type="transform",
            config={
                "mode": "template",
                "template": "Hello ${name}",
            },
        )
        assert step.type == "transform"

    def test_discriminated_union_invalid_config(self) -> None:
        """Invalid config for type should raise validation error."""
        # Missing required fields for api_rest
        with pytest.raises(ValidationError):
            TaskFlowStep(
                id="test_step",
                type="api_rest",
                config={},  # Missing method and url
            )

        # HTTP URL for api_rest
        with pytest.raises(ValidationError):
            TaskFlowStep(
                id="test_step",
                type="api_rest",
                config={
                    "method": "GET",
                    "url": "http://insecure.com",  # Should be HTTPS
                },
            )


class TestParallelBlock:
    """Tests for ParallelBlock model."""

    def test_parallel_block_validation(self) -> None:
        """Test valid parallel block."""
        block = ParallelBlock(
            parallel=[
                TaskFlowStep(
                    id="step_a",
                    type="api_rest",
                    config={"method": "GET", "url": "https://api.a.com"},
                ),
                TaskFlowStep(
                    id="step_b",
                    type="api_rest",
                    config={"method": "GET", "url": "https://api.b.com"},
                ),
            ]
        )
        assert len(block.parallel) == 2
        assert block.parallel[0].id == "step_a"
        assert block.parallel[1].id == "step_b"


class TestConditionalBlock:
    """Tests for ConditionalBlock model."""

    def test_conditional_block_validation(self) -> None:
        """Test valid conditional block."""
        block = ConditionalBlock(
            condition="${step_001.status} == 'success'",
            if_true=[
                TaskFlowStep(
                    id="on_success",
                    type="transform",
                    config={"mode": "template", "template": "Success!"},
                ),
            ],
            if_false=[
                TaskFlowStep(
                    id="on_failure",
                    type="transform",
                    config={"mode": "template", "template": "Failed!"},
                ),
            ],
        )
        assert block.condition == "${step_001.status} == 'success'"
        assert len(block.if_true) == 1
        assert len(block.if_false) == 1


class TestTaskFlowWorkflow:
    """Tests for TaskFlowWorkflow model."""

    def test_workflow_complete_validation(self) -> None:
        """Test complete workflow validation."""
        workflow = TaskFlowWorkflow(
            workflow_name="example_workflow",
            description="An example workflow",
            input_schema={"user_input": IOSchemaType.STRING},
            output_schema={"result": IOSchemaType.STRING},
            steps=[
                TaskFlowStep(
                    id="fetch",
                    type="api_rest",
                    config={"method": "GET", "url": "https://api.example.com"},
                ),
                TaskFlowStep(
                    id="format",
                    type="transform",
                    config={"mode": "template", "template": "${fetch.data}"},
                ),
            ],
            output={"result": "${format}"},
        )
        assert workflow.workflow_name == "example_workflow"
        assert len(workflow.steps) == 2

    def test_workflow_name_pattern(self) -> None:
        """Workflow name must match pattern."""
        # Valid names
        TaskFlowWorkflow(
            workflow_name="my_workflow",
            input_schema={},
            output_schema={},
            steps=[],
            output={},
        )
        TaskFlowWorkflow(
            workflow_name="workflow123",
            input_schema={},
            output_schema={},
            steps=[],
            output={},
        )

        # Invalid name (starts with number)
        with pytest.raises(ValidationError):
            TaskFlowWorkflow(
                workflow_name="123workflow",
                input_schema={},
                output_schema={},
                steps=[],
                output={},
            )

    def test_workflow_with_parallel_block(self) -> None:
        """Workflow can contain parallel blocks."""
        workflow = TaskFlowWorkflow(
            workflow_name="parallel_workflow",
            input_schema={"query": IOSchemaType.STRING},
            output_schema={"combined": IOSchemaType.OBJECT},
            steps=[
                ParallelBlock(
                    parallel=[
                        TaskFlowStep(
                            id="api_a",
                            type="api_rest",
                            config={"method": "GET", "url": "https://a.com"},
                        ),
                        TaskFlowStep(
                            id="api_b",
                            type="api_rest",
                            config={"method": "GET", "url": "https://b.com"},
                        ),
                    ]
                ),
            ],
            output={"combined": "${api_a}, ${api_b}"},
        )
        assert len(workflow.steps) == 1

    def test_workflow_with_conditional_block(self) -> None:
        """Workflow can contain conditional blocks."""
        workflow = TaskFlowWorkflow(
            workflow_name="conditional_workflow",
            input_schema={"flag": IOSchemaType.BOOLEAN},
            output_schema={"result": IOSchemaType.STRING},
            steps=[
                ConditionalBlock(
                    condition="${inputs.flag}",
                    if_true=[
                        TaskFlowStep(
                            id="on_true",
                            type="transform",
                            config={"mode": "template", "template": "True path"},
                        ),
                    ],
                    if_false=[
                        TaskFlowStep(
                            id="on_false",
                            type="transform",
                            config={"mode": "template", "template": "False path"},
                        ),
                    ],
                ),
            ],
            output={"result": "${on_true}"},
        )
        assert len(workflow.steps) == 1


class TestJsonStringParsing:
    """Tests for JSON string to dict parsing validators.

    Issue #350 fix: LLMs sometimes return dict fields as JSON strings.
    These tests verify automatic conversion.
    """

    def test_output_schema_accepts_dict(self) -> None:
        """output_schema should accept normal dict input."""
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema={},
            output_schema={"result": "string"},
            steps=[],
            output={},
        )
        assert workflow.output_schema == {"result": "string"}

    def test_output_schema_parses_json_string(self) -> None:
        """output_schema should parse JSON string to dict.

        This is the exact scenario from Langfuse trace where LLM returned:
        output_schema='{"search_results":"array"}' as a string instead of dict.
        """
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema={},
            output_schema='{"search_results": "array"}',  # JSON string
            steps=[],
            output={},
        )
        assert workflow.output_schema == {"search_results": "array"}
        assert isinstance(workflow.output_schema, dict)

    def test_output_parses_json_string(self) -> None:
        """output field should parse JSON string to dict.

        This is the exact scenario from Langfuse trace where LLM returned:
        output='{"search_results":"${google_search.data.items}"}' as string.
        """
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema={},
            output_schema={},
            steps=[],
            output='{"search_results": "${google_search.data.items}"}',  # JSON string
        )
        assert workflow.output == {"search_results": "${google_search.data.items}"}
        assert isinstance(workflow.output, dict)

    def test_input_schema_parses_json_string(self) -> None:
        """input_schema should parse JSON string to dict."""
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema='{"query": "string", "limit": "number"}',  # JSON string
            output_schema={},
            steps=[],
            output={},
        )
        assert workflow.input_schema == {"query": "string", "limit": "number"}
        assert isinstance(workflow.input_schema, dict)

    def test_invalid_json_string_raises_error(self) -> None:
        """Invalid JSON string should raise validation error."""
        with pytest.raises(ValidationError) as exc_info:
            TaskFlowWorkflow(
                workflow_name="test_workflow",
                input_schema={},
                output_schema='{"invalid json',  # Invalid JSON
                steps=[],
                output={},
            )
        assert "not valid json" in str(exc_info.value).lower()

    def test_non_dict_json_raises_error(self) -> None:
        """JSON string that parses to non-dict should raise error."""
        with pytest.raises(ValidationError) as exc_info:
            TaskFlowWorkflow(
                workflow_name="test_workflow",
                input_schema={},
                output_schema='["array", "not", "dict"]',  # JSON array
                steps=[],
                output={},
            )
        # Error message should indicate dict type expected
        error_str = str(exc_info.value).lower()
        assert "dict" in error_str or "dictionary" in error_str

    def test_llm_realistic_response(self) -> None:
        """Test with realistic LLM response pattern.

        This simulates the actual error scenario from production where
        the LLM returned stringified JSON for multiple dict fields.
        """
        # Simulated LLM response with stringified dicts
        workflow = TaskFlowWorkflow(
            workflow_name="google_search_workflow",
            description="Search and format results",
            input_schema='{"query": "string"}',  # LLM returned as string
            output_schema='{"search_results": "array"}',  # LLM returned as string
            steps=[
                TaskFlowStep(
                    id="google_search",
                    type="api_rest",
                    config={
                        "method": "GET",
                        "url": "https://www.googleapis.com/customsearch/v1",
                    },
                ),
            ],
            output='{"search_results": "${google_search.data.items}"}',  # String
        )

        # Verify all fields were properly parsed to dicts
        assert isinstance(workflow.input_schema, dict)
        assert isinstance(workflow.output_schema, dict)
        assert isinstance(workflow.output, dict)
        assert workflow.input_schema == {"query": "string"}
        assert workflow.output_schema == {"search_results": "array"}
        assert workflow.output == {"search_results": "${google_search.data.items}"}
