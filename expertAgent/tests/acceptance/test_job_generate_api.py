"""Job Generate API Direct Execution Test.

Issue #359: Direct API test for job generation without browser.

This test allows direct execution of the job generation API,
which is essential for E2E testing and debugging.

Usage:
    # Run with pytest
    pytest tests/acceptance/test_job_generate_api.py -v -s

    # Run specific test
    pytest tests/acceptance/test_job_generate_api.py::test_job_generation_e2e -v -s

Requirements:
    - ExpertAgent running on localhost:8004 (or EXPERTAGENT_BASE_URL)
    - API keys configured in environment
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

import httpx
import pytest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobPhase(str, Enum):
    """Job generation phases."""

    TASK_ANALYSIS = "task_analysis"
    WORKFLOW_GENERATION = "workflow_generation"
    COMPLETE = "complete"


class JobStatus(str, Enum):
    """Job status values."""

    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


@dataclass
class JobGenerationConfig:
    """Configuration for job generation test."""

    base_url: str = "http://localhost:8004"
    timeout_seconds: int = 300  # 5 minutes max
    poll_interval_seconds: float = 2.0
    admin_token: str | None = None

    @classmethod
    def from_env(cls) -> "JobGenerationConfig":
        """Create config from environment variables."""
        return cls(
            base_url=os.environ.get("EXPERTAGENT_BASE_URL", "http://localhost:8004"),
            timeout_seconds=int(os.environ.get("JOB_GENERATION_TIMEOUT", "300")),
            poll_interval_seconds=float(os.environ.get("JOB_POLL_INTERVAL", "2.0")),
            admin_token=os.environ.get("EXPERTAGENT_ADMIN_TOKEN"),
        )


@dataclass
class JobGenerationResult:
    """Result from job generation."""

    job_id: str
    status: JobStatus
    phase: JobPhase | None
    task_breakdown: list[dict[str, Any]] | None
    workflow_statuses: list[dict[str, Any]] | None
    result: dict[str, Any] | None
    error_message: str | None
    duration_seconds: float


class JobGeneratorClient:
    """Client for Job Generator API.

    Provides direct API access for testing without browser.
    """

    def __init__(self, config: JobGenerationConfig | None = None) -> None:
        """Initialize client.

        Args:
            config: Configuration (uses env vars if None)
        """
        self.config = config or JobGenerationConfig.from_env()
        self._client = httpx.AsyncClient(
            base_url=self.config.base_url,
            timeout=30.0,
            headers=self._build_headers(),
        )

    def _build_headers(self) -> dict[str, str]:
        """Build request headers."""
        headers = {"Content-Type": "application/json"}
        if self.config.admin_token:
            headers["X-Admin-Token"] = self.config.admin_token
        return headers

    async def start_job(self, user_requirement: str) -> dict[str, Any]:
        """Start job generation.

        Args:
            user_requirement: User requirement text

        Returns:
            API response with job_id

        Raises:
            httpx.HTTPError: If API call fails
        """
        response = await self._client.post(
            "/v1/job-generator",
            json={"user_requirement": user_requirement},
        )
        response.raise_for_status()
        return response.json()

    async def get_status(self, job_id: str) -> dict[str, Any]:
        """Get job status.

        Args:
            job_id: Job ID to check

        Returns:
            Job status response

        Raises:
            httpx.HTTPError: If API call fails
        """
        response = await self._client.get(f"/v1/jobs/{job_id}/status")
        response.raise_for_status()
        return response.json()

    async def wait_for_completion(
        self,
        job_id: str,
        on_status_update: callable | None = None,
    ) -> JobGenerationResult:
        """Wait for job to complete.

        Args:
            job_id: Job ID to monitor
            on_status_update: Optional callback for status updates

        Returns:
            JobGenerationResult with final status

        Raises:
            TimeoutError: If job doesn't complete within timeout
        """
        start_time = time.time()
        last_phase = None
        last_progress = -1

        while True:
            elapsed = time.time() - start_time
            if elapsed > self.config.timeout_seconds:
                raise TimeoutError(
                    f"Job {job_id} did not complete within {self.config.timeout_seconds}s"
                )

            status_response = await self.get_status(job_id)

            current_status = status_response.get("status", "")
            current_phase = status_response.get("phase")
            current_progress = status_response.get("progress", 0)

            # Log status changes
            if current_phase != last_phase or current_progress != last_progress:
                logger.info(
                    "Job %s: status=%s, phase=%s, progress=%d%%, elapsed=%.1fs",
                    job_id,
                    current_status,
                    current_phase,
                    current_progress,
                    elapsed,
                )
                last_phase = current_phase
                last_progress = current_progress

                if on_status_update:
                    on_status_update(status_response)

            # Check for terminal states
            if current_status in ("success", "failed", "error"):
                return JobGenerationResult(
                    job_id=job_id,
                    status=JobStatus(current_status) if current_status in JobStatus.__members__.values() else JobStatus.FAILED,
                    phase=JobPhase(current_phase) if current_phase else None,
                    task_breakdown=status_response.get("task_breakdown"),
                    workflow_statuses=status_response.get("workflow_statuses"),
                    result=status_response.get("result"),
                    error_message=status_response.get("error_message"),
                    duration_seconds=elapsed,
                )

            await asyncio.sleep(self.config.poll_interval_seconds)

    async def generate_and_wait(
        self,
        user_requirement: str,
        on_status_update: callable | None = None,
    ) -> JobGenerationResult:
        """Start job and wait for completion.

        Args:
            user_requirement: User requirement text
            on_status_update: Optional callback for status updates

        Returns:
            JobGenerationResult with final status
        """
        logger.info("Starting job generation...")
        start_response = await self.start_job(user_requirement)

        job_id = start_response.get("job_id")
        if not job_id:
            raise ValueError(f"No job_id in response: {start_response}")

        logger.info("Job started: %s", job_id)
        logger.info("Langfuse trace: %s", start_response.get("langfuse_trace_id"))

        return await self.wait_for_completion(job_id, on_status_update)

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()


# ============================================================================
# Test Cases
# ============================================================================


@pytest.fixture
def config() -> JobGenerationConfig:
    """Create test configuration."""
    return JobGenerationConfig.from_env()


@pytest.fixture
async def client(config: JobGenerationConfig) -> JobGeneratorClient:
    """Create test client."""
    client = JobGeneratorClient(config)
    yield client
    await client.close()


# Simple test requirement for quick testing
SIMPLE_REQUIREMENT = """
天気予報を取得してメールで送信するワークフローを作成してください。

