"""Unit tests for Google authentication endpoints."""

from unittest.mock import MagicMock, mock_open, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestGoogleAuthEndpoints:
    """Test suite for Google OAuth endpoints."""

    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)

    @pytest.fixture
    def mock_admin_token(self):
        """Mock admin token for testing."""
        with patch("app.api.v1.google_auth_endpoints.settings") as mock_settings:
            mock_settings.ADMIN_TOKEN = "test-admin-token"  # noqa: S105 # Test fixture token
            yield "test-admin-token"  # noqa: S105 # Test fixture token

    def test_oauth2_start_success(self, client, mock_admin_token):
        """Test OAuth2 start endpoint - success case."""
        with patch("app.api.v1.google_auth_endpoints.google_creds_manager") as mock_gcm:
            mock_gcm.initiate_oauth2_flow.return_value = (
                "https://accounts.google.com/auth",
                "state123",
            )

            response = client.post(
                "/v1/google-auth/oauth2-start",
                json={
                    "project": "test-project",
                    "redirect_uri": "http://localhost:8501",
                },
                headers={"X-Admin-Token": mock_admin_token},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["auth_url"] == "https://accounts.google.com/auth"
            assert data["state"] == "state123"
            assert data["project"] == "test-project"

    def test_oauth2_start_error(self, client, mock_admin_token):
        """Test OAuth2 start endpoint - error case."""
        with patch("app.api.v1.google_auth_endpoints.google_creds_manager") as mock_gcm:
            mock_gcm.initiate_oauth2_flow.side_effect = Exception(
                "OAuth initialization failed"
            )

            response = client.post(
                "/v1/google-auth/oauth2-start",
                json={
                    "project": "test-project",
                    "redirect_uri": "http://localhost:8501",
                },
                headers={"X-Admin-Token": mock_admin_token},
            )

            assert response.status_code == 500
            assert "Failed to initiate OAuth2 flow" in response.json()["detail"]

    def test_oauth2_start_invalid_token(self, client):
        """Test OAuth2 start endpoint - invalid admin token."""
        with patch("app.api.v1.google_auth_endpoints.settings") as mock_settings:
            mock_settings.ADMIN_TOKEN = "correct-token"  # noqa: S105 # Test fixture token

            response = client.post(
                "/v1/google-auth/oauth2-start",
                json={"project": "test", "redirect_uri": "http://localhost:8501"},
                headers={"X-Admin-Token": "wrong-token"},
            )

            assert response.status_code == 401
            assert "Invalid admin token" in response.json()["detail"]

    def test_oauth2_callback_success(self, client, mock_admin_token):
        """Test OAuth2 callback endpoint - success case."""
        with patch("app.api.v1.google_auth_endpoints.google_creds_manager") as mock_gcm:
            with patch("app.api.v1.google_auth_endpoints.secrets_manager") as mock_sm:
                mock_gcm.complete_oauth2_flow.return_value = (True, "test")
                mock_gcm.get_token_path.return_value = "/tmp/token.json"  # noqa: S108 # Test fixture path
                mock_sm.myvault_client = MagicMock()

                with patch("builtins.open", mock_open(read_data='{"token": "test"}')):
                    response = client.post(
                        "/v1/google-auth/oauth2-callback",
                        json={
                            "state": "state123",
                            "code": "auth_code",
                            "project": "test",
                        },
                        headers={"X-Admin-Token": mock_admin_token},
                    )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "completed successfully" in data["message"]

    def test_oauth2_callback_flow_failure(self, client, mock_admin_token):
        """Test OAuth2 callback endpoint - flow completion failure."""
        with patch("app.api.v1.google_auth_endpoints.google_creds_manager") as mock_gcm:
            mock_gcm.complete_oauth2_flow.return_value = (False, "test")

            response = client.post(
                "/v1/google-auth/oauth2-callback",
                json={"state": "state123", "code": "auth_code"},
                headers={"X-Admin-Token": mock_admin_token},
            )

            assert response.status_code == 500
            assert "Failed to complete OAuth2 flow" in response.json()["detail"]

    def test_oauth2_callback_myvault_save_error(self, client, mock_admin_token):
        """Test OAuth2 callback endpoint - MyVault save error (non-fatal)."""
        with patch("app.api.v1.google_auth_endpoints.google_creds_manager") as mock_gcm:
            with patch("app.api.v1.google_auth_endpoints.secrets_manager") as mock_sm:
                mock_gcm.complete_oauth2_flow.return_value = (True, "test")
                mock_gcm.get_token_path.return_value = "/tmp/token.json"  # noqa: S108 # Test fixture path

                # MyVault client exists but update fails
                mock_sm.myvault_client = MagicMock()
                mock_sm.myvault_client.update_secret.side_effect = Exception(
                    "MyVault connection error"
                )

                with patch("builtins.open", mock_open(read_data='{"token": "test"}')):
                    response = client.post(
                        "/v1/google-auth/oauth2-callback",
                        json={"state": "state123", "code": "auth_code"},
                        headers={"X-Admin-Token": mock_admin_token},
                    )

                # Should still succeed (local save succeeded)
                assert response.status_code == 200
                assert response.json()["success"] is True

    def test_get_token_status_valid(self, client, mock_admin_token):
        """Test get token status endpoint - valid token."""
        with patch("app.api.v1.google_auth_endpoints.google_creds_manager") as mock_gcm:
            mock_gcm.check_token_validity.return_value = (True, None)

            response = client.get(
                "/v1/google-auth/token-status?project=test",
                headers={"X-Admin-Token": mock_admin_token},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["is_valid"] is True
            assert data["exists"] is True

    def test_get_token_data_exists(self, client, mock_admin_token):
        """Test get token data endpoint - token exists."""
        with patch("app.api.v1.google_auth_endpoints.google_creds_manager") as mock_gcm:
            mock_gcm.get_token_path.return_value = "/tmp/token.json"  # noqa: S108 # Test fixture path

            with patch(
                "builtins.open", mock_open(read_data='{"access_token": "test"}')
            ):
                response = client.get(
                    "/v1/google-auth/token-data?project=test",
                    headers={"X-Admin-Token": mock_admin_token},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["exists"] is True
            assert data["token_json"] == '{"access_token": "test"}'  # noqa: S105 # Test fixture

    def test_get_token_data_not_found(self, client, mock_admin_token):
        """Test get token data endpoint - token not found."""
        with patch("app.api.v1.google_auth_endpoints.google_creds_manager") as mock_gcm:
            mock_gcm.get_token_path.return_value = None

            response = client.get(
                "/v1/google-auth/token-data?project=test",
                headers={"X-Admin-Token": mock_admin_token},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["exists"] is False
            assert data["token_json"] is None
            assert "Token not found" in data["error_message"]

    def test_get_token_data_read_error(self, client, mock_admin_token):
        """Test get token data endpoint - file read error."""
        with patch("app.api.v1.google_auth_endpoints.google_creds_manager") as mock_gcm:
            mock_gcm.get_token_path.return_value = "/tmp/token.json"  # noqa: S108 # Test fixture path

            with patch("builtins.open", side_effect=IOError("Permission denied")):
                response = client.get(
                    "/v1/google-auth/token-data?project=test",
                    headers={"X-Admin-Token": mock_admin_token},
                )

            assert response.status_code == 200
            data = response.json()
            assert data["exists"] is False
            assert "Failed to read token" in data["error_message"]

    def test_save_token_success(self, client, mock_admin_token):
        """Test save token endpoint - success without MyVault."""
        with patch("app.api.v1.google_auth_endpoints.google_creds_manager") as mock_gcm:
            mock_gcm.save_token.return_value = True

            response = client.post(
                "/v1/google-auth/save-token",
                json={
                    "project": "test",
                    "token_json": '{"access_token": "test"}',
                    "save_to_myvault": False,
                },
                headers={"X-Admin-Token": mock_admin_token},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["myvault_saved"] is False

    def test_save_token_with_myvault(self, client, mock_admin_token):
        """Test save token endpoint - success with MyVault."""
        with patch("app.api.v1.google_auth_endpoints.google_creds_manager") as mock_gcm:
            with patch("app.api.v1.google_auth_endpoints.secrets_manager") as mock_sm:
                mock_gcm.save_token.return_value = True
                mock_sm.myvault_client = MagicMock()

                response = client.post(
                    "/v1/google-auth/save-token",
                    json={
                        "token_json": '{"access_token": "test"}',
                        "save_to_myvault": True,
                    },
                    headers={"X-Admin-Token": mock_admin_token},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["myvault_saved"] is True

    def test_save_token_local_failure(self, client, mock_admin_token):
        """Test save token endpoint - local save failure."""
        with patch("app.api.v1.google_auth_endpoints.google_creds_manager") as mock_gcm:
            mock_gcm.save_token.return_value = False

            response = client.post(
                "/v1/google-auth/save-token",
                json={"token_json": '{"access_token": "test"}'},
                headers={"X-Admin-Token": mock_admin_token},
            )

            assert response.status_code == 500
            assert "Failed to save token locally" in response.json()["detail"]

    def test_save_token_myvault_error(self, client, mock_admin_token):
        """Test save token endpoint - MyVault save error (non-fatal)."""
        with patch("app.api.v1.google_auth_endpoints.google_creds_manager") as mock_gcm:
            with patch("app.api.v1.google_auth_endpoints.secrets_manager") as mock_sm:
                mock_gcm.save_token.return_value = True
                mock_sm.myvault_client = MagicMock()
                mock_sm.myvault_client.update_secret.side_effect = Exception(
                    "MyVault error"
                )

                response = client.post(
                    "/v1/google-auth/save-token",
                    json={
                        "token_json": '{"access_token": "test"}',
                        "save_to_myvault": True,
                    },
                    headers={"X-Admin-Token": mock_admin_token},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["myvault_saved"] is False
                assert "myvault_error" in data

    def test_sync_from_myvault_success(self, client, mock_admin_token):
        """Test sync from MyVault endpoint - success."""
        with patch("app.api.v1.google_auth_endpoints.google_creds_manager") as mock_gcm:
            mock_gcm.sync_from_myvault.return_value = True

            response = client.post(
                "/v1/google-auth/sync-from-myvault",
                json={"project": "test"},
                headers={"X-Admin-Token": mock_admin_token},
            )

            assert response.status_code == 200
            data = response.json()
            assert "Synced from MyVault successfully" in data["message"]
            assert data["project"] == "test"

    def test_sync_from_myvault_failure(self, client, mock_admin_token):
        """Test sync from MyVault endpoint - failure."""
        with patch("app.api.v1.google_auth_endpoints.google_creds_manager") as mock_gcm:
            mock_gcm.sync_from_myvault.return_value = False

            response = client.post(
                "/v1/google-auth/sync-from-myvault",
                json={"project": "test"},
                headers={"X-Admin-Token": mock_admin_token},
            )

            assert response.status_code == 404
            assert (
                "GOOGLE_CREDENTIALS_JSON not found in MyVault"
                in response.json()["detail"]
            )

    def test_list_projects_success(self, client, mock_admin_token):
        """Test list projects endpoint - success."""
        with patch("app.api.v1.google_auth_endpoints.google_creds_manager") as mock_gcm:
            mock_gcm.list_projects.return_value = ["default", "project1", "project2"]

            response = client.get(
                "/v1/google-auth/list-projects",
                headers={"X-Admin-Token": mock_admin_token},
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data["projects"]) == 3
            assert "default" in data["projects"]

    def test_verify_admin_token_no_token_configured(self, client):
        """Test admin token verification - no token configured."""
        with patch("app.api.v1.google_auth_endpoints.settings") as mock_settings:
            mock_settings.ADMIN_TOKEN = ""

            response = client.get(
                "/v1/google-auth/list-projects",
                headers={"X-Admin-Token": "any-token"},
            )

            assert response.status_code == 401
