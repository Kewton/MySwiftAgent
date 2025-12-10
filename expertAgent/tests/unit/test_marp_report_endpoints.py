"""Tests for Marp report generation endpoints."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api.v1.marp_report_endpoints import (
    _count_slides,
    _extract_template_data,
    _load_job_result,
    generate_marp_report,
    get_marp_report_by_job_id,
)
from app.schemas.marp_report import MarpReportRequest, MarpReportResponse
from app.services.job_creation_state import JobCreationStatus


class TestLoadJobResult:
    """Test _load_job_result function."""

    def test_load_from_dict(self):
        """Test loading job result from direct JSON input."""
        request = MarpReportRequest(
            job_result={"status": "failed", "job_id": None},
        )

        result = _load_job_result(request)

        assert result["status"] == "failed"
        assert result["job_id"] is None

    def test_load_from_file_success(self, tmp_path: Path):
        """Test loading job result from file path."""
        # Create temp JSON file
        test_data = {
            "status": "failed",
            "infeasible_tasks": [{"task_id": "task_1", "task_name": "Test"}],
            "requirement_relaxation_suggestions": [],
        }
        test_file = tmp_path / "test_result.json"
        test_file.write_text(json.dumps(test_data), encoding="utf-8")

        request = MarpReportRequest(json_file_path=str(test_file))

        result = _load_job_result(request)

        assert result["status"] == "failed"
        assert len(result["infeasible_tasks"]) == 1

    def test_load_from_file_not_found(self):
        """Test file not found error."""
        request = MarpReportRequest(json_file_path="/nonexistent/path/file.json")

        with pytest.raises(HTTPException) as exc_info:
            _load_job_result(request)

        assert exc_info.value.status_code == 404
        assert "not found" in str(exc_info.value.detail).lower()

    def test_load_from_file_invalid_json(self, tmp_path: Path):
        """Test invalid JSON file error."""
        # Create temp file with invalid JSON
        test_file = tmp_path / "invalid.json"
        test_file.write_text("{ invalid json", encoding="utf-8")

        request = MarpReportRequest(json_file_path=str(test_file))

        with pytest.raises(HTTPException) as exc_info:
            _load_job_result(request)

        assert exc_info.value.status_code == 400
        assert "invalid" in str(exc_info.value.detail).lower()


class TestExtractTemplateData:
    """Test _extract_template_data function."""

    def test_extract_with_suggestions(self):
        """Test extracting template data with suggestions."""
        job_result: dict[str, Any] = {
            "status": "failed",
            "error_message": "Job generation did not complete successfully.\nSome details",
            "infeasible_tasks": [
                {"task_id": "task_1", "task_name": "Slack Notification"}
            ],
            "requirement_relaxation_suggestions": [
                {
                    "relaxation_type": "automation_level_reduction",
                    "original_requirement": "Send Slack message",
                    "relaxed_requirement": "Create draft message",
                }
            ],
            "job_id": None,
        }

        result = _extract_template_data(job_result)

        assert result["status"] == "failed"
        assert result["infeasible_tasks_count"] == 1
        assert result["suggestions_count"] == 1
        assert len(result["suggestions"]) == 1
        assert (
            result["suggestions"][0]["relaxation_type"] == "automation_level_reduction"
        )
        assert result["theme"] == "default"
        assert result["include_implementation_steps"] is True
        assert "timestamp" in result

    def test_extract_without_suggestions(self):
        """Test extracting template data without suggestions."""
        job_result: dict[str, Any] = {
            "status": "success",
            "job_id": "123e4567-e89b-12d3-a456-426614174000",
            "infeasible_tasks": [],
            "requirement_relaxation_suggestions": [],
        }

        result = _extract_template_data(job_result)

        assert result["status"] == "success"
        assert result["infeasible_tasks_count"] == 0
        assert result["suggestions_count"] == 0
        assert result["suggestions"] == []
        assert result["job_id"] == "123e4567-e89b-12d3-a456-426614174000"

    def test_extract_with_missing_fields(self):
        """Test extracting template data with missing fields."""
        job_result: dict[str, Any] = {
            "status": "unknown",
        }

        result = _extract_template_data(job_result)

        assert result["status"] == "unknown"
        assert result["infeasible_tasks_count"] == 0
        assert result["suggestions_count"] == 0
        assert result["suggestions"] == []
        assert result["job_id"] is None


class TestCountSlides:
    """Test _count_slides function."""

    def test_count_slides_no_suggestions(self):
        """Test slide count with no suggestions."""
        result = _count_slides(suggestions_count=0, include_implementation_steps=True)

        # Title (1) + Summary (1) + Conclusion (1) = 3
        assert result == 3

    def test_count_slides_with_suggestions(self):
        """Test slide count with suggestions."""
        result = _count_slides(suggestions_count=5, include_implementation_steps=True)

        # Title (1) + Summary (1) + Suggestions (5 * 3) + Conclusion (1) = 18
        assert result == 18

    def test_count_slides_without_implementation_steps(self):
        """Test slide count without implementation steps (no impact currently)."""
        result = _count_slides(suggestions_count=2, include_implementation_steps=False)

        # Title (1) + Summary (1) + Suggestions (2 * 3) + Conclusion (1) = 9
        # Note: Current implementation doesn't change count based on include_implementation_steps
        assert result == 9


class TestMarpReportRequest:
    """Test MarpReportRequest Pydantic model validation."""

    def test_valid_request_with_dict(self):
        """Test valid request with job_result dict."""
        request = MarpReportRequest(
            job_result={"status": "failed"},
            theme="gaia",
            include_implementation_steps=False,
        )

        assert request.job_result == {"status": "failed"}
        assert request.json_file_path is None
        assert request.theme == "gaia"
        assert request.include_implementation_steps is False

    def test_valid_request_with_file_path(self):
        """Test valid request with json_file_path."""
        request = MarpReportRequest(
            json_file_path="/tmp/result.json",
            theme="uncover",
        )

        assert request.job_result is None
        assert request.json_file_path == "/tmp/result.json"
        assert request.theme == "uncover"
        assert request.include_implementation_steps is True  # default

    def test_invalid_both_inputs(self):
        """Test validation error when both inputs are provided."""
        with pytest.raises(ValueError, match="Only one of"):
            MarpReportRequest(
                job_result={"status": "failed"},
                json_file_path="/tmp/result.json",
            )

    def test_invalid_neither_input(self):
        """Test validation error when neither input is provided."""
        with pytest.raises(ValueError, match="Either job_result or json_file_path"):
            MarpReportRequest()

    def test_invalid_theme(self):
        """Test validation error for invalid theme."""
        with pytest.raises(ValueError, match="pattern"):
            MarpReportRequest(
                job_result={"status": "failed"},
                theme="invalid_theme",
            )

    def test_default_values(self):
        """Test default values."""
        request = MarpReportRequest(job_result={"status": "failed"})

        assert request.theme == "default"
        assert request.include_implementation_steps is True


class TestGenerateMarpReport:
    """Test generate_marp_report endpoint."""

    @pytest.mark.asyncio
    async def test_generate_report_success(self, tmp_path: Path):
        """Test successful Marp report generation."""
        # Create test data file
        test_data = {
            "status": "failed",
            "error_message": "Job generation did not complete successfully.",
            "infeasible_tasks": [{"task_id": "task_1"}],
            "requirement_relaxation_suggestions": [
                {
                    "relaxation_type": "automation_level_reduction",
                    "original_requirement": "Original task",
                    "relaxed_requirement": "Relaxed task",
                    "feasibility_after_relaxation": "High",
                    "recommendation_level": "Highly Recommended",
                    "what_is_sacrificed": "Full automation",
                    "what_is_preserved": "Core functionality",
                    "implementation_note": "Requires manual step",
                    "available_capabilities_used": ["geminiAgent"],
                    "implementation_steps": ["Step 1", "Step 2"],
                }
            ],
            "job_id": None,
        }
        test_file = tmp_path / "test_report.json"
        test_file.write_text(json.dumps(test_data), encoding="utf-8")

        request = MarpReportRequest(
            json_file_path=str(test_file),
            theme="default",
            include_implementation_steps=True,
        )

        result = await generate_marp_report(request)

        assert isinstance(result, MarpReportResponse)
        assert (
            result.slide_count == 6
        )  # Title + Summary + (1 suggestion * 3) + Conclusion
        assert result.suggestions_count == 1
        assert result.generation_time_ms > 0
        assert "marp: true" in result.marp_markdown
        assert "Job/Task 生成レポート" in result.marp_markdown
        assert (
            "自動化レベルの調整" in result.marp_markdown
        )  # Japanese label for automation_level_reduction

    @pytest.mark.asyncio
    async def test_generate_report_with_dict_input(self):
        """Test Marp report generation with direct JSON input."""
        test_data = {
            "status": "success",
            "infeasible_tasks": [],
            "requirement_relaxation_suggestions": [],
            "job_id": "123e4567-e89b-12d3-a456-426614174000",
        }

        request = MarpReportRequest(
            job_result=test_data,
            theme="gaia",
            include_implementation_steps=False,
        )

        result = await generate_marp_report(request)

        assert isinstance(result, MarpReportResponse)
        assert result.slide_count == 3  # Title + Summary + Conclusion
        assert result.suggestions_count == 0
        assert "theme: gaia" in result.marp_markdown

    @pytest.mark.asyncio
    async def test_generate_report_file_not_found(self):
        """Test error handling for file not found."""
        request = MarpReportRequest(json_file_path="/nonexistent/file.json")

        with pytest.raises(HTTPException) as exc_info:
            await generate_marp_report(request)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_generate_report_invalid_json(self, tmp_path: Path):
        """Test error handling for invalid JSON file."""
        test_file = tmp_path / "invalid.json"
        test_file.write_text("{ invalid", encoding="utf-8")

        request = MarpReportRequest(json_file_path=str(test_file))

        with pytest.raises(HTTPException) as exc_info:
            await generate_marp_report(request)

        assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    @patch("app.api.v1.marp_report_endpoints.jinja_env")
    async def test_generate_report_template_error(self, mock_jinja_env: MagicMock):
        """Test error handling for template rendering failure."""
        # Mock template to raise exception
        mock_template = MagicMock()
        mock_template.render.side_effect = Exception("Template error")
        mock_jinja_env.get_template.return_value = mock_template

        request = MarpReportRequest(job_result={"status": "failed"})

        with pytest.raises(HTTPException) as exc_info:
            await generate_marp_report(request)

        assert exc_info.value.status_code == 500
        assert "internal server error" in str(exc_info.value.detail).lower()


class TestGetMarpReportByJobId:
    """Test get_marp_report_by_job_id endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.marp_report_endpoints.job_state_manager")
    @patch("app.api.v1.marp_report_endpoints.jinja_env")
    async def test_get_marp_report_by_job_id_success(
        self, mock_jinja_env: MagicMock, mock_state_manager: MagicMock
    ):
        """Test successful retrieval of completed job's Marp report."""
        from datetime import datetime

        # Setup mock job status with completed state
        mock_status = JobCreationStatus(
            job_id="test-job-123",
            status="completed",
            progress=100,
            start_time=datetime.now(),
            result={
                "status": "failed",
                "error_message": "Job generation did not complete successfully.",
                "infeasible_tasks": [{"task_id": "task_1", "task_name": "Test Task"}],
                "requirement_relaxation_suggestions": [
                    {
                        "relaxation_type": "automation_level_reduction",
                        "original_requirement": "Original task",
                        "relaxed_requirement": "Relaxed task",
                        "feasibility_after_relaxation": "High",
                        "recommendation_level": "Highly Recommended",
                    }
                ],
                "job_id": "test-job-123",
            },
        )

        # Mock async method
        mock_state_manager.get_status_async = AsyncMock(return_value=mock_status)

        # Mock template rendering
        mock_template = MagicMock()
        mock_template.render.return_value = "---\nmarp: true\n---\n# Test Report"
        mock_jinja_env.get_template.return_value = mock_template

        result = await get_marp_report_by_job_id("test-job-123")

        # Verify async method was called
        mock_state_manager.get_status_async.assert_called_once_with("test-job-123")

        # Verify response
        assert result.job_id == "test-job-123"
        assert result.markdown == "---\nmarp: true\n---\n# Test Report"
        assert result.slide_count > 0

    @pytest.mark.asyncio
    @patch("app.api.v1.marp_report_endpoints.job_state_manager")
    async def test_get_marp_report_by_job_id_not_found(
        self, mock_state_manager: MagicMock
    ):
        """Test 404 error with improved message when job not found."""
        # Mock async method returning None (job not found)
        mock_state_manager.get_status_async = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_marp_report_by_job_id("nonexistent-job-id")

        # Verify async method was called
        mock_state_manager.get_status_async.assert_called_once_with(
            "nonexistent-job-id"
        )

        # Verify error response
        assert exc_info.value.status_code == 404
        assert "Job not found or expired" in str(exc_info.value.detail)
        assert "24 hours" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("app.api.v1.marp_report_endpoints.job_state_manager")
    async def test_get_marp_report_by_job_id_not_completed(
        self, mock_state_manager: MagicMock
    ):
        """Test 400 error when job is not yet completed."""
        from datetime import datetime

        # Setup mock job status with 'creating' state
        mock_status = JobCreationStatus(
            job_id="in-progress-job",
            status="creating",
            progress=50,
            start_time=datetime.now(),
        )

        mock_state_manager.get_status_async = AsyncMock(return_value=mock_status)

        with pytest.raises(HTTPException) as exc_info:
            await get_marp_report_by_job_id("in-progress-job")

        # Verify async method was called
        mock_state_manager.get_status_async.assert_called_once_with("in-progress-job")

        # Verify error response
        assert exc_info.value.status_code == 400
        assert "not completed" in str(exc_info.value.detail).lower()
        assert "creating" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("app.api.v1.marp_report_endpoints.job_state_manager")
    async def test_get_marp_report_by_job_id_no_result(
        self, mock_state_manager: MagicMock
    ):
        """Test 404 error when job completed but has no result data."""
        from datetime import datetime

        # Setup mock job status with completed state but no result
        mock_status = JobCreationStatus(
            job_id="job-no-result",
            status="completed",
            progress=100,
            start_time=datetime.now(),
            result=None,  # No result available
        )

        mock_state_manager.get_status_async = AsyncMock(return_value=mock_status)

        with pytest.raises(HTTPException) as exc_info:
            await get_marp_report_by_job_id("job-no-result")

        # Verify async method was called
        mock_state_manager.get_status_async.assert_called_once_with("job-no-result")

        # Verify error response
        assert exc_info.value.status_code == 404
        assert "job-no-result" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("app.api.v1.marp_report_endpoints.job_state_manager")
    @patch("app.api.v1.marp_report_endpoints.jinja_env")
    async def test_get_marp_report_by_job_id_template_error(
        self, mock_jinja_env: MagicMock, mock_state_manager: MagicMock
    ):
        """Test 500 error when template rendering fails."""
        from datetime import datetime

        # Setup mock job status with completed state
        mock_status = JobCreationStatus(
            job_id="job-template-error",
            status="completed",
            progress=100,
            start_time=datetime.now(),
            result={
                "status": "failed",
                "infeasible_tasks": [],
                "requirement_relaxation_suggestions": [],
            },
        )

        mock_state_manager.get_status_async = AsyncMock(return_value=mock_status)

        # Mock template to raise exception
        mock_template = MagicMock()
        mock_template.render.side_effect = Exception("Template rendering failed")
        mock_jinja_env.get_template.return_value = mock_template

        with pytest.raises(HTTPException) as exc_info:
            await get_marp_report_by_job_id("job-template-error")

        # Verify error response
        assert exc_info.value.status_code == 500
        assert "internal server error" in str(exc_info.value.detail).lower()
