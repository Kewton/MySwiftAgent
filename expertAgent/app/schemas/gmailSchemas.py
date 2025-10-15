"""Gmail Utility API用スキーマ定義

AIエージェントが利活用しやすいレスポンス形式を提供します。

設計思想:
- 高速性: LLM推論を介さないDirect API（5秒）
- JSON保証: 構造化データを100%保証
- AIフレンドリー: プロンプトに埋め込みやすい形式
- トークン効率: 必要最小限の情報のみ
"""

from typing import List, Optional

from pydantic import BaseModel, Field

# ========================================
# Request Schema
# ========================================


class GmailSearchRequest(BaseModel):
    """Gmail検索リクエスト

    高速なGmail検索を実行するためのパラメータを指定します。
    """

    keyword: str = Field(
        ...,
        description="検索キーワード（必須）",
    )

    top: int = Field(
        default=5,
        ge=1,
        le=100,
        description="取得するメールの最大件数（1-100）",
    )

    search_in: str = Field(
        default="all",
        pattern="^(subject|body|from|to|all)$",
        description="検索対象フィールド（subject/body/from/to/all）",
    )

    unread_only: bool = Field(
        default=False,
        description="未読メールのみ検索",
    )

    has_attachment: Optional[bool] = Field(
        default=None,
        description="添付ファイルの有無でフィルタ（True/False/None）",
    )

    date_after: Optional[str] = Field(
        default=None,
        description="指定日以降のメールを検索（YYYY/MM/DD, YYYY-MM-DD, or 7d/2w/3m/1y）",
    )

    date_before: Optional[str] = Field(
        default=None,
        description="指定日以前のメールを検索（YYYY/MM/DD or YYYY-MM-DD）",
    )

    labels: Optional[List[str]] = Field(
        default=None,
        description="ラベルでフィルタ（例: ['important', 'work']）",
    )

    include_summary: bool = Field(
        default=False,
        description="AIサマリーを含めるか（LLM呼び出しあり、処理時間+10-20秒）",
    )

    project: Optional[str] = Field(
        default=None,
        description="MyVaultプロジェクト名（認証情報取得用）",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "keyword": "週刊Life is beautiful",
                "top": 10,
                "search_in": "subject",
                "date_after": "7d",
                "unread_only": False,
                "include_summary": False,
                "project": "default",
            }
        }


# ========================================
# Response Schema (AIフレンドリー設計)
# ========================================


class GmailEmailDetail(BaseModel):
    """メール詳細情報（AIエージェント最適化版）

    AIエージェントが効率的に利用できるよう、以下の工夫を実装:
    - snippet: 本文全体の代わりに100文字要約（トークン90%削減）
    - bool/listフィールド: LLM推論不要な構造化データ
    - 必須/オプション分離: 常に必要な情報と詳細情報を分離
    """

    # ========================================
    # 基本情報（必須フィールド）
    # ========================================

    id: str = Field(
        ...,
        description="メールID",
    )

    subject: str = Field(
        ...,
        description="件名",
    )

    from_address: str = Field(
        ...,
        alias="from",
        description="送信者",
    )

    date: str = Field(
        ...,
        description="送信日時",
    )

    # ========================================
    # 本文（AI推論用・最重要）
    # ========================================

    body_text: str = Field(
        ...,
        description="本文（プレーンテキスト）- AIエージェントの主要入力",
    )

    snippet: str = Field(
        ...,
        description="スニペット（要約・100文字程度）- プロンプト埋め込み用",
    )

    # ========================================
    # メタデータ（条件分岐用）
    # ========================================

    is_unread: bool = Field(
        ...,
        description="未読フラグ",
    )

    has_attachments: bool = Field(
        ...,
        description="添付ファイル有無",
    )

    labels: List[str] = Field(
        default_factory=list,
        description="ラベルリスト",
    )

    # ========================================
    # オプション情報（詳細分析用）
    # ========================================

    to_addresses: List[str] = Field(
        default_factory=list,
        description="宛先リスト",
    )

    cc_addresses: List[str] = Field(
        default_factory=list,
        description="CCリスト",
    )

    thread_id: str = Field(
        default="",
        description="スレッドID",
    )

    # ========================================
    # 詳細情報（完全な本文が必要な場合のみ）
    # ========================================

    body_html: Optional[str] = Field(
        default=None,
        description="本文（HTML）- 必要時のみ取得",
    )

    body_markdown: Optional[str] = Field(
        default=None,
        description="本文（Markdown）- 必要時のみ取得",
    )

    attachments: List[dict] = Field(
        default_factory=list,
        description="添付ファイルリスト",
    )

    class Config:
        populate_by_name = True  # alias対応


