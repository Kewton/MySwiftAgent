"""Prompt caching service.

Provides in-memory caching for loaded prompts to improve performance.
"""

from typing import Any, Optional


class PromptCache:
    """In-memory cache for prompts."""

    def __init__(self) -> None:
        """Initialize the cache."""
        self._cache: dict[str, dict[str, Any]] = {}

    def set(self, key: str, value: dict[str, Any]) -> None:
        """Set a cache entry.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = value

    def get(self, key: str) -> Optional[dict[str, Any]]:
        """Get a cache entry.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        return self._cache.get(key)

    def invalidate(self, key: str) -> None:
        """Invalidate a specific cache entry.

        Args:
            key: Cache key to invalidate
        """
        self._cache.pop(key, None)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def invalidate_prompt(self, prompt_name: str) -> None:
        """Invalidate all versions of a prompt.

        Args:
            prompt_name: Prompt name (e.g., "test_prompt")
        """
        # Remove all keys starting with prompt_name:
        keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{prompt_name}:")]
        for key in keys_to_remove:
            self._cache.pop(key, None)

    def make_key(self, prompt_name: str, version: str) -> str:
        """Generate a cache key.

        Args:
            prompt_name: Prompt name
            version: Version name

        Returns:
            Cache key in format "prompt_name:version"
        """
        return f"{prompt_name}:{version}"

    def contains(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        return key in self._cache

    def size(self) -> int:
        """Get cache size.

        Returns:
            Number of cached entries
        """
        return len(self._cache)
