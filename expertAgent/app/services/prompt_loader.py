"""Prompt loader service with YAML support and caching.

Provides functionality to load prompts from YAML files with:
- Default fallback (default.yaml)
- Version specification
- Caching for performance
- Factory pattern for creating loaders
- Strategy pattern for different loading strategies (extensible)
"""

import logging
from pathlib import Path
from typing import Any, Optional

import yaml

from app.services.prompt_cache import PromptCache

logger = logging.getLogger(__name__)

# Constants
DEFAULT_VERSION = "default"
YAML_FILE_EXTENSION = ".yaml"
DEFAULT_PROMPTS_DIR = "prompts"


class PromptNotFoundError(Exception):
    """Exception raised when prompt cannot be found.

    This exception is raised when:
    - The prompt directory doesn't exist
    - The requested version file doesn't exist
    - The YAML file has invalid format
    - The YAML file cannot be parsed
    """

    pass


class PromptLoader:
    """Load prompts from YAML files with caching.

    This class provides functionality to load prompt configurations from YAML files
    with support for versioning and caching. It follows the Single Responsibility
    Principle by focusing solely on prompt loading logic.

    Attributes:
        base_dir: Base directory containing prompt files
        enable_cache: Whether caching is enabled
    """

    def __init__(
        self,
        base_dir: Optional[Path] = None,
        enable_cache: bool = True,
    ) -> None:
        """Initialize the prompt loader.

        Args:
            base_dir: Base directory for prompts (defaults to expertAgent/prompts)
            enable_cache: Enable caching (default: True)
        """
        if base_dir is None:
            # Default to expertAgent/prompts
            base_dir = Path(__file__).parent.parent.parent / DEFAULT_PROMPTS_DIR

        self.base_dir = Path(base_dir)
        self.enable_cache = enable_cache
        self._cache = PromptCache() if enable_cache else None
        logger.info(
            f"PromptLoader initialized (base_dir={self.base_dir}, cache={'enabled' if enable_cache else 'disabled'})"
        )

    @classmethod
    def create_default(cls) -> "PromptLoader":
        """Factory method: Create a loader with default settings.

        Returns:
            PromptLoader instance with default configuration
        """
        return cls(base_dir=None, enable_cache=True)

    @classmethod
    def create_without_cache(cls, base_dir: Optional[Path] = None) -> "PromptLoader":
        """Factory method: Create a loader without caching.

        Args:
            base_dir: Base directory for prompts

        Returns:
            PromptLoader instance with caching disabled
        """
        return cls(base_dir=base_dir, enable_cache=False)

    def load_prompt(
        self,
        prompt_name: str,
        version: Optional[str] = None,
    ) -> dict[str, Any]:
        """Load a prompt from YAML file.

        This method first checks the cache (if enabled) for the requested prompt.
        If not cached, it loads from the filesystem and caches the result.

        Args:
            prompt_name: Name of the prompt (directory name)
            version: Optional version name (defaults to "default")

        Returns:
            Loaded prompt data as a dictionary

        Raises:
            PromptNotFoundError: If prompt or version not found, or YAML is invalid
        """
        # Default to "default" version
        version = version or DEFAULT_VERSION

        # Check cache first
        cached_data = self._get_from_cache(prompt_name, version)
        if cached_data is not None:
            return cached_data

        # Load from file
        prompt_dir = self._get_prompt_directory(prompt_name)
        yaml_file = self._get_yaml_file(prompt_dir, version)
        data = self._load_yaml_file(yaml_file)

        # Cache if enabled
        self._set_to_cache(prompt_name, version, data)

        logger.info(f"Loaded prompt: {prompt_name} (version: {version})")
        return data

    def _get_from_cache(
        self, prompt_name: str, version: str
    ) -> Optional[dict[str, Any]]:
        """Get prompt from cache if available.

        Args:
            prompt_name: Name of the prompt
            version: Version name

        Returns:
            Cached data or None if not cached
        """
        if self._cache is not None:
            cache_key = self._cache.make_key(prompt_name, version)
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached
        return None

    def _set_to_cache(
        self, prompt_name: str, version: str, data: dict[str, Any]
    ) -> None:
        """Set prompt data to cache.

        Args:
            prompt_name: Name of the prompt
            version: Version name
            data: Data to cache
        """
        if self._cache is not None:
            cache_key = self._cache.make_key(prompt_name, version)
            self._cache.set(cache_key, data)
            logger.debug(f"Cached {cache_key}")

    def _get_prompt_directory(self, prompt_name: str) -> Path:
        """Get and validate prompt directory.

        Args:
            prompt_name: Name of the prompt

        Returns:
            Path to prompt directory

        Raises:
            PromptNotFoundError: If directory doesn't exist
        """
        prompt_dir = self.base_dir / prompt_name
        if not prompt_dir.exists():
            raise PromptNotFoundError(f"Prompt directory not found: {prompt_dir}")
        return prompt_dir

    def _get_yaml_file(self, prompt_dir: Path, version: str) -> Path:
        """Get and validate YAML file path.

        Args:
            prompt_dir: Directory containing prompts
            version: Version name

        Returns:
            Path to YAML file

        Raises:
            PromptNotFoundError: If file doesn't exist
        """
        yaml_file = prompt_dir / f"{version}{YAML_FILE_EXTENSION}"
        if not yaml_file.exists():
            raise PromptNotFoundError(
                f"Prompt file not found: {yaml_file} (version: {version})"
            )
        return yaml_file

    def _load_yaml_file(self, yaml_file: Path) -> dict[str, Any]:
        """Load and validate YAML file.

        Args:
            yaml_file: Path to YAML file

        Returns:
            Loaded YAML data

        Raises:
            PromptNotFoundError: If YAML is invalid or cannot be parsed
        """
        try:
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                raise PromptNotFoundError(
                    f"Invalid YAML format in {yaml_file}: expected dict, got {type(data)}"
                )

            return data

        except yaml.YAMLError as e:
            error_msg = f"Failed to parse YAML in {yaml_file}: {e}"
            logger.error(error_msg)
            raise PromptNotFoundError(error_msg) from e
        except (OSError, IOError) as e:
            error_msg = f"Failed to read file {yaml_file}: {e}"
            logger.error(error_msg)
            raise PromptNotFoundError(error_msg) from e

    def list_versions(self, prompt_name: str) -> list[str]:
        """List all available versions for a prompt.

        Args:
            prompt_name: Name of the prompt

        Returns:
            List of version names (without .yaml extension), sorted alphabetically
        """
        prompt_dir = self.base_dir / prompt_name
        if not prompt_dir.exists():
            logger.debug(f"Prompt directory not found: {prompt_dir}")
            return []

        # Find all .yaml files
        yaml_files = prompt_dir.glob(f"*{YAML_FILE_EXTENSION}")
        versions = [f.stem for f in yaml_files]

        logger.debug(
            f"Found {len(versions)} versions for prompt '{prompt_name}': {versions}"
        )
        return sorted(versions)

    def clear_cache(self) -> None:
        """Clear the entire cache.

        This method clears all cached prompts. Use this when you need to
        force a reload of all prompts from disk.
        """
        if self._cache is not None:
            self._cache.clear()
        else:
            logger.debug("Cache clear requested but caching is disabled")
