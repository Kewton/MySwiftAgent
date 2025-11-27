"""Unit tests for Issue #176: Real-time Dashboard SSE Implementation.

TDD Red Phase: These tests define the expected behavior of the SSE dashboard.
Tests cover:
- SSE streaming endpoint
- 5-second update interval
- 30-second heartbeat
- Differential data transmission
- Memory leak prevention
- Concurrent client support (100 clients)
"""

import asyncio
import json
from datetime import datetime
from typing import Any, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.observability import (
    ModelUsage,
    RequirementDefinitionMetrics,
)


class TestDashboardSSESchemas:
    """Test SSE dashboard schemas."""

    def test_sse_metrics_event_schema(self):
        """Test SSEMetricsEvent schema has required fields."""
        from app.schemas.dashboard import SSEMetricsEvent

        event = SSEMetricsEvent(
            event_type="metrics_update",
            timestamp=datetime.now(),
            data={
                "metrics": {
                    "average_score": 0.85,
                    "total_turns": 100,
                    "completion_rate": 75.0,
                    "total_sessions": 50,
                    "model_usage": [],
                }
            },
        )
        assert event.event_type == "metrics_update"
        assert "metrics" in event.data

    def test_sse_heartbeat_event_schema(self):
        """Test SSEHeartbeatEvent schema."""
        from app.schemas.dashboard import SSEMetricsEvent

        event = SSEMetricsEvent(
            event_type="heartbeat",
            timestamp=datetime.now(),
            data={},
        )
        assert event.event_type == "heartbeat"

    def test_dashboard_metrics_snapshot_schema(self):
        """Test DashboardMetricsSnapshot schema for differential updates."""
        from app.schemas.dashboard import DashboardMetricsSnapshot

        snapshot = DashboardMetricsSnapshot(
            average_score=0.85,
            total_turns=100,
            completion_rate=75.0,
            total_sessions=50,
            model_usage=[
                ModelUsage(
                    model_name="gpt-4o", usage_percentage=60.0, usage_count=30
                ),
                ModelUsage(
                    model_name="claude-haiku-4-5", usage_percentage=40.0, usage_count=20
                ),
            ],
            timestamp=datetime.now(),
        )
        assert snapshot.average_score == 0.85
        assert len(snapshot.model_usage) == 2

    def test_differential_update_schema(self):
        """Test DifferentialUpdate schema for changed fields only."""
        from app.schemas.dashboard import DifferentialUpdate

        update = DifferentialUpdate(
            changed_fields={"average_score": 0.90, "total_turns": 105},
            timestamp=datetime.now(),
        )
        assert "average_score" in update.changed_fields
        assert update.changed_fields["average_score"] == 0.90


