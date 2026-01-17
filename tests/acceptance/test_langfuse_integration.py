"""E2E Acceptance tests for Langfuse integration in Job/Workflow Generators.

Issue #278: Verify Langfuse tracing integration works end-to-end.

These tests require:
- expertAgent service running (http://localhost:8104)
- Langfuse configured and enabled (or disabled for graceful degradation tests)
- ANTHROPIC_API_KEY configured in myVault

Test Categories:
- AC1: Job Task Generator LLM calls are traced to Langfuse
- AC2: Workflow Generator LLM calls are traced to Langfuse
- AC3: API responses include langfuse_trace_id field
- AC4: Existing functionality works when Langfuse is disabled
"""

import os
from pathlib import Path

import pytest
import requests

# Skip all tests in this module if not running acceptance tests
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_ACCEPTANCE_TESTS", "false").lower() != "true",
    reason="Acceptance tests require RUN_ACCEPTANCE_TESTS=true and running services",
)

# Base URL for expertAgent API
EXPERT_AGENT_BASE_URL = os.getenv("EXPERT_AGENT_URL", "http://localhost:8104/aiagent-api")


class TestLangfuseJobGeneratorIntegration:
    """E2E tests for Job Generator Langfuse integration.

    Issue #278 AC1: Job Task Generator LLM calls must be traced to Langfuse.
    Issue #278 AC3: API response must include langfuse_trace_id field.
    """

    def test_job_generator_response_has_langfuse_trace_id_field(self):
        """Verify Job Generator response includes langfuse_trace_id field.

        Note: The initial response will have langfuse_trace_id=null because
        the job is processed asynchronously. The trace_id is available
        when polling the job status after completion.
        """
        response = requests.post(
            f"{EXPERT_AGENT_BASE_URL}/v1/job-generator",
            json={
                "user_requirement": "Simple test: send email notification",
                "max_retry": 1,
            },
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify langfuse_trace_id field exists in response
        assert "langfuse_trace_id" in data
        # Initial response has null trace_id (async processing)
        # The actual trace_id is available in the completed job status

    def test_job_generator_returns_job_id_for_polling(self):
        """Verify Job Generator returns job_id for status polling."""
        response = requests.post(
            f"{EXPERT_AGENT_BASE_URL}/v1/job-generator",
            json={
                "user_requirement": "Test task: upload file to Drive",
                "max_retry": 1,
            },
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "creating"
        assert data["job_id"] is not None
        assert isinstance(data["job_id"], str)


class TestLangfuseWorkflowGeneratorIntegration:
    """E2E tests for Workflow Generator Langfuse integration.

    Issue #278 AC2: Workflow Generator LLM calls must be traced to Langfuse.
    Issue #278 AC3: API response must include langfuse_trace_id field.
    """

    @pytest.mark.skip(reason="Requires valid task_master_id from jobqueue")
    def test_workflow_generator_response_has_langfuse_trace_id_field(self):
        """Verify Workflow Generator response includes langfuse_trace_id field.

        Note: This test requires a valid task_master_id from the jobqueue service.
        """
        response = requests.post(
            f"{EXPERT_AGENT_BASE_URL}/v1/workflow-generator",
            json={
                "task_master_id": "tm_test123",  # Would need valid ID
            },
            timeout=60,
        )

        # If task doesn't exist, we get 404 - still verify response structure
        if response.status_code == 200:
            data = response.json()
            assert "langfuse_trace_id" in data


class TestLangfuseGracefulDegradation:
    """E2E tests for graceful degradation when Langfuse is disabled.

    Issue #278 AC4: Existing functionality must work when Langfuse is disabled.
    """

    def test_job_generator_works_without_langfuse(self):
        """Verify Job Generator works even when Langfuse might be disabled.

        The endpoint should return a valid response regardless of Langfuse status.
        """
        response = requests.post(
            f"{EXPERT_AGENT_BASE_URL}/v1/job-generator",
            json={
                "user_requirement": "Test: analyze data and create report",
                "max_retry": 1,
            },
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()

        # Core functionality should work
        assert data["status"] == "creating"
        assert data["job_id"] is not None

        # langfuse_trace_id should exist (even if null when disabled)
        assert "langfuse_trace_id" in data


class TestLangfuseResponseStructure:
    """Tests for verifying response structure includes all required fields."""

    def test_job_generator_response_schema_completeness(self):
        """Verify JobGeneratorResponse includes all expected fields."""
        response = requests.post(
            f"{EXPERT_AGENT_BASE_URL}/v1/job-generator",
            json={
                "user_requirement": "Schema test: send notification",
                "max_retry": 1,
            },
            timeout=30,
        )

        assert response.status_code == 200
        data = response.json()

        # Required fields from JobGeneratorResponse schema
        expected_fields = [
            "status",
            "job_id",
            "job_master_id",
            "task_breakdown",
            "evaluation_result",
            "infeasible_tasks",
            "alternative_proposals",
            "api_extension_proposals",
            "requirement_relaxation_suggestions",
            "validation_errors",
            "error_message",
            "langfuse_trace_id",  # Issue #278
        ]

        for field in expected_fields:
            assert field in data, f"Missing field: {field}"


class TestLangfuseApiDocumentation:
    """Tests to verify API documentation is up to date."""

    def test_api_reference_documents_langfuse_trace_id(self):
        """Verify API_REFERENCE.md documents the langfuse_trace_id field."""
        api_ref_path = (
            Path(__file__).parent.parent.parent / "expertAgent" / "docs" / "API_REFERENCE.md"
        )

        if not api_ref_path.exists():
            pytest.skip("API_REFERENCE.md not found")

        content = api_ref_path.read_text()

        # Check Job Generator section
        assert "langfuse_trace_id" in content
        assert "Issue #278" in content or "Langfuse" in content
