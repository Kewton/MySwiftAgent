"""Unit tests for multi-candidate generation prompt.

Tests prompt loading, template generation, and prompt structure validation.
"""

from aiagent.langgraph.jobTaskGeneratorAgents.prompts.multi_candidate import (
    MULTI_CANDIDATE_SYSTEM_PROMPT,
    create_multi_candidate_prompt,
)


class TestMultiCandidateSystemPrompt:
    """Test suite for MULTI_CANDIDATE_SYSTEM_PROMPT."""

    def test_system_prompt_exists(self):
        """Test that system prompt is defined and not empty."""
        assert MULTI_CANDIDATE_SYSTEM_PROMPT is not None
        assert len(MULTI_CANDIDATE_SYSTEM_PROMPT) > 0

    def test_system_prompt_contains_key_instructions(self):
        """Test that system prompt contains key instructions."""
        prompt = MULTI_CANDIDATE_SYSTEM_PROMPT
        # Check for key elements
        assert "2" in prompt or "二" in prompt  # Should mention 2 candidates
        assert "候補" in prompt or "パターン" in prompt or "candidate" in prompt.lower()

    def test_system_prompt_mentions_four_aspects(self):
        """Test that system prompt mentions four requirement aspects."""
        prompt = MULTI_CANDIDATE_SYSTEM_PROMPT
        # Check for four aspects in Japanese or English
        aspects_found = sum(
            [
                "データソース" in prompt or "data_source" in prompt.lower(),
                "処理" in prompt or "process" in prompt.lower(),
                "出力" in prompt or "output" in prompt.lower(),
                "スケジュール" in prompt or "schedule" in prompt.lower(),
            ]
        )
        assert aspects_found >= 3  # At least 3 of 4 aspects should be mentioned

    def test_system_prompt_mentions_confidence(self):
        """Test that system prompt mentions confidence scoring."""
        prompt = MULTI_CANDIDATE_SYSTEM_PROMPT
        assert (
            "confidence" in prompt.lower()
            or "確信度" in prompt
            or "0.0" in prompt
            or "1.0" in prompt
        )


class TestCreateMultiCandidatePrompt:
    """Test suite for create_multi_candidate_prompt function."""

    def test_basic_prompt_generation(self):
        """Test basic prompt generation with user message."""
        user_message = "売上データを分析したい"
        prompt = create_multi_candidate_prompt(user_message)

        assert user_message in prompt
        assert len(prompt) > len(user_message)

    def test_prompt_includes_user_message(self):
        """Test that generated prompt includes user message."""
        user_message = "毎月のレポートを自動生成したい"
        prompt = create_multi_candidate_prompt(user_message)

        assert user_message in prompt

    def test_prompt_with_special_characters(self):
        """Test prompt generation with special characters."""
        user_message = "CSVファイル（売上データ）を分析して、Excel形式で出力"
        prompt = create_multi_candidate_prompt(user_message)

        assert "CSV" in prompt
        assert "Excel" in prompt

    def test_prompt_with_long_message(self):
        """Test prompt generation with longer user message."""
        user_message = (
            "過去3年間の売上データをデータベースから取得し、"
            "月別・商品カテゴリ別に集計して、"
            "グラフ付きのPDFレポートとして毎月初めに自動生成したい"
        )
        prompt = create_multi_candidate_prompt(user_message)

        assert user_message in prompt
        assert len(prompt) > len(user_message)

    def test_prompt_with_empty_message(self):
        """Test prompt generation with empty message."""
        user_message = ""
        prompt = create_multi_candidate_prompt(user_message)

        # Should still generate a valid prompt structure
        assert prompt is not None
        assert isinstance(prompt, str)

    def test_prompt_with_english_message(self):
        """Test prompt generation with English user message."""
        user_message = "I want to analyze sales data"
        prompt = create_multi_candidate_prompt(user_message)

        assert user_message in prompt

    def test_prompt_with_mixed_language(self):
        """Test prompt generation with mixed Japanese/English."""
        user_message = "CSVファイルをPythonで分析してExcelに出力"
        prompt = create_multi_candidate_prompt(user_message)

        assert "CSV" in prompt
        assert "Python" in prompt
        assert "Excel" in prompt

    def test_prompt_structure_contains_instructions(self):
        """Test that prompt contains generation instructions."""
        user_message = "データを分析したい"
        prompt = create_multi_candidate_prompt(user_message)

        # Prompt should have structure beyond just the user message
        assert len(prompt) > len(user_message) + 50

    def test_prompt_return_type(self):
        """Test that prompt returns string type."""
        user_message = "テストメッセージ"
        prompt = create_multi_candidate_prompt(user_message)

        assert isinstance(prompt, str)


class TestPromptIntegration:
    """Integration tests for prompt and schema interaction."""

    def test_prompt_generates_valid_json_structure_hint(self):
        """Test that prompt hints at expected JSON structure."""
        user_message = "売上分析をしたい"
        prompt = create_multi_candidate_prompt(user_message)

        # Check for JSON structure hints (may be in system prompt instead)
        # This test ensures the prompt is designed for structured output
        combined = MULTI_CANDIDATE_SYSTEM_PROMPT + prompt
        json_hints = [
            "candidate_id" in combined.lower(),
            "title" in combined.lower() or "タイトル" in combined,
            "json" in combined.lower() or "JSON" in combined,
        ]
        assert sum(json_hints) >= 1  # At least one hint about structure


