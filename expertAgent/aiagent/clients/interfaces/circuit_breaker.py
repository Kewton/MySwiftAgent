"""Circuit breaker pattern implementation.

Issue #361: Fault tolerance for external service calls.

This module implements the Circuit Breaker pattern with three states:
- CLOSED: Normal operation, requests pass through
- OPEN: Service failure detected, requests are blocked
- HALF_OPEN: Testing if service recovered

State transitions:
    CLOSED --[failures >= threshold]--> OPEN
    OPEN --[timeout elapsed]--> HALF_OPEN
    HALF_OPEN --[success >= threshold]--> CLOSED
    HALF_OPEN --[failure]--> OPEN
"""

import asyncio
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker state.

    States:
        CLOSED: Normal operation, requests allowed
        OPEN: Failure detected, requests blocked
        HALF_OPEN: Testing recovery, limited requests allowed
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration.

    Attributes:
        failure_threshold: Consecutive failures to trip to OPEN
        success_threshold: Consecutive successes to recover to CLOSED
        timeout_seconds: Time in OPEN before trying HALF_OPEN
        excluded_exceptions: Exceptions that don't count as failures
    """

    failure_threshold: int = 5
    success_threshold: int = 3
    timeout_seconds: float = 30.0
    excluded_exceptions: tuple[type[Exception], ...] = ()


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is OPEN.

    This error indicates the circuit breaker is blocking requests
    to protect the system from a failing service.
    """

    pass


class CircuitBreaker:
    """Circuit breaker for fault tolerance.

    Implements the Circuit Breaker pattern to prevent cascading failures
    when external services are unavailable.

    Example:
        cb = CircuitBreaker(
            config=CircuitBreakerConfig(failure_threshold=3)
        )

        async def call_api():
            return await external_service()

        try:
            result = await cb.call(call_api)
        except CircuitBreakerOpenError:
            # Service is down, use fallback
            result = fallback_value

    Attributes:
        state: Current circuit state
    """

    def __init__(self, config: CircuitBreakerConfig | None = None):
        """Initialize circuit breaker.

        Args:
            config: Circuit breaker configuration
        """
        self._config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float | None = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._state

    async def call(
        self,
        func: Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute function through circuit breaker.

        Args:
            func: Async function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func

        Raises:
            CircuitBreakerOpenError: If circuit is OPEN
            Exception: Any exception raised by func
        """
        async with self._lock:
            self._check_state_transition()

            if self._state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. Wait {self._config.timeout_seconds}s"
                )

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except self._config.excluded_exceptions:
            # Excluded exceptions don't affect circuit state
            raise
        except Exception:
            await self._on_failure()
            raise

    def _check_state_transition(self) -> None:
        """Check and perform state transitions.

        Called before each request to check if OPEN circuit
        should transition to HALF_OPEN after timeout.
        """
        if self._state == CircuitState.OPEN:
            if (
                self._last_failure_time
                and (time.time() - self._last_failure_time)
                >= self._config.timeout_seconds
            ):
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0

    async def _on_success(self) -> None:
        """Handle successful call.

        In HALF_OPEN: Count successes toward recovery
        In CLOSED: Reset failure count
        """
        async with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self._config.success_threshold:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
            else:
                # Reset failure count on success
                self._failure_count = 0

    async def _on_failure(self) -> None:
        """Handle failed call.

        Count failure and potentially trip circuit to OPEN.
        In HALF_OPEN: Any failure trips back to OPEN.
        """
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # Any failure in HALF_OPEN trips back to OPEN
                self._state = CircuitState.OPEN
            elif self._failure_count >= self._config.failure_threshold:
                self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Reset circuit breaker to initial CLOSED state.

        Useful for testing or manual recovery.
        """
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None
