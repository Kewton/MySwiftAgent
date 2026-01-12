"""Unit tests for TaskFlowAdapter.

Issue #355: TaskFlow Adapter Layer implementation.
Tests TC-001 through TC-012 from acceptance-plan.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter.taskflow_adapter import (
        TaskFlowAdapter,
    )


class TestConversionResultStructure:
    """TC-007: ConversionResult structure verification."""

    def test_tc_007_conversion_result_structure(self) -> None:
        """ConversionResult has correct structure."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter.taskflow_adapter import (
            ConversionResult,
        )

        result = ConversionResult(
            success=True,
            data={"key": "value"},
            errors=[],
            warnings=["test warning"],
        )

        assert isinstance(result.success, bool)
        assert isinstance(result.data, dict)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.errors == []
        assert result.warnings == ["test warning"]

    def test_conversion_result_with_failure(self) -> None:
        """ConversionResult with failure state."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter.taskflow_adapter import (
            ConversionResult,
        )

        result = ConversionResult(
            success=False,
            data=None,
            errors=["error 1", "error 2"],
            warnings=[],
        )

        assert result.success is False
        assert result.data is None
        assert len(result.errors) == 2
        assert "error 1" in result.errors


class TestTaskFlowAdapterConstants:
    """Test TaskFlowAdapter class constants."""

    def test_workflow_json_string_fields_defined(self) -> None:
        """WORKFLOW_JSON_STRING_FIELDS contains correct fields."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter.taskflow_adapter import (
            TaskFlowAdapter,
        )

        assert hasattr(TaskFlowAdapter, "WORKFLOW_JSON_STRING_FIELDS")
        assert "input_schema" in TaskFlowAdapter.WORKFLOW_JSON_STRING_FIELDS
        assert "output_schema" in TaskFlowAdapter.WORKFLOW_JSON_STRING_FIELDS
        assert "output" in TaskFlowAdapter.WORKFLOW_JSON_STRING_FIELDS

    def test_step_json_string_fields_defined(self) -> None:
        """STEP_JSON_STRING_FIELDS contains correct fields."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter.taskflow_adapter import (
            TaskFlowAdapter,
        )

        assert hasattr(TaskFlowAdapter, "STEP_JSON_STRING_FIELDS")
        assert "body" in TaskFlowAdapter.STEP_JSON_STRING_FIELDS


class TestJsonStringToObjectConversion:
    """Tests for JSON string to object conversion (TC-001 to TC-004)."""

    @pytest.fixture
    def adapter(self) -> TaskFlowAdapter:
        """Create TaskFlowAdapter instance."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter.taskflow_adapter import (
            TaskFlowAdapter,
        )

        return TaskFlowAdapter()

    def test_tc_001_convert_json_string_input_schema(
        self, adapter: TaskFlowAdapter
    ) -> None:
        """TC-001: JSON string input_schema is converted to object."""
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": '{"query": "string"}',
            "output_schema": '{"result": "string"}',
            "output": '{"result": "${step_001.output}"}',
            "steps": [
                {
                    "id": "step_001",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "GET",
                        "url": "https://example.com",
                    },
                }
            ],
        }

        result = adapter.convert(workflow)

        assert result.success is True
        assert isinstance(result.data["input_schema"], dict)
        assert result.data["input_schema"] == {"query": "string"}

    def test_tc_002_convert_json_string_output_schema(
        self, adapter: TaskFlowAdapter
    ) -> None:
        """TC-002: JSON string output_schema is converted to object."""
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": '{"query": "string"}',
            "output_schema": '{"result": "string", "count": "number"}',
            "output": '{"result": "${step_001.output}"}',
            "steps": [
                {
                    "id": "step_001",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "GET",
                        "url": "https://example.com",
                    },
                }
            ],
        }

        result = adapter.convert(workflow)

        assert result.success is True
        assert isinstance(result.data["output_schema"], dict)
        assert result.data["output_schema"] == {"result": "string", "count": "number"}

    def test_tc_003_convert_json_string_output(self, adapter: TaskFlowAdapter) -> None:
        """TC-003: JSON string output is converted to object.

        Variable references like ${step_001.output} should be preserved.
        """
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": '{"query": "string"}',
            "output_schema": '{"result": "string"}',
            "output": '{"result": "${step_001.output.data}"}',
            "steps": [
                {
                    "id": "step_001",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "GET",
                        "url": "https://example.com",
                    },
                }
            ],
        }

        result = adapter.convert(workflow)

        assert result.success is True
        assert isinstance(result.data["output"], dict)
        assert result.data["output"] == {"result": "${step_001.output.data}"}

    def test_tc_004_convert_json_string_step_body(
        self, adapter: TaskFlowAdapter
    ) -> None:
        """TC-004: JSON string steps[*].config.body is converted to object."""
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": '{"query": "string"}',
            "output_schema": '{"result": "string"}',
            "output": '{"result": "${step_001.output}"}',
            "steps": [
                {
                    "id": "step_001",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "POST",
                        "url": "https://example.com/api",
                        "body": '{"data": "${inputs.query}"}',
                    },
                }
            ],
        }

        result = adapter.convert(workflow)

        assert result.success is True
        body = result.data["steps"][0]["config"]["body"]
        assert isinstance(body, dict)
        assert body == {"data": "${inputs.query}"}


