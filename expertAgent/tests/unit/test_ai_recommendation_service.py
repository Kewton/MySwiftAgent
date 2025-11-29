"""Unit tests for AI recommendation service - Issue #174.

Tests for the integrated AI recommendation service.
"""

import time

import pytest

from app.schemas.chat import RequirementCandidate
from app.schemas.recommendation import AIRecommendation, ComplexityLevel
from app.services.recommendation.ai_recommendation_service import (
    AIRecommendationService,
    generate_recommendation,
)


class TestAIRecommendationService:
    """Test AIRecommendationService class."""

    @pytest.fixture
    def service(self) -> AIRecommendationService:
        """Create AIRecommendationService instance."""
        return AIRecommendationService()

    @pytest.fixture
    def simple_candidate_a(self) -> RequirementCandidate:
        """Create a simple candidate A."""
        return RequirementCandidate(
            candidate_id="A",
            title="簡易集計",
            data_source="CSVファイル",
            process_description="売上データの月別集計",
            output_format="Excelレポート",
            schedule="オンデマンド",
            confidence=0.8,
        )

    @pytest.fixture
    def complex_candidate_b(self) -> RequirementCandidate:
        """Create a complex candidate B."""
        return RequirementCandidate(
            candidate_id="B",
            title="予測分析",
            data_source="API連携",
            process_description="機械学習による売上予測と自動通知",
            output_format="リアルタイムダッシュボード",
            schedule="毎日自動実行",
            confidence=0.75,
        )

    def test_recommend_returns_ai_recommendation(
        self,
        service: AIRecommendationService,
        simple_candidate_a: RequirementCandidate,
        complex_candidate_b: RequirementCandidate,
    ) -> None:
        """Test that recommend returns AIRecommendation object."""
        result = service.recommend(
            user_message="売上データを集計してCSVで出力してください",
            candidates=[simple_candidate_a, complex_candidate_b],
        )

        assert isinstance(result, AIRecommendation)

    def test_recommend_simple_message_selects_simple_candidate(
        self,
        service: AIRecommendationService,
        simple_candidate_a: RequirementCandidate,
        complex_candidate_b: RequirementCandidate,
    ) -> None:
        """Test that simple message recommends simple candidate."""
        result = service.recommend(
            user_message="売上データを集計してCSVで出力してください",
            candidates=[simple_candidate_a, complex_candidate_b],
        )

        # Simple message should prefer simple candidate (A)
        assert result.recommended_candidate_id == "A"
        assert result.complexity == ComplexityLevel.SIMPLE

    def test_recommend_complex_message_selects_complex_candidate(
        self,
        service: AIRecommendationService,
        simple_candidate_a: RequirementCandidate,
        complex_candidate_b: RequirementCandidate,
    ) -> None:
        """Test that complex message recommends complex candidate."""
        result = service.recommend(
            user_message="機械学習を使って売上を予測し、APIで自動連携してください",
            candidates=[simple_candidate_a, complex_candidate_b],
        )

        # Complex message should prefer complex candidate (B)
        assert result.recommended_candidate_id == "B"
        assert result.complexity == ComplexityLevel.COMPLEX

    def test_recommend_confidence_in_valid_range(
        self,
        service: AIRecommendationService,
        simple_candidate_a: RequirementCandidate,
        complex_candidate_b: RequirementCandidate,
    ) -> None:
        """Test that confidence is in valid range."""
        result = service.recommend(
            user_message="データを分析してください",
            candidates=[simple_candidate_a, complex_candidate_b],
        )

        assert 0.0 <= result.confidence <= 1.0

    def test_recommend_generates_reason(
        self,
        service: AIRecommendationService,
        simple_candidate_a: RequirementCandidate,
        complex_candidate_b: RequirementCandidate,
    ) -> None:
        """Test that recommendation includes a reason."""
        result = service.recommend(
            user_message="売上データを集計してください",
            candidates=[simple_candidate_a, complex_candidate_b],
        )

        assert result.reason
        assert len(result.reason) > 0
        assert len(result.reason) <= 200

    def test_recommend_includes_detected_keywords(
        self,
        service: AIRecommendationService,
        simple_candidate_a: RequirementCandidate,
        complex_candidate_b: RequirementCandidate,
    ) -> None:
        """Test that recommendation includes detected keywords."""
        result = service.recommend(
            user_message="売上データを集計してCSVで出力",
            candidates=[simple_candidate_a, complex_candidate_b],
        )

        assert isinstance(result.keywords_detected, list)
        assert "集計" in result.keywords_detected
        assert "CSV" in result.keywords_detected

    def test_recommend_empty_message(
        self,
        service: AIRecommendationService,
        simple_candidate_a: RequirementCandidate,
        complex_candidate_b: RequirementCandidate,
    ) -> None:
        """Test recommendation with empty message."""
        result = service.recommend(
            user_message="",
            candidates=[simple_candidate_a, complex_candidate_b],
        )

        # Should still return a valid recommendation
        assert isinstance(result, AIRecommendation)
        # Empty message should default to simple complexity
        assert result.complexity == ComplexityLevel.SIMPLE
        # Low confidence for empty message
        assert result.confidence < 0.5

    def test_recommend_long_message(
        self,
        service: AIRecommendationService,
        simple_candidate_a: RequirementCandidate,
        complex_candidate_b: RequirementCandidate,
    ) -> None:
        """Test recommendation with long message (1000+ chars)."""
        base = "売上データを集計して分析し、"
        long_message = base * 50  # ~1000 chars

        result = service.recommend(
            user_message=long_message,
            candidates=[simple_candidate_a, complex_candidate_b],
        )

        assert isinstance(result, AIRecommendation)
        assert 0.0 <= result.confidence <= 1.0

    def test_recommend_performance_under_100ms(
        self,
        service: AIRecommendationService,
        simple_candidate_a: RequirementCandidate,
        complex_candidate_b: RequirementCandidate,
    ) -> None:
        """Test that recommendation completes within 100ms."""
        start_time = time.time()

        service.recommend(
            user_message="売上データを集計してCSVで出力してください",
            candidates=[simple_candidate_a, complex_candidate_b],
        )

        elapsed_time = (time.time() - start_time) * 1000  # ms
        assert elapsed_time < 100, f"Recommendation took {elapsed_time}ms"

    def test_recommend_medium_complexity_message(
        self,
        service: AIRecommendationService,
        simple_candidate_a: RequirementCandidate,
        complex_candidate_b: RequirementCandidate,
    ) -> None:
        """Test recommendation with medium complexity message."""
        result = service.recommend(
            user_message="複数のデータを比較してグラフで分析してください",
            candidates=[simple_candidate_a, complex_candidate_b],
        )

        assert result.complexity == ComplexityLevel.MEDIUM

    def test_recommend_accuracy_simple_cases(
        self,
        service: AIRecommendationService,
        simple_candidate_a: RequirementCandidate,
        complex_candidate_b: RequirementCandidate,
    ) -> None:
        """Test recommendation accuracy for simple cases."""
        simple_messages = [
            "売上一覧を表示してください",
            "データを合計してください",
            "CSVで出力してください",
            "Excelレポートを作成してください",
            "平均値を計算してください",
        ]

        correct_count = 0
        for msg in simple_messages:
            result = service.recommend(
                user_message=msg,
                candidates=[simple_candidate_a, complex_candidate_b],
            )
            if result.recommended_candidate_id == "A":
                correct_count += 1

        accuracy = correct_count / len(simple_messages)
        assert accuracy >= 0.8, f"Accuracy {accuracy} is below 80%"

    def test_recommend_accuracy_complex_cases(
        self,
        service: AIRecommendationService,
        simple_candidate_a: RequirementCandidate,
        complex_candidate_b: RequirementCandidate,
    ) -> None:
        """Test recommendation accuracy for complex cases."""
        complex_messages = [
            "機械学習で予測してください",
            "AIで自動化してください",
            "API連携でリアルタイム通知してください",
            "自動で連携してください",
            "予測モデルを作成してください",
        ]

        correct_count = 0
        for msg in complex_messages:
            result = service.recommend(
                user_message=msg,
                candidates=[simple_candidate_a, complex_candidate_b],
            )
            if result.recommended_candidate_id == "B":
                correct_count += 1

        accuracy = correct_count / len(complex_messages)
        assert accuracy >= 0.8, f"Accuracy {accuracy} is below 80%"


class TestGenerateRecommendationFunction:
    """Test the standalone generate_recommendation function."""

    def test_generate_recommendation_basic(self) -> None:
        """Test generate_recommendation function."""
        candidates = [
            RequirementCandidate(
                candidate_id="A",
                title="簡易",
                data_source="CSV",
                process_description="集計",
                output_format="Excel",
                schedule="毎日",
                confidence=0.8,
            ),
            RequirementCandidate(
                candidate_id="B",
                title="複雑",
                data_source="API",
                process_description="予測",
                output_format="ダッシュボード",
                schedule="リアルタイム",
                confidence=0.7,
            ),
        ]

        result = generate_recommendation(
            user_message="データを集計してください",
            candidates=candidates,
        )

        assert isinstance(result, AIRecommendation)
        assert result.recommended_candidate_id in ["A", "B"]
