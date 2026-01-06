"""Unit tests for Job Generator V2 context module.

Tests for ExecutionContext and related context classes.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock


class TestExecutionContext:
    """Test cases for ExecutionContext."""

    def test_execution_context_exists(self):
        """ExecutionContext should be importable."""
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext

        assert ExecutionContext is not None

    def test_execution_context_creation(self):
        """ExecutionContext should be creatable."""
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext

        context = ExecutionContext(
            job_id="test-job-123",
            user_requirement="Fetch emails and summarize",
            max_total_retries=5,
        )
        assert context.job_id == "test-job-123"
        assert context.user_requirement == "Fetch emails and summarize"

    def test_execution_context_has_phase_retry_states(self):
        """ExecutionContext should manage per-phase retry states."""
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        context = ExecutionContext(
            job_id="test-job-123",
            user_requirement="Test requirement",
        )

        # Should have retry state for each phase
        assert context.get_phase_retry_state(Phase.TASK_BREAKDOWN) is not None
        assert context.get_phase_retry_state(Phase.INTERFACE_DESIGN) is not None
        assert context.get_phase_retry_state(Phase.REGISTRATION) is not None
        assert context.get_phase_retry_state(Phase.WORKFLOW_GEN) is not None

    def test_can_retry_checks_phase_state(self):
        """can_retry should check the specific phase's retry state."""
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        context = ExecutionContext(
            job_id="test-job-123",
            user_requirement="Test requirement",
        )

        # Initially should be able to retry
        assert context.can_retry(Phase.TASK_BREAKDOWN) is True

        # After max retries, should not be able to retry
        for _ in range(3):
            context.record_retry(Phase.TASK_BREAKDOWN, "Test reason")

        assert context.can_retry(Phase.TASK_BREAKDOWN) is False

    def test_total_retry_limit(self):
        """Should respect total retry limit across all phases."""
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        context = ExecutionContext(
            job_id="test-job-123",
            user_requirement="Test requirement",
            max_total_retries=5,
        )

        # Record retries across different phases
        context.record_retry(Phase.TASK_BREAKDOWN, "Retry 1")
        context.record_retry(Phase.TASK_BREAKDOWN, "Retry 2")
        context.record_retry(Phase.INTERFACE_DESIGN, "Retry 3")
        context.record_retry(Phase.INTERFACE_DESIGN, "Retry 4")
        context.record_retry(Phase.REGISTRATION, "Retry 5")

        # Total limit reached
        assert context.total_retry_count() == 5
        assert context.can_retry_any() is False

    def test_get_rollback_count(self):
        """Should track rollback count."""
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        context = ExecutionContext(
            job_id="test-job-123",
            user_requirement="Test requirement",
        )

        assert context.get_rollback_count() == 0

        context.record_rollback(Phase.INTERFACE_DESIGN, Phase.TASK_BREAKDOWN)
        assert context.get_rollback_count() == 1

        context.record_rollback(Phase.REGISTRATION, Phase.INTERFACE_DESIGN)
        assert context.get_rollback_count() == 2


class TestLLMContext:
    """Test cases for LLMContext."""

    def test_llm_context_exists(self):
        """LLMContext should be importable."""
        from aiagent.langgraph.jobGeneratorV2.context import LLMContext

        assert LLMContext is not None

    def test_llm_context_creation(self):
        """LLMContext should be creatable with model configuration."""
        from aiagent.langgraph.jobGeneratorV2.context import LLMContext

        context = LLMContext(
            model_name="claude-haiku-4-5",
            temperature=0.7,
            max_tokens=4096,
        )
        assert context.model_name == "claude-haiku-4-5"
        assert context.temperature == 0.7


