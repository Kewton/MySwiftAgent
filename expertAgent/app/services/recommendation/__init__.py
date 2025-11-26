"""AI Recommendation service package - Issue #174.

This package provides AI-based recommendation functionality for
requirement interpretation candidates.

Modules:
- keyword_mapping: Shared keyword-to-level mapping utilities (DRY)
- keyword_analyzer: Extract and classify keywords from user messages
- complexity_estimator: Estimate task complexity based on keywords
- confidence_calculator: Calculate recommendation confidence scores
- ai_recommendation_service: Main service integrating all components
"""

from app.services.recommendation.ai_recommendation_service import (
    AIRecommendationService,
    generate_recommendation,
)
from app.services.recommendation.complexity_estimator import (
    ComplexityEstimator,
    estimate_complexity,
)
from app.services.recommendation.confidence_calculator import (
    ConfidenceCalculator,
    calculate_confidence,
)
from app.services.recommendation.keyword_analyzer import (
    KeywordAnalyzer,
    extract_keywords,
)
from app.services.recommendation.keyword_mapping import (
    COMPLEXITY_KEYWORDS,
    build_keyword_to_level_mapping,
    get_default_keyword_mapping,
    get_keyword_level,
)

__all__ = [
    "AIRecommendationService",
    "generate_recommendation",
    "ComplexityEstimator",
    "estimate_complexity",
    "ConfidenceCalculator",
    "calculate_confidence",
    "KeywordAnalyzer",
    "extract_keywords",
    "COMPLEXITY_KEYWORDS",
    "build_keyword_to_level_mapping",
    "get_default_keyword_mapping",
    "get_keyword_level",
]
