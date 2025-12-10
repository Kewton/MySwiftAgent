"""Integration tests for Prompts API endpoints.

Issue #191: Prompts Management API Implementation
Tests for the FastAPI endpoints for prompts management.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI application."""
    return TestClient(app)


class TestPromptsEndpointsList:
    """Test GET /v1/prompts endpoint."""

    def test_get_prompts_returns_list(self, client: TestClient) -> None:
        """Test that GET /v1/prompts returns a list of prompts."""
        response = client.get("/v1/prompts")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)

    def test_get_prompts_returns_expected_fields(self, client: TestClient) -> None:
        """Test that each prompt item has expected fields."""
        response = client.get("/v1/prompts")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        if data["total"] > 0:
            item = data["items"][0]
            assert "id" in item
            assert "name" in item
            assert "current_version" in item
            assert "versions" in item

    def test_get_prompts_contains_known_prompts(self, client: TestClient) -> None:
        """Test that known prompts are included in the response."""
        response = client.get("/v1/prompts")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        prompt_ids = [item["id"] for item in data["items"]]

        # These are known prompts from the expertAgent/prompts directory
        expected_prompts = [
            "requirement_clarification",
            "workflow_generation",
            "evaluation",
        ]

        for expected in expected_prompts:
            assert expected in prompt_ids, f"Expected prompt '{expected}' not found"

    def test_get_prompts_response_content_type(self, client: TestClient) -> None:
        """Test that response has correct content type."""
        response = client.get("/v1/prompts")

        assert response.status_code == status.HTTP_200_OK
        assert "application/json" in response.headers.get("content-type", "")


class TestPromptsEndpointsDetail:
    """Test GET /v1/prompts/{prompt_id} endpoint."""

    def test_get_prompt_by_id(self, client: TestClient) -> None:
        """Test getting a specific prompt by ID."""
        response = client.get("/v1/prompts/requirement_clarification")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == "requirement_clarification"
        assert "name" in data
        assert "versions" in data
        assert "current_version" in data

    def test_get_prompt_not_found(self, client: TestClient) -> None:
        """Test that non-existent prompt returns 404."""
        response = client.get("/v1/prompts/nonexistent_prompt_xyz")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "detail" in data

    def test_get_prompt_includes_versions(self, client: TestClient) -> None:
        """Test that prompt detail includes version information."""
        response = client.get("/v1/prompts/requirement_clarification")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert "versions" in data
        assert isinstance(data["versions"], list)

        if len(data["versions"]) > 0:
            version = data["versions"][0]
            assert "id" in version
            assert "version" in version
            assert "content" in version

    def test_get_prompt_response_format(self, client: TestClient) -> None:
        """Test that prompt detail response has correct format."""
        response = client.get("/v1/prompts/workflow_generation")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify all expected fields
        expected_fields = [
            "id",
            "name",
            "current_version",
            "versions",
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    def test_get_multiple_prompts(self, client: TestClient) -> None:
        """Test getting multiple different prompts."""
        prompts_to_test = [
            "requirement_clarification",
            "workflow_generation",
            "evaluation",
        ]

        for prompt_id in prompts_to_test:
            response = client.get(f"/v1/prompts/{prompt_id}")
            assert response.status_code == status.HTTP_200_OK, f"Failed for {prompt_id}"
            data = response.json()
            assert data["id"] == prompt_id


class TestPromptsEndpointsVersionContent:
    """Test version content in prompt responses."""

    def test_version_contains_content(self, client: TestClient) -> None:
        """Test that each version contains the prompt content."""
        response = client.get("/v1/prompts/requirement_clarification")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert len(data["versions"]) > 0
        version = data["versions"][0]

        # Content should be a string containing the prompt
        assert "content" in version
        assert version["content"] is not None
        assert len(version["content"]) > 0

    def test_version_is_active_flag(self, client: TestClient) -> None:
        """Test that versions have is_active flag."""
        response = client.get("/v1/prompts/evaluation")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        if len(data["versions"]) > 0:
            version = data["versions"][0]
            assert "is_active" in version
            assert isinstance(version["is_active"], bool)


class TestPromptsEndpointsOpenAPI:
    """Test OpenAPI documentation for prompts endpoints."""

    def test_openapi_includes_prompts_endpoints(self, client: TestClient) -> None:
        """Test that OpenAPI schema includes prompts endpoints."""
        response = client.get("/openapi.json")

        assert response.status_code == status.HTTP_200_OK
        openapi = response.json()

        paths = openapi.get("paths", {})
        assert "/v1/prompts" in paths
        assert "/v1/prompts/{prompt_id}" in paths

    def test_openapi_prompts_list_schema(self, client: TestClient) -> None:
        """Test that OpenAPI defines correct schema for prompts list."""
        response = client.get("/openapi.json")

        assert response.status_code == status.HTTP_200_OK
        openapi = response.json()

        # Check that the endpoint exists and has GET method
        prompts_path = openapi.get("paths", {}).get("/v1/prompts", {})
        assert "get" in prompts_path

    def test_openapi_prompts_detail_schema(self, client: TestClient) -> None:
        """Test that OpenAPI defines correct schema for prompt detail."""
        response = client.get("/openapi.json")

        assert response.status_code == status.HTTP_200_OK
        openapi = response.json()

        # Check that the endpoint exists and has GET method
        prompt_detail_path = openapi.get("paths", {}).get("/v1/prompts/{prompt_id}", {})
        assert "get" in prompt_detail_path


class TestPromptsEndpointsEdgeCases:
    """Test edge cases for prompts endpoints."""

    def test_prompt_id_with_special_characters(self, client: TestClient) -> None:
        """Test handling of prompt ID with special characters."""
        # URL encoding should handle this
        response = client.get("/v1/prompts/test%20prompt")
        # Should return 404 for non-existent prompt
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_prompt_id_empty(self, client: TestClient) -> None:
        """Test handling of empty prompt ID."""
        # This should either be 404 or 405 depending on routing
        response = client.get("/v1/prompts/")
        # Empty path should match the list endpoint
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_307_TEMPORARY_REDIRECT,
        ]

    def test_concurrent_requests(self, client: TestClient) -> None:
        """Test handling of concurrent requests."""
        import concurrent.futures

        def make_request():
            return client.get("/v1/prompts")

        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]

        for response in results:
            assert response.status_code == status.HTTP_200_OK


class TestPromptsEndpointsErrorHandling:
    """Test error handling for prompts endpoints."""

    def test_list_prompts_internal_error(self, client: TestClient) -> None:
        """Test that internal errors return 500 status code."""
        from unittest.mock import patch

        # Mock the service to raise an exception
        with patch(
            "app.api.v1.prompts_endpoints._prompt_management_service.get_prompts",
            side_effect=RuntimeError("Simulated internal error"),
        ):
            response = client.get("/v1/prompts")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "detail" in data
        assert "Failed to list prompts" in data["detail"]

    def test_get_prompt_internal_error(self, client: TestClient) -> None:
        """Test that internal errors in get_prompt return 500 status code."""
        from unittest.mock import patch

        # Mock the service to raise an exception
        with patch(
            "app.api.v1.prompts_endpoints._prompt_management_service.get_prompt",
            side_effect=RuntimeError("Simulated internal error"),
        ):
            response = client.get("/v1/prompts/requirement_clarification")

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        data = response.json()
        assert "detail" in data
        assert "Failed to get prompt" in data["detail"]
