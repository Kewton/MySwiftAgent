"""Unit tests for keyword mapping utilities - Issue #174.

Tests for the shared keyword-to-level mapping functionality.
"""

import pytest

from app.services.recommendation.keyword_mapping import (
    COMPLEXITY_KEYWORDS,
    build_keyword_to_level_mapping,
    get_default_keyword_mapping,
    get_keyword_level,
)


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


class TestBuildKeywordToLevelMapping:
    """Test the build_keyword_to_level_mapping function."""

    def test_build_returns_dict(self) -> None:
        """Test that build_keyword_to_level_mapping returns a dictionary."""
        result = build_keyword_to_level_mapping()
        assert isinstance(result, dict)

    def test_build_with_default_keywords(self) -> None:
        """Test building mapping with default COMPLEXITY_KEYWORDS."""
        result = build_keyword_to_level_mapping()

        # Simple keywords
        assert result.get("集計") == "simple"
        assert result.get("csv") == "simple"

        # Medium keywords
        assert result.get("比較") == "medium"
        assert result.get("分析") == "medium"

        # Complex keywords
        assert result.get("予測") == "complex"
        assert result.get("api") == "complex"

    def test_build_with_custom_keywords(self) -> None:
        """Test building mapping with custom keywords dictionary."""
        custom_keywords = {
            "low": ["easy", "basic"],
            "high": ["advanced", "expert"],
        }

        result = build_keyword_to_level_mapping(custom_keywords)

        assert result.get("easy") == "low"
        assert result.get("basic") == "low"
        assert result.get("advanced") == "high"
        assert result.get("expert") == "high"

    def test_build_is_case_insensitive(self) -> None:
        """Test that mapping keys are lowercase."""
        result = build_keyword_to_level_mapping()

        # All keys should be lowercase
        for key in result.keys():
            assert key == key.lower()


class TestGetDefaultKeywordMapping:
    """Test the get_default_keyword_mapping function."""

    def test_returns_dict(self) -> None:
        """Test that get_default_keyword_mapping returns a dictionary."""
        result = get_default_keyword_mapping()
        assert isinstance(result, dict)

    def test_returns_copy(self) -> None:
        """Test that get_default_keyword_mapping returns a copy."""
        result1 = get_default_keyword_mapping()
        result2 = get_default_keyword_mapping()

        # Should be equal but not the same object
        assert result1 == result2
        assert result1 is not result2

    def test_modification_does_not_affect_original(self) -> None:
        """Test that modifying returned dict doesn't affect the original."""
        result = get_default_keyword_mapping()
        original_length = len(result)

        # Modify the returned dict
        result["new_keyword"] = "new_level"

        # Get a new copy and verify original is unchanged
        new_result = get_default_keyword_mapping()
        assert len(new_result) == original_length
        assert "new_keyword" not in new_result


class TestGetKeywordLevel:
    """Test the get_keyword_level function."""

    def test_returns_level_for_known_keyword(self) -> None:
        """Test that known keywords return correct level."""
        assert get_keyword_level("集計") == "simple"
        assert get_keyword_level("比較") == "medium"
        assert get_keyword_level("予測") == "complex"

    def test_case_insensitive(self) -> None:
        """Test that lookup is case insensitive."""
        assert get_keyword_level("CSV") == "simple"
        assert get_keyword_level("csv") == "simple"
        assert get_keyword_level("Csv") == "simple"
        assert get_keyword_level("API") == "complex"
        assert get_keyword_level("api") == "complex"

    def test_returns_none_for_unknown_keyword(self) -> None:
        """Test that unknown keywords return None."""
        assert get_keyword_level("unknown") is None
        assert get_keyword_level("random") is None
        assert get_keyword_level("") is None