class GmailSearchResponse(BaseModel):
    """Gmail検索レスポンス（AIエージェント最適化版）

    AIエージェントが効率的に利用できるよう、以下の機能を提供:
    - ai_prompt_snippet: プロンプトに直接埋め込める要約テキスト
    - query_info: 検索条件のサマリー（デバッグ用）
    - emails: 構造化されたメール詳細リスト
    """

    # ========================================
    # メタデータ
    # ========================================

    total_count: int = Field(
        ...,
        description="検索結果の総数",
    )

    returned_count: int = Field(
        ...,
        description="実際に返却されたメール数",
    )

    query_info: dict = Field(
        default_factory=dict,
        description="検索条件のサマリー（デバッグ用）",
    )

    # ========================================
    # メール詳細リスト（主要データ）
    # ========================================

    emails: List[GmailEmailDetail] = Field(
        default_factory=list, description="メール詳細情報のリスト"
    )

    # ========================================
    # AIサマリー（オプション）
    # ========================================

    summary: Optional[str] = Field(
        default=None,
        description="AIによる全体サマリー（include_summary=Trueの場合のみ）",
    )

    # ========================================
    # AIエージェント向けヘルパー
    # ========================================

    ai_prompt_snippet: str = Field(
        default="",
        description="AIプロンプトに直接埋め込み可能な要約テキスト",
    )

    @classmethod
    def from_search_result(
        cls, result: dict, request: GmailSearchRequest
    ) -> "GmailSearchResponse":
        """get_emails_by_keyword()の返却値からAIフレンドリーなレスポンスを生成

        Args:
            result: get_emails_by_keyword()の返却値
            request: 元のリクエストオブジェクト

        Returns:
            AIフレンドリーなGmailSearchResponse
        """
        emails = []
        for email in result.get("emails", []):
            # Use model_validate to handle 'from' alias properly
            email_data = {
                "id": email.get("id", ""),
                "subject": email.get("subject", ""),
                "from": email.get("from", ""),  # Use 'from' key for alias
                "date": email.get("date", ""),
                "body_text": email.get("body_text", ""),
                "snippet": email.get("snippet", ""),
                "is_unread": email.get("is_unread", False),
                "has_attachments": email.get("has_attachments", False),
                "labels": email.get("labels", []),
                "to_addresses": email.get("to", []),
                "cc_addresses": email.get("cc", []),
                "thread_id": email.get("thread_id", ""),
                "body_html": email.get("body_html"),
                "body_markdown": email.get("body_markdown"),
                "attachments": email.get("attachments", []),
            }
            emails.append(GmailEmailDetail.model_validate(email_data))

        # AIプロンプト用スニペット生成
        ai_prompt_snippet = cls._generate_ai_prompt_snippet(
            emails, result.get("total_count", 0), result.get("returned_count", 0)
        )

        # 検索条件サマリー生成
        query_info = cls._generate_query_info(result, request)

        return cls(
            total_count=result.get("total_count", 0),
            returned_count=result.get("returned_count", 0),
            query_info=query_info,
            emails=emails,
            summary=result.get("summary"),
            ai_prompt_snippet=ai_prompt_snippet,
        )

    @staticmethod
    def _generate_ai_prompt_snippet(
        emails: List[GmailEmailDetail], total_count: int, returned_count: int
    ) -> str:
        """AIプロンプト用スニペットを生成

        AIエージェントがプロンプトに直接埋め込める形式を生成します。
        トークン効率を考慮し、必要最小限の情報のみを含めます。

        Args:
            emails: メール詳細リスト
            total_count: 検索結果の総数
            returned_count: 実際に返却されたメール数

        Returns:
            AIプロンプト用スニペット
        """
        if not emails:
            return f"検索結果: {total_count}件（該当メールなし）"

        lines = [f"検索結果: {total_count}件中{returned_count}件を表示\n"]

        for i, email in enumerate(emails, 1):
            lines.append(f"【{i}】件名: {email.subject}")
            lines.append(f"送信者: {email.from_address}")
            lines.append(f"日時: {email.date}")

            # スニペット（100文字程度に制限）
            snippet_preview = (
                email.snippet[:100] + "..."
                if len(email.snippet) > 100
                else email.snippet
            )
            lines.append(f"要約: {snippet_preview}")

            # 追加メタデータ（条件付き）
            if email.is_unread:
                lines.append("状態: 未読")
            if email.has_attachments:
                lines.append(f"添付: {len(email.attachments)}件")

            lines.append("")  # 空行

        return "\n".join(lines)

    @staticmethod
    def _generate_query_info(result: dict, request: GmailSearchRequest) -> dict:
        """検索条件サマリーを生成

        Args:
            result: get_emails_by_keyword()の返却値
            request: 元のリクエストオブジェクト

        Returns:
            検索条件サマリー
        """
        query_info = {
            "keyword": request.keyword,
            "search_in": request.search_in,
            "top": request.top,
        }

        # オプションパラメータを追加
        if request.date_after:
            query_info["date_after"] = request.date_after
        if request.date_before:
            query_info["date_before"] = request.date_before
        if request.unread_only:
            query_info["unread_only"] = True
        if request.has_attachment is not None:
            query_info["has_attachment"] = request.has_attachment
        if request.labels:
            query_info["labels"] = request.labels

        return query_info

    class Config:
        json_schema_extra = {
            "example": {
                "total_count": 15,
                "returned_count": 10,
                "query_info": {
                    "keyword": "週刊Life is beautiful",
                    "search_in": "subject",
                    "date_after": "2025/10/01",
                },
                "emails": [
                    {
                        "id": "abc123",
                        "subject": "週刊Life is beautiful 2025年10月14日号",
                        "from": "中島聡 <nakajima@example.com>",
                        "date": "Mon, 14 Oct 2025 07:10:00 +0900",
                        "body_text": "今週のトピック...",
                        "snippet": "今週のトピック: オンデマンド・コンテンツの時代...",
                        "is_unread": False,
                        "has_attachments": False,
                        "labels": ["INBOX"],
                    }
                ],
                "ai_prompt_snippet": "検索結果: 15件中10件を表示\n\n【1】...",
            }
        }


