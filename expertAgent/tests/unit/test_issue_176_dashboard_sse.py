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

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.observability import (
    ModelUsage,
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
                ModelUsage(model_name="gpt-4o", usage_percentage=60.0, usage_count=30),
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


class TestConnectionManagerEdgeCases:
    """Test edge cases for ConnectionManager to improve coverage."""

    @pytest.mark.asyncio
    async def test_reconnect_existing_client(self):
        """Test reconnecting an existing client (lines 65-67)."""
        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()
        client_id = "client_reconnect"

        # First connection
        await manager.add_client(client_id)
        first_queue = manager.get_client_queue(client_id)
        assert first_queue is not None

        # Put a message in the queue
        await first_queue.put({"test": "message"})

        # Reconnect same client
        await manager.add_client(client_id)
        second_queue = manager.get_client_queue(client_id)
        assert second_queue is not None

        # New queue should be empty (old queue was discarded)
        assert second_queue.empty()
        assert manager.get_client_count() == 1

    @pytest.mark.asyncio
    async def test_get_client_metadata_for_nonexistent_client(self):
        """Test getting metadata for a client that doesn't exist (line 147)."""
        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()

        # Get metadata for non-existent client
        metadata = manager.get_client_metadata("nonexistent_client")
        assert metadata is None

    @pytest.mark.asyncio
    async def test_get_connection_start_time_for_nonexistent_client(self):
        """Test getting connection start time for non-existent client."""
        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()

        # Get start time for non-existent client
        start_time = manager.get_connection_start_time("nonexistent_client")
        assert start_time is None

    @pytest.mark.asyncio
    async def test_remove_nonexistent_client(self):
        """Test removing a client that doesn't exist."""
        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()

        # Should not raise an error
        await manager.remove_client("nonexistent_client")
        assert manager.get_client_count() == 0


class TestBroadcastErrorHandling:
    """Test broadcast error handling scenarios."""

    @pytest.mark.asyncio
    async def test_broadcast_timeout_handling(self):
        """Test broadcast handles timeout errors (lines 165-166)."""
        from app.schemas.dashboard import DashboardStreamConfig
        from app.services.dashboard_sse_service import ConnectionManager

        # Create manager with very small queue
        config = DashboardStreamConfig(queue_max_size=10)
        manager = ConnectionManager(config=config)

        await manager.add_client("slow_client")
        queue = manager.get_client_queue("slow_client")

        # Fill the queue completely
        for _ in range(10):
            queue.put_nowait({"filler": True})

        # Broadcast should handle timeout gracefully
        # Note: This tests the timeout branch indirectly
        await manager.broadcast({"test": "message"})

        # Client should still be connected (timeout doesn't disconnect)
        assert manager.get_client_count() == 1

    @pytest.mark.asyncio
    async def test_broadcast_updates_metadata(self):
        """Test that broadcast updates client metadata correctly."""
        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()
        await manager.add_client("client_001")

        # Get initial metadata
        initial_metadata = manager.get_client_metadata("client_001")
        assert initial_metadata["messages_sent"] == 0
        assert initial_metadata["last_message_at"] is None

        # Broadcast a message
        await manager.broadcast({"test": "message"})

        # Check updated metadata
        updated_metadata = manager.get_client_metadata("client_001")
        assert updated_metadata["messages_sent"] == 1
        assert updated_metadata["last_message_at"] is not None


class TestDifferentialUpdateGeneration:
    """Test differential update generation scenarios."""

    @pytest.mark.asyncio
    async def test_generate_metrics_event_with_changes(self):
        """Test generating metrics event when data has changed (lines 330-337)."""
        from unittest.mock import AsyncMock

        from app.schemas.dashboard import DashboardMetricsSnapshot
        from app.services.dashboard_sse_service import DashboardSSEService

        service = DashboardSSEService()

        # Set initial snapshot
        initial_snapshot = DashboardMetricsSnapshot(
            average_score=0.80,
            total_turns=100,
            completion_rate=70.0,
            total_sessions=50,
            model_usage=[],
        )
        service._last_snapshot = initial_snapshot

        # Mock fetch to return changed data
        new_snapshot = DashboardMetricsSnapshot(
            average_score=0.85,
            total_turns=110,
            completion_rate=75.0,
            total_sessions=55,
            model_usage=[],
        )

        with patch.object(
            service, "fetch_current_metrics", new=AsyncMock(return_value=new_snapshot)
        ):
            event = await service.generate_metrics_event(is_initial=False)

        assert event is not None
        assert event.event_type == "metrics_update"
        assert event.data["is_full_snapshot"] is False
        assert "changed_fields" in event.data

    @pytest.mark.asyncio
    async def test_generate_metrics_event_no_changes_returns_none(self):
        """Test that no event is generated when metrics haven't changed."""
        from unittest.mock import AsyncMock

        from app.schemas.dashboard import DashboardMetricsSnapshot
        from app.services.dashboard_sse_service import DashboardSSEService

        service = DashboardSSEService()

        # Set initial snapshot
        snapshot = DashboardMetricsSnapshot(
            average_score=0.80,
            total_turns=100,
            completion_rate=70.0,
            total_sessions=50,
            model_usage=[],
        )
        service._last_snapshot = snapshot

        # Mock fetch to return same data
        with patch.object(
            service, "fetch_current_metrics", new=AsyncMock(return_value=snapshot)
        ):
            event = await service.generate_metrics_event(is_initial=False)

        # Should return None when no changes
        assert event is None


class TestFetchMetricsErrorHandling:
    """Test fetch_current_metrics error handling."""

    @pytest.mark.asyncio
    async def test_fetch_metrics_handles_error(self):
        """Test fetch_current_metrics returns empty snapshot on error (lines 299-302)."""
        from unittest.mock import AsyncMock

        from app.services.dashboard_sse_service import DashboardSSEService

        service = DashboardSSEService()

        # Mock the metrics service to raise an exception
        with patch.object(
            service._metrics_service,
            "get_requirement_definition_metrics",
            new=AsyncMock(side_effect=Exception("Test error")),
        ):
            snapshot = await service.fetch_current_metrics()

        # Should return empty snapshot
        assert snapshot is not None
        assert snapshot.average_score == 0.0
        assert snapshot.total_turns == 0


class TestSSEConnectionInfo:
    """Test SSEConnectionInfo schema."""

    def test_sse_connection_info_schema(self):
        """Test SSEConnectionInfo schema fields."""
        from app.schemas.dashboard import SSEConnectionInfo

        info = SSEConnectionInfo(
            client_id="test_client",
            connected_at=datetime.now(),
            last_message_at=datetime.now(),
            messages_sent=5,
        )
        assert info.client_id == "test_client"
        assert info.messages_sent == 5

    def test_sse_connection_info_defaults(self):
        """Test SSEConnectionInfo default values."""
        from app.schemas.dashboard import SSEConnectionInfo

        info = SSEConnectionInfo(client_id="test_client")
        assert info.messages_sent == 0
        assert info.last_message_at is None


class TestDashboardStreamConfig:
    """Test DashboardStreamConfig schema."""

    def test_dashboard_stream_config_defaults(self):
        """Test DashboardStreamConfig default values."""
        from app.schemas.dashboard import DashboardStreamConfig

        config = DashboardStreamConfig()
        assert config.update_interval_seconds == 5
        assert config.heartbeat_interval_seconds == 30
        assert config.max_connections == 100
        assert config.queue_max_size == 50

    def test_dashboard_stream_config_custom(self):
        """Test DashboardStreamConfig custom values."""
        from app.schemas.dashboard import DashboardStreamConfig

        config = DashboardStreamConfig(
            update_interval_seconds=10,
            heartbeat_interval_seconds=60,
            max_connections=200,
            queue_max_size=100,
        )
        assert config.update_interval_seconds == 10
        assert config.heartbeat_interval_seconds == 60
        assert config.max_connections == 200
        assert config.queue_max_size == 100


class TestSnapshotToDict:
    """Test DashboardMetricsSnapshot.to_dict method."""

    def test_snapshot_to_dict_with_model_usage(self):
        """Test to_dict with model usage data."""
        from app.schemas.dashboard import DashboardMetricsSnapshot
        from app.schemas.observability import ModelUsage

        snapshot = DashboardMetricsSnapshot(
            average_score=0.85,
            total_turns=100,
            completion_rate=75.0,
            total_sessions=50,
            model_usage=[
                ModelUsage(model_name="gpt-4o", usage_percentage=60.0, usage_count=30),
            ],
        )

        result = snapshot.to_dict()
        assert result["average_score"] == 0.85
        assert result["total_turns"] == 100
        assert len(result["model_usage"]) == 1
        assert result["model_usage"][0]["model_name"] == "gpt-4o"

    def test_snapshot_to_dict_empty_model_usage(self):
        """Test to_dict with empty model usage."""
        from app.schemas.dashboard import DashboardMetricsSnapshot

        snapshot = DashboardMetricsSnapshot(
            average_score=0.0,
            total_turns=0,
            completion_rate=0.0,
            total_sessions=0,
            model_usage=[],
        )

        result = snapshot.to_dict()
        assert result["model_usage"] == []


class TestBroadcastExceptionHandling:
    """Test broadcast exception and cleanup handling (lines 167-176)."""

    @pytest.mark.asyncio
    async def test_broadcast_exception_triggers_cleanup(self):
        """Test that exceptions during broadcast trigger client cleanup."""

        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()
        await manager.add_client("error_client")

        # Get the queue and make it raise an exception
        queue = manager.get_client_queue("error_client")

        # Replace the queue's put method to raise an exception
        async def failing_put(*args, **kwargs):
            raise RuntimeError("Simulated error")

        with patch.object(queue, "put", side_effect=failing_put):
            # Broadcast should handle the error
            await manager.broadcast({"test": "message"})

        # Client should be cleaned up after error
        assert manager.get_client_count() == 0

    @pytest.mark.asyncio
    async def test_broadcast_cleans_up_multiple_errored_clients(self):
        """Test that multiple errored clients are cleaned up."""
        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()

        # Add multiple clients
        for i in range(3):
            await manager.add_client(f"client_{i}")

        assert manager.get_client_count() == 3

        # Make all queues fail
        for i in range(3):
            queue = manager.get_client_queue(f"client_{i}")

            async def failing_put(*args, **kwargs):
                raise RuntimeError("Simulated error")

            queue.put = failing_put

        # Broadcast should clean up all errored clients
        await manager.broadcast({"test": "message"})

        # All clients should be removed
        assert manager.get_client_count() == 0


class TestBroadcastNoWaitEdgeCases:
    """Test broadcast_no_wait edge cases (lines 197-198)."""

    @pytest.mark.asyncio
    async def test_broadcast_no_wait_handles_queue_empty_during_discard(self):
        """Test broadcast_no_wait handles QueueEmpty during discard."""

        from app.schemas.dashboard import DashboardStreamConfig
        from app.services.dashboard_sse_service import ConnectionManager

        # Create manager with small queue
        config = DashboardStreamConfig(queue_max_size=10)
        manager = ConnectionManager(config=config)

        await manager.add_client("edge_client")
        queue = manager.get_client_queue("edge_client")

        # Fill queue to capacity
        for i in range(10):
            queue.put_nowait({"msg": i})

        assert queue.full()

        # Now we need to simulate the race condition where:
        # 1. put_nowait fails with QueueFull
        # 2. get_nowait is called but queue is empty (race condition)
        # This is hard to test directly, but we test that the code handles it gracefully

        # Broadcast many messages to trigger the discard logic
        for i in range(20):
            await manager.broadcast_no_wait({"test": i})

        # Queue should still be bounded
        assert queue.qsize() <= 10

    @pytest.mark.asyncio
    async def test_broadcast_no_wait_updates_metadata(self):
        """Test broadcast_no_wait updates client metadata."""
        from app.services.dashboard_sse_service import ConnectionManager

        manager = ConnectionManager()
        await manager.add_client("client_001")

        # Initial state
        metadata = manager.get_client_metadata("client_001")
        assert metadata["messages_sent"] == 0

        # Broadcast several messages
        for i in range(5):
            await manager.broadcast_no_wait({"count": i})

        # Metadata should be updated
        metadata = manager.get_client_metadata("client_001")
        assert metadata["messages_sent"] == 5


class TestConnectionManagerWithCustomConfig:
    """Test ConnectionManager with custom configuration."""

    @pytest.mark.asyncio
    async def test_custom_queue_size(self):
        """Test that custom queue size is respected."""
        from app.schemas.dashboard import DashboardStreamConfig
        from app.services.dashboard_sse_service import ConnectionManager

        config = DashboardStreamConfig(queue_max_size=25)
        manager = ConnectionManager(config=config)

        await manager.add_client("client_001")
        queue = manager.get_client_queue("client_001")

        assert queue.maxsize == 25

    @pytest.mark.asyncio
    async def test_custom_max_connections(self):
        """Test that custom max connections is respected."""
        from app.schemas.dashboard import DashboardStreamConfig
        from app.services.dashboard_sse_service import ConnectionManager

        config = DashboardStreamConfig(max_connections=50)
        manager = ConnectionManager(config=config)

        assert manager.max_connections == 50
