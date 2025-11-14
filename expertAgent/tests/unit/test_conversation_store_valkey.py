"""Unit tests for ConversationStoreValkey.

Tests for Issue #169: Valkey persistence infrastructure implementation.
This test module verifies the ConversationStoreValkey implementation with 90% coverage target.
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.stores.conversation_store_valkey import ConversationStoreValkey
from app.services.valkey_client import ValkeyConnectionError


@pytest.fixture
def mock_valkey_client():
    """Mock ValkeyClient."""
    client = MagicMock()
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.get = AsyncMock()
    client.set = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.exists = AsyncMock(return_value=True)
    client.ping = AsyncMock(return_value=True)
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client


@pytest.fixture
def sample_conversation_data():
    """Sample conversation data for testing."""
    return {
        "conversation_id": "test-conv-123",
        "messages": [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ],
        "metadata": {
            "trace_id": "trace-456",
            "prompt_version": "v1.0",
            "created_at": "2025-11-14T00:00:00Z",
        },
    }


class TestConversationStoreValkeyInit:
    """Test ConversationStoreValkey initialization."""

    @pytest.mark.unit
    def test_init_default_values(self):
        """Test initialization with default values."""
        with patch("app.stores.conversation_store_valkey.ValkeyClient") as mock_client:
            store = ConversationStoreValkey()

            mock_client.assert_called_once_with(
                host="localhost", port=6379, db=0
            )

    @pytest.mark.unit
    def test_init_custom_values(self):
        """Test initialization with custom values."""
        with patch("app.stores.conversation_store_valkey.ValkeyClient") as mock_client:
            store = ConversationStoreValkey(
                host="valkey.example.com",
                port=6380,
                db=1,
                ttl=3600,
                key_prefix="custom:",
            )

            mock_client.assert_called_once_with(
                host="valkey.example.com", port=6380, db=1
            )
            assert store.ttl == 3600
            assert store.key_prefix == "custom:"

    @pytest.mark.unit
    def test_default_ttl(self):
        """Test default TTL is 24 hours."""
        with patch("app.stores.conversation_store_valkey.ValkeyClient"):
            store = ConversationStoreValkey()
            assert store.ttl == 86400  # 24 hours in seconds


class TestConversationStoreValkeySave:
    """Test ConversationStoreValkey save operations."""

    @pytest.mark.unit
    async def test_save_conversation(self, mock_valkey_client, sample_conversation_data):
        """Test saving a conversation."""
        with patch(
            "app.stores.conversation_store_valkey.ValkeyClient",
            return_value=mock_valkey_client,
        ):
            store = ConversationStoreValkey()
            await store.connect()

            result = await store.save_conversation(
                conversation_id="test-conv-123",
                messages=sample_conversation_data["messages"],
                trace_id="trace-456",
                prompt_version="v1.0",
            )

            assert result is True
            mock_valkey_client.set.assert_awaited_once()
            call_args = mock_valkey_client.set.call_args
            assert call_args[0][0] == "conversation:test-conv-123"
            assert call_args.kwargs.get("ttl") == 86400

    @pytest.mark.unit
    async def test_save_conversation_with_custom_ttl(
        self, mock_valkey_client, sample_conversation_data
    ):
        """Test saving a conversation with custom TTL."""
        with patch(
            "app.stores.conversation_store_valkey.ValkeyClient",
            return_value=mock_valkey_client,
        ):
            store = ConversationStoreValkey(ttl=3600)
            await store.connect()

            await store.save_conversation(
                conversation_id="test-conv-123",
                messages=sample_conversation_data["messages"],
            )

            call_args = mock_valkey_client.set.call_args
            assert call_args.kwargs.get("ttl") == 3600

    @pytest.mark.unit
    async def test_save_conversation_without_metadata(self, mock_valkey_client):
        """Test saving a conversation without optional metadata."""
        with patch(
            "app.stores.conversation_store_valkey.ValkeyClient",
            return_value=mock_valkey_client,
        ):
            store = ConversationStoreValkey()
            await store.connect()

            result = await store.save_conversation(
                conversation_id="test-conv-123",
                messages=[{"role": "user", "content": "Hello"}],
            )

            assert result is True
            mock_valkey_client.set.assert_awaited_once()

    @pytest.mark.unit
    async def test_save_conversation_error(self, mock_valkey_client):
        """Test error handling during save operation."""
        mock_valkey_client.set = AsyncMock(side_effect=Exception("Save failed"))

        with patch(
            "app.stores.conversation_store_valkey.ValkeyClient",
            return_value=mock_valkey_client,
        ):
            store = ConversationStoreValkey()
            await store.connect()

            with pytest.raises(Exception, match="Save failed"):
                await store.save_conversation(
                    conversation_id="test-conv-123",
                    messages=[{"role": "user", "content": "Hello"}],
                )


class TestConversationStoreValkeyGet:
    """Test ConversationStoreValkey get operations."""

    @pytest.mark.unit
    async def test_get_conversation(self, mock_valkey_client, sample_conversation_data):
        """Test getting a conversation."""
        mock_valkey_client.get = AsyncMock(return_value=sample_conversation_data)

        with patch(
            "app.stores.conversation_store_valkey.ValkeyClient",
            return_value=mock_valkey_client,
        ):
            store = ConversationStoreValkey()
            await store.connect()

            result = await store.get_conversation("test-conv-123")

            assert result == sample_conversation_data
            mock_valkey_client.get.assert_awaited_once_with("conversation:test-conv-123")

    @pytest.mark.unit
    async def test_get_nonexistent_conversation(self, mock_valkey_client):
        """Test getting a non-existent conversation returns None."""
        mock_valkey_client.get = AsyncMock(return_value=None)

        with patch(
            "app.stores.conversation_store_valkey.ValkeyClient",
            return_value=mock_valkey_client,
        ):
            store = ConversationStoreValkey()
            await store.connect()

            result = await store.get_conversation("nonexistent-conv")

            assert result is None

    @pytest.mark.unit
    async def test_get_conversation_with_custom_prefix(
        self, mock_valkey_client, sample_conversation_data
    ):
        """Test getting a conversation with custom key prefix."""
        mock_valkey_client.get = AsyncMock(return_value=sample_conversation_data)

        with patch(
            "app.stores.conversation_store_valkey.ValkeyClient",
            return_value=mock_valkey_client,
        ):
            store = ConversationStoreValkey(key_prefix="custom:")
            await store.connect()

            result = await store.get_conversation("test-conv-123")

            mock_valkey_client.get.assert_awaited_once_with("custom:test-conv-123")


class TestConversationStoreValkeyDelete:
    """Test ConversationStoreValkey delete operations."""

    @pytest.mark.unit
    async def test_delete_conversation(self, mock_valkey_client):
        """Test deleting a conversation."""
        with patch(
            "app.stores.conversation_store_valkey.ValkeyClient",
            return_value=mock_valkey_client,
        ):
            store = ConversationStoreValkey()
            await store.connect()

            result = await store.delete_conversation("test-conv-123")

            assert result is True
            mock_valkey_client.delete.assert_awaited_once_with(
                "conversation:test-conv-123"
            )

    @pytest.mark.unit
    async def test_delete_nonexistent_conversation(self, mock_valkey_client):
        """Test deleting a non-existent conversation."""
        mock_valkey_client.delete = AsyncMock(return_value=0)

        with patch(
            "app.stores.conversation_store_valkey.ValkeyClient",
            return_value=mock_valkey_client,
        ):
            store = ConversationStoreValkey()
            await store.connect()

            result = await store.delete_conversation("nonexistent-conv")

            assert result is False


class TestConversationStoreValkeyExists:
    """Test ConversationStoreValkey exists operations."""

    @pytest.mark.unit
    async def test_conversation_exists(self, mock_valkey_client):
        """Test checking if a conversation exists."""
        with patch(
            "app.stores.conversation_store_valkey.ValkeyClient",
            return_value=mock_valkey_client,
        ):
            store = ConversationStoreValkey()
            await store.connect()

            result = await store.exists("test-conv-123")

            assert result is True
            mock_valkey_client.exists.assert_awaited_once_with(
                "conversation:test-conv-123"
            )

    @pytest.mark.unit
    async def test_conversation_not_exists(self, mock_valkey_client):
        """Test checking if a conversation does not exist."""
        mock_valkey_client.exists = AsyncMock(return_value=False)

        with patch(
            "app.stores.conversation_store_valkey.ValkeyClient",
            return_value=mock_valkey_client,
        ):
            store = ConversationStoreValkey()
            await store.connect()

            result = await store.exists("nonexistent-conv")

            assert result is False


class TestConversationStoreValkeyConnection:
    """Test ConversationStoreValkey connection management."""

    @pytest.mark.unit
    async def test_connect(self, mock_valkey_client):
        """Test connecting to Valkey."""
        with patch(
            "app.stores.conversation_store_valkey.ValkeyClient",
            return_value=mock_valkey_client,
        ):
            store = ConversationStoreValkey()
            await store.connect()

            mock_valkey_client.connect.assert_awaited_once()

    @pytest.mark.unit
    async def test_disconnect(self, mock_valkey_client):
        """Test disconnecting from Valkey."""
        with patch(
            "app.stores.conversation_store_valkey.ValkeyClient",
            return_value=mock_valkey_client,
        ):
            store = ConversationStoreValkey()
            await store.connect()
            await store.disconnect()

            mock_valkey_client.disconnect.assert_awaited_once()

    @pytest.mark.unit
    async def test_connection_error_handling(self, mock_valkey_client):
        """Test connection error handling."""
        mock_valkey_client.connect = AsyncMock(
            side_effect=ValkeyConnectionError("Connection failed")
        )

        with patch(
            "app.stores.conversation_store_valkey.ValkeyClient",
            return_value=mock_valkey_client,
        ):
            store = ConversationStoreValkey()

            with pytest.raises(ValkeyConnectionError):
                await store.connect()

    @pytest.mark.unit
    async def test_context_manager(self, mock_valkey_client):
        """Test ConversationStoreValkey as async context manager."""
        with patch(
            "app.stores.conversation_store_valkey.ValkeyClient",
            return_value=mock_valkey_client,
        ):
            async with ConversationStoreValkey() as store:
                result = await store.exists("test-conv-123")
                assert result is True

            mock_valkey_client.disconnect.assert_awaited_once()
