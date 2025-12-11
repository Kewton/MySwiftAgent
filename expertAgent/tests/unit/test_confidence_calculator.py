"""Unit tests for confidence calculator - Issue #174.

Tests for the confidence score calculation functionality.
"""

import pytest

from app.schemas.recommendation import ComplexityLevel
from app.services.recommendation.confidence_calculator import (
    ConfidenceCalculator,
    calculate_confidence,
)


class TestConfidenceCalculator:
    """Test ConfidenceCalculator class."""

    @pytest.fixture
    def calculator(self) -> ConfidenceCalculator:
        """Create ConfidenceCalculator instance."""
        return ConfidenceCalculator()

    def test_calculate_returns_float(self, calculator: ConfidenceCalculator) -> None:
        """Test that calculate returns a float."""
        result = calculator.calculate(
            keywords=["集計"],
            complexity=ComplexityLevel.SIMPLE,
            message_length=50,
        )
        assert isinstance(result, float)

    def test_confidence_in_valid_range(self, calculator: ConfidenceCalculator) -> None:
        """Test that confidence is always between 0.0 and 1.0."""
        result = calculator.calculate(
            keywords=["集計", "CSV"],
            complexity=ComplexityLevel.SIMPLE,
            message_length=100,
        )
        assert 0.0 <= result <= 1.0

    def test_more_keywords_higher_confidence(
        self, calculator: ConfidenceCalculator
    ) -> None:
        """Test that more keywords lead to higher confidence."""
        result_few = calculator.calculate(
            keywords=["集計"],
            complexity=ComplexityLevel.SIMPLE,
            message_length=50,
        )
        result_many = calculator.calculate(
            keywords=["集計", "CSV", "出力", "レポート"],
            complexity=ComplexityLevel.SIMPLE,
            message_length=50,
        )
        assert result_many >= result_few

    def test_empty_keywords_low_confidence(
        self, calculator: ConfidenceCalculator
    ) -> None:
        """Test that empty keywords result in low confidence."""
        result = calculator.calculate(
            keywords=[],
            complexity=ComplexityLevel.SIMPLE,
            message_length=50,
        )
        assert result <= 0.5  # At most 0.5 for empty keywords

    def test_complexity_affects_confidence(
        self, calculator: ConfidenceCalculator
    ) -> None:
        """Test that complexity affects confidence calculation."""
        keywords = ["予測", "API"]

        result_simple = calculator.calculate(
            keywords=keywords,
            complexity=ComplexityLevel.SIMPLE,
            message_length=50,
        )
        result_complex = calculator.calculate(
            keywords=keywords,
            complexity=ComplexityLevel.COMPLEX,
            message_length=50,
        )

        # Complex tasks with complex keywords should have higher confidence
        assert result_complex >= result_simple

    def test_very_long_message_confidence(
        self, calculator: ConfidenceCalculator
    ) -> None:
        """Test confidence calculation with very long message."""
        result = calculator.calculate(
            keywords=["集計", "分析"],
            complexity=ComplexityLevel.MEDIUM,
            message_length=1000,  # 1000 chars
        )
        assert 0.0 <= result <= 1.0

    def test_empty_message_confidence(self, calculator: ConfidenceCalculator) -> None:
        """Test confidence calculation with empty message."""
        result = calculator.calculate(
            keywords=[],
            complexity=ComplexityLevel.SIMPLE,
            message_length=0,
        )
        assert 0.0 <= result <= 1.0
        assert result <= 0.3  # Very low confidence for empty input

    def test_optimal_message_length_bonus(
        self, calculator: ConfidenceCalculator
    ) -> None:
        """Test that moderate message length provides optimal confidence."""
        keywords = ["集計", "CSV"]
        complexity = ComplexityLevel.SIMPLE

        # Very short message
        result_short = calculator.calculate(
            keywords=keywords,
            complexity=complexity,
            message_length=10,
        )

        # Moderate message length (optimal)
        result_moderate = calculator.calculate(
            keywords=keywords,
            complexity=complexity,
            message_length=100,
        )

        # Very long message - verify it doesn't raise error
        calculator.calculate(
            keywords=keywords,
            complexity=complexity,
            message_length=1000,
        )

        # Moderate length should have reasonable confidence
        assert result_moderate > result_short

    def test_keyword_complexity_alignment_bonus(
        self, calculator: ConfidenceCalculator
    ) -> None:
        """Test bonus for aligned keyword complexity."""
        # Simple keywords with simple complexity
        result_aligned = calculator.calculate(
            keywords=["集計", "CSV", "レポート"],
            complexity=ComplexityLevel.SIMPLE,
            message_length=50,
        )

        # Simple keywords with complex complexity (misaligned)
        result_misaligned = calculator.calculate(
            keywords=["集計", "CSV", "レポート"],
            complexity=ComplexityLevel.COMPLEX,
            message_length=50,
        )

        # Aligned should have higher confidence
        assert result_aligned >= result_misaligned


class TestCalculateConfidenceFunction:
    """Test the standalone calculate_confidence function."""

    def test_calculate_confidence_basic(self) -> None:
        """Test calculate_confidence function."""
        result = calculate_confidence(
            keywords=["集計"],
            complexity=ComplexityLevel.SIMPLE,
            message_length=50,
        )
        assert isinstance(result, float)
        assert 0.0 <= result <= 1.0

    def test_calculate_confidence_returns_bounded_value(self) -> None:
        """Test that calculate_confidence returns bounded value."""
        # Test with extreme values
        result = calculate_confidence(
            keywords=["a"] * 100,  # Many keywords
            complexity=ComplexityLevel.COMPLEX,
            message_length=10000,
        )
        assert result <= 1.0

        result_empty = calculate_confidence(
            keywords=[],
            complexity=ComplexityLevel.SIMPLE,
            message_length=0,
        )
        assert result_empty >= 0.0
