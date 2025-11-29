"""Integration tests for AI recommendation flow - Issue #174.

End-to-end tests for the complete recommendation workflow.
"""

import time

import pytest

from app.schemas.chat import RequirementCandidate
from app.schemas.recommendation import AIRecommendation, ComplexityLevel
from app.services.recommendation.ai_recommendation_service import (
    AIRecommendationService,
)
from app.services.recommendation.complexity_estimator import ComplexityEstimator
from app.services.recommendation.confidence_calculator import ConfidenceCalculator
from app.services.recommendation.keyword_analyzer import KeywordAnalyzer


class TestRecommendationFlowIntegration:
    """Integration tests for the complete recommendation flow."""

    @pytest.fixture
    def keyword_analyzer(self) -> KeywordAnalyzer:
        """Create KeywordAnalyzer instance."""
        return KeywordAnalyzer()

    @pytest.fixture
    def complexity_estimator(self) -> ComplexityEstimator:
        """Create ComplexityEstimator instance."""
        return ComplexityEstimator()

    @pytest.fixture
    def confidence_calculator(self) -> ConfidenceCalculator:
        """Create ConfidenceCalculator instance."""
        return ConfidenceCalculator()

    @pytest.fixture
    def recommendation_service(self) -> AIRecommendationService:
        """Create AIRecommendationService instance."""
        return AIRecommendationService()

    @pytest.fixture
    def sample_candidates(self) -> list[RequirementCandidate]:
        """Create sample candidates for testing."""
        return [
            RequirementCandidate(
                candidate_id="A",
                title="簡易レポート",
                data_source="CSVファイル",
                process_description="データの集計と出力",
                output_format="Excelレポート",
                schedule="オンデマンド",
                confidence=0.85,
            ),
            RequirementCandidate(
                candidate_id="B",
                title="高度な分析",
                data_source="API連携",
                process_description="機械学習による予測と自動通知",
                output_format="リアルタイムダッシュボード",
                schedule="自動実行",
                confidence=0.75,
            ),
        ]

    def test_full_flow_simple_message(
        self,
        keyword_analyzer: KeywordAnalyzer,
        complexity_estimator: ComplexityEstimator,
        confidence_calculator: ConfidenceCalculator,
        recommendation_service: AIRecommendationService,
        sample_candidates: list[RequirementCandidate],
    ) -> None:
        """Test complete flow with simple message."""
        message = "売上データを集計してCSVで出力してください"

        # Step 1: Extract keywords
        keywords = keyword_analyzer.extract_keywords(message)
        assert len(keywords) > 0
        assert "集計" in keywords
        assert "CSV" in keywords

        # Step 2: Estimate complexity
        complexity = complexity_estimator.estimate(keywords)
        assert complexity == ComplexityLevel.SIMPLE

        # Step 3: Calculate confidence
        confidence = confidence_calculator.calculate(
            keywords=keywords,
            complexity=complexity,
            message_length=len(message),
        )
        assert 0.0 <= confidence <= 1.0

        # Step 4: Generate recommendation
        recommendation = recommendation_service.recommend(
            user_message=message,
            candidates=sample_candidates,
        )
        assert recommendation.recommended_candidate_id == "A"
        assert recommendation.complexity == ComplexityLevel.SIMPLE

    def test_full_flow_complex_message(
        self,
        keyword_analyzer: KeywordAnalyzer,
        complexity_estimator: ComplexityEstimator,
        confidence_calculator: ConfidenceCalculator,
        recommendation_service: AIRecommendationService,
        sample_candidates: list[RequirementCandidate],
    ) -> None:
        """Test complete flow with complex message."""
        message = "機械学習を使って売上を予測し、APIで自動連携してリアルタイム通知"

        # Step 1: Extract keywords
        keywords = keyword_analyzer.extract_keywords(message)
        assert "機械学習" in keywords
        assert "予測" in keywords
        assert "API" in keywords

        # Step 2: Estimate complexity
        complexity = complexity_estimator.estimate(keywords)
        assert complexity == ComplexityLevel.COMPLEX

        # Step 3: Calculate confidence
        confidence = confidence_calculator.calculate(
            keywords=keywords,
            complexity=complexity,
            message_length=len(message),
        )
        assert confidence > 0.5  # High confidence for matching keywords

        # Step 4: Generate recommendation
        recommendation = recommendation_service.recommend(
            user_message=message,
            candidates=sample_candidates,
        )
        assert recommendation.recommended_candidate_id == "B"
        assert recommendation.complexity == ComplexityLevel.COMPLEX

    def test_full_flow_medium_message(
        self,
        recommendation_service: AIRecommendationService,
        sample_candidates: list[RequirementCandidate],
    ) -> None:
        """Test complete flow with medium complexity message."""
        message = "複数のデータソースを比較して分析し、グラフで表示"

        recommendation = recommendation_service.recommend(
            user_message=message,
            candidates=sample_candidates,
        )

        assert isinstance(recommendation, AIRecommendation)
        assert recommendation.complexity == ComplexityLevel.MEDIUM

    def test_full_flow_empty_message(
        self,
        recommendation_service: AIRecommendationService,
        sample_candidates: list[RequirementCandidate],
    ) -> None:
        """Test complete flow with empty message."""
        message = ""

        recommendation = recommendation_service.recommend(
            user_message=message,
            candidates=sample_candidates,
        )

        assert isinstance(recommendation, AIRecommendation)
        assert recommendation.complexity == ComplexityLevel.SIMPLE
        assert recommendation.confidence < 0.5

    def test_full_flow_long_message(
        self,
        recommendation_service: AIRecommendationService,
        sample_candidates: list[RequirementCandidate],
    ) -> None:
        """Test complete flow with long message (1000+ chars)."""
        base = "売上データを集計して分析し、"
        message = base * 50  # ~1000 chars

        start_time = time.time()
        recommendation = recommendation_service.recommend(
            user_message=message,
            candidates=sample_candidates,
        )
        elapsed_time = (time.time() - start_time) * 1000

        assert isinstance(recommendation, AIRecommendation)
        assert elapsed_time < 100, f"Processing took {elapsed_time}ms"

    def test_recommendation_consistency(
        self,
        recommendation_service: AIRecommendationService,
        sample_candidates: list[RequirementCandidate],
    ) -> None:
        """Test that same input produces consistent recommendations."""
        message = "売上データを集計してCSVで出力"

        results = [
            recommendation_service.recommend(
                user_message=message,
                candidates=sample_candidates,
            )
            for _ in range(5)
        ]

        # All recommendations should be the same
        first_candidate = results[0].recommended_candidate_id
        for result in results:
            assert result.recommended_candidate_id == first_candidate

    def test_keywords_flow_to_recommendation(
        self,
        keyword_analyzer: KeywordAnalyzer,
        recommendation_service: AIRecommendationService,
        sample_candidates: list[RequirementCandidate],
    ) -> None:
        """Test that extracted keywords appear in recommendation."""
        message = "データを集計してCSVで出力"

        # Extract keywords directly
        direct_keywords = keyword_analyzer.extract_keywords(message)

        # Get recommendation
        recommendation = recommendation_service.recommend(
            user_message=message,
            candidates=sample_candidates,
        )

        # Keywords in recommendation should match direct extraction
        for kw in recommendation.keywords_detected:
            assert kw in direct_keywords

    def test_performance_batch_processing(
        self,
        recommendation_service: AIRecommendationService,
        sample_candidates: list[RequirementCandidate],
    ) -> None:
        """Test performance with batch of messages."""
        messages = [
            "データを集計してください",
            "売上を予測してください",
            "レポートを作成してください",
            "グラフで分析してください",
            "API連携してください",
        ] * 10  # 50 messages

        start_time = time.time()
        for message in messages:
            recommendation_service.recommend(
                user_message=message,
                candidates=sample_candidates,
            )
        elapsed_time = (time.time() - start_time) * 1000

        # Average should be well under 100ms per message
        avg_time = elapsed_time / len(messages)
        assert avg_time < 100, f"Average time {avg_time}ms exceeds limit"

    def test_recommendation_reason_quality(
        self,
        recommendation_service: AIRecommendationService,
        sample_candidates: list[RequirementCandidate],
    ) -> None:
        """Test that recommendation reasons are meaningful."""
        message = "売上データを集計してCSVで出力"

        recommendation = recommendation_service.recommend(
            user_message=message,
            candidates=sample_candidates,
        )

        reason = recommendation.reason
        assert len(reason) >= 10  # Minimum meaningful length
        assert len(reason) <= 200  # Max length
        # Reason should mention something relevant
        assert any(
            term in reason
            for term in ["簡易", "シンプル", "simple", "集計", "CSV", "候補A"]
        )

    def test_edge_case_unicode_message(
        self,
        recommendation_service: AIRecommendationService,
        sample_candidates: list[RequirementCandidate],
    ) -> None:
        """Test handling of Unicode characters."""
        message = "売上データを集計してください。"

        recommendation = recommendation_service.recommend(
            user_message=message,
            candidates=sample_candidates,
        )

        assert isinstance(recommendation, AIRecommendation)
        assert recommendation.keywords_detected is not None

    def test_edge_case_mixed_language(
        self,
        recommendation_service: AIRecommendationService,
        sample_candidates: list[RequirementCandidate],
    ) -> None:
        """Test handling of mixed Japanese/English message."""
        message = "CSVファイルをExcelレポートに変換してAPIで連携"

        recommendation = recommendation_service.recommend(
            user_message=message,
            candidates=sample_candidates,
        )

        assert isinstance(recommendation, AIRecommendation)
        assert "CSV" in recommendation.keywords_detected
        assert "Excel" in recommendation.keywords_detected
        assert "API" in recommendation.keywords_detected
