"""Integration tests for Valkey persistence.

Tests for Issue #169: Valkey persistence infrastructure implementation.
This test module verifies end-to-end Valkey integration with 50% coverage target.
"""

import time
from typing import Any, Dict, List

import pytest

from app.services.valkey_client import ValkeyClient, ValkeyConnectionError
from app.stores.conversation_store_valkey import ConversationStoreValkey


@pytest.mark.integration
class TestValkeyClientIntegration:
    """Integration tests for ValkeyClient with real Valkey server."""

    async def test_connection_lifecycle(self, valkey_test_client: ValkeyClient):
        """Test complete connection lifecycle."""
        # Client is already connected via fixture
        assert await valkey_test_client.ping()

        await valkey_test_client.disconnect()

        # Reconnect
        await valkey_test_client.connect()
        assert await valkey_test_client.ping()

    async def test_basic_set_get_operations(self, valkey_test_client: ValkeyClient):
        """Test basic set and get operations."""
        test_data = {"key": "value", "number": 42, "nested": {"data": "test"}}

        # Set value
        result = await valkey_test_client.set("test:basic", test_data)
        assert result is True

        # Get value
        retrieved = await valkey_test_client.get("test:basic")
        assert retrieved == test_data

    async def test_ttl_expiration(self, valkey_test_client: ValkeyClient):
        """Test TTL expiration functionality."""
        test_data = {"message": "This will expire"}

        # Set with short TTL (2 seconds)
        await valkey_test_client.set("test:ttl", test_data, ttl=2)

        # Verify exists immediately
        assert await valkey_test_client.exists("test:ttl")

        # Check TTL
        ttl = await valkey_test_client.get_ttl("test:ttl")
        assert 0 < ttl <= 2

        # Wait for expiration
        time.sleep(3)

        # Verify expired
        assert not await valkey_test_client.exists("test:ttl")
        assert await valkey_test_client.get("test:ttl") is None

    async def test_delete_operations(self, valkey_test_client: ValkeyClient):
        """Test delete operations."""
        # Set a value
        await valkey_test_client.set("test:delete", {"data": "to_delete"})

        # Verify exists
        assert await valkey_test_client.exists("test:delete")

        # Delete
        result = await valkey_test_client.delete("test:delete")
        assert result == 1

        # Verify deleted
        assert not await valkey_test_client.exists("test:delete")

    async def test_multiple_keys(self, valkey_test_client: ValkeyClient):
        """Test operations with multiple keys."""
        keys_data = {
            "test:multi:1": {"id": 1, "name": "first"},
            "test:multi:2": {"id": 2, "name": "second"},
            "test:multi:3": {"id": 3, "name": "third"},
        }

        # Set multiple keys
        for key, data in keys_data.items():
            await valkey_test_client.set(key, data)

        # Get all keys
        for key, expected_data in keys_data.items():
            retrieved = await valkey_test_client.get(key)
            assert retrieved == expected_data


