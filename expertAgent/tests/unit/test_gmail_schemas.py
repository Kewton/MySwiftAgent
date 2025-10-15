"""Gmail Utility API スキーマの単体テスト

AIフレンドリーなレスポンス形式の検証を行います。
"""

import pytest

from app.schemas.gmailSchemas import (
    GmailEmailDetail,
    GmailSearchRequest,
    GmailSearchResponse,
    GmailSendRequest,
    GmailSendResponse,
)


class TestGmailSearchRequest:
    """GmailSearchRequestスキーマのテスト"""

    def test_minimal_request(self):
        """最小限のリクエスト（keywordのみ）"""
        request = GmailSearchRequest(keyword="test")

        assert request.keyword == "test"
        assert request.top == 5  # デフォルト値
        assert request.search_in == "all"  # デフォルト値
        assert request.unread_only is False
        assert request.has_attachment is None
        assert request.date_after is None
        assert request.date_before is None
        assert request.labels is None
        assert request.include_summary is False
        assert request.project is None

    def test_full_request(self):
        """全パラメータ指定のリクエスト"""
        request = GmailSearchRequest(
            keyword="週刊Life is beautiful",
            top=10,
            search_in="subject",
            unread_only=True,
            has_attachment=True,
            date_after="7d",
            date_before="2025/10/31",
            labels=["important", "work"],
            include_summary=True,
            project="default",
        )

        assert request.keyword == "週刊Life is beautiful"
        assert request.top == 10
        assert request.search_in == "subject"
        assert request.unread_only is True
        assert request.has_attachment is True
        assert request.date_after == "7d"
        assert request.date_before == "2025/10/31"
        assert request.labels == ["important", "work"]
        assert request.include_summary is True
        assert request.project == "default"

    def test_invalid_search_in(self):
        """無効なsearch_in値でバリデーションエラー"""
        with pytest.raises(ValueError):
            GmailSearchRequest(keyword="test", search_in="invalid")

    def test_invalid_top_value(self):
        """無効なtop値（範囲外）でバリデーションエラー"""
        with pytest.raises(ValueError):
            GmailSearchRequest(keyword="test", top=0)  # 1未満

        with pytest.raises(ValueError):
            GmailSearchRequest(keyword="test", top=101)  # 100超過


class TestGmailEmailDetail:
    """GmailEmailDetailスキーマのテスト"""

    def test_minimal_email_detail(self):
        """最小限のメール詳細"""
        email = GmailEmailDetail(
            id="abc123",
            subject="Test Subject",
            from_address="test@example.com",
            date="Mon, 14 Oct 2025 07:10:00 +0900",
            body_text="Test body",
            snippet="Test snippet",
            is_unread=False,
            has_attachments=False,
        )

        assert email.id == "abc123"
        assert email.subject == "Test Subject"
        assert email.from_address == "test@example.com"
        assert email.date == "Mon, 14 Oct 2025 07:10:00 +0900"
        assert email.body_text == "Test body"
        assert email.snippet == "Test snippet"
        assert email.is_unread is False
        assert email.has_attachments is False
        assert email.labels == []  # デフォルト値
        assert email.to_addresses == []  # デフォルト値
        assert email.cc_addresses == []  # デフォルト値
        assert email.thread_id == ""  # デフォルト値

    def test_full_email_detail(self):
        """全フィールド指定のメール詳細"""
        email = GmailEmailDetail(
            id="abc123",
            subject="Test Subject",
            from_address="sender@example.com",
            date="Mon, 14 Oct 2025 07:10:00 +0900",
            body_text="Test body text",
            snippet="Test snippet",
            is_unread=True,
            has_attachments=True,
            labels=["INBOX", "IMPORTANT"],
            to_addresses=["user1@example.com", "user2@example.com"],
            cc_addresses=["cc@example.com"],
            thread_id="thread123",
            body_html="<html>Test</html>",
            body_markdown="# Test",
            attachments=[
                {
                    "filename": "test.pdf",
                    "mimeType": "application/pdf",
                    "size": 1024,
                    "attachmentId": "attach123",
                }
            ],
        )

        assert email.id == "abc123"
        assert email.is_unread is True
        assert email.has_attachments is True
        assert email.labels == ["INBOX", "IMPORTANT"]
        assert len(email.to_addresses) == 2
        assert len(email.cc_addresses) == 1
        assert email.thread_id == "thread123"
        assert email.body_html == "<html>Test</html>"
        assert email.body_markdown == "# Test"
        assert len(email.attachments) == 1
        assert email.attachments[0]["filename"] == "test.pdf"

    def test_from_alias(self):
        """'from'エイリアスが正しく動作"""
        # JSON形式でfromを指定
        email_dict = {
            "id": "abc123",
            "subject": "Test",
            "from": "test@example.com",  # aliasを使用
            "date": "Mon, 14 Oct 2025 07:10:00 +0900",
            "body_text": "Test",
            "snippet": "Test",
            "is_unread": False,
            "has_attachments": False,
        }

        email = GmailEmailDetail(**email_dict)
        assert email.from_address == "test@example.com"


