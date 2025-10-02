"""Integration tests for API endpoints."""

from fastapi.testclient import TestClient


class TestHealthAPI:
    """Test health check endpoint."""

    def test_health_check(self, client: TestClient) -> None:
        """Test health check endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy", "service": "expertAgent"}


class TestRootAPI:
    """Test root endpoints."""

    def test_root(self, client: TestClient) -> None:
        """Test root endpoint returns welcome message."""
        response = client.get("/")
        assert response.status_code == 200
        assert "message" in response.json()
        assert response.json()["message"] == "Welcome to Expert Agent Service"

    def test_api_v1_root(self, client: TestClient) -> None:
        """Test API v1 root endpoint returns version info."""
        response = client.get("/api/v1/")
        assert response.status_code == 200
        assert response.json() == {"version": "1.0", "service": "expertAgent"}
