"""Custom exceptions for expertAgent services."""

from __future__ import annotations

from typing import Any


class ServiceError(RuntimeError):
    """Base class for errors raised by the service layer."""

    def __init__(
        self,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.context = context or {}


class JsonConversionError(ServiceError):
    """Raised when JSON parsing or coercion fails."""


class AgentExecutionError(ServiceError):
    """Raised when an agent invocation fails."""


class TestModeBypass(ServiceError):
    """Raised to bypass execution when test mode short-circuits the flow."""
