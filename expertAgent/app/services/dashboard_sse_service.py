"""Dashboard SSE Service for real-time metrics streaming.

Issue #176: Real-time Dashboard Implementation
- SSE streaming with 5-second update intervals
- 30-second heartbeat for connection keep-alive
- Differential data transmission
- Support for 100 concurrent clients
- Memory leak prevention with bounded queues
"""

import asyncio
import logging
from datetime import datetime
from typing import Any

from app.schemas.dashboard import (
    DashboardMetricsSnapshot,
    DashboardStreamConfig,
    DifferentialUpdate,
    SSEConnectionInfo,
    SSEMetricsEvent,
)
from app.services.metrics_aggregation_service import MetricsAggregationService

logger = logging.getLogger(__name__)

# Singleton instance of metrics service
metrics_aggregation_service = MetricsAggregationService()


class ConnectionManager:
    """Manages concurrent SSE client connections.

    Features:
    - Support for 100+ concurrent clients
    - Bounded message queues to prevent memory leaks
    - Efficient broadcast to all clients
    - Clean connection tracking and cleanup
    """

    def __init__(self, config: DashboardStreamConfig | None = None) -> None:
        """Initialize ConnectionManager.

        Args:
            config: Optional configuration, uses defaults if not provided.
        """
        self._config = config or DashboardStreamConfig()
        self._clients: dict[str, asyncio.Queue[dict[str, Any]]] = {}
        self._metadata: dict[str, SSEConnectionInfo] = {}
        self._lock = asyncio.Lock()

    @property
    def max_connections(self) -> int:
        """Maximum number of concurrent connections allowed."""
        return self._config.max_connections

    async def add_client(self, client_id: str) -> None:
        """Add a new client connection.

        Args:
            client_id: Unique identifier for the client.
        """
        async with self._lock:
            if client_id in self._clients:
                logger.warning(f"Client {client_id} already connected, reconnecting")
                # Clean up old connection
                del self._clients[client_id]

            # Create bounded queue for this client
            queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(
                maxsize=self._config.queue_max_size
            )
            self._clients[client_id] = queue
            self._metadata[client_id] = SSEConnectionInfo(
                client_id=client_id,
                connected_at=datetime.now(),
                last_message_at=None,
                messages_sent=0,
            )
            logger.info(
                f"Client {client_id} connected. Total clients: {len(self._clients)}"
            )

    async def remove_client(self, client_id: str) -> None:
        """Remove a client connection.

        Args:
            client_id: Unique identifier for the client.
        """
        async with self._lock:
            if client_id in self._clients:
                del self._clients[client_id]
            if client_id in self._metadata:
                del self._metadata[client_id]
            logger.info(
                f"Client {client_id} disconnected. Total clients: {len(self._clients)}"
            )

    def get_client_count(self) -> int:
        """Get current number of connected clients."""
        return len(self._clients)

    def get_client_queue(self, client_id: str) -> asyncio.Queue[dict[str, Any]] | None:
        """Get the message queue for a specific client.

        Args:
            client_id: Client identifier.

        Returns:
            The client's message queue, or None if not connected.
        """
        return self._clients.get(client_id)

    def get_connection_start_time(self, client_id: str) -> datetime | None:
        """Get when a client connected.

        Args:
            client_id: Client identifier.

        Returns:
            Connection start time, or None if not connected.
        """
        metadata = self._metadata.get(client_id)
        return metadata.connected_at if metadata else None

    def get_client_metadata(self, client_id: str) -> dict[str, Any] | None:
        """Get metadata for a specific client.

        Args:
            client_id: Client identifier.

        Returns:
            Client metadata dict, or None if not connected.
        """
        metadata = self._metadata.get(client_id)
        if metadata:
            return {
                "client_id": metadata.client_id,
                "connected_at": metadata.connected_at.isoformat(),
                "last_message_at": (
                    metadata.last_message_at.isoformat()
                    if metadata.last_message_at
                    else None
                ),
                "messages_sent": metadata.messages_sent,
            }
        return None

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Broadcast a message to all connected clients.

        Args:
            message: Message to broadcast.
        """
        async with self._lock:
            disconnected_clients: list[str] = []

            for client_id, queue in self._clients.items():
                try:
                    await asyncio.wait_for(queue.put(message), timeout=1.0)
                    # Update metadata
                    if client_id in self._metadata:
                        self._metadata[client_id].last_message_at = datetime.now()
                        self._metadata[client_id].messages_sent += 1
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout sending to client {client_id}")
                except Exception as e:
                    logger.error(f"Error sending to client {client_id}: {e}")
                    disconnected_clients.append(client_id)

            # Cleanup disconnected clients
            for client_id in disconnected_clients:
                if client_id in self._clients:
                    del self._clients[client_id]
                if client_id in self._metadata:
                    del self._metadata[client_id]

    async def broadcast_no_wait(self, message: dict[str, Any]) -> None:
        """Broadcast a message without waiting, discarding if queue is full.

        Args:
            message: Message to broadcast.
        """
        async with self._lock:
            for client_id, queue in list(self._clients.items()):
                try:
                    # Non-blocking put - discard if full
                    queue.put_nowait(message)
                    if client_id in self._metadata:
                        self._metadata[client_id].last_message_at = datetime.now()
                        self._metadata[client_id].messages_sent += 1
                except asyncio.QueueFull:
                    # Queue is full, discard oldest message and add new one
                    try:
                        queue.get_nowait()  # Remove oldest
                        queue.put_nowait(message)  # Add new
                    except (asyncio.QueueEmpty, asyncio.QueueFull):
                        pass  # Best effort


class DashboardSSEService:
    """Service for managing real-time dashboard SSE streaming.

    Features:
    - 5-second update intervals
    - 30-second heartbeat for connection keep-alive
    - Differential data transmission (only changed fields)
    - Integration with MetricsAggregationService
    """

    def __init__(self, config: DashboardStreamConfig | None = None) -> None:
        """Initialize DashboardSSEService.

        Args:
            config: Optional configuration, uses defaults if not provided.
        """
        self._config = config or DashboardStreamConfig()
        self._connection_manager = ConnectionManager(self._config)
        self._last_snapshot: DashboardMetricsSnapshot | None = None
        self._metrics_service = metrics_aggregation_service

    @property
    def update_interval_seconds(self) -> int:
        """Get the update interval in seconds."""
        return self._config.update_interval_seconds

    @property
    def heartbeat_interval_seconds(self) -> int:
        """Get the heartbeat interval in seconds."""
        return self._config.heartbeat_interval_seconds

    @property
    def connection_manager(self) -> ConnectionManager:
        """Get the connection manager."""
        return self._connection_manager

    def compute_differential(
        self,
        old_snapshot: DashboardMetricsSnapshot,
        new_snapshot: DashboardMetricsSnapshot,
    ) -> DifferentialUpdate:
        """Compute differential update between two snapshots.

        Args:
            old_snapshot: Previous metrics snapshot.
            new_snapshot: Current metrics snapshot.

        Returns:
            DifferentialUpdate containing only changed fields.
        """
        changed_fields: dict[str, Any] = {}

        old_dict = old_snapshot.to_dict()
        new_dict = new_snapshot.to_dict()

        for key, new_value in new_dict.items():
            old_value = old_dict.get(key)
            if old_value != new_value:
                changed_fields[key] = new_value

        return DifferentialUpdate(
            changed_fields=changed_fields,
            timestamp=datetime.now(),
        )

    def should_send_full_snapshot(self, is_new_or_reconnect: bool) -> bool:
        """Determine if full snapshot should be sent.

        Args:
            is_new_or_reconnect: Whether this is a new connection or reconnect.

        Returns:
            True if full snapshot should be sent.
        """
        return is_new_or_reconnect or self._last_snapshot is None

    async def fetch_current_metrics(self) -> DashboardMetricsSnapshot:
        """Fetch current metrics from the aggregation service.

        Returns:
            Current metrics snapshot.
        """
        from app.schemas.observability import RequirementDefinitionMetricsRequest

        try:
            request = RequirementDefinitionMetricsRequest()
            response = await self._metrics_service.get_requirement_definition_metrics(
                request
            )

            return DashboardMetricsSnapshot(
                average_score=response.metrics.average_score,
                total_turns=response.metrics.total_turns,
                completion_rate=response.metrics.completion_rate,
                total_sessions=response.metrics.total_sessions,
                model_usage=response.metrics.model_usage,
                timestamp=datetime.now(),
            )
        except Exception as e:
            logger.error(f"Error fetching metrics: {e}")
            # Return empty snapshot on error
            return DashboardMetricsSnapshot(timestamp=datetime.now())

    async def generate_metrics_event(
        self, is_initial: bool = False
    ) -> SSEMetricsEvent | None:
        """Generate a metrics update event.

        Args:
            is_initial: Whether this is the initial update.

        Returns:
            SSEMetricsEvent with metrics data, or None if no changes.
        """
        current_snapshot = await self.fetch_current_metrics()

        if is_initial or self._last_snapshot is None:
            # Send full snapshot
            self._last_snapshot = current_snapshot
            return SSEMetricsEvent(
                event_type="metrics_update",
                timestamp=datetime.now(),
                data={
                    "metrics": current_snapshot.to_dict(),
                    "is_full_snapshot": True,
                },
            )

        # Compute differential
        diff = self.compute_differential(self._last_snapshot, current_snapshot)

        if not diff.changed_fields:
            # No changes, no need to send
            return None

        self._last_snapshot = current_snapshot
        return SSEMetricsEvent(
            event_type="metrics_update",
            timestamp=datetime.now(),
            data={
                "changed_fields": diff.changed_fields,
                "is_full_snapshot": False,
            },
        )

    def generate_heartbeat_event(self) -> SSEMetricsEvent:
        """Generate a heartbeat event.

        Returns:
            SSEMetricsEvent with heartbeat type.
        """
        return SSEMetricsEvent(
            event_type="heartbeat",
            timestamp=datetime.now(),
            data={},
        )

    def generate_connected_event(self, client_id: str) -> SSEMetricsEvent:
        """Generate a connected event for new clients.

        Args:
            client_id: The client's identifier.

        Returns:
            SSEMetricsEvent with connected type.
        """
        return SSEMetricsEvent(
            event_type="connected",
            timestamp=datetime.now(),
            data={"client_id": client_id},
        )

    def generate_error_event(self, message: str) -> SSEMetricsEvent:
        """Generate an error event.

        Args:
            message: Error message.

        Returns:
            SSEMetricsEvent with error type.
        """
        return SSEMetricsEvent(
            event_type="error",
            timestamp=datetime.now(),
            data={"message": message},
        )


# Singleton instance
dashboard_sse_service = DashboardSSEService()
