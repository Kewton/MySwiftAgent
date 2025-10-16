"""
Gmail readonly機能のユニットテスト
"""

import base64
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from googleapiclient.errors import HttpError

from mymcp.googleapis.gmail.readonly import (
    _build_search_query,
    _normalize_date,
    _parse_relative_date,
    extract_attachments,
    get_email_details,
    get_emails_by_keyword,
    parse_email_body,
    parse_email_headers,
    search_emails,
)


class TestRelativeDateParsing:
    """相対日付解析のテスト"""

    def test_parse_relative_date_days(self):
        """日数指定の相対日付"""
        result = _parse_relative_date("7d")
        expected = (datetime.now() - timedelta(days=7)).strftime("%Y/%m/%d")
        assert result == expected

    def test_parse_relative_date_weeks(self):
        """週数指定の相対日付"""
        result = _parse_relative_date("2w")
        expected = (datetime.now() - timedelta(weeks=2)).strftime("%Y/%m/%d")
        assert result == expected

    def test_parse_relative_date_months(self):
        """月数指定の相対日付"""
        result = _parse_relative_date("3m")
        expected = (datetime.now() - timedelta(days=90)).strftime("%Y/%m/%d")
        assert result == expected

    def test_parse_relative_date_years(self):
        """年数指定の相対日付"""
        result = _parse_relative_date("1y")
        expected = (datetime.now() - timedelta(days=365)).strftime("%Y/%m/%d")
        assert result == expected

    def test_parse_relative_date_invalid(self):
        """無効な相対日付"""
        assert _parse_relative_date("invalid") is None
        assert _parse_relative_date("7x") is None
        assert _parse_relative_date("d7") is None


class TestDateNormalization:
    """日付正規化のテスト"""

    def test_normalize_date_slash_format(self):
        """スラッシュ形式の日付"""
        assert _normalize_date("2025/10/15") == "2025/10/15"

    def test_normalize_date_hyphen_format(self):
        """ハイフン形式の日付"""
        assert _normalize_date("2025-10-15") == "2025/10/15"

    def test_normalize_date_relative(self):
        """相対日付"""
        result = _normalize_date("7d")
        expected = (datetime.now() - timedelta(days=7)).strftime("%Y/%m/%d")
        assert result == expected

    def test_normalize_date_invalid(self):
        """無効な日付形式"""
        with pytest.raises(ValueError, match="Invalid date format"):
            _normalize_date("invalid date")

        with pytest.raises(ValueError, match="Invalid date format"):
            _normalize_date("20251301")  # 不正な形式


class TestBuildSearchQuery:
    """検索クエリ構築のテスト"""

    def test_build_query_keyword_only(self):
        """キーワードのみ"""
        query = _build_search_query("meeting")
        assert query == "meeting"

    def test_build_query_subject_search(self):
        """件名検索"""
        query = _build_search_query("invoice", search_in="subject")
        assert query == "subject:invoice"

    def test_build_query_from_search(self):
        """送信者検索"""
        query = _build_search_query("john@example.com", search_in="from")
        assert query == "from:john@example.com"

    def test_build_query_unread_only(self):
        """未読メールのみ"""
        query = _build_search_query("report", unread_only=True)
        assert "is:unread" in query

    def test_build_query_has_attachment_true(self):
        """添付ファイルあり"""
        query = _build_search_query("document", has_attachment=True)
        assert "has:attachment" in query

    def test_build_query_has_attachment_false(self):
        """添付ファイルなし"""
        query = _build_search_query("note", has_attachment=False)
        assert "-has:attachment" in query

    def test_build_query_date_after(self):
        """指定日以降"""
        query = _build_search_query("meeting", date_after="2025/10/01")
        assert "after:2025/10/01" in query

    def test_build_query_date_before(self):
        """指定日以前"""
        query = _build_search_query("meeting", date_before="2025/10/15")
        assert "before:2025/10/15" in query

    def test_build_query_labels(self):
        """ラベルフィルタ"""
        query = _build_search_query("task", labels=["important", "work"])
        assert "label:important" in query
        assert "label:work" in query

    def test_build_query_combined(self):
        """複合条件"""
        query = _build_search_query(
            "project",
            search_in="subject",
            unread_only=True,
            has_attachment=True,
            date_after="2025/10/01",
            labels=["work"],
        )
        assert "subject:project" in query
        assert "is:unread" in query
        assert "has:attachment" in query
        assert "after:2025/10/01" in query
        assert "label:work" in query


