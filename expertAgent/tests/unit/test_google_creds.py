"""Unit tests for Google credentials management."""

import json
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from core.google_creds import GoogleCredsManager, get_project_name


class TestGetProjectName:
    """Test suite for get_project_name function."""

    def test_get_project_name_with_none(self):
        """Test get_project_name with None returns 'default' or settings value."""
        with patch("core.google_creds.settings") as mock_settings:
            mock_settings.MYVAULT_DEFAULT_PROJECT = "default"
            result = get_project_name(None)
            assert result == "default"

    def test_get_project_name_with_value(self):
        """Test get_project_name with a value returns that value."""
        assert get_project_name("custom-project") == "custom-project"


class TestGoogleCredsManager:
    """Test suite for GoogleCredsManager class."""

    @pytest.fixture
    def manager(self):
        """Create a GoogleCredsManager instance for testing."""
        return GoogleCredsManager()

    def test_initialization(self, manager):
        """Test GoogleCredsManager initialization."""
        assert manager is not None
        assert manager._fernet is None
        assert manager._current_project is None

    def test_get_token_path_not_exists(self, manager):
        """Test get_token_path when token file doesn't exist."""
        with patch.object(manager, "_get_token_file") as mock_get_file:
            mock_token_file = MagicMock()
            mock_token_file.exists.return_value = False
            mock_get_file.return_value = mock_token_file

            path = manager.get_token_path("test-project")
            assert path is None

    def test_check_token_validity_token_not_found(self, manager):
        """Test check_token_validity when token is not found."""
        with patch.object(manager, "_get_token_file") as mock_get_file:
            mock_token_file = MagicMock()
            mock_token_file.exists.return_value = False
            mock_get_file.return_value = mock_token_file

            is_valid, error = manager.check_token_validity("test-project")
            assert is_valid is False
            assert "Token not found" in error

    def test_check_token_validity_exception(self, manager):
        """Test check_token_validity when an exception occurs."""
        with patch.object(manager, "_get_token_file") as mock_get_file:
            mock_token_file = MagicMock()
            mock_token_file.exists.return_value = True
            mock_get_file.return_value = mock_token_file

            with patch.object(manager, "_decrypt_file", side_effect=Exception("Decrypt error")):
                is_valid, error = manager.check_token_validity("test-project")
                assert is_valid is False
                assert "Decrypt error" in error

    def test_sync_from_myvault_success(self, manager):
        """Test sync_from_myvault success case."""
        with patch("core.google_creds.secrets_manager") as mock_sm:
            mock_sm.get_secret.return_value = '{"type": "service_account"}'

            with patch.object(manager, "_encrypt_file"):
                result = manager.sync_from_myvault("test-project")
                assert result is True

    def test_sync_from_myvault_exception(self, manager):
        """Test sync_from_myvault when exception occurs."""
        with patch("core.google_creds.secrets_manager") as mock_sm:
            mock_sm.get_secret.side_effect = Exception("MyVault error")

            result = manager.sync_from_myvault("test-project")
            assert result is False

    def test_list_projects_no_directory(self, manager):
        """Test list_projects when credentials directory doesn't exist."""
        with patch("core.google_creds.CREDS_DIR") as mock_dir:
            mock_dir.exists.return_value = False

            projects = manager.list_projects()
            assert projects == []

    def test_save_token_success(self, manager):
        """Test save_token success case."""
        token_json = '{"access_token": "test", "refresh_token": "refresh"}'

        with patch.object(manager, "_encrypt_file"):
            result = manager.save_token(token_json, "test-project")
            assert result is True

    def test_save_token_invalid_json(self, manager):
        """Test save_token with invalid JSON."""
        invalid_json = "not a valid json"

        result = manager.save_token(invalid_json, "test-project")
        assert result is False

    def test_save_token_exception(self, manager):
        """Test save_token when exception occurs."""
        token_json = '{"access_token": "test"}'

        with patch.object(manager, "_encrypt_file", side_effect=Exception("Encrypt error")):
            result = manager.save_token(token_json, "test-project")
            assert result is False

    def test_initiate_oauth2_flow_success(self, manager):
        """Test initiate_oauth2_flow success case."""
        with patch("google_auth_oauthlib.flow.Flow") as MockFlow:
            mock_flow_instance = MagicMock()
            mock_flow_instance.authorization_url.return_value = (
                "https://accounts.google.com/auth",
                "state123",
            )
            MockFlow.from_client_secrets_file.return_value = mock_flow_instance

            with patch.object(manager, "get_credentials_path", return_value="/tmp/creds.json"):
                auth_url, state = manager.initiate_oauth2_flow(
                    project="test", redirect_uri="http://localhost:8501"
                )

                assert auth_url == "https://accounts.google.com/auth"
                assert state is not None
                assert hasattr(manager, "_oauth_flows")
                assert state in manager._oauth_flows

    def test_initiate_oauth2_flow_exception(self, manager):
        """Test initiate_oauth2_flow when exception occurs."""
        with patch.object(manager, "get_credentials_path", side_effect=FileNotFoundError("No creds")):
            with pytest.raises(ValueError) as exc_info:
                manager.initiate_oauth2_flow(project="test")

            assert "Failed to initiate OAuth2 flow" in str(exc_info.value)

    def test_complete_oauth2_flow_invalid_state(self, manager):
        """Test complete_oauth2_flow with invalid state."""
        result = manager.complete_oauth2_flow(
            state="invalid_state", code="auth_code", project="test"
        )
        assert result is False

    def test_complete_oauth2_flow_success(self, manager):
        """Test complete_oauth2_flow success case."""
        # Setup: initiate flow first
        mock_flow = MagicMock()
        mock_creds = MagicMock()
        mock_creds.to_json.return_value = '{"token": "test"}'
        mock_flow.credentials = mock_creds

        manager._oauth_flows = {"state123": {"flow": mock_flow, "project": "test", "redirect_uri": "http://localhost"}}

        with patch.object(manager, "save_token", return_value=True):
            result = manager.complete_oauth2_flow(
                state="state123", code="auth_code", project="test"
            )

            assert result is True
            mock_flow.fetch_token.assert_called_once_with(code="auth_code")
            assert "state123" not in manager._oauth_flows  # Cleaned up

    def test_complete_oauth2_flow_save_failure(self, manager):
        """Test complete_oauth2_flow when save fails."""
        mock_flow = MagicMock()
        mock_creds = MagicMock()
        mock_creds.to_json.return_value = '{"token": "test"}'
        mock_flow.credentials = mock_creds

        manager._oauth_flows = {"state123": {"flow": mock_flow, "project": "test", "redirect_uri": "http://localhost"}}

        with patch.object(manager, "save_token", return_value=False):
            result = manager.complete_oauth2_flow(
                state="state123", code="auth_code", project="test"
            )

            assert result is False

    def test_switch_project_success(self, manager):
        """Test switch_project success case."""
        with patch.object(manager, "_get_credentials_file") as mock_get_file:
            mock_creds_file = MagicMock()
            mock_creds_file.exists.return_value = True
            mock_get_file.return_value = mock_creds_file

            result = manager.switch_project("test-project")
            assert result is True
            assert manager._current_project == "test-project"

    def test_switch_project_sync_required(self, manager):
        """Test switch_project when sync from MyVault is required."""
        with patch.object(manager, "_get_credentials_file") as mock_get_file:
            mock_creds_file = MagicMock()
            mock_creds_file.exists.return_value = False
            mock_get_file.return_value = mock_creds_file

            with patch.object(manager, "sync_from_myvault", return_value=True):
                result = manager.switch_project("test-project")
                assert result is True

    def test_switch_project_sync_failure(self, manager):
        """Test switch_project when sync fails."""
        with patch.object(manager, "_get_credentials_file") as mock_get_file:
            mock_creds_file = MagicMock()
            mock_creds_file.exists.return_value = False
            mock_get_file.return_value = mock_creds_file

            with patch.object(manager, "sync_from_myvault", return_value=False):
                result = manager.switch_project("test-project")
                assert result is False
