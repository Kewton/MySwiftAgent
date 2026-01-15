"""Contract tests for TaskFlow schema compatibility.

Issue #356: TaskFlow Contract Tests implementation.

These tests verify the contract between ExpertAgent and GraphAiServer:
1. JSON string fields (input_schema, output_schema, output, body) are converted to objects
2. Pydantic model outputs are compatible with TaskFlowAdapter
3. Converted workflows pass GraphAiServer validation

Test Categories:
- Unit tests: Run without external dependencies
- Integration tests: Require GraphAiServer to be running

Refactoring Applied:
- Extracted common assertion patterns into helper functions
- Moved skip_if_graphai_unavailable fixture to conftest.py
- Improved import organization
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import httpx
import pytest

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter import (
        TaskFlowAdapter,
    )
    from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.taskflow_schema import (
        TaskFlowWorkflow,
    )

from tests.contract.conftest import (
    VALID_WORKFLOWS_DIR,
    create_api_rest_step,
    create_workflow,
    list_fixture_workflows,
    load_fixture_workflow,
)

# ============================================================================
# Assertion Helpers (DRY Pattern)
# ============================================================================


def assert_conversion_success(
    result: Any,
    context: str = "",
) -> dict[str, Any]:
    """Assert that adapter conversion succeeded and return data.

    Args:
        result: Conversion result from adapter.convert()
        context: Optional context string for error messages

    Returns:
        The converted workflow data dict

    Raises:
        AssertionError: If conversion failed
    """
    error_msg = f"Conversion failed: {result.errors}"
    if context:
        error_msg = f"{context}: {error_msg}"
    assert result.success is True, error_msg
    assert result.data is not None
    data: dict[str, Any] = result.data
    return data


def assert_field_is_dict(
    data: dict[str, Any],
    field_name: str,
    context: str = "",
) -> None:
    """Assert that a workflow field is a dict (not a string).

    Args:
        data: Workflow data dict
        field_name: Name of the field to check
        context: Optional context string for error messages

    Raises:
        AssertionError: If field is not a dict
    """
    error_msg = f"Field {field_name} should be dict"
    if context:
        error_msg = f"{context}: {error_msg}"
    assert isinstance(data[field_name], dict), error_msg


def assert_schema_fields_are_dicts(
    data: dict[str, Any],
    context: str = "",
) -> None:
    """Assert that all schema fields are dicts.

    Checks input_schema, output_schema, and output fields.

    Args:
        data: Workflow data dict
        context: Optional context string for error messages
    """
    for field in ["input_schema", "output_schema", "output"]:
        assert_field_is_dict(data, field, context)


class TestJsonStringFieldsConversion:
    """Contract tests for JSON string field conversion.

    Verifies that LLM-generated workflows with JSON string fields
    are correctly converted to objects by TaskFlowAdapter.
    """

    def test_json_string_fields_are_converted(
        self,
        adapter: TaskFlowAdapter,
        sample_workflow_with_json_strings: dict[str, Any],
    ) -> None:
        """Verify JSON string fields are converted to dict objects.

        This is the core contract test that ensures:
        - input_schema: JSON string -> dict
        - output_schema: JSON string -> dict
        - output: JSON string -> dict
        - steps[*].config.body: JSON string -> dict

        Args:
            adapter: TaskFlowAdapter instance
            sample_workflow_with_json_strings: Workflow with JSON string fields
        """
        workflow = sample_workflow_with_json_strings

        # Pre-condition: fields are JSON strings
        assert isinstance(workflow["input_schema"], str)
        assert isinstance(workflow["output_schema"], str)
        assert isinstance(workflow["output"], str)
        assert isinstance(workflow["steps"][0]["config"]["body"], str)

        # Execute conversion
        result = adapter.convert(workflow)

        # Post-condition: conversion succeeded and fields are now dicts
        data = assert_conversion_success(result)
        assert_schema_fields_are_dicts(data)
        assert isinstance(data["steps"][0]["config"]["body"], dict)

        # Verify content is preserved
        assert data["input_schema"] == {"query": "string", "limit": "number"}
        assert data["output_schema"] == {"results": "array", "total": "number"}
        assert data["steps"][0]["config"]["body"]["q"] == "${inputs.query}"

    def test_already_object_fields_are_preserved(
        self,
        adapter: TaskFlowAdapter,
        sample_workflow_with_objects: dict[str, Any],
    ) -> None:
        """Verify already-object fields are preserved unchanged.

        Args:
            adapter: TaskFlowAdapter instance
            sample_workflow_with_objects: Workflow with object fields
        """
        workflow = sample_workflow_with_objects

        # Pre-condition: fields are already dicts
        assert isinstance(workflow["input_schema"], dict)
        assert isinstance(workflow["output_schema"], dict)
        assert isinstance(workflow["output"], dict)

        # Execute conversion
        result = adapter.convert(workflow)

        # Post-condition: conversion succeeded and fields remain dicts
        data = assert_conversion_success(result)
        assert_schema_fields_are_dicts(data)

    def test_mixed_string_and_object_fields(
        self,
        adapter: TaskFlowAdapter,
    ) -> None:
        """Verify mixed string and object fields are handled correctly."""
        # Using factory function for step creation
        workflow = create_workflow(
            name="mixed_fields_test",
            input_schema='{"query": "string"}',  # JSON string
            output_schema={"result": "string"},  # Already object
            output='{"result": "${step_001.output}"}',  # JSON string
            steps=[
                create_api_rest_step(
                    step_id="step_001",
                    url="https://api.example.com",
                    method="GET",
                ),
            ],
        )

        result = adapter.convert(workflow)

        data = assert_conversion_success(result)
        assert_schema_fields_are_dicts(data)

    def test_invalid_json_string_returns_error(
        self,
        adapter: TaskFlowAdapter,
    ) -> None:
        """Verify invalid JSON strings result in conversion errors."""
        workflow = create_workflow(
            name="invalid_json_test",
            input_schema="not valid json",  # Invalid JSON
            output_schema='{"result": "string"}',
            output='{"result": "${step_001.output}"}',
            steps=[],
        )

        result = adapter.convert(workflow)

        assert result.success is False
        assert len(result.errors) > 0
        assert any("input_schema" in error for error in result.errors)


class TestPydanticModelOutputConversion:
    """Contract tests for Pydantic model output compatibility.

    Verifies that TaskFlowWorkflow.model_dump() output is correctly
    converted by TaskFlowAdapter.
    """

    def test_pydantic_model_output_is_convertible(
        self,
        adapter: TaskFlowAdapter,
        sample_pydantic_workflow: TaskFlowWorkflow,
    ) -> None:
        """Verify Pydantic model output can be converted by adapter.

        This test ensures the contract between Pydantic schema and adapter:
        - model_dump() output is valid input for adapter.convert()
        - Conversion produces valid GraphAiServer-compatible output

        Args:
            adapter: TaskFlowAdapter instance
            sample_pydantic_workflow: TaskFlowWorkflow Pydantic model instance
        """
        # Convert Pydantic model to dict
        workflow_dict = sample_pydantic_workflow.model_dump()

        # Verify Pydantic output structure has required fields
        required_fields = [
            "workflow_name",
            "input_schema",
            "output_schema",
            "output",
            "steps",
        ]
        for field in required_fields:
            assert field in workflow_dict, f"Missing required field: {field}"

        # Execute conversion
        result = adapter.convert(workflow_dict)

        # Post-condition: conversion succeeded
        data = assert_conversion_success(result, "Pydantic model conversion")

        # Verify converted fields are objects (regardless of original format)
        assert_field_is_dict(data, "input_schema", "Pydantic model")

    def test_pydantic_model_with_complex_steps(
        self,
        adapter: TaskFlowAdapter,
    ) -> None:
        """Verify Pydantic model with multiple step types is convertible."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.taskflow_schema import (
            TaskFlowStep,
            TaskFlowWorkflow,
            UnifiedStepConfig,
        )

        workflow = TaskFlowWorkflow(
            workflow_name="complex_pydantic_test",
            description="Test with multiple step types",
            input_schema='{"data": "string"}',
            output_schema='{"processed": "string"}',
            output='{"processed": "${step_002.output}"}',
            steps=[
                TaskFlowStep(
                    id="step_001",
                    type="api_rest",
                    config=UnifiedStepConfig(
                        step_type="api_rest",
                        method="GET",
                        url="https://api.example.com/fetch",
                    ),
                ),
                TaskFlowStep(
                    id="step_002",
                    type="transform",
                    config=UnifiedStepConfig(
                        step_type="transform",
                        mode="template",
                        template="Result: ${step_001.output}",
                    ),
                ),
            ],
        )

        workflow_dict = workflow.model_dump()
        result = adapter.convert(workflow_dict)

        data = assert_conversion_success(result, "Complex Pydantic model")
        assert len(data["steps"]) == 2

    def test_pydantic_model_serialization_roundtrip(
        self,
        adapter: TaskFlowAdapter,
        sample_pydantic_workflow: TaskFlowWorkflow,
    ) -> None:
        """Verify Pydantic model can be serialized, deserialized, and converted."""
        # Serialize to JSON string
        json_str = sample_pydantic_workflow.to_json()

        # Deserialize back to dict
        workflow_dict = json.loads(json_str)

        # Convert with adapter
        result = adapter.convert(workflow_dict)

        data = assert_conversion_success(result, "Serialization roundtrip")
        assert data["workflow_name"] == sample_pydantic_workflow.workflow_name