class TestExistingObjectPreservation:
    """TC-005: Tests for preserving existing objects."""

    @pytest.fixture
    def adapter(self) -> TaskFlowAdapter:
        """Create TaskFlowAdapter instance."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter.taskflow_adapter import (
            TaskFlowAdapter,
        )

        return TaskFlowAdapter()

    def test_tc_005_preserve_existing_objects(self, adapter: TaskFlowAdapter) -> None:
        """TC-005: Existing dict objects are preserved unchanged."""
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": {"query": "string"},  # Already a dict
            "output_schema": {"result": "string"},  # Already a dict
            "output": {"result": "${step_001.output}"},  # Already a dict
            "steps": [
                {
                    "id": "step_001",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "POST",
                        "url": "https://example.com/api",
                        "body": {"data": "value"},  # Already a dict
                    },
                }
            ],
        }

        result = adapter.convert(workflow)

        assert result.success is True
        assert result.data["input_schema"] == {"query": "string"}
        assert result.data["output_schema"] == {"result": "string"}
        assert result.data["output"] == {"result": "${step_001.output}"}
        assert result.data["steps"][0]["config"]["body"] == {"data": "value"}

    def test_preserve_none_values(self, adapter: TaskFlowAdapter) -> None:
        """None values are preserved."""
        workflow: dict[str, Any] = {
            "workflow_name": "test_workflow",
            "input_schema": None,
            "output_schema": None,
            "output": None,
            "steps": [],
        }

        result = adapter.convert(workflow)

        assert result.success is True
        assert result.data["input_schema"] is None
        assert result.data["output_schema"] is None
        assert result.data["output"] is None


class TestInvalidJsonHandling:
    """TC-006: Tests for invalid JSON error handling."""

    @pytest.fixture
    def adapter(self) -> TaskFlowAdapter:
        """Create TaskFlowAdapter instance."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter.taskflow_adapter import (
            TaskFlowAdapter,
        )

        return TaskFlowAdapter()

    def test_tc_006_error_on_invalid_json(self, adapter: TaskFlowAdapter) -> None:
        """TC-006: Invalid JSON string returns error."""
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": "invalid json string",
            "output_schema": '{"result": "string"}',
            "output": '{"result": "${step_001.output}"}',
            "steps": [],
        }

        result = adapter.convert(workflow)

        assert result.success is False
        assert len(result.errors) > 0
        assert any("input_schema" in error for error in result.errors)
        assert any(
            "Invalid JSON" in error or "JSON" in error for error in result.errors
        )

    def test_error_on_invalid_json_output_schema(
        self, adapter: TaskFlowAdapter
    ) -> None:
        """Invalid JSON in output_schema returns error."""
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": '{"query": "string"}',
            "output_schema": "{broken",
            "output": '{"result": "${step_001.output}"}',
            "steps": [],
        }

        result = adapter.convert(workflow)

        assert result.success is False
        assert any("output_schema" in error for error in result.errors)

    def test_error_on_invalid_json_output(self, adapter: TaskFlowAdapter) -> None:
        """Invalid JSON in output returns error."""
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": '{"query": "string"}',
            "output_schema": '{"result": "string"}',
            "output": "not valid json",
            "steps": [],
        }

        result = adapter.convert(workflow)

        assert result.success is False
        assert any("output" in error.lower() for error in result.errors)

    def test_error_message_contains_field_name_and_cause(
        self, adapter: TaskFlowAdapter
    ) -> None:
        """Error message contains field name and error cause."""
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": "{invalid: json}",
            "output_schema": '{"result": "string"}',
            "output": '{"result": "${step_001.output}"}',
            "steps": [],
        }

        result = adapter.convert(workflow)

        assert result.success is False
        error_message = " ".join(result.errors)
        assert "input_schema" in error_message

    def test_non_string_non_dict_returns_error(self, adapter: TaskFlowAdapter) -> None:
        """Non-string, non-dict value returns error."""
        workflow: dict[str, Any] = {
            "workflow_name": "test_workflow",
            "input_schema": 12345,  # Invalid type
            "output_schema": '{"result": "string"}',
            "output": '{"result": "${step_001.output}"}',
            "steps": [],
        }

        result = adapter.convert(workflow)

        assert result.success is False
        assert any("input_schema" in error for error in result.errors)


