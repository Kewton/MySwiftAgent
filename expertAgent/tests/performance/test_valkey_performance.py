"""Performance tests for Valkey operations.

Tests for Issue #169: Valkey persistence infrastructure implementation.
Verifies response times meet the requirement of <50ms.
"""

import asyncio
import time
from typing import Any, Dict, List

import pytest

from app.services.valkey_client import ValkeyClient
from app.stores.conversation_store_valkey import ConversationStoreValkey


@pytest.mark.integration
class TestValkeyClientPerformance:
    """Performance tests for ValkeyClient operations."""

    async def test_single_write_performance(self, valkey_test_client: ValkeyClient):
        """Test single write operation performance (<50ms)."""
        test_data = {"key": "value", "number": 42}

        start_time = time.perf_counter()
        await valkey_test_client.set("perf:write", test_data)
        elapsed = (time.perf_counter() - start_time) * 1000  # Convert to ms

        assert elapsed < 50, f"Write took {elapsed:.2f}ms, expected <50ms"

    async def test_single_read_performance(self, valkey_test_client: ValkeyClient):
        """Test single read operation performance (<50ms)."""
        # Setup: write test data
        await valkey_test_client.set("perf:read", {"data": "test"})

        start_time = time.perf_counter()
        await valkey_test_client.get("perf:read")
        elapsed = (time.perf_counter() - start_time) * 1000  # Convert to ms

        assert elapsed < 50, f"Read took {elapsed:.2f}ms, expected <50ms"

    async def test_bulk_write_performance(self, valkey_test_client: ValkeyClient):
        """Test bulk write operations (100 writes) performance."""
        num_writes = 100
        test_data = {"data": "test", "value": 42}

        start_time = time.perf_counter()
        for i in range(num_writes):
            await valkey_test_client.set(f"perf:bulk:{i}", test_data)
        elapsed = (time.perf_counter() - start_time) * 1000  # Convert to ms

        avg_time = elapsed / num_writes
        assert (
            avg_time < 50
        ), f"Average write took {avg_time:.2f}ms, expected <50ms"
        print(f"\nBulk write: {num_writes} ops in {elapsed:.2f}ms (avg: {avg_time:.2f}ms/op)")

    async def test_bulk_read_performance(self, valkey_test_client: ValkeyClient):
        """Test bulk read operations (100 reads) performance."""
        num_reads = 100
        test_data = {"data": "test", "value": 42}

        # Setup: write test data
        for i in range(num_reads):
            await valkey_test_client.set(f"perf:bulk_read:{i}", test_data)

        start_time = time.perf_counter()
        for i in range(num_reads):
            await valkey_test_client.get(f"perf:bulk_read:{i}")
        elapsed = (time.perf_counter() - start_time) * 1000  # Convert to ms

        avg_time = elapsed / num_reads
        assert (
            avg_time < 50
        ), f"Average read took {avg_time:.2f}ms, expected <50ms"
        print(f"\nBulk read: {num_reads} ops in {elapsed:.2f}ms (avg: {avg_time:.2f}ms/op)")


