"""Storage interface definitions.

Issue #169: Valkey persistence infrastructure implementation.
Defines abstract interfaces for conversation storage backends.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class ConversationStore(ABC):
    """Abstract interface for conversation storage backends.

    Defines the contract that all conversation storage implementations must follow.
    Supports CRUD operations with metadata (trace_id, prompt_version, etc.).
    """

    @abstractmethod
    async def connect(self) -> None:
        """Connect to the storage backend.

        Should be called before any operations.
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the storage backend.

        Should be called when done with the store.
        """
        pass

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
            **kwargs: Additional metadata fields

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a conversation by ID.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            Conversation data with messages and metadata, or None if not found
        """
        pass

    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation by ID.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    async def exists(self, conversation_id: str) -> bool:
        """Check if a conversation exists.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            True if exists
        """
        pass
