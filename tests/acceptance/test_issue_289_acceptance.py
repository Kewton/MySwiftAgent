"""
L3 Acceptance Tests for Issue #289: Workbench List/Detail Screens
myAgentDesk (SvelteKit frontend)

This test verifies:
1. Frontend page endpoints (HTML responses)
2. API endpoints (JSON responses with structure validation)
3. Data creation and retrieval
4. Security (project mismatch handling)

Prerequisites:
- myAgentDesk dev server running on http://localhost:5173
- Database seeded with test data (npm run db:seed)
"""

import pytest
import httpx
from typing import Any

# Base URL for myAgentDesk
BASE_URL = "http://localhost:5173"
API_BASE_URL = f"{BASE_URL}/api"

# Test data (based on db-seed.ts)
TEST_PROJECT_ID = "proj_001"
TEST_WORKBENCH_ID = "wb_001"
INVALID_WORKBENCH_ID = "invalid_id"
WRONG_PROJECT_ID = "proj_002"  # wb_001 belongs to proj_001, not proj_002


@pytest.fixture
def client() -> httpx.Client:
    """Create HTTP client for testing."""
    return httpx.Client(base_url=BASE_URL, timeout=10.0)


@pytest.fixture
def api_client() -> httpx.Client:
    """Create HTTP client for API testing."""
    return httpx.Client(base_url=API_BASE_URL, timeout=10.0)


# =============================================================================
# Page Tests (HTML responses)
# =============================================================================


