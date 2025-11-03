"""Observability API endpoints for Langfuse tracing.

このモジュールはLangfuseトレーシング情報を取得・管理するAPIエンドポイントを提供します。
トレース一覧取得、詳細情報、フィードバック投稿などの機能を実装します。

Issue #113: Langfuse Self-hosted統合 - Observability API
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.exceptions import ServiceError
from app.schemas.observability import (
    ScoreRequest,
    ScoreResponse,
    TraceDetail,
    TraceListRequest,
    TraceListResponse,
)
from app.services.observability_service import ObservabilityService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["observability"], prefix="/observability")
_observability_service = ObservabilityService()


def get_observability_service() -> ObservabilityService:
    """Return the shared ObservabilityService instance."""
    return _observability_service


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
