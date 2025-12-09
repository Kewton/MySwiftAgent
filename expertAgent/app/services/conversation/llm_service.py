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
from typing import AsyncGenerator, Dict, List

from langchain_core.runnables.config import RunnableConfig

from aiagent.langgraph.jobTaskGeneratorAgents.prompts.requirement_clarification import (
    REQUIREMENT_CLARIFICATION_SYSTEM_PROMPT,
    create_requirement_clarification_prompt,
    extract_requirement_with_llm,
)
from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_factory import (
    create_llm_with_fallback,
)
from app.schemas.chat import RequirementState
from app.services.langfuse_service import langfuse_service

logger = logging.getLogger(__name__)


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
    # Generate prompt
    user_prompt = create_requirement_clarification_prompt(
        user_message, previous_messages, current_requirements
    )

    messages = [
        {"role": "system", "content": REQUIREMENT_CLARIFICATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    # Get model name and max tokens from environment
    model_name = os.getenv("CHAT_CLARIFICATION_MODEL", "gemini-2.0-flash")
    max_tokens = int(os.getenv("CHAT_CLARIFICATION_MAX_TOKENS", "8192"))

    # Create LLM with streaming enabled
    model, perf_tracker, _cost_tracker = create_llm_with_fallback(
        model_name=model_name,
        temperature=0.7,  # Slightly higher for natural conversation
        max_tokens=max_tokens,
    )

    # Langfuse CallbackHandler生成 (Issue #135: LLM Observability)
    langfuse_handler = langfuse_service.get_callback_handler(
        trace_name="requirement_clarification",
        user_id=user_id,
        session_id=conversation_id,
        tags=["chat", "requirement_clarification", "streaming"],
        metadata={
            "model": model_name,
            "completeness_before": current_requirements.completeness,
        },
    )

    # CallbackHandlerをconfigに追加
    config: RunnableConfig | None = None
    if langfuse_handler:
        config = RunnableConfig(callbacks=[langfuse_handler])

    perf_tracker.start()

    try:
        # Stream LLM response
        full_response = ""

        async for chunk in model.astream(messages, config=config):
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

        perf_tracker.end(success=True)
        perf_tracker.log_metrics()

    except Exception as e:
        perf_tracker.end(success=False, error=str(e))
        perf_tracker.log_metrics()
        logger.error(f"LLM streaming failed: {e}")
        raise
    finally:
        # Langfuseトレースをフラッシュ
        if langfuse_handler:
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
    user_prompt = create_requirement_clarification_prompt(
        user_message, previous_messages, current_requirements
    )

    messages = [
        {"role": "system", "content": REQUIREMENT_CLARIFICATION_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    model_name = os.getenv("CHAT_CLARIFICATION_MODEL", "gemini-2.0-flash")
    max_tokens = int(os.getenv("CHAT_CLARIFICATION_MAX_TOKENS", "8192"))

    model, perf_tracker, _cost_tracker = create_llm_with_fallback(
        model_name=model_name,
        temperature=0.7,
        max_tokens=max_tokens,
    )

    # Langfuse CallbackHandler生成 (Issue #135: LLM Observability)
    langfuse_handler = langfuse_service.get_callback_handler(
        trace_name="requirement_clarification",
        user_id=user_id,
        session_id=conversation_id,
        tags=["chat", "requirement_clarification", "non_streaming"],
        metadata={
            "model": model_name,
            "completeness_before": current_requirements.completeness,
        },
    )

    # CallbackHandlerをconfigに追加
    config: RunnableConfig | None = None
    if langfuse_handler:
        config = RunnableConfig(callbacks=[langfuse_handler])

    perf_tracker.start()

    try:
        response = await model.ainvoke(messages, config=config)
        full_response = (
            str(response.content) if hasattr(response, "content") else str(response)
        )

        updated_requirements = await extract_requirement_with_llm(
            user_message, full_response, current_requirements
        )

        perf_tracker.end(success=True)
        perf_tracker.log_metrics()

        return full_response, updated_requirements

    except Exception as e:
        perf_tracker.end(success=False, error=str(e))
        perf_tracker.log_metrics()
        logger.error(f"Non-streaming clarification failed: {e}")
        raise
    finally:
        # Langfuseトレースをフラッシュ
        if langfuse_handler:
            langfuse_service.flush()
