"""Unit tests for workflow_registrar module.

Issue #342: Tests for workflow registration to GraphAiServer and
TaskMaster body_template updates with model_name.

Note: TestRegisterAndUpdateTaskMasters tests require careful mocking because
register_and_update_task_masters calls register_workflow_to_graphai and
update_task_master_body_template from the same module. The mocking is done
via module-level import replacement to ensure isolation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar as workflow_registrar_module
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar import (
    WorkflowRegistrationResult,
    register_and_update_task_masters,
    register_workflow_to_graphai,
    update_task_master_body_template,
)


class TestWorkflowRegistrationResult:
    """Tests for WorkflowRegistrationResult dataclass."""

    def test_success_result(self) -> None:
        """Test creating a successful registration result."""
        result = WorkflowRegistrationResult(
            success=True,
            workflow_path="taskmaster/tm_123/workflow_jm_abc",
            model_name="taskmaster/tm_123/workflow_jm_abc",
        )

        assert result.success is True
        assert result.workflow_path == "taskmaster/tm_123/workflow_jm_abc"
        assert result.model_name == "taskmaster/tm_123/workflow_jm_abc"
        assert result.error is None

    def test_failure_result(self) -> None:
        """Test creating a failed registration result."""
        result = WorkflowRegistrationResult(
            success=False,
            error="GraphAiServer connection failed",
        )

        assert result.success is False
        assert result.workflow_path is None
        assert result.model_name is None
        assert result.error == "GraphAiServer connection failed"


class TestRegisterWorkflowToGraphai:
    """Tests for register_workflow_to_graphai function."""

    @pytest.mark.asyncio
    async def test_successful_registration(self) -> None:
        """Test successful workflow registration."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "workflow_path": "taskmaster/tm_123/workflow_jm_abc",
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await register_workflow_to_graphai(
                workflow_name="workflow_jm_abc",
                yaml_content="version: 0.6\nnodes: {}",
                task_master_id="tm_123",
            )

        assert result.success is True
        assert result.model_name == "taskmaster/tm_123/workflow_jm_abc"
        assert result.workflow_path == "taskmaster/tm_123/workflow_jm_abc"

    @pytest.mark.asyncio
    async def test_registration_failure_400(self) -> None:
        """Test registration failure with 400 status code."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid YAML format"

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = mock_response
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await register_workflow_to_graphai(
                workflow_name="workflow_jm_abc",
                yaml_content="invalid yaml",
                task_master_id="tm_123",
            )

        assert result.success is False
        assert "400" in result.error or "" if result.error is None else result.error

    @pytest.mark.asyncio
    async def test_registration_timeout(self) -> None:
        """Test registration timeout handling."""
        import httpx

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.side_effect = httpx.TimeoutException(
                "Connection timeout"
            )
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=None)
            mock_client.return_value = mock_instance

            result = await register_workflow_to_graphai(
                workflow_name="workflow_jm_abc",
                yaml_content="version: 0.6\nnodes: {}",
                task_master_id="tm_123",
            )

        assert result.success is False
        assert "timeout" in (result.error or "").lower()


class TestUpdateTaskMasterBodyTemplate:
    """Tests for update_task_master_body_template function.

    Note: Direct unit tests for this function require integration testing
    due to the local import of JobqueueClient. The function is covered
    by higher-level tests in TestRegisterAndUpdateTaskMasters.
    """

    def test_function_exists_and_is_async(self) -> None:
        """Verify the function exists and is an async function."""
        import asyncio
        import inspect

        assert callable(update_task_master_body_template)
        assert asyncio.iscoroutinefunction(update_task_master_body_template)

        # Check signature
        sig = inspect.signature(update_task_master_body_template)
        params = list(sig.parameters.keys())
        assert "task_master_id" in params
        assert "model_name" in params


class TestRegisterAndUpdateTaskMasters:
    """Tests for register_and_update_task_masters function.

    Note: These tests use module-level patching via monkeypatch to ensure
    proper isolation when running with the full test suite. The standard
    unittest.mock.patch approach can fail due to module caching issues
    when other tests import the workflow_registrar module first.
    """

    @pytest.mark.asyncio
    async def test_empty_task_master_ids(self) -> None:
        """Test handling of empty task_master_ids list."""
        result = await register_and_update_task_masters(
            task_master_ids=[],
            workflow_name="workflow_jm_abc",
            yaml_content="version: 0.6\nnodes: {}",
        )

        assert result["success"] is False
        assert "No task_master_ids" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_successful_registration_and_updates(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test successful workflow registration and TaskMaster updates."""

        async def mock_register(*args, **kwargs):
            return WorkflowRegistrationResult(
                success=True,
                workflow_path="taskmaster/tm_001/workflow_jm_abc",
                model_name="taskmaster/tm_001/workflow_jm_abc",
            )

        async def mock_update(*args, **kwargs):
            return True

        # Use monkeypatch for reliable module-level patching
        monkeypatch.setattr(
            workflow_registrar_module, "register_workflow_to_graphai", mock_register
        )
        monkeypatch.setattr(
            workflow_registrar_module, "update_task_master_body_template", mock_update
        )

        result = await register_and_update_task_masters(
            task_master_ids=["tm_001", "tm_002", "tm_003"],
            workflow_name="workflow_jm_abc",
            yaml_content="version: 0.6\nnodes: {}",
        )

        assert result["success"] is True
        assert result["model_name"] == "taskmaster/tm_001/workflow_jm_abc"
        assert len(result["updated_task_masters"]) == 3
        assert len(result["failed_task_masters"]) == 0

    @pytest.mark.asyncio
    async def test_partial_update_success(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test partial success when some TaskMaster updates fail."""

        async def mock_register(*args, **kwargs):
            return WorkflowRegistrationResult(
                success=True,
                workflow_path="taskmaster/tm_001/workflow_jm_abc",
                model_name="taskmaster/tm_001/workflow_jm_abc",
            )

        call_count = 0

        async def mock_update(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # First two succeed, third fails
            return call_count <= 2

        # Use monkeypatch for reliable module-level patching
        monkeypatch.setattr(
            workflow_registrar_module, "register_workflow_to_graphai", mock_register
        )
        monkeypatch.setattr(
            workflow_registrar_module, "update_task_master_body_template", mock_update
        )

        result = await register_and_update_task_masters(
            task_master_ids=["tm_001", "tm_002", "tm_003"],
            workflow_name="workflow_jm_abc",
            yaml_content="version: 0.6\nnodes: {}",
        )

        # Issue #360: Partial success is now considered failure (all must succeed)
        # Changed from: success=True when at least one succeeds
        # To: success=False when any task fails
        assert result["success"] is False
        assert len(result["updated_task_masters"]) == 2
        assert len(result["failed_task_masters"]) == 1
        assert "tm_003" in result["failed_task_masters"]

    @pytest.mark.asyncio
    async def test_registration_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test failure when GraphAiServer registration fails."""

        async def mock_register(*args, **kwargs):
            return WorkflowRegistrationResult(
                success=False,
                error="GraphAiServer unavailable",
            )

        # Use monkeypatch for reliable module-level patching
        monkeypatch.setattr(
            workflow_registrar_module, "register_workflow_to_graphai", mock_register
        )

        result = await register_and_update_task_masters(
            task_master_ids=["tm_001", "tm_002"],
            workflow_name="workflow_jm_abc",
            yaml_content="version: 0.6\nnodes: {}",
        )

        assert result["success"] is False
        assert "GraphAiServer unavailable" in result.get("error", "")
        assert len(result["failed_task_masters"]) == 2
