"""Gmail Utility API エンドポイント

高速なGmail検索・送信APIを提供します。
- 処理時間: 3-5秒（Utility Agentの36倍高速）
- JSON保証: 100%
- AIフレンドリー: プロンプト埋め込み可能な構造化データ

設計思想:
- LLM推論を介さないDirect API呼び出し
- AIエージェントが利活用しやすいレスポンス形式
- トークン効率を考慮した最適化
"""

import logging

from fastapi import APIRouter, HTTPException
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from app.schemas.gmailSchemas import (
    GmailSearchRequest,
    GmailSearchResponse,
    GmailSendRequest,
    GmailSendResponse,
)
from core.test_mode_handler import handle_test_mode
from mymcp.googleapis.gmail.readonly import get_emails_by_keyword
from mymcp.googleapis.gmail.send import send_email_v2

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

        # テストモードチェック
        test_result = handle_test_mode(
            request.test_mode, request.test_response, "gmail_search"
        )
        if test_result is not None:
            # Type cast for test mode response
            return test_result  # type: ignore[return-value]

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


@router.post(
    "/utility/gmail/send",
    response_model=GmailSendResponse,
    summary="Gmail送信（高速・AIフレンドリー）",
    description="""
高速なGmail送信Utility API（3秒で完了）

**主な特徴**:
- ⚡ 高速: LLM推論を介さないDirect API（3秒、Action Agentの6-20倍高速）
- ✅ JSON保証: 構造化データを100%保証
- 🤖 AIフレンドリー: message_id, thread_id等のメタデータを返却
- 🎯 動的宛先指定: リクエストボディで宛先を指定可能

**AIエージェントからの利用例**:
```python
# GraphAIワークフロー
response = fetch("http://localhost:8104/v1/utility/gmail/send", {
    "to": "recipient@example.com",
    "subject": "作業完了通知",
    "body": "本日の作業が完了しました。"
})

# 送信結果を次のノードで利用
message_id = response.message_id
```

**パフォーマンス**:
- Direct API: 3秒
- Action Agent: 20-60秒
- 改善効果: 6-20倍高速化

**Action Agentとの使い分け**:
- **Utility API**: ワークフローで確実にメール送信（宛先を動的指定）
- **Action Agent**: LLMが送信判断（条件付き送信、宛先は環境変数固定）
""",
    tags=["Utility API", "Gmail"],
)
async def gmail_send_api(request: GmailSendRequest) -> GmailSendResponse:
    """Gmail送信Utility API

    Args:
        request: Gmail送信リクエスト（to, subject, body必須）

    Returns:
        GmailSendResponse: AIフレンドリーな構造化データ

    Raises:
        HTTPException: Gmail API呼び出しエラー

    Examples:
        基本的な送信:
        ```json
        {
          "to": "recipient@example.com",
          "subject": "テストメール",
          "body": "これはテストメールです。"
        }
        ```

        複数宛先:
        ```json
        {
          "to": ["user1@example.com", "user2@example.com"],
          "subject": "重要なお知らせ",
          "body": "プロジェクト進捗報告\\n\\n本日の作業内容..."
        }
        ```

        MyVault認証:
        ```json
        {
          "to": "manager@example.com",
          "subject": "日次レポート",
          "body": "本日の分析結果...",
          "project": "default_project"
        }
        ```
    """
    try:
        logger.info(
            f"Gmail send request: to='{request.to}', subject='{request.subject}'"
        )

        # テストモードチェック
        test_result = handle_test_mode(
            request.test_mode, request.test_response, "gmail_send"
        )
        if test_result is not None:
            # Type cast for test mode response
            return test_result  # type: ignore[return-value]

        # 宛先をリスト化
        to_list = [request.to] if isinstance(request.to, str) else request.to

        # Direct API呼び出し（高速: 3秒）
        result = send_email_v2(
            to_emails=to_list,
            subject=request.subject,
            body=request.body,
            project=request.project,
        )

        # AIフレンドリーなレスポンス形式に変換
        response = GmailSendResponse.from_gmail_result(result, request)

        logger.info(
            f"Gmail send completed: message_id={response.message_id}, "
            f"sent_to={response.sent_to}"
        )

        return response

    except RefreshError as e:
        # 認証エラー
        logger.error(f"Gmail authentication failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=401,
            detail="Gmail API authentication failed. Please check your credentials.",
        ) from e

    except HttpError as e:
        # Gmail APIエラー
        error_details = f"Status: {e.resp.status}, Content: {e.content.decode('utf-8')}"
        logger.error(f"Gmail API error: {error_details}", exc_info=True)
        raise HTTPException(
            status_code=e.resp.status,
            detail=f"Gmail API error: {error_details}",
        ) from e

    except ValueError as e:
        # パラメータバリデーションエラー
        logger.error(f"Parameter validation error: {e}")
        raise HTTPException(
            status_code=400, detail=f"Invalid parameter: {str(e)}"
        ) from e

    except Exception as e:
        # 予期しないエラー
        logger.exception("Unexpected error in gmail_send_api")
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        ) from e
