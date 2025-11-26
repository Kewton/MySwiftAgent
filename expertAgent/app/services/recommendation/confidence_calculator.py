"""Confidence calculator for AI recommendation - Issue #174.

This module provides confidence score calculation functionality
based on keywords, complexity, and message characteristics.
"""

from typing import List

from app.schemas.recommendation import ComplexityLevel
from app.services.recommendation.keyword_analyzer import COMPLEXITY_KEYWORDS


class ConfidenceCalculator:
    """Confidence calculator for recommendation scoring.

    Calculates confidence based on:
    - Number of matching keywords
    - Alignment between keywords and detected complexity
    - Message length (moderate length = higher confidence)
    """

    def __init__(self) -> None:
        """Initialize ConfidenceCalculator."""
        self._complexity_keywords = COMPLEXITY_KEYWORDS
        # Build reverse lookup
        self._keyword_to_level: dict[str, str] = {}
        for level, keywords in self._complexity_keywords.items():
            for kw in keywords:
                self._keyword_to_level[kw.lower()] = level

    def calculate(
        self,
        keywords: List[str],
        complexity: ComplexityLevel,
        message_length: int,
    ) -> float:
        """Calculate confidence score.

        Args:
            keywords: List of detected keywords
            complexity: Estimated complexity level
            message_length: Length of user message

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Base confidence starts at 0.3
        base_confidence = 0.3

        # Keyword score: more keywords = higher confidence
        keyword_score = self._calculate_keyword_score(keywords)

        # Alignment score: keywords matching complexity = bonus
        alignment_score = self._calculate_alignment_score(keywords, complexity)

        # Message length score: moderate length = bonus
        length_score = self._calculate_length_score(message_length)

        # Combine scores
        total = base_confidence + keyword_score + alignment_score + length_score

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, total))

    def _calculate_keyword_score(self, keywords: List[str]) -> float:
        """Calculate score based on keyword count.

        Args:
            keywords: List of detected keywords

        Returns:
            Score between 0.0 and 0.3
        """
        if not keywords:
            return 0.0

        # More keywords = higher score, capped at 0.3
        count = len(keywords)
        # Each keyword adds 0.1, max 0.3
        return min(0.3, count * 0.1)

    def _calculate_alignment_score(
        self,
        keywords: List[str],
        complexity: ComplexityLevel,
    ) -> float:
        """Calculate score based on keyword-complexity alignment.

        Args:
            keywords: List of detected keywords
            complexity: Estimated complexity level

        Returns:
            Score between 0.0 and 0.2
        """
        if not keywords:
            return 0.0

        # Count keywords matching the detected complexity
        complexity_name = complexity.value
        matching_count = 0

        for keyword in keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in self._keyword_to_level:
                if self._keyword_to_level[keyword_lower] == complexity_name:
                    matching_count += 1

        # Ratio of matching keywords
        if len(keywords) == 0:
            return 0.0

        ratio = matching_count / len(keywords)
        # Max bonus of 0.2 for perfect alignment
        return ratio * 0.2

    def _calculate_length_score(self, message_length: int) -> float:
        """Calculate score based on message length.

        Args:
            message_length: Length of user message

        Returns:
            Score between 0.0 and 0.2
        """
        # Very short messages have low confidence
        if message_length < 10:
            return 0.0

        # Very long messages (>500) slightly reduce confidence
        if message_length > 500:
            return 0.1

        # Moderate length (20-200) gets bonus
        if 20 <= message_length <= 200:
            return 0.2

        # Other lengths get partial bonus
        return 0.15


def calculate_confidence(
    keywords: List[str],
    complexity: ComplexityLevel,
    message_length: int,
) -> float:
    """Standalone function to calculate confidence.

    Args:
        keywords: List of detected keywords
        complexity: Estimated complexity level
        message_length: Length of user message

    Returns:
        Confidence score between 0.0 and 1.0
    """
    calculator = ConfidenceCalculator()
    return calculator.calculate(keywords, complexity, message_length)
