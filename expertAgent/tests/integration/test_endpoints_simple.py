"""Simple integration tests for all endpoints."""

from fastapi.testclient import TestClient


class TestSimpleEndpoints:
    """Test all endpoints with simple requests."""

    def test_home_endpoint(self, client: TestClient):
        """Test home endpoint."""
        response = client.get("/aiagent-api/v1/")
        assert response.status_code == 200
        assert "message" in response.json()

    def test_mylllm_endpoint_validation_error(self, client: TestClient):
        """Test mylllm endpoint with invalid input."""
        response = client.post("/aiagent-api/v1/mylllm", json={})
        assert response.status_code == 422  # Validation error

    def test_aiagent_sample_validation_error(self, client: TestClient):
        """Test aiagent sample endpoint with invalid input."""
        response = client.post("/aiagent-api/v1/aiagent/sample", json={})
        assert response.status_code == 422

    def test_utility_agent_unknown(self, client: TestClient):
        """Test utility agent with unknown agent name."""
        response = client.post(
            "/aiagent-api/v1/aiagent/utility/unknown",
            json={"user_input": "test"},
        )
        assert response.status_code == 200
        assert response.json() == {"message": "No matching agent found."}

    def test_tts_validation_error(self, client: TestClient):
        """Test TTS endpoint with invalid input."""
        response = client.post("/aiagent-api/v1/utility/tts_and_upload_drive", json={})
        assert response.status_code == 422

    def test_google_search_validation_error(self, client: TestClient):
        """Test Google search endpoint with invalid input."""
        response = client.post("/aiagent-api/v1/utility/google_search", json={})
        assert response.status_code == 422

    def test_google_search_overview_validation_error(self, client: TestClient):
        """Test Google search overview endpoint with invalid input."""
        response = client.post(
            "/aiagent-api/v1/utility/google_search_overview", json={}
        )
        assert response.status_code == 422
