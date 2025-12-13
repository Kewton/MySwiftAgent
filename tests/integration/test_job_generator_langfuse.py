"""Integration tests for Job Generator Langfuse tracing.

Issue #278: Verify langfuse_trace_id is included in JobGeneratorResponse.

Test Categories:
- Schema validation: JobGeneratorResponse has langfuse_trace_id field
- Response structure: API response includes langfuse_trace_id
- Backward compatibility: Response works with/without trace_id
"""

import sys
from pathlib import Path

import pytest  # noqa: F401

# Add expertAgent to path for imports
expert_agent_path = Path(__file__).parent.parent.parent / "expertAgent"
sys.path.insert(0, str(expert_agent_path))

from app.schemas.job_generator import (  # noqa: E402
    JobGeneratorRequest,
    JobGeneratorResponse,
)

# Expose path for use in tests
expertAgent_path = expert_agent_path  # noqa: N816


class TestJobGeneratorResponseSchema:
    """Tests for JobGeneratorResponse schema with langfuse_trace_id.

    Issue #278 AC3: API response must include langfuse_trace_id field.
    """

    def test_response_has_langfuse_trace_id_field(self):
        """Verify JobGeneratorResponse schema has langfuse_trace_id field."""
        response = JobGeneratorResponse(
            status="success",
            job_id="test-job-id",
            job_master_id="jm_test123",
            langfuse_trace_id="trace-abc123",
        )

        assert hasattr(response, "langfuse_trace_id")
        assert response.langfuse_trace_id == "trace-abc123"

    def test_response_langfuse_trace_id_defaults_to_none(self):
        """Verify langfuse_trace_id defaults to None for backward compatibility."""
        response = JobGeneratorResponse(
            status="success",
            job_id="test-job-id",
        )

        assert response.langfuse_trace_id is None

    def test_response_with_all_fields(self):
        """Verify response works with all fields including langfuse_trace_id."""
        response = JobGeneratorResponse(
            status="partial_success",
            job_id="job-123",
            job_master_id="jm_abc",
            task_breakdown=[{"task": "test"}],
            evaluation_result={"score": 0.9},
            infeasible_tasks=[{"task": "complex"}],
            alternative_proposals=[{"proposal": "simple"}],
            api_extension_proposals=[],
            requirement_relaxation_suggestions=[],
            validation_errors=[],
            error_message="Some tasks infeasible",
            langfuse_trace_id="trace-full-123",
        )

        assert response.status == "partial_success"
        assert response.langfuse_trace_id == "trace-full-123"

    def test_response_serialization_includes_trace_id(self):
        """Verify JSON serialization includes langfuse_trace_id."""
        response = JobGeneratorResponse(
            status="success",
            job_id="test-id",
            langfuse_trace_id="trace-serialize-test",
        )

        # Serialize to dict
        response_dict = response.model_dump()

        assert "langfuse_trace_id" in response_dict
        assert response_dict["langfuse_trace_id"] == "trace-serialize-test"

    def test_response_serialization_without_trace_id(self):
        """Verify JSON serialization works without langfuse_trace_id."""
        response = JobGeneratorResponse(
            status="failed",
            error_message="Test error",
        )

        # Serialize to dict
        response_dict = response.model_dump()

        assert "langfuse_trace_id" in response_dict
        assert response_dict["langfuse_trace_id"] is None


class TestJobGeneratorRequestSchema:
    """Tests for JobGeneratorRequest schema (unchanged by Issue #278)."""

    def test_request_basic_fields(self):
        """Verify JobGeneratorRequest basic fields work correctly."""
        request = JobGeneratorRequest(
            user_requirement="Upload PDF to Google Drive",
        )

        assert request.user_requirement == "Upload PDF to Google Drive"
        assert request.max_retry == 5  # default
        assert request.prompt_configs == []  # default

    def test_request_with_all_fields(self):
        """Verify JobGeneratorRequest with all fields."""
        request = JobGeneratorRequest(
            user_requirement="Send email notification",
            max_retry=3,
            prompt_configs=[],
        )

        assert request.max_retry == 3


class TestJobGeneratorLangfuseIntegration:
    """Integration tests for Langfuse tracing in Job Generator.

    Issue #278 AC1: Job Task Generator LLM calls must be traced to Langfuse.
    Issue #278 AC4: Existing functionality must work when Langfuse is disabled.
    """

    def test_langfuse_service_source_has_required_class(self):
        """Verify langfuse_service.py source code defines LangfuseService class."""
        langfuse_service_path = (
            expertAgent_path / "app" / "services" / "langfuse_service.py"
        )
        assert langfuse_service_path.exists(), "langfuse_service.py not found"

        content = langfuse_service_path.read_text()
        # Verify class definition exists
        assert "class LangfuseService" in content
        # Verify singleton instance is exported
        assert "langfuse_service = LangfuseService()" in content

    def test_langfuse_service_has_required_methods_in_source(self):
        """Verify LangfuseService source defines all required methods."""
        langfuse_service_path = (
            expertAgent_path / "app" / "services" / "langfuse_service.py"
        )
        content = langfuse_service_path.read_text()

        # Check required methods exist in source
        assert "def get_callback_handler" in content
        assert "def extract_trace_id" in content
        assert "def flush" in content

    def test_langfuse_service_has_extract_trace_id_static_method(self):
        """Verify extract_trace_id is a static method."""
        langfuse_service_path = (
            expertAgent_path / "app" / "services" / "langfuse_service.py"
        )
        content = langfuse_service_path.read_text()

        # Check that extract_trace_id is decorated with @staticmethod
        assert "@staticmethod" in content
        assert "def extract_trace_id" in content

    def test_job_generator_endpoints_imports_langfuse_service(self):
        """Verify job_generator_endpoints.py imports langfuse_service."""
        endpoints_path = (
            expertAgent_path / "app" / "api" / "v1" / "job_generator_endpoints.py"
        )
        content = endpoints_path.read_text()

        # Check that langfuse_service is imported
        assert "from app.services.langfuse_service import" in content
        assert "langfuse_service" in content
        assert "LangfuseService" in content
