"""Unit tests for Orchestrator Issue #385 features.

Issue #385: Capability fetch and empty task validation tests.

These tests verify:
- Task 2.2: Orchestrator unit tests
- _validate_task_count() method
- _execute_workflow_gen() with capabilities
- OrchestratorError on empty tasks
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestValidateTaskCount:
    """Tests for _validate_task_count method (Task 1.3)."""

    def test_validate_task_count_success(self):
        """Test _validate_task_count passes with non-empty task list."""
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer import AnalyzedTask
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )

        orchestrator = JobGenerationOrchestrator()

        tasks = [
            AnalyzedTask(
                task_id="task_001",
                name="Test Task",
                description="Test description",
                task_type="fetch",
                recommended_api="fetchAgent",
                dependencies=[],
            ),
        ]

        # Should not raise
        orchestrator._validate_task_count(tasks)

    def test_validate_task_count_multiple_tasks(self):
        """Test _validate_task_count passes with multiple tasks."""
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer import AnalyzedTask
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )

        orchestrator = JobGenerationOrchestrator()

        tasks = [
            AnalyzedTask(
                task_id="task_001",
                name="Task 1",
                description="Description 1",
                task_type="fetch",
                recommended_api="fetchAgent",
                dependencies=[],
            ),
            AnalyzedTask(
                task_id="task_002",
                name="Task 2",
                description="Description 2",
                task_type="transform",
                recommended_api="transformAgent",
                dependencies=["task_001"],
            ),
        ]

        # Should not raise
        orchestrator._validate_task_count(tasks)

    def test_validate_task_count_empty_error(self):
        """Test _validate_task_count raises OrchestratorError with empty list."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
            OrchestratorError,
        )
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        orchestrator = JobGenerationOrchestrator()

        with pytest.raises(OrchestratorError) as exc_info:
            orchestrator._validate_task_count([])

        assert exc_info.value.phase == Phase.JOB_ANALYSIS
        assert "0" in str(exc_info.value) or "empty" in str(exc_info.value).lower()


