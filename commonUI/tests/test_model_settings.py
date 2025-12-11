"""Unit tests for model settings loader.

Issue #269: LLM model settings management via MyVault.
"""

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
import yaml

from core.model_settings import (
    ModelSettingsLoader,
    get_model_display_name,
)

# Sample test configuration
SAMPLE_CONFIG: dict[str, Any] = {
    "providers": {
        "claude": {
            "name": "Anthropic Claude",
            "models": [
                {
                    "id": "claude-haiku-4-5",
                    "name": "Claude Haiku 4.5",
                    "description": "Fast and cost-effective",
                    "context_window": 200000,
                    "cost_tier": "low",
                },
                {
                    "id": "claude-sonnet-4-20250514",
                    "name": "Claude Sonnet 4",
                    "description": "Balanced performance",
                    "context_window": 200000,
                    "cost_tier": "medium",
                },
            ],
        },
        "gemini": {
            "name": "Google Gemini",
            "models": [
                {
                    "id": "gemini-2.0-flash",
                    "name": "Gemini 2.0 Flash",
                    "description": "Fast responses",
                    "context_window": 1000000,
                    "cost_tier": "low",
                },
            ],
        },
    },
    "settings_categories": {
        "chat": {
            "name": "Chat & Conversation",
            "description": "Models for conversational interactions",
            "recommended_models": ["gemini-2.0-flash", "claude-haiku-4-5"],
            "settings": [
                {
                    "key": "CHAT_CLARIFICATION_MODEL",
                    "name": "Chat Clarification Model",
                    "description": "Model for requirement clarification",
                    "default": "gemini-2.0-flash",
                },
            ],
        },
        "job_generator": {
            "name": "Job Generator",
            "description": "Models for job generation",
            "recommended_models": ["claude-haiku-4-5"],
            "settings": [
                {
                    "key": "JOB_GENERATOR_EVALUATOR_MODEL",
                    "name": "Evaluator Model",
                    "description": "Model for evaluating jobs",
                    "default": "claude-haiku-4-5",
                },
            ],
        },
    },
}


class TestModelSettingsLoader:
    """Test suite for ModelSettingsLoader class."""

    @pytest.fixture
    def loader_with_config(self, tmp_path: Path) -> ModelSettingsLoader:
        """Create loader with sample config file."""
        config_path = tmp_path / "available_models.yaml"
        with open(config_path, "w") as f:
            yaml.dump(SAMPLE_CONFIG, f)
        return ModelSettingsLoader(config_path)

    @pytest.fixture
    def loader_without_config(self, tmp_path: Path) -> ModelSettingsLoader:
        """Create loader with non-existent config file."""
        config_path = tmp_path / "nonexistent.yaml"
        return ModelSettingsLoader(config_path)

    def test_load_config_success(self, loader_with_config: ModelSettingsLoader) -> None:
        """Test: 設定ファイルの正常読み込み."""
        models = loader_with_config.get_all_models()
        assert len(models) == 3  # 2 claude + 1 gemini

    def test_load_config_file_not_found(
        self,
        loader_without_config: ModelSettingsLoader,
    ) -> None:
        """Test: 設定ファイルが存在しない場合は空のconfig."""
        models = loader_without_config.get_all_models()
        assert models == []

    def test_get_all_models(self, loader_with_config: ModelSettingsLoader) -> None:
        """Test: 全モデル取得."""
        models = loader_with_config.get_all_models()

        # Check structure
        assert all("provider" in m for m in models)
        assert all("provider_name" in m for m in models)
        assert all("id" in m for m in models)
        assert all("name" in m for m in models)

        # Check content
        model_ids = [m["id"] for m in models]
        assert "claude-haiku-4-5" in model_ids
        assert "claude-sonnet-4-20250514" in model_ids
        assert "gemini-2.0-flash" in model_ids

    def test_get_models_by_provider(
        self,
        loader_with_config: ModelSettingsLoader,
    ) -> None:
        """Test: プロバイダ別モデル取得."""
        claude_models = loader_with_config.get_models_by_provider("claude")
        assert len(claude_models) == 2

        gemini_models = loader_with_config.get_models_by_provider("gemini")
        assert len(gemini_models) == 1

        unknown_models = loader_with_config.get_models_by_provider("unknown")
        assert unknown_models == []

    def test_get_model_ids(self, loader_with_config: ModelSettingsLoader) -> None:
        """Test: モデルID一覧取得."""
        ids = loader_with_config.get_model_ids()
        assert set(ids) == {
            "claude-haiku-4-5",
            "claude-sonnet-4-20250514",
            "gemini-2.0-flash",
        }

    def test_get_settings_categories(
        self,
        loader_with_config: ModelSettingsLoader,
    ) -> None:
        """Test: 設定カテゴリ取得."""
        categories = loader_with_config.get_settings_categories()
        assert "chat" in categories
        assert "job_generator" in categories

    def test_get_settings_by_category(
        self,
        loader_with_config: ModelSettingsLoader,
    ) -> None:
        """Test: カテゴリ別設定取得."""
        chat_settings = loader_with_config.get_settings_by_category("chat")
        assert len(chat_settings) == 1
        assert chat_settings[0]["key"] == "CHAT_CLARIFICATION_MODEL"

    def test_get_all_settings(self, loader_with_config: ModelSettingsLoader) -> None:
        """Test: 全設定取得."""
        settings = loader_with_config.get_all_settings()
        assert len(settings) == 2  # 1 chat + 1 job_generator

        keys = [s["key"] for s in settings]
        assert "CHAT_CLARIFICATION_MODEL" in keys
        assert "JOB_GENERATOR_EVALUATOR_MODEL" in keys

    def test_get_setting_default(self, loader_with_config: ModelSettingsLoader) -> None:
        """Test: 設定のデフォルト値取得."""
        default = loader_with_config.get_setting_default("CHAT_CLARIFICATION_MODEL")
        assert default == "gemini-2.0-flash"

        unknown = loader_with_config.get_setting_default("UNKNOWN_MODEL")
        assert unknown is None

    def test_get_recommended_models(
        self,
        loader_with_config: ModelSettingsLoader,
    ) -> None:
        """Test: カテゴリの推奨モデル取得."""
        recommended = loader_with_config.get_recommended_models("chat")
        assert "gemini-2.0-flash" in recommended
        assert "claude-haiku-4-5" in recommended