# ========================================
# Gmail Send Schema
# ========================================


class GmailSendRequest(BaseModel):
    """Gmail送信リクエスト

    高速なGmail送信を実行するためのパラメータを指定します。
    """

    to: str | List[str] = Field(
        ...,
        description="宛先メールアドレス（必須）- 単一または複数指定可能",
    )

    subject: str = Field(
        ...,
        min_length=1,
        description="件名（必須・1文字以上）",
    )

    body: str = Field(
        ...,
        min_length=1,
        description="本文（必須・1文字以上）- プレーンテキスト",
    )

    # オプション（将来拡張用）
    cc: Optional[List[str]] = Field(
        default=None,
        description="CC宛先リスト（将来拡張）",
    )

    bcc: Optional[List[str]] = Field(
        default=None,
        description="BCC宛先リスト（将来拡張）",
    )

    html_body: Optional[str] = Field(
        default=None,
        description="HTML本文（将来拡張）",
    )

    # MyVault認証情報
    project: Optional[str] = Field(
        default=None,
        description="MyVaultプロジェクト名（認証情報取得用）",
    )

    # テストモード
    test_mode: bool = Field(
        default=False,
        description="テストモードフラグ",
    )

    test_response: Optional[dict | str] = Field(
        default=None,
        description="テストモード用モックレスポンス",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "to": "recipient@example.com",
                "subject": "テストメール",
                "body": "これはテストメールです。\n\nよろしくお願いします。",
                "project": "default_project",
            }
        }


class GmailSendResponse(BaseModel):
    """Gmail送信レスポンス（AIエージェント最適化版）

    AIエージェントが効率的に利用できるよう、以下の機能を提供:
    - success: 送信成功フラグ（bool）
    - message_id: GmailメッセージID
    - ai_summary: AIプロンプト用要約テキスト
    """

    # ========================================
    # 送信結果（必須フィールド）
    # ========================================

    success: bool = Field(
        ...,
        description="送信成功フラグ",
    )

    message_id: str = Field(
        ...,
        description="GmailメッセージID",
    )

    thread_id: str = Field(
        ...,
        description="スレッドID",
    )

    label_ids: List[str] = Field(
        default_factory=list,
        description="付与されたラベル（通常: ['SENT']）",
    )

    # ========================================
    # 送信情報サマリー
    # ========================================

    sent_to: List[str] = Field(
        default_factory=list,
        description="送信先リスト",
    )

    subject: str = Field(
        ...,
        description="送信した件名",
    )

    sent_at: str = Field(
        ...,
        description="送信日時（ISO8601形式）",
    )

    # ========================================
    # AIエージェント向けヘルパー
    # ========================================

    ai_summary: str = Field(
        default="",
        description="AIプロンプト用要約テキスト",
    )

    @classmethod
    def from_gmail_result(
        cls, result: dict, request: GmailSendRequest
    ) -> "GmailSendResponse":
        """send_email_v2()の返却値からAIフレンドリーなレスポンスを生成

        Args:
            result: send_email_v2()の返却値
            request: 元のリクエストオブジェクト

        Returns:
            AIフレンドリーなGmailSendResponse
        """
        # 宛先をリスト化
        sent_to = [request.to] if isinstance(request.to, str) else request.to

        # AI要約生成
        ai_summary = cls._generate_ai_summary(sent_to, request.subject)

        # ISO8601形式の送信日時
        from datetime import datetime, timezone

        sent_at = datetime.now(timezone.utc).isoformat()

        return cls(
            success=True,
            message_id=result.get("id", ""),
            thread_id=result.get("threadId", ""),
            label_ids=result.get("labelIds", ["SENT"]),
            sent_to=sent_to,
            subject=request.subject,
            sent_at=sent_at,
            ai_summary=ai_summary,
        )

    @staticmethod
    def _generate_ai_summary(sent_to: List[str], subject: str) -> str:
        """AI用要約を生成

        Args:
            sent_to: 送信先リスト
            subject: 件名

        Returns:
            AI用要約テキスト
        """
        recipients_str = ", ".join(sent_to)
        return f"{recipients_str} 宛にメール送信完了（件名: {subject}）"

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message_id": "18c5a2b3f4d6e890",
                "thread_id": "18c5a2b3f4d6e890",
                "label_ids": ["SENT"],
                "sent_to": ["recipient@example.com"],
                "subject": "テストメール",
                "sent_at": "2025-10-15T10:30:45+09:00",
                "ai_summary": "recipient@example.com 宛にメール送信完了（件名: テストメール）",
            }
        }
