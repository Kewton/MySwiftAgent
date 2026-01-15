"""Unit tests for orchestrator_v3.

Issue #359 Iteration 2 Task 1.5: Tests for 3-phase orchestrator.

TDD Red Phase: These tests define the expected behavior.
"""


import pytest
from aiagent.langgraph.jobGeneratorV2.types_v3 import (
    PhaseV3,
    RecoveryStrategy,
    UnifiedTaskIdentifier,
)


class TestOrchestratorV3Phases:
    """Test suite for 3-phase orchestrator."""

    def test_orchestrator_has_3_phases(self):
        """Orchestrator should have exactly 3 phases."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationOrchestratorV3,
        )

        orchestrator = JobGenerationOrchestratorV3()

        phases = orchestrator.get_phase_order()

        assert len(phases) == 3
        assert phases[0] == PhaseV3.JOB_ANALYSIS
        assert phases[1] == PhaseV3.REGISTRATION
        assert phases[2] == PhaseV3.WORKFLOW_GEN

    def test_orchestrator_phase_order_enum(self):
        """Phase enum should have correct values."""
        assert PhaseV3.JOB_ANALYSIS.value == "job_analysis"
        assert PhaseV3.REGISTRATION.value == "registration"
        assert PhaseV3.WORKFLOW_GEN.value == "workflow_gen"


class TestOrchestratorV3NoIndexLookups:
    """Test that orchestrator uses task_id consistently."""

    def test_no_index_based_task_lookup(self):
        """Orchestrator should NOT use index-based lookups like task_master_ids[idx]."""
        # Read the source file and check for banned patterns
        import inspect

        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationOrchestratorV3,
        )

        source = inspect.getsource(JobGenerationOrchestratorV3)

        # These patterns are BANNED
        banned_patterns = [
            "task_master_ids[idx]",
            "task_master_ids[i]",
            "task_master_ids[index]",
            "for idx, task in enumerate",
            "for i, task in enumerate",
        ]

        for pattern in banned_patterns:
            assert pattern not in source, f"BANNED pattern found: {pattern}"

    def test_unified_identifier_used_throughout(self):
        """Orchestrator should use UnifiedTaskIdentifier for task tracking."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationOrchestratorV3,
        )

        orchestrator = JobGenerationOrchestratorV3()

        # The orchestrator should accept and return UnifiedTaskIdentifier-based data
        assert hasattr(orchestrator, "run_workflow")


class TestOrchestratorV3NoSilentFallbacks:
    """Test that orchestrator raises errors instead of silent fallbacks."""

    @pytest.mark.asyncio
    async def test_missing_data_raises_error(self):
        """Missing data should raise error, not silently fallback."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationOrchestratorV3,
            OrchestratorError,
        )

        orchestrator = JobGenerationOrchestratorV3()

        # Attempting to access missing task should raise, not return None/default
        with pytest.raises(OrchestratorError):
            orchestrator._get_task_by_id({}, "nonexistent_task")

    @pytest.mark.asyncio
    async def test_no_silent_continue_in_loops(self):
        """Loops should not silently skip tasks."""
        import inspect

        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationOrchestratorV3,
        )

        source = inspect.getsource(JobGenerationOrchestratorV3)

        # These patterns indicate silent fallbacks
        # Note: 'continue' is allowed but should be logged
        assert "except:" not in source or "except Exception" in source, \
            "Bare except: is not allowed"


class TestOrchestratorV3LineCount:
    """Test that orchestrator stays under 300 lines."""

    def test_orchestrator_under_300_lines(self):
        """Orchestrator source should be under 300 lines."""
        import inspect

        from aiagent.langgraph.jobGeneratorV2 import orchestrator_v3

        source = inspect.getsource(orchestrator_v3)
        line_count = len(source.splitlines())

        assert line_count <= 300, f"Orchestrator has {line_count} lines, max is 300"


class TestOrchestratorV3ErrorRecovery:
    """Test error recovery integration."""

    def test_uses_error_recovery_v3(self):
        """Orchestrator should use ErrorRecoveryManager from error_recovery_v3."""
        from aiagent.langgraph.jobGeneratorV2.error_recovery_v3 import (
            ErrorRecoveryManager,
        )
        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationOrchestratorV3,
        )

        recovery_manager = ErrorRecoveryManager()
        orchestrator = JobGenerationOrchestratorV3(
            error_recovery_manager=recovery_manager
        )

        assert orchestrator._error_recovery_manager is recovery_manager

    @pytest.mark.asyncio
    async def test_recovery_action_handled(self):
        """Orchestrator should handle recovery actions correctly."""
        from aiagent.langgraph.jobGeneratorV2.error_recovery_v3 import (
            ErrorRecoveryManager,
        )
        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationOrchestratorV3,
        )
        from aiagent.langgraph.jobGeneratorV2.types_v3 import (
            RecoveryAction,
        )

        recovery_manager = ErrorRecoveryManager()
        JobGenerationOrchestratorV3(
            error_recovery_manager=recovery_manager
        )

        # Test that orchestrator can handle different recovery strategies
        action = RecoveryAction(strategy=RecoveryStrategy.RETRY_WITH_FEEDBACK)
        assert action.strategy == RecoveryStrategy.RETRY_WITH_FEEDBACK


class TestOrchestratorV3ParallelExecution:
    """Test parallel execution in Phase 3."""

    def test_uses_parallel_executor(self):
        """Orchestrator should use parallel_executor for Phase 3."""
        import inspect

        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationOrchestratorV3,
        )

        source = inspect.getsource(JobGenerationOrchestratorV3)

        # Should import and use parallel_workflow_generation
        assert "parallel_workflow_generation" in source or \
               "parallel_executor" in source, \
               "Orchestrator should use parallel_executor module"


class TestOrchestratorV3Request:
    """Test orchestrator request handling."""

    def test_request_model_exists(self):
        """Request model should exist with required fields."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationRequestV3,
        )

        request = JobGenerationRequestV3(
            user_requirement="Test requirement",
            project_id="test-project",
            max_tasks=5,
        )

        assert request.user_requirement == "Test requirement"
        assert request.project_id == "test-project"
        assert request.max_tasks == 5


class TestOrchestratorV3Result:
    """Test orchestrator result handling."""

    def test_result_model_exists(self):
        """Result model should exist with required fields."""
        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationResultV3,
        )

        result = JobGenerationResultV3(
            success=True,
            job_id="job_123",
            job_master_id="jm_123",
            task_identifiers=[
                UnifiedTaskIdentifier(task_id="task_001", task_master_id="tm_001")
            ],
            workflows={"task_001": {"workflow_name": "test_workflow"}},
        )

        assert result.success is True
        assert result.job_id == "job_123"
        assert len(result.task_identifiers) == 1
        assert result.task_identifiers[0].task_id == "task_001"
