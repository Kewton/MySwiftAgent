"""Prompt Management Service.

Issue #191: Prompts Management API Implementation
Service layer for managing prompt templates and versions.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from app.schemas.prompts import (
    PromptListResponse,
    PromptTemplate,
    PromptVersion,
)
from app.services.prompt_loader import PromptLoader

logger = logging.getLogger(__name__)


class PromptManagementService:
    """Service for managing prompt templates.

    This service provides methods to list and retrieve prompt templates
    with their versions and metadata. It leverages the existing PromptLoader
    for loading prompt content from YAML files.
    """

    def __init__(
        self,
        prompt_loader: PromptLoader | None = None,
        base_dir: Path | None = None,
    ) -> None:
        """Initialize the PromptManagementService.

        Args:
            prompt_loader: Optional custom PromptLoader instance
            base_dir: Optional base directory for prompts (defaults to expertAgent/prompts)
        """
        if base_dir is not None:
            self._base_dir = base_dir
            self._prompt_loader = PromptLoader(base_dir=base_dir)
        elif prompt_loader is not None:
            self._prompt_loader = prompt_loader
            self._base_dir = prompt_loader.base_dir
        else:
            self._prompt_loader = PromptLoader.create_default()
            self._base_dir = self._prompt_loader.base_dir

        logger.info(f"PromptManagementService initialized (base_dir={self._base_dir})")

    def get_prompts(self) -> PromptListResponse:
        """Get all available prompt templates.

        Returns:
            PromptListResponse containing list of all prompts and total count
        """
        prompts: list[PromptTemplate] = []

        if not self._base_dir.exists():
            logger.warning(f"Prompts directory not found: {self._base_dir}")
            return PromptListResponse(items=[], total=0)

        # Iterate through prompt directories
        for item in sorted(self._base_dir.iterdir()):
            if not item.is_dir():
                continue

            prompt_id = item.name
            template = self._build_prompt_template(prompt_id, item)
            if template is not None:
                prompts.append(template)

        logger.info(f"Found {len(prompts)} prompt templates")
        return PromptListResponse(items=prompts, total=len(prompts))

    def get_prompt(self, prompt_id: str) -> PromptTemplate | None:
        """Get a specific prompt template by ID.

        Args:
            prompt_id: The prompt identifier (directory name)

        Returns:
            PromptTemplate if found, None otherwise
        """
        prompt_dir = self._base_dir / prompt_id

        if not prompt_dir.exists() or not prompt_dir.is_dir():
            logger.debug(f"Prompt not found: {prompt_id}")
            return None

        return self._build_prompt_template(prompt_id, prompt_dir)

    def _build_prompt_template(
        self, prompt_id: str, prompt_dir: Path
    ) -> PromptTemplate | None:
        """Build a PromptTemplate from a prompt directory.

        Args:
            prompt_id: The prompt identifier
            prompt_dir: Path to the prompt directory

        Returns:
            PromptTemplate or None if directory is invalid
        """
        versions = self._load_versions(prompt_id, prompt_dir)

        if not versions:
            logger.debug(f"No valid versions found for prompt: {prompt_id}")
            return None

        # Extract metadata from the default version
        default_version = next((v for v in versions if v.id == "default"), versions[0])

        # Try to get description from YAML content
        description = self._extract_description(prompt_dir)
        category = self._extract_category(prompt_dir)

        # Determine current version (prefer default, otherwise first)
        current_version = default_version.version

        return PromptTemplate(
            id=prompt_id,
            name=self._format_name(prompt_id),
            description=description,
            category=category,
            current_version=current_version,
            versions=versions,
            created_at=self._get_directory_creation_time(prompt_dir),
            updated_at=self._get_directory_modification_time(prompt_dir),
        )

    def _load_versions(self, prompt_id: str, prompt_dir: Path) -> list[PromptVersion]:
        """Load all versions of a prompt.

        Args:
            prompt_id: The prompt identifier
            prompt_dir: Path to the prompt directory

        Returns:
            List of PromptVersion objects
        """
        versions: list[PromptVersion] = []
        version_names = self._prompt_loader.list_versions(prompt_id)

        for idx, version_name in enumerate(version_names, start=1):
            try:
                yaml_file = prompt_dir / f"{version_name}.yaml"
                if not yaml_file.exists():
                    continue

                content = self._read_yaml_as_string(yaml_file)
                yaml_data = self._load_yaml_file(yaml_file)

                # Determine version number
                version_num = idx
                if version_name == "default":
                    version_num = 1

                version = PromptVersion(
                    id=version_name,
                    version=version_num,
                    content=content,
                    description=yaml_data.get("description"),
                    created_at=self._get_file_creation_time(yaml_file),
                    is_active=version_name == "default",
                )
                versions.append(version)

            except Exception as e:
                logger.warning(
                    f"Failed to load version {version_name} for {prompt_id}: {e}"
                )
                continue

        return versions

    def _read_yaml_as_string(self, yaml_file: Path) -> str:
        """Read YAML file content as string.

        Args:
            yaml_file: Path to the YAML file

        Returns:
            File content as string
        """
        try:
            with open(yaml_file, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Failed to read file {yaml_file}: {e}")
            return ""

    def _load_yaml_file(self, yaml_file: Path) -> dict[str, Any]:
        """Load and parse YAML file.

        Args:
            yaml_file: Path to the YAML file

        Returns:
            Parsed YAML content as dictionary
        """
        try:
            with open(yaml_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.error(f"Failed to parse YAML {yaml_file}: {e}")
            return {}

    def _extract_description(self, prompt_dir: Path) -> str | None:
        """Extract description from the default YAML file.

        Args:
            prompt_dir: Path to the prompt directory

        Returns:
            Description string or None
        """
        default_yaml = prompt_dir / "default.yaml"
        if default_yaml.exists():
            data = self._load_yaml_file(default_yaml)
            return data.get("description") or data.get("purpose")
        return None

    def _extract_category(self, prompt_dir: Path) -> str | None:
        """Extract category from the default YAML file.

        Args:
            prompt_dir: Path to the prompt directory

        Returns:
            Category string or None
        """
        default_yaml = prompt_dir / "default.yaml"
        if default_yaml.exists():
            data = self._load_yaml_file(default_yaml)
            return data.get("agent_type")
        return None

    def _format_name(self, prompt_id: str) -> str:
        """Format prompt ID as display name.

        Args:
            prompt_id: The prompt identifier (e.g., 'requirement_clarification')

        Returns:
            Formatted display name (e.g., 'Requirement Clarification')
        """
        return prompt_id.replace("_", " ").title()

    def _get_creation_time(self, path: Path) -> datetime | None:
        """Get creation timestamp for a file or directory.

        Uses birth time if available (macOS), otherwise falls back to ctime.

        Args:
            path: Path to the file or directory

        Returns:
            Creation datetime or None if path doesn't exist or access fails
        """
        try:
            stat = path.stat()
            # Use birth time if available (macOS), otherwise modification time
            ctime = getattr(stat, "st_birthtime", stat.st_ctime)
            return datetime.fromtimestamp(ctime)
        except (OSError, ValueError) as e:
            logger.debug(f"Failed to get creation time for {path}: {e}")
            return None

    def _get_modification_time(self, path: Path) -> datetime | None:
        """Get last modification timestamp for a file or directory.

        Args:
            path: Path to the file or directory

        Returns:
            Modification datetime or None if path doesn't exist or access fails
        """
        try:
            stat = path.stat()
            return datetime.fromtimestamp(stat.st_mtime)
        except (OSError, ValueError) as e:
            logger.debug(f"Failed to get modification time for {path}: {e}")
            return None

    # Aliases for backward compatibility and semantic clarity
    def _get_directory_creation_time(self, path: Path) -> datetime | None:
        """Get directory creation timestamp (alias for _get_creation_time)."""
        return self._get_creation_time(path)

    def _get_directory_modification_time(self, path: Path) -> datetime | None:
        """Get directory modification timestamp (alias for _get_modification_time)."""
        return self._get_modification_time(path)

    def _get_file_creation_time(self, path: Path) -> datetime | None:
        """Get file creation timestamp (alias for _get_creation_time)."""
        return self._get_creation_time(path)
