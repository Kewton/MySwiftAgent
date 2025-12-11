"""Unit tests for keyword analyzer - Issue #174.

Tests for the keyword extraction and classification functionality.
"""

import pytest

from app.services.recommendation.keyword_analyzer import (
    COMPLEXITY_KEYWORDS,
    KeywordAnalyzer,
    extract_keywords,
)


class TestKeywordAnalyzer:
    """Test KeywordAnalyzer class."""

    @pytest.fixture
    def analyzer(self) -> KeywordAnalyzer:
        """Create KeywordAnalyzer instance."""
        return KeywordAnalyzer()

    def test_extract_simple_keywords(self, analyzer: KeywordAnalyzer) -> None:
        """Test extraction of simple complexity keywords."""
        message = "売上データを集計してCSVで出力してください"
        result = analyzer.extract_keywords(message)

        assert "集計" in result
        assert "CSV" in result
        assert "出力" in result

    def test_extract_medium_keywords(self, analyzer: KeywordAnalyzer) -> None:
        """Test extraction of medium complexity keywords."""
        message = "複数の部門のデータを比較してグラフにしてください"
        result = analyzer.extract_keywords(message)

        assert "複数" in result
        assert "比較" in result
        assert "グラフ" in result

    def test_extract_complex_keywords(self, analyzer: KeywordAnalyzer) -> None:
        """Test extraction of complex keywords."""
        message = "機械学習を使って売上を予測し、APIで連携してください"
        result = analyzer.extract_keywords(message)

        assert "機械学習" in result
        assert "予測" in result
        assert "API" in result
        assert "連携" in result

    def test_empty_message_returns_empty_list(self, analyzer: KeywordAnalyzer) -> None:
        """Test that empty message returns empty keyword list."""
        result = analyzer.extract_keywords("")
        assert result == []

    def test_no_keywords_found(self, analyzer: KeywordAnalyzer) -> None:
        """Test message with no recognized keywords."""
        message = "こんにちは、お元気ですか"
        result = analyzer.extract_keywords(message)
        assert result == []

    def test_case_insensitive_matching(self, analyzer: KeywordAnalyzer) -> None:
        """Test that matching is case insensitive for English keywords."""
        message = "api連携とcsv出力をお願いします"
        result = analyzer.extract_keywords(message)

        # Should match regardless of case
        assert any(kw.upper() == "API" for kw in result)
        assert any(kw.upper() == "CSV" for kw in result)

    def test_long_message_performance(self, analyzer: KeywordAnalyzer) -> None:
        """Test keyword extraction with long message (1000+ chars)."""
        # Create a long message with various keywords
        base_message = "売上データを集計して比較分析し、"
        long_message = base_message * 50  # ~1000 chars

        result = analyzer.extract_keywords(long_message)

        # Should still work and find keywords
        assert "集計" in result
        assert "比較" in result
        assert "分析" in result

    def test_duplicate_keywords_removed(self, analyzer: KeywordAnalyzer) -> None:
        """Test that duplicate keywords are removed."""
        message = "集計して集計して集計してください"
        result = analyzer.extract_keywords(message)

        # Should only contain one instance of each keyword
        assert result.count("集計") == 1

    def test_get_keywords_by_complexity(self, analyzer: KeywordAnalyzer) -> None:
        """Test getting keywords grouped by complexity."""
        message = "売上を集計してAPIで連携してください"
        result = analyzer.get_keywords_by_complexity(message)

        assert "simple" in result
        assert "集計" in result["simple"]
        assert "complex" in result
        assert "API" in result["complex"]
        assert "連携" in result["complex"]


class TestExtractKeywordsFunction:
    """Test the standalone extract_keywords function."""

    def test_extract_keywords_simple_case(self) -> None:
        """Test extract_keywords function with simple message."""
        result = extract_keywords("データを集計してください")
        assert "集計" in result

    def test_extract_keywords_returns_list(self) -> None:
        """Test that extract_keywords always returns a list."""
        result = extract_keywords("テストメッセージ")
        assert isinstance(result, list)


class TestComplexityKeywords:
    """Test the COMPLEXITY_KEYWORDS dictionary."""

    def test_all_complexity_levels_present(self) -> None:
        """Test that all complexity levels are defined."""
        assert "simple" in COMPLEXITY_KEYWORDS
        assert "medium" in COMPLEXITY_KEYWORDS
        assert "complex" in COMPLEXITY_KEYWORDS

    def test_keywords_are_non_empty(self) -> None:
        """Test that each complexity level has keywords."""
        for level, keywords in COMPLEXITY_KEYWORDS.items():
            assert len(keywords) > 0, f"{level} should have keywords"

    def test_expected_simple_keywords(self) -> None:
        """Test expected simple keywords are present."""
        simple = COMPLEXITY_KEYWORDS["simple"]
        expected = ["集計", "合計", "平均", "一覧", "CSV", "Excel"]
        for kw in expected:
            assert kw in simple, f"{kw} should be in simple keywords"

    def test_expected_medium_keywords(self) -> None:
        """Test expected medium keywords are present."""
        medium = COMPLEXITY_KEYWORDS["medium"]
        expected = ["比較", "分析", "グラフ", "複数", "条件", "フィルタ"]
        for kw in expected:
            assert kw in medium, f"{kw} should be in medium keywords"

    def test_expected_complex_keywords(self) -> None:
        """Test expected complex keywords are present."""
        complex_kw = COMPLEXITY_KEYWORDS["complex"]
        expected = ["予測", "機械学習", "AI", "自動化", "連携", "API"]
        for kw in expected:
            assert kw in complex_kw, f"{kw} should be in complex keywords"