class TestGmailSearchResponse:
    """GmailSearchResponseスキーマのテスト"""

    def test_empty_response(self):
        """空の検索結果"""
        response = GmailSearchResponse(
            total_count=0,
            returned_count=0,
            query_info={"keyword": "test"},
            emails=[],
            ai_prompt_snippet="検索結果: 0件（該当メールなし）",
        )

        assert response.total_count == 0
        assert response.returned_count == 0
        assert response.query_info["keyword"] == "test"
        assert len(response.emails) == 0
        assert response.summary is None
        assert "0件" in response.ai_prompt_snippet

    def test_response_with_emails(self):
        """メールありの検索結果"""
        emails = [
            GmailEmailDetail(
                id="abc123",
                subject="Test 1",
                from_address="test1@example.com",
                date="Mon, 14 Oct 2025 07:10:00 +0900",
                body_text="Body 1",
                snippet="Snippet 1",
                is_unread=False,
                has_attachments=False,
            ),
            GmailEmailDetail(
                id="def456",
                subject="Test 2",
                from_address="test2@example.com",
                date="Tue, 15 Oct 2025 08:00:00 +0900",
                body_text="Body 2",
                snippet="Snippet 2",
                is_unread=True,
                has_attachments=True,
                attachments=[{"filename": "test.pdf"}],
            ),
        ]

        response = GmailSearchResponse(
            total_count=10,
            returned_count=2,
            query_info={"keyword": "test", "search_in": "subject"},
            emails=emails,
            ai_prompt_snippet="Test snippet",
        )

        assert response.total_count == 10
        assert response.returned_count == 2
        assert len(response.emails) == 2
        assert response.emails[0].id == "abc123"
        assert response.emails[1].id == "def456"
        assert response.emails[1].is_unread is True

    def test_from_search_result_minimal(self):
        """from_search_result: 最小限のデータ"""
        search_result = {
            "total_count": 0,
            "returned_count": 0,
            "emails": [],
        }

        request = GmailSearchRequest(keyword="test")
        response = GmailSearchResponse.from_search_result(search_result, request)

        assert response.total_count == 0
        assert response.returned_count == 0
        assert len(response.emails) == 0
        assert "0件" in response.ai_prompt_snippet

    def test_from_search_result_with_emails(self):
        """from_search_result: メールデータあり"""
        search_result = {
            "total_count": 2,
            "returned_count": 2,
            "emails": [
                {
                    "id": "abc123",
                    "subject": "Test Subject",
                    "from": "test@example.com",
                    "date": "Mon, 14 Oct 2025 07:10:00 +0900",
                    "body_text": "Test body",
                    "snippet": "Test snippet",
                    "is_unread": False,
                    "has_attachments": False,
                    "labels": ["INBOX"],
                    "to": ["user@example.com"],
                    "cc": [],
                    "thread_id": "thread123",
                }
            ],
        }

        request = GmailSearchRequest(keyword="test", search_in="subject", top=5)
        response = GmailSearchResponse.from_search_result(search_result, request)

        assert response.total_count == 2
        assert response.returned_count == 2
        assert len(response.emails) == 1
        assert response.emails[0].id == "abc123"
        assert response.emails[0].from_address == "test@example.com"

        # query_info検証
        assert response.query_info["keyword"] == "test"
        assert response.query_info["search_in"] == "subject"
        assert response.query_info["top"] == 5

        # ai_prompt_snippet検証
        assert "2件中2件を表示" in response.ai_prompt_snippet
        assert "Test Subject" in response.ai_prompt_snippet
        assert "test@example.com" in response.ai_prompt_snippet

    def test_from_search_result_with_summary(self):
        """from_search_result: AIサマリーあり"""
        search_result = {
            "total_count": 5,
            "returned_count": 5,
            "emails": [],
            "summary": "AI generated summary",
        }

        request = GmailSearchRequest(keyword="test", include_summary=True)
        response = GmailSearchResponse.from_search_result(search_result, request)

        assert response.summary == "AI generated summary"

    def test_generate_ai_prompt_snippet_with_attachments(self):
        """ai_prompt_snippet: 添付ファイルありのメール"""
        emails = [
            GmailEmailDetail(
                id="abc123",
                subject="Test",
                from_address="test@example.com",
                date="Mon, 14 Oct 2025 07:10:00 +0900",
                body_text="Body",
                snippet="Snippet",
                is_unread=False,
                has_attachments=True,
                attachments=[{"filename": "test.pdf"}, {"filename": "test2.pdf"}],
            )
        ]

        snippet = GmailSearchResponse._generate_ai_prompt_snippet(emails, 1, 1)

        assert "添付: 2件" in snippet

    def test_generate_ai_prompt_snippet_with_unread(self):
        """ai_prompt_snippet: 未読メール"""
        emails = [
            GmailEmailDetail(
                id="abc123",
                subject="Test",
                from_address="test@example.com",
                date="Mon, 14 Oct 2025 07:10:00 +0900",
                body_text="Body",
                snippet="Snippet",
                is_unread=True,
                has_attachments=False,
            )
        ]

        snippet = GmailSearchResponse._generate_ai_prompt_snippet(emails, 1, 1)

        assert "状態: 未読" in snippet

    def test_generate_query_info_with_filters(self):
        """query_info: フィルタ条件あり"""
        request = GmailSearchRequest(
            keyword="test",
            search_in="subject",
            top=10,
            date_after="7d",
            unread_only=True,
            has_attachment=True,
            labels=["important"],
        )

        result = {"total_count": 0, "returned_count": 0, "emails": []}
        response = GmailSearchResponse.from_search_result(result, request)

        assert response.query_info["keyword"] == "test"
        assert response.query_info["search_in"] == "subject"
        assert response.query_info["top"] == 10
        assert response.query_info["date_after"] == "7d"
        assert response.query_info["unread_only"] is True
        assert response.query_info["has_attachment"] is True
        assert response.query_info["labels"] == ["important"]


