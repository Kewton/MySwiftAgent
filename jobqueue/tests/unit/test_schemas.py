"""Test Pydantic schemas."""

from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models.job import BackoffStrategy, JobStatus
from app.schemas.job import JobCreate, JobDetail, JobResponse
from app.schemas.result import JobResultResponse


class TestJobSchemas:
    """Test job schemas."""

    def test_job_create_valid(self):
        """Test valid job creation schema."""
        data = {
            "method": "POST",
            "url": "https://httpbin.org/post",
            "headers": {"Content-Type": "application/json"},
            "body": {"message": "hello"},
            "timeout_sec": 15,
            "max_attempts": 3,
        }

        job_create = JobCreate(**data)

        assert job_create.method == "POST"
        assert str(job_create.url) == "https://httpbin.org/post"
        assert job_create.headers == {"Content-Type": "application/json"}
        assert job_create.body == {"message": "hello"}
        assert job_create.timeout_sec == 15
        assert job_create.max_attempts == 3
        assert job_create.priority == 5  # default
        assert job_create.backoff_strategy == BackoffStrategy.EXPONENTIAL  # default

    def test_job_create_minimal(self):
        """Test minimal job creation schema."""
        data = {
            "method": "GET",
            "url": "https://httpbin.org/get",
        }

        job_create = JobCreate(**data)

        assert job_create.method == "GET"
        assert str(job_create.url) == "https://httpbin.org/get"
        assert job_create.headers is None
        assert job_create.body is None
        assert job_create.timeout_sec == 30  # default
        assert job_create.max_attempts == 1  # default

    def test_job_create_invalid_method(self):
        """Test invalid HTTP method."""
        data = {
            "method": "INVALID",
            "url": "https://httpbin.org/get",
        }

        with pytest.raises(ValidationError) as exc_info:
            JobCreate(**data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("method",)
        assert "string_pattern_mismatch" in errors[0]["type"]

    def test_job_create_invalid_url(self):
        """Test invalid URL."""
        data = {
            "method": "GET",
            "url": "not-a-valid-url",
        }

        with pytest.raises(ValidationError) as exc_info:
            JobCreate(**data)

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0]["loc"] == ("url",)

    def test_job_create_validation_ranges(self):
        """Test validation ranges for numeric fields."""
        # Test timeout_sec range
        with pytest.raises(ValidationError):
            JobCreate(method="GET", url="https://httpbin.org/get", timeout_sec=0)

        with pytest.raises(ValidationError):
            JobCreate(method="GET", url="https://httpbin.org/get", timeout_sec=3601)

        # Test priority range
        with pytest.raises(ValidationError):
            JobCreate(method="GET", url="https://httpbin.org/get", priority=0)

        with pytest.raises(ValidationError):
            JobCreate(method="GET", url="https://httpbin.org/get", priority=11)

        # Test max_attempts range
        with pytest.raises(ValidationError):
            JobCreate(method="GET", url="https://httpbin.org/get", max_attempts=0)

        with pytest.raises(ValidationError):
            JobCreate(method="GET", url="https://httpbin.org/get", max_attempts=11)

    def test_job_response_schema(self):
        """Test job response schema."""
        data = {
            "job_id": "j_01HXYZ123",
            "status": "queued",
        }

        response = JobResponse(**data)

        assert response.job_id == "j_01HXYZ123"
        assert response.status == JobStatus.QUEUED

    def test_job_detail_schema(self):
        """Test job detail schema."""
        now = datetime.utcnow()
        data = {
            "id": "j_01HXYZ123",
            "status": "running",
            "attempt": 1,
            "max_attempts": 3,
            "priority": 5,
            "method": "POST",
            "url": "https://httpbin.org/post",
            "timeout_sec": 30,
            "created_at": now,
            "started_at": now,
            "tags": ["test", "api"],
        }

        detail = JobDetail(**data)

        assert detail.id == "j_01HXYZ123"
        assert detail.status == JobStatus.RUNNING
        assert detail.attempt == 1
        assert detail.max_attempts == 3
        assert detail.priority == 5
        assert detail.method == "POST"
        assert detail.url == "https://httpbin.org/post"
        assert detail.timeout_sec == 30
        assert detail.created_at == now
        assert detail.started_at == now
        assert detail.tags == ["test", "api"]


class TestJobResultSchema:
    """Test job result schema."""

    def test_result_response_success(self):
        """Test successful result response schema."""
        data = {
            "job_id": "j_01HXYZ123",
            "status": "succeeded",
            "response_status": 200,
            "response_headers": {"content-type": "application/json"},
            "response_body": {"success": True},
            "duration_ms": 250,
        }

        result = JobResultResponse(**data)

        assert result.job_id == "j_01HXYZ123"
        assert result.status == JobStatus.SUCCEEDED
        assert result.response_status == 200
        assert result.response_headers == {"content-type": "application/json"}
        assert result.response_body == {"success": True}
        assert result.error is None
        assert result.duration_ms == 250

    def test_result_response_failure(self):
        """Test failed result response schema."""
        data = {
            "job_id": "j_01HXYZ456",
            "status": "failed",
            "error": "Connection timeout",
            "duration_ms": 30000,
        }

        result = JobResultResponse(**data)

        assert result.job_id == "j_01HXYZ456"
        assert result.status == JobStatus.FAILED
        assert result.response_status is None
        assert result.response_headers is None
        assert result.response_body is None
        assert result.error == "Connection timeout"
        assert result.duration_ms == 30000
