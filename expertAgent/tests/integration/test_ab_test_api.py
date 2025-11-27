"""Integration tests for AB Test API endpoints.

Tests for Issue #178: AB Test Infrastructure Implementation.
This module tests the AB test REST API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


class TestABTestEndpoints:
    """Test AB test API endpoints."""

    @pytest.mark.integration
    def test_create_ab_test(self, client: TestClient):
        """Test creating a new AB test."""
        payload = {
            "name": "Test Experiment",
            "description": "Testing prompt variations",
            "variants": [
                {"name": "control", "prompt_version": "v1.0", "weight": 0.5},
                {"name": "treatment", "prompt_version": "v2.0", "weight": 0.5},
            ],
        }

        response = client.post("/v1/ab-tests", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["test"]["name"] == "Test Experiment"
        assert len(data["test"]["variants"]) == 2
        assert data["test"]["status"] == "draft"
        assert "id" in data["test"]

    @pytest.mark.integration
    def test_create_ab_test_validation_error(self, client: TestClient):
        """Test validation error for invalid AB test."""
        # Missing required variants
        payload = {"name": "Invalid Test", "variants": []}

        response = client.post("/v1/ab-tests", json=payload)

        assert response.status_code == 422

    @pytest.mark.integration
    def test_create_ab_test_single_variant(self, client: TestClient):
        """Test validation error for single variant."""
        payload = {
            "name": "Single Variant",
            "variants": [{"name": "only_one", "prompt_version": "v1.0"}],
        }

        response = client.post("/v1/ab-tests", json=payload)

        assert response.status_code == 422

    @pytest.mark.integration
    def test_list_ab_tests(self, client: TestClient):
        """Test listing AB tests."""
        # Create a test first
        payload = {
            "name": "List Test",
            "variants": [
                {"name": "a", "prompt_version": "v1.0"},
                {"name": "b", "prompt_version": "v2.0"},
            ],
        }
        client.post("/v1/ab-tests", json=payload)

        response = client.get("/v1/ab-tests")

        assert response.status_code == 200
        data = response.json()
        assert "tests" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.integration
    def test_list_ab_tests_with_filter(self, client: TestClient):
        """Test listing AB tests with status filter."""
        response = client.get("/v1/ab-tests?status=draft")

        assert response.status_code == 200
        data = response.json()
        assert "tests" in data
        # All returned tests should be draft status
        for test in data["tests"]:
            assert test["status"] == "draft"

    @pytest.mark.integration
    def test_list_ab_tests_pagination(self, client: TestClient):
        """Test listing AB tests with pagination."""
        response = client.get("/v1/ab-tests?limit=5&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tests"]) <= 5

    @pytest.mark.integration
    def test_get_ab_test(self, client: TestClient):
        """Test getting a specific AB test."""
        # Create a test first
        create_payload = {
            "name": "Get Test",
            "variants": [
                {"name": "a", "prompt_version": "v1.0"},
                {"name": "b", "prompt_version": "v2.0"},
            ],
        }
        create_response = client.post("/v1/ab-tests", json=create_payload)
        test_id = create_response.json()["test"]["id"]

        response = client.get(f"/v1/ab-tests/{test_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["test"]["id"] == test_id
        assert data["test"]["name"] == "Get Test"

    @pytest.mark.integration
    def test_get_ab_test_not_found(self, client: TestClient):
        """Test getting non-existent AB test."""
        response = client.get("/v1/ab-tests/non-existent-id")

        assert response.status_code == 404

    @pytest.mark.integration
    def test_update_ab_test_status(self, client: TestClient):
        """Test updating AB test status."""
        # Create a test first
        create_payload = {
            "name": "Status Update Test",
            "variants": [
                {"name": "a", "prompt_version": "v1.0"},
                {"name": "b", "prompt_version": "v2.0"},
            ],
        }
        create_response = client.post("/v1/ab-tests", json=create_payload)
        test_id = create_response.json()["test"]["id"]

        # Update status
        update_payload = {"status": "running"}
        response = client.put(f"/v1/ab-tests/{test_id}/status", json=update_payload)

        assert response.status_code == 200
        data = response.json()
        assert data["old_status"] == "draft"
        assert data["new_status"] == "running"

    @pytest.mark.integration
    def test_delete_ab_test(self, client: TestClient):
        """Test deleting an AB test."""
        # Create a test first
        create_payload = {
            "name": "Delete Test",
            "variants": [
                {"name": "a", "prompt_version": "v1.0"},
                {"name": "b", "prompt_version": "v2.0"},
            ],
        }
        create_response = client.post("/v1/ab-tests", json=create_payload)
        test_id = create_response.json()["test"]["id"]

        # Delete
        response = client.delete(f"/v1/ab-tests/{test_id}")

        assert response.status_code == 204

        # Verify deleted
        get_response = client.get(f"/v1/ab-tests/{test_id}")
        assert get_response.status_code == 404

    @pytest.mark.integration
    def test_delete_ab_test_not_found(self, client: TestClient):
        """Test deleting non-existent AB test."""
        response = client.delete("/v1/ab-tests/non-existent-id")

        assert response.status_code == 404


class TestVariantAssignmentEndpoints:
    """Test variant assignment API endpoints."""

    @pytest.mark.integration
    def test_get_or_create_assignment(self, client: TestClient):
        """Test creating variant assignment."""
        # Create a test first
        create_payload = {
            "name": "Assignment Test",
            "variants": [
                {"name": "control", "prompt_version": "v1.0", "weight": 0.5},
                {"name": "treatment", "prompt_version": "v2.0", "weight": 0.5},
            ],
        }
        create_response = client.post("/v1/ab-tests", json=create_payload)
        test_id = create_response.json()["test"]["id"]

        # Get assignment
        assignment_payload = {"session_id": "test-session-123"}
        response = client.post(
            f"/v1/ab-tests/{test_id}/assignment", json=assignment_payload
        )

        assert response.status_code == 200
        data = response.json()
        assert data["is_new"] is True
        assert data["assignment"]["session_id"] == "test-session-123"
        assert data["assignment"]["variant_name"] in ["control", "treatment"]

    @pytest.mark.integration
    def test_assignment_idempotency(self, client: TestClient):
        """Test that repeated assignment returns same variant."""
        # Create a test first
        create_payload = {
            "name": "Idempotency Test",
            "variants": [
                {"name": "control", "prompt_version": "v1.0"},
                {"name": "treatment", "prompt_version": "v2.0"},
            ],
        }
        create_response = client.post("/v1/ab-tests", json=create_payload)
        test_id = create_response.json()["test"]["id"]

        # First assignment
        assignment_payload = {"session_id": "idempotent-session"}
        response1 = client.post(
            f"/v1/ab-tests/{test_id}/assignment", json=assignment_payload
        )
        assert response1.status_code == 200
        first_variant = response1.json()["assignment"]["variant_name"]
        assert response1.json()["is_new"] is True

        # Second assignment (same session)
        response2 = client.post(
            f"/v1/ab-tests/{test_id}/assignment", json=assignment_payload
        )
        assert response2.status_code == 200
        assert response2.json()["is_new"] is False
        assert response2.json()["assignment"]["variant_name"] == first_variant

    @pytest.mark.integration
    def test_get_existing_assignment(self, client: TestClient):
        """Test getting existing assignment via GET endpoint."""
        # Create a test first
        create_payload = {
            "name": "Get Assignment Test",
            "variants": [
                {"name": "control", "prompt_version": "v1.0"},
                {"name": "treatment", "prompt_version": "v2.0"},
            ],
        }
        create_response = client.post("/v1/ab-tests", json=create_payload)
        test_id = create_response.json()["test"]["id"]

        # Create assignment first
        session_id = "existing-session"
        assignment_payload = {"session_id": session_id}
        client.post(f"/v1/ab-tests/{test_id}/assignment", json=assignment_payload)

        # Get existing assignment
        response = client.get(f"/v1/ab-tests/{test_id}/assignment/{session_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["assignment"]["session_id"] == session_id

    @pytest.mark.integration
    def test_get_assignment_not_found(self, client: TestClient):
        """Test getting non-existent assignment."""
        # Create a test first
        create_payload = {
            "name": "Not Found Test",
            "variants": [
                {"name": "a", "prompt_version": "v1.0"},
                {"name": "b", "prompt_version": "v2.0"},
            ],
        }
        create_response = client.post("/v1/ab-tests", json=create_payload)
        test_id = create_response.json()["test"]["id"]

        response = client.get(f"/v1/ab-tests/{test_id}/assignment/non-existent")

        assert response.status_code == 404


class TestMetricsEndpoints:
    """Test metrics collection API endpoints."""

    @pytest.mark.integration
    def test_collect_metric(self, client: TestClient):
        """Test collecting a metric."""
        # Create test and assignment
        create_payload = {
            "name": "Metrics Test",
            "variants": [
                {"name": "control", "prompt_version": "v1.0"},
                {"name": "treatment", "prompt_version": "v2.0"},
            ],
        }
        create_response = client.post("/v1/ab-tests", json=create_payload)
        test_id = create_response.json()["test"]["id"]

        session_id = "metrics-session"
        client.post(
            f"/v1/ab-tests/{test_id}/assignment", json={"session_id": session_id}
        )

        # Collect metric
        response = client.post(
            f"/v1/ab-tests/{test_id}/metrics",
            params={
                "session_id": session_id,
                "value": 0.85,
                "metric_name": "quality_score",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["data_point"]["value"] == 0.85

    @pytest.mark.integration
    def test_collect_metric_no_assignment(self, client: TestClient):
        """Test collecting metric without assignment."""
        # Create test without assignment
        create_payload = {
            "name": "No Assignment Metrics Test",
            "variants": [
                {"name": "control", "prompt_version": "v1.0"},
                {"name": "treatment", "prompt_version": "v2.0"},
            ],
        }
        create_response = client.post("/v1/ab-tests", json=create_payload)
        test_id = create_response.json()["test"]["id"]

        # Try to collect metric without assignment
        response = client.post(
            f"/v1/ab-tests/{test_id}/metrics",
            params={
                "session_id": "unassigned-session",
                "value": 0.85,
            },
        )

        assert response.status_code == 400


class TestReportEndpoints:
    """Test report generation API endpoints."""

    @pytest.mark.integration
    def test_generate_report(self, client: TestClient):
        """Test generating AB test report."""
        # Create test
        create_payload = {
            "name": "Report Test",
            "variants": [
                {"name": "control", "prompt_version": "v1.0"},
                {"name": "treatment", "prompt_version": "v2.0"},
            ],
        }
        create_response = client.post("/v1/ab-tests", json=create_payload)
        test_id = create_response.json()["test"]["id"]

        # Generate report (even without data)
        response = client.post(f"/v1/ab-tests/{test_id}/report")

        assert response.status_code == 200
        data = response.json()
        assert data["test_id"] == test_id
        assert "metrics" in data
        assert "warning_messages" in data

    @pytest.mark.integration
    def test_generate_report_with_data(self, client: TestClient):
        """Test generating report with collected data."""
        # Create test
        create_payload = {
            "name": "Report With Data",
            "variants": [
                {"name": "control", "prompt_version": "v1.0", "weight": 0.5},
                {"name": "treatment", "prompt_version": "v2.0", "weight": 0.5},
            ],
        }
        create_response = client.post("/v1/ab-tests", json=create_payload)
        test_id = create_response.json()["test"]["id"]

        # Create assignments and metrics for multiple sessions
        for i in range(40):
            session_id = f"report-session-{i}"
            # Assign variant
            client.post(
                f"/v1/ab-tests/{test_id}/assignment",
                json={"session_id": session_id},
            )
            # Collect metric
            client.post(
                f"/v1/ab-tests/{test_id}/metrics",
                params={
                    "session_id": session_id,
                    "value": 0.70 + (i % 20) * 0.01,  # Varied scores
                },
            )

        # Generate report
        response = client.post(
            f"/v1/ab-tests/{test_id}/report",
            json={"minimum_sample_size": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["metrics"]) >= 1

    @pytest.mark.integration
    def test_generate_report_not_found(self, client: TestClient):
        """Test generating report for non-existent test."""
        response = client.post("/v1/ab-tests/non-existent/report")

        assert response.status_code == 404

    @pytest.mark.integration
    def test_generate_report_custom_params(self, client: TestClient):
        """Test generating report with custom parameters."""
        # Create test
        create_payload = {
            "name": "Custom Report Test",
            "variants": [
                {"name": "control", "prompt_version": "v1.0"},
                {"name": "treatment", "prompt_version": "v2.0"},
            ],
        }
        create_response = client.post("/v1/ab-tests", json=create_payload)
        test_id = create_response.json()["test"]["id"]

        # Generate report with custom params
        report_params = {
            "metric_name": "latency",
            "significance_level": 0.01,
            "minimum_sample_size": 50,
        }
        response = client.post(f"/v1/ab-tests/{test_id}/report", json=report_params)

        assert response.status_code == 200


class TestAPIEdgeCases:
    """Test API edge cases and error handling."""

    @pytest.mark.integration
    def test_create_test_empty_name(self, client: TestClient):
        """Test creating test with empty name."""
        payload = {
            "name": "",
            "variants": [
                {"name": "a", "prompt_version": "v1.0"},
                {"name": "b", "prompt_version": "v2.0"},
            ],
        }

        response = client.post("/v1/ab-tests", json=payload)

        assert response.status_code == 422

    @pytest.mark.integration
    def test_create_test_long_name(self, client: TestClient):
        """Test creating test with very long name."""
        payload = {
            "name": "x" * 300,  # Exceeds 255 limit
            "variants": [
                {"name": "a", "prompt_version": "v1.0"},
                {"name": "b", "prompt_version": "v2.0"},
            ],
        }

        response = client.post("/v1/ab-tests", json=payload)

        assert response.status_code == 422

    @pytest.mark.integration
    def test_invalid_status_value(self, client: TestClient):
        """Test updating with invalid status value."""
        # Create a test first
        create_payload = {
            "name": "Invalid Status Test",
            "variants": [
                {"name": "a", "prompt_version": "v1.0"},
                {"name": "b", "prompt_version": "v2.0"},
            ],
        }
        create_response = client.post("/v1/ab-tests", json=create_payload)
        test_id = create_response.json()["test"]["id"]

        # Try invalid status
        response = client.put(
            f"/v1/ab-tests/{test_id}/status", json={"status": "invalid_status"}
        )

        assert response.status_code == 422

    @pytest.mark.integration
    def test_health_check(self, client: TestClient):
        """Test health check endpoint still works."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