class TestDashboardSSEService:
    """Test Dashboard SSE service layer."""

    @pytest.fixture
    def mock_metrics_service(self):
        """Create mock metrics aggregation service."""
        mock = MagicMock()
        mock.get_requirement_definition_metrics = AsyncMock()
        return mock

    def test_dashboard_service_exists(self):
        """Test DashboardSSEService class exists."""
        from app.services.dashboard_sse_service import DashboardSSEService

        service = DashboardSSEService()
        assert service is not None

    def test_service_has_update_interval(self):
        """Test service has 5-second update interval."""
        from app.services.dashboard_sse_service import DashboardSSEService

        service = DashboardSSEService()
        assert hasattr(service, "update_interval_seconds")
        assert service.update_interval_seconds == 5

    def test_service_has_heartbeat_interval(self):
        """Test service has 30-second heartbeat interval."""
        from app.services.dashboard_sse_service import DashboardSSEService

        service = DashboardSSEService()
        assert hasattr(service, "heartbeat_interval_seconds")
        assert service.heartbeat_interval_seconds == 30

    @pytest.mark.asyncio
    async def test_compute_differential_update(self):
        """Test differential update computation."""
        from app.schemas.dashboard import DashboardMetricsSnapshot
        from app.services.dashboard_sse_service import DashboardSSEService

        service = DashboardSSEService()
        now = datetime.now()

        old_snapshot = DashboardMetricsSnapshot(
            average_score=0.80,
            total_turns=100,
            completion_rate=70.0,
            total_sessions=50,
            model_usage=[],
            timestamp=now,
        )

        new_snapshot = DashboardMetricsSnapshot(
            average_score=0.85,  # Changed
            total_turns=105,  # Changed
            completion_rate=70.0,  # Same
            total_sessions=50,  # Same
            model_usage=[],
            timestamp=now,
        )

        diff = service.compute_differential(old_snapshot, new_snapshot)
        assert "average_score" in diff.changed_fields
        assert "total_turns" in diff.changed_fields
        assert "completion_rate" not in diff.changed_fields

    @pytest.mark.asyncio
    async def test_no_update_when_no_changes(self):
        """Test no update sent when data hasn't changed."""
        from app.schemas.dashboard import DashboardMetricsSnapshot
        from app.services.dashboard_sse_service import DashboardSSEService

        service = DashboardSSEService()
        now = datetime.now()

        snapshot = DashboardMetricsSnapshot(
            average_score=0.80,
            total_turns=100,
            completion_rate=70.0,
            total_sessions=50,
            model_usage=[],
            timestamp=now,
        )

        diff = service.compute_differential(snapshot, snapshot)
        assert len(diff.changed_fields) == 0


class TestClientConnectionManager:
    """Test concurrent client connection management."""

    def test_connection_manager_exists(self):
        """Test ConnectionManager class exists."""
        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()
        assert manager is not None

    def test_supports_100_concurrent_clients(self):
        """Test connection manager supports 100 concurrent clients."""
        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()
        assert manager.max_connections >= 100

    @pytest.mark.asyncio
    async def test_add_connection(self):
        """Test adding a client connection."""
        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()
        client_id = "client_001"

        await manager.add_client(client_id)
        assert manager.get_client_count() == 1

    @pytest.mark.asyncio
    async def test_remove_connection(self):
        """Test removing a client connection."""
        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()
        client_id = "client_001"

        await manager.add_client(client_id)
        await manager.remove_client(client_id)
        assert manager.get_client_count() == 0

    @pytest.mark.asyncio
    async def test_broadcast_to_all_clients(self):
        """Test broadcasting data to all connected clients."""
        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()

        # Add multiple clients with mock queues
        for i in range(5):
            await manager.add_client(f"client_{i}")

        # Broadcast message
        message = {"type": "metrics_update", "data": {"value": 123}}
        await manager.broadcast(message)

        # Verify all clients received the message
        for i in range(5):
            client_queue = manager.get_client_queue(f"client_{i}")
            assert client_queue is not None
            received = await client_queue.get()
            assert received["type"] == "metrics_update"


class TestSSEEndpoint:
    """Test SSE streaming endpoint."""

    def test_sse_service_generates_events(self):
        """Test that SSE service can generate events correctly."""
        from app.schemas.dashboard import SSEMetricsEvent
        from app.services.dashboard_sse_service import DashboardSSEService

        service = DashboardSSEService()

        # Test connected event generation
        connected = service.generate_connected_event("test_client")
        assert connected.event_type == "connected"
        assert connected.data["client_id"] == "test_client"

        # Test heartbeat event generation
        heartbeat = service.generate_heartbeat_event()
        assert heartbeat.event_type == "heartbeat"

        # Test error event generation
        error = service.generate_error_event("Test error")
        assert error.event_type == "error"
        assert error.data["message"] == "Test error"

    @pytest.mark.asyncio
    async def test_sse_service_generates_metrics_event(self):
        """Test that SSE service can generate metrics events."""
        from app.services.dashboard_sse_service import DashboardSSEService

        service = DashboardSSEService()

        # Generate initial metrics event (may be empty if no data)
        event = await service.generate_metrics_event(is_initial=True)
        assert event is not None
        assert event.event_type == "metrics_update"
        assert "is_full_snapshot" in event.data

    def test_sse_heartbeat_event_structure(self):
        """Test SSE heartbeat event structure."""
        from app.schemas.dashboard import SSEMetricsEvent

        heartbeat = SSEMetricsEvent(
            event_type="heartbeat",
            timestamp=datetime.now(),
            data={},
        )
        assert heartbeat.event_type == "heartbeat"
        assert heartbeat.data == {}

    def test_sse_endpoint_route_registered(self):
        """Test that SSE endpoint route is registered in the app."""
        from app.main import app

        # Check that the route exists
        routes = [route.path for route in app.routes]
        assert "/v1/observability/dashboard/stream" in routes


