"""Unit tests for PromptCache.

Tests cover:
- Cache storage and retrieval
- Cache key generation
- Cache invalidation
- Memory management
"""

from app.services.prompt_cache import PromptCache


class TestPromptCache:
    """Test prompt caching functionality."""

    def test_cache_set_and_get(self) -> None:
        """Test basic cache set and get operations."""
        # Arrange
        cache = PromptCache()
        key = "test_prompt:default"
        value = {"system_prompt": "Test"}

        # Act
        cache.set(key, value)
        result = cache.get(key)

        # Assert
        assert result == value

    def test_cache_miss_returns_none(self) -> None:
        """Test that cache miss returns None."""
        # Arrange
        cache = PromptCache()

        # Act
        result = cache.get("nonexistent_key")

        # Assert
        assert result is None

    def test_cache_invalidation(self) -> None:
        """Test cache invalidation for specific key."""
        # Arrange
        cache = PromptCache()
        cache.set("key1", {"value": 1})
        cache.set("key2", {"value": 2})

        # Act
        cache.invalidate("key1")

        # Assert
        assert cache.get("key1") is None
        assert cache.get("key2") == {"value": 2}

    def test_cache_clear_all(self) -> None:
        """Test clearing all cache entries."""
        # Arrange
        cache = PromptCache()
        cache.set("key1", {"value": 1})
        cache.set("key2", {"value": 2})
        cache.set("key3", {"value": 3})

        # Act
        cache.clear()

        # Assert
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.get("key3") is None

    def test_invalidate_by_prompt_name(self) -> None:
        """Test invalidating all versions of a prompt."""
        # Arrange
        cache = PromptCache()
        cache.set("test_prompt:default", {"version": "default"})
        cache.set("test_prompt:v2", {"version": "v2"})
        cache.set("other_prompt:default", {"version": "other"})

        # Act
        cache.invalidate_prompt("test_prompt")

        # Assert
        assert cache.get("test_prompt:default") is None
        assert cache.get("test_prompt:v2") is None
        assert cache.get("other_prompt:default") == {"version": "other"}

    def test_cache_key_generation(self) -> None:
        """Test that cache keys are generated correctly."""
        # Arrange
        cache = PromptCache()

        # Act & Assert
        key1 = cache.make_key("test_prompt", "default")
        key2 = cache.make_key("test_prompt", "v2")
        key3 = cache.make_key("other_prompt", "default")

        assert key1 == "test_prompt:default"
        assert key2 == "test_prompt:v2"
        assert key3 == "other_prompt:default"

    def test_cache_contains(self) -> None:
        """Test checking if key exists in cache."""
        # Arrange
        cache = PromptCache()
        cache.set("existing_key", {"value": 1})

        # Act & Assert
        assert cache.contains("existing_key")
        assert not cache.contains("nonexistent_key")

    def test_cache_size(self) -> None:
        """Test getting cache size."""
        # Arrange
        cache = PromptCache()

        # Act & Assert
        assert cache.size() == 0

        cache.set("key1", {"value": 1})
        assert cache.size() == 1

        cache.set("key2", {"value": 2})
        assert cache.size() == 2

        cache.clear()
        assert cache.size() == 0


class TestPromptCacheSingleton:
    """Test singleton pattern for PromptCache."""

    def test_get_instance_returns_same_instance(self) -> None:
        """Test that get_instance returns the same instance."""
        # Arrange & Act
        PromptCache.reset_instance()  # Ensure clean state
        instance1 = PromptCache.get_instance()
        instance2 = PromptCache.get_instance()

        # Assert
        assert instance1 is instance2

    def test_reset_instance(self) -> None:
        """Test that reset_instance clears singleton."""
        # Arrange
        instance1 = PromptCache.get_instance()
        instance1.set("key", {"value": 1})

        # Act
        PromptCache.reset_instance()
        instance2 = PromptCache.get_instance()

        # Assert
        assert instance1 is not instance2
        assert instance2.get("key") is None  # New instance has no data

    def test_invalidate_prompt_no_entries(self) -> None:
        """Test invalidate_prompt when no entries exist for the prompt."""
        # Arrange
        cache = PromptCache()
        cache.set("other_prompt:v1", {"value": 1})

        # Act: Invalidate non-existent prompt
        cache.invalidate_prompt("test_prompt")

        # Assert: Other prompt should still exist
        assert cache.get("other_prompt:v1") == {"value": 1}