class TestGmailSendRequest:
    """GmailSendRequestスキーマのテスト"""

    def test_minimal_request_single_recipient(self):
        """最小限のリクエスト（単一宛先）"""
        request = GmailSendRequest(
            to="test@example.com", subject="Test Subject", body="Test body"
        )

        assert request.to == "test@example.com"
        assert request.subject == "Test Subject"
        assert request.body == "Test body"
        assert request.cc is None
        assert request.bcc is None
        assert request.html_body is None
        assert request.project is None
        assert request.test_mode is False
        assert request.test_response is None

    def test_minimal_request_multiple_recipients(self):
        """最小限のリクエスト（複数宛先）"""
        request = GmailSendRequest(
            to=["user1@example.com", "user2@example.com"],
            subject="Test Subject",
            body="Test body",
        )

        assert isinstance(request.to, list)
        assert len(request.to) == 2
        assert request.to[0] == "user1@example.com"
        assert request.to[1] == "user2@example.com"

    def test_full_request(self):
        """全パラメータ指定のリクエスト"""
        request = GmailSendRequest(
            to=["primary@example.com"],
            subject="Important Notice",
            body="This is the body",
            cc=["cc@example.com"],
            bcc=["bcc@example.com"],
            html_body="<html>HTML body</html>",
            project="default_project",
            test_mode=True,
            test_response={"message_id": "test123"},
        )

        assert request.to == ["primary@example.com"]
        assert request.subject == "Important Notice"
        assert request.body == "This is the body"
        assert request.cc == ["cc@example.com"]
        assert request.bcc == ["bcc@example.com"]
        assert request.html_body == "<html>HTML body</html>"
        assert request.project == "default_project"
        assert request.test_mode is True
        assert request.test_response == {"message_id": "test123"}

    def test_empty_subject_validation(self):
        """件名が空文字でバリデーションエラー"""
        with pytest.raises(ValueError):
            GmailSendRequest(to="test@example.com", subject="", body="Test")

    def test_empty_body_validation(self):
        """本文が空文字でバリデーションエラー"""
        with pytest.raises(ValueError):
            GmailSendRequest(to="test@example.com", subject="Test", body="")


