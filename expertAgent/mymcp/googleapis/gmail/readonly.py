import base64
import logging
import re
from datetime import datetime, timedelta

from googleapiclient.errors import HttpError

from mymcp.googleapis.googleapi_services import get_googleapis_service
from mymcp.utils.extract_knowledge_from_text import extract_knowledge_from_text
from mymcp.utils.html_operation import convert_html_to_markdown

logger = logging.getLogger(__name__)

SERVICE_NAME = "gmail"


def _parse_relative_date(date_str: str) -> str | None:
    """
    相対日付文字列（例: "7d", "2w", "3m", "1y"）を絶対日付（YYYY/MM/DD）に変換します。

    Args:
        date_str: 相対日付文字列（例: "7d", "2w", "3m", "1y"）

    Returns:
        YYYY/MM/DD形式の日付文字列、または変換できない場合はNone
    """
    pattern = r"^(\d+)([dwmy])$"
    match = re.match(pattern, date_str)
    if not match:
        return None

    amount, unit = int(match.group(1)), match.group(2)
    today = datetime.now()

    if unit == "d":
        target_date = today - timedelta(days=amount)
    elif unit == "w":
        target_date = today - timedelta(weeks=amount)
    elif unit == "m":
        # 月の計算は概算（30日）
        target_date = today - timedelta(days=amount * 30)
    elif unit == "y":
        # 年の計算は概算（365日）
        target_date = today - timedelta(days=amount * 365)
    else:
        return None

    return target_date.strftime("%Y/%m/%d")


def _normalize_date(date_str: str) -> str:
    """
    日付文字列をGmail API形式（YYYY/MM/DD）に正規化します。

    Args:
        date_str: 日付文字列（YYYY/MM/DD, YYYY-MM-DD, または相対日付）

    Returns:
        YYYY/MM/DD形式の日付文字列

    Raises:
        ValueError: 日付形式が不正な場合
    """
    # 相対日付の場合
    relative = _parse_relative_date(date_str)
    if relative:
        return relative

    # YYYY-MM-DD を YYYY/MM/DD に変換
    if "-" in date_str:
        return date_str.replace("-", "/")

    # YYYY/MM/DD 形式の検証
    if re.match(r"^\d{4}/\d{2}/\d{2}$", date_str):
        return date_str

    raise ValueError(
        f"Invalid date format: {date_str}. Expected YYYY/MM/DD, YYYY-MM-DD, or relative (e.g., 7d)"
    )


def _build_search_query(
    keyword: str,
    search_in: str = "all",
    unread_only: bool = False,
    has_attachment: bool | None = None,
    date_after: str | None = None,
    date_before: str | None = None,
    labels: list[str] | None = None,
) -> str:
    """
    Gmail API検索クエリを構築します。

    Args:
        keyword: 検索キーワード
        search_in: 検索対象フィールド（"subject", "body", "from", "to", "all"）
        unread_only: 未読メールのみ検索
        has_attachment: 添付ファイルの有無でフィルタ
        date_after: 指定日以降のメールを検索
        date_before: 指定日以前のメールを検索
        labels: ラベルでフィルタ

    Returns:
        Gmail API検索クエリ文字列
    """
    query_parts = []

    # キーワード検索
    if keyword:
        if search_in == "subject":
            query_parts.append(f"subject:{keyword}")
        elif search_in == "from":
            query_parts.append(f"from:{keyword}")
        elif search_in == "to":
            query_parts.append(f"to:{keyword}")
        elif search_in == "body":
            query_parts.append(keyword)
        else:  # "all"
            query_parts.append(keyword)

    # 未読フィルタ
    if unread_only:
        query_parts.append("is:unread")

    # 添付ファイルフィルタ
    if has_attachment is True:
        query_parts.append("has:attachment")
    elif has_attachment is False:
        query_parts.append("-has:attachment")

    # 日付フィルタ
    if date_after:
        normalized_date = _normalize_date(date_after)
        query_parts.append(f"after:{normalized_date}")

    if date_before:
        normalized_date = _normalize_date(date_before)
        query_parts.append(f"before:{normalized_date}")

    # ラベルフィルタ
    if labels:
        for label in labels:
            query_parts.append(f"label:{label}")

    return " ".join(query_parts) if query_parts else ""


def search_emails(query: str, max_results: int = 100) -> list[str]:
    """
    Gmail APIを使用してメールを検索し、メッセージIDのリストを返します。

    Args:
        query: Gmail API検索クエリ
        max_results: 取得する最大件数（デフォルト: 100）

    Returns:
        メッセージIDのリスト

    Raises:
        HttpError: Gmail API呼び出しエラー
    """
    try:
        service = get_googleapis_service(SERVICE_NAME)
        if service is None:
            raise ValueError("Failed to get Gmail service")
        results = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=query,
                maxResults=max_results,
            )
            .execute()
        )

        messages = results.get("messages", [])
        return [msg["id"] for msg in messages]

    except HttpError as e:
        logger.error(f"Gmail API search error: {e}")
        raise


