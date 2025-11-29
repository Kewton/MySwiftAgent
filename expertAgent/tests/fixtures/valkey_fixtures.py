"""Pytest fixtures for Valkey integration tests.

Tests for Issue #169: Valkey persistence infrastructure implementation.
"""

import asyncio
from typing import AsyncGenerator

import pytest

from app.services.valkey_client import ValkeyClient, ValkeyConnectionError
from app.stores.conversation_store_valkey import ConversationStoreValkey


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def valkey_test_client() -> AsyncGenerator[ValkeyClient, None]:
    """Provide a ValkeyClient instance for integration tests.

    Uses a separate test database (db=15) to avoid conflicts with production data.
    Skips tests if Valkey is not available (e.g., in CI without Valkey service).
    """
    client = ValkeyClient(host="localhost", port=6379, db=15)
    try:
        await client.connect()
    except ValkeyConnectionError as e:
        pytest.skip(f"Valkey not available: {e}")

    # Clean up test data before tests
    try:
        # Clear all keys in test database
        await client._client.flushdb()
    except Exception:  # noqa: S110
        pass

    yield client

    # Clean up test data after tests
    try:
        await client._client.flushdb()
    except Exception:  # noqa: S110
        pass

    await client.disconnect()


@pytest.fixture
async def conversation_store_test(
    valkey_test_client: ValkeyClient,
) -> AsyncGenerator[ConversationStoreValkey, None]:
    """Provide a ConversationStoreValkey instance for integration tests.

    Uses the test Valkey client with database 15.
    """
    store = ConversationStoreValkey(host="localhost", port=6379, db=15)
    await store.connect()

    yield store

    await store.disconnect()


@pytest.fixture
def sample_messages():
    """Sample conversation messages for testing."""
    return [
        {"role": "user", "content": "What is the weather today?"},
        {
            "role": "assistant",
            "content": "I'm sorry, but I don't have access to real-time weather information.",
        },
        {"role": "user", "content": "Can you help me with Python?"},
        {
            "role": "assistant",
            "content": "Of course! I'd be happy to help you with Python. What would you like to know?",
        },
    ]


@pytest.fixture
def sample_metadata():
    """Sample conversation metadata for testing."""
    return {
        "trace_id": "test-trace-12345",
        "prompt_version": "v2.1.0",
        "user_id": "user-789",
        "created_at": "2025-11-14T10:30:00Z",
        "model": "gpt-4o-mini",
    }
