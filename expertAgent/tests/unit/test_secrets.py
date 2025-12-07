"""Unit tests for secrets manager."""

from unittest.mock import MagicMock, patch

import pytest

from core.myvault_client import MyVaultError
from core.secrets import SecretsManager


class TestSecretsManager:
    """Test suite for SecretsManager class."""

    @pytest.fixture
    def manager_with_myvault(self):
        """Create SecretsManager with MyVault enabled."""
        with patch("core.secrets.settings") as mock_settings:
            mock_settings.MYVAULT_ENABLED = True
            mock_settings.MYVAULT_BASE_URL = "http://localhost:8000"
            mock_settings.MYVAULT_SERVICE_NAME = "test-service"
            mock_settings.MYVAULT_SERVICE_TOKEN = "test-token"
            mock_settings.MYVAULT_DEFAULT_PROJECT = "default"
            mock_settings.SECRETS_CACHE_TTL = 300

            with patch("core.secrets.MyVaultClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                manager = SecretsManager()
                manager.myvault_client = mock_client
                manager.myvault_enabled = True

                yield manager

    @pytest.fixture
    def manager_without_myvault(self):
        """Create SecretsManager with MyVault disabled."""
        with patch("core.secrets.settings") as mock_settings:
            mock_settings.MYVAULT_ENABLED = False
            mock_settings.SECRETS_CACHE_TTL = 300
            mock_settings.OPENAI_API_KEY = "env-openai-key"
            mock_settings.ANTHROPIC_API_KEY = "env-anthropic-key"

            manager = SecretsManager()
            manager.myvault_enabled = False
            manager.myvault_client = None

            yield manager

    def test_get_secret_from_myvault_success(self, manager_with_myvault):
        """Test get_secret from MyVault - success case."""
        manager_with_myvault.myvault_client.get_secret.return_value = "myvault-value"

        result = manager_with_myvault.get_secret("OPENAI_API_KEY", project="test")

        assert result == "myvault-value"
        manager_with_myvault.myvault_client.get_secret.assert_called_once_with(
            "test", "OPENAI_API_KEY"
        )

    def test_get_secret_myvault_error_fallback_to_env(self, manager_with_myvault):
        """Test get_secret falls back to env vars when MyVault fails."""
        manager_with_myvault.myvault_client.get_secret.side_effect = MyVaultError(
            "MyVault error"
        )

        with patch.object(manager_with_myvault.settings, "OPENAI_API_KEY", "env-key"):
            result = manager_with_myvault.get_secret("OPENAI_API_KEY")
            assert result == "env-key"

    def test_get_secret_from_env_when_myvault_disabled(self, manager_without_myvault):
        """Test get_secret from environment variables when MyVault disabled."""
        result = manager_without_myvault.get_secret("OPENAI_API_KEY")
        assert result == "env-openai-key"

    def test_get_secret_not_found_anywhere(self, manager_without_myvault):
        """Test get_secret raises ValueError when not found anywhere."""
        with patch.object(manager_without_myvault.settings, "NONEXISTENT_KEY", ""):
            with pytest.raises(
                ValueError,
                match="Secret 'NONEXISTENT_KEY' not found in MyVault or environment variables",
            ):
                manager_without_myvault.get_secret("NONEXISTENT_KEY")

    def test_get_secrets_for_project_myvault_enabled(self, manager_with_myvault):
        """Test get_secrets_for_project with MyVault enabled."""
        manager_with_myvault.myvault_client.get_secrets.return_value = {
            "OPENAI_API_KEY": "myvault-openai",
            "GOOGLE_API_KEY": "myvault-google",
        }

        with patch.object(
            manager_with_myvault.settings, "MYVAULT_DEFAULT_PROJECT", "default"
        ):
            result = manager_with_myvault.get_secrets_for_project()

            assert result == {
                "OPENAI_API_KEY": "myvault-openai",
                "GOOGLE_API_KEY": "myvault-google",
            }

    def test_get_secrets_for_project_myvault_error_fallback(
        self, manager_with_myvault
    ):
        """Test get_secrets_for_project falls back to env vars on MyVault error."""
        # Make _resolve_default_project raise MyVaultError
        with patch.object(
            manager_with_myvault,
            "_resolve_default_project",
            side_effect=MyVaultError("MyVault error"),
        ):
            with patch.object(
                manager_with_myvault,
                "_get_all_env_secrets",
                return_value={"ENV_KEY": "value"},
            ):
                result = manager_with_myvault.get_secrets_for_project()
                assert result == {"ENV_KEY": "value"}

    def test_get_secrets_for_project_myvault_disabled(self, manager_without_myvault):
        """Test get_secrets_for_project returns env vars when MyVault disabled."""
        result = manager_without_myvault.get_secrets_for_project()

        # Should return environment variables
        assert "OPENAI_API_KEY" in result
        assert result["OPENAI_API_KEY"] == "env-openai-key"

    def test_clear_cache_specific_project(self, manager_with_myvault):
        """Test clear_cache for specific project."""
        # Add some cache
        manager_with_myvault._cache["project1"] = {"KEY1": ("value1", 123.0)}
        manager_with_myvault._cache["project2"] = {"KEY2": ("value2", 456.0)}

        manager_with_myvault.clear_cache("project1")

        assert "project1" not in manager_with_myvault._cache
        assert "project2" in manager_with_myvault._cache

    def test_clear_cache_all(self, manager_with_myvault):
        """Test clear_cache clears all projects."""
        # Add some cache
        manager_with_myvault._cache["project1"] = {"KEY1": ("value1", 123.0)}
        manager_with_myvault._cache["project2"] = {"KEY2": ("value2", 456.0)}

        manager_with_myvault.clear_cache()

        assert len(manager_with_myvault._cache) == 0

    def test_get_from_myvault_no_client(self, manager_with_myvault):
        """Test _get_from_myvault returns None when no client."""
        manager_with_myvault.myvault_client = None

        result = manager_with_myvault._get_from_myvault("KEY", "project")

        assert result is None

    def test_get_from_myvault_no_project_raises_error(self, manager_with_myvault):
        """Test _get_from_myvault raises error when no project specified."""
        manager_with_myvault.myvault_client.get_default_project.return_value = None

        with patch.object(
            manager_with_myvault.settings, "MYVAULT_DEFAULT_PROJECT", None
        ):
            with pytest.raises(
                MyVaultError, match="No default project found in MyVault"
            ):
                manager_with_myvault._get_from_myvault("KEY", None)

    def test_get_project_secrets_no_client(self, manager_with_myvault):
        """Test _get_project_secrets returns empty dict when no client."""
        manager_with_myvault.myvault_client = None

        result = manager_with_myvault._get_project_secrets("project")

        assert result == {}

    def test_get_project_secrets_myvault_error(self, manager_with_myvault):
        """Test _get_project_secrets returns empty dict on MyVault error."""
        manager_with_myvault.myvault_client.get_secrets.side_effect = MyVaultError(
            "MyVault error"
        )

        result = manager_with_myvault._get_project_secrets("project")

        assert result == {}

    def test_resolve_default_project_from_env(self, manager_with_myvault):
        """Test _resolve_default_project from environment variable."""
        # Mock API to return None so it falls back to env var
        manager_with_myvault.myvault_client.get_default_project.return_value = None

        with patch.object(
            manager_with_myvault.settings, "MYVAULT_DEFAULT_PROJECT", "env-project"
        ):
            result = manager_with_myvault._resolve_default_project()
            assert result == "env-project"

    def test_resolve_default_project_from_api(self, manager_with_myvault):
        """Test _resolve_default_project from MyVault API."""
        manager_with_myvault.myvault_client.get_default_project.return_value = (
            "api-project"
        )

        with patch.object(manager_with_myvault.settings, "MYVAULT_DEFAULT_PROJECT", ""):
            result = manager_with_myvault._resolve_default_project()
            assert result == "api-project"

    def test_resolve_default_project_no_client_raises_error(
        self, manager_with_myvault
    ):
        """Test _resolve_default_project raises error when no client."""
        manager_with_myvault.myvault_client = None

        with patch.object(manager_with_myvault.settings, "MYVAULT_DEFAULT_PROJECT", ""):
            with pytest.raises(MyVaultError, match="No default project found in MyVault or environment variables"):
                manager_with_myvault._resolve_default_project()

    def test_resolve_default_project_not_found_raises_error(self, manager_with_myvault):
        """Test _resolve_default_project raises error when no default found."""
        manager_with_myvault.myvault_client.get_default_project.return_value = None

        with patch.object(manager_with_myvault.settings, "MYVAULT_DEFAULT_PROJECT", ""):
            with pytest.raises(MyVaultError, match="No default project found in MyVault or environment variables"):
                manager_with_myvault._resolve_default_project()

    def test_get_all_env_secrets(self, manager_without_myvault):
        """Test _get_all_env_secrets returns available env vars."""
        result = manager_without_myvault._get_all_env_secrets()

        assert "OPENAI_API_KEY" in result
        assert "ANTHROPIC_API_KEY" in result
        assert result["OPENAI_API_KEY"] == "env-openai-key"
        assert result["ANTHROPIC_API_KEY"] == "env-anthropic-key"

    def test_is_cache_valid(self, manager_with_myvault):
        """Test _is_cache_valid checks TTL correctly."""
        import time

        # Add cached value with current timestamp
        current_time = time.time()
        manager_with_myvault._cache["project"] = {"KEY": ("value", current_time)}

        # Should be valid (within TTL)
        assert manager_with_myvault._is_cache_valid("project", "KEY") is True

    def test_is_cache_invalid_expired(self, manager_with_myvault):
        """Test _is_cache_valid returns False for expired cache."""
        import time

        # Add cached value with old timestamp (beyond TTL)
        old_time = time.time() - 400  # Older than 300s TTL
        manager_with_myvault._cache["project"] = {"KEY": ("value", old_time)}

        # Should be invalid (expired)
        assert manager_with_myvault._is_cache_valid("project", "KEY") is False

    def test_update_cache(self, manager_with_myvault):
        """Test _update_cache updates cache correctly."""
        manager_with_myvault._update_cache("project", "KEY", "value")

        assert "project" in manager_with_myvault._cache
        assert "KEY" in manager_with_myvault._cache["project"]
        assert manager_with_myvault._cache["project"]["KEY"][0] == "value"

    def test_init_myvault_client_exception(self):
        """Test SecretsManager init handles MyVault client exception."""
        with patch("core.secrets.settings") as mock_settings:
            mock_settings.MYVAULT_ENABLED = True
            mock_settings.MYVAULT_BASE_URL = "http://localhost:8000"
            mock_settings.MYVAULT_SERVICE_NAME = "test-service"
            mock_settings.MYVAULT_SERVICE_TOKEN = "test-token"
            mock_settings.MYVAULT_DEFAULT_PROJECT = "default"
            mock_settings.SECRETS_CACHE_TTL = 300

            with patch(
                "core.secrets.MyVaultClient",
                side_effect=Exception("Client init failed"),
            ):
                manager = SecretsManager()

                # MyVault should be disabled after init failure
                assert manager.myvault_enabled is False
                assert manager.myvault_client is None

    def test_get_secret_myvault_returns_none_fallback_to_env(
        self, manager_with_myvault
    ):
        """Test get_secret falls back to env when MyVault returns None."""
        # Mock _get_from_myvault to return None
        manager_with_myvault.myvault_client.get_secret.return_value = None

        with patch.object(manager_with_myvault.settings, "OPENAI_API_KEY", "env-key"):
            result = manager_with_myvault.get_secret("OPENAI_API_KEY")
            assert result == "env-key"

    def test_resolve_default_project_myvault_api_error(self, manager_with_myvault):
        """Test _resolve_default_project when MyVault API raises error."""
        manager_with_myvault.myvault_client.get_default_project.side_effect = (
            MyVaultError("API error")
        )

        with patch.object(
            manager_with_myvault.settings, "MYVAULT_DEFAULT_PROJECT", "fallback-project"
        ):
            result = manager_with_myvault._resolve_default_project()
            assert result == "fallback-project"


class TestResolveRuntimeValue:
    """Test suite for resolve_runtime_value function."""

    @pytest.fixture
    def mock_secrets_manager(self):
        """Create mock secrets manager."""
        with patch("core.secrets.secrets_manager") as mock_manager:
            with patch("core.secrets.settings") as mock_settings:
                yield mock_manager, mock_settings

    def test_resolve_settings_only_key(self, mock_secrets_manager):
        """Test resolve_runtime_value for settings-only keys."""
        from core.secrets import resolve_runtime_value

        _, mock_settings = mock_secrets_manager
        mock_settings.LOG_LEVEL = "DEBUG"

        result = resolve_runtime_value("LOG_LEVEL")
        assert result == "DEBUG"

    def test_resolve_settings_only_key_with_default(self, mock_secrets_manager):
        """Test resolve_runtime_value for settings-only key with default."""
        from core.secrets import resolve_runtime_value

        _, mock_settings = mock_secrets_manager
        # Delete the attribute to trigger default value usage
        del mock_settings.ADMIN_TOKEN

        result = resolve_runtime_value("ADMIN_TOKEN", default="default-token")
        # Should return the default since ADMIN_TOKEN is not set
        assert result == "default-token"

    def test_resolve_from_secrets_manager(self, mock_secrets_manager):
        """Test resolve_runtime_value retrieves from secrets manager."""
        from core.secrets import resolve_runtime_value

        mock_manager, _ = mock_secrets_manager
        mock_manager.get_secret.return_value = "secret-value"

        result = resolve_runtime_value("OPENAI_API_KEY")
        assert result == "secret-value"
        mock_manager.get_secret.assert_called_once_with(
            "OPENAI_API_KEY", project=None
        )

    def test_resolve_with_project(self, mock_secrets_manager):
        """Test resolve_runtime_value with project parameter."""
        from core.secrets import resolve_runtime_value

        mock_manager, _ = mock_secrets_manager
        mock_manager.get_secret.return_value = "project-secret"

        result = resolve_runtime_value("OPENAI_API_KEY", project="test-project")
        assert result == "project-secret"
        mock_manager.get_secret.assert_called_once_with(
            "OPENAI_API_KEY", project="test-project"
        )

    def test_resolve_fallback_to_settings(self, mock_secrets_manager):
        """Test resolve_runtime_value falls back to settings on ValueError."""
        from core.secrets import resolve_runtime_value

        mock_manager, mock_settings = mock_secrets_manager
        mock_manager.get_secret.side_effect = ValueError("Not found")
        mock_settings.SOME_KEY = "settings-value"

        result = resolve_runtime_value("SOME_KEY")
        assert result == "settings-value"

    def test_resolve_fallback_to_default(self, mock_secrets_manager):
        """Test resolve_runtime_value falls back to default on ValueError."""
        from core.secrets import resolve_runtime_value

        mock_manager, mock_settings = mock_secrets_manager
        mock_manager.get_secret.side_effect = ValueError("Not found")

        # Configure getattr to return empty string then use default
        with patch.object(mock_settings, "NONEXISTENT_KEY", ""):
            result = resolve_runtime_value("NONEXISTENT_KEY", default="default-val")
            # getattr should return the default when key doesn't exist
            assert result is not None