class TestSearchEmails:
    """メール検索のテスト"""

    @patch("mymcp.googleapis.gmail.readonly.get_googleapis_service")
    def test_search_emails_success(self, mock_get_service):
        """正常な検索"""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mock_service.users().messages().list().execute.return_value = {
            "messages": [{"id": "msg1"}, {"id": "msg2"}, {"id": "msg3"}]
        }

        result = search_emails("test query", max_results=10)
        assert result == ["msg1", "msg2", "msg3"]

    @patch("mymcp.googleapis.gmail.readonly.get_googleapis_service")
    def test_search_emails_no_results(self, mock_get_service):
        """検索結果0件"""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mock_service.users().messages().list().execute.return_value = {}

        result = search_emails("nonexistent")
        assert result == []

    @patch("mymcp.googleapis.gmail.readonly.get_googleapis_service")
    def test_search_emails_api_error(self, mock_get_service):
        """APIエラー"""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mock_service.users().messages().list().execute.side_effect = HttpError(
            resp=MagicMock(status=500), content=b"Internal Server Error"
        )

        with pytest.raises(HttpError):
            search_emails("error query")


class TestParseEmailHeaders:
    """メールヘッダー解析のテスト"""

    def test_parse_headers_complete(self):
        """完全なヘッダー"""
        payload = {
            "headers": [
                {"name": "Subject", "value": "Test Email"},
                {"name": "From", "value": "sender@example.com"},
                {"name": "To", "value": "recipient@example.com, other@example.com"},
                {"name": "Cc", "value": "cc@example.com"},
                {"name": "Date", "value": "Mon, 14 Oct 2025 10:00:00 +0900"},
            ]
        }

        result = parse_email_headers(payload)
        assert result["subject"] == "Test Email"
        assert result["from"] == "sender@example.com"
        assert result["to"] == ["recipient@example.com", "other@example.com"]
        assert result["cc"] == ["cc@example.com"]
        assert result["date"] == "Mon, 14 Oct 2025 10:00:00 +0900"

    def test_parse_headers_missing_fields(self):
        """一部フィールド欠損"""
        payload = {"headers": [{"name": "Subject", "value": "Test"}]}

        result = parse_email_headers(payload)
        assert result["subject"] == "Test"
        assert result["from"] == ""
        assert result["to"] == []
        assert result["cc"] == []

    def test_parse_headers_empty(self):
        """ヘッダーなし"""
        payload = {}
        result = parse_email_headers(payload)
        assert result["subject"] == ""


class TestParseEmailBody:
    """メール本文解析のテスト"""

    def _encode_body(self, text: str) -> str:
        """テキストをBase64エンコード"""
        return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")

    def test_parse_body_plain_text(self):
        """プレーンテキストメール"""
        payload = {
            "mimeType": "text/plain",
            "body": {"data": self._encode_body("This is plain text")},
        }

        result = parse_email_body(payload)
        assert result["body_text"] == "This is plain text"
        assert result["body_html"] == ""
        assert "plain text" in result["body_markdown"]

    def test_parse_body_html(self):
        """HTMLメール"""
        html = "<html><body><h1>Title</h1><p>Content</p></body></html>"
        payload = {
            "mimeType": "text/html",
            "body": {"data": self._encode_body(html)},
        }

        result = parse_email_body(payload, prefer_html=True)
        assert result["body_html"] == html
        assert "Title" in result["body_markdown"]

    @patch("mymcp.googleapis.gmail.readonly.convert_html_to_markdown")
    def test_parse_body_multipart_html_priority(self, mock_convert):
        """マルチパート（HTML優先）"""
        mock_convert.return_value = "# Converted"

        payload = {
            "parts": [
                {
                    "mimeType": "text/plain",
                    "body": {"data": self._encode_body("Plain text")},
                },
                {
                    "mimeType": "text/html",
                    "body": {"data": self._encode_body("<p>HTML content</p>")},
                },
            ]
        }

        result = parse_email_body(payload, prefer_html=True)
        assert result["body_html"] == "<p>HTML content</p>"
        assert result["body_markdown"] == "# Converted"

    def test_parse_body_nested_parts(self):
        """ネストされたパート"""
        payload = {
            "parts": [
                {
                    "mimeType": "multipart/alternative",
                    "parts": [
                        {
                            "mimeType": "text/plain",
                            "body": {"data": self._encode_body("Nested plain")},
                        }
                    ],
                }
            ]
        }

        result = parse_email_body(payload)
        assert "Nested plain" in result["body_text"]