class TestFixtureWorkflowsValidation:
    """Tests using JSON fixture files.

    Verifies that all fixture workflows can be loaded and converted.
    """

    def test_fixture_directory_exists(self) -> None:
        """Verify fixture directory exists."""
        assert VALID_WORKFLOWS_DIR.exists(), (
            f"Fixture directory not found: {VALID_WORKFLOWS_DIR}"
        )

    def test_fixture_files_are_valid_json(self) -> None:
        """Verify all fixture files contain valid JSON."""
        fixture_names = list_fixture_workflows()
        assert len(fixture_names) >= 3, (
            f"Expected at least 3 fixture files, found {len(fixture_names)}"
        )

        for name in fixture_names:
            workflow = load_fixture_workflow(name)
            assert isinstance(workflow, dict), f"Fixture {name} is not a dict"
            assert "workflow_name" in workflow, f"Fixture {name} missing workflow_name"

    def test_all_fixture_workflows_are_convertible(
        self,
        adapter: TaskFlowAdapter,
        fixture_workflows: list[tuple[str, dict[str, Any]]],
    ) -> None:
        """Verify all fixture workflows can be converted by adapter.

        Args:
            adapter: TaskFlowAdapter instance
            fixture_workflows: List of (name, workflow) tuples from fixtures
        """
        assert len(fixture_workflows) >= 3, (
            f"Expected at least 3 fixtures, found {len(fixture_workflows)}"
        )

        for name, workflow in fixture_workflows:
            result = adapter.convert(workflow)
            assert_conversion_success(result, f"Fixture {name}")


