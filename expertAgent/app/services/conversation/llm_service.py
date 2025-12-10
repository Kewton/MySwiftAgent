"""LLM service for streaming requirement clarification chat.

This module provides streaming LLM invocation for real-time chat responses
during the requirement clarification process.

Design decisions:
- Use LangChain streaming mode for real-time responses
- Extract RequirementState from full response (not streamed)
- Simple keyword-based extraction in Phase 1 (improve in Phase 2)
- Langfuse integration for LLM observability (Issue #135)
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.runnables.config import RunnableConfig

from aiagent.langgraph.jobTaskGeneratorAgents.prompts.requirement_clarification import (
    REQUIREMENT_CLARIFICATION_SYSTEM_PROMPT,
    create_requirement_clarification_prompt,
    extract_requirement_with_llm,
)
from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_factory import (
    ModelPerformanceTracker,
    create_llm_with_fallback,
)
from app.schemas.chat import RequirementState
from app.services.langfuse_service import langfuse_service
from core.secrets import get_model_config

logger = logging.getLogger(__name__)


@dataclass
class ClarificationSetup:
    """Container for clarification LLM setup components.

    Groups together the common components needed for both streaming
    and non-streaming clarification functions.
    """

    messages: List[Dict[str, str]]
    model: BaseChatModel
    perf_tracker: ModelPerformanceTracker
    config: RunnableConfig | None
    langfuse_handler: Any


def _setup_clarification_llm(
    user_message: str,
    previous_messages: List[Dict],
    current_requirements: RequirementState,
    conversation_id: str | None = None,
    user_id: str | None = None,
    is_streaming: bool = True,
) -> ClarificationSetup:
    """Set up LLM components for requirement clarification.

    Extracts common setup logic for both streaming and non-streaming modes.

    Args:
        user_message: User's latest message
        previous_messages: Previous conversation history
        current_requirements: Current requirement state
        conversation_id: Conversation ID for Langfuse session tracking
        user_id: User ID for Langfuse user tracking
        is_streaming: Whether streaming mode is enabled

    Returns:
        ClarificationSetup with all configured components
    """
    # Generate prompt
    user_prompt = create_requirement_clarification_prompt(
        user_message, previous_messages, current_requirements
    )

    messages = [
        {"role": "system", "content": REQUIREMENT_CLARIFICATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    # Get model name and max tokens from environment
    # Issue #269: Use get_model_config for MyVault-managed model settings
    model_name = get_model_config("CHAT_CLARIFICATION_MODEL", "gemini-2.0-flash")
    max_tokens = int(os.getenv("CHAT_CLARIFICATION_MAX_TOKENS", "8192"))

    # Create LLM
    model, perf_tracker, _cost_tracker = create_llm_with_fallback(
        model_name=model_name,
        temperature=0.7,  # Slightly higher for natural conversation
        max_tokens=max_tokens,
    )

    # Langfuse CallbackHandler
    mode_tag = "streaming" if is_streaming else "non_streaming"
    langfuse_handler = langfuse_service.get_callback_handler(
        trace_name="requirement_clarification",
        user_id=user_id,
        session_id=conversation_id,
        tags=["chat", "requirement_clarification", mode_tag],
        metadata={
            "model": model_name,
            "completeness_before": current_requirements.completeness,
        },
    )

    # Build config with callback handler
    config: RunnableConfig | None = None
    if langfuse_handler:
        config = RunnableConfig(callbacks=[langfuse_handler])

    return ClarificationSetup(
        messages=messages,
        model=model,
        perf_tracker=perf_tracker,
        config=config,
        langfuse_handler=langfuse_handler,
    )


async def stream_requirement_clarification(
    user_message: str,
    previous_messages: List[Dict],
    current_requirements: RequirementState,
    conversation_id: str | None = None,
    user_id: str | None = None,
) -> AsyncGenerator[Dict, None]:
    """Stream requirement clarification chat responses.

    Yields SSE-compatible events:
    - type='message': Streaming text chunks
    - type='requirement_update': Updated requirement state
    - type='requirements_ready': Requirements are 80%+ complete

    Args:
        user_message: User's latest message
        previous_messages: Previous conversation history
        current_requirements: Current requirement state
        conversation_id: Conversation ID for Langfuse session tracking
        user_id: User ID for Langfuse user tracking

    Yields:
        Dict with 'type' and 'data' keys for SSE events

    Example:
        >>> async for event in stream_requirement_clarification(...):
        ...     if event['type'] == 'message':
        ...         print(event['data']['content'], end='')
        かしこまりました。どのような形式の売上データですか？

    Raises:
        Exception: If LLM invocation fails
    """
    # Set up LLM components using shared helper
    setup = _setup_clarification_llm(
        user_message,
        previous_messages,
        current_requirements,
        conversation_id,
        user_id,
        is_streaming=True,
    )

    setup.perf_tracker.start()

    try:
        # Stream LLM response
        full_response = ""

        async for chunk in setup.model.astream(setup.messages, config=setup.config):
            # Extract text content from chunk
            content = ""
            if hasattr(chunk, "content"):
                content = str(chunk.content)
            elif isinstance(chunk, str):
                content = chunk

            if content:
                full_response += content
                yield {"type": "message", "data": {"content": content}}

        # Extract requirements from full conversation using LLM
        updated_requirements = await extract_requirement_with_llm(
            user_message, full_response, current_requirements
        )

        # Yield updated requirement state
        yield {
            "type": "requirement_update",
            "data": {"requirements": updated_requirements.model_dump()},
        }

        # Check if requirements are ready for job creation (80%+)
        if updated_requirements.completeness >= 0.8:
            yield {"type": "requirements_ready", "data": {}}
            logger.info(
                f"Requirements ready for job creation "
                f"(completeness={updated_requirements.completeness:.0%})"
            )

        setup.perf_tracker.end(success=True)
        setup.perf_tracker.log_metrics()

    except Exception as e:
        setup.perf_tracker.end(success=False, error=str(e))
        setup.perf_tracker.log_metrics()
        logger.error(f"LLM streaming failed: {e}")
        raise
    finally:
        # Langfuse trace flush
        if setup.langfuse_handler:
            langfuse_service.flush()


async def non_streaming_clarification(
    user_message: str,
    previous_messages: List[Dict],
    current_requirements: RequirementState,
    conversation_id: str | None = None,
    user_id: str | None = None,
) -> tuple[str, RequirementState]:
    """Non-streaming fallback for requirement clarification.

    Used when streaming fails or is not supported.

    Args:
        user_message: User's latest message
        previous_messages: Previous conversation history
        current_requirements: Current requirement state
        conversation_id: Conversation ID for Langfuse session tracking
        user_id: User ID for Langfuse user tracking

    Returns:
        Tuple of (full_response, updated_requirements)

    Example:
        >>> response, state = await non_streaming_clarification(...)
        >>> print(response)
        'かしこまりました。どのような形式の売上データですか？'
        >>> print(state.completeness)
        0.35
    """
    # Set up LLM components using shared helper
    setup = _setup_clarification_llm(
        user_message,
        previous_messages,
        current_requirements,
        conversation_id,
        user_id,
        is_streaming=False,
    )

    setup.perf_tracker.start()

    try:
        response = await setup.model.ainvoke(setup.messages, config=setup.config)
        full_response = (
            str(response.content) if hasattr(response, "content") else str(response)
        )

        updated_requirements = await extract_requirement_with_llm(
            user_message, full_response, current_requirements
        )

        setup.perf_tracker.end(success=True)
        setup.perf_tracker.log_metrics()

        return full_response, updated_requirements

    except Exception as e:
        setup.perf_tracker.end(success=False, error=str(e))
        setup.perf_tracker.log_metrics()
        logger.error(f"Non-streaming clarification failed: {e}")
        raise
    finally:
        # Langfuse trace flush
        if setup.langfuse_handler:
            langfuse_service.flush()
