"""Observability API endpoints for Langfuse tracing.

このモジュールはLangfuseトレーシング情報を取得・管理するAPIエンドポイントを提供します。
トレース一覧取得、詳細情報、フィードバック投稿などの機能を実装します。

Issue #113: Langfuse Self-hosted統合 - Observability API
Issue #175: 品質可視化API実装 - Requirement Definition Metrics
Issue #176: リアルタイムダッシュボード実装 - SSE Streaming
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Any, AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query
from sse_starlette.sse import EventSourceResponse

from app.exceptions import ServiceError
from app.schemas.observability import (
    RequirementDefinitionMetricsRequest,
    RequirementDefinitionMetricsResponse,
    ScoreRequest,
    ScoreResponse,
    TraceDetail,
    TraceListRequest,
    TraceListResponse,
)
from app.services.dashboard_sse_service import (
    DashboardSSEService,
    dashboard_sse_service,
)
from app.services.metrics_aggregation_service import MetricsAggregationService
from app.services.observability_service import ObservabilityService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["observability"], prefix="/observability")
_observability_service = ObservabilityService()
_metrics_aggregation_service = MetricsAggregationService()


def get_observability_service() -> ObservabilityService:
    """Return the shared ObservabilityService instance."""
    return _observability_service


def get_metrics_aggregation_service() -> MetricsAggregationService:
    """Return the shared MetricsAggregationService instance."""
    return _metrics_aggregation_service


@router.get(
    "/traces",
    response_model=TraceListResponse,
    summary="Get trace list",
    description="Langfuseからトレース一覧を取得します。user_id, session_id, tagsでフィルタ可能です。",
)
async def get_traces(
    user_id: str | None = Query(None, description="Filter by user ID"),
    session_id: str | None = Query(None, description="Filter by session ID"),
    tags: str | None = Query(None, description="Filter by tags (comma-separated)"),
    limit: int = Query(50, ge=1, le=1000, description="Number of traces to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    service: ObservabilityService = Depends(get_observability_service),
) -> TraceListResponse:
    """トレース一覧を取得するエンドポイント.

    Args:
        user_id: ユーザーIDでフィルタ
        session_id: セッションIDでフィルタ
        tags: タグでフィルタ（カンマ区切り）
        limit: 取得件数
        offset: ページネーション用オフセット
        service: ObservabilityService dependency

    Returns:
        TraceListResponse: トレース一覧

    Raises:
        HTTPException: エラー発生時
    """
    try:
        # タグをリストに変換
        tags_list = tags.split(",") if tags else None

        request = TraceListRequest(
            user_id=user_id,
            session_id=session_id,
            tags=tags_list,
            limit=limit,
            offset=offset,
        )

        return await service.get_traces(request)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ServiceError as e:
        logger.exception("Service error getting traces")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception:
        logger.exception("Unexpected error getting traces")
        raise HTTPException(status_code=500, detail="Internal server error") from None


@router.get(
    "/traces/{trace_id}",
    response_model=TraceDetail,
    summary="Get trace detail",
    description="指定されたトレースIDの詳細情報（observations含む）を取得します。",
)
async def get_trace_detail(
    trace_id: str,
    service: ObservabilityService = Depends(get_observability_service),
) -> TraceDetail:
    """トレース詳細を取得するエンドポイント.

    Args:
        trace_id: トレースID
        service: ObservabilityService dependency

    Returns:
        TraceDetail: トレース詳細

    Raises:
        HTTPException: トレースが見つからない、またはエラー発生時
    """
    try:
        trace_detail = await service.get_trace_detail(trace_id)

        if trace_detail is None:
            raise HTTPException(
                status_code=404,
                detail=f"Trace not found: {trace_id}",
            )

        return trace_detail

    except HTTPException:
        raise
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ServiceError as e:
        logger.exception(f"Service error getting trace {trace_id}")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception:
        logger.exception(f"Unexpected error getting trace {trace_id}")
        raise HTTPException(status_code=500, detail="Internal server error") from None


@router.post(
    "/scores",
    response_model=ScoreResponse,
    summary="Submit feedback score",
    description="トレースに対するフィードバックスコアを送信します（例: user_rating, accuracy）。",
)
async def submit_score(
    request: ScoreRequest,
    service: ObservabilityService = Depends(get_observability_service),
) -> ScoreResponse:
    """フィードバックスコアを送信するエンドポイント.

    Args:
        request: スコア送信リクエスト
        service: ObservabilityService dependency

    Returns:
        ScoreResponse: スコア送信結果

    Raises:
        HTTPException: エラー発生時
    """
    try:
        response = await service.submit_score(request)

        if not response.success:
            raise HTTPException(
                status_code=500,
                detail=response.message,
            )

        return response

    except HTTPException:
        raise
    except ServiceError as e:
        logger.exception("Service error submitting score")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception:
        logger.exception("Unexpected error submitting score")
        raise HTTPException(status_code=500, detail="Internal server error") from None


@router.get(
    "/requirement-definition-metrics",
    response_model=RequirementDefinitionMetricsResponse,
    summary="Get requirement definition metrics",
    description="要件定義会話の品質メトリクスを取得します。平均スコア、対話ターン数、完了率、モデル使用率を集計します。",
)
async def get_requirement_definition_metrics(
    from_date: datetime | None = Query(
        None, description="Start date for metrics (default: 30 days ago)"
    ),
    to_date: datetime | None = Query(
        None, description="End date for metrics (default: today)"
    ),
    service: MetricsAggregationService = Depends(get_metrics_aggregation_service),
) -> RequirementDefinitionMetricsResponse:
    """要件定義メトリクスを取得するエンドポイント.

    Args:
        from_date: 開始日（デフォルト: 30日前）
        to_date: 終了日（デフォルト: 今日）
        service: MetricsAggregationService dependency

    Returns:
        RequirementDefinitionMetricsResponse: 集計メトリクス

    Raises:
        HTTPException: エラー発生時
    """
    try:
        # Create request with optional date overrides
        request_data = {}
        if from_date is not None:
            request_data["from_date"] = from_date
        if to_date is not None:
            request_data["to_date"] = to_date

        request = RequirementDefinitionMetricsRequest(**request_data)
        return await service.get_requirement_definition_metrics(request)

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e)) from e
    except ServiceError as e:
        logger.exception("Service error getting metrics")
        raise HTTPException(status_code=500, detail=str(e)) from e
    except Exception:
        logger.exception("Unexpected error getting metrics")
        raise HTTPException(status_code=500, detail="Internal server error") from None


# ========================================
# Issue #176: Real-time Dashboard SSE Streaming
# ========================================


def get_dashboard_sse_service() -> DashboardSSEService:
    """Return the shared DashboardSSEService instance."""
    return dashboard_sse_service


@router.get(
    "/dashboard/stream",
    summary="Stream dashboard metrics (SSE)",
    description="""
