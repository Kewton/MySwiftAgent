"""Dashboard SSE schemas for real-time metrics streaming.

Issue #176: Real-time Dashboard Implementation
- SSE streaming for metrics updates
- Differential data transmission
- Heartbeat support
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.observability import ModelUsage


class SSEMetricsEvent(BaseModel):
    """SSE event for metrics updates and heartbeats.

    Attributes:
        event_type: Type of event (metrics_update, heartbeat, error)
        timestamp: When the event was generated
        data: Event payload data
    """

    event_type: str = Field(
        ...,
        description="Event type: metrics_update, heartbeat, error, connected",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Event timestamp",
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Event data payload",
    )


class DashboardMetricsSnapshot(BaseModel):
    """Snapshot of dashboard metrics at a point in time.

    Used for tracking state and computing differential updates.
    """

    average_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Average quality score (0.0 - 1.0)",
    )
    total_turns: int = Field(
        default=0,
        ge=0,
        description="Total dialogue turns",
    )
    completion_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Completion rate percentage (0.0 - 100.0)",
    )
    total_sessions: int = Field(
        default=0,
        ge=0,
        description="Total number of sessions",
    )
    model_usage: list[ModelUsage] = Field(
        default_factory=list,
        description="Model usage statistics",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Snapshot timestamp",
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert snapshot to dictionary for comparison."""
        return {
            "average_score": self.average_score,
            "total_turns": self.total_turns,
            "completion_rate": self.completion_rate,
            "total_sessions": self.total_sessions,
            "model_usage": [m.model_dump() for m in self.model_usage],
        }


class DifferentialUpdate(BaseModel):
    """Differential update containing only changed fields.

    Used to minimize data transmission by only sending changed values.
    """

    changed_fields: dict[str, Any] = Field(
        default_factory=dict,
        description="Dictionary of changed field names and their new values",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="Update timestamp",
    )


class SSEConnectionInfo(BaseModel):
    """Information about an SSE connection.

    Tracks connection metadata for monitoring and debugging.
    """

    client_id: str = Field(..., description="Unique client identifier")
    connected_at: datetime = Field(
        default_factory=datetime.now,
        description="Connection start time",
    )
    last_message_at: datetime | None = Field(
        None,
        description="Last message sent to client",
    )
    messages_sent: int = Field(
        default=0,
        ge=0,
        description="Total messages sent to this client",
    )


class DashboardStreamConfig(BaseModel):
    """Configuration for dashboard SSE streaming.

    Defines intervals and limits for the streaming service.
    """

    update_interval_seconds: int = Field(
        default=5,
        ge=1,
        description="Interval between metrics updates (default: 5 seconds)",
    )
    heartbeat_interval_seconds: int = Field(
        default=30,
        ge=5,
        description="Interval between heartbeat messages (default: 30 seconds)",
    )
    max_connections: int = Field(
        default=100,
        ge=1,
        description="Maximum concurrent client connections",
    )
    queue_max_size: int = Field(
        default=50,
        ge=10,
        description="Maximum size of per-client message queue",
    )
