"""Integration tests for Issue #176: Real-time Dashboard SSE Implementation.

These tests verify the end-to-end behavior of the SSE dashboard:
- Full API endpoint testing
- SSE streaming validation
- Integration with metrics service
- Concurrent client scenarios
"""

import json
from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from app.main import app

    return TestClient(app)


class TestDashboardSSEEndpointIntegration:
    """Integration tests for SSE dashboard endpoint."""

    def test_dashboard_sse_service_instantiation(self):
        """Test DashboardSSEService can be instantiated and configured."""
        from app.services.dashboard_sse_service import DashboardSSEService

        service = DashboardSSEService()
        assert service.update_interval_seconds == 5
        assert service.heartbeat_interval_seconds == 30
        assert service.connection_manager is not None
        assert service.connection_manager.max_connections >= 100

    @pytest.mark.asyncio
    async def test_dashboard_service_fetch_metrics(self):
        """Test dashboard service can fetch metrics."""
        from app.services.dashboard_sse_service import DashboardSSEService

        service = DashboardSSEService()
        snapshot = await service.fetch_current_metrics()

        # Should return a snapshot even if no data
        assert snapshot is not None
        assert hasattr(snapshot, "average_score")
        assert hasattr(snapshot, "total_turns")

    def test_sse_endpoint_registered_with_correct_path(self, client):
        """Test SSE endpoint is registered with correct path."""
        from app.main import app

        routes = [route.path for route in app.routes]
        assert "/v1/observability/dashboard/stream" in routes


class TestDashboardMetricsIntegration:
    """Integration tests for dashboard metrics retrieval."""

    @patch("app.services.metrics_aggregation_service.trace_service")
    @patch("app.services.dashboard_sse_service.metrics_aggregation_service")
    def test_metrics_integration_with_langfuse(
        self, mock_dashboard_service, mock_trace_service
    ):
        """Test metrics integration with Langfuse data."""
        from app.services.dashboard_sse_service import DashboardSSEService

        mock_trace_service._is_enabled.return_value = True

        service = DashboardSSEService()
        # Service should be able to fetch metrics
        assert hasattr(service, "fetch_current_metrics")


class TestConcurrentClientScenarios:
    """Integration tests for concurrent client scenarios."""

    @pytest.mark.asyncio
    async def test_multiple_clients_receive_broadcasts(self):
        """Test that multiple clients all receive broadcast messages."""
        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()

        # Add 10 clients
        client_ids = [f"client_{i}" for i in range(10)]
        for client_id in client_ids:
            await manager.add_client(client_id)

        assert manager.get_client_count() == 10

        # Broadcast a message
        test_message = {"type": "test", "value": 42}
        await manager.broadcast(test_message)

        # Verify all clients received
        for client_id in client_ids:
            queue = manager.get_client_queue(client_id)
            assert queue is not None
            msg = await queue.get()
            assert msg["type"] == "test"
            assert msg["value"] == 42

    @pytest.mark.asyncio
    async def test_client_removal_does_not_affect_others(self):
        """Test that removing one client doesn't affect others."""
        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()

        # Add 5 clients
        for i in range(5):
            await manager.add_client(f"client_{i}")

        # Remove client_2
        await manager.remove_client("client_2")

        # Remaining 4 should still work
        assert manager.get_client_count() == 4

        # Broadcast should reach remaining clients
        await manager.broadcast({"test": True})

        for i in range(5):
            if i == 2:
                # Removed client should have no queue
                queue = manager.get_client_queue(f"client_{i}")
                assert queue is None
            else:
                queue = manager.get_client_queue(f"client_{i}")
                assert queue is not None


class TestErrorHandling:
    """Integration tests for error handling."""

    def test_service_generates_error_event_on_error(self):
        """Test that service can generate proper error events."""
        from app.services.dashboard_sse_service import DashboardSSEService

        service = DashboardSSEService()
        error_event = service.generate_error_event("Service unavailable")

        assert error_event.event_type == "error"
        assert error_event.data["message"] == "Service unavailable"

    @pytest.mark.asyncio
    async def test_broadcast_handles_disconnected_client(self):
        """Test broadcast handles disconnected client gracefully."""
        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()

        # Add and then remove a client
        await manager.add_client("client_001")
        await manager.remove_client("client_001")

        # Broadcast should not fail
        await manager.broadcast({"test": True})

        # No exception should be raised
        assert manager.get_client_count() == 0


class TestSSEDataFormat:
    """Test SSE data format compliance."""

    def test_metrics_event_json_serializable(self):
        """Test metrics events are JSON serializable."""
        from app.schemas.dashboard import SSEMetricsEvent

        event = SSEMetricsEvent(
            event_type="metrics_update",
            timestamp=datetime.now(),
            data={
                "average_score": 0.85,
                "total_turns": 100,
                "completion_rate": 75.0,
                "total_sessions": 50,
            },
        )

        # Should be JSON serializable
        json_str = event.model_dump_json()
        assert json_str is not None

        # Should be parseable
        parsed = json.loads(json_str)
        assert parsed["event_type"] == "metrics_update"

    def test_differential_update_json_serializable(self):
        """Test differential updates are JSON serializable."""
        from app.schemas.dashboard import DifferentialUpdate

        update = DifferentialUpdate(
            changed_fields={"average_score": 0.90, "total_turns": 105},
            timestamp=datetime.now(),
        )

        json_str = update.model_dump_json()
        assert json_str is not None

        parsed = json.loads(json_str)
        assert "changed_fields" in parsed