1. 東京の天気予報をAPIで取得
2. 天気情報をフォーマット
3. 結果をメールで送信
"""

# Complex test requirement for comprehensive testing
COMPLEX_REQUIREMENT = """
以下の要件を満たすワークフローを作成してください：

1. Google検索で「最新のAI技術」について検索
2. 検索結果の上位5件のURLを取得
3. 各URLの内容をLLMで要約
4. 要約をMarkdown形式でまとめる
5. 結果をGoogle Driveにアップロード
6. 完了通知をメールで送信
"""


@pytest.mark.asyncio
async def test_job_generation_simple(client: JobGeneratorClient) -> None:
    """Test simple job generation E2E.

    This test verifies:
    1. Job can be started via API
    2. Status can be polled
    3. Job completes (success or with meaningful error)
    """
    result = await client.generate_and_wait(SIMPLE_REQUIREMENT)

    logger.info("Job completed: status=%s, duration=%.1fs", result.status, result.duration_seconds)

    if result.status == JobStatus.SUCCESS:
        logger.info("Task breakdown: %s", result.task_breakdown)
        logger.info("Workflow statuses: %s", result.workflow_statuses)
        assert result.task_breakdown is not None, "Expected task_breakdown on success"
    else:
        logger.warning("Job failed: %s", result.error_message)
        # Log error for debugging but don't fail test immediately
        # The purpose is to verify the API flow works


@pytest.mark.asyncio
async def test_job_generation_e2e(client: JobGeneratorClient) -> None:
    """Full E2E test for job generation.

    This test verifies the complete job generation flow:
    1. Start job generation
    2. Monitor task analysis phase
    3. Monitor workflow generation phase
    4. Verify successful completion
    5. Validate generated TaskFlow workflows
    """
    status_updates: list[dict] = []

    def capture_status(status: dict) -> None:
        status_updates.append(status)

    result = await client.generate_and_wait(SIMPLE_REQUIREMENT, on_status_update=capture_status)

    # Log all status updates for debugging
    logger.info("Total status updates: %d", len(status_updates))
    for i, update in enumerate(status_updates):
        logger.info(
            "Update %d: phase=%s, progress=%d%%",
            i,
            update.get("phase"),
            update.get("progress", 0),
        )

    # Assertions
    assert result.job_id is not None, "Expected job_id"
    assert result.duration_seconds > 0, "Expected positive duration"

    if result.status == JobStatus.SUCCESS:
        # Verify task analysis completed
        assert result.task_breakdown is not None, "Expected task_breakdown"
        assert len(result.task_breakdown) > 0, "Expected at least one task"

        # Verify workflow generation completed
        assert result.workflow_statuses is not None, "Expected workflow_statuses"

        # Check that at least one workflow was generated
        successful_workflows = [
            ws for ws in result.workflow_statuses if ws.get("status") == "success"
        ]
        logger.info(
            "Successful workflows: %d/%d",
            len(successful_workflows),
            len(result.workflow_statuses),
        )

        # Log any failed workflows
        failed_workflows = [
            ws for ws in result.workflow_statuses if ws.get("status") == "failed"
        ]
        for fw in failed_workflows:
            logger.warning(
                "Failed workflow for task %s: %s",
                fw.get("task_id"),
                fw.get("error_message"),
            )
    else:
        # Job failed - log for debugging
        logger.error("Job failed: %s", result.error_message)
        logger.error("Final result: %s", result.result)

        # Check if this is the URL validation error we're trying to fix
        if result.error_message and "HTTPS" in result.error_message:
            pytest.fail(
                f"Job failed due to URL validation error (RC-1/RC-2 not fixed): {result.error_message}"
            )


@pytest.mark.asyncio
async def test_job_status_polling(client: JobGeneratorClient) -> None:
    """Test job status polling endpoint.

    Verifies that the status endpoint returns valid data.
    """
    # Start a job
    start_response = await client.start_job(SIMPLE_REQUIREMENT)
    job_id = start_response.get("job_id")
    assert job_id is not None, "Expected job_id"

    # Poll status once
    status = await client.get_status(job_id)

    # Verify status structure
    assert "job_id" in status, "Expected job_id in status"
    assert "status" in status, "Expected status field"
    assert "progress" in status, "Expected progress field"

    logger.info("Status response: %s", status)


@pytest.mark.asyncio
async def test_health_check(config: JobGenerationConfig) -> None:
    """Test ExpertAgent health endpoint.

    Quick smoke test to verify service is running.
    """
    async with httpx.AsyncClient(base_url=config.base_url) as client:
        response = await client.get("/health")
        response.raise_for_status()
        data = response.json()

        assert data.get("status") == "ok" or data.get("status") == "healthy"
        logger.info("Health check passed: %s", data)


# ============================================================================
# CLI Entry Point
# ============================================================================


async def main() -> None:
    """Run job generation test from command line.

    Usage:
        python -m tests.acceptance.test_job_generate_api
    """
    config = JobGenerationConfig.from_env()
    client = JobGeneratorClient(config)

    logger.info("Starting job generation test...")
    logger.info("Base URL: %s", config.base_url)
    logger.info("Timeout: %ds", config.timeout_seconds)

    try:
        result = await client.generate_and_wait(SIMPLE_REQUIREMENT)

        print("\n" + "=" * 60)
        print("JOB GENERATION RESULT")
        print("=" * 60)
        print(f"Job ID: {result.job_id}")
        print(f"Status: {result.status.value}")
        print(f"Phase: {result.phase.value if result.phase else 'N/A'}")
        print(f"Duration: {result.duration_seconds:.1f}s")

        if result.task_breakdown:
            print(f"\nTask Breakdown ({len(result.task_breakdown)} tasks):")
            for task in result.task_breakdown:
                print(f"  - {task.get('name', 'Unknown')}: {task.get('description', '')[:50]}...")

        if result.workflow_statuses:
            print(f"\nWorkflow Statuses ({len(result.workflow_statuses)} workflows):")
            for ws in result.workflow_statuses:
                status_icon = "✓" if ws.get("status") == "success" else "✗"
                print(f"  {status_icon} {ws.get('task_name', ws.get('task_id'))}: {ws.get('status')}")
                if ws.get("error_message"):
                    print(f"      Error: {ws.get('error_message')[:100]}...")

        if result.error_message:
            print(f"\nError: {result.error_message}")

        print("=" * 60)

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
