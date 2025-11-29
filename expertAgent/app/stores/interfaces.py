"""Storage interface definitions.

Issue #169: Valkey persistence infrastructure implementation.
Issue #171: Extended with list_conversations for diagnostic API.
Defines abstract interfaces for conversation storage backends.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set


class ConversationStore(ABC):
    """Abstract interface for conversation storage backends.

    Defines the contract that all conversation storage implementations must follow.
    Supports CRUD operations with metadata (trace_id, prompt_version, etc.).

    Issue #171: Extended with list_conversations for diagnostic API filtering.
    """

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the storage backend.

        Should be called before any operations.
        """
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the storage backend.

        Should be called when done with the store.
        """
        ...

    @abstractmethod
    async def save_conversation(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        trace_id: Optional[str] = None,
        prompt_version: Optional[str] = None,
        **kwargs: Any,
    ) -> bool:
        """Save a conversation with metadata.

        Args:
            conversation_id: Unique conversation identifier
            messages: List of conversation messages
            trace_id: Optional trace ID for observability
            prompt_version: Optional prompt version identifier
            **kwargs: Additional metadata fields (including job_id, user_id, etc.)

        Returns:
            True if successful
        """
        ...

    @abstractmethod
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a conversation by ID.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            Conversation data with messages and metadata, or None if not found
        """
        ...

    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation by ID.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            True if deleted, False if not found
        """
        ...

    @abstractmethod
    async def exists(self, conversation_id: str) -> bool:
        """Check if a conversation exists.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            True if exists
        """
        ...

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
        # Default implementation returns empty list
        # Subclasses should override for actual implementation
        return []
