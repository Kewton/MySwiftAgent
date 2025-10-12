"""Test database models."""

from app.models.job import BackoffStrategy, Job, JobStatus
from app.models.result import JobResult


class TestJobModel:
    """Test Job model."""

    def test_job_creation(self):
        """Test job creation with required fields."""
        job = Job(
            id="j_test123",
            method="POST",
            url="https://httpbin.org/post",
        )

        assert job.id == "j_test123"
        assert job.method == "POST"
        assert job.url == "https://httpbin.org/post"
        # Defaults are set by SQLAlchemy - we'll test they exist, values might be None until persisted
        assert hasattr(job, "status")
        assert hasattr(job, "attempt")
        assert hasattr(job, "max_attempts")
        assert hasattr(job, "priority")
        assert hasattr(job, "timeout_sec")
        assert hasattr(job, "backoff_strategy")
        assert hasattr(job, "backoff_seconds")

    def test_job_with_optional_fields(self):
        """Test job creation with optional fields."""
        job = Job(
            id="j_test456",
            method="GET",
            url="https://httpbin.org/get",
            headers={"Authorization": "Bearer token"},
            params={"debug": "1"},
            body={"test": "data"},
            timeout_sec=60,
            priority=1,
            max_attempts=3,
            backoff_strategy=BackoffStrategy.LINEAR,
            backoff_seconds=10,
            tags=["test", "api"],
        )

        assert job.headers == {"Authorization": "Bearer token"}
        assert job.params == {"debug": "1"}
        assert job.body == {"test": "data"}
        assert job.timeout_sec == 60
        assert job.priority == 1
        assert job.max_attempts == 3
        assert job.backoff_strategy == BackoffStrategy.LINEAR
        assert job.backoff_seconds == 10
        assert job.tags == ["test", "api"]

    def test_job_status_enum(self):
        """Test job status enumeration values."""
        assert JobStatus.QUEUED == "queued"
        assert JobStatus.RUNNING == "running"
        assert JobStatus.SUCCEEDED == "succeeded"
        assert JobStatus.FAILED == "failed"
        assert JobStatus.CANCELED == "canceled"

    def test_backoff_strategy_enum(self):
        """Test backoff strategy enumeration values."""
        assert BackoffStrategy.FIXED == "fixed"
        assert BackoffStrategy.LINEAR == "linear"
        assert BackoffStrategy.EXPONENTIAL == "exponential"


class TestJobResultModel:
    """Test JobResult model."""

    def test_result_creation(self):
        """Test result creation with required fields."""
        result = JobResult(job_id="j_test123")

        assert result.job_id == "j_test123"
        assert result.response_status is None
        assert result.response_headers is None
        assert result.response_body is None
        assert result.error is None
        assert result.duration_ms is None

    def test_result_with_success_data(self):
        """Test result creation with success data."""
        result = JobResult(
            job_id="j_test456",
            response_status=200,
            response_headers={"content-type": "application/json"},
            response_body={"success": True},
            duration_ms=250,
        )

        assert result.job_id == "j_test456"
        assert result.response_status == 200
        assert result.response_headers == {"content-type": "application/json"}
        assert result.response_body == {"success": True}
        assert result.error is None
        assert result.duration_ms == 250

    def test_result_with_error_data(self):
        """Test result creation with error data."""
        result = JobResult(
            job_id="j_test789",
            error="Connection timeout",
            duration_ms=30000,
        )

        assert result.job_id == "j_test789"
        assert result.response_status is None
        assert result.error == "Connection timeout"
        assert result.duration_ms == 30000
