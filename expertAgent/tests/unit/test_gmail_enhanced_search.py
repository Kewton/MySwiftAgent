"""
Gmail拡張検索機能の統合テスト
新しいパラメータを組み合わせた実用的なシナリオをテスト
"""

from unittest.mock import patch

from mymcp.googleapis.gmail.readonly import get_emails_by_keyword


class TestEnhancedGmailSearch:
    """拡張検索機能の実用シナリオテスト"""

    @patch("mymcp.googleapis.gmail.readonly.search_emails")
    @patch("mymcp.googleapis.gmail.readonly.get_email_details")
    def test_scenario_unread_recent_emails(self, mock_get_details, mock_search):
        """シナリオ1: 過去1週間の未読メール検索"""
        mock_search.return_value = ["msg1", "msg2"]
        mock_get_details.side_effect = [
            {
                "id": "msg1",
                "subject": "Weekly Report",
                "from": "team@example.com",
                "is_unread": True,
                "body_markdown": "This week's report...",
            },
            {
                "id": "msg2",
                "subject": "Meeting Notes",
                "from": "manager@example.com",
                "is_unread": True,
                "body_markdown": "Meeting summary...",
            },
        ]

        result = get_emails_by_keyword(
            keyword="report", date_after="7d", unread_only=True, top=10
        )

        assert result["total_count"] == 2
        assert result["returned_count"] == 2
        assert all(email["is_unread"] for email in result["emails"])
        mock_search.assert_called_once()

    @patch("mymcp.googleapis.gmail.readonly.search_emails")
    @patch("mymcp.googleapis.gmail.readonly.get_email_details")
    def test_scenario_invoices_with_attachments(self, mock_get_details, mock_search):
        """シナリオ2: 特定期間の添付ファイル付き請求書検索"""
        mock_search.return_value = ["msg1"]
        mock_get_details.return_value = {
            "id": "msg1",
            "subject": "Invoice #12345",
            "from": "billing@company.com",
            "has_attachments": True,
            "attachments": [
                {
                    "filename": "invoice_12345.pdf",
                    "mimeType": "application/pdf",
                    "size": 102400,
                }
            ],
            "body_markdown": "Please find attached invoice...",
        }

        result = get_emails_by_keyword(
            keyword="invoice",
            search_in="subject",
            date_after="2025/10/01",
            date_before="2025/10/31",
            has_attachment=True,
        )

        assert result["returned_count"] == 1
        assert result["emails"][0]["has_attachments"] is True
        assert len(result["emails"][0]["attachments"]) > 0
        assert "invoice_12345.pdf" == result["emails"][0]["attachments"][0]["filename"]

    @patch("mymcp.googleapis.gmail.readonly.search_emails")
    @patch("mymcp.googleapis.gmail.readonly.get_email_details")
    def test_scenario_important_project_emails(self, mock_get_details, mock_search):
        """シナリオ3: 重要ラベル付きプロジェクトメール検索"""
        mock_search.return_value = ["msg1", "msg2", "msg3"]
        mock_get_details.side_effect = [
            {
                "id": "msg1",
                "subject": "Project Alpha Update",
                "labels": ["IMPORTANT", "work"],
                "body_markdown": "Project status...",
            },
            {
                "id": "msg2",
                "subject": "Project Beta Milestone",
                "labels": ["IMPORTANT", "work"],
                "body_markdown": "Milestone achieved...",
            },
            {
                "id": "msg3",
                "subject": "Project Gamma Review",
                "labels": ["IMPORTANT", "work"],
                "body_markdown": "Review results...",
            },
        ]

        result = get_emails_by_keyword(
            keyword="project",
            search_in="subject",
            labels=["important", "work"],
            date_after="3m",
            top=20,
        )

        assert result["returned_count"] == 3
        for email in result["emails"]:
            assert "IMPORTANT" in email["labels"]
            assert "work" in email["labels"]

    @patch("mymcp.googleapis.gmail.readonly.search_emails")
    @patch("mymcp.googleapis.gmail.readonly.get_email_details")
    @patch("mymcp.googleapis.gmail.readonly.extract_knowledge_from_text")
    def test_scenario_ai_summary_generation(
        self, mock_extract, mock_get_details, mock_search
    ):
        """シナリオ4: AI要約付きメール検索"""
        mock_search.return_value = ["msg1", "msg2"]
        mock_get_details.side_effect = [
            {
                "id": "msg1",
                "subject": "Q3 Results",
                "from": "ceo@company.com",
                "date": "Mon, 14 Oct 2025 10:00:00 +0900",
                "body_markdown": "Q3 financial results show 20% growth...",
            },
            {
                "id": "msg2",
                "subject": "Q4 Forecast",
                "from": "cfo@company.com",
                "date": "Tue, 15 Oct 2025 11:00:00 +0900",
                "body_markdown": "Q4 forecast indicates continued growth...",
            },
        ]
        mock_extract.return_value = "要約: Q3は20%成長、Q4も継続的な成長が見込まれる。"

        result = get_emails_by_keyword(
            keyword="quarterly results",
            date_after="2025/10/01",
            top=10,
            include_summary=True,
        )

        assert "summary" in result
        assert result["summary"] == "要約: Q3は20%成長、Q4も継続的な成長が見込まれる。"
        assert result["returned_count"] == 2

        # extract_knowledge_from_textが正しい形式で呼ばれたことを確認
        mock_extract.assert_called_once()
        call_args = mock_extract.call_args[0][0]
        assert isinstance(call_args, str)
        assert "Q3 Results" in call_args
        assert "Q4 Forecast" in call_args

    @patch("mymcp.googleapis.gmail.readonly.search_emails")
    @patch("mymcp.googleapis.gmail.readonly.get_email_details")
    def test_scenario_sender_specific_search(self, mock_get_details, mock_search):
        """シナリオ5: 特定の送信者からのメール検索"""
        mock_search.return_value = ["msg1", "msg2", "msg3"]
        mock_get_details.side_effect = [
            {
                "id": "msg1",
                "subject": "Welcome",
                "from": "john@example.com",
                "body_markdown": "Welcome message...",
            },
            {
                "id": "msg2",
                "subject": "Follow up",
                "from": "john@example.com",
                "body_markdown": "Follow up message...",
            },
            {
                "id": "msg3",
                "subject": "Update",
                "from": "john@example.com",
                "body_markdown": "Update message...",
            },
        ]

        result = get_emails_by_keyword(
            keyword="john@example.com", search_in="from", top=10
        )

        assert result["returned_count"] == 3
        for email in result["emails"]:
            assert email["from"] == "john@example.com"

    @patch("mymcp.googleapis.gmail.readonly.search_emails")
    @patch("mymcp.googleapis.gmail.readonly.get_email_details")
    def test_scenario_no_attachment_emails(self, mock_get_details, mock_search):
        """シナリオ6: 添付ファイルなしのメール検索"""
        mock_search.return_value = ["msg1", "msg2"]
        mock_get_details.side_effect = [
            {
                "id": "msg1",
                "subject": "Quick Question",
                "has_attachments": False,
                "attachments": [],
                "body_markdown": "Quick question about...",
            },
            {
                "id": "msg2",
                "subject": "Simple Reply",
                "has_attachments": False,
                "attachments": [],
                "body_markdown": "Simple reply...",
            },
        ]

        result = get_emails_by_keyword(keyword="question", has_attachment=False, top=10)

        assert result["returned_count"] == 2
        for email in result["emails"]:
            assert email["has_attachments"] is False
            assert len(email["attachments"]) == 0

    @patch("mymcp.googleapis.gmail.readonly.search_emails")
    @patch("mymcp.googleapis.gmail.readonly.get_email_details")
    def test_scenario_relative_date_formats(self, mock_get_details, mock_search):
        """シナリオ7: 各種相対日付フォーマットのテスト"""
        mock_search.return_value = ["msg1"]
        mock_get_details.return_value = {
            "id": "msg1",
            "subject": "Test",
            "body_markdown": "Test content",
        }

        # 7日前から
        result_7d = get_emails_by_keyword("test", date_after="7d")
        assert result_7d["returned_count"] == 1

        # 2週間前から
        result_2w = get_emails_by_keyword("test", date_after="2w")
        assert result_2w["returned_count"] == 1

        # 3ヶ月前から
        result_3m = get_emails_by_keyword("test", date_after="3m")
        assert result_3m["returned_count"] == 1

        # 1年前から
        result_1y = get_emails_by_keyword("test", date_after="1y")
        assert result_1y["returned_count"] == 1

    @patch("mymcp.googleapis.gmail.readonly.search_emails")
    @patch("mymcp.googleapis.gmail.readonly.get_email_details")
    def test_scenario_complex_combined_filters(self, mock_get_details, mock_search):
        """シナリオ8: 複数フィルタの複雑な組み合わせ"""
        mock_search.return_value = ["msg1"]
        mock_get_details.return_value = {
            "id": "msg1",
            "subject": "Urgent: Contract Review",
            "from": "legal@company.com",
            "is_unread": True,
            "has_attachments": True,
            "attachments": [{"filename": "contract.pdf"}],
            "labels": ["IMPORTANT", "legal"],
            "body_markdown": "Contract review needed...",
        }

        result = get_emails_by_keyword(
            keyword="contract",
            search_in="subject",
            unread_only=True,
            has_attachment=True,
            date_after="7d",
            labels=["important", "legal"],
            top=5,
        )

        assert result["returned_count"] == 1
        email = result["emails"][0]
        assert email["is_unread"] is True
        assert email["has_attachments"] is True
        assert "IMPORTANT" in email["labels"]
        assert "legal" in email["labels"]
        assert email["from"] == "legal@company.com"

    @patch("mymcp.googleapis.gmail.readonly._build_search_query")
    def test_query_construction_with_all_parameters(self, mock_build_query):
        """全パラメータを使用した検索クエリ構築テスト"""
        mock_build_query.return_value = (
            "test subject:test is:unread has:attachment "
            "after:2025/10/01 before:2025/10/31 label:important label:work"
        )

        with patch("mymcp.googleapis.gmail.readonly.search_emails") as mock_search:
            mock_search.return_value = []

            get_emails_by_keyword(
                keyword="test",
                search_in="subject",
                unread_only=True,
                has_attachment=True,
                date_after="2025/10/01",
                date_before="2025/10/31",
                labels=["important", "work"],
            )

            mock_build_query.assert_called_once_with(
                keyword="test",
                search_in="subject",
                unread_only=True,
                has_attachment=True,
                date_after="2025/10/01",
                date_before="2025/10/31",
                labels=["important", "work"],
            )
