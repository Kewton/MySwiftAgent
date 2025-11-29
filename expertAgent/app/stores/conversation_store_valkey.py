"""Valkey-backed conversation storage implementation.

Issue #169: Valkey persistence infrastructure implementation.
Issue #171: Extended with list_conversations and metadata support.
Implements ConversationStore interface using Valkey for persistent storage.
"""

import logging
from datetime import UTC, datetime
from typing import Any, Dict, List, Optional, Set

from app.services.valkey_client import ValkeyClient
from app.stores.interfaces import ConversationStore

logger = logging.getLogger(__name__)


class ConversationStoreValkey(ConversationStore):
    """Valkey-backed implementation of ConversationStore.

    Stores conversation data in Valkey with automatic TTL (24 hours default).
    Includes metadata support for trace_id, prompt_version, and custom fields.

    Args:
        host: Valkey server host (default: localhost)
        port: Valkey server port (default: 6379)
        db: Database number (default: 0)
        ttl: Time to live in seconds (default: 86400 = 24 hours)
        key_prefix: Key prefix for namespacing (default: "conversation:")

    Example:
        async with ConversationStoreValkey() as store:
            await store.save_conversation(
                conversation_id="conv-123",
                messages=[{"role": "user", "content": "Hello"}],
                trace_id="trace-456",
                prompt_version="v1.0"
            )
            conversation = await store.get_conversation("conv-123")
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        ttl: int = 86400,  # 24 hours default
        key_prefix: str = "conversation:",
    ):
        """Initialize Valkey conversation store.

        Args:
            host: Valkey server host
            port: Valkey server port
            db: Database number
            ttl: Default TTL in seconds (24 hours)
            key_prefix: Key prefix for namespacing
        """
        self._client = ValkeyClient(host=host, port=port, db=db)
        self.ttl = ttl
        self.key_prefix = key_prefix

    async def connect(self) -> None:
        """Connect to Valkey server."""
        await self._client.connect()

    async def disconnect(self) -> None:
        """Disconnect from Valkey server."""
        await self._client.disconnect()

    async def save_conversation(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        trace_id: Optional[str] = None,
        prompt_version: Optional[str] = None,
        **kwargs: Any,
    ) -> bool:
        """Save a conversation with metadata to Valkey.

        Args:
            conversation_id: Unique conversation identifier
            messages: List of conversation messages
            trace_id: Optional trace ID for observability
            prompt_version: Optional prompt version identifier
            **kwargs: Additional metadata fields (including optional ttl parameter)

        Returns:
            True if successful
        """
        key = self._get_key(conversation_id)

        # Extract TTL from kwargs, or use default
        ttl = kwargs.pop("ttl", self.ttl)

        # Build conversation data structure
        metadata: Dict[str, Any] = {
            "updated_at": datetime.now(UTC).isoformat(),
        }

        # Add optional metadata
        if trace_id:
            metadata["trace_id"] = trace_id
        if prompt_version:
            metadata["prompt_version"] = prompt_version

        # Add any additional metadata from kwargs
        metadata.update(kwargs)

        conversation_data: Dict[str, Any] = {
            "conversation_id": conversation_id,
            "messages": messages,
            "metadata": metadata,
        }

        # Save with TTL
        return await self._client.set(key, conversation_data, ttl=ttl)

    async def get_conversation(
        self, conversation_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve a conversation from Valkey.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            Conversation data with messages and metadata, or None if not found
        """
        key = self._get_key(conversation_id)
        return await self._client.get(key)

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation from Valkey.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            True if deleted, False if not found
        """
        key = self._get_key(conversation_id)
        result = await self._client.delete(key)
        return result > 0

    async def exists(self, conversation_id: str) -> bool:
        """Check if a conversation exists in Valkey.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            True if exists
        """
        key = self._get_key(conversation_id)
        return await self._client.exists(key)

    def _get_key(self, conversation_id: str) -> str:
        """Build the full key name with prefix.

        Args:
            conversation_id: Conversation ID

        Returns:
            Full key name with prefix
        """
        return f"{self.key_prefix}{conversation_id}"

    async def list_conversations(
        self,
        conversation_ids: Optional[Set[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List conversations with optional filtering by IDs.

        Issue #171: Added for diagnostic API support.

        Args:
            conversation_ids: Optional set of conversation IDs to filter by
            limit: Maximum number of conversations to return
            offset: Number of conversations to skip

        Returns:
            List of conversation data dictionaries
        """
        conversations: List[Dict[str, Any]] = []

        if conversation_ids:
            # Fetch specific conversations
            sorted_ids = sorted(conversation_ids, reverse=True)
            paginated_ids = sorted_ids[offset : offset + limit]

            for conv_id in paginated_ids:
                conv = await self.get_conversation(conv_id)
                if conv:
                    conversations.append(conv)
        else:
            # Scan for all conversations
            try:
                client = self._client._client
                if client is None:
                    logger.error("Valkey client not connected")
                    return []

                pattern = f"{self.key_prefix}*"
                cursor = 0
                all_ids: List[str] = []

                while True:
                    cursor, keys = await client.scan(
                        cursor=cursor, match=pattern, count=100
                    )
                    for key in keys:
                        key_str = (
                            key.decode("utf-8") if isinstance(key, bytes) else key
                        )
                        conv_id = key_str.replace(self.key_prefix, "")
                        all_ids.append(conv_id)

                    if cursor == 0:
                        break

                # Sort and paginate
                sorted_ids = sorted(all_ids, reverse=True)
                paginated_ids = sorted_ids[offset : offset + limit]

                for conv_id in paginated_ids:
                    conv = await self.get_conversation(conv_id)
                    if conv:
                        conversations.append(conv)

            except Exception as e:
                logger.error(f"Failed to list conversations: {e}")
                return []

        return conversations

    async def __aenter__(self) -> "ConversationStoreValkey":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[object],
    ) -> None:
        """Async context manager exit."""
        await self.disconnect()
