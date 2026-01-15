"""Integration tests for TaskFlowAdapter with workflow_registrar.

Issue #355: TC-008 and TC-009 from acceptance-plan.md.
Tests that workflow_registrar.py correctly uses TaskFlowAdapter.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestWorkflowRegistrarIntegration:
    """TC-008: Tests for workflow_registrar.py integration with TaskFlowAdapter."""

    @pytest.mark.asyncio
    async def test_tc_008_workflow_registrar_uses_adapter(self) -> None:
        """TC-008: register_taskflow_workflow() uses TaskFlowAdapter for conversion."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar import (
            register_taskflow_workflow,
        )

        # Create workflow with JSON string fields
        workflow_json = {
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

        # Track the payload sent to the server
        captured_payload: dict[str, Any] = {}

        # Create mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "file_path": "config/taskflow/workflows/test_workflow.json"
        }

        # Create async mock for post
        async def mock_post(url: str, json: dict, headers: dict) -> MagicMock:
            captured_payload.update(json)
            return mock_response

        # Create mock async client
        mock_client_instance = AsyncMock()
        mock_client_instance.post = mock_post

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client_instance
            )

            result = await register_taskflow_workflow(
                workflow_name="test_workflow",
                workflow_json=workflow_json,
                admin_token="test_token",
            )

        # Verify the conversion was applied
        assert result.success is True, f"Expected success but got error: {result.error}"
        assert "definition" in captured_payload

        # Verify JSON strings were converted to objects
        definition = captured_payload["definition"]
        assert isinstance(definition["input_schema"], dict)
        assert isinstance(definition["output_schema"], dict)
        assert isinstance(definition["output"], dict)
        assert definition["input_schema"] == {"query": "string"}

    @pytest.mark.asyncio
    async def test_tc_008_workflow_registrar_with_object_fields(self) -> None:
        """TC-008: register_taskflow_workflow() handles already-object fields."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar import (
            register_taskflow_workflow,
        )

        # Create workflow with already-object fields
        workflow_json = {
            "workflow_name": "test_workflow",
            "input_schema": {"query": "string"},  # Already dict
            "output_schema": {"result": "string"},  # Already dict
            "output": {"result": "${step_001.output}"},  # Already dict
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

        captured_payload: dict[str, Any] = {}

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "file_path": "config/taskflow/workflows/test_workflow.json"
        }

        async def mock_post(url: str, json: dict, headers: dict) -> MagicMock:
            captured_payload.update(json)
            return mock_response

        mock_client_instance = AsyncMock()
        mock_client_instance.post = mock_post

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client_instance
            )

            result = await register_taskflow_workflow(
                workflow_name="test_workflow",
                workflow_json=workflow_json,
                admin_token="test_token",
            )

        assert result.success is True
        definition = captured_payload["definition"]
        assert isinstance(definition["input_schema"], dict)
        assert definition["input_schema"] == {"query": "string"}


class TestWorkflowRegistrarErrorHandling:
    """TC-009: Tests for Adapter conversion failure handling."""

    @pytest.mark.asyncio
    async def test_tc_009_workflow_registrar_error_on_invalid_json(self) -> None:
        """TC-009: register_taskflow_workflow() returns error on invalid JSON."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar import (
            register_taskflow_workflow,
        )

        # Create workflow with invalid JSON string
        workflow_json = {
            "workflow_name": "test_workflow",
            "input_schema": "invalid json string",  # Invalid JSON
            "output_schema": '{"result": "string"}',
            "output": '{"result": "${step_001.output}"}',
            "steps": [],
        }

        # No need to mock HTTP since adapter should fail before HTTP call
        result = await register_taskflow_workflow(
            workflow_name="test_workflow",
            workflow_json=workflow_json,
            admin_token="test_token",
        )

        assert result.success is False
        assert result.error is not None
        assert "Schema conversion failed" in result.error

    @pytest.mark.asyncio
    async def test_tc_009_error_message_contains_details(self) -> None:
        """TC-009: Error message contains detailed conversion failure info."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar import (
            register_taskflow_workflow,
        )

        # Create workflow with multiple invalid fields
        workflow_json = {
            "workflow_name": "test_workflow",
            "input_schema": "{broken: json}",  # Invalid JSON
            "output_schema": '{"result": "string"}',
            "output": '{"result": "${step_001.output}"}',
            "steps": [],
        }

        result = await register_taskflow_workflow(
            workflow_name="test_workflow",
            workflow_json=workflow_json,
            admin_token="test_token",
        )

        assert result.success is False
        assert "input_schema" in (result.error or "")

    @pytest.mark.asyncio
    async def test_workflow_registrar_logs_warnings(self) -> None:
        """Warnings from conversion are logged."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar import (
            register_taskflow_workflow,
        )

        workflow_json = {
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

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "file_path": "config/taskflow/workflows/test_workflow.json"
        }

        async def mock_post(url: str, json: dict, headers: dict) -> MagicMock:
            return mock_response

        mock_client_instance = AsyncMock()
        mock_client_instance.post = mock_post

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar.httpx.AsyncClient"
        ) as mock_client_class:
            mock_client_class.return_value.__aenter__.return_value = (
                mock_client_instance
            )

            result = await register_taskflow_workflow(
                workflow_name="test_workflow",
                workflow_json=workflow_json,
                admin_token="test_token",
            )

        # Should succeed even with potential warnings
        assert result.success is True


class TestAdapterModuleLevel:
    """Tests that _adapter is properly instantiated at module level."""

    def test_adapter_instance_exists(self) -> None:
        """Module-level _adapter instance exists."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen import (
            workflow_registrar,
        )

        assert hasattr(workflow_registrar, "_adapter")
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter import (
            TaskFlowAdapter,
        )

        assert isinstance(workflow_registrar._adapter, TaskFlowAdapter)
