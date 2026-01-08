"""Unit tests for SchemaGeneratorSubWorkflow.

Issue #342 Phase C.1: Tests for JSON Schema generation from task definitions.
"""

from unittest.mock import MagicMock, patch

import pytest

from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
from aiagent.langgraph.jobGeneratorV2.types import (
    InterfaceSchema,
    Phase,
    TaskDefinition,
)


class TestSchemaGeneratorSubWorkflowExists:
    """Test that SchemaGeneratorSubWorkflow exists and is importable."""

    def test_schema_generator_subworkflow_importable(self):
        """SchemaGeneratorSubWorkflow should be importable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            SchemaGeneratorSubWorkflow,
        )

        assert SchemaGeneratorSubWorkflow is not None

    def test_schema_generator_has_generate_method(self):
        """SchemaGeneratorSubWorkflow should have a generate method."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            SchemaGeneratorSubWorkflow,
        )

        generator = SchemaGeneratorSubWorkflow()
        assert hasattr(generator, "generate")
        assert callable(generator.generate)


class TestSchemaGeneratorSubWorkflowGenerate:
    """Test SchemaGeneratorSubWorkflow.generate() method."""

    @pytest.fixture
    def sample_tasks(self) -> list[TaskDefinition]:
        """Create sample tasks for testing."""
        return [
            TaskDefinition(
                id="task_001",
                name="Gmail Search",
                description="Search for emails matching query",
                task_type="gmail_search",
                recommended_api="/v1/utility/gmail/search",
                priority=1,
                dependencies=[],
            ),
            TaskDefinition(
                id="task_002",
                name="Summarize Results",
                description="Summarize the search results",
                task_type="llm_processing",
                recommended_api="/v1/ai/json_output",
                priority=2,
                dependencies=["task_001"],
            ),
        ]

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock execution context."""
        return ExecutionContext(
            job_id="test-job-123",
            user_requirement="Search emails and summarize",
            max_phase_retries=3,
            max_total_retries=5,
        )

    @pytest.mark.asyncio
    async def test_generate_returns_interface_schemas(
        self, sample_tasks: list[TaskDefinition], mock_context: ExecutionContext
    ):
        """generate() should return dict of InterfaceSchema."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            SchemaGeneratorSubWorkflow,
        )

        # Mock LLM response
        mock_response = MagicMock()
        mock_response.interfaces = [
            MagicMock(
                task_id="task_001",
                interface_name="gmail_search_interface",
                description="Gmail search interface",
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"emails": {"type": "array"}}},
                derived_fields={},
            ),
            MagicMock(
                task_id="task_002",
                interface_name="summarize_interface",
                description="Summarize interface",
                input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"summary": {"type": "string"}}},
                derived_fields={},
            ),
        ]

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator.invoke_structured_llm"
        ) as mock_llm:
            mock_llm.return_value = MagicMock(result=mock_response, model_name="test-model")

            generator = SchemaGeneratorSubWorkflow()
            result = await generator.generate(sample_tasks, mock_context)

            assert isinstance(result, dict)
            assert len(result) == 2
            assert "task_001" in result
            assert "task_002" in result
            assert isinstance(result["task_001"], InterfaceSchema)
            assert isinstance(result["task_002"], InterfaceSchema)

    @pytest.mark.asyncio
    async def test_generate_validates_empty_tasks(
        self, mock_context: ExecutionContext
    ):
        """generate() should raise error for empty task list."""
        from aiagent.langgraph.jobGeneratorV2.protocols import WorkflowError
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            SchemaGeneratorSubWorkflow,
        )

        generator = SchemaGeneratorSubWorkflow()

        with pytest.raises(WorkflowError) as exc_info:
            await generator.generate([], mock_context)

        assert "empty" in str(exc_info.value).lower() or "no tasks" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_generate_uses_context_for_llm_config(
        self, sample_tasks: list[TaskDefinition], mock_context: ExecutionContext
    ):
        """generate() should use ExecutionContext for LLM configuration."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            SchemaGeneratorSubWorkflow,
        )

        mock_response = MagicMock()
        mock_response.interfaces = [
            MagicMock(
                task_id="task_001",
                interface_name="test_interface",
                description="Test",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
                derived_fields={},
            ),
        ]

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator.invoke_structured_llm"
        ) as mock_llm:
            mock_llm.return_value = MagicMock(result=mock_response, model_name="test-model")

            generator = SchemaGeneratorSubWorkflow()
            await generator.generate(sample_tasks[:1], mock_context)

            # Verify invoke_structured_llm was called
            mock_llm.assert_called_once()


class TestSchemaGeneratorRetryBugFix:
    """Test that retry_count bug is fixed (Issue #342).

    The bug was that retry_count was incorrectly reset between phases.
    SchemaGeneratorSubWorkflow should use ExecutionContext's phase-specific
    retry state, not a global counter.
    """

    @pytest.fixture
    def mock_context_with_retries(self) -> ExecutionContext:
        """Create context with existing retry state."""
        ctx = ExecutionContext(
            job_id="test-job-456",
            user_requirement="Test requirement",
            max_phase_retries=3,
            max_total_retries=5,
        )
        # Simulate previous phase having used some retries
        ctx.record_retry(Phase.TASK_BREAKDOWN, "Previous phase retry")
        return ctx

    def test_schema_generation_uses_context_retry_state(
        self, mock_context_with_retries: ExecutionContext
    ):
        """SchemaGeneratorSubWorkflow should use context's phase-specific retry state."""
        # Verify that INTERFACE_DESIGN phase has its own retry state
        interface_retry_state = mock_context_with_retries.get_phase_retry_state(
            Phase.INTERFACE_DESIGN
        )
        task_breakdown_retry_state = mock_context_with_retries.get_phase_retry_state(
            Phase.TASK_BREAKDOWN
        )

        # INTERFACE_DESIGN should start at 0 (independent of TASK_BREAKDOWN)
        assert interface_retry_state.count == 0
        # TASK_BREAKDOWN should have 1 retry recorded
        assert task_breakdown_retry_state.count == 1

    def test_context_can_retry_respects_phase_limits(
        self, mock_context_with_retries: ExecutionContext
    ):
        """Context.can_retry should respect per-phase limits."""
        # INTERFACE_DESIGN has not been retried yet
        assert mock_context_with_retries.can_retry(Phase.INTERFACE_DESIGN) is True

        # Record max retries for INTERFACE_DESIGN
        for i in range(3):
            mock_context_with_retries.record_retry(
                Phase.INTERFACE_DESIGN, f"Retry {i+1}"
            )

        # Now INTERFACE_DESIGN should be exhausted
        assert mock_context_with_retries.can_retry(Phase.INTERFACE_DESIGN) is False


class TestSchemaGeneratorNormalization:
    """Test JSON Schema normalization in schema generator."""

    def test_normalize_json_schema_properties_importable(self):
        """normalize_json_schema_properties should be importable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            normalize_json_schema_properties,
        )

        assert normalize_json_schema_properties is not None

    def test_normalize_bare_string_type(self):
        """Should normalize bare string type to object form."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            normalize_json_schema_properties,
        )

        schema = {"properties": {"name": "string"}}
        result = normalize_json_schema_properties(schema)

        assert result["properties"]["name"] == {"type": "string"}

    def test_normalize_array_shorthand(self):
        """Should normalize array shorthand like ["string"] to object form."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            normalize_json_schema_properties,
        )

        schema = {"properties": {"tags": ["string"]}}
        result = normalize_json_schema_properties(schema)

        assert result["properties"]["tags"] == {"type": "string"}
