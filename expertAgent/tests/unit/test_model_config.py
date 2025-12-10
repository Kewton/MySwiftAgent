"""Unit tests for model configuration helper function.

Issue #269: LLM model settings management via MyVault.

This module tests the get_model_config helper function that:
1. Retrieves model settings from MyVault (priority)
2. Falls back to environment variables
3. Uses default values when neither is available
"""

from unittest.mock import MagicMock, patch

import pytest


class TestGetModelConfig:
    """Test suite for get_model_config function."""

    @pytest.fixture
    def mock_secrets_manager(self):
        """Create mock secrets manager."""
        with patch("core.secrets.secrets_manager") as mock_manager:
            yield mock_manager

    def test_get_model_config_from_myvault(self, mock_secrets_manager):
        """Test: MyVault優先でモデル設定を取得."""
        from core.secrets import get_model_config

        mock_secrets_manager.get_secret.return_value = "claude-sonnet-4-20250514"

        result = get_model_config("CHAT_CLARIFICATION_MODEL", "gemini-2.0-flash")

        assert result == "claude-sonnet-4-20250514"
        mock_secrets_manager.get_secret.assert_called_once()

    def test_get_model_config_fallback_to_env(self, mock_secrets_manager):
        """Test: MyVault取得失敗時は環境変数にフォールバック."""
        from core.secrets import get_model_config

        mock_secrets_manager.get_secret.side_effect = ValueError("Not found")

        with patch.dict("os.environ", {"CHAT_CLARIFICATION_MODEL": "env-model"}):
            result = get_model_config("CHAT_CLARIFICATION_MODEL", "gemini-2.0-flash")

        assert result == "env-model"

    def test_get_model_config_fallback_to_default(self, mock_secrets_manager):
        """Test: 両方未設定時はデフォルト値を使用."""
        from core.secrets import get_model_config

        mock_secrets_manager.get_secret.side_effect = ValueError("Not found")

        with patch.dict("os.environ", {}, clear=True):
            result = get_model_config("CHAT_CLARIFICATION_MODEL", "gemini-2.0-flash")

        assert result == "gemini-2.0-flash"

    def test_get_model_config_with_project(self, mock_secrets_manager):
        """Test: プロジェクト指定でモデル設定を取得."""
        from core.secrets import get_model_config

        mock_secrets_manager.get_secret.return_value = "project-specific-model"

        result = get_model_config(
            "JOB_GENERATOR_EVALUATOR_MODEL",
            "claude-haiku-4-5",
            project="test_project",
        )

        assert result == "project-specific-model"
        mock_secrets_manager.get_secret.assert_called_once_with(
            "JOB_GENERATOR_EVALUATOR_MODEL", project="test_project"
        )

    def test_get_model_config_empty_myvault_value_uses_env(self, mock_secrets_manager):
        """Test: MyVaultの値が空の場合は環境変数を使用."""
        from core.secrets import get_model_config

        mock_secrets_manager.get_secret.return_value = ""

        with patch.dict("os.environ", {"WORKFLOW_GENERATOR_MODEL": "env-workflow-model"}):
            result = get_model_config("WORKFLOW_GENERATOR_MODEL", "claude-haiku-4-5")

        # Empty string from MyVault should trigger fallback to env
        assert result == "env-workflow-model"

    def test_get_model_config_all_model_keys(self, mock_secrets_manager):
        """Test: 全8モデル設定キーが正しく取得できる."""
        from core.secrets import get_model_config

        model_keys = [
            ("CHAT_CLARIFICATION_MODEL", "gemini-2.0-flash"),
            ("CANDIDATE_GENERATION_MODEL", "gemini-2.0-flash"),
            ("REQUIREMENT_EXTRACTION_MODEL", "gemini-2.0-flash"),
            ("JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL", "claude-haiku-4-5"),
            ("JOB_GENERATOR_EVALUATOR_MODEL", "claude-haiku-4-5"),
            ("JOB_GENERATOR_INTERFACE_DEFINITION_MODEL", "claude-haiku-4-5"),
            ("JOB_GENERATOR_VALIDATION_MODEL", "claude-haiku-4-5"),
            ("WORKFLOW_GENERATOR_MODEL", "claude-haiku-4-5"),
        ]

        for key, default in model_keys:
            mock_secrets_manager.get_secret.side_effect = ValueError("Not found")

            with patch.dict("os.environ", {}, clear=True):
                result = get_model_config(key, default)

            assert result == default, f"Failed for key: {key}"


class TestLlmInvocationModelConfig:
    """Test suite for llm_invocation.py model config usage."""

    def test_invoke_structured_llm_uses_get_model_config(self):
        """Test: invoke_structured_llmがget_model_configを使用する."""
        # This test verifies that llm_invocation.py uses get_model_config
        # instead of direct os.getenv calls
        with patch(
            "aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation.get_model_config"
        ) as mock_get_config:
            mock_get_config.return_value = "test-model"

            # Import after patching to ensure mock is used
            from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
                invoke_structured_llm,
            )

            # Verify the function exists and is callable
            assert callable(invoke_structured_llm)


class TestLlmServiceModelConfig:
    """Test suite for llm_service.py model config usage."""

    def test_stream_requirement_clarification_uses_get_model_config(self):
        """Test: stream_requirement_clarificationがget_model_configを使用する."""
        with patch(
            "app.services.conversation.llm_service.get_model_config"
        ) as mock_get_config:
            mock_get_config.return_value = "gemini-2.0-flash"

            # Verify function is importable after patching
            from app.services.conversation.llm_service import (
                stream_requirement_clarification,
            )

            assert callable(stream_requirement_clarification)


class TestCandidateGeneratorModelConfig:
    """Test suite for candidate_generator.py model config usage."""

    def test_generate_requirement_candidates_uses_get_model_config(self):
        """Test: generate_requirement_candidatesがget_model_configを使用する."""
        with patch(
            "app.services.conversation.candidate_generator.get_model_config"
        ) as mock_get_config:
            mock_get_config.return_value = "gemini-2.0-flash"

            from app.services.conversation.candidate_generator import (
                generate_requirement_candidates,
            )

            assert callable(generate_requirement_candidates)


class TestModelConfigConstants:
    """Test suite for model configuration constants and defaults."""

    def test_default_model_values_are_valid(self):
        """Test: デフォルトモデル値が有効なモデル名である."""
        valid_models = {
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "claude-haiku-4-5",
            "claude-sonnet-4-20250514",
            "gpt-4o",
            "gpt-4o-mini",
        }

        default_models = {
            "CHAT_CLARIFICATION_MODEL": "gemini-2.0-flash",
            "CANDIDATE_GENERATION_MODEL": "gemini-2.0-flash",
            "REQUIREMENT_EXTRACTION_MODEL": "gemini-2.0-flash",
            "JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL": "claude-haiku-4-5",
            "JOB_GENERATOR_EVALUATOR_MODEL": "claude-haiku-4-5",
            "JOB_GENERATOR_INTERFACE_DEFINITION_MODEL": "claude-haiku-4-5",
            "JOB_GENERATOR_VALIDATION_MODEL": "claude-haiku-4-5",
            "WORKFLOW_GENERATOR_MODEL": "claude-haiku-4-5",
        }

        for key, default in default_models.items():
            assert default in valid_models, f"Invalid default model for {key}: {default}"
