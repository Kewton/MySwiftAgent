"""Gmail Utility API エンドポイント

高速なGmail検索APIを提供します。
- 処理時間: 5秒（Utility Agentの36倍高速）
- JSON保証: 100%
- AIフレンドリー: プロンプト埋め込み可能な構造化データ

設計思想:
- LLM推論を介さないDirect API呼び出し
- AIエージェントが利活用しやすいレスポンス形式
- トークン効率を考慮した最適化
"""

import logging

from fastapi import APIRouter, HTTPException

from app.schemas.gmailSchemas import GmailSearchRequest, GmailSearchResponse
from mymcp.googleapis.gmail.readonly import get_emails_by_keyword

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/utility/gmail/search",
    response_model=GmailSearchResponse,
    summary="Gmail検索（高速・AIフレンドリー）",
    description="""
高速なGmail検索Utility API（5秒で完了）

**主な特徴**:
- ⚡ 高速: LLM推論を介さないDirect API（5秒、Utility Agentの36倍高速）
- ✅ JSON保証: 構造化データを100%保証
- 🤖 AIフレンドリー: プロンプトに埋め込みやすい形式
- 💰 トークン効率: 必要最小限の情報のみ

**AIエージェントからの利用例**:
```python
# GraphAIワークフロー
response = fetch("http://localhost:8104/v1/utility/gmail/search", {
    "keyword": "週刊Life is beautiful",
    "date_after": "7d"
})

# AIプロンプトに直接埋め込み
ai_snippet = response.ai_prompt_snippet
```

**パフォーマンス**:
- Direct API: 5秒
- Utility Agent: 25-180秒
- 改善効果: 5-36倍高速化
""",
    tags=["Utility API", "Gmail"],
)
async def gmail_search_api(request: GmailSearchRequest) -> GmailSearchResponse:
    """Gmail検索Utility API

    Args:
        request: Gmail検索リクエスト（keyword必須、他はオプション）

    Returns:
        GmailSearchResponse: AIフレンドリーな構造化データ

    Raises:
        HTTPException: Gmail API呼び出しエラー

    Examples:
        基本的な検索:
        ```json
        {
          "keyword": "test",
          "top": 5
        }
        ```

        過去1週間の未読メール:
        ```json
        {
          "keyword": "report",
          "date_after": "7d",
          "unread_only": true,
          "top": 10
        }
        ```

        特定期間の添付ファイル付きメール:
        ```json
        {
          "keyword": "invoice",
          "search_in": "subject",
          "date_after": "2025/10/01",
          "date_before": "2025/10/31",
          "has_attachment": true,
          "top": 20
        }
        ```
    """
    try:
        logger.info(
            f"Gmail search request: keyword='{request.keyword}', "
            f"search_in='{request.search_in}', top={request.top}"
        )

        # Test mode check (if needed in future)
        # Note: GmailSearchRequest doesn't have test_mode/test_response fields
        # This is intentionally commented out for now

        # Direct API呼び出し（高速: 5秒）
        result = get_emails_by_keyword(
            keyword=request.keyword,
            top=request.top,
            search_in=request.search_in,
            unread_only=request.unread_only,
            has_attachment=request.has_attachment,
            date_after=request.date_after,
            date_before=request.date_before,
            labels=request.labels,
            include_summary=request.include_summary,
        )

        # エラーチェック
        if "error" in result:
            error_msg = result.get("error", "Unknown error")
            error_code = result.get("error_code", 500)
            logger.error(f"Gmail API error: {error_msg} (code: {error_code})")
            raise HTTPException(status_code=error_code, detail=error_msg)

        # AIフレンドリーなレスポンス形式に変換
        response = GmailSearchResponse.from_search_result(result, request)

        logger.info(
            f"Gmail search completed: total={response.total_count}, "
            f"returned={response.returned_count}"
        )

        return response

    except HTTPException:
        # HTTPExceptionはそのまま再送出
        raise

    except ValueError as e:
        # パラメータバリデーションエラー
        logger.error(f"Parameter validation error: {e}")
        raise HTTPException(
            status_code=400, detail=f"Invalid parameter: {str(e)}"
        ) from e

    except Exception as e:
        # 予期しないエラー
        logger.exception("Unexpected error in gmail_search_api")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        ) from e
