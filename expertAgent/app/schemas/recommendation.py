"""AI Recommendation schemas for Issue #174.

This module defines the data models for the AI recommendation system:
- ComplexityLevel: Enum for task complexity classification
- AIRecommendation: Result model containing recommendation details
"""

from enum import Enum
from typing import List, Literal

from pydantic import BaseModel, Field


class ComplexityLevel(str, Enum):
    """Task complexity level classification.

    Levels:
    - SIMPLE: Single data source, simple processing (e.g., CSV export, basic aggregation)
    - MEDIUM: Multiple data sources or conditional logic (e.g., comparison, filtering)
    - COMPLEX: External API integration, ML, real-time processing
    """

    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"


class AIRecommendation(BaseModel):
    """AI recommendation result model.

    Contains the recommended candidate, confidence score, complexity assessment,
    human-readable reason, and detected keywords from the analysis.
    """

    recommended_candidate_id: Literal["A", "B"] = Field(
        ...,
        description="Recommended candidate ID",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0-1.0)",
    )
    complexity: ComplexityLevel = Field(
        ...,
        description="Estimated task complexity",
    )
    reason: str = Field(
        ...,
        description="Human-readable recommendation reason",
        max_length=200,
    )
    keywords_detected: List[str] = Field(
        default_factory=list,
        description="Keywords detected from user message",
    )
