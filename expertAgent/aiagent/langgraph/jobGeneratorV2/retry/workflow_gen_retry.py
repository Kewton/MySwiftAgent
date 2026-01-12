"""Retry logic for WORKFLOW_GEN phase.

Issue #353: Provides exponential backoff retry configuration and utilities
for WORKFLOW_GEN phase, which depends on external APIs (GraphAiServer, LLM).

This module provides:
- WorkflowGenRetryConfig: Configuration for retry behavior
- calculate_retry_delay: Calculate delay with exponential backoff and jitter
- execute_with_timeout: Execute coroutine with timeout
"""

import asyncio
import logging
import secrets
from dataclasses import dataclass
from typing import Any, Coroutine, TypeVar

from aiagent.langgraph.jobGeneratorV2.protocols import ErrorType, WorkflowError

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class WorkflowGenRetryConfig:
    """Configuration for WORKFLOW_GEN phase retry behavior.

    Issue #353: WORKFLOW_GEN phase depends on external APIs (GraphAiServer, LLM),
    so it needs specialized retry configuration with exponential backoff.

    Attributes:
        max_retries: Maximum number of retries (default: 3)
        base_delay_seconds: Base delay for exponential backoff (default: 1.0)
        max_delay_seconds: Maximum delay cap (default: 30.0)
        exponential_base: Base for exponential calculation (default: 2.0)
        llm_timeout_seconds: Timeout for LLM generation (default: 120.0)
        registration_timeout_seconds: Timeout for GraphAiServer registration (default: 30.0)
        total_phase_timeout_seconds: Total phase timeout (default: 300.0)
        retry_on_timeout: Whether to retry on timeout errors (default: True)
        retry_on_validation_error: Whether to retry on validation errors (default: True)
        retry_on_api_error: Whether to retry on API errors (default: True)

    Example:
        config = WorkflowGenRetryConfig(
            max_retries=5,
            base_delay_seconds=2.0,
        )
        for attempt in range(config.max_retries):
            delay = await calculate_retry_delay(attempt + 1, config)
            await asyncio.sleep(delay)
    """

    # Basic retry settings
    max_retries: int = 3
    base_delay_seconds: float = 1.0
    max_delay_seconds: float = 30.0
    exponential_base: float = 2.0

    # Timeout settings
    llm_timeout_seconds: float = 120.0
    registration_timeout_seconds: float = 30.0
    total_phase_timeout_seconds: float = 300.0

    # Conditional retry settings
    retry_on_timeout: bool = True
    retry_on_validation_error: bool = True
    retry_on_api_error: bool = True


async def calculate_retry_delay(
    attempt: int,
    config: WorkflowGenRetryConfig,
) -> float:
    """Calculate retry delay with exponential backoff and jitter.

    Issue #353: Implements exponential backoff with jitter to prevent
    thundering herd problem when multiple requests retry simultaneously.

    Formula: base_delay * (exponential_base ^ (attempt - 1)) + jitter
    Where jitter is +/- 20% of the calculated delay.

    Args:
        attempt: Retry attempt number (1-indexed)
        config: Retry configuration

    Returns:
        Delay in seconds

    Example:
        config = WorkflowGenRetryConfig()
        delay = await calculate_retry_delay(1, config)  # ~1.0 (+/- 20%)
        delay = await calculate_retry_delay(2, config)  # ~2.0 (+/- 20%)
        delay = await calculate_retry_delay(3, config)  # ~4.0 (+/- 20%)
    """
    # Calculate base exponential delay
    delay = config.base_delay_seconds * (config.exponential_base ** (attempt - 1))

    # Add jitter (+/- 20%) to prevent thundering herd
    # Using secrets module for better randomness
    jitter_factor = 0.2
    random_value = secrets.randbelow(1000) / 1000.0  # 0.0 to 0.999
    jitter = delay * jitter_factor * (2 * random_value - 1)
    delay += jitter

    # Cap at max delay
    delay = min(delay, config.max_delay_seconds)

    logger.debug(
        "Calculated retry delay for attempt %d: %.2f seconds",
        attempt,
        delay,
    )

    return delay


async def execute_with_timeout(
    coro: Coroutine[Any, Any, T],
    timeout_seconds: float,
    error_type: ErrorType,
    error_message: str,
) -> T:
    """Execute coroutine with timeout.

    Issue #353: Wraps coroutine execution with a timeout, raising
    WorkflowError on timeout.

    Args:
        coro: Coroutine to execute
        timeout_seconds: Timeout in seconds
        error_type: ErrorType to use if timeout occurs
        error_message: Error message if timeout occurs

    Returns:
        Result from the coroutine

    Raises:
        WorkflowError: If execution times out
        Exception: Any exception raised by the coroutine

    Example:
        result = await execute_with_timeout(
            coro=llm_generate(prompt),
            timeout_seconds=120.0,
            error_type=ErrorType.INCOMPLETE_WORKFLOW,
            error_message="LLM generation timeout",
        )
    """
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError as e:
        logger.error(
            "Timeout after %.2f seconds: %s",
            timeout_seconds,
            error_message,
        )
        raise WorkflowError(
            message=error_message,
            error_type=error_type,
            details={"timeout_seconds": timeout_seconds},
        ) from e


__all__ = [
    "WorkflowGenRetryConfig",
    "calculate_retry_delay",
    "execute_with_timeout",
]
