"""Valkey client for persistent storage.

Issue #169: Valkey persistence infrastructure implementation.
Provides async Redis-compatible client using Valkey.
"""

import json
from typing import Any, Dict, Optional, cast

import valkey


class ValkeyConnectionError(Exception):
    """Exception raised for Valkey connection errors."""

    pass


class ValkeyClient:
    """Async Valkey client for key-value storage.

    Provides async interface to Valkey (Redis-compatible) for persistent storage
    with automatic JSON serialization/deserialization.

    Args:
        host: Valkey server host (default: localhost)
        port: Valkey server port (default: 6379)
        db: Database number (default: 0)

    Example:
        async with ValkeyClient(host="localhost", port=6379) as client:
            await client.set("key", {"data": "value"}, ttl=3600)
            data = await client.get("key")
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
    ):
        """Initialize Valkey client configuration.

        Args:
            host: Valkey server host
            port: Valkey server port
            db: Database number (0-15)
        """
        self.host = host
        self.port = port
        self.db = db
        self._client: Optional[valkey.Valkey] = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to Valkey server.

        Raises:
            ValkeyConnectionError: If connection fails
        """
        try:
            self._client = valkey.Valkey(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=False,  # We handle JSON encoding ourselves
            )
            # Test connection
            await self._client.ping()
            self._connected = True
        except Exception as e:
            raise ValkeyConnectionError(f"Failed to connect to Valkey: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from Valkey server."""
        if self._client:
            await self._client.close()
            self._connected = False
            self._client = None

    async def ping(self) -> bool:
        """Ping Valkey server to check connection.

        Returns:
            True if connection is alive

        Raises:
            ValkeyConnectionError: If not connected
        """
        self._ensure_connected()
        result = await self._client.ping()  # type: ignore[union-attr]
        return bool(result)

    async def set(
        self,
        key: str,
        value: Dict[str, Any],
        ttl: Optional[int] = None,
    ) -> bool:
        """Set a key-value pair with optional TTL.

        Args:
            key: Key name
            value: Value to store (will be JSON serialized)
            ttl: Time to live in seconds (optional)

        Returns:
            True if successful

        Raises:
            ValkeyConnectionError: If not connected
        """
        self._ensure_connected()
        serialized = json.dumps(value).encode("utf-8")
        if ttl:
            result = await self._client.set(key, serialized, ex=ttl)  # type: ignore[union-attr]
        else:
            result = await self._client.set(key, serialized)  # type: ignore[union-attr]
        return bool(result)

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get value by key.

        Args:
            key: Key name

        Returns:
            Deserialized value or None if key doesn't exist

        Raises:
            ValkeyConnectionError: If not connected
        """
        self._ensure_connected()
        data = await self._client.get(key)  # type: ignore[union-attr]
        if data is None:
            return None
        decoded = cast(Dict[str, Any], json.loads(data.decode("utf-8")))
        return decoded

    async def delete(self, key: str) -> int:
        """Delete a key.

        Args:
            key: Key name

        Returns:
            Number of keys deleted (0 or 1)

        Raises:
            ValkeyConnectionError: If not connected
        """
        self._ensure_connected()
        result = await self._client.delete(key)  # type: ignore[union-attr]
        return int(result)

    async def exists(self, key: str) -> bool:
        """Check if a key exists.

        Args:
            key: Key name

        Returns:
            True if key exists

        Raises:
            ValkeyConnectionError: If not connected
        """
        self._ensure_connected()
        result = await self._client.exists(key)  # type: ignore[union-attr]
        return bool(result > 0)

    async def get_ttl(self, key: str) -> int:
        """Get TTL (time to live) of a key.

        Args:
            key: Key name

        Returns:
            TTL in seconds, -1 if no TTL, -2 if key doesn't exist

        Raises:
            ValkeyConnectionError: If not connected
        """
        self._ensure_connected()
        result = await self._client.ttl(key)  # type: ignore[union-attr]
        return int(result)

    def _ensure_connected(self) -> None:
        """Ensure client is connected.

        Raises:
            ValkeyConnectionError: If not connected
        """
        if not self._connected or self._client is None:
            raise ValkeyConnectionError(
                "Not connected to Valkey. Call connect() first."
            )

    async def __aenter__(self) -> "ValkeyClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.disconnect()
