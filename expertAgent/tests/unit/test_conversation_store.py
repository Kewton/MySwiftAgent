"""Unit tests for ConversationStore.

Tests conversation history storage with 7-day TTL support.
"""

from datetime import datetime, timedelta

from app.services.conversation.conversation_store import ConversationStore


class TestConversationStore:
    """Test suite for ConversationStore class."""

    def test_init_default_ttl(self):
        """Test initialization with default 7-day TTL."""
        store = ConversationStore()
        assert store._ttl == timedelta(days=7)

    def test_init_custom_ttl(self):
        """Test initialization with custom TTL."""
        store = ConversationStore(ttl_days=14)
        assert store._ttl == timedelta(days=14)

    def test_save_message_creates_new_conversation(self):
        """Test that save_message creates new conversation if not exists."""
        store = ConversationStore()
        store.save_message("conv_001", "user", "Hello")

        conv = store.get_conversation("conv_001")
        assert conv is not None
        assert len(conv["messages"]) == 1
        assert conv["messages"][0]["role"] == "user"
        assert conv["messages"][0]["content"] == "Hello"
        assert "created_at" in conv
        assert "updated_at" in conv

    def test_save_message_appends_to_existing_conversation(self):
        """Test that save_message appends to existing conversation."""
        store = ConversationStore()
        store.save_message("conv_001", "user", "Hello")
        store.save_message("conv_001", "assistant", "Hi there!")

        conv = store.get_conversation("conv_001")
        assert len(conv["messages"]) == 2
        assert conv["messages"][1]["role"] == "assistant"
        assert conv["messages"][1]["content"] == "Hi there!"

    def test_save_message_updates_timestamp(self):
        """Test that save_message updates updated_at timestamp."""
        store = ConversationStore()
        store.save_message("conv_001", "user", "Hello")
        first_update = store.get_conversation("conv_001")["updated_at"]

        # Wait a tiny bit to ensure different timestamp
        import time

        time.sleep(0.01)

        store.save_message("conv_001", "assistant", "Hi!")
        second_update = store.get_conversation("conv_001")["updated_at"]

        assert second_update > first_update

    def test_get_conversation_nonexistent(self):
        """Test get_conversation returns None for nonexistent conversation."""
        store = ConversationStore()
        conv = store.get_conversation("conv_999")
        assert conv is None

    def test_get_messages_empty(self):
        """Test get_messages returns empty list for nonexistent conversation."""
        store = ConversationStore()
        messages = store.get_messages("conv_999")
        assert messages == []

    def test_get_messages_no_limit(self):
        """Test get_messages returns all messages without limit."""
        store = ConversationStore()
        for i in range(5):
            store.save_message("conv_001", "user", f"Message {i}")

        messages = store.get_messages("conv_001")
        assert len(messages) == 5

    def test_get_messages_with_limit(self):
        """Test get_messages returns limited recent messages."""
        store = ConversationStore()
        for i in range(10):
            store.save_message("conv_001", "user", f"Message {i}")

        messages = store.get_messages("conv_001", limit=3)
        assert len(messages) == 3
        assert messages[0]["content"] == "Message 7"
        assert messages[1]["content"] == "Message 8"
        assert messages[2]["content"] == "Message 9"

    def test_delete_conversation_success(self):
        """Test deleting existing conversation."""
        store = ConversationStore()
        store.save_message("conv_001", "user", "Hello")

        result = store.delete_conversation("conv_001")
        assert result is True

        conv = store.get_conversation("conv_001")
        assert conv is None

    def test_delete_conversation_nonexistent(self):
        """Test deleting nonexistent conversation."""
        store = ConversationStore()
        result = store.delete_conversation("conv_999")
        assert result is False

    def test_get_conversation_count(self):
        """Test conversation count tracking."""
        store = ConversationStore()
        assert store.get_conversation_count() == 0

        store.save_message("conv_001", "user", "Hello")
        assert store.get_conversation_count() == 1

        store.save_message("conv_002", "user", "Hi")
        assert store.get_conversation_count() == 2

        store.delete_conversation("conv_001")
        assert store.get_conversation_count() == 1

    def test_cleanup_expired_conversations(self):
        """Test automatic cleanup of expired conversations (7-day TTL)."""
        store = ConversationStore(ttl_days=7)

        # Create conversation
        store.save_message("conv_001", "user", "Hello")

        # Manually set updated_at to 8 days ago (expired)
        store._conversations["conv_001"]["updated_at"] = datetime.now() - timedelta(
            days=8
        )

        # Create fresh conversation
        store.save_message("conv_002", "user", "Fresh message")

        # Trigger cleanup by calling get_conversation
        store.get_conversation("conv_002")

        # Expired conversation should be removed
        assert store.get_conversation_count() == 1
        assert store.get_conversation("conv_001") is None
        assert store.get_conversation("conv_002") is not None

    def test_cleanup_not_expired_conversations(self):
        """Test that non-expired conversations are preserved (within 7 days)."""
        store = ConversationStore(ttl_days=7)

        # Create conversation 6 days ago (not expired)
        store.save_message("conv_001", "user", "Hello")
        store._conversations["conv_001"]["updated_at"] = datetime.now() - timedelta(
            days=6
        )

        # Trigger cleanup
        store.get_conversation("conv_001")

        # Conversation should still exist
        assert store.get_conversation_count() == 1
        assert store.get_conversation("conv_001") is not None

    def test_multiple_conversations_independent(self):
        """Test that multiple conversations are stored independently."""
        store = ConversationStore()

        store.save_message("conv_001", "user", "Hello from conv_001")
        store.save_message("conv_002", "user", "Hello from conv_002")

        conv1 = store.get_conversation("conv_001")
        conv2 = store.get_conversation("conv_002")

        assert len(conv1["messages"]) == 1
        assert len(conv2["messages"]) == 1
        assert conv1["messages"][0]["content"] == "Hello from conv_001"
        assert conv2["messages"][0]["content"] == "Hello from conv_002"

    def test_message_timestamp_included(self):
        """Test that each message includes timestamp."""
        store = ConversationStore()
        store.save_message("conv_001", "user", "Hello")

        messages = store.get_messages("conv_001")
        assert "timestamp" in messages[0]
        assert isinstance(messages[0]["timestamp"], datetime)