class TestStorageContext:
    """Test cases for StorageContext."""

    def test_storage_context_exists(self):
        """StorageContext should be importable."""
        from aiagent.langgraph.jobGeneratorV2.context import StorageContext

        assert StorageContext is not None

    def test_storage_context_has_jobqueue_client(self):
        """StorageContext should have jobqueue_client."""
        from aiagent.langgraph.jobGeneratorV2.context import StorageContext

        mock_client = MagicMock()
        context = StorageContext(jobqueue_client=mock_client)
        assert context.jobqueue_client == mock_client


class TestIntegrationContext:
    """Test cases for IntegrationContext."""

    def test_integration_context_exists(self):
        """IntegrationContext should be importable."""
        from aiagent.langgraph.jobGeneratorV2.context import IntegrationContext

        assert IntegrationContext is not None

    def test_integration_context_has_graphai_client(self):
        """IntegrationContext should have graphai_client."""
        from aiagent.langgraph.jobGeneratorV2.context import IntegrationContext

        mock_client = MagicMock()
        context = IntegrationContext(graphai_client=mock_client)
        assert context.graphai_client == mock_client


class TestObservabilityContext:
    """Test cases for ObservabilityContext."""

    def test_observability_context_exists(self):
        """ObservabilityContext should be importable."""
        from aiagent.langgraph.jobGeneratorV2.context import ObservabilityContext

        assert ObservabilityContext is not None

    def test_observability_context_has_tracer(self):
        """ObservabilityContext should have tracer."""
        from aiagent.langgraph.jobGeneratorV2.context import ObservabilityContext

        mock_tracer = MagicMock()
        context = ObservabilityContext(tracer=mock_tracer)
        assert context.tracer == mock_tracer


class TestContextBuilder:
    """Test cases for ContextBuilder."""

    def test_context_builder_exists(self):
        """ContextBuilder should be importable."""
        from aiagent.langgraph.jobGeneratorV2.context import ContextBuilder

        assert ContextBuilder is not None

    def test_context_builder_creates_execution_context(self):
        """ContextBuilder should create ExecutionContext."""
        from aiagent.langgraph.jobGeneratorV2.context import ContextBuilder

        builder = ContextBuilder()
        context = (
            builder.with_job_id("test-job-123")
            .with_user_requirement("Test requirement")
            .build()
        )

        assert context.job_id == "test-job-123"
        assert context.user_requirement == "Test requirement"

    def test_context_builder_with_llm_context(self):
        """ContextBuilder should allow setting LLM context."""
        from aiagent.langgraph.jobGeneratorV2.context import ContextBuilder, LLMContext

        builder = ContextBuilder()
        llm_context = LLMContext(
            model_name="claude-haiku-4-5",
            temperature=0.5,
        )
        context = (
            builder.with_job_id("test-job")
            .with_user_requirement("Test")
            .with_llm_context(llm_context)
            .build()
        )

        assert context.llm.model_name == "claude-haiku-4-5"


class TestContextCanRetryMethod:
    """Test cases specifically for can_retry behavior to prevent infinite loops."""

    def test_can_retry_returns_false_after_max_retries(self):
        """can_retry must return False after max retries to prevent infinite loop."""
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        context = ExecutionContext(
            job_id="test-job",
            user_requirement="Test",
            max_phase_retries=3,
        )

        phase = Phase.INTERFACE_DESIGN

        # Exhaust retries
        for i in range(3):
            assert context.can_retry(phase) is True
            context.record_retry(phase, f"Retry {i + 1}")

        # Must return False to prevent infinite loop
        assert context.can_retry(phase) is False

    def test_can_retry_interface_method_matches_protocol(self):
        """can_retry should work as expected by ErrorRecoveryManager."""
        from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
        from aiagent.langgraph.jobGeneratorV2.types import Phase

        context = ExecutionContext(
            job_id="test-job",
            user_requirement="Test",
        )

        # This is how ErrorRecoveryManager calls it (via context protocol)
        # The method should accept a phase parameter
        result = context.can_retry(Phase.TASK_BREAKDOWN)
        assert isinstance(result, bool)
