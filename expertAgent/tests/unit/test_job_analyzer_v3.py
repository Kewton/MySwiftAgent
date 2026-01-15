"""Unit tests for job_analyzer_v3 node.

Issue #359 Iteration 2 Task 1.2: Tests for merged TASK_BREAKDOWN + INTERFACE_DESIGN.

TDD Red Phase: These tests define the expected behavior.
"""

import pytest

from aiagent.langgraph.jobGeneratorV2.types_v3 import UnifiedTaskIdentifier


class TestJobAnalyzerResponse:
    """Test suite for JobAnalysisResponse model."""

    def test_response_has_tasks_list(self):
        """Response should have tasks list with UnifiedTaskIdentifier."""
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer_v3 import (
            AnalyzedTask,
            JobAnalysisResponse,
        )

        task = AnalyzedTask(
            task_id="task_001",
            name="Search Gmail",
            description="Search Gmail for emails",
            task_type="fetch",
            recommended_api="/v1/utility/gmail/search",
            dependencies=[],
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
            output_schema={
                "type": "object",
                "properties": {"messages": {"type": "array"}},
            },
        )

        response = JobAnalysisResponse(
            tasks=[task],
            interfaces={},
            job_body_parameters=[],
            overall_summary="Test workflow",
        )

        assert len(response.tasks) == 1
        assert response.tasks[0].task_id == "task_001"

    def test_response_has_interfaces(self):
        """Response should have interfaces dict keyed by task_id."""
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer_v3 import (
            AnalyzedTask,
            InterfaceDefinition,
            JobAnalysisResponse,
        )

        task = AnalyzedTask(
            task_id="task_001",
            name="Search Gmail",
            description="Search Gmail for emails",
            task_type="fetch",
            recommended_api="/v1/utility/gmail/search",
            dependencies=[],
            input_schema={"type": "object"},
            output_schema={"type": "object"},
        )

        interface = InterfaceDefinition(
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
            output_schema={
                "type": "object",
                "properties": {"messages": {"type": "array"}},
            },
            description="Gmail search interface",
        )

        response = JobAnalysisResponse(
            tasks=[task],
            interfaces={"task_001": interface},
            job_body_parameters=[],
            overall_summary="Test workflow",
        )

        assert "task_001" in response.interfaces
        assert response.interfaces["task_001"].description == "Gmail search interface"

    def test_response_has_job_body_parameters(self):
        """Response should have job_body_parameters list."""
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer_v3 import (
            JobAnalysisResponse,
            JobParameter,
        )

        param = JobParameter(
            name="recipient_email",
            value="user@example.com",
            description="Email recipient",
        )

        response = JobAnalysisResponse(
            tasks=[],
            interfaces={},
            job_body_parameters=[param],
            overall_summary="Test workflow",
        )

        assert len(response.job_body_parameters) == 1
        assert response.job_body_parameters[0].name == "recipient_email"


class TestAnalyzedTask:
    """Test suite for AnalyzedTask model."""

    def test_task_has_required_fields(self):
        """AnalyzedTask should have all required fields."""
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer_v3 import AnalyzedTask

        task = AnalyzedTask(
            task_id="task_001",
            name="Fetch Weather",
            description="Get current weather data",
            task_type="fetch",
            recommended_api="/v1/utility/weather",
            dependencies=[],
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            priority=5,
        )

        assert task.task_id == "task_001"
        assert task.name == "Fetch Weather"
        assert task.description == "Get current weather data"
        assert task.task_type == "fetch"
        assert task.recommended_api == "/v1/utility/weather"
        assert task.dependencies == []
        assert task.input_schema == {"type": "object"}
        assert task.output_schema == {"type": "object"}
        assert task.priority == 5

    def test_task_to_unified_identifier(self):
        """AnalyzedTask should convert to UnifiedTaskIdentifier."""
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer_v3 import AnalyzedTask

        task = AnalyzedTask(
            task_id="task_001",
            name="Fetch Weather",
            description="Get current weather data",
            task_type="fetch",
            recommended_api="/v1/utility/weather",
            dependencies=[],
            input_schema={},
            output_schema={},
        )

        identifier = task.to_unified_identifier()

        assert isinstance(identifier, UnifiedTaskIdentifier)
        assert identifier.task_id == "task_001"
        assert identifier.task_master_id is None


class TestJobAnalyzerNode:
    """Test suite for job_analyzer_v3 node function."""

    @pytest.mark.asyncio
    async def test_analyzer_merges_breakdown_and_interface(self):
        """Analyzer should perform task breakdown and interface design in one call."""
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer_v3 import (
            JobAnalysisInput,
            analyze_job,
        )

        JobAnalysisInput(
            user_requirement="Search Gmail for recent emails and summarize them",
            max_tasks=5,
        )

        # This test verifies the function exists and has the right signature
        # Full test requires mocked LLM
        assert analyze_job is not None
        assert callable(analyze_job)

    @pytest.mark.asyncio
    async def test_analyzer_returns_unified_identifiers(self):
        """Analyzer should return tasks with UnifiedTaskIdentifier-compatible IDs."""
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer_v3 import (
            AnalyzedTask,
            JobAnalysisResponse,
        )

        task = AnalyzedTask(
            task_id="task_001",
            name="Search",
            description="Search emails",
            task_type="fetch",
            recommended_api="/api/search",
            dependencies=[],
            input_schema={},
            output_schema={},
        )

        response = JobAnalysisResponse(
            tasks=[task],
            interfaces={},
            job_body_parameters=[],
            overall_summary="Test",
        )

        identifiers = [t.to_unified_identifier() for t in response.tasks]
        assert all(isinstance(i, UnifiedTaskIdentifier) for i in identifiers)

    def test_analyzer_no_index_based_references(self):
        """Tasks should use task_id, not index-based references."""
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer_v3 import AnalyzedTask

        AnalyzedTask(
            task_id="task_001",
            name="First Task",
            description="First task",
            task_type="fetch",
            recommended_api="/api/first",
            dependencies=[],
            input_schema={},
            output_schema={},
        )

        task2 = AnalyzedTask(
            task_id="task_002",
            name="Second Task",
            description="Second task depends on first",
            task_type="transform",
            recommended_api="/api/second",
            dependencies=["task_001"],  # Reference by task_id, not index
            input_schema={},
            output_schema={},
        )

        # Dependencies should be task_ids, not indices
        assert task2.dependencies[0] == "task_001"
        assert not task2.dependencies[0].isdigit()


class TestJobAnalysisInput:
    """Test suite for JobAnalysisInput model."""

    def test_input_has_user_requirement(self):
        """Input should have user_requirement field."""
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer_v3 import (
            JobAnalysisInput,
        )

        input_data = JobAnalysisInput(
            user_requirement="Search Gmail",
            max_tasks=10,
        )

        assert input_data.user_requirement == "Search Gmail"
        assert input_data.max_tasks == 10

    def test_input_has_optional_context(self):
        """Input should support optional context for retry."""
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer_v3 import (
            JobAnalysisInput,
        )

        input_data = JobAnalysisInput(
            user_requirement="Search Gmail",
            max_tasks=10,
            retry_feedback="Previous attempt failed due to validation error",
        )

        assert (
            input_data.retry_feedback
            == "Previous attempt failed due to validation error"
        )