class TestExtractAttachments:
    """添付ファイル抽出のテスト"""

    def test_extract_attachments_single(self):
        """単一添付ファイル"""
        payload = {
            "parts": [
                {
                    "filename": "document.pdf",
                    "mimeType": "application/pdf",
                    "body": {"size": 102400, "attachmentId": "att123"},
                }
            ]
        }

        result = extract_attachments(payload)
        assert len(result) == 1
        assert result[0]["filename"] == "document.pdf"
        assert result[0]["mimeType"] == "application/pdf"
        assert result[0]["size"] == 102400
        assert result[0]["attachmentId"] == "att123"

    def test_extract_attachments_multiple(self):
        """複数添付ファイル"""
        payload = {
            "parts": [
                {"filename": "file1.pdf", "mimeType": "application/pdf", "body": {}},
                {"filename": "file2.jpg", "mimeType": "image/jpeg", "body": {}},
            ]
        }

        result = extract_attachments(payload)
        assert len(result) == 2
        assert result[0]["filename"] == "file1.pdf"
        assert result[1]["filename"] == "file2.jpg"

    def test_extract_attachments_nested(self):
        """ネストされた添付ファイル"""
        payload = {
            "parts": [
                {
                    "mimeType": "multipart/mixed",
                    "parts": [
                        {
                            "filename": "nested.txt",
                            "mimeType": "text/plain",
                            "body": {},
                        }
                    ],
                }
            ]
        }

        result = extract_attachments(payload)
        assert len(result) == 1
        assert result[0]["filename"] == "nested.txt"

    def test_extract_attachments_none(self):
        """添付ファイルなし"""
        payload = {"parts": [{"mimeType": "text/plain", "body": {}}]}
        result = extract_attachments(payload)
        assert result == []


class TestGetEmailDetails:
    """メール詳細取得のテスト"""

    @patch("mymcp.googleapis.gmail.readonly.get_googleapis_service")
    def test_get_email_details_complete(self, mock_get_service):
        """完全な詳細情報取得"""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mock_message = {
            "id": "msg123",
            "threadId": "thread456",
            "snippet": "Test snippet",
            "labelIds": ["INBOX", "UNREAD"],
            "payload": {
                "headers": [
                    {"name": "Subject", "value": "Test"},
                    {"name": "From", "value": "sender@example.com"},
                    {"name": "To", "value": "recipient@example.com"},
                    {"name": "Date", "value": "Mon, 14 Oct 2025 10:00:00 +0900"},
                ],
                "mimeType": "text/plain",
                "body": {
                    "data": base64.urlsafe_b64encode(b"Email body").decode("ascii")
                },
            },
        }

        mock_service.users().messages().get().execute.return_value = mock_message

        result = get_email_details("msg123")
        assert result["id"] == "msg123"
        assert result["thread_id"] == "thread456"
        assert result["subject"] == "Test"
        assert result["from"] == "sender@example.com"
        assert result["is_unread"] is True
        assert "Email body" in result["body_text"]

    @patch("mymcp.googleapis.gmail.readonly.get_googleapis_service")
    def test_get_email_details_api_error(self, mock_get_service):
        """API呼び出しエラー"""
        mock_service = MagicMock()
        mock_get_service.return_value = mock_service

        mock_service.users().messages().get().execute.side_effect = HttpError(
            resp=MagicMock(status=404), content=b"Not Found"
        )

        with pytest.raises(HttpError):
            get_email_details("nonexistent")


