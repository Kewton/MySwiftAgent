"""Unit tests for storage interfaces.

Tests for Issue #169: Valkey persistence infrastructure implementation.
This test module verifies the ConversationStore interface abstract methods.
"""

import pytest
from typing import Any, Dict, List, Optional

from app.stores.interfaces import ConversationStore


class MockConversationStore(ConversationStore):
    """Mock implementation of ConversationStore for testing."""

    def __init__(self):
        """Initialize mock store."""
        self.connected = False
        self.data: Dict[str, Dict[str, Any]] = {}

    async def connect(self) -> None:
        """Connect to the storage backend."""
        self.connected = True

    async def disconnect(self) -> None:
        """Disconnect from the storage backend."""
        self.connected = False

    async def save_conversation(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        trace_id: Optional[str] = None,
        prompt_version: Optional[str] = None,
        **kwargs: Any,
    ) -> bool:
        """Save a conversation with metadata."""
        self.data[conversation_id] = {
            "messages": messages,
            "trace_id": trace_id,
            "prompt_version": prompt_version,
            **kwargs,
        }
        return True

    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a conversation by ID."""
        return self.data.get(conversation_id)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation by ID."""
        if conversation_id in self.data:
            del self.data[conversation_id]
            return True
        return False

    async def exists(self, conversation_id: str) -> bool:
        """Check if a conversation exists."""
        return conversation_id in self.data


class TestConversationStoreInterface:
    """Test ConversationStore interface implementation."""

    @pytest.mark.unit
    async def test_connect(self):
        """Test connect method is implemented."""
        store = MockConversationStore()
        await store.connect()
        assert store.connected is True

    @pytest.mark.unit
    async def test_disconnect(self):
        """Test disconnect method is implemented."""
        store = MockConversationStore()
        await store.connect()
        await store.disconnect()
        assert store.connected is False

    @pytest.mark.unit
    async def test_save_conversation(self):
        """Test save_conversation method is implemented."""
        store = MockConversationStore()
        await store.connect()

        messages = [{"role": "user", "content": "Hello"}]
        result = await store.save_conversation(
            conversation_id="test-123",
            messages=messages,
            trace_id="trace-456",
            prompt_version="v1.0",
        )

        assert result is True
        assert "test-123" in store.data

    @pytest.mark.unit
    async def test_get_conversation(self):
        """Test get_conversation method is implemented."""
        store = MockConversationStore()
        await store.connect()

        messages = [{"role": "user", "content": "Hello"}]
        await store.save_conversation(
            conversation_id="test-123",
            messages=messages,
        )

        result = await store.get_conversation("test-123")
        assert result is not None
        assert result["messages"] == messages

    @pytest.mark.unit
    async def test_get_conversation_not_found(self):
        """Test get_conversation returns None for missing conversation."""
        store = MockConversationStore()
        await store.connect()

        result = await store.get_conversation("nonexistent")
        assert result is None

    @pytest.mark.unit
    async def test_delete_conversation(self):
        """Test delete_conversation method is implemented."""
        store = MockConversationStore()
        await store.connect()

        messages = [{"role": "user", "content": "Hello"}]
        await store.save_conversation(
            conversation_id="test-123",
            messages=messages,
        )

        result = await store.delete_conversation("test-123")
        assert result is True
        assert "test-123" not in store.data

    @pytest.mark.unit
    async def test_delete_conversation_not_found(self):
        """Test delete_conversation returns False for missing conversation."""
        store = MockConversationStore()
        await store.connect()

        result = await store.delete_conversation("nonexistent")
        assert result is False

    @pytest.mark.unit
    async def test_exists(self):
        """Test exists method is implemented."""
        store = MockConversationStore()
        await store.connect()

        messages = [{"role": "user", "content": "Hello"}]
        await store.save_conversation(
            conversation_id="test-123",
            messages=messages,
        )

        assert await store.exists("test-123") is True
        assert await store.exists("nonexistent") is False

    @pytest.mark.unit
    async def test_save_with_additional_metadata(self):
        """Test save_conversation with additional metadata fields."""
        store = MockConversationStore()
        await store.connect()

        messages = [{"role": "user", "content": "Hello"}]
        result = await store.save_conversation(
            conversation_id="test-123",
            messages=messages,
            trace_id="trace-456",
            prompt_version="v1.0",
            custom_field="custom_value",
        )

        assert result is True
        conversation = await store.get_conversation("test-123")
        assert conversation is not None
        assert conversation["custom_field"] == "custom_value"

    @pytest.mark.unit
    def test_interface_is_abstract(self):
        """Test that ConversationStore cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            ConversationStore()  # type: ignore[abstract]
