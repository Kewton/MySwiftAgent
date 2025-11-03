"""Integration tests for Observability API endpoints.

Issue #113: Langfuse Self-hosted統合 - Observability API
"""

from unittest.mock import patch

from fastapi.testclient import TestClient


class TestObservabilityTracesList:
    """Test GET /v1/observability/traces endpoint."""

    @patch("app.services.observability_service.trace_service")
    def test_get_traces_success(self, mock_trace_service, client: TestClient):
        """Test successful trace list retrieval."""
        # Mock trace_service methods
        mock_trace_service._is_enabled.return_value = True
        mock_trace_service.get_traces.return_value = [
            {
                "id": "trace-123",
                "name": "sample_agent",
                "userId": "test-user",
                "sessionId": "test-session",
                "timestamp": "2025-11-03T01:00:00",
                "tags": ["sample", "graph_agent"],
                "metadata": {"model": "gpt-4o-mini"},
            },
            {
                "id": "trace-456",
                "name": "explorer_agent",
                "userId": "test-user",
                "sessionId": "test-session",
                "timestamp": "2025-11-03T02:00:00",
                "tags": ["utility", "explorer"],
                "metadata": {"model": "gpt-4o-mini"},
            },
        ]
        mock_trace_service.get_trace_url.side_effect = (
            lambda trace_id: f"http://localhost:3001/project/expertAgent-traces/traces/{trace_id}"
        )

        # Call endpoint
        response = client.get("/aiagent-api/v1/observability/traces?limit=10&offset=0")

        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert "traces" in data
        assert len(data["traces"]) == 2
        assert data["total"] == 2
        assert data["limit"] == 10
        assert data["offset"] == 0

        # Check first trace
        assert data["traces"][0]["id"] == "trace-123"
        assert data["traces"][0]["name"] == "sample_agent"
        assert data["traces"][0]["user_id"] == "test-user"
        assert (
            data["traces"][0]["langfuse_url"]
            == "http://localhost:3001/project/expertAgent-traces/traces/trace-123"
        )

    @patch("app.services.observability_service.trace_service")
    def test_get_traces_with_filters(self, mock_trace_service, client: TestClient):
        """Test trace list retrieval with user_id and tags filters."""
        mock_trace_service._is_enabled.return_value = True
        mock_trace_service.get_traces.return_value = [
            {
                "id": "trace-789",
                "name": "sample_agent",
                "userId": "user-123",
                "sessionId": "session-abc",
                "timestamp": "2025-11-03T03:00:00",
                "tags": ["production", "critical"],
                "metadata": {},
            }
        ]
        mock_trace_service.get_trace_url.return_value = (
            "http://localhost:3001/project/expertAgent-traces/traces/trace-789"
        )

        # Call endpoint with filters
        response = client.get(
            "/aiagent-api/v1/observability/traces"
            "?user_id=user-123"
            "&tags=production,critical"
            "&limit=5"
        )

        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert len(data["traces"]) == 1
        assert data["traces"][0]["user_id"] == "user-123"
        assert "production" in data["traces"][0]["tags"]

        # Verify trace_service was called with correct parameters
        mock_trace_service.get_traces.assert_called_once()
        call_kwargs = mock_trace_service.get_traces.call_args.kwargs
        assert call_kwargs["user_id"] == "user-123"
        assert call_kwargs["tags"] == ["production", "critical"]

    @patch("app.services.observability_service.trace_service")
    def test_get_traces_empty(self, mock_trace_service, client: TestClient):
        """Test trace list retrieval when no traces exist."""
        mock_trace_service._is_enabled.return_value = True
        mock_trace_service.get_traces.return_value = []

        response = client.get("/aiagent-api/v1/observability/traces")

        assert response.status_code == 200
        data = response.json()
        assert data["traces"] == []
        assert data["total"] == 0

    @patch("app.services.observability_service.trace_service")
    def test_get_traces_langfuse_disabled(self, mock_trace_service, client: TestClient):
        """Test trace list retrieval when Langfuse is disabled."""
        mock_trace_service._is_enabled.return_value = False

        response = client.get("/aiagent-api/v1/observability/traces")

        # Should return 400 error
        assert response.status_code == 400
        data = response.json()
        assert "Langfuse is not enabled" in data["detail"]

    @patch("app.services.observability_service.trace_service")
    def test_get_traces_pagination(self, mock_trace_service, client: TestClient):
        """Test trace list pagination."""
        mock_trace_service._is_enabled.return_value = True
        # Return 100 traces to test pagination
        mock_traces = [
            {
                "id": f"trace-{i}",
                "name": "test_agent",
                "userId": "test-user",
                "sessionId": "test-session",
                "timestamp": f"2025-11-03T{i:02d}:00:00",
                "tags": [],
                "metadata": {},
            }
            for i in range(100)
        ]
        mock_trace_service.get_traces.return_value = mock_traces
        mock_trace_service.get_trace_url.side_effect = (
            lambda trace_id: f"http://localhost:3001/project/expertAgent-traces/traces/{trace_id}"
        )

        # Test page 1 (offset 0, limit 10)
        response = client.get("/aiagent-api/v1/observability/traces?limit=10&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert len(data["traces"]) == 10
        assert data["total"] == 100
        assert data["offset"] == 0

        # Test page 2 (offset 10, limit 10)
        response = client.get("/aiagent-api/v1/observability/traces?limit=10&offset=10")
        assert response.status_code == 200
        data = response.json()
        assert len(data["traces"]) == 10
        assert data["traces"][0]["id"] == "trace-10"


class TestObservabilityTraceDetail:
    """Test GET /v1/observability/traces/{trace_id} endpoint."""

    @patch("app.services.observability_service.trace_service")
    def test_get_trace_detail_success(self, mock_trace_service, client: TestClient):
        """Test successful trace detail retrieval."""
        mock_trace_service._is_enabled.return_value = True
        mock_trace_service.get_trace_by_id.return_value = {
            "id": "trace-123",
            "name": "sample_agent",
            "userId": "test-user",
            "sessionId": "test-session",
            "timestamp": "2025-11-03T01:00:00",
            "tags": ["sample"],
            "metadata": {"model": "gpt-4o-mini"},
        }
        mock_trace_service.get_observations_by_trace.return_value = [
            {
                "id": "obs-1",
                "type": "generation",
                "name": "llm_call",
                "startTime": "2025-11-03T01:00:01",
                "endTime": "2025-11-03T01:00:02",
                "input": {"prompt": "Hello"},
                "output": {"response": "Hi there!"},
                "metadata": {},
                "model": "gpt-4o-mini",
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
        ]
        mock_trace_service.get_trace_url.return_value = (
            "http://localhost:3001/project/expertAgent-traces/traces/trace-123"
        )

        response = client.get("/aiagent-api/v1/observability/traces/trace-123")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "trace-123"
        assert data["name"] == "sample_agent"
        assert len(data["observations"]) == 1
        assert data["observations"][0]["type"] == "generation"
        assert data["observations"][0]["model"] == "gpt-4o-mini"
        assert (
            data["langfuse_url"]
            == "http://localhost:3001/project/expertAgent-traces/traces/trace-123"
        )

    @patch("app.services.observability_service.trace_service")
    def test_get_trace_detail_not_found(self, mock_trace_service, client: TestClient):
        """Test trace detail retrieval for non-existent trace."""
        mock_trace_service._is_enabled.return_value = True
        mock_trace_service.get_trace_by_id.return_value = None

        response = client.get("/aiagent-api/v1/observability/traces/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert "Trace not found" in data["detail"]

    @patch("app.services.observability_service.trace_service")
    def test_get_trace_detail_langfuse_disabled(
        self, mock_trace_service, client: TestClient
    ):
        """Test trace detail retrieval when Langfuse is disabled."""
        mock_trace_service._is_enabled.return_value = False

        response = client.get("/aiagent-api/v1/observability/traces/trace-123")

        assert response.status_code == 400
        data = response.json()
        assert "Langfuse is not enabled" in data["detail"]


class TestObservabilityScore:
    """Test POST /v1/observability/scores endpoint."""

    @patch("app.services.observability_service.langfuse_service")
    def test_submit_score_success(self, mock_langfuse_service, client: TestClient):
        """Test successful score submission."""
        mock_langfuse_service._is_enabled.return_value = True
        mock_langfuse_service.score_trace.return_value = True

        response = client.post(
            "/aiagent-api/v1/observability/scores",
            json={
                "trace_id": "trace-123",
                "name": "user_rating",
                "value": 0.9,
                "comment": "Excellent response",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "successfully submitted" in data["message"]

        # Verify langfuse_service.score_trace was called
        mock_langfuse_service.score_trace.assert_called_once_with(
            trace_id="trace-123",
            name="user_rating",
            value=0.9,
            comment="Excellent response",
        )

    @patch("app.services.observability_service.langfuse_service")
    def test_submit_score_failure(self, mock_langfuse_service, client: TestClient):
        """Test score submission failure."""
        mock_langfuse_service._is_enabled.return_value = True
        mock_langfuse_service.score_trace.return_value = False

        response = client.post(
            "/aiagent-api/v1/observability/scores",
            json={
                "trace_id": "trace-123",
                "name": "accuracy",
                "value": 0.5,
            },
        )

        assert response.status_code == 500
        data = response.json()
        assert "Failed to submit score" in data["detail"]

    @patch("app.services.observability_service.langfuse_service")
    def test_submit_score_langfuse_disabled(
        self, mock_langfuse_service, client: TestClient
    ):
        """Test score submission when Langfuse is disabled."""
        mock_langfuse_service._is_enabled.return_value = False

        response = client.post(
            "/aiagent-api/v1/observability/scores",
            json={
                "trace_id": "trace-123",
                "name": "user_rating",
                "value": 0.8,
            },
        )

        # When Langfuse is disabled, endpoint returns 500 error
        assert response.status_code == 500
        data = response.json()
        assert "Langfuse is not enabled" in data["detail"]

    def test_submit_score_validation_errors(self, client: TestClient):
        """Test score submission with invalid input."""
        # Missing required fields
        response = client.post("/aiagent-api/v1/observability/scores", json={})
        assert response.status_code == 422

        # Value out of range (must be 0.0-1.0)
        response = client.post(
            "/aiagent-api/v1/observability/scores",
            json={
                "trace_id": "trace-123",
                "name": "rating",
                "value": 1.5,  # Invalid: > 1.0
            },
        )
        assert response.status_code == 422

        # Negative value
        response = client.post(
            "/aiagent-api/v1/observability/scores",
            json={
                "trace_id": "trace-123",
                "name": "rating",
                "value": -0.5,  # Invalid: < 0.0
            },
        )
        assert response.status_code == 422
