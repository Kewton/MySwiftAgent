"""Tests for retry helpers."""

import pytest

from app.services.retry_policies import RetryConfig


@pytest.mark.asyncio
async def test_retry_config_success_first_attempt():
    config = RetryConfig(max_attempts=3)
    call_count = 0

    async def op():
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await config.run_async(op)

    assert result.value == "ok"
    assert result.attempts == 1
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_config_success_after_retry():
    config = RetryConfig(max_attempts=3)
    call_count = 0

    async def op():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise RuntimeError("boom")
        return "ok"

    result = await config.run_async(op)

    assert result.value == "ok"
    assert result.attempts == 2
    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_config_raises_after_max_attempts():
    config = RetryConfig(max_attempts=2)
    call_count = 0

    async def op():
        nonlocal call_count
        call_count += 1
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await config.run_async(op)

    assert call_count == 2
