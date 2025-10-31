"""Unit tests for requirement clarification prompts.

Tests prompt generation, completeness calculation, and keyword extraction.
"""

from aiagent.langgraph.jobTaskGeneratorAgents.prompts.requirement_clarification import (
    calculate_completeness,
    create_requirement_clarification_prompt,
    extract_requirement_from_message,
)
from app.schemas.chat import RequirementState


class TestCalculateCompleteness:
    """Test suite for completeness calculation."""

    def test_empty_requirements(self):
        """Test completeness with no requirements filled."""
        state = RequirementState()
        assert calculate_completeness(state) == 0.0

    def test_data_source_only(self):
        """Test completeness with data_source only (25%)."""
        state = RequirementState(data_source="CSVファイル")
        assert calculate_completeness(state) == 0.25

    def test_process_description_only(self):
        """Test completeness with process_description only (35% - most important)."""
        state = RequirementState(process_description="データ分析")
        assert calculate_completeness(state) == 0.35

    def test_output_format_only(self):
        """Test completeness with output_format only (25%)."""
        state = RequirementState(output_format="Excelレポート")
        assert calculate_completeness(state) == 0.25

    def test_schedule_only(self):
        """Test completeness with schedule only (15%)."""
        state = RequirementState(schedule="毎日実行")
        assert calculate_completeness(state) == 0.15

    def test_data_source_and_process(self):
        """Test completeness with data_source + process_description (60%)."""
        state = RequirementState(
            data_source="CSVファイル", process_description="データ分析"
        )
        assert calculate_completeness(state) == 0.60

    def test_all_requirements_filled(self):
        """Test completeness with all requirements (100%)."""
        state = RequirementState(
            data_source="CSVファイル",
            process_description="データ分析",
            output_format="Excelレポート",
            schedule="毎日実行",
        )
        assert calculate_completeness(state) == 1.0

    def test_minimum_job_creation_threshold(self):
        """Test completeness reaches 80% threshold (minimum for job creation)."""
        # data_source + process + output = 85%
        state = RequirementState(
            data_source="CSVファイル",
            process_description="データ分析",
            output_format="Excelレポート",
        )
        completeness = calculate_completeness(state)
        assert completeness == 0.85
        assert completeness >= 0.8  # Ready for job creation


class TestExtractRequirementFromMessage:
    """Test suite for keyword-based requirement extraction."""

    def test_extract_csv_data_source(self):
        """Test extraction of CSV data source."""
        current = RequirementState()
        updated = extract_requirement_from_message(
            "CSVファイルを使います", "かしこまりました", current
        )
        assert updated.data_source == "CSVファイル"
        assert updated.completeness == 0.25

    def test_extract_excel_data_source(self):
        """Test extraction of Excel data source."""
        current = RequirementState()
        updated = extract_requirement_from_message(
            "Excelファイルがあります", "承知しました", current
        )
        assert updated.data_source == "Excelファイル"

    def test_extract_database_data_source(self):
        """Test extraction of database data source."""
        current = RequirementState()
        updated = extract_requirement_from_message(
            "データベースから取得", "わかりました", current
        )
        assert updated.data_source == "データベース"

    def test_extract_google_sheets_data_source(self):
        """Test extraction of Google Sheets data source."""
        current = RequirementState()
        updated = extract_requirement_from_message(
            "Google Sheetsを使います", "承知しました", current
        )
        assert updated.data_source == "Google Sheets"

    def test_extract_api_data_source(self):
        """Test extraction of API data source."""
        current = RequirementState()
        updated = extract_requirement_from_message(
            "APIから取得します", "わかりました", current
        )
        assert updated.data_source == "API"

    def test_extract_process_description(self):
        """Test extraction of process description with action keywords."""
        current = RequirementState()
        updated = extract_requirement_from_message(
            "売上データを分析したい", "かしこまりました", current
        )
        assert updated.process_description is not None
        assert "分析" in updated.process_description
        assert updated.completeness == 0.35  # Process is most important

    def test_extract_excel_output_format(self):
        """Test extraction of Excel report output format."""
        current = RequirementState()
        updated = extract_requirement_from_message(
            "Excelレポートで出力してください", "承知しました", current
        )
        assert updated.output_format == "Excelレポート"

    def test_extract_pdf_output_format(self):
        """Test extraction of PDF output format."""
        current = RequirementState()
        updated = extract_requirement_from_message(
            "PDFで出力します", "わかりました", current
        )
        assert updated.output_format == "PDFドキュメント"

    def test_extract_email_output_format(self):
        """Test extraction of email output format."""
        current = RequirementState()
        updated = extract_requirement_from_message(
            "メールで送信してください", "承知しました", current
        )
        assert updated.output_format == "メール"

    def test_extract_slack_output_format(self):
        """Test extraction of Slack output format."""
        current = RequirementState()
        updated = extract_requirement_from_message(
            "Slackに通知してください", "わかりました", current
        )
        assert updated.output_format == "Slack通知"

    def test_extract_daily_schedule(self):
        """Test extraction of daily schedule."""
        current = RequirementState()
        updated = extract_requirement_from_message(
            "毎日実行してください", "承知しました", current
        )
        assert updated.schedule == "毎日実行"

    def test_extract_weekly_schedule(self):
        """Test extraction of weekly schedule."""
        current = RequirementState()
        updated = extract_requirement_from_message(
            "毎週実行します", "わかりました", current
        )
        assert updated.schedule == "毎週実行"

    def test_extract_monthly_schedule(self):
        """Test extraction of monthly schedule."""
        current = RequirementState()
        updated = extract_requirement_from_message(
            "毎月実行してください", "承知しました", current
        )
        assert updated.schedule == "毎月実行"

    def test_extract_on_demand_schedule(self):
        """Test extraction of on-demand schedule."""
        current = RequirementState()
        updated = extract_requirement_from_message(
            "オンデマンドで実行します", "わかりました", current
        )
        assert updated.schedule == "オンデマンド実行"

    def test_extract_multiple_requirements(self):
        """Test extraction of multiple requirements from single message."""
        current = RequirementState()
        updated = extract_requirement_from_message(
            "CSVファイルを分析して、Excelレポートを毎日生成してください",
            "かしこまりました。CSVファイルから分析を行い、Excelレポートを毎日生成いたします",
            current,
        )
        assert updated.data_source == "CSVファイル"
        assert updated.process_description is not None
        assert "分析" in updated.process_description
        assert updated.output_format == "Excelレポート"
        assert updated.schedule == "毎日実行"
        assert updated.completeness == 1.0  # All requirements filled

    def test_does_not_overwrite_existing_requirements(self):
        """Test that extraction does not overwrite already-filled requirements."""
        current = RequirementState(data_source="CSVファイル")
        updated = extract_requirement_from_message(
            "Excelファイルを使います", "承知しました", current
        )
        # Should preserve original data_source
        assert updated.data_source == "CSVファイル"

    def test_completeness_recalculated(self):
        """Test that completeness is recalculated after extraction."""
        current = RequirementState(data_source="CSVファイル", completeness=0.25)
        updated = extract_requirement_from_message(
            "データを分析します", "わかりました", current
        )
        # Should have data_source (0.25) + process (0.35) = 0.60
        assert updated.completeness == 0.60

    def test_process_description_length_limit(self):
        """Test that process description is limited to 100 characters."""
        current = RequirementState()
        long_message = "分析" + "あ" * 200  # 201 chars total
        updated = extract_requirement_from_message(
            long_message, "承知しました", current
        )
        assert updated.process_description is not None
        assert len(updated.process_description) <= 100