リアルタイムダッシュボードメトリクスをServer-Sent Events (SSE)でストリーミングします。

特徴:
- 5秒ごとにメトリクス更新
- 30秒ごとにハートビート送信
- 差分データのみ送信（帯域幅最適化）
- 最大100クライアント同時接続対応

SSEイベントタイプ:
- connected: 接続確立時
- metrics_update: メトリクス更新時
- heartbeat: 接続維持用
- error: エラー発生時
""",
)
async def stream_dashboard_metrics(
    service: DashboardSSEService = Depends(get_dashboard_sse_service),
) -> EventSourceResponse:
    """リアルタイムダッシュボードメトリクスをストリーミング.

    Server-Sent Events (SSE) を使用してリアルタイムメトリクスを配信します。

    Returns:
        EventSourceResponse: SSEストリーム

    SSE Events:
        - data: {"event_type": "connected", "data": {"client_id": "..."}}
        - data: {"event_type": "metrics_update", "data": {"metrics": {...}}}
        - data: {"event_type": "heartbeat", "data": {}}
        - data: {"event_type": "error", "data": {"message": "..."}}
    """

    async def event_generator() -> AsyncGenerator[dict[str, Any], None]:
        """Generate SSE events for dashboard metrics."""
        client_id = str(uuid.uuid4())

        try:
            # Register client connection
            await service.connection_manager.add_client(client_id)

            logger.info(f"Dashboard SSE client connected: {client_id}")

            # Send connected event
            connected_event = service.generate_connected_event(client_id)
            yield {
                "event": "message",
                "data": json.dumps(connected_event.model_dump(), default=str),
            }

            # Send initial metrics snapshot
            try:
                initial_event = await service.generate_metrics_event(is_initial=True)
                if initial_event:
                    yield {
                        "event": "message",
                        "data": json.dumps(initial_event.model_dump(), default=str),
                    }
            except Exception as e:
                logger.error(f"Error sending initial metrics: {e}")
                error_event = service.generate_error_event(str(e))
                yield {
                    "event": "message",
                    "data": json.dumps(error_event.model_dump(), default=str),
                }

            # Track time for updates and heartbeats
            last_update_time = asyncio.get_event_loop().time()
            last_heartbeat_time = asyncio.get_event_loop().time()

            # Main event loop
            while True:
                current_time = asyncio.get_event_loop().time()

                # Check if it's time for metrics update
                if current_time - last_update_time >= service.update_interval_seconds:
                    try:
                        metrics_event = await service.generate_metrics_event(
                            is_initial=False
                        )
                        if metrics_event:
                            yield {
                                "event": "message",
                                "data": json.dumps(
                                    metrics_event.model_dump(), default=str
                                ),
                            }
                    except Exception as e:
                        logger.error(f"Error generating metrics event: {e}")

                    last_update_time = current_time

                # Check if it's time for heartbeat
                if (
                    current_time - last_heartbeat_time
                    >= service.heartbeat_interval_seconds
                ):
                    heartbeat_event = service.generate_heartbeat_event()
                    yield {
                        "event": "message",
                        "data": json.dumps(heartbeat_event.model_dump(), default=str),
                    }
                    last_heartbeat_time = current_time

                # Sleep briefly to avoid busy waiting
                await asyncio.sleep(0.5)

        except asyncio.CancelledError:
            logger.info(f"Dashboard SSE client disconnected: {client_id}")
            raise
        except Exception as e:
            logger.error(f"Error in dashboard SSE stream: {e}", exc_info=True)
            error_event = service.generate_error_event(
                "An error occurred. Please reconnect."
            )
            yield {
                "event": "message",
                "data": json.dumps(error_event.model_dump(), default=str),
            }
        finally:
            # Clean up client connection
            await service.connection_manager.remove_client(client_id)
            logger.info(f"Dashboard SSE client cleanup completed: {client_id}")

    return EventSourceResponse(event_generator())
