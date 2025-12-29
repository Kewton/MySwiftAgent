"""Acceptance tests for task_api_mapping feature.

Issue #305: Verify that task_api_mapping is included in prompts
and File Reader Agent is recommended for PDF reading tasks.

These tests require running services:
- expertAgent (http://localhost:8004)
- myVault (http://localhost:8003)

Run with:
    uv run pytest tests/acceptance/test_task_api_mapping_acceptance.py -v
"""

import time

import pytest
import requests

from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
    _build_expert_agent_capabilities,
    _build_task_breakdown_system_prompt,
)


class TestTaskApiMappingInPrompt:
    """Test that task_api_mapping is properly included in prompts."""

    def test_capabilities_include_task_api_mapping_table(self) -> None:
        """Verify task_api_mapping is formatted as a table in capabilities."""
        capabilities = _build_expert_agent_capabilities()

        # Verify table structure
        assert "**タスク種別ごとの推奨API**:" in capabilities
        assert "| タスク種別 | 推奨API | エンドポイント | 理由 |" in capabilities
        assert "|-----------|---------|---------------|------|" in capabilities

    def test_capabilities_include_file_reader_mapping(self) -> None:
        """Verify File Reader Agent is mapped to file reading tasks."""
        capabilities = _build_expert_agent_capabilities()

        # Verify File Reader Agent mapping
        assert "ファイル読み取り" in capabilities
        assert "File Reader Agent" in capabilities
        assert "/v1/aiagent/utility/file_reader" in capabilities

    def test_capabilities_include_all_major_mappings(self) -> None:
        """Verify all major task types have mappings."""
        capabilities = _build_expert_agent_capabilities()

        # Verify key task types are mapped
        expected_mappings = [
            ("音声合成", "Text-to-Speech"),
            ("ファイルアップロード", "Google Drive Upload"),
            ("メール送信", "Gmail送信"),
            ("メール検索", "Gmail検索"),
            ("Web検索", "Google検索"),
            ("ファイル読み取り", "File Reader Agent"),
        ]

        for task_type, api_name in expected_mappings:
            assert task_type in capabilities, f"Missing task type: {task_type}"
            assert api_name in capabilities, f"Missing API name: {api_name}"

    def test_system_prompt_includes_task_api_mapping(self) -> None:
        """Verify system prompt includes task_api_mapping."""
        prompt = _build_task_breakdown_system_prompt()

        # The system prompt should include the capabilities which includes mapping
        assert "タスク種別ごとの推奨API" in prompt


@pytest.mark.acceptance
class TestFileReaderAgentRecommendation:
    """Acceptance tests requiring live services."""

    EXPERT_AGENT_URL = "http://localhost:8004"

    @pytest.fixture(autouse=True)
    def check_services_running(self) -> None:
        """Check that required services are running."""
        try:
            response = requests.get(f"{self.EXPERT_AGENT_URL}/health", timeout=5)
            assert response.status_code == 200
        except requests.exceptions.ConnectionError:
            pytest.skip(
                "expertAgent is not running. "
                "Run: ./scripts/dev-hybrid.sh or make dev-all"
            )

    def test_pdf_reading_task_recommends_file_reader_agent(self) -> None:
        """Verify that a PDF reading task recommends File Reader Agent.

        This is the key acceptance test for Issue #305.

        Uses the async job-generator API:
        1. POST /v1/job-generator to start job creation
        2. Poll /v1/jobs/{job_id}/status until task_breakdown is available
        3. Check that File Reader Agent is in recommended_apis

        Note: We check task_breakdown from status (available during processing)
        rather than waiting for full completion (which includes workflow generation).
        """
        # Test requirement with PDF reading
        requirement = """
        以下のPDFファイルを読み取り、内容を要約してください：
        - /path/to/document.pdf
        - /path/to/report.pdf

        要約結果をJSON形式で出力してください。
        """

        # Step 1: Start async job generation
        response = requests.post(
            f"{self.EXPERT_AGENT_URL}/v1/job-generator",
            json={"user_requirement": requirement},
            timeout=30,
        )

        assert response.status_code == 200, f"Job start failed: {response.text}"
        data = response.json()
        job_id = data.get("job_id")
        assert job_id, f"No job_id in response: {data}"

        # Step 2: Poll until task_breakdown is available (max 180 seconds)
        # Task analysis phase involves LLM calls which can take time.
        # task_breakdown becomes available during the workflow_generation phase.
        max_wait = 180
        poll_interval = 3
        elapsed = 0
        task_breakdown = None
        last_phase = ""

        while elapsed < max_wait:
            status_response = requests.get(
                f"{self.EXPERT_AGENT_URL}/v1/jobs/{job_id}/status",
                timeout=10,
            )
            assert status_response.status_code == 200, (
                f"Status check failed: {status_response.text}"
            )

            status_data = status_response.json()
            status = status_data.get("status")
            phase = status_data.get("phase", "")

            # Log phase changes for debugging
            if phase != last_phase:
                print(f"Phase changed: {last_phase} -> {phase}")
                last_phase = phase

            # Check if failed
            if status == "failed":
                pytest.fail(
                    f"Job failed: {status_data.get('error_message', 'Unknown error')}"
                )

            # Check if task_breakdown is available (either from status or completed)
            task_breakdown = status_data.get("task_breakdown")
            if task_breakdown and len(task_breakdown) > 0:
                print(f"Task breakdown found in phase: {phase}")
                break

            # Also check result.task_masters if completed
            if status == "completed":
                result = status_data.get("result", {})
                if result:
                    task_breakdown = result.get("task_masters", [])
                    if task_breakdown:
                        print("Task breakdown found in completed result")
                        break

            time.sleep(poll_interval)
            elapsed += poll_interval

        assert task_breakdown is not None and len(task_breakdown) > 0, (
            f"Task breakdown not available within {max_wait} seconds. "
            f"Last phase: {last_phase}"
        )

        # Step 3: Check task breakdown for File Reader Agent recommendation
        file_reader_recommended = False
        found_apis = []

        for task in task_breakdown:
            recommended_apis = task.get("recommended_apis", [])
            for api in recommended_apis:
                # Handle various formats: string, dict with api_name, etc.
                if isinstance(api, str):
                    api_name = api
                    endpoint = ""
                elif isinstance(api, dict):
                    api_name = api.get("api_name", api.get("name", ""))
                    endpoint = api.get("endpoint", "")
                else:
                    api_name = getattr(api, "api_name", "")
                    endpoint = getattr(api, "endpoint", "")

                found_apis.append({"api_name": api_name, "endpoint": endpoint})

                if (
                    "File Reader" in api_name
                    or "file_reader" in api_name.lower()
                    or "file_reader" in endpoint
                    or "/v1/aiagent/utility/file_reader" in endpoint
                ):
                    file_reader_recommended = True

        # This is the key assertion - File Reader Agent should be recommended
        assert file_reader_recommended, (
            f"File Reader Agent was not recommended for PDF reading task.\n"
            f"Found APIs: {found_apis}\n"
            f"Task breakdown: {task_breakdown}"
        )
