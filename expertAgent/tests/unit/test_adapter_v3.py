"""Unit tests for adapter_v3.

Issue #359 Iteration 2 Task 1.6: Tests for V3 adapter.

TDD Red Phase: These tests define the expected behavior.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aiagent.langgraph.jobGeneratorV2.types_v3 import UnifiedTaskIdentifier


class TestAdapterV3Creation:
    """Test adapter creation and configuration."""

    def test_adapter_creates_orchestrator_v3(self):
        """Adapter should create OrchestratorV3 internally."""
        from aiagent.langgraph.jobGeneratorV2.adapter_v3 import JobGeneratorV3Adapter

        adapter = JobGeneratorV3Adapter(max_retry=5)

        assert adapter._orchestrator is not None
        assert hasattr(adapter._orchestrator, "run_workflow")

    def test_adapter_accepts_progress_reporter(self):
        """Adapter should accept optional progress reporter."""
        from aiagent.langgraph.jobGeneratorV2.adapter_v3 import JobGeneratorV3Adapter
        from aiagent.langgraph.jobGeneratorV2.protocols import ProgressReporter

        mock_reporter = MagicMock(spec=ProgressReporter)
        adapter = JobGeneratorV3Adapter(
            max_retry=5,
            progress_reporter=mock_reporter,
        )

        assert adapter._progress_reporter is mock_reporter


class TestAdapterV3APICompatibility:
    """Test backward compatibility with existing API."""

    def test_generate_method_exists(self):
        """Adapter should have generate method matching existing signature."""
        from aiagent.langgraph.jobGeneratorV2.adapter_v3 import JobGeneratorV3Adapter

        adapter = JobGeneratorV3Adapter(max_retry=5)

        assert hasattr(adapter, "generate")
        assert callable(adapter.generate)

    @pytest.mark.asyncio
    async def test_generate_returns_job_generator_response(self):
        """Generate should return JobGeneratorResponse type."""
        from aiagent.langgraph.jobGeneratorV2.adapter_v3 import JobGeneratorV3Adapter

        adapter = JobGeneratorV3Adapter(max_retry=5)

        # Check return type annotation
        import inspect
        sig = inspect.signature(adapter.generate)
        # The return type should be JobGeneratorResponse (from TYPE_CHECKING import)
        assert "JobGeneratorResponse" in str(sig.return_annotation)


class TestAdapterV3ResultConversion:
    """Test result conversion to API response format."""

    def test_convert_successful_result(self):
        """Adapter should convert successful V3 result to response."""
        from aiagent.langgraph.jobGeneratorV2.adapter_v3 import JobGeneratorV3Adapter
        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationResultV3,
        )

        adapter = JobGeneratorV3Adapter(max_retry=5)

        result = JobGenerationResultV3(
            success=True,
            job_id="job_123",
            job_master_id="jm_123",
            task_identifiers=[
                UnifiedTaskIdentifier(task_id="task_001", task_master_id="tm_001"),
            ],
            workflows={"task_001": {"workflow_name": "test"}},
        )

        response = adapter._convert_result(result, "job_123")

        assert response.status == "success"
        assert response.job_id == "job_123"
        assert response.job_master_id == "jm_123"

    def test_convert_failed_result(self):
        """Adapter should convert failed V3 result to response."""
        from aiagent.langgraph.jobGeneratorV2.adapter_v3 import JobGeneratorV3Adapter
        from aiagent.langgraph.jobGeneratorV2.orchestrator_v3 import (
            JobGenerationResultV3,
        )

        adapter = JobGeneratorV3Adapter(max_retry=5)

        result = JobGenerationResultV3(
            success=False,
            error="Validation failed",
        )

        response = adapter._convert_result(result, "job_456")

        assert response.status == "failed"
        assert response.error_message == "Validation failed"


class TestAdapterV3TaskBreakdown:
    """Test task breakdown conversion."""

    def test_convert_tasks_to_breakdown(self):
        """Adapter should convert UnifiedTaskIdentifier to task_breakdown format."""
        from aiagent.langgraph.jobGeneratorV2.adapter_v3 import JobGeneratorV3Adapter
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer_v3 import AnalyzedTask

        adapter = JobGeneratorV3Adapter(max_retry=5)

        tasks = [
            AnalyzedTask(
                task_id="task_001",
                name="Search Gmail",
                description="Search for emails",
                task_type="fetch",
                recommended_api="/api/gmail/search",
                dependencies=[],
                input_schema={},
                output_schema={},
                priority=1,
            ),
            AnalyzedTask(
                task_id="task_002",
                name="Send Email",
                description="Send email",
                task_type="send",
                recommended_api="/api/gmail/send",
                dependencies=["task_001"],
                input_schema={},
                output_schema={},
                priority=2,
            ),
        ]

        breakdown = adapter._convert_tasks_to_breakdown(tasks)

        assert len(breakdown) == 2
        assert breakdown[0]["task_id"] == "task_001"
        assert breakdown[1]["task_id"] == "task_002"
        assert breakdown[1]["dependencies"] == ["task_001"]


class TestAdapterV3InterfaceConversion:
    """Test interface definition conversion."""

    def test_convert_interfaces(self):
        """Adapter should convert interface definitions to API format."""
        from aiagent.langgraph.jobGeneratorV2.adapter_v3 import JobGeneratorV3Adapter
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer_v3 import (
            InterfaceDefinition,
        )

        adapter = JobGeneratorV3Adapter(max_retry=5)

        interfaces = {
            "task_001": InterfaceDefinition(
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                output_schema={"type": "object", "properties": {"results": {"type": "array"}}},
                description="Gmail search interface",
            )
        }

        converted = adapter._convert_interfaces(interfaces)

        assert "task_001" in converted
        assert converted["task_001"]["input_schema"]["type"] == "object"
        assert converted["task_001"]["description"] == "Gmail search interface"


class TestAdapterV3EngineSupport:
    """Test engine parameter support."""

    def test_default_engine_taskflow(self):
        """Default engine should be taskflow."""
        from aiagent.langgraph.jobGeneratorV2.adapter_v3 import JobGeneratorV3Adapter

        adapter = JobGeneratorV3Adapter(max_retry=5)

        assert adapter._engine == "taskflow"

    def test_engine_parameter_accepted(self):
        """Adapter should accept engine parameter."""
        from aiagent.langgraph.jobGeneratorV2.adapter_v3 import JobGeneratorV3Adapter

        adapter = JobGeneratorV3Adapter(max_retry=5, engine="graphai")

        assert adapter._engine == "graphai"
