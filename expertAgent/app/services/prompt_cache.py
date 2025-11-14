"""Prompt caching service.

Provides in-memory caching for loaded prompts to improve performance.
Uses Singleton pattern to ensure a single cache instance across the application.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Constants
CACHE_KEY_SEPARATOR = ":"


class PromptCache:
    """In-memory cache for prompts.

    This class implements a simple in-memory caching mechanism for prompts.
    It provides methods for setting, getting, invalidating, and clearing cache entries.

    Note: This class can be instantiated multiple times. If you need a singleton
    instance, use the get_instance() factory method.
    """

    _instance: Optional["PromptCache"] = None

    def __init__(self) -> None:
        """Initialize the cache.

        Creates a new cache instance with an empty dictionary.
        For singleton usage, prefer get_instance() method.
        """
        self._cache: dict[str, dict[str, Any]] = {}
        logger.debug("PromptCache instance created")

    @classmethod
    def get_instance(cls) -> "PromptCache":
        """Get or create singleton instance of PromptCache.

        Returns:
            Singleton PromptCache instance
        """
        if cls._instance is None:
            cls._instance = cls()
            logger.info("Created singleton PromptCache instance")
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (primarily for testing).

        This method should only be used in test scenarios to ensure
        a clean state between tests.
        """
        cls._instance = None
        logger.debug("Reset singleton PromptCache instance")

    def set(self, key: str, value: dict[str, Any]) -> None:
        """Set a cache entry.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = value
        logger.debug(f"Cache set: {key}")

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
        if key in self._cache:
            self._cache.pop(key, None)
            logger.debug(f"Cache invalidated: {key}")
        else:
            logger.debug(f"Cache invalidation skipped (key not found): {key}")

    def clear(self) -> None:
        """Clear all cache entries."""
        size_before = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared ({size_before} entries removed)")

    def invalidate_prompt(self, prompt_name: str) -> None:
        """Invalidate all versions of a prompt.

        Args:
            prompt_name: Prompt name (e.g., "test_prompt")
        """
        # Remove all keys starting with prompt_name:
        prefix = f"{prompt_name}{CACHE_KEY_SEPARATOR}"
        keys_to_remove = [k for k in self._cache.keys() if k.startswith(prefix)]
        for key in keys_to_remove:
            self._cache.pop(key, None)

        if keys_to_remove:
            logger.info(f"Invalidated {len(keys_to_remove)} cache entries for prompt: {prompt_name}")
        else:
            logger.debug(f"No cache entries found for prompt: {prompt_name}")

    def make_key(self, prompt_name: str, version: str) -> str:
        """Generate a cache key.

        Args:
            prompt_name: Prompt name
            version: Version name

        Returns:
            Cache key in format "prompt_name:version"
        """
        return f"{prompt_name}{CACHE_KEY_SEPARATOR}{version}"

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
