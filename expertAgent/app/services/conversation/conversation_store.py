"""In-memory conversation store for chat-based job creation.

This module provides temporary storage for conversation history during the
requirement clarification process. In Phase 1, uses in-memory storage with
TTL-based cleanup. Future phases will migrate to Redis for production.

Design decisions:
- TTL: 7 days (per user feedback)
- Storage: Dict[conversation_id, conversation_data]
- Cleanup: Lazy cleanup on access (no background tasks)
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ConversationStore:
    """In-memory conversation store with TTL support.

    Stores conversation history for requirement clarification chat sessions.
    Automatically cleans up expired conversations (older than TTL).

    Attributes:
        _conversations: Dict mapping conversation_id to conversation data
        _ttl: Time-to-live duration for conversations

    Example:
        >>> store = ConversationStore(ttl_days=7)
        >>> store.save_message('conv_001', 'user', 'Hello')
        >>> conv = store.get_conversation('conv_001')
        >>> print(len(conv['messages']))
        1
    """

    def __init__(self, ttl_days: int = 7):
        """Initialize conversation store.

        Args:
            ttl_days: Number of days to keep conversations before cleanup
        """
        self._conversations: Dict[str, Dict] = {}
        self._ttl = timedelta(days=ttl_days)
        logger.info(f"Initialized ConversationStore with TTL={ttl_days} days")

    def save_message(self, conversation_id: str, role: str, content: str) -> None:
        """Save a message to conversation history.

        Creates new conversation if it doesn't exist. Updates the conversation's
        `updated_at` timestamp on each save.

        Args:
            conversation_id: Unique conversation session ID
            role: Message role ('user' or 'assistant')
            content: Message content

        Example:
            >>> store.save_message('conv_001', 'user', '売上データを分析したい')
            >>> store.save_message('conv_001', 'assistant', 'かしこまりました')
        """
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = {
                "messages": [],
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
            }
            logger.debug(f"Created new conversation: {conversation_id}")

        self._conversations[conversation_id]["messages"].append(
            {"role": role, "content": content, "timestamp": datetime.now()}
        )
        self._conversations[conversation_id]["updated_at"] = datetime.now()

        logger.debug(
            f"Saved message to {conversation_id}: role={role}, length={len(content)}"
        )

    def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Retrieve conversation history.

        Triggers cleanup of expired conversations before retrieval.

        Args:
            conversation_id: Conversation session ID to retrieve

        Returns:
            Conversation data dict with keys: messages, created_at, updated_at
            Returns None if conversation not found or expired

        Example:
            >>> conv = store.get_conversation('conv_001')
            >>> if conv:
            ...     print(f"Messages: {len(conv['messages'])}")
            Messages: 2
        """
        self._cleanup_expired()
        conv = self._conversations.get(conversation_id)

        if conv:
            logger.debug(
                f"Retrieved conversation {conversation_id}: "
                f"{len(conv['messages'])} messages"
            )
        else:
            logger.debug(f"Conversation not found: {conversation_id}")

        return conv

    def get_messages(self, conversation_id: str, limit: Optional[int] = None) -> List[Dict]:
        """Get messages from a conversation.

        Args:
            conversation_id: Conversation session ID
            limit: Maximum number of recent messages to return (None = all)

        Returns:
            List of message dicts, most recent last

        Example:
            >>> messages = store.get_messages('conv_001', limit=10)
            >>> print(messages[-1]['content'])  # Latest message
            'かしこまりました'
        """
        conv = self.get_conversation(conversation_id)
        if not conv:
            return []

        messages = conv["messages"]
        if limit:
            return messages[-limit:]
        return messages

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation.

        Args:
            conversation_id: Conversation session ID to delete

        Returns:
            True if deleted, False if not found
        """
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            logger.info(f"Deleted conversation: {conversation_id}")
            return True

        logger.debug(f"Conversation not found for deletion: {conversation_id}")
        return False

    def get_conversation_count(self) -> int:
        """Get total number of stored conversations.

        Returns:
            Number of active conversations
        """
        self._cleanup_expired()
        return len(self._conversations)

    def _cleanup_expired(self) -> None:
        """Remove expired conversations (older than TTL).

        Called automatically on get_conversation() to ensure storage
        doesn't grow unbounded.
        """
        now = datetime.now()
        expired = [
            cid
            for cid, conv in self._conversations.items()
            if now - conv["updated_at"] > self._ttl
        ]

        for cid in expired:
            del self._conversations[cid]

        if expired:
            logger.info(f"Cleaned up {len(expired)} expired conversations")


# Singleton instance for application-wide use
conversation_store = ConversationStore()
