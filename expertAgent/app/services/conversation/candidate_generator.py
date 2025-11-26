"""Candidate generator service for multi-candidate suggestion feature.

This module provides functionality to generate multiple requirement
interpretation candidates from user's initial message using LLM.

Design decisions:
- Uses structured output for reliable JSON parsing
- Generates exactly 2 candidates (A and B)
- Candidates differ in interpretation depth and approach
- Confidence scores reflect interpretation certainty
"""

import logging
import os
from typing import List

from aiagent.langgraph.jobTaskGeneratorAgents.prompts.multi_candidate import (
    MULTI_CANDIDATE_SYSTEM_PROMPT,
    create_multi_candidate_prompt,
)
from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
    StructuredLLMError,
    invoke_structured_llm,
)
from app.schemas.chat import (
    CandidateSelectionEvent,
    RequirementCandidate,
)

logger = logging.getLogger(__name__)


async def generate_requirement_candidates(
    user_message: str,
) -> List[RequirementCandidate]:
    """Generate multiple requirement interpretation candidates.

    Analyzes user's initial message and generates two distinct
    interpretations as candidates A and B.

    Args:
        user_message: User's initial message

    Returns:
        List of RequirementCandidate objects (typically 2)

    Raises:
        Exception: If LLM invocation fails

    Example:
        >>> candidates = await generate_requirement_candidates("売上データを分析したい")
        >>> print(len(candidates))
        2
        >>> print(candidates[0].candidate_id)
        'A'
    """
    logger.info(f"Generating candidates for user message: {user_message[:50]}...")

    # Generate candidates using LLM
    candidates = await _invoke_llm_for_candidates(user_message)

    logger.info(
        f"Generated {len(candidates)} candidates: "
        f"[{', '.join(c.candidate_id for c in candidates)}]"
    )

    return candidates


async def _invoke_llm_for_candidates(
    user_message: str,
) -> List[RequirementCandidate]:
    """Invoke LLM to generate requirement candidates.

    Uses structured output to ensure reliable JSON parsing
    and candidate validation.

    Args:
        user_message: User's initial message

    Returns:
        List of RequirementCandidate objects

    Raises:
        StructuredLLMError: If LLM invocation fails
    """
    # Create user prompt
    user_prompt = create_multi_candidate_prompt(user_message)

    # Prepare messages
    messages = [
        {"role": "system", "content": MULTI_CANDIDATE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        # Get model from environment
        model_name = os.getenv("CANDIDATE_GENERATION_MODEL", "gemini-2.0-flash")

        # Invoke LLM with structured output
        result = await invoke_structured_llm(
            messages=messages,
            response_model=CandidateSelectionEvent,
            context_label="candidate_generation",
            model_env_var="CANDIDATE_GENERATION_MODEL",
            default_model=model_name,
        )

        # Extract candidates from result
        selection_event = result.result
        candidates = selection_event.candidates

        # Validate we got exactly 2 candidates
        if len(candidates) < 2:
            logger.warning(
                f"LLM generated only {len(candidates)} candidates, expected 2"
            )
            # Could add fallback logic here if needed

        # Ensure candidates have correct IDs
        _ensure_candidate_ids(candidates)

        return candidates

    except StructuredLLMError as e:
        logger.error(f"LLM candidate generation failed: {e}")
        raise Exception(f"LLM service unavailable: {e}") from e


def _ensure_candidate_ids(candidates: List[RequirementCandidate]) -> None:
    """Ensure candidates have correct IDs (A and B).

    Modifies candidates in-place if IDs are incorrect.

    Args:
        candidates: List of candidates to validate/fix
    """
    if len(candidates) >= 2:
        # Ensure first candidate is A, second is B
        if candidates[0].candidate_id != "A":
            candidates[0] = RequirementCandidate(
                candidate_id="A",
                title=candidates[0].title,
                data_source=candidates[0].data_source,
                process_description=candidates[0].process_description,
                output_format=candidates[0].output_format,
                schedule=candidates[0].schedule,
                confidence=candidates[0].confidence,
            )
        if candidates[1].candidate_id != "B":
            candidates[1] = RequirementCandidate(
                candidate_id="B",
                title=candidates[1].title,
                data_source=candidates[1].data_source,
                process_description=candidates[1].process_description,
                output_format=candidates[1].output_format,
                schedule=candidates[1].schedule,
                confidence=candidates[1].confidence,
            )


def candidate_to_requirement_state_dict(candidate: RequirementCandidate) -> dict:
    """Convert a RequirementCandidate to RequirementState dict.

    Args:
        candidate: The candidate to convert

    Returns:
        Dict compatible with RequirementState

    Example:
        >>> candidate = RequirementCandidate(
        ...     candidate_id="A",
        ...     title="テスト",
        ...     data_source="CSV",
        ...     process_description="分析",
        ...     output_format="Excel",
        ...     schedule="毎日",
        ...     confidence=0.8
        ... )
        >>> state = candidate_to_requirement_state_dict(candidate)
        >>> print(state["data_source"])
        'CSV'
    """
    # Calculate completeness based on filled fields
    completeness = 0.0
    if candidate.data_source:
        completeness += 0.25
    if candidate.process_description:
        completeness += 0.35
    if candidate.output_format:
        completeness += 0.25
    if candidate.schedule:
        completeness += 0.15

    return {
        "data_source": candidate.data_source,
        "process_description": candidate.process_description,
        "output_format": candidate.output_format,
        "schedule": candidate.schedule,
        "completeness": completeness,
    }
