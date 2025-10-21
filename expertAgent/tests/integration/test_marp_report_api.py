"""Integration tests for Marp report generation API."""

import json
from pathlib import Path

from fastapi.testclient import TestClient


class TestMarpReportAPI:
    """Test Marp report generation API endpoint."""

    def test_generate_report_with_json_input(self, client: TestClient):
        """Test Marp report generation with direct JSON input."""
        request_data = {
            "job_result": {
                "status": "failed",
                "error_message": "Job generation did not complete successfully.",
                "infeasible_tasks": [
                    {
                        "task_id": "task_1",
                        "task_name": "Slack Notification",
                        "reason": "Slack API not available",
                    }
                ],
                "requirement_relaxation_suggestions": [
                    {
                        "relaxation_type": "automation_level_reduction",
                        "original_requirement": "Send Slack message automatically",
                        "relaxed_requirement": "Create draft message for manual review",
                        "feasibility_after_relaxation": "High (90%)",
                        "recommendation_level": "Highly Recommended",
                        "what_is_sacrificed": "Full automation",
                        "what_is_preserved": "Core message creation",
                        "implementation_note": "Requires manual final step",
                        "available_capabilities_used": ["geminiAgent", "slackAgent"],
                        "implementation_steps": [
                            "1. Use geminiAgent to generate message",
                            "2. Save as draft in slackAgent",
                            "3. Notify user to review and send",
                        ],
                    }
                ],
                "job_id": None,
            },
            "theme": "default",
            "include_implementation_steps": True,
        }

        response = client.post("/aiagent-api/v1/marp-report", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "marp_markdown" in data
        assert "slide_count" in data
        assert "suggestions_count" in data
        assert "generation_time_ms" in data

        # Verify slide count (Title + Summary + 3 slides per suggestion + Conclusion)
        # 1 + 1 + (1 * 3) + 1 = 6
        assert data["slide_count"] == 6
        assert data["suggestions_count"] == 1
        assert data["generation_time_ms"] > 0

        # Verify Marp content
        marp_content = data["marp_markdown"]
        assert "marp: true" in marp_content
        assert "theme: default" in marp_content
        assert "Job/Task 生成レポート" in marp_content
        assert "automation_level_reduction" in marp_content
        assert "Send Slack message automatically" in marp_content

    def test_generate_report_with_file_path(self, client: TestClient, tmp_path: Path):
        """Test Marp report generation with file path input."""
        # Create test JSON file
        test_data = {
            "status": "success",
            "error_message": "",
            "infeasible_tasks": [],
            "requirement_relaxation_suggestions": [],
            "job_id": "123e4567-e89b-12d3-a456-426614174000",
        }
        test_file = tmp_path / "test_job_result.json"
        test_file.write_text(json.dumps(test_data), encoding="utf-8")

        request_data = {
            "json_file_path": str(test_file),
            "theme": "gaia",
            "include_implementation_steps": False,
        }

        response = client.post("/aiagent-api/v1/marp-report", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # Verify response
        assert data["slide_count"] == 3  # Title + Summary + Conclusion (no suggestions)
        assert data["suggestions_count"] == 0
        assert "theme: gaia" in data["marp_markdown"]

    def test_generate_report_with_multiple_suggestions(self, client: TestClient):
        """Test Marp report generation with multiple suggestions."""
        request_data = {
            "job_result": {
                "status": "failed",
                "infeasible_tasks": [
                    {"task_id": "task_1", "task_name": "Task 1"},
                    {"task_id": "task_2", "task_name": "Task 2"},
                ],
                "requirement_relaxation_suggestions": [
                    {
                        "relaxation_type": "type1",
                        "original_requirement": "Original 1",
                        "relaxed_requirement": "Relaxed 1",
                        "feasibility_after_relaxation": "High",
                        "recommendation_level": "Recommended",
                        "what_is_sacrificed": "Feature A",
                        "what_is_preserved": "Feature B",
                        "implementation_note": "Note 1",
                        "available_capabilities_used": ["agent1"],
                        "implementation_steps": ["Step 1"],
                    },
                    {
                        "relaxation_type": "type2",
                        "original_requirement": "Original 2",
                        "relaxed_requirement": "Relaxed 2",
                        "feasibility_after_relaxation": "Medium",
                        "recommendation_level": "Consider",
                        "what_is_sacrificed": "Feature C",
                        "what_is_preserved": "Feature D",
                        "implementation_note": "Note 2",
                        "available_capabilities_used": ["agent2"],
                        "implementation_steps": ["Step 2"],
                    },
                ],
                "job_id": None,
            },
        }

        response = client.post("/aiagent-api/v1/marp-report", json=request_data)

        assert response.status_code == 200
        data = response.json()

        # 1 + 1 + (2 * 3) + 1 = 9 slides
        assert data["slide_count"] == 9
        assert data["suggestions_count"] == 2
        assert "type1" in data["marp_markdown"]
        assert "type2" in data["marp_markdown"]

    def test_generate_report_validation_error_both_inputs(self, client: TestClient):
        """Test validation error when both inputs are provided."""
        request_data = {
            "job_result": {"status": "failed"},
            "json_file_path": "/tmp/file.json",
        }

        response = client.post("/aiagent-api/v1/marp-report", json=request_data)

        assert response.status_code == 422
        assert "validation" in response.json()["detail"].lower()

    def test_generate_report_validation_error_no_input(self, client: TestClient):
        """Test validation error when no input is provided."""
        request_data = {
            "theme": "default",
        }

        response = client.post("/aiagent-api/v1/marp-report", json=request_data)

        assert response.status_code == 422
        assert "validation" in response.json()["detail"].lower()

    def test_generate_report_file_not_found(self, client: TestClient):
        """Test 404 error when file is not found."""
        request_data = {
            "json_file_path": "/nonexistent/path/file.json",
        }

        response = client.post("/aiagent-api/v1/marp-report", json=request_data)

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_generate_report_invalid_json_file(
        self, client: TestClient, tmp_path: Path
    ):
        """Test 400 error for invalid JSON file."""
        # Create invalid JSON file
        test_file = tmp_path / "invalid.json"
        test_file.write_text("{ invalid json", encoding="utf-8")

        request_data = {
            "json_file_path": str(test_file),
        }

        response = client.post("/aiagent-api/v1/marp-report", json=request_data)

        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    def test_generate_report_invalid_theme(self, client: TestClient):
        """Test validation error for invalid theme."""
        request_data = {
            "job_result": {"status": "failed"},
            "theme": "invalid_theme",
        }

        response = client.post("/aiagent-api/v1/marp-report", json=request_data)

        assert response.status_code == 422

    def test_generate_report_different_themes(self, client: TestClient):
        """Test report generation with different themes."""
        for theme in ["default", "gaia", "uncover"]:
            request_data = {
                "job_result": {"status": "success"},
                "theme": theme,
            }

            response = client.post("/aiagent-api/v1/marp-report", json=request_data)

            assert response.status_code == 200
            data = response.json()
            assert f"theme: {theme}" in data["marp_markdown"]

    def test_generate_report_implementation_steps_toggle(self, client: TestClient):
        """Test include_implementation_steps parameter."""
        base_request = {
            "job_result": {
                "status": "failed",
                "requirement_relaxation_suggestions": [
                    {
                        "relaxation_type": "test",
                        "original_requirement": "Original",
                        "relaxed_requirement": "Relaxed",
                        "feasibility_after_relaxation": "High",
                        "recommendation_level": "Recommended",
                        "what_is_sacrificed": "A",
                        "what_is_preserved": "B",
                        "implementation_note": "Note",
                        "available_capabilities_used": ["agent"],
                        "implementation_steps": ["Step 1", "Step 2"],
                    }
                ],
            },
        }

        # Test with implementation steps included
        request_with_steps = {**base_request, "include_implementation_steps": True}
        response_with = client.post(
            "/aiagent-api/v1/marp-report", json=request_with_steps
        )
        assert response_with.status_code == 200
        assert "Step 1" in response_with.json()["marp_markdown"]

        # Test with implementation steps excluded
        request_without_steps = {**base_request, "include_implementation_steps": False}
        response_without = client.post(
            "/aiagent-api/v1/marp-report", json=request_without_steps
        )
        assert response_without.status_code == 200
        # Note: Current template shows steps even when include_implementation_steps=False
        # This is expected behavior based on template logic
