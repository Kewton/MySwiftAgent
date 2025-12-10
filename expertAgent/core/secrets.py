"""Unified secrets manager for expertAgent.

Handles secret retrieval from MyVault (priority) or
environment variables (fallback).
Includes caching with TTL and manual reload support.
Provides helpers for resolving runtime configuration values.

Issue #194: Added Docker hostname auto-resolution for seamless
dev-start and make environment switching.
"""

import logging
import socket
import time
from typing import Any, Dict, Optional, Tuple

from core.config import settings
from core.myvault_client import MyVaultClient, MyVaultError

logger = logging.getLogger(__name__)

# Docker hostname mappings for auto-resolution (Issue #194)
# Key: Docker internal hostname, Value: localhost equivalent
_DOCKER_HOST_MAPPINGS: Dict[str, str] = {
    "langfuse-server:3000": "localhost:3001",
    "valkey:6379": "localhost:6381",
    "myvault:8000": "localhost:8003",
    "jobqueue:8000": "localhost:8001",
    "expertagent:8000": "localhost:8004",
    "graphaiserver:8000": "localhost:8005",
}


def _is_docker_host_reachable(hostname: str) -> bool:
    """Check if Docker internal hostname is reachable.

    Args:
        hostname: Docker internal hostname (e.g., 'langfuse-server')

    Returns:
        True if hostname is resolvable (running in Docker), False otherwise
    """
    try:
        socket.gethostbyname(hostname)
        return True
    except socket.gaierror:
        return False


