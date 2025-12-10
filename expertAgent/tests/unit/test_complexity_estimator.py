"""Unit tests for complexity estimator - Issue #174.

Tests for the complexity estimation functionality based on keywords.
"""

import pytest

from app.schemas.recommendation import ComplexityLevel
from app.services.recommendation.complexity_estimator import (
    ComplexityEstimator,
    estimate_complexity,
)


class TestComplexityEstimator:
    """Test ComplexityEstimator class."""

    @pytest.fixture
    def estimator(self) -> ComplexityEstimator:
        """Create ComplexityEstimator instance."""
        return ComplexityEstimator()

    def test_simple_complexity_detection(self, estimator: ComplexityEstimator) -> None:
        """Test detection of simple complexity from keywords."""
        keywords = ["集計", "CSV", "出力"]
        result = estimator.estimate(keywords)

        assert result == ComplexityLevel.SIMPLE

    def test_medium_complexity_detection(self, estimator: ComplexityEstimator) -> None:
        """Test detection of medium complexity from keywords."""
        keywords = ["比較", "分析", "グラフ"]
        result = estimator.estimate(keywords)

        assert result == ComplexityLevel.MEDIUM

    def test_complex_complexity_detection(self, estimator: ComplexityEstimator) -> None:
        """Test detection of complex complexity from keywords."""
        keywords = ["予測", "機械学習", "API"]
        result = estimator.estimate(keywords)

        assert result == ComplexityLevel.COMPLEX

    def test_empty_keywords_defaults_to_simple(
        self, estimator: ComplexityEstimator
    ) -> None:
        """Test that empty keywords default to simple complexity."""
        result = estimator.estimate([])
        assert result == ComplexityLevel.SIMPLE

    def test_mixed_keywords_prioritizes_higher_complexity(
        self, estimator: ComplexityEstimator
    ) -> None:
        """Test that mixed keywords result in highest detected complexity."""
        # Contains simple, medium, and complex keywords
        keywords = ["集計", "比較", "API"]
        result = estimator.estimate(keywords)

        # Should return COMPLEX as it's the highest level
        assert result == ComplexityLevel.COMPLEX

    def test_medium_over_simple_priority(self, estimator: ComplexityEstimator) -> None:
        """Test that medium keywords take priority over simple."""
        keywords = ["集計", "CSV", "比較"]
        result = estimator.estimate(keywords)

        assert result == ComplexityLevel.MEDIUM

    def test_unknown_keywords_default_to_simple(
        self, estimator: ComplexityEstimator
    ) -> None:
        """Test that unknown keywords default to simple."""
        result = estimator.estimate(["unknown1", "unknown2"])
        assert result == ComplexityLevel.SIMPLE

    def test_estimate_from_message(self, estimator: ComplexityEstimator) -> None:
        """Test complexity estimation directly from message."""
        message = "売上データを集計してCSVで出力"
        result = estimator.estimate_from_message(message)

        assert result == ComplexityLevel.SIMPLE

    def test_estimate_from_complex_message(
        self, estimator: ComplexityEstimator
    ) -> None:
        """Test complexity estimation from complex message."""
        message = "機械学習を使って予測し、APIで連携"
        result = estimator.estimate_from_message(message)

        assert result == ComplexityLevel.COMPLEX

    def test_get_complexity_score(self, estimator: ComplexityEstimator) -> None:
        """Test getting numeric complexity score."""
        assert estimator.get_complexity_score(ComplexityLevel.SIMPLE) == 1
        assert estimator.get_complexity_score(ComplexityLevel.MEDIUM) == 2
        assert estimator.get_complexity_score(ComplexityLevel.COMPLEX) == 3

    def test_get_keyword_counts(self, estimator: ComplexityEstimator) -> None:
        """Test getting keyword counts by complexity level."""
        keywords = ["集計", "CSV", "比較", "API"]
        counts = estimator.get_keyword_counts(keywords)

        assert counts["simple"] >= 1  # 集計, CSV
        assert counts["medium"] >= 1  # 比較
        assert counts["complex"] >= 1  # API


class TestEstimateComplexityFunction:
    """Test the standalone estimate_complexity function."""

    def test_estimate_complexity_simple(self) -> None:
        """Test estimate_complexity with simple keywords."""
        result = estimate_complexity(["集計", "CSV"])
        assert result == ComplexityLevel.SIMPLE

    def test_estimate_complexity_returns_enum(self) -> None:
        """Test that estimate_complexity returns ComplexityLevel enum."""
        result = estimate_complexity(["集計"])
        assert isinstance(result, ComplexityLevel)

    def test_estimate_complexity_empty_list(self) -> None:
        """Test estimate_complexity with empty list."""
        result = estimate_complexity([])
        assert result == ComplexityLevel.SIMPLE
