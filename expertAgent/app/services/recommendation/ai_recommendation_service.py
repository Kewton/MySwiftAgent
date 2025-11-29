"""AI Recommendation service - Issue #174.

This module provides the main AI recommendation service that integrates
keyword analysis, complexity estimation, and confidence calculation
to generate recommendations for requirement candidates.
"""

from typing import List

from app.schemas.chat import RequirementCandidate
from app.schemas.recommendation import AIRecommendation, ComplexityLevel
from app.services.recommendation.complexity_estimator import ComplexityEstimator
from app.services.recommendation.confidence_calculator import ConfidenceCalculator
from app.services.recommendation.keyword_analyzer import KeywordAnalyzer


class AIRecommendationService:
    """AI Recommendation service for candidate selection.

    This service integrates all recommendation components to:
    - Analyze user messages for keywords
    - Estimate task complexity
    - Calculate recommendation confidence
    - Select the best matching candidate
    - Generate human-readable recommendation reasons
    """

    def __init__(self) -> None:
        """Initialize AIRecommendationService with all components."""
        self._keyword_analyzer = KeywordAnalyzer()
        self._complexity_estimator = ComplexityEstimator()
        self._confidence_calculator = ConfidenceCalculator()

    def recommend(
        self,
        user_message: str,
        candidates: List[RequirementCandidate],
    ) -> AIRecommendation:
        """Generate recommendation for candidate selection.

        Args:
            user_message: User's message to analyze
            candidates: List of requirement candidates to choose from

        Returns:
            AIRecommendation with selected candidate and metadata
        """
        # Step 1: Extract keywords from user message
        keywords = self._keyword_analyzer.extract_keywords(user_message)

        # Step 2: Estimate complexity based on keywords
        complexity = self._complexity_estimator.estimate(keywords)

        # Step 3: Calculate confidence score
        confidence = self._confidence_calculator.calculate(
            keywords=keywords,
            complexity=complexity,
            message_length=len(user_message),
        )

        # Step 4: Select best matching candidate
        selected_candidate = self._select_candidate(
            candidates=candidates,
            complexity=complexity,
            keywords=keywords,
        )

        # Step 5: Generate recommendation reason
        reason = self._generate_reason(
            selected_candidate=selected_candidate,
            complexity=complexity,
            keywords=keywords,
        )

        return AIRecommendation(
            recommended_candidate_id=selected_candidate.candidate_id,
            confidence=confidence,
            complexity=complexity,
            reason=reason,
            keywords_detected=keywords,
        )

    def _select_candidate(
        self,
        candidates: List[RequirementCandidate],
        complexity: ComplexityLevel,
        keywords: List[str],
    ) -> RequirementCandidate:
        """Select the best matching candidate.

        Selection logic:
        - SIMPLE complexity -> prefer candidate A (simpler interpretation)
        - COMPLEX complexity -> prefer candidate B (more advanced)
        - MEDIUM -> analyze candidate descriptions for keyword match

        Args:
            candidates: List of candidates to choose from
            complexity: Estimated complexity level
            keywords: Detected keywords

        Returns:
            Selected RequirementCandidate
        """
        if not candidates:
            raise ValueError("At least one candidate is required")

        # Default to first candidate
        if len(candidates) == 1:
            return candidates[0]

        candidate_a = candidates[0]
        candidate_b = candidates[1] if len(candidates) > 1 else candidates[0]

        # Simple complexity prefers candidate A
        if complexity == ComplexityLevel.SIMPLE:
            return candidate_a

        # Complex complexity prefers candidate B
        if complexity == ComplexityLevel.COMPLEX:
            return candidate_b

        # Medium complexity: analyze candidate descriptions
        score_a = self._score_candidate(candidate_a, keywords)
        score_b = self._score_candidate(candidate_b, keywords)

        return candidate_b if score_b > score_a else candidate_a

    def _score_candidate(
        self,
        candidate: RequirementCandidate,
        keywords: List[str],
    ) -> float:
        """Score a candidate based on keyword matching.

        Args:
            candidate: Candidate to score
            keywords: Keywords to match against

        Returns:
            Matching score
        """
        # Combine candidate text for matching
        candidate_text = " ".join(
            [
                candidate.title,
                candidate.data_source,
                candidate.process_description,
                candidate.output_format,
                candidate.schedule,
            ]
        ).lower()

        score = 0.0
        for keyword in keywords:
            if keyword.lower() in candidate_text:
                score += 1.0

        return score

    def _generate_reason(
        self,
        selected_candidate: RequirementCandidate,
        complexity: ComplexityLevel,
        keywords: List[str],
    ) -> str:
        """Generate human-readable recommendation reason.

        Args:
            selected_candidate: Selected candidate
            complexity: Estimated complexity
            keywords: Detected keywords

        Returns:
            Reason string (max 200 chars)
        """
        complexity_descriptions = {
            ComplexityLevel.SIMPLE: "シンプルな処理",
            ComplexityLevel.MEDIUM: "中程度の複雑さ",
            ComplexityLevel.COMPLEX: "高度な処理",
        }

        complexity_desc = complexity_descriptions.get(complexity, "処理")

        if keywords:
            keyword_sample = ", ".join(keywords[:3])
            reason = (
                f"候補{selected_candidate.candidate_id}を推奨します。"
                f"「{keyword_sample}」などのキーワードから{complexity_desc}と判断しました。"
            )
        else:
            reason = (
                f"候補{selected_candidate.candidate_id}を推奨します。"
                f"メッセージから明確なキーワードが検出されなかったため、"
                f"{complexity_desc}として判断しました。"
            )

        # Truncate to 200 chars if needed
        if len(reason) > 200:
            reason = reason[:197] + "..."

        return reason


def generate_recommendation(
    user_message: str,
    candidates: List[RequirementCandidate],
) -> AIRecommendation:
    """Standalone function to generate recommendation.

    Args:
        user_message: User's message to analyze
        candidates: List of requirement candidates

    Returns:
        AIRecommendation with selected candidate and metadata
    """
    service = AIRecommendationService()
    return service.recommend(user_message, candidates)
