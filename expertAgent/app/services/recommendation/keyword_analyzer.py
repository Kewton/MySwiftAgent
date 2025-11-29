"""Keyword analyzer for AI recommendation - Issue #174.

This module provides keyword extraction and classification functionality
for analyzing user messages and determining task complexity.
"""

from typing import Dict, List

from app.services.recommendation.keyword_mapping import (
    COMPLEXITY_KEYWORDS,
    get_default_keyword_mapping,
)

# Re-export for backwards compatibility
__all__ = ["KeywordAnalyzer", "extract_keywords", "COMPLEXITY_KEYWORDS"]


class KeywordAnalyzer:
    """Keyword analyzer for extracting and classifying keywords from messages.

    This class provides methods to:
    - Extract relevant keywords from user messages
    - Classify keywords by complexity level
    - Support both Japanese and English keyword matching
    """

    def __init__(self) -> None:
        """Initialize KeywordAnalyzer with complexity keywords."""
        self._keywords = COMPLEXITY_KEYWORDS
        # Use shared mapping utility (DRY principle)
        self._keyword_to_level: Dict[str, str] = get_default_keyword_mapping()

    def extract_keywords(self, message: str) -> List[str]:
        """Extract recognized keywords from a message.

        Args:
            message: User message to analyze

        Returns:
            List of unique keywords found in the message
        """
        if not message:
            return []

        found_keywords: List[str] = []
        message_lower = message.lower()

        # Check each keyword against the message
        for level_keywords in self._keywords.values():
            for keyword in level_keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in message_lower and keyword not in found_keywords:
                    found_keywords.append(keyword)

        return found_keywords

    def get_keywords_by_complexity(self, message: str) -> Dict[str, List[str]]:
        """Extract keywords grouped by complexity level.

        Args:
            message: User message to analyze

        Returns:
            Dictionary mapping complexity level to list of found keywords
        """
        result: Dict[str, List[str]] = {
            "simple": [],
            "medium": [],
            "complex": [],
        }

        if not message:
            return result

        found_keywords = self.extract_keywords(message)

        for keyword in found_keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in self._keyword_to_level:
                level = self._keyword_to_level[keyword_lower]
                if keyword not in result[level]:
                    result[level].append(keyword)

        return result


def extract_keywords(message: str) -> List[str]:
    """Standalone function to extract keywords from a message.

    Args:
        message: User message to analyze

    Returns:
        List of unique keywords found in the message
    """
    analyzer = KeywordAnalyzer()
    return analyzer.extract_keywords(message)
