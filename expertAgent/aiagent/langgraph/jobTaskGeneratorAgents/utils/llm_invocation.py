"""Shared utilities for structured LLM invocations.

This module centralizes the common pattern used by job/task generator nodes:
- call a chat model obtained via ``create_llm_with_fallback``
- request structured output (Pydantic model)
- fall back to JSON parsing when the structured call fails
- capture raw responses for diagnostics while keeping logs concise
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar, cast

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from pydantic import BaseModel, ValidationError

from app.utils.json_converter import force_to_json_response, to_parse_json

from .llm_factory import create_llm_with_fallback

logger = logging.getLogger(__name__)

TModel = TypeVar("TModel", bound=BaseModel)

RAW_LOG_PREVIEW_CHARS = 2000


class StructuredLLMError(RuntimeError):
    """Raised when structured model calls fail even after JSON recovery."""


@dataclass(slots=True)
class StructuredCallResult(Generic[TModel]):
    """Result returned by ``invoke_structured_llm``."""

    result: TModel
    recovered_via_json: bool
    raw_text: str | None
    model_name: str


def _extract_message_text(message: Any) -> str | None:
    """Extract human-readable text from LangChain message payloads."""

    if message is None:
        return None

    if isinstance(message, str):
        return message

    content: Any = None
    if isinstance(message, BaseMessage):
        content = message.content
        if isinstance(content, str):
            return content
    else:
        content = getattr(message, "content", None)
        if isinstance(content, str):
            return content

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if text:
                    parts.append(str(text))
            else:
                text_attr = getattr(item, "text", None)
                if text_attr:
                    parts.append(str(text_attr))
        if parts:
            return "\n".join(parts)

    additional_kwargs = getattr(message, "additional_kwargs", None)
    if isinstance(additional_kwargs, dict):
        for key in ("tool_calls", "function_call"):
            payload = additional_kwargs.get(key)
            if payload:
                return str(payload)

    return str(message)


def _log_raw_text_preview(raw_text: str, context: str) -> None:
    preview = raw_text[:RAW_LOG_PREVIEW_CHARS]
    truncated = "yes" if len(raw_text) > RAW_LOG_PREVIEW_CHARS else "no"
    logger.error(
        "Raw LLM response preview for %s (len=%d, truncated=%s): %s",
        context,
        len(raw_text),
        truncated,
        preview,
    )


async def _attempt_json_recovery(
    model: BaseChatModel,
    messages: list[dict[str, str]],
    response_model: type[TModel],
    context_label: str,
) -> tuple[TModel | None, str | None, Exception | None]:
    try:
        raw_response = await model.ainvoke(messages)
    except Exception as raw_error:  # pragma: no cover - diagnostics only
        logger.exception(
            "Failed to fetch raw LLM response for %s recovery: %s",
            context_label,
            raw_error,
        )
        return None, None, raw_error

    raw_text = _extract_message_text(raw_response)
    if raw_text is None:
        logger.warning(
            "Raw LLM response for %s recovery is empty (type=%s)",
            context_label,
            type(raw_response).__name__,
        )
        return None, None, ValueError("Empty raw LLM response")

    try:
        parsed_json = to_parse_json(raw_text)
    except ValueError as parse_error:
        logger.error(
            "JSON extraction failed during %s recovery: %s",
            context_label,
            parse_error,
        )
        return None, raw_text, parse_error

    try:
        recovered = response_model.model_validate(parsed_json)
    except ValidationError as validation_error:
        logger.error(
            "Validation failed for %s recovery JSON: %s",
            context_label,
            validation_error,
        )
        return None, raw_text, validation_error

    usage_metadata = getattr(raw_response, "usage_metadata", None)
    if usage_metadata:
        logger.info(
            "LLM usage metadata for %s recovery: %s",
            context_label,
            usage_metadata,
        )

    logger.info(
        "Recovered structured output for %s via JSON fallback",
        context_label,
    )
    return recovered, raw_text, None


async def invoke_structured_llm(
    *,
    messages: list[dict[str, str]],
    response_model: type[TModel],
    context_label: str,
    model_env_var: str,
    default_model: str,
    validator: Callable[[TModel], TModel] | None = None,
    max_tokens_env_var: str = "JOB_GENERATOR_MAX_TOKENS",
    default_max_tokens: int = 8192,
) -> StructuredCallResult[TModel]:
    """Invoke a chat model with structured output and JSON fallback."""

    max_tokens = int(os.getenv(max_tokens_env_var, str(default_max_tokens)))
    model_name = os.getenv(model_env_var, default_model)

    model, perf_tracker, _cost_tracker = create_llm_with_fallback(
        model_name=model_name,
        temperature=0.0,
        max_tokens=max_tokens,
    )

    perf_tracker.start()
    structured_model = model.with_structured_output(response_model)

    primary_error: Exception | None = None
    try:
        structured_response = cast(
            TModel | None,
            await structured_model.ainvoke(messages),
        )
        if structured_response is None:
            raise ValueError("Structured LLM response is None")
        validated = validator(structured_response) if validator else structured_response
        perf_tracker.end(success=True)
        perf_tracker.log_metrics()
        return StructuredCallResult(
            result=validated,
            recovered_via_json=False,
            raw_text=None,
            model_name=perf_tracker.model_name,
        )
    except Exception as err:
        primary_error = err

    (
        recovered_response,
        raw_text,
        recovery_error,
    ) = await _attempt_json_recovery(
        model,
        messages,
        response_model,
        context_label,
    )

    if recovered_response is not None:
        try:
            validated = (
                validator(recovered_response) if validator else recovered_response
            )
            perf_tracker.end(success=True)
            perf_tracker.log_metrics()
            return StructuredCallResult(
                result=validated,
                recovered_via_json=True,
                raw_text=raw_text,
                model_name=perf_tracker.model_name,
            )
        except Exception as secondary_validation_error:
            recovery_error = secondary_validation_error

    failure_error = (
        recovery_error
        or primary_error
        or RuntimeError("Unknown structured LLM failure")
    )

    perf_tracker.end(success=False, error=str(failure_error))
    perf_tracker.log_metrics()

    if raw_text:
        _log_raw_text_preview(raw_text, context_label)
        sanitized = force_to_json_response(
            raw_text,
            error_context=context_label,
            error_detail=str(failure_error),
        )
        logger.debug(
            "Sanitized %s failure payload: %s",
            context_label,
            sanitized,
        )

    raise StructuredLLMError(
        f"{context_label} failed: {failure_error}"
    ) from failure_error
