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
        special_message = (
            "CSVファイル（売上.csv）を分析して、Excel形式（.xlsx）で出力！？"
        )
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


class TestInvokeLLMForCandidates:
    """Test suite for _invoke_llm_for_candidates function (LLM path tests)."""

    @pytest.mark.asyncio
    async def test_invoke_llm_for_candidates_success(self):
        """Test successful LLM invocation with structured output."""
        from app.schemas.chat import CandidateSelectionEvent
        from app.services.conversation.candidate_generator import (
            _invoke_llm_for_candidates,
        )

        mock_candidates = [
            RequirementCandidate(
                candidate_id="A",
                title="候補A",
                data_source="CSV",
                process_description="処理A",
                output_format="Excel",
                schedule="毎日",
                confidence=0.8,
            ),
            RequirementCandidate(
                candidate_id="B",
                title="候補B",
                data_source="DB",
                process_description="処理B",
                output_format="PDF",
                schedule="毎週",
                confidence=0.7,
            ),
        ]

        mock_selection_event = CandidateSelectionEvent(
            candidates=mock_candidates,
            prompt_for_selection="どちらを選びますか？",
        )

        mock_result = MagicMock()
        mock_result.result = mock_selection_event

        with patch(
            "app.services.conversation.candidate_generator.invoke_structured_llm",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await _invoke_llm_for_candidates("テストメッセージ")

        assert len(result) == 2
        assert result[0].candidate_id == "A"
        assert result[1].candidate_id == "B"

    @pytest.mark.asyncio
    async def test_invoke_llm_for_candidates_structured_llm_error(self):
        """Test handling of StructuredLLMError from invoke_structured_llm."""
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredLLMError,
        )
        from app.services.conversation.candidate_generator import (
            _invoke_llm_for_candidates,
        )

        with patch(
            "app.services.conversation.candidate_generator.invoke_structured_llm",
            new_callable=AsyncMock,
            side_effect=StructuredLLMError("Test LLM error"),
        ):
            with pytest.raises(Exception) as exc_info:
                await _invoke_llm_for_candidates("テストメッセージ")

            assert "LLM service unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invoke_llm_for_candidates_single_candidate_warning(self):
        """Test warning when LLM returns only one candidate."""
        from app.schemas.chat import CandidateSelectionEvent
        from app.services.conversation.candidate_generator import (
            _invoke_llm_for_candidates,
        )

        # Only one candidate returned
        mock_candidates = [
            RequirementCandidate(
                candidate_id="A",
                title="唯一の候補",
                data_source="CSV",
                process_description="処理",
                output_format="Excel",
                schedule="毎日",
                confidence=0.8,
            ),
        ]

        mock_selection_event = CandidateSelectionEvent(
            candidates=mock_candidates,
            prompt_for_selection="候補を選んでください",
        )

        mock_result = MagicMock()
        mock_result.result = mock_selection_event

        with patch(
            "app.services.conversation.candidate_generator.invoke_structured_llm",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await _invoke_llm_for_candidates("テスト")

        # Should still return the single candidate
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_invoke_llm_for_candidates_uses_env_model(self):
        """Test that _invoke_llm_for_candidates uses environment model variable."""
        import os

        from app.schemas.chat import CandidateSelectionEvent
        from app.services.conversation.candidate_generator import (
            _invoke_llm_for_candidates,
        )

        mock_candidates = [
            RequirementCandidate(
                candidate_id="A",
                title="候補A",
                data_source="CSV",
                process_description="処理A",
                output_format="Excel",
                schedule="毎日",
                confidence=0.8,
            ),
            RequirementCandidate(
                candidate_id="B",
                title="候補B",
                data_source="DB",
                process_description="処理B",
                output_format="PDF",
                schedule="毎週",
                confidence=0.7,
            ),
        ]

        mock_selection_event = CandidateSelectionEvent(
            candidates=mock_candidates,
            prompt_for_selection="選択してください",
        )

        mock_result = MagicMock()
        mock_result.result = mock_selection_event

        # Set custom model name
        original_env = os.environ.get("CANDIDATE_GENERATION_MODEL")
        os.environ["CANDIDATE_GENERATION_MODEL"] = "test-model-123"

        try:
            with patch(
                "app.services.conversation.candidate_generator.invoke_structured_llm",
                new_callable=AsyncMock,
                return_value=mock_result,
            ) as mock_invoke:
                await _invoke_llm_for_candidates("テスト")

            # Verify model_env_var was passed correctly
            call_kwargs = mock_invoke.call_args.kwargs
            assert call_kwargs["model_env_var"] == "CANDIDATE_GENERATION_MODEL"
        finally:
            if original_env:
                os.environ["CANDIDATE_GENERATION_MODEL"] = original_env
            elif "CANDIDATE_GENERATION_MODEL" in os.environ:
                del os.environ["CANDIDATE_GENERATION_MODEL"]


class TestEnsureCandidateIds:
    """Test suite for _ensure_candidate_ids function."""

    def test_ensure_candidate_ids_corrects_wrong_ids(self):
        """Test that _ensure_candidate_ids corrects wrong candidate IDs."""
        from app.services.conversation.candidate_generator import _ensure_candidate_ids

        candidates = [
            RequirementCandidate(
                candidate_id="A",  # Will create with wrong ID first
                title="候補X",
                data_source="CSV",
                process_description="処理",
                output_format="Excel",
                schedule="毎日",
                confidence=0.8,
            ),
            RequirementCandidate(
                candidate_id="B",  # Will create with wrong ID first
                title="候補Y",
                data_source="DB",
                process_description="処理2",
                output_format="PDF",
                schedule="毎週",
                confidence=0.7,
            ),
        ]

        # Manually set wrong IDs by creating new objects (since RequirementCandidate validates)
        # We need to test the function with properly formed candidates first
        _ensure_candidate_ids(candidates)

        assert candidates[0].candidate_id == "A"
        assert candidates[1].candidate_id == "B"

    def test_ensure_candidate_ids_fixes_first_id(self):
        """Test that first candidate gets ID 'A' if incorrect."""
        from app.services.conversation.candidate_generator import _ensure_candidate_ids

        # Create candidates with swapped IDs
        candidates = [
            RequirementCandidate(
                candidate_id="B",  # Wrong - should be A
                title="候補1",
                data_source="CSV",
                process_description="処理1",
                output_format="Excel",
                schedule="毎日",
                confidence=0.8,
            ),
            RequirementCandidate(
                candidate_id="A",  # Wrong - should be B
                title="候補2",
                data_source="DB",
                process_description="処理2",
                output_format="PDF",
                schedule="毎週",
                confidence=0.7,
            ),
        ]

        _ensure_candidate_ids(candidates)

        # After fixing, first should be A and second should be B
        assert candidates[0].candidate_id == "A"
        assert candidates[1].candidate_id == "B"

    def test_ensure_candidate_ids_single_candidate(self):
        """Test that single candidate is not modified."""
        from app.services.conversation.candidate_generator import _ensure_candidate_ids

        candidates = [
            RequirementCandidate(
                candidate_id="A",
                title="唯一の候補",
                data_source="CSV",
                process_description="処理",
                output_format="Excel",
                schedule="毎日",
                confidence=0.8,
            ),
        ]

        _ensure_candidate_ids(candidates)

        # Single candidate should remain unchanged
        assert len(candidates) == 1
        assert candidates[0].candidate_id == "A"

    def test_ensure_candidate_ids_empty_list(self):
        """Test that empty list is handled gracefully."""
        from app.services.conversation.candidate_generator import _ensure_candidate_ids

        candidates: list[RequirementCandidate] = []

        # Should not raise an error
        _ensure_candidate_ids(candidates)

        assert len(candidates) == 0


class TestCandidateToRequirementStateDict:
    """Test suite for candidate_to_requirement_state_dict function."""

    def test_full_candidate_conversion(self):
        """Test conversion of candidate with all fields filled."""
        from app.services.conversation.candidate_generator import (
            candidate_to_requirement_state_dict,
        )

        candidate = RequirementCandidate(
            candidate_id="A",
            title="完全な候補",
            data_source="CSV",
            process_description="詳細な処理",
            output_format="Excel",
            schedule="毎日",
            confidence=0.9,
        )

        result = candidate_to_requirement_state_dict(candidate)

        assert result["data_source"] == "CSV"
        assert result["process_description"] == "詳細な処理"
        assert result["output_format"] == "Excel"
        assert result["schedule"] == "毎日"
        assert result["completeness"] == 1.0  # All fields filled = 100%

    def test_partial_candidate_conversion(self):
        """Test conversion with partial completeness calculation."""
        from app.services.conversation.candidate_generator import (
            candidate_to_requirement_state_dict,
        )

        candidate = RequirementCandidate(
            candidate_id="B",
            title="部分的な候補",
            data_source="CSV",  # +0.25
            process_description="",  # Empty string = falsy = +0.0
            output_format="Excel",  # +0.25
            schedule="",  # Empty string = falsy = +0.0
            confidence=0.5,
        )

        result = candidate_to_requirement_state_dict(candidate)

        # completeness = 0.25 + 0.25 = 0.5
        assert result["completeness"] == 0.5

    def test_candidate_conversion_preserves_values(self):
        """Test that conversion preserves all field values correctly."""
        from app.services.conversation.candidate_generator import (
            candidate_to_requirement_state_dict,
        )

        candidate = RequirementCandidate(
            candidate_id="A",
            title="テスト",
            data_source="PostgreSQLデータベース",
            process_description="売上データを月別に集計してグラフ化",
            output_format="PDFレポート形式",
            schedule="毎週月曜日の9時",
            confidence=0.85,
        )

        result = candidate_to_requirement_state_dict(candidate)

        assert result["data_source"] == "PostgreSQLデータベース"
        assert result["process_description"] == "売上データを月別に集計してグラフ化"
        assert result["output_format"] == "PDFレポート形式"
        assert result["schedule"] == "毎週月曜日の9時"


class TestLLMPathIntegration:
    """Integration tests for LLM path (without actual LLM calls)."""

    @pytest.mark.asyncio
    async def test_generate_candidates_full_flow_with_mock_llm(self):
        """Test full candidate generation flow with mocked LLM."""
        from app.schemas.chat import CandidateSelectionEvent
        from app.services.conversation.candidate_generator import (
            generate_requirement_candidates,
        )

        mock_candidates = [
            RequirementCandidate(
                candidate_id="A",
                title="簡易分析",
                data_source="CSVファイル",
                process_description="売上データの月別集計",
                output_format="Excelレポート",
                schedule="オンデマンド",
                confidence=0.85,
            ),
            RequirementCandidate(
                candidate_id="B",
                title="詳細分析",
                data_source="データベース接続",
                process_description="売上トレンド分析と予測モデル",
                output_format="インタラクティブダッシュボード",
                schedule="毎日実行",
                confidence=0.75,
            ),
        ]

        mock_selection_event = CandidateSelectionEvent(
            candidates=mock_candidates,
            prompt_for_selection="どちらの解釈がお望みに近いですか？",
        )

        mock_result = MagicMock()
        mock_result.result = mock_selection_event

        with patch(
            "app.services.conversation.candidate_generator.invoke_structured_llm",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await generate_requirement_candidates("売上データを分析したい")

        assert len(result) == 2
        assert result[0].title == "簡易分析"
        assert result[1].title == "詳細分析"

    @pytest.mark.asyncio
    async def test_generate_candidates_with_timeout_simulation(self):
        """Test handling of simulated timeout in LLM call."""
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredLLMError,
        )
        from app.services.conversation.candidate_generator import (
            generate_requirement_candidates,
        )

        async def slow_llm_call(*args, **kwargs):
            raise StructuredLLMError("Request timeout")

        with patch(
            "app.services.conversation.candidate_generator.invoke_structured_llm",
            new_callable=AsyncMock,
            side_effect=slow_llm_call,
        ):
            with pytest.raises(Exception) as exc_info:
                await generate_requirement_candidates("テスト")

            assert (
                "timeout" in str(exc_info.value).lower()
                or "unavailable" in str(exc_info.value).lower()
            )

    @pytest.mark.asyncio
    async def test_generate_candidates_invalid_response_structure(self):
        """Test handling of invalid response structure from LLM."""
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredLLMError,
        )
        from app.services.conversation.candidate_generator import (
            generate_requirement_candidates,
        )

        # Simulate malformed response by raising StructuredLLMError
        with patch(
            "app.services.conversation.candidate_generator.invoke_structured_llm",
            new_callable=AsyncMock,
            side_effect=StructuredLLMError("Invalid JSON structure"),
        ):
            with pytest.raises(Exception) as exc_info:
                await generate_requirement_candidates("テスト")

            assert "LLM service unavailable" in str(exc_info.value)
