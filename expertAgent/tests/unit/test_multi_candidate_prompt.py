"""Unit tests for multi-candidate generation prompt.

Tests prompt loading, template generation, and prompt structure validation.
"""

import pytest

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
