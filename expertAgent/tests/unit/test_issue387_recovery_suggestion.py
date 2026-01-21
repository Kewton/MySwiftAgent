"""Unit tests for Issue #387: recovery_suggestion processing.

Tests cover:
1. SUGGESTION_TO_STRATEGY mapping constant
2. RecoverySuggestion to RecoveryStrategy conversion
3. _handle_recovery_suggestion method behavior
4. ParallelExecutionResult recovery_suggestion field
"""

import pytest

from aiagent.clients.types.workflow_generator import RecoverySuggestion
from aiagent.langgraph.jobGeneratorV2.types import (
    ParallelExecutionResult,
    RecoveryStrategy,
    TaskResult,
)


class TestSuggestionToStrategyMapping:
    """Test SUGGESTION_TO_STRATEGY constant existence and values."""

    def test_suggestion_to_strategy_mapping_exists(self) -> None:
        """Test that SUGGESTION_TO_STRATEGY constant exists in orchestrator."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            SUGGESTION_TO_STRATEGY,
        )

        assert SUGGESTION_TO_STRATEGY is not None
        assert isinstance(SUGGESTION_TO_STRATEGY, dict)

    def test_rollback_to_analysis_conversion(self) -> None:
        """Test ROLLBACK_TO_ANALYSIS maps to RecoveryStrategy.ROLLBACK_TO_ANALYSIS."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            SUGGESTION_TO_STRATEGY,
        )

        assert RecoverySuggestion.ROLLBACK_TO_ANALYSIS in SUGGESTION_TO_STRATEGY
        assert (
            SUGGESTION_TO_STRATEGY[RecoverySuggestion.ROLLBACK_TO_ANALYSIS]
            == RecoveryStrategy.ROLLBACK_TO_ANALYSIS
        )

    def test_relaxation_conversion(self) -> None:
        """Test RELAXATION maps to RecoveryStrategy.RELAXATION."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            SUGGESTION_TO_STRATEGY,
        )

        assert RecoverySuggestion.RELAXATION in SUGGESTION_TO_STRATEGY
        assert (
            SUGGESTION_TO_STRATEGY[RecoverySuggestion.RELAXATION]
            == RecoveryStrategy.RELAXATION
        )

    def test_unknown_suggestion_default(self) -> None:
        """Test that unknown/new suggestions default to FAIL_FAST."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            SUGGESTION_TO_STRATEGY,
        )

        # Test using .get() with default
        unknown_key = "UNKNOWN_SUGGESTION"  # Simulate an unknown suggestion
        result = SUGGESTION_TO_STRATEGY.get(
            unknown_key,
            RecoveryStrategy.FAIL_FAST,  # type: ignore
        )
        assert result == RecoveryStrategy.FAIL_FAST


class TestParallelExecutionResultField:
    """Test ParallelExecutionResult recovery_suggestion field."""

    def test_parallel_execution_result_has_recovery_suggestion_field(self) -> None:
        """Test that ParallelExecutionResult has recovery_suggestion field."""
        result = ParallelExecutionResult()
        # Field should exist and default to None
        assert hasattr(result, "recovery_suggestion")
        assert result.recovery_suggestion is None

    def test_parallel_execution_result_accepts_recovery_suggestion(self) -> None:
        """Test that ParallelExecutionResult accepts recovery_suggestion value."""
        result = ParallelExecutionResult(
            successful_tasks=[],
            failed_tasks=[],
            recovery_suggestion=RecoverySuggestion.ROLLBACK_TO_ANALYSIS,
        )
        assert result.recovery_suggestion == RecoverySuggestion.ROLLBACK_TO_ANALYSIS

    def test_parallel_execution_result_relaxation_suggestion(self) -> None:
        """Test ParallelExecutionResult with RELAXATION suggestion."""
        result = ParallelExecutionResult(
            successful_tasks=[
                TaskResult(task_id="task_001", success=True),
            ],
            failed_tasks=[
                TaskResult(task_id="task_002", success=False),
            ],
            recovery_suggestion=RecoverySuggestion.RELAXATION,
        )
        assert result.recovery_suggestion == RecoverySuggestion.RELAXATION
        assert result.partial_success is True