def _resolve_docker_hostname(url: str) -> str:
    """Resolve Docker internal hostname to appropriate host based on environment.

    If running inside Docker (hostname resolvable), returns the URL unchanged.
    If running on host machine (hostname not resolvable), converts to localhost.

    Args:
        url: URL potentially containing Docker internal hostname

    Returns:
        Resolved URL appropriate for current environment

    Example:
        # Running in Docker:
        >>> _resolve_docker_hostname("http://langfuse-server:3000")
        'http://langfuse-server:3000'

        # Running on host (dev-start):
        >>> _resolve_docker_hostname("http://langfuse-server:3000")
        'http://localhost:3001'
    """
    for docker_host, localhost_host in _DOCKER_HOST_MAPPINGS.items():
        if docker_host in url:
            # Extract just the hostname part (without port)
            hostname = docker_host.split(":")[0]
            if _is_docker_host_reachable(hostname):
                logger.debug("Docker hostname '%s' is reachable, using as-is", hostname)
                return url
            else:
                resolved_url = url.replace(docker_host, localhost_host)
                logger.info(
                    "Resolved Docker hostname: %s -> %s",
                    docker_host,
                    localhost_host,
                )
                return resolved_url
    return url


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

        logger.debug(
            "SecretsManager init: MYVAULT_ENABLED=%s, BASE_URL=%s, "
            "SERVICE_NAME=%s, TOKEN=%s",
            self.myvault_enabled,
            settings.MYVAULT_BASE_URL,
            settings.MYVAULT_SERVICE_NAME,
            "*" * 10 if settings.MYVAULT_SERVICE_TOKEN else "EMPTY",
        )

        if self.myvault_enabled:
            try:
                self.myvault_client = MyVaultClient(
                    base_url=settings.MYVAULT_BASE_URL,
                    service_name=settings.MYVAULT_SERVICE_NAME,
                    token=settings.MYVAULT_SERVICE_TOKEN,
                )
                logger.info(
                    "✓ MyVault client initialized: %s",
                    settings.MYVAULT_BASE_URL,
                )
            except Exception as e:
                logger.error(f"❌ Failed to initialize MyVault client: {e}")
                self.myvault_enabled = False
        else:
            logger.warning("⚠ MyVault is disabled - using environment variables only")

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
                    project_name = (
                        project or self.settings.MYVAULT_DEFAULT_PROJECT or "default"
                    )
                    logger.info(
                        "✓ Secret '%s' retrieved from MyVault (project: %s)",
                        key,
                        project_name,
                    )
                    return value
            except MyVaultError as e:
                logger.warning(f"MyVault retrieval failed for '{key}': {e}")
                # Continue to fallback

        # 2. Fallback to environment variable
        env_value = getattr(self.settings, key, "")
        if env_value:
            logger.info(
                "↓ Secret '%s' retrieved from environment variable (fallback)",
                key,
            )
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
            logger.warning("Failed to get secrets from MyVault, using env vars")
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
        except MyVaultError as e:
            # Secret not found in this project
            logger.warning(
                "MyVault retrieval failed for '%s' in project '%s': %s",
                key,
                project_name,
                e,
            )
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
        1. Default project from MyVault API (is_default flag)
        2. MYVAULT_DEFAULT_PROJECT env var (override for special cases)
        3. Raise error if not found
        """
        # 1. Try to get default project from MyVault API first
        if self.myvault_client:
            try:
                default_project = self.myvault_client.get_default_project()
                if default_project:
                    logger.debug(
                        "Using default project from MyVault API: %s",
                        default_project,
                    )
                    return default_project
            except MyVaultError as e:
                logger.warning("Failed to get default project from MyVault API: %s", e)
                # Continue to fallback

        # 2. Fallback to env var override (special cases only)
        if self.settings.MYVAULT_DEFAULT_PROJECT:
            logger.debug(
                "Using default project from environment variable: %s",
                self.settings.MYVAULT_DEFAULT_PROJECT,
            )
            return str(self.settings.MYVAULT_DEFAULT_PROJECT)

        # 3. No default project found
        raise MyVaultError(
            "No default project found in MyVault or environment variables"
        )

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
        return bool(age < self.cache_ttl)

    def _update_cache(self, project: str, key: str, value: str):
        """Update cache with new value and timestamp."""
        if project not in self._cache:
            self._cache[project] = {}

        self._cache[project][key] = (value, time.time())

    # ========== Connection Config Methods (Issue #250) ==========

    # Boolean conversion value sets (class-level constants for reusability)
    _BOOL_TRUTHY_VALUES = frozenset({"true", "1", "yes", "on"})
    _BOOL_FALSY_VALUES = frozenset({"false", "0", "no", "off"})

    def _convert_type(self, value: str, value_type: type) -> Any:
        """Convert string value to the specified type.

        Args:
            value: String value to convert
            value_type: Target type (str, int, bool)

        Returns:
            Converted value

        Raises:
            ValueError: If conversion fails or type is unsupported
        """
        if value_type is str:
            return value

        if value_type is int:
            return int(value)

        if value_type is bool:
            return self._convert_to_bool(value)

        raise ValueError(f"Unsupported type: {value_type}")

    def _convert_to_bool(self, value: str) -> bool:
        """Convert string value to boolean.

        Args:
            value: String value to convert

        Returns:
            Boolean value

        Raises:
            ValueError: If value is not a valid boolean string
        """
        lower_value = value.lower()

        if lower_value in self._BOOL_TRUTHY_VALUES:
            return True
        if lower_value in self._BOOL_FALSY_VALUES:
            return False

        raise ValueError(f"Cannot convert '{value}' to bool")

    def _validate_connection_config(
        self, key: str, value: Any, value_type: type
    ) -> None:
        """Validate connection configuration value.

        Args:
            key: Configuration key name
            value: Value to validate
            value_type: Type of the value

        Raises:
            ValueError: If validation fails
        """
        # Port number validation
        if "PORT" in key.upper() and value_type is int:
            if not (1 <= value <= 65535):
                raise ValueError(
                    f"Port number for '{key}' ({value}) must be between 1 and 65535"
                )

        # Hostname validation
        if "HOST" in key.upper() and value_type is str:
            if not (1 <= len(value) <= 255):
                raise ValueError(
                    f"Hostname length for '{key}' must be between 1 and 255 characters"
                )

    def _log_config_retrieval(self, key: str, source: str, value: Any) -> None:
        """Log configuration retrieval with appropriate masking.

        Args:
            key: Configuration key name
            source: Source of the value (e.g., "myvault", "env")
            value: Retrieved value
        """
        upper_key = key.upper()

        # Port numbers are logged without masking
        if "PORT" in upper_key:
            logger.info(
                "Config '%s' retrieved from %s: %s",
                key,
                source,
                value,
            )
        # Hostnames are partially masked
        elif "HOST" in upper_key:
            if isinstance(value, str) and len(value) > 3:
                masked_value = value[:3] + "***"
            else:
                masked_value = "***"
            logger.info(
                "Config '%s' retrieved from %s: %s",
                key,
                source,
                masked_value,
            )
        # Other values are fully masked
        else:
            logger.info(
                "Config '%s' retrieved from %s: ****",
                key,
                source,
            )

    def get_connection_config(
        self,
        key: str,
        project: Optional[str] = None,
        *,
        default: Optional[Any] = None,
        value_type: type = str,
    ) -> Any:
        """Get connection configuration value with type conversion.

        Retrieves configuration values from MyVault (priority) or environment
        variables (fallback), with automatic type conversion.

        Args:
            key: Configuration key name (e.g., "VALKEY_PORT")
            project: Optional project name (uses default if not specified)
            default: Default value if not found (must match value_type)
            value_type: Expected value type (str, int, bool)

        Returns:
            Configuration value converted to value_type

        Raises:
            ValueError: If value not found and no default provided,
                       or if type conversion fails
        """
        raw_value: Optional[str] = None
        source: str = ""

        # 1. Try MyVault first (priority)
        if self.myvault_enabled and self.myvault_client:
            try:
                raw_value = self._get_from_myvault(key, project)
                if raw_value:
                    source = "myvault"
            except MyVaultError as e:
                logger.warning(f"MyVault retrieval failed for '{key}': {e}")
                # Continue to fallback

        # 2. Fallback to environment variable
        if raw_value is None:
            env_value = getattr(self.settings, key, "")
            if env_value:
                raw_value = str(env_value)
                source = "env"

        # 3. Use default if provided
        if raw_value is None:
            if default is not None:
                logger.info(
                    "Config '%s' using default value",
                    key,
                )
                return default

            # 4. Not found anywhere
            raise ValueError(
                f"Connection config '{key}' not found in MyVault or environment variables"
            )

        # Convert type
        try:
            converted_value = self._convert_type(raw_value, value_type)
        except ValueError as e:
            raise ValueError(
                f"Failed to convert '{key}' value '{raw_value}' to {value_type.__name__}: {e}"
            ) from e

        # Validate
        self._validate_connection_config(key, converted_value, value_type)

        # Auto-resolve Docker hostnames for HOST keys (Issue #194)
        if "HOST" in key.upper() and value_type is str:
            converted_value = _resolve_docker_hostname(converted_value)

        # Log retrieval
        self._log_config_retrieval(key, source, converted_value)

        return converted_value


# Global instance
secrets_manager = SecretsManager()


_SETTINGS_ONLY_KEYS = {
    "LOG_LEVEL",
    "LOG_DIR",
    "MYVAULT_ENABLED",
    "MYVAULT_SERVICE_NAME",
    "MYVAULT_SERVICE_TOKEN",
    "MYVAULT_DEFAULT_PROJECT",
    "ADMIN_TOKEN",
}


def _convert_runtime_type(value: str, value_type: type) -> Any:
    """Convert string value to specified type.

    Args:
        value: String value to convert
        value_type: Target type (str, int, bool)

    Returns:
        Converted value

    Raises:
        ValueError: If type conversion fails or type is unsupported

    Note:
        This function mirrors SecretsManager._convert_type() but is kept
        separate to avoid mock coupling in tests and maintain backward
        compatibility with existing test fixtures.
    """
    if value_type is str:
        return value

    if value_type is int:
        try:
            return int(value)
        except ValueError as e:
            raise ValueError(f"Failed to convert '{value}' to int: {e}") from e

    if value_type is bool:
        # Use same logic as SecretsManager._convert_to_bool
        lower_value = value.lower()
        return lower_value in ("true", "1", "yes", "on")

    raise ValueError(f"Unsupported type: {value_type}")


def resolve_runtime_value(
    key: str,
    project: Optional[str] = None,
    *,
    default: Optional[Any] = None,
    value_type: type = str,
) -> Any:
    """Resolve configuration values with MyVault priority and env fallback.

    Args:
        key: Configuration key name
        project: Optional project name for MyVault
        default: Default value if not found
        value_type: Target type for conversion (str, int, bool). Default: str

    Returns:
        Configuration value converted to specified type

    Raises:
        ValueError: If type conversion fails
    """
    if key in _SETTINGS_ONLY_KEYS:
        value = getattr(settings, key, default)
        if value is None:
            return default
        return _convert_runtime_type(str(value), value_type)

    try:
        value = secrets_manager.get_secret(key, project=project)
        return _convert_runtime_type(value, value_type)
    except ValueError as e:
        # Re-raise type conversion errors
        if "Failed to convert" in str(e) or "Unsupported type" in str(e):
            raise
        # Fallback to settings for "not found" errors
        env_value = getattr(settings, key, None)
        if env_value is not None:
            return _convert_runtime_type(str(env_value), value_type)
        return default


def get_model_config(
    key: str,
    default: str,
    project: Optional[str] = None,
) -> str:
    """Get LLM model configuration with MyVault priority and env fallback.

    Retrieves model configuration values with the following priority:
    1. MyVault secret (if available and non-empty)
    2. Environment variable (if set and non-empty)
    3. Default value (always returned if others fail)

    This function is designed for LLM model settings that need to be
    configurable at runtime without service restart.

    Args:
        key: Configuration key name (e.g., "CHAT_CLARIFICATION_MODEL")
        default: Default model name to use if not found elsewhere
        project: Optional project name for MyVault (uses default if not specified)

    Returns:
        Model name string

    Example:
        >>> model = get_model_config("CHAT_CLARIFICATION_MODEL", "gemini-2.0-flash")
        >>> print(model)
        'gemini-2.0-flash'

    Issue #269: LLM model settings management via MyVault.
    """
    import os

    # 1. Try MyVault first (priority)
    try:
        myvault_value = secrets_manager.get_secret(key, project=project)
        if myvault_value:  # Non-empty value from MyVault
            logger.debug(
                "Model config '%s' retrieved from MyVault: %s",
                key,
                myvault_value,
            )
            return myvault_value
    except ValueError as e:
        logger.debug(
            "Model config '%s' not found in MyVault: %s, trying env var",
            key,
            e,
        )
        # Continue to environment variable fallback

    # 2. Fallback to environment variable
    env_value = os.getenv(key, "")
    if env_value:
        logger.debug(
            "Model config '%s' retrieved from environment: %s",
            key,
            env_value,
        )
        return env_value

    # 3. Use default value
    logger.debug(
        "Model config '%s' using default: %s",
        key,
        default,
    )
    return default
