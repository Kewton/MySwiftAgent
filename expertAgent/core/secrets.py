"""Unified secrets manager for expertAgent.

Handles secret retrieval from MyVault (priority) or environment variables (fallback).
Includes caching with TTL and manual reload support.
"""

import logging
import time
from typing import Dict, Optional, Tuple

from core.config import settings
from core.myvault_client import MyVaultClient, MyVaultError

logger = logging.getLogger(__name__)


class SecretsManager:
    """Unified secrets manager with MyVault priority and env var fallback."""

    def __init__(self):
        """Initialize secrets manager."""
        self.settings = settings
        self._cache: Dict[str, Dict[str, Tuple[str, float]]] = {}
        self.cache_ttl = settings.SECRETS_CACHE_TTL

        # Initialize MyVault client if enabled
        self.myvault_enabled = settings.MYVAULT_ENABLED
        self.myvault_client: Optional[MyVaultClient] = None

        if self.myvault_enabled:
            try:
                self.myvault_client = MyVaultClient(
                    base_url=settings.MYVAULT_BASE_URL,
                    service_name=settings.MYVAULT_SERVICE_NAME,
                    token=settings.MYVAULT_SERVICE_TOKEN,
                )
                logger.info(
                    f"MyVault client initialized: {settings.MYVAULT_BASE_URL}"
                )
            except Exception as e:
                logger.error(f"Failed to initialize MyVault client: {e}")
                self.myvault_enabled = False

    def get_secret(self, key: str, project: Optional[str] = None) -> str:
        """Get secret value with MyVault priority.

        Priority:
        1. MyVault (if enabled) → use project or default project
        2. Environment variable (fallback)
        3. Raise error if not found

        Args:
            key: Secret key name (e.g., "OPENAI_API_KEY")
            project: Optional project name (uses default if not specified)

        Returns:
            Secret value

        Raises:
            ValueError: If secret not found in MyVault or environment
        """
        # 1. Try MyVault first (priority)
        if self.myvault_enabled and self.myvault_client:
            try:
                value = self._get_from_myvault(key, project)
                if value:
                    project_name = project or self.settings.MYVAULT_DEFAULT_PROJECT or "default"
                    logger.info(f"✓ Secret '{key}' retrieved from MyVault (project: {project_name})")
                    return value
            except MyVaultError as e:
                logger.warning(f"MyVault retrieval failed for '{key}': {e}")
                # Continue to fallback

        # 2. Fallback to environment variable
        env_value = getattr(self.settings, key, "")
        if env_value:
            logger.info(f"↓ Secret '{key}' retrieved from environment variable (fallback)")
            return env_value

        # 3. Not found anywhere
        raise ValueError(
            f"Secret '{key}' not found in MyVault or environment variables"
        )

    def get_secrets_for_project(self, project: Optional[str] = None) -> Dict[str, str]:
        """Get all secrets for a project (or default project).

        Args:
            project: Optional project name

        Returns:
            Dictionary of secret names to values
        """
        if not self.myvault_enabled or not self.myvault_client:
            # Return all env vars
            return self._get_all_env_secrets()

        try:
            project_name = project or self._resolve_default_project()
            return self._get_project_secrets(project_name)
        except MyVaultError:
            logger.warning(f"Failed to get secrets from MyVault, using env vars")
            return self._get_all_env_secrets()

    def clear_cache(self, project: Optional[str] = None):
        """Clear cache for manual reload.

        Args:
            project: Optional project name (clears all if not specified)
        """
        if project:
            self._cache.pop(project, None)
            logger.info(f"Cache cleared for project: {project}")
        else:
            self._cache.clear()
            logger.info("All cache cleared")

    def _get_from_myvault(self, key: str, project: Optional[str]) -> Optional[str]:
        """Get secret from MyVault with cache."""
        if not self.myvault_client:
            return None

        # Resolve project name
        project_name = project or self._resolve_default_project()
        if not project_name:
            raise MyVaultError("No project specified and no default project found")

        # Check cache
        if self._is_cache_valid(project_name, key):
            logger.debug(f"Cache hit for '{key}' in project '{project_name}'")
            return self._cache[project_name][key][0]

        # Fetch from MyVault
        try:
            value = self.myvault_client.get_secret(project_name, key)
            self._update_cache(project_name, key, value)
            return value
        except MyVaultError:
            # Secret not found in this project
            return None

    def _get_project_secrets(self, project: str) -> Dict[str, str]:
        """Get all secrets for a project with cache."""
        if not self.myvault_client:
            return {}

        # Check if we have cached all secrets for this project
        # (We cache individual secrets, so check if cache is recent enough)
        try:
            secrets = self.myvault_client.get_secrets(project)
            # Update cache for all fetched secrets
            for key, value in secrets.items():
                self._update_cache(project, key, value)
            return secrets
        except MyVaultError:
            return {}

    def _resolve_default_project(self) -> str:
        """Resolve default project name.

        Priority:
        1. MYVAULT_DEFAULT_PROJECT env var (override)
        2. Default project from MyVault API
        3. Raise error if not found
        """
        # Check env var override
        if self.settings.MYVAULT_DEFAULT_PROJECT:
            return self.settings.MYVAULT_DEFAULT_PROJECT

        # Get from MyVault API
        if not self.myvault_client:
            raise MyVaultError("MyVault client not initialized")

        default_project = self.myvault_client.get_default_project()
        if not default_project:
            raise MyVaultError("No default project found in MyVault")

        return default_project

    def _get_all_env_secrets(self) -> Dict[str, str]:
        """Get all secrets from environment variables."""
        secret_keys = [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GOOGLE_API_KEY",
            "SERPER_API_KEY",
            "GRAPH_AGENT_MODEL",
            "PODCAST_SCRIPT_DEFAULT_MODEL",
            "MAIL_TO",
            "SPREADSHEET_ID",
            "OLLAMA_URL",
            "OLLAMA_DEF_SMALL_MODEL",
        ]

        return {
            key: getattr(self.settings, key, "")
            for key in secret_keys
            if getattr(self.settings, key, "")
        }

    def _is_cache_valid(self, project: str, key: str) -> bool:
        """Check if cached value is still valid (within TTL)."""
        if project not in self._cache or key not in self._cache[project]:
            return False

        _, timestamp = self._cache[project][key]
        age = time.time() - timestamp
        return age < self.cache_ttl

    def _update_cache(self, project: str, key: str, value: str):
        """Update cache with new value and timestamp."""
        if project not in self._cache:
            self._cache[project] = {}

        self._cache[project][key] = (value, time.time())


# Global instance
secrets_manager = SecretsManager()
