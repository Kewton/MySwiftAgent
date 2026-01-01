"""Unit tests for SecretsManager."""

import time
from unittest.mock import Mock, patch

import pytest

from core.myvault_client import MyVaultError
from core.secrets import SecretsManager


class TestSecretsManager:
    """Test SecretsManager functionality."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings."""
        mock = Mock()
        mock.MYVAULT_ENABLED = True
        mock.MYVAULT_BASE_URL = "http://localhost:8000"
        mock.MYVAULT_SERVICE_NAME = "test-service"
        mock.MYVAULT_SERVICE_TOKEN = "test-token"
        mock.MYVAULT_DEFAULT_PROJECT = ""
        mock.SECRETS_CACHE_TTL = 300
        mock.OPENAI_API_KEY = "env-openai-key"
        mock.GOOGLE_API_KEY = "env-google-key"
        mock.ANTHROPIC_API_KEY = "env-anthropic-key"
        mock.SERPER_API_KEY = "env-serper-key"
        return mock

    @pytest.fixture
    def mock_myvault_client(self):
        """Mock MyVault client."""
        return Mock()

    @patch("core.secrets.settings")
    @patch("core.secrets.MyVaultClient")
    def test_myvault_priority_success(
        self, mock_client_class, mock_settings_class, mock_settings, mock_myvault_client
    ):
        """Test MyVault priority - successful retrieval from MyVault."""
        mock_settings_class.return_value = mock_settings
        mock_client_class.return_value = mock_myvault_client

        # Setup: MyVault returns value
        mock_myvault_client.get_default_project.return_value = "test-project"
        mock_myvault_client.get_secret.return_value = "myvault-openai-key"

        manager = SecretsManager()
        manager.myvault_enabled = True
        manager.myvault_client = mock_myvault_client
        manager.settings = mock_settings

        # Execute
        result = manager.get_secret("OPENAI_API_KEY")

        # Verify: MyVault value is used (not env var)
        assert result == "myvault-openai-key"
        mock_myvault_client.get_secret.assert_called_once()

    @patch("core.secrets.settings")
    @patch("core.secrets.MyVaultClient")
    def test_fallback_to_env_when_myvault_fails(
        self, mock_client_class, mock_settings_class, mock_settings, mock_myvault_client
    ):
        """Test fallback to environment variable when MyVault fails."""
        mock_settings_class.return_value = mock_settings
        mock_client_class.return_value = mock_myvault_client

        # Setup: MyVault raises error
        mock_myvault_client.get_default_project.return_value = "test-project"
        mock_myvault_client.get_secret.side_effect = MyVaultError("Secret not found")

        manager = SecretsManager()
        manager.myvault_enabled = True
        manager.myvault_client = mock_myvault_client
        manager.settings = mock_settings

        # Execute
        result = manager.get_secret("OPENAI_API_KEY")

        # Verify: Falls back to environment variable
        assert result == "env-openai-key"

    @patch("core.secrets.settings")
    def test_error_when_no_secret_found(self, mock_settings_class, mock_settings):
        """Test error when secret not found in MyVault or env."""
        mock_settings_class.return_value = mock_settings
        mock_settings.NONEXISTENT_KEY = ""  # Empty env var

        manager = SecretsManager()
        manager.myvault_enabled = False  # Disable MyVault
        manager.settings = mock_settings

        # Execute & Verify
        with pytest.raises(
            ValueError,
            match="Secret 'NONEXISTENT_KEY' not found in MyVault or environment variables",
        ):
            manager.get_secret("NONEXISTENT_KEY")

    @patch("core.secrets.settings")
    @patch("core.secrets.MyVaultClient")
    def test_cache_functionality(
        self, mock_client_class, mock_settings_class, mock_settings, mock_myvault_client
    ):
        """Test cache with TTL."""
        mock_settings_class.return_value = mock_settings
        mock_client_class.return_value = mock_myvault_client

        # Setup
        mock_myvault_client.get_default_project.return_value = "test-project"
        mock_myvault_client.get_secret.return_value = "cached-value"

        manager = SecretsManager()
        manager.myvault_enabled = True
        manager.myvault_client = mock_myvault_client
        manager.settings = mock_settings
        manager.cache_ttl = 300

        # First call - cache miss
        result1 = manager.get_secret("OPENAI_API_KEY", project="test-project")
        assert result1 == "cached-value"
        assert mock_myvault_client.get_secret.call_count == 1

        # Second call - cache hit (within TTL)
        result2 = manager.get_secret("OPENAI_API_KEY", project="test-project")
        assert result2 == "cached-value"
        assert mock_myvault_client.get_secret.call_count == 1  # No additional call

    @patch("core.secrets.settings")
    @patch("core.secrets.MyVaultClient")
    def test_cache_expiration(
        self, mock_client_class, mock_settings_class, mock_settings, mock_myvault_client
    ):
        """Test cache expiration after TTL."""
        mock_settings_class.return_value = mock_settings
        mock_client_class.return_value = mock_myvault_client

        # Setup
        mock_myvault_client.get_default_project.return_value = "test-project"
        mock_myvault_client.get_secret.return_value = "cached-value"

        manager = SecretsManager()
        manager.myvault_enabled = True
        manager.myvault_client = mock_myvault_client
        manager.settings = mock_settings
        manager.cache_ttl = 1  # 1 second TTL

        # First call
        result1 = manager.get_secret("OPENAI_API_KEY", project="test-project")
        assert result1 == "cached-value"
        assert mock_myvault_client.get_secret.call_count == 1

        # Wait for TTL to expire
        time.sleep(1.1)

        # Second call - cache expired
        result2 = manager.get_secret("OPENAI_API_KEY", project="test-project")
        assert result2 == "cached-value"
        assert mock_myvault_client.get_secret.call_count == 2  # New call made

    @patch("core.secrets.settings")
    @patch("core.secrets.MyVaultClient")
    def test_manual_cache_clear(
        self, mock_client_class, mock_settings_class, mock_settings, mock_myvault_client
    ):
        """Test manual cache clearing."""
        mock_settings_class.return_value = mock_settings
        mock_client_class.return_value = mock_myvault_client

        # Setup
        mock_myvault_client.get_default_project.return_value = "test-project"
        mock_myvault_client.get_secret.return_value = "cached-value"

        manager = SecretsManager()
        manager.myvault_enabled = True
        manager.myvault_client = mock_myvault_client
        manager.settings = mock_settings

        # First call - populate cache
        manager.get_secret("OPENAI_API_KEY", project="test-project")
        assert mock_myvault_client.get_secret.call_count == 1

        # Clear cache
        manager.clear_cache()

        # Second call - cache cleared
        manager.get_secret("OPENAI_API_KEY", project="test-project")
        assert mock_myvault_client.get_secret.call_count == 2

    @patch("core.secrets.settings")
    @patch("core.secrets.MyVaultClient")
    def test_clear_specific_project_cache(
        self, mock_client_class, mock_settings_class, mock_settings, mock_myvault_client
    ):
        """Test clearing cache for specific project."""
        mock_settings_class.return_value = mock_settings
        mock_client_class.return_value = mock_myvault_client

        # Setup
        mock_myvault_client.get_default_project.return_value = "test-project"
        mock_myvault_client.get_secret.return_value = "cached-value"

        manager = SecretsManager()
        manager.myvault_enabled = True
        manager.myvault_client = mock_myvault_client
        manager.settings = mock_settings
        manager.cache_ttl = 300  # Set cache TTL

        # Populate cache for project1
        manager.get_secret("OPENAI_API_KEY", project="project1")
        # Populate cache for project2
        manager.get_secret("GOOGLE_API_KEY", project="project2")
        assert mock_myvault_client.get_secret.call_count == 2

        # Clear only project1 cache
        manager.clear_cache(project="project1")

        # Access project1 - should fetch again
        manager.get_secret("OPENAI_API_KEY", project="project1")
        assert mock_myvault_client.get_secret.call_count == 3

        # Access project2 - should use cache
        manager.get_secret("GOOGLE_API_KEY", project="project2")
        assert mock_myvault_client.get_secret.call_count == 3  # No new call

    @patch("core.secrets.settings")
    @patch("core.secrets.MyVaultClient")
    def test_get_secrets_for_project(
        self, mock_client_class, mock_settings_class, mock_settings, mock_myvault_client
    ):
        """Test getting all secrets for a project."""
        mock_settings_class.return_value = mock_settings
        mock_client_class.return_value = mock_myvault_client

        # Setup
        mock_myvault_client.get_default_project.return_value = "test-project"
        mock_myvault_client.get_secrets.return_value = {
            "OPENAI_API_KEY": "sk-test",
            "GOOGLE_API_KEY": "goog-test",
        }

        manager = SecretsManager()
        manager.myvault_enabled = True
        manager.myvault_client = mock_myvault_client
        manager.settings = mock_settings

        # Execute
        result = manager.get_secrets_for_project("test-project")

        # Verify
        assert result == {
            "OPENAI_API_KEY": "sk-test",
            "GOOGLE_API_KEY": "goog-test",
        }
        mock_myvault_client.get_secrets.assert_called_once_with("test-project")

    @patch("core.secrets.settings")
    def test_get_secrets_without_myvault(self, mock_settings_class, mock_settings):
        """Test getting secrets when MyVault is disabled."""
        mock_settings_class.return_value = mock_settings

        manager = SecretsManager()
        manager.myvault_enabled = False
        manager.settings = mock_settings

        # Execute
        result = manager.get_secrets_for_project()

        # Verify: Returns env vars
        assert "OPENAI_API_KEY" in result
        assert result["OPENAI_API_KEY"] == "env-openai-key"

    @patch("core.secrets.settings")
    @patch("core.secrets.MyVaultClient")
    def test_project_parameter_override(
        self, mock_client_class, mock_settings_class, mock_settings, mock_myvault_client
    ):
        """Test project parameter overrides default project."""
        mock_settings_class.return_value = mock_settings
        mock_client_class.return_value = mock_myvault_client

        # Setup
        mock_settings.MYVAULT_DEFAULT_PROJECT = "default-project"
        mock_myvault_client.get_secret.return_value = "project-specific-value"

        manager = SecretsManager()
        manager.myvault_enabled = True
        manager.myvault_client = mock_myvault_client
        manager.settings = mock_settings

        # Execute with specific project
        manager.get_secret("OPENAI_API_KEY", project="custom-project")

        # Verify: custom-project is used instead of default-project
        mock_myvault_client.get_secret.assert_called_once_with(
            "custom-project", "OPENAI_API_KEY"
        )