class TestCreateRequirementClarificationPrompt:
    """Test suite for prompt generation."""

    def test_prompt_includes_conversation_start(self):
        """Test prompt generation for first message (no history)."""
        prompt = create_requirement_clarification_prompt(
            "売上データを分析したい", [], RequirementState()
        )
        assert "(対話開始)" in prompt
        assert "売上データを分析したい" in prompt

    def test_prompt_includes_previous_messages(self):
        """Test prompt includes conversation history."""
        previous_messages = [
            {"role": "user", "content": "こんにちは"},
            {"role": "assistant", "content": "お手伝いできることがあります"},
        ]
        prompt = create_requirement_clarification_prompt(
            "売上データを分析したい", previous_messages, RequirementState()
        )
        assert "user: こんにちは" in prompt
        assert "assistant: お手伝いできることがあります" in prompt

    def test_prompt_limits_history_to_10_messages(self):
        """Test prompt limits conversation history to last 10 messages."""
        previous_messages = [
            {"role": "user", "content": f"Message {i}"} for i in range(20)
        ]
        prompt = create_requirement_clarification_prompt(
            "最新メッセージ", previous_messages, RequirementState()
        )
        # Should only include last 10 messages (10-19)
        assert "Message 10" in prompt
        assert "Message 19" in prompt
        assert "Message 0" not in prompt
        assert "Message 9" not in prompt

    def test_prompt_shows_current_requirements(self):
        """Test prompt displays current requirement state."""
        current = RequirementState(
            data_source="CSVファイル",
            process_description="データ分析",
            completeness=0.60,  # Explicitly set completeness
        )
        prompt = create_requirement_clarification_prompt(
            "どうすればいいですか", [], current
        )
        assert "データソース: CSVファイル" in prompt
        assert "処理内容: データ分析" in prompt
        assert "60%" in prompt  # Completeness

    def test_prompt_shows_undefined_requirements(self):
        """Test prompt shows '未定' for unfilled requirements."""
        prompt = create_requirement_clarification_prompt(
            "こんにちは", [], RequirementState()
        )
        assert "データソース: 未定" in prompt
        assert "処理内容: 未定" in prompt
        assert "出力形式: 未定" in prompt
        assert "スケジュール: 未定" in prompt

    def test_prompt_includes_next_question_hint_for_process(self):
        """Test prompt includes hint to ask about process description."""
        prompt = create_requirement_clarification_prompt(
            "こんにちは", [], RequirementState()
        )
        assert "まず処理内容を聞きましょう" in prompt

    def test_prompt_includes_next_question_hint_for_data_source(self):
        """Test prompt includes hint to ask about data source after process."""
        current = RequirementState(process_description="データ分析")
        prompt = create_requirement_clarification_prompt(
            "データを分析します", [], current
        )
        assert "次はデータソースを聞きましょう" in prompt

    def test_prompt_includes_next_question_hint_for_output(self):
        """Test prompt includes hint to ask about output format."""
        current = RequirementState(data_source="CSV", process_description="データ分析")
        prompt = create_requirement_clarification_prompt(
            "CSVから分析します", [], current
        )
        assert "次は出力形式を聞きましょう" in prompt

    def test_prompt_includes_next_question_hint_for_schedule(self):
        """Test prompt includes hint to ask about schedule."""
        current = RequirementState(
            data_source="CSV", process_description="データ分析", output_format="Excel"
        )
        prompt = create_requirement_clarification_prompt(
            "Excelで出力します", [], current
        )
        assert "最後にスケジュールを聞きましょう" in prompt

    def test_prompt_no_hint_when_complete(self):
        """Test prompt has no hint when requirements are ≥80% complete."""
        current = RequirementState(
            data_source="CSV",
            process_description="データ分析",
            output_format="Excel",
            completeness=0.85,
        )
        prompt = create_requirement_clarification_prompt("完了しました", [], current)
        # Should not have any hints
        assert "ヒント:" not in prompt
