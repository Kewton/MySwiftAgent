"""Keyword mapping utilities for AI recommendation - Issue #174.

This module provides shared keyword-to-level mapping functionality
used by multiple recommendation components (DRY principle).
"""

from typing import Dict, List

# Complexity keywords dictionary mapping complexity level to keywords
COMPLEXITY_KEYWORDS: Dict[str, List[str]] = {
    "simple": [
        "集計",
        "合計",
        "平均",
        "一覧",
        "表示",
        "出力",
        "CSV",
        "Excel",
        "レポート",
    ],
    "medium": [
        "比較",
        "分析",
        "グラフ",
        "複数",
        "条件",
        "フィルタ",
        "並べ替え",
        "グループ",
    ],
    "complex": [
        "予測",
        "機械学習",
        "AI",
        "自動化",
        "連携",
        "API",
        "リアルタイム",
        "通知",
        "自動",
    ],
}


def build_keyword_to_level_mapping(
    keywords_dict: Dict[str, List[str]] | None = None,
) -> Dict[str, str]:
    """Build a reverse lookup mapping from keyword to complexity level.

    This function centralizes the keyword-to-level mapping logic
    to avoid code duplication across multiple classes (DRY principle).

    Args:
        keywords_dict: Optional custom keywords dictionary.
                       Defaults to COMPLEXITY_KEYWORDS.

    Returns:
        Dictionary mapping lowercase keyword to complexity level name.
    """
    if keywords_dict is None:
        keywords_dict = COMPLEXITY_KEYWORDS

    mapping: Dict[str, str] = {}
    for level, keywords in keywords_dict.items():
        for kw in keywords:
            mapping[kw.lower()] = level

    return mapping


# Pre-built default mapping for performance
_DEFAULT_KEYWORD_TO_LEVEL: Dict[str, str] = build_keyword_to_level_mapping()


def get_keyword_level(keyword: str) -> str | None:
    """Get the complexity level for a keyword.

    Args:
        keyword: The keyword to look up (case-insensitive)

    Returns:
        Complexity level name ('simple', 'medium', 'complex') or None if not found
    """
    return _DEFAULT_KEYWORD_TO_LEVEL.get(keyword.lower())


def get_default_keyword_mapping() -> Dict[str, str]:
    """Get the default keyword-to-level mapping.

    Returns:
        Copy of the default mapping dictionary
    """
    return _DEFAULT_KEYWORD_TO_LEVEL.copy()