class TestMultipleFieldConversion:
    """TC-011: Tests for multiple field simultaneous conversion."""

    @pytest.fixture
    def adapter(self) -> TaskFlowAdapter:
        """Create TaskFlowAdapter instance."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter.taskflow_adapter import (
            TaskFlowAdapter,
        )

        return TaskFlowAdapter()

    def test_tc_011_convert_multiple_fields(self, adapter: TaskFlowAdapter) -> None:
        """TC-011: Multiple JSON string fields are converted simultaneously."""
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": '{"query": "string", "limit": "number"}',
            "output_schema": '{"results": "array", "total": "number"}',
            "output": '{"results": "${step_001.output.items}", "total": "${step_001.output.count}"}',
            "steps": [
                {
                    "id": "step_001",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "POST",
                        "url": "https://example.com/search",
                        "body": '{"q": "${inputs.query}", "max": "${inputs.limit}"}',
                    },
                },
                {
                    "id": "step_002",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "POST",
                        "url": "https://example.com/log",
                        "body": '{"message": "search completed"}',
                    },
                },
            ],
        }

        result = adapter.convert(workflow)

        assert result.success is True
        # Verify all workflow-level fields are converted
        assert isinstance(result.data["input_schema"], dict)
        assert isinstance(result.data["output_schema"], dict)
        assert isinstance(result.data["output"], dict)
        # Verify all step bodies are converted
        assert isinstance(result.data["steps"][0]["config"]["body"], dict)
        assert isinstance(result.data["steps"][1]["config"]["body"], dict)


class TestDeepCopyPreservation:
    """TC-012: Tests for deep copy preservation."""

    @pytest.fixture
    def adapter(self) -> TaskFlowAdapter:
        """Create TaskFlowAdapter instance."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter.taskflow_adapter import (
            TaskFlowAdapter,
        )

        return TaskFlowAdapter()

    def test_tc_012_deep_copy_preservation(self, adapter: TaskFlowAdapter) -> None:
        """TC-012: Original data is not modified by conversion."""
        original_workflow = {
            "workflow_name": "test_workflow",
            "input_schema": '{"query": "string"}',
            "output_schema": '{"result": "string"}',
            "output": '{"result": "${step_001.output}"}',
            "steps": [
                {
                    "id": "step_001",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "POST",
                        "url": "https://example.com/api",
                        "body": '{"data": "value"}',
                    },
                }
            ],
        }

        # Store original values
        original_input_schema = original_workflow["input_schema"]
        original_body = original_workflow["steps"][0]["config"]["body"]

        result = adapter.convert(original_workflow)

        # Verify conversion succeeded
        assert result.success is True

        # Verify original data is unchanged
        assert original_workflow["input_schema"] == original_input_schema
        assert original_workflow["steps"][0]["config"]["body"] == original_body
        assert isinstance(original_workflow["input_schema"], str)

        # Verify result data is different
        assert isinstance(result.data["input_schema"], dict)

    def test_deep_copy_nested_structures(self, adapter: TaskFlowAdapter) -> None:
        """Deep copy preserves nested structure independence."""
        original_workflow: dict[str, Any] = {
            "workflow_name": "test_workflow",
            "input_schema": {"nested": {"deep": "value"}},
            "output_schema": {"result": "string"},
            "output": {"result": "${step_001.output}"},
            "steps": [],
        }

        result = adapter.convert(original_workflow)

        # Modify the result
        result.data["input_schema"]["nested"]["deep"] = "modified"

        # Original should be unchanged
        assert original_workflow["input_schema"]["nested"]["deep"] == "value"


