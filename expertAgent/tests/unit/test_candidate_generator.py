"""Unit tests for candidate generator service.

Tests the generate_requirement_candidates function and related logic.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.chat import RequirementCandidate
from app.services.conversation.candidate_generator import (
    generate_requirement_candidates,
)


class TestGenerateRequirementCandidates:
    """Test suite for generate_requirement_candidates function."""

    @pytest.mark.asyncio
    async def test_generates_two_candidates(self):
        """Test that function generates exactly two candidates."""
        mock_candidates = [
            RequirementCandidate(
                candidate_id="A",
                title="簡易分析",
                data_source="CSVファイル",
                process_description="基本的な売上集計",
                output_format="Excelレポート",
                schedule="オンデマンド",
                confidence=0.85,
            ),
            RequirementCandidate(
                candidate_id="B",
                title="詳細分析",
                data_source="データベース",
                process_description="詳細なトレンド分析",
                output_format="PDFレポート",
                schedule="毎日実行",
                confidence=0.75,
            ),
        ]

        with patch(
            "app.services.conversation.candidate_generator._invoke_llm_for_candidates",
            new_callable=AsyncMock,
            return_value=mock_candidates,
        ):
            result = await generate_requirement_candidates("売上データを分析したい")

        assert len(result) == 2
        assert result[0].candidate_id == "A"
        assert result[1].candidate_id == "B"

    @pytest.mark.asyncio
    async def test_candidates_have_required_fields(self):
        """Test that generated candidates have all required fields."""
        mock_candidates = [
            RequirementCandidate(
                candidate_id="A",
                title="テスト候補A",
                data_source="CSV",
                process_description="処理A",
                output_format="Excel",
                schedule="毎日",
                confidence=0.8,
            ),
            RequirementCandidate(
                candidate_id="B",
                title="テスト候補B",
                data_source="DB",
                process_description="処理B",
                output_format="PDF",
                schedule="毎週",
                confidence=0.7,
            ),
        ]

        with patch(
            "app.services.conversation.candidate_generator._invoke_llm_for_candidates",
            new_callable=AsyncMock,
            return_value=mock_candidates,
        ):
            result = await generate_requirement_candidates("テストメッセージ")

        for candidate in result:
            assert candidate.candidate_id in ["A", "B"]
            assert candidate.title is not None
            assert candidate.data_source is not None
            assert candidate.process_description is not None
            assert candidate.output_format is not None
            assert candidate.schedule is not None
            assert 0.0 <= candidate.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_candidates_have_different_interpretations(self):
        """Test that candidates have distinct interpretations."""
        mock_candidates = [
            RequirementCandidate(
                candidate_id="A",
                title="シンプル集計",
                data_source="CSVファイル",
                process_description="月別売上の単純集計",
                output_format="Excelファイル",
                schedule="オンデマンド",
                confidence=0.9,
            ),
            RequirementCandidate(
                candidate_id="B",
                title="高度な分析",
                data_source="データベース",
                process_description="AIによるトレンド予測分析",
                output_format="インタラクティブダッシュボード",
                schedule="リアルタイム",
                confidence=0.7,
            ),
        ]

        with patch(
            "app.services.conversation.candidate_generator._invoke_llm_for_candidates",
            new_callable=AsyncMock,
            return_value=mock_candidates,
        ):
            result = await generate_requirement_candidates("売上データを分析したい")

        # Check that candidates are different
        assert result[0].title != result[1].title
        assert (
            result[0].process_description != result[1].process_description
            or result[0].output_format != result[1].output_format
        )

    @pytest.mark.asyncio
    async def test_handles_llm_error_gracefully(self):
        """Test graceful handling of LLM errors."""
        with patch(
            "app.services.conversation.candidate_generator._invoke_llm_for_candidates",
            new_callable=AsyncMock,
            side_effect=Exception("LLM service unavailable"),
        ):
            with pytest.raises(Exception) as exc_info:
                await generate_requirement_candidates("売上データを分析したい")

            assert "LLM" in str(exc_info.value) or "unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_handles_empty_user_message(self):
        """Test handling of empty user message."""
        mock_candidates = [
            RequirementCandidate(
                candidate_id="A",
                title="一般的なデータ処理",
                data_source="不明",
                process_description="データの整理と出力",
                output_format="Excel",
                schedule="オンデマンド",
                confidence=0.5,
            ),
            RequirementCandidate(
                candidate_id="B",
                title="レポート生成",
                data_source="不明",
                process_description="レポート作成",
                output_format="PDF",
                schedule="毎週",
                confidence=0.4,
            ),
        ]

        with patch(
            "app.services.conversation.candidate_generator._invoke_llm_for_candidates",
            new_callable=AsyncMock,
            return_value=mock_candidates,
        ):
            result = await generate_requirement_candidates("")

        # Should still return candidates with lower confidence
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_candidate_ids_are_a_and_b(self):
        """Test that candidate IDs are exactly 'A' and 'B'."""
        mock_candidates = [
            RequirementCandidate(
                candidate_id="A",
                title="候補A",
                data_source="CSV",
                process_description="処理",
                output_format="Excel",
                schedule="毎日",
                confidence=0.8,
            ),
            RequirementCandidate(
                candidate_id="B",
                title="候補B",
                data_source="DB",
                process_description="処理",
                output_format="PDF",
                schedule="毎週",
                confidence=0.7,
            ),
        ]

        with patch(
            "app.services.conversation.candidate_generator._invoke_llm_for_candidates",
            new_callable=AsyncMock,
            return_value=mock_candidates,
        ):
            result = await generate_requirement_candidates("テスト")

        candidate_ids = [c.candidate_id for c in result]
        assert "A" in candidate_ids
        assert "B" in candidate_ids

    @pytest.mark.asyncio
    async def test_confidence_scores_are_valid(self):
        """Test that confidence scores are within valid range."""
        mock_candidates = [
            RequirementCandidate(
                candidate_id="A",
                title="高確信度",
                data_source="CSV",
                process_description="明確な処理",
                output_format="Excel",
                schedule="毎日",
                confidence=0.95,
            ),
            RequirementCandidate(
                candidate_id="B",
                title="低確信度",
                data_source="不明",
                process_description="推測的な処理",
                output_format="不明",
                schedule="未定",
                confidence=0.45,
            ),
        ]

        with patch(
            "app.services.conversation.candidate_generator._invoke_llm_for_candidates",
            new_callable=AsyncMock,
            return_value=mock_candidates,
        ):
            result = await generate_requirement_candidates("曖昧なリクエスト")

        for candidate in result:
            assert 0.0 <= candidate.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_user_message_is_passed_to_llm(self):
        """Test that user message is correctly passed to LLM."""
        test_message = "売上データを月別にグラフ化したい"
        mock_candidates = [
            RequirementCandidate(
                candidate_id="A",
                title="テスト",
                data_source="CSV",
                process_description="処理",
                output_format="Excel",
                schedule="毎日",
                confidence=0.8,
            ),
            RequirementCandidate(
                candidate_id="B",
                title="テスト2",
                data_source="DB",
                process_description="処理2",
                output_format="PDF",
                schedule="毎週",
                confidence=0.7,
            ),
        ]

        with patch(
            "app.services.conversation.candidate_generator._invoke_llm_for_candidates",
            new_callable=AsyncMock,
            return_value=mock_candidates,
        ) as mock_llm:
            await generate_requirement_candidates(test_message)

        # Verify that the user message was passed to the LLM
        mock_llm.assert_called_once()
        call_args = mock_llm.call_args
        assert test_message in str(call_args)


class TestCandidateGeneratorEdgeCases:
    """Test edge cases for candidate generator."""

    @pytest.mark.asyncio
    async def test_very_long_user_message(self):
        """Test handling of very long user messages."""
        long_message = "データ分析 " * 100  # Very long message
        mock_candidates = [
            RequirementCandidate(
                candidate_id="A",
                title="長文解釈A",
                data_source="CSV",
                process_description="処理A",
                output_format="Excel",
                schedule="毎日",
                confidence=0.7,
            ),
            RequirementCandidate(
                candidate_id="B",
                title="長文解釈B",
                data_source="DB",
                process_description="処理B",
                output_format="PDF",
                schedule="毎週",
                confidence=0.6,
            ),
        ]

        with patch(
            "app.services.conversation.candidate_generator._invoke_llm_for_candidates",
            new_callable=AsyncMock,
            return_value=mock_candidates,
        ):
            result = await generate_requirement_candidates(long_message)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_special_characters_in_message(self):
        """Test handling of special characters in user message."""
        special_message = "CSVファイル（売上.csv）を分析して、Excel形式（.xlsx）で出力！？"
        mock_candidates = [
            RequirementCandidate(
                candidate_id="A",
                title="特殊文字A",
                data_source="CSV",
                process_description="処理A",
                output_format="Excel",
                schedule="毎日",
                confidence=0.8,
            ),
            RequirementCandidate(
                candidate_id="B",
                title="特殊文字B",
                data_source="DB",
                process_description="処理B",
                output_format="PDF",
                schedule="毎週",
                confidence=0.7,
            ),
        ]

        with patch(
            "app.services.conversation.candidate_generator._invoke_llm_for_candidates",
            new_callable=AsyncMock,
            return_value=mock_candidates,
        ):
            result = await generate_requirement_candidates(special_message)

        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_unicode_in_message(self):
        """Test handling of Unicode characters in user message."""
        unicode_message = "売上データを分析"
        mock_candidates = [
            RequirementCandidate(
                candidate_id="A",
                title="日本語候補",
                data_source="CSV",
                process_description="処理",
                output_format="Excel",
                schedule="毎日",
                confidence=0.8,
            ),
            RequirementCandidate(
                candidate_id="B",
                title="別の候補",
                data_source="DB",
                process_description="処理2",
                output_format="PDF",
                schedule="毎週",
                confidence=0.7,
            ),
        ]

        with patch(
            "app.services.conversation.candidate_generator._invoke_llm_for_candidates",
            new_callable=AsyncMock,
            return_value=mock_candidates,
        ):
            result = await generate_requirement_candidates(unicode_message)

        assert len(result) == 2
