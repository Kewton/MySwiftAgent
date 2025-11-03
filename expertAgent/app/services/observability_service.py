"""Observability service for Langfuse tracing management.

このサービスはLangfuseトレーシング情報の取得・管理機能を提供します。
トレース一覧、詳細情報、フィードバック投稿などの機能を統合します。

Issue #113: Langfuse Self-hosted統合 - Observability API
"""

import logging
from datetime import datetime

from app.schemas.observability import (
    ObservationItem,
    ScoreRequest,
    ScoreResponse,
    TraceDetail,
    TraceItem,
    TraceListRequest,
    TraceListResponse,
)
from app.services.langfuse_service import langfuse_service
from app.services.trace_service import trace_service

from .base import BaseService
from .response_builder import ResponseBuilder

logger = logging.getLogger(__name__)


class ObservabilityService(BaseService):
    """Observability operations for Langfuse tracing."""

    def __init__(self) -> None:
        super().__init__(logger=logger, response_builder=ResponseBuilder())

    async def get_traces(self, request: TraceListRequest) -> TraceListResponse:
        """トレース一覧を取得.

        Args:
            request: トレース一覧取得リクエスト

        Returns:
            TraceListResponse: トレース一覧レスポンス

        Raises:
            ValueError: Langfuseが無効な場合
        """
        if not trace_service._is_enabled():
            raise ValueError("Langfuse is not enabled")

        # Langfuse API からトレース一覧を取得
        raw_traces = trace_service.get_traces(
            limit=request.limit + request.offset,  # offsetを考慮
            user_id=request.user_id,
            tags=request.tags,
        )

        if raw_traces is None:
            # エラー時は空のリストを返す
            return TraceListResponse(
                traces=[],
                total=0,
                limit=request.limit,
                offset=request.offset,
            )

        # offsetを適用してスライス
        paginated_traces = raw_traces[request.offset : request.offset + request.limit]

        # Pydanticモデルに変換
        trace_items = []
        for raw_trace in paginated_traces:
            try:
                trace_item = TraceItem(
                    id=raw_trace.get("id", ""),
                    name=raw_trace.get("name"),
                    user_id=raw_trace.get("userId"),
                    session_id=raw_trace.get("sessionId"),
                    timestamp=datetime.fromisoformat(
                        raw_trace.get("timestamp", datetime.now().isoformat())
                    ),
                    tags=raw_trace.get("tags", []),
                    metadata=raw_trace.get("metadata", {}),
                    langfuse_url=trace_service.get_trace_url(raw_trace.get("id", "")),
                )
                trace_items.append(trace_item)
            except Exception as e:
                self.logger.warning(f"Failed to parse trace item: {e}")
                continue

        return TraceListResponse(
            traces=trace_items,
            total=len(raw_traces),
            limit=request.limit,
            offset=request.offset,
        )

    async def get_trace_detail(self, trace_id: str) -> TraceDetail | None:
        """トレース詳細を取得.

        Args:
            trace_id: トレースID

        Returns:
            TraceDetail or None: トレース詳細

        Raises:
            ValueError: Langfuseが無効な場合
        """
        if not trace_service._is_enabled():
            raise ValueError("Langfuse is not enabled")

        # トレース基本情報を取得
        raw_trace = trace_service.get_trace_by_id(trace_id)
        if raw_trace is None:
            return None

        # Observationsを取得
        raw_observations = trace_service.get_observations_by_trace(trace_id)
        observations = []

        if raw_observations:
            for raw_obs in raw_observations:
                try:
                    obs_item = ObservationItem(
                        id=raw_obs.get("id", ""),
                        type=raw_obs.get("type", "unknown"),
                        name=raw_obs.get("name"),
                        start_time=(
                            datetime.fromisoformat(raw_obs["startTime"])
                            if raw_obs.get("startTime")
                            else None
                        ),
                        end_time=(
                            datetime.fromisoformat(raw_obs["endTime"])
                            if raw_obs.get("endTime")
                            else None
                        ),
                        input=raw_obs.get("input"),
                        output=raw_obs.get("output"),
                        metadata=raw_obs.get("metadata", {}),
                        model=raw_obs.get("model"),
                        usage=raw_obs.get("usage"),
                    )
                    observations.append(obs_item)
                except Exception as e:
                    self.logger.warning(f"Failed to parse observation: {e}")
                    continue

        # TraceDetailに変換
        trace_detail = TraceDetail(
            id=raw_trace.get("id", trace_id),
            name=raw_trace.get("name"),
            user_id=raw_trace.get("userId"),
            session_id=raw_trace.get("sessionId"),
            timestamp=datetime.fromisoformat(
                raw_trace.get("timestamp", datetime.now().isoformat())
            ),
            tags=raw_trace.get("tags", []),
            metadata=raw_trace.get("metadata", {}),
            observations=observations,
            langfuse_url=trace_service.get_trace_url(trace_id),
        )

        return trace_detail

    async def submit_score(self, request: ScoreRequest) -> ScoreResponse:
        """フィードバックスコアを送信.

        Args:
            request: スコア送信リクエスト

        Returns:
            ScoreResponse: スコア送信レスポンス
        """
        if not langfuse_service._is_enabled():
            return ScoreResponse(
                success=False,
                score_id=None,
                message="Langfuse is not enabled",
            )

        # LangfuseServiceのscore_traceメソッドを使用
        success = langfuse_service.score_trace(
            trace_id=request.trace_id,
            name=request.name,
            value=request.value,
            comment=request.comment,
        )

        if success:
            return ScoreResponse(
                success=True,
                score_id=None,  # Langfuse APIがscore IDを返す場合はここに設定
                message=f"Score '{request.name}' successfully submitted for trace {request.trace_id}",
            )
        else:
            return ScoreResponse(
                success=False,
                score_id=None,
                message="Failed to submit score",
            )