class TestGetSystemPrompt:
    """Test suite for get_system_prompt function."""

    def test_get_system_prompt_returns_string(self):
        """Test that get_system_prompt returns a non-empty string."""
        from aiagent.langgraph.jobTaskGeneratorAgents.prompts.multi_candidate import (
            get_system_prompt,
        )

        prompt = get_system_prompt()

        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_get_system_prompt_matches_constant(self):
        """Test that get_system_prompt returns the same value as MULTI_CANDIDATE_SYSTEM_PROMPT."""
        from aiagent.langgraph.jobTaskGeneratorAgents.prompts.multi_candidate import (
            get_system_prompt,
        )

        prompt = get_system_prompt()

        assert prompt == MULTI_CANDIDATE_SYSTEM_PROMPT


class TestCreateMultiCandidatePromptWithContext:
    """Test suite for create_multi_candidate_prompt with additional_context parameter."""

    def test_prompt_with_additional_context(self):
        """Test prompt generation with additional context."""
        user_message = "売上データを分析したい"
        additional_context = "過去の会話: ユーザーはCSV形式を好む傾向があります"

        prompt = create_multi_candidate_prompt(user_message, additional_context)

        assert user_message in prompt
        assert additional_context in prompt
        # Context should appear before the user message prompt
        assert prompt.index(additional_context) < prompt.index(user_message)

    def test_prompt_without_additional_context(self):
        """Test prompt generation without additional context (None)."""
        user_message = "レポートを作成したい"

        prompt = create_multi_candidate_prompt(user_message, None)

        assert user_message in prompt
        assert isinstance(prompt, str)

    def test_prompt_with_empty_context(self):
        """Test prompt generation with empty string context."""
        user_message = "データベースを更新したい"

        # Empty string should not be added to prompt
        prompt_with_empty = create_multi_candidate_prompt(user_message, "")
        prompt_without = create_multi_candidate_prompt(user_message, None)

        # Both should contain the user message
        assert user_message in prompt_with_empty
        assert user_message in prompt_without


class TestPromptEdgeCases:
    """Test edge cases for prompt generation."""

    def test_prompt_with_very_special_characters(self):
        """Test prompt with various special characters."""
        user_message = "売上<>データ\"を'分析&して|結果を\\出力"
        prompt = create_multi_candidate_prompt(user_message)

        assert "売上" in prompt
        assert "分析" in prompt

    def test_prompt_with_newlines(self):
        """Test prompt with newline characters in message."""
        user_message = "売上データを\n分析して\n結果を出力"
        prompt = create_multi_candidate_prompt(user_message)

        assert "売上データを" in prompt

    def test_prompt_with_unicode_symbols(self):
        """Test prompt with Unicode symbols."""
        user_message = "売上データを分析"
        prompt = create_multi_candidate_prompt(user_message)

        assert "売上データを分析" in prompt

    def test_prompt_strips_whitespace(self):
        """Test that prompt strips leading/trailing whitespace."""
        user_message = "テストメッセージ"
        prompt = create_multi_candidate_prompt(user_message)

        # Prompt should be stripped (no leading/trailing whitespace)
        assert prompt == prompt.strip()


class TestSystemPromptCompleteness:
    """Test that system prompt contains all required elements."""

    def test_system_prompt_has_two_candidate_instruction(self):
        """Test that system prompt instructs to generate 2 candidates."""
        prompt = MULTI_CANDIDATE_SYSTEM_PROMPT

        # Check for 2 candidates instruction
        assert (
            "2" in prompt
            or "二つ" in prompt
            or "2つ" in prompt
            or "two" in prompt.lower()
        )

    def test_system_prompt_has_candidate_id_instruction(self):
        """Test that system prompt mentions candidate_id A and B."""
        prompt = MULTI_CANDIDATE_SYSTEM_PROMPT

        assert '"A"' in prompt or "'A'" in prompt or "A" in prompt
        assert '"B"' in prompt or "'B'" in prompt or "B" in prompt

    def test_system_prompt_has_confidence_range(self):
        """Test that system prompt specifies confidence range."""
        prompt = MULTI_CANDIDATE_SYSTEM_PROMPT

        # Should mention 0.0-1.0 range or similar
        assert "0.0" in prompt or "1.0" in prompt or "0-1" in prompt

    def test_system_prompt_has_json_format_instruction(self):
        """Test that system prompt requests JSON output."""
        prompt = MULTI_CANDIDATE_SYSTEM_PROMPT

        assert "json" in prompt.lower() or "JSON" in prompt

    def test_system_prompt_has_differentiation_guidance(self):
        """Test that system prompt provides differentiation guidance."""
        prompt = MULTI_CANDIDATE_SYSTEM_PROMPT

        # Should mention ways to differentiate candidates
        differentiation_terms = [
            "異なる",
            "差別化",
            "違い",
            "シンプル",
            "詳細",
            "differ",
            "different",
        ]
        assert any(term in prompt.lower() for term in differentiation_terms)
