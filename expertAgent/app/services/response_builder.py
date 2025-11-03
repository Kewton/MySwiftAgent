"""Utilities for normalising responses returned by services."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.schemas.standardAiAgent import (
    ExpertAiAgentResponse,
    ExpertAiAgentResponseJson,
)
from app.utils.json_converter import (
    ensure_json_structure,
    force_to_json_response,
    to_parse_json,
)

_THINK_PATTERN = re.compile(r"<think>.*?</think>", flags=re.DOTALL)


def _strip_think_tags(text: str) -> str:
    return _THINK_PATTERN.sub("", text)


@dataclass(slots=True)
class JsonConversionResult:
    """Details for JSON conversion attempts."""

    result: dict[str, Any] | list[Any]
    attempts: int | None = None


class ResponseBuilder:
    """Helper for building consistent response payloads."""

    def remove_think_tags(self, text: str) -> str:
        return _strip_think_tags(text)

    def build_text_response(
        self,
        *,
        result: str,
        response_type: str,
        text: str | None = None,
        chathistory: list[Any] | None = None,
    ) -> ExpertAiAgentResponse:
        cleaned = self.remove_think_tags(result)
        return ExpertAiAgentResponse(
            result=cleaned,
            text=text or cleaned,
            type=response_type,
            chathistory=chathistory,
        )

    def build_json_response(
        self,
        *,
        raw: str | dict[str, Any] | list[Any],
        response_type: str,
        attempts: int | None = None,
        error_context: str | None = None,
        error_detail: str | None = None,
        chathistory: list[Any] | None = None,
    ) -> ExpertAiAgentResponseJson:
        if isinstance(raw, (dict, list)):
            structured = ensure_json_structure(raw, response_type)
            return ExpertAiAgentResponseJson(
                result=structured["result"],
                type=structured.get("type") or response_type,
                attempts=attempts,
                chathistory=chathistory or structured.get("chathistory"),
            )

        cleaned = self.remove_think_tags(str(raw))
        try:
            parsed = to_parse_json(cleaned)
            return ExpertAiAgentResponseJson(
                result=parsed,
                type=response_type,
                attempts=attempts,
                chathistory=chathistory,
            )
        except ValueError:
            forced = force_to_json_response(
                cleaned,
                error_context=error_context or response_type,
                error_detail=error_detail or "JSON conversion failed",
            )
            return ExpertAiAgentResponseJson(
                result=forced,
                type=response_type,
                attempts=attempts,
                chathistory=chathistory,
            )

    def ensure_json_structure(
        self,
        payload: Any,
        *,
        default_type: str | None = None,
    ) -> dict[str, Any]:
        return ensure_json_structure(payload, default_type)
