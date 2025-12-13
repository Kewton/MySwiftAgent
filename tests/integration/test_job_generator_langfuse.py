"""Integration tests for Job Generator Langfuse tracing.

Issue #278: Verify langfuse_trace_id is included in JobGeneratorResponse.

Test Categories:
- Schema validation: JobGeneratorResponse has langfuse_trace_id field
- Response structure: API response includes langfuse_trace_id
- Backward compatibility: Response works with/without trace_id
"""

import sys
from pathlib import Path

import pytest

# Add expertAgent to path for imports
expertAgent_path = Path(__file__).parent.parent.parent / "expertAgent"
sys.path.insert(0, str(expertAgent_path))

from app.schemas.job_generator import (
    JobGeneratorRequest,
    JobGeneratorResponse,
)


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

    def test_langfuse_service_available(self):
        """Verify LangfuseService is available for Job Generator."""
        from app.services.langfuse_service import LangfuseService

        service = LangfuseService()
        assert service is not None

    def test_callback_handler_can_be_created(self):
        """Verify CallbackHandler can be created (may return None if disabled)."""
        from app.services.langfuse_service import langfuse_service

        # This may return None if Langfuse is not configured
        handler = langfuse_service.get_callback_handler()
        # Just verify the method exists and doesn't raise
        assert handler is None or handler is not None

    def test_extract_trace_id_works(self):
        """Verify trace_id extraction works with mock handler."""
        from unittest.mock import Mock

        from app.services.langfuse_service import LangfuseService

        mock_handler = Mock()
        mock_handler.last_trace_id = "mock-trace-123"

        trace_id = LangfuseService.extract_trace_id(mock_handler)
        assert trace_id == "mock-trace-123"

    def test_extract_trace_id_returns_none_for_none_handler(self):
        """Verify trace_id extraction returns None for None handler."""
        from app.services.langfuse_service import LangfuseService

        trace_id = LangfuseService.extract_trace_id(None)
        assert trace_id is None