class TestGetEmailsByKeyword:
    """get_emails_by_keyword のテスト"""

    @patch("mymcp.googleapis.gmail.readonly.search_emails")
    @patch("mymcp.googleapis.gmail.readonly.get_email_details")
    def test_get_emails_basic(self, mock_get_details, mock_search):
        """基本的なメール取得"""
        mock_search.return_value = ["msg1", "msg2"]
        mock_get_details.side_effect = [
            {"id": "msg1", "subject": "Email 1", "body_markdown": "Content 1"},
            {"id": "msg2", "subject": "Email 2", "body_markdown": "Content 2"},
        ]

        result = get_emails_by_keyword("test")
        assert result["total_count"] == 2
        assert result["returned_count"] == 2
        assert len(result["emails"]) == 2
        assert result["emails"][0]["subject"] == "Email 1"

    @patch("mymcp.googleapis.gmail.readonly.search_emails")
    def test_get_emails_no_results(self, mock_search):
        """検索結果0件"""
        mock_search.return_value = []

        result = get_emails_by_keyword("nonexistent")
        assert result["total_count"] == 0
        assert result["returned_count"] == 0
        assert result["emails"] == []

    @patch("mymcp.googleapis.gmail.readonly.search_emails")
    @patch("mymcp.googleapis.gmail.readonly.get_email_details")
    @patch("mymcp.googleapis.gmail.readonly.extract_knowledge_from_text")
    def test_get_emails_with_summary(self, mock_extract, mock_get_details, mock_search):
        """サマリー生成付き"""
        mock_search.return_value = ["msg1"]
        mock_get_details.return_value = {
            "id": "msg1",
            "subject": "Test",
            "body_markdown": "Content",
        }
        mock_extract.return_value = "AI-generated summary"

        result = get_emails_by_keyword("test", include_summary=True)
        assert result["summary"] == "AI-generated summary"
        mock_extract.assert_called_once()

    @patch("mymcp.googleapis.gmail.readonly.search_emails")
    def test_get_emails_api_error(self, mock_search):
        """APIエラー処理"""
        mock_search.side_effect = HttpError(
            resp=MagicMock(status=500), content=b"Internal Server Error"
        )

        result = get_emails_by_keyword("error")
        assert "error" in result
        assert result["total_count"] == 0

    @patch("mymcp.googleapis.gmail.readonly._build_search_query")
    def test_get_emails_invalid_date(self, mock_build_query):
        """不正な日付形式"""
        mock_build_query.side_effect = ValueError("Invalid date format")

        result = get_emails_by_keyword("test", date_after="invalid")
        assert "error" in result
        assert "Invalid date format" in result["error"]

    @patch("mymcp.googleapis.gmail.readonly.search_emails")
    @patch("mymcp.googleapis.gmail.readonly.get_email_details")
    def test_get_emails_partial_failure(self, mock_get_details, mock_search):
        """一部メールの取得失敗"""
        mock_search.return_value = ["msg1", "msg2", "msg3"]
        mock_get_details.side_effect = [
            {"id": "msg1", "subject": "Email 1"},
            HttpError(resp=MagicMock(status=404), content=b"Not Found"),
            {"id": "msg3", "subject": "Email 3"},
        ]

        result = get_emails_by_keyword("test")
        assert result["total_count"] == 3
        assert result["returned_count"] == 2  # msg2は失敗
        assert len(result["emails"]) == 2

    @patch("mymcp.googleapis.gmail.readonly.search_emails")
    @patch("mymcp.googleapis.gmail.readonly.get_email_details")
    def test_get_emails_filters_combined(self, mock_get_details, mock_search):
        """複合フィルタ"""
        mock_search.return_value = ["msg1"]
        mock_get_details.return_value = {"id": "msg1", "subject": "Test"}

        result = get_emails_by_keyword(
            "report",
            top=10,
            search_in="subject",
            unread_only=True,
            has_attachment=True,
            date_after="7d",
            labels=["work"],
        )

        assert result["returned_count"] == 1
        # _build_search_query が正しく呼ばれたことを確認
        mock_search.assert_called_once()
