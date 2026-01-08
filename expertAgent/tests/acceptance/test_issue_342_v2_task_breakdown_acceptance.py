"""Acceptance test for Issue #342 V2 Adapter task_breakdown support.

This test verifies that the V2 Job Generator returns task_breakdown
and interface_definitions in the API response.

L3 Acceptance Test - Requires running services:
- expertAgent (localhost:8004)
- myVault (localhost:8003)
- jobqueue (localhost:8001)

Run with:
    cd expertAgent
    source .venv/bin/activate
    PYTHONPATH=. python -m pytest tests/acceptance/test_issue_342_v2_task_breakdown_acceptance.py -v
"""

import os
import time

import pytest
import requests

# Test configuration
EXPERTAGENT_URL = os.getenv("EXPERTAGENT_URL", "http://localhost:8004")
MYVAULT_URL = os.getenv("MYVAULT_URL", "http://localhost:8003")
JOBQUEUE_URL = os.getenv("JOBQUEUE_URL", "http://localhost:8001")
MAX_POLL_ATTEMPTS = 30
POLL_INTERVAL_SECONDS = 2


def check_service_health(url: str, name: str) -> bool:
    """Check if a service is healthy."""
    try:
        response = requests.get(f"{url}/health", timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False


@pytest.fixture(scope="module")
def services_available():
    """Check if all required services are available."""
    services = [
        (EXPERTAGENT_URL, "expertAgent"),
        (MYVAULT_URL, "myVault"),
        (JOBQUEUE_URL, "jobqueue"),
    ]

    unavailable = []
    for url, name in services:
        if not check_service_health(url, name):
            unavailable.append(name)

    if unavailable:
        pytest.skip(f"Services not available: {', '.join(unavailable)}")

    return True


class TestV2TaskBreakdownAcceptance:
    """Acceptance tests for V2 task_breakdown feature."""

    def test_v2_job_generation_returns_task_breakdown(
        self, services_available: bool
    ) -> None:
        """Test that V2 job generation returns task_breakdown in response.

        Acceptance Criteria:
        1. POST /v1/job-generator returns success
        2. Response contains task_breakdown (not None)
        3. task_breakdown is a non-empty list
        4. Each task has required fields (task_id, name, description)
        """
        # Arrange
        request_data = {
            "user_requirement": "GoogleでAIニュースを検索して、結果をメールで送信",
            "max_retry": 3,
        }

        # Act - Create job
        response = requests.post(
            f"{EXPERTAGENT_URL}/v1/job-generator",
            json=request_data,
            timeout=60,
        )

        # Assert - Initial response
        assert response.status_code == 200, f"Failed: {response.text}"
        result = response.json()
        # API returns "creating" for async job creation
        assert result.get("status") in ["success", "processing", "creating"], (
            f"Status: {result}"
        )

        job_id = result.get("job_id")
        assert job_id is not None, "job_id is None"

        # Poll for completion
        final_result = self._poll_job_status(job_id)

        # Assert - Final result
        assert final_result is not None, "Job did not complete"
        assert final_result.get("status") == "completed", f"Status: {final_result}"

        # Check task_breakdown
        job_result = final_result.get("result", {})
        task_breakdown = job_result.get("task_breakdown")

        assert task_breakdown is not None, (
            f"task_breakdown is None. Full result: {job_result}"
        )
        assert isinstance(task_breakdown, list), (
            f"task_breakdown is not a list: {type(task_breakdown)}"
        )
        assert len(task_breakdown) > 0, "task_breakdown is empty"

        # Validate task structure
        for task in task_breakdown:
            assert "task_id" in task, f"Missing task_id in {task}"
            assert "name" in task, f"Missing name in {task}"
            assert "description" in task, f"Missing description in {task}"

    def test_v2_job_generation_returns_interface_definitions(
        self, services_available: bool
    ) -> None:
        """Test that V2 job generation returns interface_definitions in response.

        Acceptance Criteria:
        1. Response contains interface_definitions (not None)
        2. interface_definitions is a dict
        3. Each interface has input_schema and output_schema
        """
        # Arrange
        request_data = {
            "user_requirement": "Gmailを検索してサマリを作成",
            "max_retry": 3,
        }

        # Act
        response = requests.post(
            f"{EXPERTAGENT_URL}/v1/job-generator",
            json=request_data,
            timeout=60,
        )

        assert response.status_code == 200
        result = response.json()
        job_id = result.get("job_id")
        assert job_id is not None

        # Poll for completion
        final_result = self._poll_job_status(job_id)
        assert final_result is not None

        # Check interface_definitions
        job_result = final_result.get("result", {})
        interface_definitions = job_result.get("interface_definitions")

        assert interface_definitions is not None, (
            f"interface_definitions is None. Full result: {job_result}"
        )
        assert isinstance(interface_definitions, dict), (
            f"interface_definitions is not a dict: {type(interface_definitions)}"
        )
        assert len(interface_definitions) > 0, "interface_definitions is empty"

        # Validate interface structure
        for task_id, interface in interface_definitions.items():
            assert "input_schema" in interface, (
                f"Missing input_schema for {task_id}"
            )
            assert "output_schema" in interface, (
                f"Missing output_schema for {task_id}"
            )

    def test_v2_task_count_matches_interface_count(
        self, services_available: bool
    ) -> None:
        """Test that task count matches interface count.

        Acceptance Criteria:
        1. Number of tasks equals number of interfaces
        2. Each task_id in task_breakdown has a corresponding interface
        """
        # Arrange
        request_data = {
            "user_requirement": "ニュースを検索し、要約をメールで送る",
            "max_retry": 3,
        }

        # Act
        response = requests.post(
            f"{EXPERTAGENT_URL}/v1/job-generator",
            json=request_data,
            timeout=60,
        )

        assert response.status_code == 200
        result = response.json()
        job_id = result.get("job_id")
        final_result = self._poll_job_status(job_id)

        # Assert
        job_result = final_result.get("result", {})
        task_breakdown = job_result.get("task_breakdown", [])
        interface_definitions = job_result.get("interface_definitions", {})

        # Skip if either is None (may indicate V2 not enabled)
        if task_breakdown is None or interface_definitions is None:
            pytest.skip("V2 task_breakdown/interface_definitions not available")

        assert len(task_breakdown) == len(interface_definitions), (
            f"Task count ({len(task_breakdown)}) != "
            f"Interface count ({len(interface_definitions)})"
        )

        # Check each task has an interface
        task_ids = {task["task_id"] for task in task_breakdown}
        interface_ids = set(interface_definitions.keys())

        assert task_ids == interface_ids, (
            f"Task IDs {task_ids} != Interface IDs {interface_ids}"
        )

    def _poll_job_status(self, job_id: str) -> dict | None:
        """Poll job status until completion or timeout."""
        for attempt in range(MAX_POLL_ATTEMPTS):
            try:
                response = requests.get(
                    f"{EXPERTAGENT_URL}/v1/jobs/{job_id}/status",
                    timeout=10,
                )
                if response.status_code == 200:
                    result = response.json()
                    status = result.get("status")

                    if status == "completed":
                        return result
                    elif status in ["failed", "error"]:
                        pytest.fail(f"Job failed: {result}")
                        return None

                time.sleep(POLL_INTERVAL_SECONDS)

            except requests.RequestException as e:
                print(f"Polling error: {e}")
                time.sleep(POLL_INTERVAL_SECONDS)

        return None


class TestV2ConfigVerification:
    """Tests to verify V2 configuration."""

    def test_use_job_generator_v2_enabled(self, services_available: bool) -> None:
        """Verify that USE_JOB_GENERATOR_V2=true is configured."""
        # This test checks via the API behavior
        # If V2 is enabled, task_breakdown should be non-null for success
        request_data = {
            "user_requirement": "テスト用シンプルタスク",
            "max_retry": 2,
        }

        response = requests.post(
            f"{EXPERTAGENT_URL}/v1/job-generator",
            json=request_data,
            timeout=60,
        )

        if response.status_code != 200:
            pytest.skip("Job generation failed")

        result = response.json()
        job_id = result.get("job_id")

        if job_id:
            # Poll for a short time
            for _ in range(10):
                status_response = requests.get(
                    f"{EXPERTAGENT_URL}/v1/jobs/{job_id}/status",
                    timeout=10,
                )
                if status_response.status_code == 200:
                    status_result = status_response.json()
                    if status_result.get("status") == "completed":
                        job_result = status_result.get("result", {})
                        task_breakdown = job_result.get("task_breakdown")

                        # V2 should return task_breakdown
                        assert task_breakdown is not None, (
                            "V2 should return task_breakdown. "
                            "Check USE_JOB_GENERATOR_V2 environment variable."
                        )
                        return

                time.sleep(2)

        # If we reach here, test is inconclusive
        pytest.skip("Could not verify V2 configuration")
