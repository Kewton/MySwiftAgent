"""Complexity estimator for AI recommendation - Issue #174.

This module provides complexity estimation functionality based on
detected keywords from user messages.
"""

from typing import Dict, List

from app.schemas.recommendation import ComplexityLevel
from app.services.recommendation.keyword_analyzer import (
    COMPLEXITY_KEYWORDS,
    KeywordAnalyzer,
)


class ComplexityEstimator:
    """Complexity estimator based on keyword analysis.

    This class estimates task complexity based on:
    - Keywords detected in user message
    - Priority: complex > medium > simple
    - Default to SIMPLE when no keywords detected
    """

    def __init__(self) -> None:
        """Initialize ComplexityEstimator."""
        self._keyword_analyzer = KeywordAnalyzer()
        self._complexity_keywords = COMPLEXITY_KEYWORDS
        # Build reverse lookup: keyword -> complexity level
        self._keyword_to_level: Dict[str, str] = {}
        for level, keywords in self._complexity_keywords.items():
            for kw in keywords:
                self._keyword_to_level[kw.lower()] = level

    def estimate(self, keywords: List[str]) -> ComplexityLevel:
        """Estimate complexity based on keywords.

        Uses priority: COMPLEX > MEDIUM > SIMPLE
        Returns SIMPLE as default when no keywords match.

        Args:
            keywords: List of detected keywords

        Returns:
            Estimated ComplexityLevel
        """
        if not keywords:
            return ComplexityLevel.SIMPLE

        # Count keywords by level
        counts = self.get_keyword_counts(keywords)

        # Priority: complex > medium > simple
        if counts["complex"] > 0:
            return ComplexityLevel.COMPLEX
        if counts["medium"] > 0:
            return ComplexityLevel.MEDIUM

        return ComplexityLevel.SIMPLE

    def estimate_from_message(self, message: str) -> ComplexityLevel:
        """Estimate complexity directly from a message.

        Args:
            message: User message to analyze

        Returns:
            Estimated ComplexityLevel
        """
        keywords = self._keyword_analyzer.extract_keywords(message)
        return self.estimate(keywords)

    def get_keyword_counts(self, keywords: List[str]) -> Dict[str, int]:
        """Count keywords by complexity level.

        Args:
            keywords: List of keywords to count

        Returns:
            Dictionary mapping level name to count
        """
        counts: Dict[str, int] = {
            "simple": 0,
            "medium": 0,
            "complex": 0,
        }

        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in self._keyword_to_level:
                level = self._keyword_to_level[keyword_lower]
                counts[level] += 1

        return counts

    def get_complexity_score(self, complexity: ComplexityLevel) -> int:
        """Get numeric score for complexity level.

        Args:
            complexity: ComplexityLevel enum value

        Returns:
            Numeric score (1=simple, 2=medium, 3=complex)
        """
        scores = {
            ComplexityLevel.SIMPLE: 1,
            ComplexityLevel.MEDIUM: 2,
            ComplexityLevel.COMPLEX: 3,
        }
        return scores.get(complexity, 1)


def estimate_complexity(keywords: List[str]) -> ComplexityLevel:
    """Standalone function to estimate complexity from keywords.

    Args:
        keywords: List of detected keywords

    Returns:
        Estimated ComplexityLevel
    """
    estimator = ComplexityEstimator()
    return estimator.estimate(keywords)