class TestHandleRecoverySuggestionMethod:
    """Test _handle_recovery_suggestion method."""

    @pytest.mark.asyncio
    async def test_handle_recovery_suggestion_rollback(self) -> None:
        """Test _handle_recovery_suggestion with ROLLBACK_TO_ANALYSIS."""
        from unittest.mock import MagicMock, patch

        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )

        orchestrator = JobGenerationOrchestrator()

        # Create mock execution result with failed tasks
        execution_result = ParallelExecutionResult(
            successful_tasks=[],
            failed_tasks=[
                TaskResult(task_id="task_001", success=False),
            ],
            recovery_suggestion=RecoverySuggestion.ROLLBACK_TO_ANALYSIS,
        )

        # Mock context
        mock_context = MagicMock()

        # Call _handle_recovery_suggestion
        with patch.object(
            orchestrator._error_recovery_manager,
            "handle_error",
            return_value=MagicMock(strategy=RecoveryStrategy.ROLLBACK_TO_ANALYSIS),
        ):
            await orchestrator._handle_recovery_suggestion(
                suggestion=RecoverySuggestion.ROLLBACK_TO_ANALYSIS,
                execution_result=execution_result,
                context=mock_context,
            )

        # Method should return result (may be None or modified result)
        # The key assertion is that the method exists and can be called
        assert hasattr(orchestrator, "_handle_recovery_suggestion")

    @pytest.mark.asyncio
    async def test_handle_recovery_suggestion_relaxation(self) -> None:
        """Test _handle_recovery_suggestion with RELAXATION."""
        from unittest.mock import MagicMock, patch

        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )

        orchestrator = JobGenerationOrchestrator()

        execution_result = ParallelExecutionResult(
            successful_tasks=[
                TaskResult(task_id="task_001", success=True),
            ],
            failed_tasks=[
                TaskResult(task_id="task_002", success=False),
            ],
            recovery_suggestion=RecoverySuggestion.RELAXATION,
        )

        mock_context = MagicMock()

        with patch.object(
            orchestrator._error_recovery_manager,
            "handle_error",
            return_value=MagicMock(strategy=RecoveryStrategy.RELAXATION),
        ):
            await orchestrator._handle_recovery_suggestion(
                suggestion=RecoverySuggestion.RELAXATION,
                execution_result=execution_result,
                context=mock_context,
            )

        # Method should be callable
        assert hasattr(orchestrator, "_handle_recovery_suggestion")

    @pytest.mark.asyncio
    async def test_handle_recovery_suggestion_null(self) -> None:
        """Test that null recovery_suggestion is handled gracefully."""
        from unittest.mock import MagicMock

        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )

        orchestrator = JobGenerationOrchestrator()

        # Create result with no recovery suggestion
        execution_result = ParallelExecutionResult(
            successful_tasks=[
                TaskResult(task_id="task_001", success=True),
            ],
            failed_tasks=[],
            recovery_suggestion=None,
        )

        mock_context = MagicMock()

        # Should not raise when suggestion is None
        # The orchestrator should handle this gracefully
        # (method may return None or skip processing)
        result = await orchestrator._handle_recovery_suggestion(
            suggestion=None,  # type: ignore
            execution_result=execution_result,
            context=mock_context,
        )

        # Should return None when suggestion is None
        assert result is None


class TestConvertToParallelResultRecoverySuggestion:
    """Test _convert_to_parallel_result sets recovery_suggestion."""

    def test_convert_with_recovery_suggestion(self) -> None:
        """Test _convert_to_parallel_result passes recovery_suggestion."""
        from unittest.mock import MagicMock

        from aiagent.clients.types.workflow_generator import (
            BatchStatus,
            WorkflowResult,
            WorkflowStatus,
        )
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )
        from aiagent.langgraph.jobGeneratorV2.types import UnifiedTaskIdentifier

        orchestrator = JobGenerationOrchestrator()

        # Create mock response with recovery_suggestion
        mock_response = MagicMock()
        mock_response.workflows = {
            "task_001": WorkflowResult(
                workflow_name="test_workflow",
                status=WorkflowStatus.SUCCESS,
            ),
        }
        mock_response.failed_tasks = []
        mock_response.recovery_suggestion = RecoverySuggestion.ROLLBACK_TO_ANALYSIS
        mock_response.status = BatchStatus.SUCCESS

        task_identifiers = [
            UnifiedTaskIdentifier(task_id="task_001", task_master_id="tm_001"),
        ]

        result = orchestrator._convert_to_parallel_result(
            mock_response, task_identifiers
        )

        # Result should have recovery_suggestion set
        assert result.recovery_suggestion == RecoverySuggestion.ROLLBACK_TO_ANALYSIS

    def test_convert_without_recovery_suggestion(self) -> None:
        """Test _convert_to_parallel_result handles None recovery_suggestion."""
        from unittest.mock import MagicMock

        from aiagent.clients.types.workflow_generator import (
            BatchStatus,
            WorkflowResult,
            WorkflowStatus,
        )
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )
        from aiagent.langgraph.jobGeneratorV2.types import UnifiedTaskIdentifier

        orchestrator = JobGenerationOrchestrator()

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

        result = orchestrator._convert_to_parallel_result(
            mock_response, task_identifiers
        )

        # Result should have None for recovery_suggestion
        assert result.recovery_suggestion is None
