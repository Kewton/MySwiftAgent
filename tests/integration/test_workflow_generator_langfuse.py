"""Integration tests for Workflow Generator Langfuse tracing.

Issue #278: Verify langfuse_trace_id is included in WorkflowGeneratorResponse.

Test Categories:
- Schema validation: WorkflowGeneratorResponse has langfuse_trace_id field
- Response structure: API response includes langfuse_trace_id
- Backward compatibility: Response works with/without trace_id
"""

import sys
from pathlib import Path

import pytest

# Add expertAgent to path for imports
expert_agent_path = Path(__file__).parent.parent.parent / "expertAgent"
sys.path.insert(0, str(expert_agent_path))

from app.schemas.workflow_generator import (  # noqa: E402
    WorkflowGeneratorRequest,
    WorkflowGeneratorResponse,
    WorkflowResult,
)

# Expose path for use in tests
expertAgent_path = expert_agent_path  # noqa: N816


class TestWorkflowGeneratorResponseSchema:
    """Tests for WorkflowGeneratorResponse schema with langfuse_trace_id.

    Issue #278 AC3: API response must include langfuse_trace_id field.
    """

    def test_response_has_langfuse_trace_id_field(self):
        """Verify WorkflowGeneratorResponse schema has langfuse_trace_id field."""
        response = WorkflowGeneratorResponse(
            status="success",
            total_tasks=1,
            successful_tasks=1,
            failed_tasks=0,
            langfuse_trace_id="trace-workflow-abc123",
        )

        assert hasattr(response, "langfuse_trace_id")
        assert response.langfuse_trace_id == "trace-workflow-abc123"

    def test_response_langfuse_trace_id_defaults_to_none(self):
        """Verify langfuse_trace_id defaults to None for backward compatibility."""
        response = WorkflowGeneratorResponse(
            status="success",
            total_tasks=0,
        )

        assert response.langfuse_trace_id is None

    def test_response_with_all_fields(self):
        """Verify response works with all fields including langfuse_trace_id."""
        workflow_result = WorkflowResult(
            task_master_id="tm_test123",
            task_name="Send Email",
            workflow_name="send_email",
            yaml_content="version: 0.5\nnodes: {}",
            status="success",
        )

        response = WorkflowGeneratorResponse(
            status="success",
            workflows=[workflow_result],
            total_tasks=1,
            successful_tasks=1,
            failed_tasks=0,
            generation_time_ms=1234.5,
            langfuse_trace_id="trace-full-workflow-123",
        )

        assert response.status == "success"
        assert len(response.workflows) == 1
        assert response.langfuse_trace_id == "trace-full-workflow-123"

    def test_response_serialization_includes_trace_id(self):
        """Verify JSON serialization includes langfuse_trace_id."""
        response = WorkflowGeneratorResponse(
            status="success",
            total_tasks=1,
            successful_tasks=1,
            failed_tasks=0,
            langfuse_trace_id="trace-serialize-workflow",
        )

        # Serialize to dict
        response_dict = response.model_dump()

        assert "langfuse_trace_id" in response_dict
        assert response_dict["langfuse_trace_id"] == "trace-serialize-workflow"

    def test_response_serialization_without_trace_id(self):
        """Verify JSON serialization works without langfuse_trace_id."""
        response = WorkflowGeneratorResponse(
            status="failed",
            error_message="Test error",
        )

        # Serialize to dict
        response_dict = response.model_dump()

        assert "langfuse_trace_id" in response_dict
        assert response_dict["langfuse_trace_id"] is None


class TestWorkflowResultSchema:
    """Tests for WorkflowResult schema (unchanged by Issue #278)."""

    def test_workflow_result_basic_fields(self):
        """Verify WorkflowResult basic fields work correctly."""
        result = WorkflowResult(
            task_master_id="tm_123",
            task_name="Test Task",
            workflow_name="test_task",
            yaml_content="version: 0.5",
            status="success",
        )

        assert result.task_master_id == "tm_123"
        assert result.status == "success"
        assert result.retry_count == 0  # default

    def test_workflow_result_with_error(self):
        """Verify WorkflowResult with error fields."""
        result = WorkflowResult(
            task_master_id="tm_456",
            task_name="Failed Task",
            workflow_name="failed_task",
            yaml_content="",
            status="failed",
            error_message="Generation failed",
            retry_count=3,
        )

        assert result.status == "failed"
        assert result.error_message == "Generation failed"
        assert result.retry_count == 3


class TestWorkflowGeneratorRequestSchema:
    """Tests for WorkflowGeneratorRequest schema (unchanged by Issue #278)."""

    def test_request_with_job_master_id(self):
        """Verify request with job_master_id."""
        request = WorkflowGeneratorRequest(
            job_master_id="jm_abc123",
        )

        assert request.job_master_id == "jm_abc123"
        assert request.task_master_id is None

    def test_request_with_task_master_id(self):
        """Verify request with task_master_id."""
        request = WorkflowGeneratorRequest(
            task_master_id="tm_xyz789",
        )

        assert request.task_master_id == "tm_xyz789"
        assert request.job_master_id is None

    def test_request_xor_validation(self):
        """Verify XOR validation: exactly one ID must be provided."""
        # Both provided - should fail
        with pytest.raises(ValueError):
            WorkflowGeneratorRequest(
                job_master_id="jm_123",
                task_master_id="tm_456",
            )

        # Neither provided - should fail
        with pytest.raises(ValueError):
            WorkflowGeneratorRequest()


class TestWorkflowGeneratorLangfuseIntegration:
    """Integration tests for Langfuse tracing in Workflow Generator.

    Issue #278 AC2: Workflow Generator LLM calls must be traced to Langfuse.
    Issue #278 AC4: Existing functionality must work when Langfuse is disabled.
    """

    def test_langfuse_service_source_has_required_class(self):
        """Verify langfuse_service.py source code defines LangfuseService class."""
        langfuse_service_path = expertAgent_path / "app" / "services" / "langfuse_service.py"
        assert langfuse_service_path.exists(), "langfuse_service.py not found"

        content = langfuse_service_path.read_text()
        # Verify class definition exists
        assert "class LangfuseService" in content
        # Verify singleton instance is exported
        assert "langfuse_service = LangfuseService()" in content

    def test_langfuse_service_has_required_methods_in_source(self):
        """Verify LangfuseService source defines all required methods."""
        langfuse_service_path = expertAgent_path / "app" / "services" / "langfuse_service.py"
        content = langfuse_service_path.read_text()

        # Check required methods exist in source
        assert "def get_callback_handler" in content
        assert "def extract_trace_id" in content
        assert "def flush" in content

    def test_workflow_generator_endpoints_imports_langfuse_service(self):
        """Verify workflow_generator_endpoints.py imports langfuse_service."""
        endpoints_path = expertAgent_path / "app" / "api" / "v1" / "workflow_generator_endpoints.py"
        content = endpoints_path.read_text()

        # Check that langfuse_service is imported
        assert "from app.services.langfuse_service import" in content
        assert "langfuse_service" in content
        assert "LangfuseService" in content

    def test_structured_call_result_has_trace_id(self):
        """Verify StructuredCallResult includes trace_id field in source."""
        llm_invocation_path = (
            expertAgent_path
            / "aiagent"
            / "langgraph"
            / "jobTaskGeneratorAgents"
            / "utils"
            / "llm_invocation.py"
        )
        assert llm_invocation_path.exists()

        content = llm_invocation_path.read_text()
        # Verify trace_id field is defined in StructuredCallResult
        assert "trace_id: str | None" in content
        assert "trace_id=trace_id" in content or "trace_id=" in content