@pytest.mark.integration
class TestGraphAiServerValidation:
    """Integration tests for GraphAiServer validation.

    These tests require GraphAiServer to be running at the configured URL.
    Run with: pytest -m integration

    Note: skip_if_graphai_unavailable fixture is defined in conftest.py
    """

    def test_converted_workflow_passes_graphai_validation(
        self,
        adapter: TaskFlowAdapter,
        sample_workflow_with_json_strings: dict[str, Any],
        graphai_validate_url: str,
        skip_if_graphai_unavailable: None,
    ) -> None:
        """Verify converted workflow passes GraphAiServer validation.

        This integration test ensures the full contract:
        1. LLM output (JSON strings) is converted by adapter
        2. Converted output is accepted by GraphAiServer

        Args:
            adapter: TaskFlowAdapter instance
            sample_workflow_with_json_strings: LLM-style workflow
            graphai_validate_url: GraphAiServer validation URL
            skip_if_graphai_unavailable: Fixture to skip if server unavailable
        """
        # Step 1: Convert workflow
        result = adapter.convert(sample_workflow_with_json_strings)
        data = assert_conversion_success(result)

        # Step 2: Send to GraphAiServer for validation
        # Note: GraphAiServer expects { "definition": workflow_data }
        response = httpx.post(
            graphai_validate_url,
            json={"definition": data},
            timeout=30.0,
        )

        # Step 3: Verify validation passed
        assert response.status_code == 200, (
            f"GraphAiServer validation failed: {response.status_code} - {response.text}"
        )

        validation_result = response.json()
        assert validation_result.get("valid", False) is True, (
            f"Workflow validation failed: {validation_result}"
        )

    def test_all_fixture_workflows_pass_graphai_validation(
        self,
        adapter: TaskFlowAdapter,
        fixture_workflows: list[tuple[str, dict[str, Any]]],
        graphai_validate_url: str,
        skip_if_graphai_unavailable: None,
    ) -> None:
        """Verify all fixture workflows pass GraphAiServer validation.

        Args:
            adapter: TaskFlowAdapter instance
            fixture_workflows: List of (name, workflow) tuples
            graphai_validate_url: GraphAiServer validation URL
            skip_if_graphai_unavailable: Fixture to skip if server unavailable
        """
        for name, workflow in fixture_workflows:
            # Convert workflow
            result = adapter.convert(workflow)
            data = assert_conversion_success(result, f"Fixture {name}")

            # Validate with GraphAiServer
            # Note: GraphAiServer expects { "definition": workflow_data }
            response = httpx.post(
                graphai_validate_url,
                json={"definition": data},
                timeout=30.0,
            )

            assert response.status_code == 200, (
                f"Fixture {name} GraphAiServer validation request failed: "
                f"{response.status_code}"
            )


class TestContractTestInfrastructure:
    """Tests for the contract test infrastructure itself.

    Ensures the test fixtures and utilities work correctly.
    """

    def test_adapter_fixture_is_correct_type(
        self,
        adapter: TaskFlowAdapter,
    ) -> None:
        """Verify adapter fixture returns correct type."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter import (
            TaskFlowAdapter as AdapterClass,
        )

        assert isinstance(adapter, AdapterClass)

    def test_sample_workflows_have_required_fields(
        self,
        sample_workflow_with_json_strings: dict[str, Any],
        sample_workflow_with_objects: dict[str, Any],
    ) -> None:
        """Verify sample workflows contain all required fields."""
        required_fields = [
            "workflow_name",
            "input_schema",
            "output_schema",
            "output",
            "steps",
        ]

        for field in required_fields:
            assert field in sample_workflow_with_json_strings, (
                f"Missing field {field} in json_strings workflow"
            )
            assert field in sample_workflow_with_objects, (
                f"Missing field {field} in objects workflow"
            )

    def test_graphai_validate_url_is_configured(
        self,
        graphai_validate_url: str,
    ) -> None:
        """Verify GraphAI validation URL is properly configured."""
        assert graphai_validate_url.startswith("http")
        assert "/api/v2/workflows/validate" in graphai_validate_url
