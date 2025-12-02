"""Integration tests for Requirement Definition Metrics API.

Issue #175: Quality visualization API implementation.
Tests the GET /v1/observability/requirement-definition-metrics endpoint.
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


class TestRequirementDefinitionMetricsEndpoint:
    """Test GET /v1/observability/requirement-definition-metrics endpoint."""

    @patch("app.services.metrics_aggregation_service.trace_service")
    def test_get_metrics_success(self, mock_trace_service, client: TestClient):
        """Test successful metrics retrieval."""
        # Mock trace service
        mock_trace_service._is_enabled.return_value = True
        mock_trace_service.get_traces.return_value = [
            {
                "id": "trace-1",
                "sessionId": "session-1",
                "name": "requirement_definition",
                "timestamp": "2025-11-01T10:00:00",
                "tags": ["requirement_definition"],
                "metadata": {"status": "completed"},
            },
            {
                "id": "trace-2",
                "sessionId": "session-2",
                "name": "requirement_definition",
                "timestamp": "2025-11-02T11:00:00",
                "tags": ["requirement_definition"],
                "metadata": {"status": "completed"},
            },
        ]
        mock_trace_service.get_scores_by_trace.return_value = [
            {"name": "quality_score", "value": 0.85}
        ]
        mock_trace_service.get_observations_by_trace.return_value = [
            {"type": "generation", "model": "gpt-4o"}
        ]

        # Call endpoint
        response = client.get("/aiagent-api/v1/observability/requirement-definition-metrics")

        # Assert response
        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
        assert "average_score" in data["metrics"]
        assert "total_turns" in data["metrics"]
        assert "completion_rate" in data["metrics"]
        assert "total_sessions" in data["metrics"]
        assert "model_usage" in data["metrics"]
        assert "from_date" in data
        assert "to_date" in data
        assert "cache_hit" in data
        assert "generated_at" in data

    @patch("app.services.metrics_aggregation_service.trace_service")
    def test_get_metrics_with_date_range(self, mock_trace_service, client: TestClient):
        """Test metrics retrieval with custom date range."""
        mock_trace_service._is_enabled.return_value = True
        mock_trace_service.get_traces.return_value = []

        # Call endpoint with date parameters
        response = client.get(
            "/aiagent-api/v1/observability/requirement-definition-metrics",
            params={
                "from_date": "2025-11-01T00:00:00",
                "to_date": "2025-11-15T23:59:59",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "2025-11-01" in data["from_date"]
        assert "2025-11-15" in data["to_date"]

    @patch("app.services.metrics_aggregation_service.trace_service")
    def test_get_metrics_empty_data(self, mock_trace_service, client: TestClient):
        """Test metrics when no data is available."""
        mock_trace_service._is_enabled.return_value = True
        mock_trace_service.get_traces.return_value = []

        response = client.get("/aiagent-api/v1/observability/requirement-definition-metrics")

        assert response.status_code == 200
        data = response.json()
        assert data["metrics"]["average_score"] == 0.0
        assert data["metrics"]["total_turns"] == 0
        assert data["metrics"]["completion_rate"] == 0.0
        assert data["metrics"]["total_sessions"] == 0
        assert data["metrics"]["model_usage"] == []

    @patch("app.services.metrics_aggregation_service.trace_service")
    def test_get_metrics_langfuse_disabled(self, mock_trace_service, client: TestClient):
        """Test metrics when Langfuse is disabled."""
        mock_trace_service._is_enabled.return_value = False

        response = client.get("/aiagent-api/v1/observability/requirement-definition-metrics")

        # Should return empty metrics (not an error)
        assert response.status_code == 200
        data = response.json()
        assert data["metrics"]["total_sessions"] == 0

    @patch("app.services.metrics_aggregation_service.trace_service")
    def test_get_metrics_model_usage_aggregation(self, mock_trace_service, client: TestClient):
        """Test model usage percentage calculation."""
        mock_trace_service._is_enabled.return_value = True
        mock_trace_service.get_traces.return_value = [
            {
                "id": f"trace-{i}",
                "sessionId": f"session-{i}",
                "name": "requirement_definition",
                "timestamp": f"2025-11-{(i % 28) + 1:02d}T10:00:00",
                "tags": ["requirement_definition"],
                "metadata": {"status": "completed"},
            }
            for i in range(5)
        ]
        # Model usage: 3 gpt-4o, 2 claude-haiku-4-5
        mock_trace_service.get_scores_by_trace.return_value = [
            {"name": "quality_score", "value": 0.85}
        ]

        def get_observations(trace_id):
            idx = int(trace_id.split("-")[1])
            model = "gpt-4o" if idx < 3 else "claude-haiku-4-5"
            return [{"type": "generation", "model": model}]

        mock_trace_service.get_observations_by_trace.side_effect = get_observations

        response = client.get("/aiagent-api/v1/observability/requirement-definition-metrics")

        assert response.status_code == 200
        data = response.json()
        model_usage = data["metrics"]["model_usage"]
        assert len(model_usage) == 2
        # gpt-4o should be first (60%)
        assert model_usage[0]["model_name"] == "gpt-4o"
        assert model_usage[0]["usage_percentage"] == pytest.approx(60.0, rel=0.01)

    @patch("app.services.metrics_aggregation_service.trace_service")
    def test_get_metrics_completion_rate_calculation(self, mock_trace_service, client: TestClient):
        """Test completion rate calculation."""
        mock_trace_service._is_enabled.return_value = True
        mock_trace_service.get_traces.return_value = [
            {
                "id": "trace-1",
                "sessionId": "session-1",
                "name": "requirement_definition",
                "timestamp": "2025-11-01T10:00:00",
                "tags": ["requirement_definition"],
                "metadata": {"status": "completed"},
            },
            {
                "id": "trace-2",
                "sessionId": "session-2",
                "name": "requirement_definition",
                "timestamp": "2025-11-02T11:00:00",
                "tags": ["requirement_definition"],
                "metadata": {"status": "completed"},
            },
            {
                "id": "trace-3",
                "sessionId": "session-3",
                "name": "requirement_definition",
                "timestamp": "2025-11-03T12:00:00",
                "tags": ["requirement_definition"],
                "metadata": {"status": "in_progress"},
            },
        ]
        mock_trace_service.get_scores_by_trace.return_value = []
        mock_trace_service.get_observations_by_trace.return_value = []

        response = client.get("/aiagent-api/v1/observability/requirement-definition-metrics")

        assert response.status_code == 200
        data = response.json()
        # 2 completed out of 3 = 66.67%
        assert data["metrics"]["completion_rate"] == pytest.approx(66.67, rel=0.01)


class TestMetricsResponseFormat:
    """Test response format and schema validation."""

    @patch("app.services.metrics_aggregation_service.trace_service")
    def test_response_schema_validation(self, mock_trace_service, client: TestClient):
        """Test that response matches expected schema."""
        mock_trace_service._is_enabled.return_value = True
        mock_trace_service.get_traces.return_value = [
            {
                "id": "trace-1",
                "sessionId": "session-1",
                "name": "requirement_definition",
                "timestamp": "2025-11-01T10:00:00",
                "tags": ["requirement_definition"],
                "metadata": {"status": "completed"},
            }
        ]
        mock_trace_service.get_scores_by_trace.return_value = [
            {"name": "quality_score", "value": 0.90}
        ]
        mock_trace_service.get_observations_by_trace.return_value = [
            {"type": "generation", "model": "gpt-4o-mini"}
        ]

        response = client.get("/aiagent-api/v1/observability/requirement-definition-metrics")

        assert response.status_code == 200
        data = response.json()

        # Validate metrics structure
        metrics = data["metrics"]
        assert isinstance(metrics["average_score"], float)
        assert isinstance(metrics["total_turns"], int)
        assert isinstance(metrics["completion_rate"], float)
        assert isinstance(metrics["total_sessions"], int)
        assert isinstance(metrics["model_usage"], list)

        # Validate model_usage items
        for model_item in metrics["model_usage"]:
            assert "model_name" in model_item
            assert "usage_percentage" in model_item
            assert "usage_count" in model_item

        # Validate response level fields
        assert "from_date" in data
        assert "to_date" in data
        assert isinstance(data["cache_hit"], bool)
        assert "generated_at" in data

    @patch("app.services.metrics_aggregation_service.trace_service")
    def test_average_score_bounds(self, mock_trace_service, client: TestClient):
        """Test that average_score is within valid bounds."""
        mock_trace_service._is_enabled.return_value = True
        mock_trace_service.get_traces.return_value = [
            {
                "id": "trace-1",
                "sessionId": "session-1",
                "name": "requirement_definition",
                "timestamp": "2025-11-01T10:00:00",
                "tags": ["requirement_definition"],
                "metadata": {"status": "completed"},
            }
        ]
        mock_trace_service.get_scores_by_trace.return_value = [
            {"name": "quality_score", "value": 0.95}
        ]
        mock_trace_service.get_observations_by_trace.return_value = []

        response = client.get("/aiagent-api/v1/observability/requirement-definition-metrics")

        assert response.status_code == 200
        data = response.json()
        assert 0.0 <= data["metrics"]["average_score"] <= 1.0

    @patch("app.services.metrics_aggregation_service.trace_service")
    def test_completion_rate_bounds(self, mock_trace_service, client: TestClient):
        """Test that completion_rate is within valid bounds."""
        mock_trace_service._is_enabled.return_value = True
        mock_trace_service.get_traces.return_value = [
            {
                "id": "trace-1",
                "sessionId": "session-1",
                "name": "requirement_definition",
                "timestamp": "2025-11-01T10:00:00",
                "tags": ["requirement_definition"],
                "metadata": {"status": "completed"},
            }
        ]
        mock_trace_service.get_scores_by_trace.return_value = []
        mock_trace_service.get_observations_by_trace.return_value = []

        response = client.get("/aiagent-api/v1/observability/requirement-definition-metrics")

        assert response.status_code == 200
        data = response.json()
        assert 0.0 <= data["metrics"]["completion_rate"] <= 100.0