class TestWorkbenchListPage:
    """Tests for the workbench list page (HTML)."""

    def test_workbench_list_returns_200(self, client: httpx.Client) -> None:
        """Workbench list page should return HTTP 200."""
        response = client.get(f"/projects/{TEST_PROJECT_ID}/workbenches")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_workbench_list_contains_title(self, client: httpx.Client) -> None:
        """Workbench list page should contain 'Workbenches' title."""
        response = client.get(f"/projects/{TEST_PROJECT_ID}/workbenches")
        assert "Workbenches" in response.text, "Page should contain 'Workbenches' title"

    def test_workbench_list_contains_workbench_cards(
        self, client: httpx.Client
    ) -> None:
        """Workbench list page should contain workbench cards."""
        response = client.get(f"/projects/{TEST_PROJECT_ID}/workbenches")
        assert (
            'data-testid="workbench-card"' in response.text
        ), "Page should contain workbench cards"

    def test_status_filter_active_returns_200(self, client: httpx.Client) -> None:
        """Filtering by active status should return HTTP 200."""
        response = client.get(
            f"/projects/{TEST_PROJECT_ID}/workbenches?status=active"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_status_filter_draft_returns_200(self, client: httpx.Client) -> None:
        """Filtering by draft status should return HTTP 200."""
        response = client.get(f"/projects/{TEST_PROJECT_ID}/workbenches?status=draft")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_status_filter_archived_returns_200(self, client: httpx.Client) -> None:
        """Filtering by archived status should return HTTP 200."""
        response = client.get(
            f"/projects/{TEST_PROJECT_ID}/workbenches?status=archived"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"


class TestWorkbenchDetailPage:
    """Tests for the workbench detail page (HTML)."""

    def test_workbench_detail_returns_200(self, client: httpx.Client) -> None:
        """Valid workbench detail page should return HTTP 200."""
        response = client.get(
            f"/projects/{TEST_PROJECT_ID}/workbenches/{TEST_WORKBENCH_ID}"
        )
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    def test_workbench_detail_contains_workbench_name(
        self, client: httpx.Client
    ) -> None:
        """Workbench detail page should contain the workbench name."""
        response = client.get(
            f"/projects/{TEST_PROJECT_ID}/workbenches/{TEST_WORKBENCH_ID}"
        )
        assert (
            "Email Auto Reply" in response.text
        ), "Page should contain workbench name 'Email Auto Reply'"

    def test_invalid_workbench_id_returns_404(self, client: httpx.Client) -> None:
        """Invalid workbench ID should return HTTP 404."""
        response = client.get(
            f"/projects/{TEST_PROJECT_ID}/workbenches/{INVALID_WORKBENCH_ID}"
        )
        assert response.status_code == 404, f"Expected 404, got {response.status_code}"

    def test_project_mismatch_returns_404(self, client: httpx.Client) -> None:
        """
        Accessing a workbench that belongs to a different project should return 404.
        This is a security test - wb_001 belongs to proj_001, not proj_002.
        """
        response = client.get(
            f"/projects/{WRONG_PROJECT_ID}/workbenches/{TEST_WORKBENCH_ID}"
        )
        assert response.status_code == 404, (
            f"Expected 404 for project mismatch, got {response.status_code}. "
            "This is a security vulnerability if not returning 404."
        )


# =============================================================================
# API Tests (JSON responses with structure validation)
# =============================================================================


class TestWorkbenchListAPI:
    """Tests for the workbench list API endpoint (JSON)."""

    def test_api_workbench_list_returns_json(self, api_client: httpx.Client) -> None:
        """API should return JSON response."""
        response = api_client.get(f"/projects/{TEST_PROJECT_ID}/workbenches")
        assert response.status_code == 200
        assert response.headers.get("content-type", "").startswith("application/json")

    def test_api_workbench_list_structure(self, api_client: httpx.Client) -> None:
        """API response should have correct structure."""
        response = api_client.get(f"/projects/{TEST_PROJECT_ID}/workbenches")
        data: dict[str, Any] = response.json()

        # Verify top-level structure
        assert "workbenches" in data, "Response should contain 'workbenches' key"
        assert "statusCounts" in data, "Response should contain 'statusCounts' key"
        assert "currentFilter" in data, "Response should contain 'currentFilter' key"

        # Verify workbenches is a list
        assert isinstance(data["workbenches"], list), "'workbenches' should be a list"

        # Verify at least one workbench exists
        assert len(data["workbenches"]) > 0, "Should have at least one workbench"

    def test_api_workbench_item_structure(self, api_client: httpx.Client) -> None:
        """Each workbench item should have required fields."""
        response = api_client.get(f"/projects/{TEST_PROJECT_ID}/workbenches")
        data: dict[str, Any] = response.json()

        workbench = data["workbenches"][0]

        # Required fields
        required_fields = ["id", "name", "status", "createdAt", "updatedAt"]
        for field in required_fields:
            assert field in workbench, f"Workbench should have '{field}' field"

        # ID format check
        assert workbench["id"].startswith("wb_"), "Workbench ID should start with 'wb_'"

        # Status validation
        valid_statuses = ["draft", "active", "archived"]
        assert (
            workbench["status"] in valid_statuses
        ), f"Status should be one of {valid_statuses}"

    def test_api_workbench_stats_fields(self, api_client: httpx.Client) -> None:
        """Workbench items should include statistical fields."""
        response = api_client.get(f"/projects/{TEST_PROJECT_ID}/workbenches")
        data: dict[str, Any] = response.json()

        workbench = data["workbenches"][0]

        # Stats fields (from N+1 optimized query)
        stats_fields = ["runCount", "scheduleCount"]
        for field in stats_fields:
            assert field in workbench, f"Workbench should have '{field}' stat field"
            assert isinstance(
                workbench[field], int
            ), f"'{field}' should be an integer"

    def test_api_status_counts_structure(self, api_client: httpx.Client) -> None:
        """Status counts should have all status types."""
        response = api_client.get(f"/projects/{TEST_PROJECT_ID}/workbenches")
        data: dict[str, Any] = response.json()

        status_counts = data["statusCounts"]

        # All status types should be present
        required_counts = ["all", "active", "draft", "archived"]
        for count_type in required_counts:
            assert count_type in status_counts, f"statusCounts should have '{count_type}'"
            assert isinstance(
                status_counts[count_type], int
            ), f"'{count_type}' count should be an integer"

        # 'all' should equal sum of other counts
        expected_all = (
            status_counts["active"]
            + status_counts["draft"]
            + status_counts["archived"]
        )
        assert (
            status_counts["all"] == expected_all
        ), "'all' count should equal sum of status counts"

    def test_api_filter_active_returns_only_active(
        self, api_client: httpx.Client
    ) -> None:
        """Filtering by active should return only active workbenches."""
        response = api_client.get(f"/projects/{TEST_PROJECT_ID}/workbenches?status=active")
        data: dict[str, Any] = response.json()

        assert data["currentFilter"] == "active"

        for wb in data["workbenches"]:
            assert (
                wb["status"] == "active"
            ), f"Expected only active workbenches, got {wb['status']}"

    def test_api_filter_draft_returns_only_draft(
        self, api_client: httpx.Client
    ) -> None:
        """Filtering by draft should return only draft workbenches."""
        response = api_client.get(f"/projects/{TEST_PROJECT_ID}/workbenches?status=draft")
        data: dict[str, Any] = response.json()

        assert data["currentFilter"] == "draft"

        for wb in data["workbenches"]:
            assert (
                wb["status"] == "draft"
            ), f"Expected only draft workbenches, got {wb['status']}"

    def test_api_invalid_status_filter_returns_400(
        self, api_client: httpx.Client
    ) -> None:
        """Invalid status filter should return 400 Bad Request."""
        response = api_client.get(
            f"/projects/{TEST_PROJECT_ID}/workbenches?status=invalid_status"
        )
        assert response.status_code == 400, f"Expected 400, got {response.status_code}"


# =============================================================================
# API Create Workbench Tests (POST)
# =============================================================================


class TestWorkbenchCreateAPI:
    """Tests for the workbench creation API endpoint."""

    def test_api_create_workbench_success(self, api_client: httpx.Client) -> None:
        """Creating a workbench should return 201 with workbench data."""
        payload = {
            "name": "Test Workbench from Acceptance Test",
            "description": "Created by automated test"
        }

        response = api_client.post(
            f"/projects/{TEST_PROJECT_ID}/workbenches",
            json=payload
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        data: dict[str, Any] = response.json()
        assert "workbench" in data, "Response should contain 'workbench' key"
        assert "message" in data, "Response should contain 'message' key"

        workbench = data["workbench"]
        assert workbench["name"] == payload["name"]
        assert workbench["description"] == payload["description"]
        assert workbench["status"] == "draft", "New workbench should have 'draft' status"
        assert workbench["projectId"] == TEST_PROJECT_ID

    def test_api_create_workbench_minimal(self, api_client: httpx.Client) -> None:
        """Creating a workbench with only name should succeed."""
        payload = {"name": "Minimal Workbench"}

        response = api_client.post(
            f"/projects/{TEST_PROJECT_ID}/workbenches",
            json=payload
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}"

        data: dict[str, Any] = response.json()
        workbench = data["workbench"]
        assert workbench["name"] == payload["name"]
        assert workbench["description"] is None, "Description should be null when not provided"

    def test_api_create_workbench_empty_name_fails(
        self, api_client: httpx.Client
    ) -> None:
        """Creating a workbench without name should return 400."""
        payload: dict[str, str] = {"description": "No name provided"}

        response = api_client.post(
            f"/projects/{TEST_PROJECT_ID}/workbenches",
            json=payload
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"

    def test_api_create_workbench_whitespace_name_fails(
        self, api_client: httpx.Client
    ) -> None:
        """Creating a workbench with whitespace-only name should return 400."""
        payload = {"name": "   "}

        response = api_client.post(
            f"/projects/{TEST_PROJECT_ID}/workbenches",
            json=payload
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"

    def test_api_create_workbench_invalid_json_fails(
        self, api_client: httpx.Client
    ) -> None:
        """Creating a workbench with invalid JSON should return 400."""
        response = api_client.post(
            f"/projects/{TEST_PROJECT_ID}/workbenches",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"

    def test_api_create_workbench_appears_in_list(
        self, api_client: httpx.Client
    ) -> None:
        """Created workbench should appear in the list."""
        # Create a uniquely named workbench
        unique_name = f"Verification Test {__import__('time').time()}"
        payload = {"name": unique_name}

        create_response = api_client.post(
            f"/projects/{TEST_PROJECT_ID}/workbenches",
            json=payload
        )
        assert create_response.status_code == 201

        created_wb = create_response.json()["workbench"]
        created_id = created_wb["id"]

        # Verify it appears in the list
        list_response = api_client.get(f"/projects/{TEST_PROJECT_ID}/workbenches")
        data: dict[str, Any] = list_response.json()

        workbench_ids = [wb["id"] for wb in data["workbenches"]]
        assert created_id in workbench_ids, (
            f"Created workbench {created_id} should appear in list"
        )


# =============================================================================
# Service Health Tests
# =============================================================================


class TestServiceHealth:
    """Tests for service availability."""

    def test_myagentdesk_is_running(self, client: httpx.Client) -> None:
        """myAgentDesk dev server should be accessible."""
        response = client.get("/")
        assert (
            response.status_code == 200
        ), "myAgentDesk dev server is not running on port 5173"

    def test_projects_page_accessible(self, client: httpx.Client) -> None:
        """Projects page should be accessible."""
        response = client.get("/projects")
        assert response.status_code == 200, "Projects page should be accessible"

    def test_api_endpoint_accessible(self, api_client: httpx.Client) -> None:
        """API endpoint should be accessible."""
        response = api_client.get(f"/projects/{TEST_PROJECT_ID}/workbenches")
        assert response.status_code == 200, "API endpoint should be accessible"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
