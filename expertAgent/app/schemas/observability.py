"""Observability API schemas for Langfuse tracing.

Issue #113: Langfuse Self-hosted統合 - Observability API
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TraceListRequest(BaseModel):
    """トレース一覧取得リクエスト."""

    user_id: str | None = Field(None, description="Filter by user ID")
    session_id: str | None = Field(None, description="Filter by session ID")
    tags: list[str] | None = Field(None, description="Filter by tags")
    limit: int = Field(50, ge=1, le=1000, description="Number of traces to return")
    offset: int = Field(0, ge=0, description="Offset for pagination")


class TraceItem(BaseModel):
    """トレースアイテム（一覧表示用）."""

    id: str = Field(..., description="Trace ID")
    name: str | None = Field(None, description="Trace name")
    user_id: str | None = Field(None, description="User ID")
    session_id: str | None = Field(None, description="Session ID")
    timestamp: datetime = Field(..., description="Trace creation timestamp")
    tags: list[str] = Field(default_factory=list, description="Tags")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata")
    langfuse_url: str | None = Field(None, description="Langfuse UI URL")


class TraceListResponse(BaseModel):
    """トレース一覧取得レスポンス."""

    traces: list[TraceItem] = Field(..., description="List of traces")
    total: int = Field(..., description="Total number of traces")
    limit: int = Field(..., description="Limit used")
    offset: int = Field(..., description="Offset used")


class ObservationItem(BaseModel):
    """Observation アイテム（Generation/Span/Event）."""

    id: str = Field(..., description="Observation ID")
    type: str = Field(..., description="Type: generation, span, event")
    name: str | None = Field(None, description="Observation name")
    start_time: datetime | None = Field(None, description="Start time")
    end_time: datetime | None = Field(None, description="End time")
    input: Any = Field(None, description="Input data")
    output: Any = Field(None, description="Output data")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata")
    model: str | None = Field(None, description="Model name (for generations)")
    usage: dict[str, Any] | None = Field(None, description="Token usage")


class TraceDetail(BaseModel):
    """トレース詳細."""

    id: str = Field(..., description="Trace ID")
    name: str | None = Field(None, description="Trace name")
    user_id: str | None = Field(None, description="User ID")
    session_id: str | None = Field(None, description="Session ID")
    timestamp: datetime = Field(..., description="Trace creation timestamp")
    tags: list[str] = Field(default_factory=list, description="Tags")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Metadata")
    observations: list[ObservationItem] = Field(
        default_factory=list, description="Child observations"
    )
    langfuse_url: str | None = Field(None, description="Langfuse UI URL")


class ScoreRequest(BaseModel):
    """フィードバック送信リクエスト."""

    trace_id: str = Field(..., description="Trace ID to score")
    name: str = Field(..., description="Score name (e.g., 'user_rating', 'accuracy')")
    value: float = Field(..., ge=0.0, le=1.0, description="Score value (0.0 - 1.0)")
    comment: str | None = Field(None, description="Optional comment")


class ScoreResponse(BaseModel):
    """フィードバック送信レスポンス."""

    success: bool = Field(..., description="Whether score was successfully submitted")
    score_id: str | None = Field(None, description="Score ID if available")
    message: str = Field(..., description="Response message")