def parse_email_headers(payload: dict) -> dict:
    """
    メールヘッダーを解析して辞書形式で返します。

    Args:
        payload: Gmail APIメッセージのpayload

    Returns:
        ヘッダー情報の辞書
    """
    headers = {}
    for header in payload.get("headers", []):
        name = header.get("name", "")
        value = header.get("value", "")
        headers[name.lower()] = value

    return {
        "subject": headers.get("subject", ""),
        "from": headers.get("from", ""),
        "to": headers.get("to", "").split(", ") if headers.get("to") else [],
        "cc": headers.get("cc", "").split(", ") if headers.get("cc") else [],
        "date": headers.get("date", ""),
    }


def parse_email_body(payload: dict, prefer_html: bool = True) -> dict:
    """
    メール本文を解析してテキスト・HTML・Markdown形式で返します。

    Args:
        payload: Gmail APIメッセージのpayload
        prefer_html: HTML形式を優先するか（デフォルト: True）

    Returns:
        本文情報の辞書（body_text, body_html, body_markdown）
    """

    def _extract_body_data(part: dict, mime_type: str) -> str | None:
        """指定されたMIME typeの本文データを抽出"""
        if part.get("mimeType") == mime_type:
            body_data = part.get("body", {}).get("data")
            if body_data:
                try:
                    return base64.urlsafe_b64decode(body_data.encode("ASCII")).decode(
                        "utf-8"
                    )
                except Exception as e:
                    logger.warning(f"Failed to decode body data: {e}")
                    return None
        return None

    def _extract_from_parts(parts: list, mime_type: str) -> str | None:
        """パートリストから指定されたMIME typeの本文を再帰的に抽出"""
        for part in parts:
            # 直接抽出を試みる
            body = _extract_body_data(part, mime_type)
            if body:
                return body

            # ネストされたパートを再帰的に探索
            if "parts" in part:
                body = _extract_from_parts(part["parts"], mime_type)
                if body:
                    return body
        return None

    body_html = None
    body_text = None

    # マルチパートメールの場合
    if "parts" in payload:
        # HTML優先の場合
        if prefer_html:
            body_html = _extract_from_parts(payload["parts"], "text/html")
            if not body_html:
                body_text = _extract_from_parts(payload["parts"], "text/plain")
        else:
            body_text = _extract_from_parts(payload["parts"], "text/plain")
            if not body_text:
                body_html = _extract_from_parts(payload["parts"], "text/html")
    else:
        # シンプルなメールの場合
        mime_type = payload.get("mimeType", "")
        if mime_type == "text/html":
            body_html = _extract_body_data(payload, "text/html")
        elif mime_type == "text/plain":
            body_text = _extract_body_data(payload, "text/plain")

    # Markdown変換
    body_markdown = ""
    if body_html:
        body_markdown = convert_html_to_markdown(body_html)
        if not body_text:
            # HTMLのみの場合、Markdownをテキストとしても使用
            body_text = body_markdown
    elif body_text:
        body_markdown = convert_html_to_markdown(body_text)

    return {
        "body_text": body_text or "",
        "body_html": body_html or "",
        "body_markdown": body_markdown,
    }


def extract_attachments(payload: dict) -> list[dict]:
    """
    添付ファイルのメタデータを抽出します。

    Args:
        payload: Gmail APIメッセージのpayload

    Returns:
        添付ファイル情報のリスト
    """

    def _extract_from_parts(parts: list) -> list[dict]:
        """パートリストから添付ファイルを再帰的に抽出"""
        attachments = []
        for part in parts:
            filename = part.get("filename")
            if filename:
                attachment_id = part.get("body", {}).get("attachmentId")
                attachments.append(
                    {
                        "filename": filename,
                        "mimeType": part.get("mimeType", ""),
                        "size": part.get("body", {}).get("size", 0),
                        "attachmentId": attachment_id,
                    }
                )

            # ネストされたパートを再帰的に探索
            if "parts" in part:
                attachments.extend(_extract_from_parts(part["parts"]))

        return attachments

    if "parts" in payload:
        return _extract_from_parts(payload["parts"])
    return []


