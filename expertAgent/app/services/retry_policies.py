"""Retry helpers for service operations."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Generic, NoReturn, TypeVar

_T = TypeVar("_T")


@dataclass(slots=True)
class RetryResult(Generic[_T]):
    """Result of a retry operation."""

    value: _T
    attempts: int


@dataclass(slots=True)
class RetryConfig:
    """Retry policy configuration."""

    max_attempts: int = 1

    async def run_async(
        self,
        operation: Callable[[], Awaitable[_T]],
        *,
        logger: Any | None = None,
    ) -> RetryResult[_T]:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be greater than zero")

        for attempt in range(1, self.max_attempts + 1):
            try:
                value = await operation()
                return RetryResult(value=value, attempts=attempt)
            except Exception as exc:  # pragma: no cover - defensive logging
                if logger is not None:
                    logger.warning("Retry attempt %s failed: %s", attempt, exc)
                if attempt >= self.max_attempts:
                    raise
                await asyncio.sleep(0)

        self._raise_unreachable()

    def _raise_unreachable(self) -> NoReturn:
        raise RuntimeError("Retry loop exited without returning a result")