class TestExecuteWorkflowGenWithCapabilities:
    """Tests for _execute_workflow_gen with capabilities (Task 1.2)."""

    @pytest.mark.asyncio
    async def test_execute_workflow_gen_with_capabilities(self):
        """Test _execute_workflow_gen fetches and passes capabilities."""
        from aiagent.clients.types.workflow_generator import (
            BatchStatus,
            BatchWorkflowGenerationResponse,
            WorkflowResult,
            WorkflowStatus,
        )
        from aiagent.clients.workflow_generator_client import WorkflowGeneratorClient
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer import (
            InterfaceDefinition,
        )
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )
        from aiagent.langgraph.jobGeneratorV2.types import UnifiedTaskIdentifier

        # Mock workflow generator client
        mock_client = AsyncMock(spec=WorkflowGeneratorClient)
        mock_client.fetch_capabilities = AsyncMock(
            return_value=[
                {"name": "fetchAgent", "endpoint": "/api/fetch"},
                {"name": "searchAgent", "endpoint": "/api/search"},
            ]
        )
        mock_client.generate_workflows = AsyncMock(
            return_value=BatchWorkflowGenerationResponse(
                status=BatchStatus.SUCCESS,
                success=True,
                workflows={
                    "task_001": WorkflowResult(
                        workflow_name="workflow_task_001",
                        status=WorkflowStatus.SUCCESS,
                    ),
                },
                total_tasks=1,
                succeeded_tasks=1,
                failed_task_count=0,
            )
        )

        orchestrator = JobGenerationOrchestrator(
            workflow_generator_client=mock_client,
        )

        task_identifiers = [
            UnifiedTaskIdentifier(
                task_id="task_001",
                task_master_id="tm_task_001",
            ),
        ]
        interfaces = {
            "task_001": InterfaceDefinition(
                input_schema={"query": "string"},
                output_schema={"result": "string"},
            ),
        }

        await orchestrator._execute_workflow_gen(
            task_identifiers,
            interfaces,
            project_id="test_project",
        )

        # Verify capabilities were fetched
        mock_client.fetch_capabilities.assert_called_once_with("test_project")

        # Verify generate_workflows was called with capabilities
        call_args = mock_client.generate_workflows.call_args
        assert call_args.kwargs.get("capabilities") is not None
        capabilities = call_args.kwargs["capabilities"]
        assert len(capabilities) == 2

    @pytest.mark.asyncio
    async def test_execute_workflow_gen_capability_fetch_failure(self):
        """Test _execute_workflow_gen raises error on capability fetch failure."""
        from aiagent.clients.workflow_generator_client import (
            CapabilityFetchError,
            WorkflowGeneratorClient,
        )
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer import (
            InterfaceDefinition,
        )
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
            OrchestratorError,
        )
        from aiagent.langgraph.jobGeneratorV2.types import Phase, UnifiedTaskIdentifier

        # Mock workflow generator client that fails on fetch_capabilities
        mock_client = AsyncMock(spec=WorkflowGeneratorClient)
        mock_client.fetch_capabilities = AsyncMock(
            side_effect=CapabilityFetchError(
                "Failed to fetch capabilities",
                project_id="test_project",
            )
        )

        orchestrator = JobGenerationOrchestrator(
            workflow_generator_client=mock_client,
        )

        task_identifiers = [
            UnifiedTaskIdentifier(
                task_id="task_001",
                task_master_id="tm_task_001",
            ),
        ]
        interfaces = {
            "task_001": InterfaceDefinition(
                input_schema={},
                output_schema={},
            ),
        }

        with pytest.raises(OrchestratorError) as exc_info:
            await orchestrator._execute_workflow_gen(
                task_identifiers,
                interfaces,
                project_id="test_project",
            )

        assert exc_info.value.phase == Phase.WORKFLOW_GEN
        assert "capabilities" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_execute_workflow_gen_logs_capability_summary(self):
        """Test _execute_workflow_gen logs capability summary without sensitive data."""
        import logging

        from aiagent.clients.types.workflow_generator import (
            BatchStatus,
            BatchWorkflowGenerationResponse,
        )
        from aiagent.clients.workflow_generator_client import WorkflowGeneratorClient
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )

        # Mock workflow generator client
        mock_client = AsyncMock(spec=WorkflowGeneratorClient)
        mock_client.fetch_capabilities = AsyncMock(
            return_value=[
                {"name": "fetchAgent", "api_key": "secret-key-123"},
            ]
        )
        mock_client.generate_workflows = AsyncMock(
            return_value=BatchWorkflowGenerationResponse(
                status=BatchStatus.SUCCESS,
                success=True,
                workflows={},
                total_tasks=0,
                succeeded_tasks=0,
                failed_task_count=0,
            )
        )

        orchestrator = JobGenerationOrchestrator(
            workflow_generator_client=mock_client,
        )

        task_identifiers = []
        interfaces = {}

        with patch.object(logging, "getLogger") as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            await orchestrator._execute_workflow_gen(
                task_identifiers,
                interfaces,
                project_id="test_project",
            )

            # Check that any logged message does not contain the secret key
            for call in mock_logger.info.call_args_list:
                logged_message = str(call)
                assert "secret-key-123" not in logged_message


class TestExecuteJobAnalysisWithValidation:
    """Tests for _execute_job_analysis with empty task validation."""

    @pytest.mark.asyncio
    async def test_execute_job_analysis_validates_task_count(self):
        """Test _execute_job_analysis calls _validate_task_count."""
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer import (
            JobAnalysisResponse,
        )
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
            JobGenerationRequest,
            OrchestratorError,
        )
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        orchestrator = JobGenerationOrchestrator()

        # Mock analyze_job to return empty tasks
        with patch(
            "aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer.analyze_job"
        ) as mock_analyze:
            mock_analyze.return_value = JobAnalysisResponse(
                tasks=[],  # Empty task list
                interfaces={},
            )

            request = JobGenerationRequest(
                user_requirement="Test requirement",
                project_id="test_project",
            )

            with pytest.raises(OrchestratorError) as exc_info:
                await orchestrator._execute_job_analysis(request)

            assert exc_info.value.phase == Phase.JOB_ANALYSIS


class TestOrchestratorErrorPhase:
    """Tests for OrchestratorError with phase information."""

    def test_orchestrator_error_with_phase(self):
        """Test OrchestratorError stores phase information."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator import OrchestratorError
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        error = OrchestratorError(
            "Task validation failed",
            phase=Phase.JOB_ANALYSIS,
        )

        assert error.phase == Phase.JOB_ANALYSIS
        assert "Task validation failed" in str(error)

    def test_orchestrator_error_without_phase(self):
        """Test OrchestratorError works without phase."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator import OrchestratorError

        error = OrchestratorError("Generic error")

        assert error.phase is None
        assert "Generic error" in str(error)