def get_email_details(
    message_id: str,
    include_body: bool = True,
    include_attachments: bool = True,
) -> dict:
    """
    メールの詳細情報を取得します。

    Args:
        message_id: メールID
        include_body: 本文を含めるか（デフォルト: True）
        include_attachments: 添付ファイル情報を含めるか（デフォルト: True）

    Returns:
        メール詳細情報の辞書

    Raises:
        HttpError: Gmail API呼び出しエラー
    """
    try:
        service = get_googleapis_service(SERVICE_NAME)
        if service is None:
            raise ValueError("Failed to get Gmail service")
        message = (
            service.users()
            .messages()
            .get(
                userId="me",
                id=message_id,
                format="full",
            )
            .execute()
        )

        payload = message.get("payload", {})
        headers = parse_email_headers(payload)

        # 基本情報
        email_data = {
            "id": message.get("id", ""),
            "thread_id": message.get("threadId", ""),
            "snippet": message.get("snippet", ""),
            "labels": message.get("labelIds", []),
            "is_unread": "UNREAD" in message.get("labelIds", []),
            **headers,
        }

        # 本文解析
        if include_body:
            body_data = parse_email_body(payload)
            email_data.update(body_data)

        # 添付ファイル抽出
        if include_attachments:
            attachments = extract_attachments(payload)
            email_data["has_attachments"] = len(attachments) > 0
            email_data["attachments"] = attachments
        else:
            email_data["has_attachments"] = False
            email_data["attachments"] = []

        return email_data

    except HttpError as e:
        logger.error(f"Gmail API get message error: {e}")
        raise


def get_emails_by_keyword(
    keyword: str,
    top: int = 5,
    search_in: str = "all",
    unread_only: bool = False,
    has_attachment: bool | None = None,
    date_after: str | None = None,
    date_before: str | None = None,
    labels: list[str] | None = None,
    include_summary: bool = False,
) -> dict:
    """
    指定された条件でメールを検索し、詳細情報を取得します。

    Args:
        keyword: 検索キーワード
        top: 取得するメールの最大件数（デフォルト: 5）
        search_in: 検索対象フィールド（"subject", "body", "from", "to", "all"）
        unread_only: 未読メールのみ検索（デフォルト: False）
        has_attachment: 添付ファイルの有無でフィルタ（True/False/None）
        date_after: 指定日以降のメールを検索（"YYYY/MM/DD", "YYYY-MM-DD", "7d"など）
        date_before: 指定日以前のメールを検索（"YYYY/MM/DD", "YYYY-MM-DD"など）
        labels: ラベルでフィルタ（例: ["important", "work"]）
        include_summary: AIサマリーを含めるか（デフォルト: False）

    Returns:
        dict: 検索結果とメール詳細情報
            - total_count: 検索結果の総数
            - returned_count: 実際に返却されたメール数
            - emails: メール詳細情報のリスト
            - summary: AIサマリー（include_summary=Trueの場合のみ）

    Raises:
        ValueError: パラメータが不正な場合
        HttpError: Gmail API呼び出しエラー

    Examples:
        # 過去7日間の未読メール
        get_emails_by_keyword("meeting", date_after="7d", unread_only=True)

        # 特定期間の添付ファイル付きメール
        get_emails_by_keyword("report", date_after="2025/10/01",
                             date_before="2025/10/15", has_attachment=True)

        # 件名検索のみ
        get_emails_by_keyword("invoice", search_in="subject")
    """
    try:
        # 検索クエリ構築
        query = _build_search_query(
            keyword=keyword,
            search_in=search_in,
            unread_only=unread_only,
            has_attachment=has_attachment,
            date_after=date_after,
            date_before=date_before,
            labels=labels,
        )

        logger.info(f"Gmail search query: {query}")

        # メール検索
        message_ids = search_emails(query, max_results=top)
        total_count = len(message_ids)

        if total_count == 0:
            logger.warning(f"No emails found with query: {query}")
            return {
                "total_count": 0,
                "returned_count": 0,
                "emails": [],
            }

        # メール詳細取得
        emails = []
        for message_id in message_ids[:top]:
            try:
                email_data = get_email_details(message_id)
                emails.append(email_data)
            except HttpError as e:
                logger.error(f"Failed to get email details for {message_id}: {e}")
                continue

        result = {
            "total_count": total_count,
            "returned_count": len(emails),
            "emails": emails,
        }

        # AIサマリー生成（オプション）
        if include_summary and emails:
            try:
                # メール本文を結合して1つの文字列として渡す
                combined_text = "\n\n---\n\n".join(
                    [
                        f"Subject: {email.get('subject', '')}\n"
                        f"From: {email.get('from', '')}\n"
                        f"Date: {email.get('date', '')}\n\n"
                        f"{email.get('body_markdown', '')}"
                        for email in emails
                    ]
                )
                summary = extract_knowledge_from_text(combined_text)
                result["summary"] = summary
            except Exception as e:
                logger.warning(f"Failed to generate summary: {e}")
                result["summary"] = ""

        return result

    except HttpError as e:
        logger.error(f"Gmail API error: {e}")
        return {
            "error": str(e),
            "error_code": getattr(e.resp, "status", None),
            "total_count": 0,
            "returned_count": 0,
            "emails": [],
        }
    except ValueError as e:
        logger.error(f"Parameter validation error: {e}")
        return {
            "error": str(e),
            "total_count": 0,
            "returned_count": 0,
            "emails": [],
        }
    except Exception as e:
        logger.exception("Unexpected error in get_emails_by_keyword")
        return {
            "error": f"Internal error: {str(e)}",
            "total_count": 0,
            "returned_count": 0,
            "emails": [],
        }
