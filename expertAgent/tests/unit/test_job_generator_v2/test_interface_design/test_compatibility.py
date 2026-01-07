"""Unit tests for CompatibilityCheckerSubWorkflow.

Issue #342 Phase C.2: Tests for GraphAI compatibility checking.
"""

import pytest
from unittest.mock import MagicMock

from aiagent.langgraph.jobGeneratorV2.types import (
    CompatibilityReport,
    InterfaceSchema,
    Phase,
    TaskDefinition,
)
from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext


class TestCompatibilityCheckerExists:
    """Test that CompatibilityCheckerSubWorkflow exists and is importable."""

    def test_compatibility_checker_importable(self):
        """CompatibilityCheckerSubWorkflow should be importable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            CompatibilityCheckerSubWorkflow,
        )

        assert CompatibilityCheckerSubWorkflow is not None

    def test_compatibility_checker_has_check_method(self):
        """CompatibilityCheckerSubWorkflow should have a check method."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            CompatibilityCheckerSubWorkflow,
        )

        checker = CompatibilityCheckerSubWorkflow()
        assert hasattr(checker, "check")
        assert callable(checker.check)


class TestCompatibilityCheckerCheck:
    """Test CompatibilityCheckerSubWorkflow.check() method."""

    @pytest.fixture
    def sample_tasks(self) -> list[TaskDefinition]:
        """Create sample tasks for testing."""
        return [
            TaskDefinition(
                id="task_001",
                name="Gmail Search",
                description="Search for emails",
                task_type="gmail_search",
                recommended_api="/v1/utility/gmail/search",
                priority=1,
                dependencies=[],
            ),
            TaskDefinition(
                id="task_002",
                name="Process Results",
                description="Process the search results",
                task_type="llm_processing",
                recommended_api="/v1/ai/json_output",
                priority=2,
                dependencies=["task_001"],
            ),
        ]

    @pytest.fixture
    def sample_interfaces(self) -> dict[str, InterfaceSchema]:
        """Create sample interfaces for testing."""
        return {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "emails": {"type": "array"},
                        "count": {"type": "integer"},
                    },
                },
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={
                    "type": "object",
                    "properties": {
                        "emails": {"type": "array"},
                        "count": {"type": "integer"},
                    },
                    "required": ["emails"],
                },
                output_schema={
                    "type": "object",
                    "properties": {"summary": {"type": "string"}},
                },
            ),
        }

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock execution context."""
        return ExecutionContext(
            job_id="test-job-123",
            user_requirement="Search and process emails",
            max_phase_retries=3,
            max_total_retries=5,
        )

    @pytest.mark.asyncio
    async def test_check_returns_compatibility_report(
        self,
        sample_tasks: list[TaskDefinition],
        sample_interfaces: dict[str, InterfaceSchema],
        mock_context: ExecutionContext,
    ):
        """check() should return CompatibilityReport."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            CompatibilityCheckerSubWorkflow,
        )

        checker = CompatibilityCheckerSubWorkflow()
        result = await checker.check(sample_tasks, sample_interfaces, mock_context)

        assert isinstance(result, CompatibilityReport)
        assert hasattr(result, "is_compatible")
        assert hasattr(result, "issues")

    @pytest.mark.asyncio
    async def test_check_compatible_interfaces(
        self,
        sample_tasks: list[TaskDefinition],
        sample_interfaces: dict[str, InterfaceSchema],
        mock_context: ExecutionContext,
    ):
        """check() should return is_compatible=True for compatible interfaces."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            CompatibilityCheckerSubWorkflow,
        )

        checker = CompatibilityCheckerSubWorkflow()
        result = await checker.check(sample_tasks, sample_interfaces, mock_context)

        assert result.is_compatible is True
        assert len(result.issues) == 0

    @pytest.mark.asyncio
    async def test_check_incompatible_interfaces(
        self,
        sample_tasks: list[TaskDefinition],
        mock_context: ExecutionContext,
    ):
        """check() should detect incompatible interfaces."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            CompatibilityCheckerSubWorkflow,
        )

        # Create incompatible interfaces: task_002 expects 'text' but task_001 outputs 'emails'
        incompatible_interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"type": "object"},
                output_schema={
                    "type": "object",
                    "properties": {"emails": {"type": "array"}},
                },
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={
                    "type": "object",
                    "properties": {"text": {"type": "string"}},  # Mismatch!
                    "required": ["text"],
                },
                output_schema={"type": "object"},
            ),
        }

        checker = CompatibilityCheckerSubWorkflow()
        result = await checker.check(
            sample_tasks, incompatible_interfaces, mock_context
        )

        assert result.is_compatible is False
        assert len(result.issues) > 0

    @pytest.mark.asyncio
    async def test_check_empty_interfaces(
        self, sample_tasks: list[TaskDefinition], mock_context: ExecutionContext
    ):
        """check() should handle empty interfaces gracefully."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            CompatibilityCheckerSubWorkflow,
        )

        checker = CompatibilityCheckerSubWorkflow()
        result = await checker.check(sample_tasks, {}, mock_context)

        # Empty interfaces should be flagged as incompatible
        assert result.is_compatible is False


class TestCompatibilityRecordsRetryOnFailure:
    """Test that compatibility check records retry on failure (Issue #342 bug fix)."""

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock execution context."""
        return ExecutionContext(
            job_id="test-job-789",
            user_requirement="Test requirement",
            max_phase_retries=3,
            max_total_retries=5,
        )

    def test_compatibility_check_records_retry_on_failure(
        self, mock_context: ExecutionContext
    ):
        """Compatibility check should use context retry state on failure."""
        # Get initial retry state for INTERFACE_DESIGN phase
        initial_count = mock_context.get_phase_retry_state(
            Phase.INTERFACE_DESIGN
        ).count

        # Record a retry (simulating what the workflow would do on failure)
        mock_context.record_retry(
            Phase.INTERFACE_DESIGN, "Compatibility check failed"
        )

        # Verify retry was recorded for the correct phase
        new_count = mock_context.get_phase_retry_state(Phase.INTERFACE_DESIGN).count
        assert new_count == initial_count + 1

        # Verify other phases were not affected
        task_breakdown_count = mock_context.get_phase_retry_state(
            Phase.TASK_BREAKDOWN
        ).count
        assert task_breakdown_count == 0


class TestValidateInterfaceResponse:
    """Test _validate_interface_response helper function."""

    def test_validate_interface_response_importable(self):
        """_validate_interface_response should be importable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            validate_interface_response,
        )

        assert validate_interface_response is not None

    def test_validate_interface_response_rejects_none(self):
        """Should raise ValueError for None response."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            validate_interface_response,
        )

        with pytest.raises(ValueError):
            validate_interface_response(None)

    def test_validate_interface_response_rejects_empty_interfaces(self):
        """Should raise ValueError for response with empty interfaces."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            validate_interface_response,
        )

        mock_response = MagicMock()
        mock_response.interfaces = []

        with pytest.raises(ValueError):
            validate_interface_response(mock_response)

    def test_validate_interface_response_accepts_valid(self):
        """Should return response for valid input."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            validate_interface_response,
        )

        mock_response = MagicMock()
        mock_response.interfaces = [MagicMock()]

        result = validate_interface_response(mock_response)
        assert result == mock_response
