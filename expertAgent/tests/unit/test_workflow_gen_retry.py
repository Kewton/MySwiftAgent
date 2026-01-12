"""Unit tests for WorkflowGenRetry module.

Issue #353: Tests for WORKFLOW_GEN phase retry logic with exponential backoff.
"""

import asyncio

import pytest

from aiagent.langgraph.jobGeneratorV2.protocols import ErrorType, WorkflowError
from aiagent.langgraph.jobGeneratorV2.retry.workflow_gen_retry import (
    WorkflowGenRetryConfig,
    calculate_retry_delay,
    execute_with_timeout,
)


class TestWorkflowGenRetryConfig:
    """Tests for WorkflowGenRetryConfig dataclass."""

    def test_default_values(self) -> None:
        """Config should have sensible defaults."""
        config = WorkflowGenRetryConfig()
        assert config.max_retries == 3
        assert config.base_delay_seconds == 1.0
        assert config.max_delay_seconds == 30.0
        assert config.exponential_base == 2.0
        assert config.llm_timeout_seconds == 120.0
        assert config.registration_timeout_seconds == 30.0
        assert config.total_phase_timeout_seconds == 300.0
        assert config.retry_on_timeout is True
        assert config.retry_on_validation_error is True
        assert config.retry_on_api_error is True

    def test_custom_values(self) -> None:
        """Config should accept custom values."""
        config = WorkflowGenRetryConfig(
            max_retries=5,
            base_delay_seconds=2.0,
            max_delay_seconds=60.0,
            exponential_base=3.0,
            llm_timeout_seconds=180.0,
        )
        assert config.max_retries == 5
        assert config.base_delay_seconds == 2.0
        assert config.max_delay_seconds == 60.0
        assert config.exponential_base == 3.0
        assert config.llm_timeout_seconds == 180.0


class TestCalculateRetryDelay:
    """Tests for calculate_retry_delay function."""

    @pytest.mark.asyncio
    async def test_first_attempt_delay(self) -> None:
        """First attempt should use base delay."""
        config = WorkflowGenRetryConfig(
            base_delay_seconds=1.0,
            max_delay_seconds=30.0,
            exponential_base=2.0,
        )
        delay = await calculate_retry_delay(attempt=1, config=config)
        # With jitter, delay should be close to base_delay (1.0 +/- 20%)
        assert 0.8 <= delay <= 1.2

    @pytest.mark.asyncio
    async def test_exponential_backoff(self) -> None:
        """Delay should increase exponentially."""
        config = WorkflowGenRetryConfig(
            base_delay_seconds=1.0,
            max_delay_seconds=30.0,
            exponential_base=2.0,
        )
        delay1 = await calculate_retry_delay(attempt=1, config=config)
        delay2 = await calculate_retry_delay(attempt=2, config=config)
        delay3 = await calculate_retry_delay(attempt=3, config=config)

        # Without jitter, expected: 1.0, 2.0, 4.0
        # With jitter (+/- 20%), we test approximate ranges
        assert 0.8 <= delay1 <= 1.2
        assert 1.6 <= delay2 <= 2.4
        assert 3.2 <= delay3 <= 4.8

    @pytest.mark.asyncio
    async def test_max_delay_cap(self) -> None:
        """Delay should not exceed max_delay_seconds."""
        config = WorkflowGenRetryConfig(
            base_delay_seconds=10.0,
            max_delay_seconds=15.0,
            exponential_base=2.0,
        )
        # attempt=3: 10 * 2^2 = 40, should be capped at 15
        delay = await calculate_retry_delay(attempt=3, config=config)
        assert delay <= 15.0

    @pytest.mark.asyncio
    async def test_jitter_variation(self) -> None:
        """Multiple calls should produce varying delays due to jitter."""
        config = WorkflowGenRetryConfig(
            base_delay_seconds=10.0,
            max_delay_seconds=30.0,
            exponential_base=2.0,
        )
        delays = [await calculate_retry_delay(attempt=1, config=config) for _ in range(10)]
        # With jitter, delays should not all be identical
        unique_delays = set(delays)
        assert len(unique_delays) > 1  # At least some variation


class TestExecuteWithTimeout:
    """Tests for execute_with_timeout function."""

    @pytest.mark.asyncio
    async def test_successful_execution(self) -> None:
        """Should return result when execution completes in time."""

        async def fast_operation() -> str:
            return "success"

        result = await execute_with_timeout(
            coro=fast_operation(),
            timeout_seconds=5.0,
            error_type=ErrorType.TRANSIENT,
            error_message="Timeout occurred",
        )
        assert result == "success"

    @pytest.mark.asyncio
    async def test_timeout_raises_workflow_error(self) -> None:
        """Should raise WorkflowError when execution times out."""

        async def slow_operation() -> str:
            await asyncio.sleep(10.0)
            return "never"

        with pytest.raises(WorkflowError) as exc_info:
            await execute_with_timeout(
                coro=slow_operation(),
                timeout_seconds=0.1,
                error_type=ErrorType.TRANSIENT,
                error_message="LLM generation timeout",
            )

        assert exc_info.value.error_type == ErrorType.TRANSIENT
        assert "LLM generation timeout" in str(exc_info.value)
        assert exc_info.value.details is not None
        assert "timeout_seconds" in exc_info.value.details

    @pytest.mark.asyncio
    async def test_timeout_with_incomplete_workflow_error_type(self) -> None:
        """Should use INCOMPLETE_WORKFLOW error type when specified."""

        async def slow_operation() -> str:
            await asyncio.sleep(10.0)
            return "never"

        with pytest.raises(WorkflowError) as exc_info:
            await execute_with_timeout(
                coro=slow_operation(),
                timeout_seconds=0.1,
                error_type=ErrorType.INCOMPLETE_WORKFLOW,
                error_message="WORKFLOW_GEN phase timeout",
            )

        assert exc_info.value.error_type == ErrorType.INCOMPLETE_WORKFLOW

    @pytest.mark.asyncio
    async def test_propagates_inner_exceptions(self) -> None:
        """Should propagate exceptions from the coroutine."""

        async def failing_operation() -> str:
            raise ValueError("Inner error")

        with pytest.raises(ValueError) as exc_info:
            await execute_with_timeout(
                coro=failing_operation(),
                timeout_seconds=5.0,
                error_type=ErrorType.TRANSIENT,
                error_message="Timeout occurred",
            )

        assert "Inner error" in str(exc_info.value)
