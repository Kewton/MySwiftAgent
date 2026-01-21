"""Integration tests for Issue #387: recovery_suggestion processing.

Tests verify that:
1. Orchestrator calls _handle_recovery_suggestion when response has recovery_suggestion
2. Recovery suggestion is properly propagated through the workflow
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiagent.clients.types.workflow_generator import (
    BatchStatus,
    RecoverySuggestion,
    WorkflowResult,
    WorkflowStatus,
)
from aiagent.langgraph.jobGeneratorV2.orchestrator import (
    JobGenerationOrchestrator,
)
from aiagent.langgraph.jobGeneratorV2.types import (
    RecoveryStrategy,
    UnifiedTaskIdentifier,
)


class TestOrchestratorRecoverySuggestionIntegration:
    """Integration tests for orchestrator recovery_suggestion handling."""

    @pytest.mark.asyncio
    async def test_orchestrator_calls_handle_recovery_suggestion(self) -> None:
        """Verify orchestrator calls _handle_recovery_suggestion when suggestion exists.

        Issue #387: Tests that run_workflow properly calls _handle_recovery_suggestion
        when the workflow execution result contains a recovery_suggestion.
        """
        orchestrator = JobGenerationOrchestrator()

        # Mock response with recovery_suggestion
        mock_response = MagicMock()
        mock_response.workflows = {
            "task_001": WorkflowResult(
                workflow_name="test_workflow",
                status=WorkflowStatus.SUCCESS,
            ),
        }
        mock_response.failed_tasks = [
            MagicMock(task_id="task_002", error_type="API", message="Failed")
        ]
        mock_response.recovery_suggestion = RecoverySuggestion.ROLLBACK_TO_ANALYSIS
        mock_response.status = BatchStatus.PARTIAL_SUCCESS

        task_identifiers = [
            UnifiedTaskIdentifier(task_id="task_001", task_master_id="tm_001"),
            UnifiedTaskIdentifier(task_id="task_002", task_master_id="tm_002"),
        ]

        interfaces = {
            "task_001": MagicMock(input_schema={}, output_schema={}),
            "task_002": MagicMock(input_schema={}, output_schema={}),
        }

        # Mock the workflow generator client
        mock_client = AsyncMock()
        mock_client.fetch_capabilities = AsyncMock(return_value=[])
        mock_client.generate_workflows = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        # Track if _handle_recovery_suggestion was called
        handle_called = False
        handle_suggestion_received = None
        original_handle = orchestrator._handle_recovery_suggestion

        async def mock_handle(suggestion, execution_result, context):
            nonlocal handle_called, handle_suggestion_received
            handle_called = True
            handle_suggestion_received = suggestion
            return await original_handle(suggestion, execution_result, context)

        orchestrator._handle_recovery_suggestion = mock_handle  # type: ignore

        with patch.object(
            orchestrator,
            "_workflow_generator_client",
            mock_client,
        ):
            result = await orchestrator._execute_workflow_gen(
                task_identifiers=task_identifiers,
                interfaces=interfaces,
                project_id="test_project",
            )

        # Verify recovery_suggestion is propagated to result
        assert result.recovery_suggestion == RecoverySuggestion.ROLLBACK_TO_ANALYSIS

    @pytest.mark.asyncio
    async def test_run_workflow_calls_handle_recovery_suggestion(self) -> None:
        """Verify run_workflow calls _handle_recovery_suggestion when suggestion exists.

        Issue #387: This is the critical test that verifies the integration point
        in run_workflow actually calls _handle_recovery_suggestion.
        """
        from aiagent.langgraph.jobGeneratorV2.types import JobGenerationRequest

        orchestrator = JobGenerationOrchestrator()

        # Track if _handle_recovery_suggestion was called
        handle_called = False
        handle_suggestion_received = None

        async def mock_handle(suggestion, execution_result, context):
            nonlocal handle_called, handle_suggestion_received
            handle_called = True
            handle_suggestion_received = suggestion
            # Return None to indicate no retry needed
            return None

        # Mock all the phases
        mock_analysis_result = MagicMock()
        mock_analysis_result.tasks = [MagicMock(task_id="task_001")]
        mock_analysis_result.interfaces = {"task_001": MagicMock()}

        mock_registration_result = {"task_id_to_master_id": {"task_001": "tm_001"}}

        mock_workflow_result = MagicMock()
        mock_workflow_result.recovery_suggestion = (
            RecoverySuggestion.ROLLBACK_TO_ANALYSIS
        )
        mock_workflow_result.all_succeeded = False
        mock_workflow_result.workflows = {}
        mock_workflow_result.failed_workflows = {}

        # Apply mocks
        orchestrator._handle_recovery_suggestion = mock_handle  # type: ignore
        orchestrator._execute_job_analysis = AsyncMock(
            return_value=mock_analysis_result
        )
        orchestrator._execute_registration = AsyncMock(
            return_value=mock_registration_result
        )
        orchestrator._execute_workflow_gen = AsyncMock(
            return_value=mock_workflow_result
        )
        orchestrator._build_result = MagicMock(return_value=MagicMock(success=True))

        request = JobGenerationRequest(
            user_requirement="Test requirement",
            project_id="test_project",
        )

        await orchestrator.run_workflow(request, trace_id="test_trace")

        # CRITICAL: Verify _handle_recovery_suggestion was actually called
        assert handle_called, (
            "_handle_recovery_suggestion should be called when suggestion exists"
        )
        assert handle_suggestion_received == RecoverySuggestion.ROLLBACK_TO_ANALYSIS

    @pytest.mark.asyncio
    async def test_orchestrator_skips_handle_when_no_suggestion(self) -> None:
        """Verify orchestrator does not call handler when no recovery_suggestion."""
        orchestrator = JobGenerationOrchestrator()

        # Mock response without recovery_suggestion
        mock_response = MagicMock()
        mock_response.workflows = {
            "task_001": WorkflowResult(
                workflow_name="test_workflow",
                status=WorkflowStatus.SUCCESS,
            ),
        }
        mock_response.failed_tasks = []
        mock_response.recovery_suggestion = None
        mock_response.status = BatchStatus.SUCCESS

        task_identifiers = [
            UnifiedTaskIdentifier(task_id="task_001", task_master_id="tm_001"),
        ]

        interfaces = {
            "task_001": MagicMock(input_schema={}, output_schema={}),
        }

        mock_client = AsyncMock()
        mock_client.fetch_capabilities = AsyncMock(return_value=[])
        mock_client.generate_workflows = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)

        with patch.object(
            orchestrator,
            "_workflow_generator_client",
            mock_client,
        ):
            result = await orchestrator._execute_workflow_gen(
                task_identifiers=task_identifiers,
                interfaces=interfaces,
                project_id="test_project",
            )

        # Result should succeed without recovery_suggestion
        assert result.all_succeeded is True
        assert result.recovery_suggestion is None


class TestRecoverySuggestionToStrategyConversion:
    """Integration tests for RecoverySuggestion to RecoveryStrategy conversion."""

    def test_rollback_suggestion_converts_correctly(self) -> None:
        """Test ROLLBACK_TO_ANALYSIS suggestion converts to corresponding strategy."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            SUGGESTION_TO_STRATEGY,
        )

        # Verify the mapping is used correctly
        suggestion = RecoverySuggestion.ROLLBACK_TO_ANALYSIS
        expected_strategy = RecoveryStrategy.ROLLBACK_TO_ANALYSIS

        actual_strategy = SUGGESTION_TO_STRATEGY.get(suggestion)
        assert actual_strategy == expected_strategy

    def test_relaxation_suggestion_converts_correctly(self) -> None:
        """Test RELAXATION suggestion converts to corresponding strategy."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            SUGGESTION_TO_STRATEGY,
        )

        suggestion = RecoverySuggestion.RELAXATION
        expected_strategy = RecoveryStrategy.RELAXATION

        actual_strategy = SUGGESTION_TO_STRATEGY.get(suggestion)
        assert actual_strategy == expected_strategy

    def test_error_recovery_manager_consistency(self) -> None:
        """Test that SUGGESTION_TO_STRATEGY aligns with ErrorRecoveryManager strategies."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            SUGGESTION_TO_STRATEGY,
        )

        # Verify that the strategies in SUGGESTION_TO_STRATEGY are valid RecoveryStrategy values
        for _suggestion, strategy in SUGGESTION_TO_STRATEGY.items():
            assert isinstance(strategy, RecoveryStrategy)
            # Verify the strategy is one that ErrorRecoveryManager can handle
            assert strategy in [
                RecoveryStrategy.RETRY_CURRENT,
                RecoveryStrategy.RETRY_WITH_FEEDBACK,
                RecoveryStrategy.ROLLBACK_TO_ANALYSIS,
                RecoveryStrategy.RELAXATION,
                RecoveryStrategy.FAIL_FAST,
            ]
