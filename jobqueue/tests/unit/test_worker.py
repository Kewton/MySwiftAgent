"""Test background worker functionality."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.core.worker import JobExecutor, WorkerManager
from app.models.job import BackoffStrategy, Job, JobStatus


class TestJobExecutor:
    """Test job executor functionality."""

    @pytest.fixture
    def mock_session(self):
        """Create mock database session."""
        session = AsyncMock()
        session.commit = AsyncMock()
        session.scalar = AsyncMock()
        session.add = MagicMock()
        return session

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = MagicMock()
        settings.result_max_bytes = 1048576
        return settings

    @pytest.fixture
    def sample_job(self):
        """Create sample job for testing."""
        return Job(
            id="j_test123",
            method="GET",
            url="https://httpbin.org/get",
            timeout_sec=30,
            attempt=1,
            max_attempts=3,
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            backoff_seconds=5,
        )

    @pytest.mark.asyncio
    async def test_execute_job_success(self, mock_session, mock_settings, sample_job):
        """Test successful job execution."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.is_success = True
        mock_response.headers = {"content-type": "application/json"}
        mock_response.content = b'{"success": true}'
        mock_response.json.return_value = {"success": True}

        # Mock session scalar to return None (no existing result)
        mock_session.scalar.return_value = None

        executor = JobExecutor(mock_session, mock_settings)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.request.return_value = mock_response

            await executor.execute_job(sample_job)

            # Verify job status updated
            assert sample_job.status == JobStatus.SUCCEEDED
            assert sample_job.started_at is not None
            assert sample_job.finished_at is not None

            # Verify HTTP request made correctly
            mock_client.request.assert_called_once_with(
                method="GET",
                url="https://httpbin.org/get",
                headers={},
                params={},
                json=None,
                timeout=30,
            )

            # Verify result created
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called()

    @pytest.mark.asyncio
    async def test_execute_job_http_error(self, mock_session, mock_settings, sample_job):
        """Test job execution with HTTP error response."""
        # Mock HTTP response with error
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.is_success = False
        mock_response.text = "Not Found"
        mock_response.headers = {"content-type": "text/plain"}
        mock_response.content = b"Not Found"

        mock_session.scalar.return_value = None

        executor = JobExecutor(mock_session, mock_settings)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.request.return_value = mock_response

            await executor.execute_job(sample_job)

            # Verify job marked as failed
            assert sample_job.status == JobStatus.FAILED
            assert sample_job.finished_at is not None

    @pytest.mark.asyncio
    async def test_execute_job_exception_with_retry(self, mock_session, mock_settings, sample_job):
        """Test job execution with exception and retry."""
        mock_session.scalar.return_value = None

        executor = JobExecutor(mock_session, mock_settings)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.request.side_effect = httpx.TimeoutException("Request timeout")

            await executor.execute_job(sample_job)

            # Should schedule retry since attempt < max_attempts
            assert sample_job.status == JobStatus.QUEUED
            assert sample_job.attempt == 2
            assert sample_job.next_attempt_at > datetime.utcnow()

    @pytest.mark.asyncio
    async def test_execute_job_exception_no_more_retries(self, mock_session, mock_settings, sample_job):
        """Test job execution with exception when no more retries available."""
        # Set to last attempt
        sample_job.attempt = sample_job.max_attempts

        mock_session.scalar.return_value = None

        executor = JobExecutor(mock_session, mock_settings)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.request.side_effect = httpx.TimeoutException("Request timeout")

            await executor.execute_job(sample_job)

            # Should mark as failed since no more retries
            assert sample_job.status == JobStatus.FAILED
            assert sample_job.finished_at is not None

    def test_calculate_backoff_fixed(self, mock_session, mock_settings):
        """Test fixed backoff calculation."""
        executor = JobExecutor(mock_session, mock_settings)

        job = Job(
            id="test",
            method="GET",
            url="https://httpbin.org/get",
            backoff_strategy=BackoffStrategy.FIXED,
            backoff_seconds=10,
            attempt=3,
        )

        delay = executor._calculate_backoff(job)
        assert delay == 10  # Fixed delay regardless of attempt

    def test_calculate_backoff_linear(self, mock_session, mock_settings):
        """Test linear backoff calculation."""
        executor = JobExecutor(mock_session, mock_settings)

        job = Job(
            id="test",
            method="GET",
            url="https://httpbin.org/get",
            backoff_strategy=BackoffStrategy.LINEAR,
            backoff_seconds=5,
            attempt=3,
        )

        delay = executor._calculate_backoff(job)
        assert delay == 10  # 5 * (3-1) = 10

    def test_calculate_backoff_exponential(self, mock_session, mock_settings):
        """Test exponential backoff calculation."""
        executor = JobExecutor(mock_session, mock_settings)

        job = Job(
            id="test",
            method="GET",
            url="https://httpbin.org/get",
            backoff_strategy=BackoffStrategy.EXPONENTIAL,
            backoff_seconds=2,
            attempt=4,
        )

        delay = executor._calculate_backoff(job)
        assert delay == 16  # 2 * (2^(4-1)) = 16


class TestWorkerManager:
    """Test worker manager functionality."""

    @pytest.mark.asyncio
    async def test_worker_manager_initialization(self):
        """Test worker manager initialization."""
        with patch("app.core.worker.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.concurrency = 2
            mock_get_settings.return_value = mock_settings

            manager = WorkerManager()
            assert not manager.running
            assert len(manager.workers) == 0

    @pytest.mark.asyncio
    async def test_worker_manager_start_stop(self):
        """Test worker manager start and stop."""
        with patch("app.core.worker.get_settings") as mock_get_settings:
            mock_settings = MagicMock()
            mock_settings.concurrency = 1
            mock_get_settings.return_value = mock_settings

            manager = WorkerManager()

            # Start workers
            start_task = asyncio.create_task(manager.start())

            # Give it a moment to start
            await asyncio.sleep(0.1)

            assert manager.running
            assert len(manager.workers) == 1

            # Stop workers
            await manager.stop()

            assert not manager.running
            assert len(manager.workers) == 0

            # Cancel the start task
            start_task.cancel()
            try:
                await start_task
            except asyncio.CancelledError:
                pass
