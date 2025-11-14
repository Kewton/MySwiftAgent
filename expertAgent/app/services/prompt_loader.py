"""Prompt loader service with YAML support and caching.

Provides functionality to load prompts from YAML files with:
- Default fallback (default.yaml)
- Version specification
- Caching for performance
"""

import logging
from pathlib import Path
from typing import Any, Optional

import yaml

from app.services.prompt_cache import PromptCache

logger = logging.getLogger(__name__)


class PromptNotFoundError(Exception):
    """Exception raised when prompt cannot be found."""

    pass


class PromptLoader:
    """Load prompts from YAML files with caching."""

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
            base_dir = Path(__file__).parent.parent.parent / "prompts"

        self.base_dir = Path(base_dir)
        self.enable_cache = enable_cache
        self._cache = PromptCache() if enable_cache else None

    def load_prompt(
        self,
        prompt_name: str,
        version: Optional[str] = None,
    ) -> dict[str, Any]:
        """Load a prompt from YAML file.

        Args:
            prompt_name: Name of the prompt (directory name)
            version: Optional version name (defaults to "default")

        Returns:
            Loaded prompt data

        Raises:
            PromptNotFoundError: If prompt or version not found
        """
        # Default to "default" version
        version = version or "default"

        # Check cache first
        if self._cache is not None:
            cache_key = self._cache.make_key(prompt_name, version)
            cached = self._cache.get(cache_key)
            if cached is not None:
                logger.debug(f"Cache hit for {cache_key}")
                return cached

        # Load from file
        prompt_dir = self.base_dir / prompt_name
        if not prompt_dir.exists():
            raise PromptNotFoundError(f"Prompt directory not found: {prompt_dir}")

        yaml_file = prompt_dir / f"{version}.yaml"
        if not yaml_file.exists():
            raise PromptNotFoundError(
                f"Prompt file not found: {yaml_file} (version: {version})"
            )

        # Load YAML
        try:
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                raise PromptNotFoundError(
                    f"Invalid YAML format in {yaml_file}: expected dict, got {type(data)}"
                )

            # Cache if enabled
            if self._cache is not None:
                cache_key = self._cache.make_key(prompt_name, version)
                self._cache.set(cache_key, data)
                logger.debug(f"Cached {cache_key}")

            logger.info(f"Loaded prompt: {prompt_name} (version: {version})")
            return data

        except yaml.YAMLError as e:
            raise PromptNotFoundError(f"Failed to parse YAML in {yaml_file}: {e}") from e

    def list_versions(self, prompt_name: str) -> list[str]:
        """List all available versions for a prompt.

        Args:
            prompt_name: Name of the prompt

        Returns:
            List of version names (without .yaml extension)
        """
        prompt_dir = self.base_dir / prompt_name
        if not prompt_dir.exists():
            return []

        # Find all .yaml files
        yaml_files = prompt_dir.glob("*.yaml")
        versions = [f.stem for f in yaml_files]

        return sorted(versions)

    def clear_cache(self) -> None:
        """Clear the entire cache."""
        if self._cache is not None:
            self._cache.clear()
            logger.info("Prompt cache cleared")
