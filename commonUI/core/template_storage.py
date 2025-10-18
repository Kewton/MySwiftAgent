"""Template storage service for CommonUI.

This module provides functionality to save and load job/scheduler templates
for JobQueue and MyScheduler pages.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, cast


class TemplateStorage:
    """Template storage service."""

    def __init__(self, storage_dir: str | None = None) -> None:
        """Initialize template storage.

        Args:
            storage_dir: Directory to store template files.
                        If None, automatically determines based on environment:
                        - Docker: /app/data/templates (mapped to docker-compose-data/commonUI)
                        - Script: ./data/templates (local development)
        """
        if storage_dir is None:
            # Auto-detect environment
            if os.getenv("JOBQUEUE_API_URL") and "jobqueue:8000" in os.getenv(
                "JOBQUEUE_API_URL",
                "",
            ):
                # Running in docker-compose (internal service URLs)
                storage_dir = "/app/data/templates"
            else:
                # Running via script (local development)
                storage_dir = "data/templates"

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_template_file(self, service_name: str) -> Path:
        """Get template file path for a service.

        Args:
            service_name: Service name (e.g., 'jobqueue', 'myscheduler')

        Returns:
            Path to template file
        """
        return self.storage_dir / f"{service_name}_templates.json"

    def save_template(
        self,
        service_name: str,
        template_name: str,
        template_data: dict[str, Any],
    ) -> None:
        """Save a template.

        Args:
            service_name: Service name (e.g., 'jobqueue', 'myscheduler')
            template_name: Template name
            template_data: Template data dictionary
        """
        file_path = self._get_template_file(service_name)

        # Load existing templates
        templates = self.load_all_templates(service_name)

        # Add/update template with metadata
        templates[template_name] = {
            "data": template_data,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        # Save to file
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(templates, f, indent=2, ensure_ascii=False)

    def load_template(
        self,
        service_name: str,
        template_name: str,
    ) -> dict[str, Any] | None:
        """Load a specific template.

        Args:
            service_name: Service name (e.g., 'jobqueue', 'myscheduler')
            template_name: Template name

        Returns:
            Template data or None if not found
        """
        templates = self.load_all_templates(service_name)
        template = templates.get(template_name)
        return template["data"] if template else None

    def load_all_templates(self, service_name: str) -> dict[str, Any]:
        """Load all templates for a service.

        Args:
            service_name: Service name (e.g., 'jobqueue', 'myscheduler')

        Returns:
            Dictionary of templates
        """
        file_path = self._get_template_file(service_name)

        if not file_path.exists():
            return {}

        try:
            with file_path.open(encoding="utf-8") as f:
                return cast("dict[str, Any]", json.load(f))
        except json.JSONDecodeError:
            return {}

    def delete_template(self, service_name: str, template_name: str) -> bool:
        """Delete a template.

        Args:
            service_name: Service name (e.g., 'jobqueue', 'myscheduler')
            template_name: Template name

        Returns:
            True if deleted, False if not found
        """
        file_path = self._get_template_file(service_name)

        if not file_path.exists():
            return False

        templates = self.load_all_templates(service_name)

        if template_name in templates:
            del templates[template_name]

            # Save updated templates
            with file_path.open("w", encoding="utf-8") as f:
                json.dump(templates, f, indent=2, ensure_ascii=False)

            return True

        return False

    def list_template_names(self, service_name: str) -> list[str]:
        """List all template names for a service.

        Args:
            service_name: Service name (e.g., 'jobqueue', 'myscheduler')

        Returns:
            List of template names
        """
        templates = self.load_all_templates(service_name)
        return sorted(templates.keys())