class TestGmailSendResponse:
    """GmailSendResponseスキーマのテスト"""

    def test_minimal_response(self):
        """最小限のレスポンス"""
        response = GmailSendResponse(
            success=True,
            message_id="msg123",
            thread_id="thread123",
            label_ids=["SENT"],
            sent_to=["test@example.com"],
            subject="Test Subject",
            sent_at="2025-10-15T00:00:00Z",
            ai_summary="test@example.com 宛にメール送信完了（件名: Test Subject）",
        )

        assert response.success is True
        assert response.message_id == "msg123"
        assert response.thread_id == "thread123"
        assert response.label_ids == ["SENT"]
        assert len(response.sent_to) == 1
        assert response.sent_to[0] == "test@example.com"
        assert response.subject == "Test Subject"
        assert "2025-10-15" in response.sent_at
        assert "test@example.com" in response.ai_summary

    def test_from_gmail_result_single_recipient(self):
        """from_gmail_result: 単一宛先"""
        gmail_result = {
            "id": "msg456",
            "threadId": "thread456",
            "labelIds": ["SENT"],
        }

        request = GmailSendRequest(
            to="recipient@example.com", subject="Test", body="Body"
        )

        response = GmailSendResponse.from_gmail_result(gmail_result, request)

        assert response.success is True
        assert response.message_id == "msg456"
        assert response.thread_id == "thread456"
        assert response.label_ids == ["SENT"]
        assert response.sent_to == ["recipient@example.com"]
        assert response.subject == "Test"
        assert "recipient@example.com" in response.ai_summary
        assert "Test" in response.ai_summary

    def test_from_gmail_result_multiple_recipients(self):
        """from_gmail_result: 複数宛先"""
        gmail_result = {
            "id": "msg789",
            "threadId": "thread789",
            "labelIds": ["SENT"],
        }

        request = GmailSendRequest(
            to=["user1@example.com", "user2@example.com"],
            subject="Multi-recipient Test",
            body="Test body",
        )

        response = GmailSendResponse.from_gmail_result(gmail_result, request)

        assert response.success is True
        assert len(response.sent_to) == 2
        assert "user1@example.com" in response.sent_to
        assert "user2@example.com" in response.sent_to
        assert "user1@example.com, user2@example.com" in response.ai_summary

    def test_generate_ai_summary(self):
        """ai_summary生成のテスト"""
        sent_to = ["recipient@example.com"]
        subject = "Important Notice"

        summary = GmailSendResponse._generate_ai_summary(sent_to, subject)

        assert "recipient@example.com" in summary
        assert "Important Notice" in summary
        assert "メール送信完了" in summary

    def test_generate_ai_summary_multiple_recipients(self):
        """ai_summary生成のテスト（複数宛先）"""
        sent_to = ["user1@example.com", "user2@example.com", "user3@example.com"]
        subject = "Team Update"

        summary = GmailSendResponse._generate_ai_summary(sent_to, subject)

        assert "user1@example.com, user2@example.com, user3@example.com" in summary
        assert "Team Update" in summary
