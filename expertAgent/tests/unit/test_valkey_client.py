"""Unit tests for ValkeyClient.

Tests for Issue #169: Valkey persistence infrastructure implementation.
This test module verifies the ValkeyClient implementation with 90% coverage target.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.valkey_client import ValkeyClient, ValkeyConnectionError


@pytest.fixture
def mock_valkey():
    """Mock Valkey client."""
    with patch("app.services.valkey_client.valkey.Valkey") as mock:
        client = MagicMock()
        client.ping = AsyncMock(return_value=True)
        client.set = AsyncMock(return_value=True)
        client.get = AsyncMock(return_value=b'{"test": "data"}')
        client.delete = AsyncMock(return_value=1)
        client.exists = AsyncMock(return_value=1)
        client.ttl = AsyncMock(return_value=86400)
        client.close = AsyncMock()
        mock.return_value = client
        yield mock, client


class TestValkeyClientConnection:
    """Test ValkeyClient connection functionality."""

    @pytest.mark.unit
    async def test_connect_success(self, mock_valkey):
        """Test successful connection to Valkey."""
        mock_class, mock_client = mock_valkey

        client = ValkeyClient(host="localhost", port=6379, db=0)
        await client.connect()

        mock_class.assert_called_once_with(
            host="localhost", port=6379, db=0, decode_responses=False
        )
        mock_client.ping.assert_awaited_once()

    @pytest.mark.unit
    async def test_connect_failure(self):
        """Test connection failure handling."""
        with patch("app.services.valkey_client.valkey.Valkey") as mock:
            mock.side_effect = Exception("Connection failed")

            client = ValkeyClient(host="invalid-host", port=6379)

            with pytest.raises(ValkeyConnectionError, match="Failed to connect"):
                await client.connect()

    @pytest.mark.unit
    async def test_ping_success(self, mock_valkey):
        """Test successful ping to Valkey."""
        _, mock_client = mock_valkey

        client = ValkeyClient()
        await client.connect()
        result = await client.ping()

        assert result is True
        mock_client.ping.assert_awaited()

    @pytest.mark.unit
    async def test_disconnect(self, mock_valkey):
        """Test disconnection from Valkey."""
        _, mock_client = mock_valkey

        client = ValkeyClient()
        await client.connect()
        await client.disconnect()

        mock_client.close.assert_awaited_once()

    @pytest.mark.unit
    async def test_context_manager(self, mock_valkey):
        """Test ValkeyClient as async context manager."""
        _, mock_client = mock_valkey

        async with ValkeyClient() as client:
            result = await client.ping()
            assert result is True

        mock_client.close.assert_awaited_once()


class TestValkeyClientOperations:
    """Test ValkeyClient CRUD operations."""

    @pytest.mark.unit
    async def test_set_value(self, mock_valkey):
        """Test setting a value in Valkey."""
        _, mock_client = mock_valkey

        client = ValkeyClient()
        await client.connect()

        result = await client.set("test_key", {"data": "value"})

        assert result is True
        mock_client.set.assert_awaited_once()

    @pytest.mark.unit
    async def test_set_value_with_ttl(self, mock_valkey):
        """Test setting a value with TTL."""
        _, mock_client = mock_valkey

        client = ValkeyClient()
        await client.connect()

        result = await client.set("test_key", {"data": "value"}, ttl=3600)

        assert result is True
        call_args = mock_client.set.call_args
        assert call_args.kwargs.get("ex") == 3600

    @pytest.mark.unit
    async def test_get_value(self, mock_valkey):
        """Test getting a value from Valkey."""
        _, mock_client = mock_valkey

        client = ValkeyClient()
        await client.connect()

        result = await client.get("test_key")

        assert result == {"test": "data"}
        mock_client.get.assert_awaited_once_with("test_key")

    @pytest.mark.unit
    async def test_get_nonexistent_value(self, mock_valkey):
        """Test getting a non-existent value returns None."""
        _, mock_client = mock_valkey
        mock_client.get = AsyncMock(return_value=None)

        client = ValkeyClient()
        await client.connect()

        result = await client.get("nonexistent_key")

        assert result is None

    @pytest.mark.unit
    async def test_delete_value(self, mock_valkey):
        """Test deleting a value from Valkey."""
        _, mock_client = mock_valkey

        client = ValkeyClient()
        await client.connect()

        result = await client.delete("test_key")

        assert result == 1
        mock_client.delete.assert_awaited_once_with("test_key")

    @pytest.mark.unit
    async def test_exists(self, mock_valkey):
        """Test checking if a key exists."""
        _, mock_client = mock_valkey

        client = ValkeyClient()
        await client.connect()

        result = await client.exists("test_key")

        assert result is True
        mock_client.exists.assert_awaited_once_with("test_key")

    @pytest.mark.unit
    async def test_get_ttl(self, mock_valkey):
        """Test getting TTL of a key."""
        _, mock_client = mock_valkey

        client = ValkeyClient()
        await client.connect()

        result = await client.get_ttl("test_key")

        assert result == 86400
        mock_client.ttl.assert_awaited_once_with("test_key")


class TestValkeyClientErrorHandling:
    """Test ValkeyClient error handling."""

    @pytest.mark.unit
    async def test_operation_without_connection(self):
        """Test operations fail when not connected."""
        client = ValkeyClient()

        with pytest.raises(ValkeyConnectionError, match="Not connected"):
            await client.get("test_key")

    @pytest.mark.unit
    async def test_set_operation_failure(self, mock_valkey):
        """Test handling of set operation failure."""
        _, mock_client = mock_valkey
        mock_client.set = AsyncMock(side_effect=Exception("Set failed"))

        client = ValkeyClient()
        await client.connect()

        with pytest.raises(Exception, match="Set failed"):
            await client.set("test_key", {"data": "value"})

    @pytest.mark.unit
    async def test_get_operation_failure(self, mock_valkey):
        """Test handling of get operation failure."""
        _, mock_client = mock_valkey
        mock_client.get = AsyncMock(side_effect=Exception("Get failed"))

        client = ValkeyClient()
        await client.connect()

        with pytest.raises(Exception, match="Get failed"):
            await client.get("test_key")

    @pytest.mark.unit
    async def test_invalid_json_handling(self, mock_valkey):
        """Test handling of invalid JSON data."""
        _, mock_client = mock_valkey
        mock_client.get = AsyncMock(return_value=b"invalid json")

        client = ValkeyClient()
        await client.connect()

        with pytest.raises(Exception):
            await client.get("test_key")


class TestValkeyClientConfiguration:
    """Test ValkeyClient configuration options."""

    @pytest.mark.unit
    async def test_custom_host_port(self, mock_valkey):
        """Test custom host and port configuration."""
        mock_class, _ = mock_valkey

        client = ValkeyClient(host="valkey.example.com", port=6380, db=1)
        await client.connect()

        mock_class.assert_called_once_with(
            host="valkey.example.com", port=6380, db=1, decode_responses=False
        )

    @pytest.mark.unit
    async def test_default_configuration(self, mock_valkey):
        """Test default configuration values."""
        mock_class, _ = mock_valkey

        client = ValkeyClient()
        await client.connect()

        mock_class.assert_called_once_with(
            host="localhost", port=6379, db=0, decode_responses=False
        )
