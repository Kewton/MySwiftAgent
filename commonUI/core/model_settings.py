"""Model settings loader for LLM configuration.

Issue #269: LLM model settings management via MyVault.

This module provides:
- YAML configuration loading for available models
- Model list retrieval by provider and category
- Setting definitions with defaults
"""

import logging
from pathlib import Path
from typing import Any, cast

import yaml

logger = logging.getLogger(__name__)


class ModelSettingsLoader:
    """Loader for LLM model configuration from YAML file."""

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize the model settings loader.

        Args:
            config_path: Path to the YAML configuration file.
                        Defaults to config/available_models.yaml
        """
        if config_path is None:
            # Try Docker path first, then local development path
            docker_path = Path("/app/config/available_models.yaml")
            local_path = (
                Path(__file__).parent.parent / "config" / "available_models.yaml"
            )

            config_path = docker_path if docker_path.exists() else local_path

        self.config_path = config_path
        self._config: dict[str, Any] | None = None

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from YAML file.

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid YAML
        """
        if self._config is not None:
            return self._config

        if not self.config_path.exists():
            logger.warning(
                "Model settings config not found at %s, using empty config",
                self.config_path,
            )
            return {"providers": {}, "settings_categories": {}}

        try:
            with open(self.config_path) as f:
                self._config = cast("dict[str, Any]", yaml.safe_load(f))
                return self._config or {"providers": {}, "settings_categories": {}}
        except yaml.YAMLError:
            logger.exception("Failed to parse model settings config")
            return {"providers": {}, "settings_categories": {}}

    def get_all_models(self) -> list[dict[str, Any]]:
        """Get all available models across all providers.

        Returns:
            List of model dictionaries with provider information
        """
        config = self._load_config()
        models: list[dict[str, Any]] = []

        for provider_id, provider_data in config.get("providers", {}).items():
            for model in provider_data.get("models", []):
                models.append(
                    {
                        "provider": provider_id,
                        "provider_name": provider_data.get("name", provider_id),
                        **model,
                    },
                )

        return models

    def get_models_by_provider(self, provider: str) -> list[dict[str, Any]]:
        """Get models for a specific provider.

        Args:
            provider: Provider ID (e.g., "claude", "gemini", "gpt")

        Returns:
            List of model dictionaries for the provider
        """
        config = self._load_config()
        provider_data = config.get("providers", {}).get(provider, {})
        models: list[dict[str, Any]] = provider_data.get("models", [])
        return models

    def get_model_ids(self) -> list[str]:
        """Get list of all model IDs.

        Returns:
            List of model ID strings
        """
        models = self.get_all_models()
        return [m["id"] for m in models]

    def get_settings_categories(self) -> dict[str, Any]:
        """Get all settings categories.

        Returns:
            Dictionary of category ID to category data
        """
        config = self._load_config()
        categories: dict[str, Any] = config.get("settings_categories", {})
        return categories

    def get_settings_by_category(self, category: str) -> list[dict[str, Any]]:
        """Get settings for a specific category.

        Args:
            category: Category ID (e.g., "chat", "job_generator", "workflow")

        Returns:
            List of setting dictionaries
        """
        categories = self.get_settings_categories()
        category_data = categories.get(category, {})
        settings: list[dict[str, Any]] = category_data.get("settings", [])
        return settings

    def get_all_settings(self) -> list[dict[str, Any]]:
        """Get all model settings across all categories.

        Returns:
            List of setting dictionaries with category information
        """
        categories = self.get_settings_categories()
        settings: list[dict[str, Any]] = []

        for category_id, category_data in categories.items():
            for setting in category_data.get("settings", []):
                settings.append(
                    {
                        "category": category_id,
                        "category_name": category_data.get("name", category_id),
                        **setting,
                    },
                )

        return settings

    def get_setting_default(self, key: str) -> str | None:
        """Get the default value for a setting.

        Args:
            key: Setting key (e.g., "CHAT_CLARIFICATION_MODEL")

        Returns:
            Default model ID or None if not found
        """
        settings = self.get_all_settings()
        for setting in settings:
            if setting.get("key") == key:
                return setting.get("default")
        return None

    def get_recommended_models(self, category: str) -> list[str]:
        """Get recommended model IDs for a category.

        Args:
            category: Category ID

        Returns:
            List of recommended model IDs
        """
        categories = self.get_settings_categories()
        category_data = categories.get(category, {})
        recommended: list[str] = category_data.get("recommended_models", [])
        return recommended


# Global instance for convenience
model_settings_loader = ModelSettingsLoader()


def get_model_options() -> list[tuple[str, str]]:
    """Get model options for Streamlit selectbox.

    Returns:
        List of (model_id, display_name) tuples
    """
    models = model_settings_loader.get_all_models()
    return [(m["id"], f"{m['provider_name']}: {m['name']}") for m in models]


def get_model_display_name(model_id: str) -> str:
    """Get display name for a model ID.

    Args:
        model_id: Model ID string

    Returns:
        Display name or the ID if not found
    """
    models = model_settings_loader.get_all_models()
    for m in models:
        if m["id"] == model_id:
            return f"{m['provider_name']}: {m['name']}"
    return model_id