@pytest.mark.integration
class TestConversationStorePerformance:
    """Performance tests for ConversationStoreValkey operations."""

    async def test_save_conversation_performance(
        self,
        conversation_store_test: ConversationStoreValkey,
        sample_messages: List[Dict[str, Any]],
    ):
        """Test conversation save performance (<50ms)."""
        start_time = time.perf_counter()
        await conversation_store_test.save_conversation(
            conversation_id="perf-save-001",
            messages=sample_messages,
            trace_id="trace-perf",
            prompt_version="v1.0",
        )
        elapsed = (time.perf_counter() - start_time) * 1000  # Convert to ms

        assert (
            elapsed < 50
        ), f"Save conversation took {elapsed:.2f}ms, expected <50ms"
        print(f"\nSave conversation: {elapsed:.2f}ms")

    async def test_get_conversation_performance(
        self,
        conversation_store_test: ConversationStoreValkey,
        sample_messages: List[Dict[str, Any]],
    ):
        """Test conversation retrieval performance (<50ms)."""
        # Setup: save conversation
        await conversation_store_test.save_conversation(
            conversation_id="perf-get-001",
            messages=sample_messages,
        )

        start_time = time.perf_counter()
        await conversation_store_test.get_conversation("perf-get-001")
        elapsed = (time.perf_counter() - start_time) * 1000  # Convert to ms

        assert (
            elapsed < 50
        ), f"Get conversation took {elapsed:.2f}ms, expected <50ms"
        print(f"\nGet conversation: {elapsed:.2f}ms")

    async def test_large_conversation_performance(
        self, conversation_store_test: ConversationStoreValkey
    ):
        """Test performance with large conversation (100 messages)."""
        # Create large conversation
        large_messages = [
            {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i} with some content",
            }
            for i in range(100)
        ]

        # Test save performance
        start_time = time.perf_counter()
        await conversation_store_test.save_conversation(
            conversation_id="perf-large-001",
            messages=large_messages,
        )
        save_elapsed = (time.perf_counter() - start_time) * 1000

        # Test get performance
        start_time = time.perf_counter()
        await conversation_store_test.get_conversation("perf-large-001")
        get_elapsed = (time.perf_counter() - start_time) * 1000

        print("\nLarge conversation (100 messages):")
        print(f"  Save: {save_elapsed:.2f}ms")
        print(f"  Get: {get_elapsed:.2f}ms")

        # These might take slightly longer but should still be reasonable
        assert save_elapsed < 100, f"Large save took {save_elapsed:.2f}ms"
        assert get_elapsed < 100, f"Large get took {get_elapsed:.2f}ms"

    async def test_concurrent_operations_performance(
        self,
        conversation_store_test: ConversationStoreValkey,
        sample_messages: List[Dict[str, Any]],
    ):
        """Test performance under concurrent operations (1000 conversations)."""
        num_conversations = 1000

        # Test concurrent saves
        start_time = time.perf_counter()
        tasks = [
            conversation_store_test.save_conversation(
                conversation_id=f"perf-concurrent-{i}",
                messages=sample_messages,
            )
            for i in range(num_conversations)
        ]
        await asyncio.gather(*tasks)
        save_elapsed = (time.perf_counter() - start_time) * 1000

        # Test concurrent reads
        start_time = time.perf_counter()
        tasks = [
            conversation_store_test.get_conversation(f"perf-concurrent-{i}")
            for i in range(num_conversations)
        ]
        await asyncio.gather(*tasks)
        get_elapsed = (time.perf_counter() - start_time) * 1000

        avg_save = save_elapsed / num_conversations
        avg_get = get_elapsed / num_conversations

        print(f"\nConcurrent operations ({num_conversations} conversations):")
        print(f"  Total save time: {save_elapsed:.2f}ms (avg: {avg_save:.2f}ms/op)")
        print(f"  Total get time: {get_elapsed:.2f}ms (avg: {avg_get:.2f}ms/op)")

        # With concurrent operations, individual ops should be well under 50ms
        assert avg_save < 50, f"Average save took {avg_save:.2f}ms"
        assert avg_get < 50, f"Average get took {avg_get:.2f}ms"

    async def test_delete_performance(
        self,
        conversation_store_test: ConversationStoreValkey,
        sample_messages: List[Dict[str, Any]],
    ):
        """Test conversation delete performance (<50ms)."""
        # Setup: save conversation
        await conversation_store_test.save_conversation(
            conversation_id="perf-delete-001",
            messages=sample_messages,
        )

        start_time = time.perf_counter()
        await conversation_store_test.delete_conversation("perf-delete-001")
        elapsed = (time.perf_counter() - start_time) * 1000

        assert elapsed < 50, f"Delete took {elapsed:.2f}ms, expected <50ms"
        print(f"\nDelete conversation: {elapsed:.2f}ms")

    async def test_exists_check_performance(
        self,
        conversation_store_test: ConversationStoreValkey,
        sample_messages: List[Dict[str, Any]],
    ):
        """Test exists check performance (<50ms)."""
        # Setup: save conversation
        await conversation_store_test.save_conversation(
            conversation_id="perf-exists-001",
            messages=sample_messages,
        )

        start_time = time.perf_counter()
        await conversation_store_test.exists("perf-exists-001")
        elapsed = (time.perf_counter() - start_time) * 1000

        assert elapsed < 50, f"Exists check took {elapsed:.2f}ms, expected <50ms"
        print(f"\nExists check: {elapsed:.2f}ms")