class TestHelperFunctions:
    """Test suite for helper functions."""

    @pytest.fixture
    def mock_loader(self, tmp_path: Path) -> None:
        """Setup mock loader."""
        config_path = tmp_path / "available_models.yaml"
        with open(config_path, "w") as f:
            yaml.dump(SAMPLE_CONFIG, f)

        # Patch the global loader
        with patch(
            "core.model_settings.model_settings_loader",
            ModelSettingsLoader(config_path),
        ):
            yield

    def test_get_model_options(self, mock_loader: None) -> None:
        """Test: Streamlit selectbox用オプション取得."""
        from core.model_settings import model_settings_loader

        # Create fresh loader with test config
        options = [
            (m["id"], f"{m['provider_name']}: {m['name']}")
            for m in model_settings_loader.get_all_models()
        ]

        # Verify format
        for model_id, display in options:
            assert isinstance(model_id, str)
            assert isinstance(display, str)
            assert ":" in display  # "Provider: Model Name" format

    def test_get_model_display_name(self, mock_loader: None) -> None:
        """Test: モデルIDから表示名取得."""
        from core.model_settings import model_settings_loader

        models = model_settings_loader.get_all_models()
        if models:
            model_id = models[0]["id"]
            display_name = get_model_display_name(model_id)
            assert ":" in display_name

        # Unknown model returns ID
        unknown_display = get_model_display_name("unknown-model")
        assert unknown_display == "unknown-model"


class TestYAMLConfigIntegrity:
    """Test suite for YAML configuration file integrity."""

    def test_actual_config_file_loads(self) -> None:
        """Test: 実際の設定ファイルが読み込める."""
        config_path = Path(__file__).parent.parent / "config" / "available_models.yaml"
        if config_path.exists():
            loader = ModelSettingsLoader(config_path)
            models = loader.get_all_models()

            # Should have at least some models
            assert len(models) > 0

            # All models should have required fields
            for model in models:
                assert "id" in model
                assert "name" in model

    def test_all_default_models_exist(self) -> None:
        """Test: 全設定のデフォルトモデルが存在する."""
        config_path = Path(__file__).parent.parent / "config" / "available_models.yaml"
        if config_path.exists():
            loader = ModelSettingsLoader(config_path)
            model_ids = set(loader.get_model_ids())
            settings = loader.get_all_settings()

            for setting in settings:
                default = setting.get("default")
                if default:
                    assert default in model_ids, (
                        f"Default model '{default}' for '{setting['key']}' not found in available models"
                    )