@pytest.mark.integration
class TestConversationStoreValkeyIntegration:
    """Integration tests for ConversationStoreValkey with real Valkey server."""

    async def test_save_and_retrieve_conversation(
        self,
        conversation_store_test: ConversationStoreValkey,
        sample_messages: List[Dict[str, Any]],
    ):
        """Test saving and retrieving a conversation."""
        conversation_id = "conv-integration-001"

        # Save conversation
        result = await conversation_store_test.save_conversation(
            conversation_id=conversation_id,
            messages=sample_messages,
            trace_id="trace-001",
            prompt_version="v1.0",
        )
        assert result is True

        # Retrieve conversation
        conversation = await conversation_store_test.get_conversation(conversation_id)

        assert conversation is not None
        assert conversation["conversation_id"] == conversation_id
        assert conversation["messages"] == sample_messages
        assert conversation["metadata"]["trace_id"] == "trace-001"
        assert conversation["metadata"]["prompt_version"] == "v1.0"

    async def test_conversation_ttl(
        self,
        conversation_store_test: ConversationStoreValkey,
        sample_messages: List[Dict[str, Any]],
    ):
        """Test conversation TTL (24 hours default)."""
        conversation_id = "conv-ttl-test"

        # Save conversation with default TTL
        await conversation_store_test.save_conversation(
            conversation_id=conversation_id, messages=sample_messages
        )

        # Verify exists
        assert await conversation_store_test.exists(conversation_id)

        # Check TTL is approximately 24 hours
        client = conversation_store_test._client
        ttl = await client.get_ttl(f"{conversation_store_test.key_prefix}{conversation_id}")

        # TTL should be close to 86400 seconds (24 hours)
        assert 86395 <= ttl <= 86400

    async def test_update_conversation(
        self,
        conversation_store_test: ConversationStoreValkey,
        sample_messages: List[Dict[str, Any]],
    ):
        """Test updating an existing conversation."""
        conversation_id = "conv-update-test"

        # Save initial conversation
        await conversation_store_test.save_conversation(
            conversation_id=conversation_id,
            messages=sample_messages[:2],
            trace_id="trace-001",
        )

        # Update with more messages
        updated_messages = sample_messages + [
            {"role": "user", "content": "Another question"}
        ]
        await conversation_store_test.save_conversation(
            conversation_id=conversation_id,
            messages=updated_messages,
            trace_id="trace-002",
        )

        # Retrieve and verify
        conversation = await conversation_store_test.get_conversation(conversation_id)
        assert len(conversation["messages"]) == len(updated_messages)
        assert conversation["metadata"]["trace_id"] == "trace-002"

    async def test_delete_conversation(
        self,
        conversation_store_test: ConversationStoreValkey,
        sample_messages: List[Dict[str, Any]],
    ):
        """Test deleting a conversation."""
        conversation_id = "conv-delete-test"

        # Save conversation
        await conversation_store_test.save_conversation(
            conversation_id=conversation_id, messages=sample_messages
        )

        # Verify exists
        assert await conversation_store_test.exists(conversation_id)

        # Delete
        result = await conversation_store_test.delete_conversation(conversation_id)
        assert result is True

        # Verify deleted
        assert not await conversation_store_test.exists(conversation_id)
        assert await conversation_store_test.get_conversation(conversation_id) is None

    async def test_concurrent_conversations(
        self,
        conversation_store_test: ConversationStoreValkey,
        sample_messages: List[Dict[str, Any]],
    ):
        """Test handling multiple concurrent conversations."""
        num_conversations = 10
        conversation_ids = [f"conv-concurrent-{i}" for i in range(num_conversations)]

        # Save multiple conversations
        for conv_id in conversation_ids:
            await conversation_store_test.save_conversation(
                conversation_id=conv_id,
                messages=sample_messages,
                trace_id=f"trace-{conv_id}",
            )

        # Verify all exist
        for conv_id in conversation_ids:
            assert await conversation_store_test.exists(conv_id)
            conversation = await conversation_store_test.get_conversation(conv_id)
            assert conversation is not None
            assert conversation["conversation_id"] == conv_id

    async def test_large_conversation_data(
        self, conversation_store_test: ConversationStoreValkey
    ):
        """Test handling large conversation data."""
        conversation_id = "conv-large-data"

        # Create large conversation (100 messages)
        large_messages = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
            for i in range(100)
        ]

        # Save large conversation
        result = await conversation_store_test.save_conversation(
            conversation_id=conversation_id, messages=large_messages
        )
        assert result is True

        # Retrieve and verify
        conversation = await conversation_store_test.get_conversation(conversation_id)
        assert len(conversation["messages"]) == 100

    async def test_metadata_persistence(
        self,
        conversation_store_test: ConversationStoreValkey,
        sample_messages: List[Dict[str, Any]],
        sample_metadata: Dict[str, Any],
    ):
        """Test that metadata is correctly persisted."""
        conversation_id = "conv-metadata-test"

        # Save with metadata
        await conversation_store_test.save_conversation(
            conversation_id=conversation_id,
            messages=sample_messages,
            trace_id=sample_metadata["trace_id"],
            prompt_version=sample_metadata["prompt_version"],
        )

        # Retrieve and verify metadata
        conversation = await conversation_store_test.get_conversation(conversation_id)
        assert conversation["metadata"]["trace_id"] == sample_metadata["trace_id"]
        assert (
            conversation["metadata"]["prompt_version"]
            == sample_metadata["prompt_version"]
        )


@pytest.mark.integration
class TestValkeyErrorHandling:
    """Integration tests for error handling scenarios."""

    async def test_connection_to_invalid_host(self):
        """Test connection error to invalid host."""
        client = ValkeyClient(host="invalid-host-12345", port=6379, db=0)

        with pytest.raises(ValkeyConnectionError):
            await client.connect()

    async def test_connection_to_invalid_port(self):
        """Test connection error to invalid port."""
        client = ValkeyClient(host="localhost", port=9999, db=0)

        with pytest.raises(ValkeyConnectionError):
            await client.connect()

    async def test_operation_on_disconnected_client(
        self, valkey_test_client: ValkeyClient
    ):
        """Test operations on disconnected client."""
        await valkey_test_client.disconnect()

        with pytest.raises(ValkeyConnectionError):
            await valkey_test_client.get("test:key")