class TestUnexpectedErrorHandling:
    """Tests for unexpected error handling."""

    @pytest.fixture
    def adapter(self) -> TaskFlowAdapter:
        """Create TaskFlowAdapter instance."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter.taskflow_adapter import (
            TaskFlowAdapter,
        )

        return TaskFlowAdapter()

    def test_handles_unexpected_exception(self, adapter: TaskFlowAdapter) -> None:
        """Unexpected exceptions are caught and returned as errors."""
        # Pass something that will cause an unexpected error
        workflow = None  # type: ignore

        result = adapter.convert(workflow)  # type: ignore

        assert result.success is False
        assert any(
            "Unexpected" in error or "error" in error.lower() for error in result.errors
        )


class TestStepConversion:
    """Tests for step-level conversion."""

    @pytest.fixture
    def adapter(self) -> TaskFlowAdapter:
        """Create TaskFlowAdapter instance."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter.taskflow_adapter import (
            TaskFlowAdapter,
        )

        return TaskFlowAdapter()

    def test_step_without_config_is_handled(self, adapter: TaskFlowAdapter) -> None:
        """Steps without config field are handled gracefully."""
        workflow: dict[str, Any] = {
            "workflow_name": "test_workflow",
            "input_schema": '{"query": "string"}',
            "output_schema": '{"result": "string"}',
            "output": '{"result": "${step_001.output}"}',
            "steps": [
                {
                    "id": "step_001",
                    "type": "transform",
                    # No config field
                }
            ],
        }

        result = adapter.convert(workflow)

        # Should succeed (no conversion needed for config.body)
        assert result.success is True

    def test_step_config_without_body_is_handled(
        self, adapter: TaskFlowAdapter
    ) -> None:
        """Step config without body field is handled gracefully."""
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": '{"query": "string"}',
            "output_schema": '{"result": "string"}',
            "output": '{"result": "${step_001.output}"}',
            "steps": [
                {
                    "id": "step_001",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "GET",
                        "url": "https://example.com",
                        # No body field
                    },
                }
            ],
        }

        result = adapter.convert(workflow)

        assert result.success is True

    def test_step_with_params_is_preserved(self, adapter: TaskFlowAdapter) -> None:
        """Step params field is preserved during conversion."""
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": '{"query": "string"}',
            "output_schema": '{"result": "string"}',
            "output": '{"result": "${step_001.output}"}',
            "steps": [
                {
                    "id": "step_001",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "GET",
                        "url": "https://example.com",
                    },
                    "params": {
                        "api_key": "${secrets.API_KEY}",
                    },
                }
            ],
        }

        result = adapter.convert(workflow)

        assert result.success is True
        assert result.data["steps"][0]["params"] == {"api_key": "${secrets.API_KEY}"}
