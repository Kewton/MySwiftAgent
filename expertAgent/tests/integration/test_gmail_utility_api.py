"""Gmail Utility API の統合テスト

実際のエンドポイント呼び出しをテストします。
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestGmailUtilityAPI:
    """Gmail Utility APIエンドポイントのテスト"""

    def test_gmail_search_minimal(self, mock_gmail_service):
        """最小限のリクエスト（keywordのみ）"""
        response = client.post("/v1/utility/gmail/search", json={"keyword": "test"})

        assert response.status_code == 200
        data = response.json()

        # レスポンス構造の検証
        assert "total_count" in data
        assert "returned_count" in data
        assert "emails" in data
        assert "ai_prompt_snippet" in data
        assert "query_info" in data

        # デフォルト値の検証
        assert data["query_info"]["keyword"] == "test"
        assert data["query_info"]["search_in"] == "all"
        assert data["query_info"]["top"] == 5

    def test_gmail_search_with_filters(self, mock_gmail_service):
        """フィルタ条件付きリクエスト"""
        response = client.post(
            "/v1/utility/gmail/search",
            json={
                "keyword": "週刊Life is beautiful",
                "search_in": "subject",
                "top": 10,
                "date_after": "7d",
                "unread_only": False,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # フィルタ条件の検証
        assert data["query_info"]["keyword"] == "週刊Life is beautiful"
        assert data["query_info"]["search_in"] == "subject"
        assert data["query_info"]["top"] == 10
        assert data["query_info"]["date_after"] == "7d"

    def test_gmail_search_ai_prompt_snippet(self, mock_gmail_service):
        """ai_prompt_snippetフィールドの検証"""
        response = client.post(
            "/v1/utility/gmail/search", json={"keyword": "test", "top": 5}
        )

        assert response.status_code == 200
        data = response.json()

        # ai_prompt_snippetが存在し、文字列であること
        assert "ai_prompt_snippet" in data
        assert isinstance(data["ai_prompt_snippet"], str)

        # 最低限の情報が含まれていること
        snippet = data["ai_prompt_snippet"]
        assert "検索結果" in snippet
        assert "件" in snippet

    def test_gmail_search_email_structure(self, mock_gmail_service_with_data):
        """メール詳細の構造検証"""
        response = client.post("/v1/utility/gmail/search", json={"keyword": "test"})

        assert response.status_code == 200
        data = response.json()

        # メールが1件以上あることを想定
        assert len(data["emails"]) > 0

        # 最初のメールの構造検証
        email = data["emails"][0]
        required_fields = [
            "id",
            "subject",
            "from",
            "date",
            "body_text",
            "snippet",
            "is_unread",
            "has_attachments",
            "labels",
        ]

        for field in required_fields:
            assert field in email, f"Required field '{field}' is missing"

        # データ型の検証
        assert isinstance(email["id"], str)
        assert isinstance(email["subject"], str)
        assert isinstance(email["from"], str)
        assert isinstance(email["is_unread"], bool)
        assert isinstance(email["has_attachments"], bool)
        assert isinstance(email["labels"], list)

    def test_gmail_search_invalid_search_in(self):
        """無効なsearch_in値でエラー"""
        response = client.post(
            "/v1/utility/gmail/search",
            json={"keyword": "test", "search_in": "invalid"},
        )

        assert response.status_code == 422  # Validation error

    def test_gmail_search_invalid_top_value(self):
        """無効なtop値（範囲外）でエラー"""
        # top=0（1未満）
        response = client.post(
            "/v1/utility/gmail/search", json={"keyword": "test", "top": 0}
        )
        assert response.status_code == 422

        # top=101（100超過）
        response = client.post(
            "/v1/utility/gmail/search", json={"keyword": "test", "top": 101}
        )
        assert response.status_code == 422

    def test_gmail_search_missing_keyword(self):
        """keyword未指定でエラー"""
        response = client.post("/v1/utility/gmail/search", json={"top": 10})

        assert response.status_code == 422  # Validation error

    def test_gmail_search_empty_result(self, mock_gmail_service_empty):
        """検索結果0件の場合"""
        response = client.post(
            "/v1/utility/gmail/search", json={"keyword": "nonexistent"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_count"] == 0
        assert data["returned_count"] == 0
        assert len(data["emails"]) == 0
        assert "0件" in data["ai_prompt_snippet"]

    def test_gmail_search_with_attachments(self, mock_gmail_service_with_attachments):
        """添付ファイル付きメールの検証"""
        response = client.post(
            "/v1/utility/gmail/search",
            json={"keyword": "test", "has_attachment": True},
        )

        assert response.status_code == 200
        data = response.json()

        # 添付ファイルありのメールが取得されること
        assert len(data["emails"]) > 0
        email = data["emails"][0]
        assert email["has_attachments"] is True
        assert len(email.get("attachments", [])) > 0

        # ai_prompt_snippetに添付情報が含まれること
        assert "添付" in data["ai_prompt_snippet"]

    def test_gmail_search_unread_only(self, mock_gmail_service_with_unread):
        """未読メールのみの検証"""
        response = client.post(
            "/v1/utility/gmail/search",
            json={"keyword": "test", "unread_only": True},
        )

        assert response.status_code == 200
        data = response.json()

        # 未読メールのみ取得されること
        for email in data["emails"]:
            assert email["is_unread"] is True

        # ai_prompt_snippetに未読情報が含まれること
        if len(data["emails"]) > 0:
            assert "未読" in data["ai_prompt_snippet"]

    def test_gmail_search_performance(self, mock_gmail_service):
        """レスポンス時間の検証（5秒以内）"""
        import time

        start_time = time.time()

        response = client.post("/v1/utility/gmail/search", json={"keyword": "test"})

        elapsed_time = time.time() - start_time

        assert response.status_code == 200
        # モックなので実際は1秒未満だが、実環境では5秒以内を想定
        assert elapsed_time < 5.0

    def test_gmail_search_json_guaranteed(self, mock_gmail_service):
        """JSON形式が保証されていること"""
        response = client.post("/v1/utility/gmail/search", json={"keyword": "test"})

        assert response.status_code == 200

        # レスポンスがJSON形式であること
        assert response.headers["content-type"] == "application/json"

        # JSONパース可能であること
        data = response.json()
        assert isinstance(data, dict)

    def test_gmail_search_query_info_all_filters(self, mock_gmail_service):
        """query_infoに全フィルタ条件が含まれること"""
        response = client.post(
            "/v1/utility/gmail/search",
            json={
                "keyword": "test",
                "search_in": "subject",
                "top": 20,
                "date_after": "2025/10/01",
                "date_before": "2025/10/31",
                "unread_only": True,
                "has_attachment": True,
                "labels": ["important", "work"],
            },
        )

        assert response.status_code == 200
        data = response.json()

        query_info = data["query_info"]
        assert query_info["keyword"] == "test"
        assert query_info["search_in"] == "subject"
        assert query_info["top"] == 20
        assert query_info["date_after"] == "2025/10/01"
        assert query_info["date_before"] == "2025/10/31"
        assert query_info["unread_only"] is True
        assert query_info["has_attachment"] is True
        assert query_info["labels"] == ["important", "work"]


class TestGmailSendAPI:
    """Gmail Send APIエンドポイントのテスト"""

    def test_gmail_send_minimal_single_recipient(self, mock_gmail_send_service):
        """最小限のリクエスト（単一宛先）"""
        response = client.post(
            "/v1/utility/gmail/send",
            json={
                "to": "test@example.com",
                "subject": "Test Subject",
                "body": "Test body",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # レスポンス構造の検証
        assert "success" in data
        assert "message_id" in data
        assert "thread_id" in data
        assert "label_ids" in data
        assert "sent_to" in data
        assert "subject" in data
        assert "sent_at" in data
        assert "ai_summary" in data

        # データの検証
        assert data["success"] is True
        assert data["sent_to"] == ["test@example.com"]
        assert data["subject"] == "Test Subject"
        assert "test@example.com" in data["ai_summary"]

    def test_gmail_send_multiple_recipients(self, mock_gmail_send_service):
        """複数宛先のリクエスト"""
        response = client.post(
            "/v1/utility/gmail/send",
            json={
                "to": ["user1@example.com", "user2@example.com"],
                "subject": "Multi-recipient Test",
                "body": "Test body for multiple recipients",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert len(data["sent_to"]) == 2
        assert "user1@example.com" in data["sent_to"]
        assert "user2@example.com" in data["sent_to"]
        assert "user1@example.com, user2@example.com" in data["ai_summary"]

    def test_gmail_send_missing_required_fields(self):
        """必須フィールド未指定でエラー"""
        # toなし
        response = client.post(
            "/v1/utility/gmail/send",
            json={"subject": "Test", "body": "Test body"},
        )
        assert response.status_code == 422

        # subjectなし
        response = client.post(
            "/v1/utility/gmail/send",
            json={"to": "test@example.com", "body": "Test body"},
        )
        assert response.status_code == 422

        # bodyなし
        response = client.post(
            "/v1/utility/gmail/send",
            json={"to": "test@example.com", "subject": "Test"},
        )
        assert response.status_code == 422

    def test_gmail_send_empty_subject(self):
        """件名が空文字でバリデーションエラー"""
        response = client.post(
            "/v1/utility/gmail/send",
            json={"to": "test@example.com", "subject": "", "body": "Test body"},
        )

        assert response.status_code == 422

    def test_gmail_send_empty_body(self):
        """本文が空文字でバリデーションエラー"""
        response = client.post(
            "/v1/utility/gmail/send",
            json={"to": "test@example.com", "subject": "Test", "body": ""},
        )

        assert response.status_code == 422

    def test_gmail_send_test_mode(self):
        """テストモードの動作確認"""
        response = client.post(
            "/v1/utility/gmail/send",
            json={
                "to": "test@example.com",
                "subject": "Test Subject",
                "body": "Test body",
                "test_mode": True,
                "test_response": {
                    "success": True,
                    "message_id": "test_msg_123",
                    "thread_id": "test_thread_123",
                    "label_ids": ["SENT"],
                    "sent_to": ["test@example.com"],
                    "subject": "Test Subject",
                    "sent_at": "2025-10-15T00:00:00Z",
                    "ai_summary": "Test summary",
                },
            },
        )

        assert response.status_code == 200
        data = response.json()

        # テストレスポンスが返されること
        assert data["success"] is True
        assert data["message_id"] == "test_msg_123"
        assert data["thread_id"] == "test_thread_123"

    def test_gmail_send_ai_summary_content(self, mock_gmail_send_service):
        """ai_summaryの内容検証"""
        response = client.post(
            "/v1/utility/gmail/send",
            json={
                "to": "recipient@example.com",
                "subject": "Important Notice",
                "body": "This is important",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # ai_summaryに必要な情報が含まれていること
        assert "recipient@example.com" in data["ai_summary"]
        assert "Important Notice" in data["ai_summary"]
        assert "メール送信完了" in data["ai_summary"]

    def test_gmail_send_json_guaranteed(self, mock_gmail_send_service):
        """JSON形式が保証されていること"""
        response = client.post(
            "/v1/utility/gmail/send",
            json={
                "to": "test@example.com",
                "subject": "Test",
                "body": "Test body",
            },
        )

        assert response.status_code == 200

        # レスポンスがJSON形式であること
        assert response.headers["content-type"] == "application/json"

        # JSONパース可能であること
        data = response.json()
        assert isinstance(data, dict)

    def test_gmail_send_performance(self, mock_gmail_send_service):
        """レスポンス時間の検証（3秒以内）"""
        import time

        start_time = time.time()

        response = client.post(
            "/v1/utility/gmail/send",
            json={
                "to": "test@example.com",
                "subject": "Performance Test",
                "body": "Testing response time",
            },
        )

        elapsed_time = time.time() - start_time

        assert response.status_code == 200
        # モックなので実際は1秒未満だが、実環境では3秒以内を想定
        assert elapsed_time < 3.0

    def test_gmail_send_with_project(self, mock_gmail_send_service):
        """MyVaultプロジェクト指定のテスト"""
        response = client.post(
            "/v1/utility/gmail/send",
            json={
                "to": "test@example.com",
                "subject": "Test with project",
                "body": "Test body",
                "project": "default_project",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