class TestMemoryLeakPrevention:
    """Test memory leak prevention mechanisms."""

    @pytest.mark.asyncio
    async def test_cleanup_disconnected_clients(self):
        """Test that disconnected clients are cleaned up."""
        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()

        # Add client
        await manager.add_client("client_001")
        assert manager.get_client_count() == 1

        # Simulate disconnect by removing
        await manager.remove_client("client_001")
        assert manager.get_client_count() == 0

    @pytest.mark.asyncio
    async def test_client_queue_bounded(self):
        """Test that client message queues are bounded to prevent memory issues."""
        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()
        await manager.add_client("client_001")

        # Queue should have a maximum size
        queue = manager.get_client_queue("client_001")
        assert queue is not None
        # asyncio.Queue maxsize is accessible
        assert queue.maxsize > 0
        assert queue.maxsize <= 100  # Reasonable bound

    @pytest.mark.asyncio
    async def test_old_messages_discarded_when_queue_full(self):
        """Test that old messages are discarded when queue is full."""
        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()
        await manager.add_client("client_001")

        queue = manager.get_client_queue("client_001")
        max_size = queue.maxsize

        # Fill queue beyond capacity
        for i in range(max_size + 10):
            # broadcast_no_wait should not block
            await manager.broadcast_no_wait({"message_id": i})

        # Queue should not exceed max size
        assert queue.qsize() <= max_size


class TestLongRunningConnection:
    """Test long-running connection scenarios (edge case: 1 hour)."""

    @pytest.mark.asyncio
    async def test_service_tracks_connection_duration(self):
        """Test service tracks how long each client has been connected."""
        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()
        await manager.add_client("client_001")

        # Should be able to get connection start time
        start_time = manager.get_connection_start_time("client_001")
        assert start_time is not None
        assert isinstance(start_time, datetime)

    @pytest.mark.asyncio
    async def test_connection_metadata_stored(self):
        """Test connection metadata is stored properly."""
        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()
        await manager.add_client("client_001")

        metadata = manager.get_client_metadata("client_001")
        assert metadata is not None
        assert "connected_at" in metadata


class TestDisconnectReconnect:
    """Test disconnect and reconnect scenarios."""

    @pytest.mark.asyncio
    async def test_reconnect_receives_full_snapshot(self):
        """Test that reconnecting client receives full data snapshot."""
        from app.services.dashboard_sse_service import DashboardSSEService

        service = DashboardSSEService()

        # Simulate reconnect - client should get full snapshot, not differential
        is_reconnect = True
        should_send_full = service.should_send_full_snapshot(is_reconnect)
        assert should_send_full is True

    @pytest.mark.asyncio
    async def test_new_connection_receives_full_snapshot(self):
        """Test that new connections receive full data snapshot."""
        from app.services.dashboard_sse_service import DashboardSSEService

        service = DashboardSSEService()

        # New connection should get full snapshot
        is_new = True
        should_send_full = service.should_send_full_snapshot(is_new)
        assert should_send_full is True
