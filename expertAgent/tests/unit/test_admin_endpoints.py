"""Unit tests for admin endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app


class TestAdminEndpoints:
    """Test admin endpoints functionality."""

    @pytest.fixture
    def client(self):
        """Test client fixture."""
        return TestClient(app)

    @pytest.fixture
    def admin_token(self):
        """Admin token for testing."""
        return "test-admin-token"

    @patch("app.api.v1.admin_endpoints.settings")
    @patch("app.api.v1.admin_endpoints.secrets_manager")
    def test_reload_secrets_success(
        self, mock_secrets_manager, mock_settings, client, admin_token
    ):
        """Test successful secrets reload."""
        mock_settings.ADMIN_TOKEN = admin_token

        response = client.post(
            "/v1/admin/reload-secrets",
            json={"project": None},
            headers={"X-Admin-Token": admin_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "All secrets cache cleared" in data["message"]
        mock_secrets_manager.clear_cache.assert_called_once_with(project=None)

    @patch("app.api.v1.admin_endpoints.settings")
    @patch("app.api.v1.admin_endpoints.secrets_manager")
    def test_reload_secrets_specific_project(
        self, mock_secrets_manager, mock_settings, client, admin_token
    ):
        """Test reloading secrets for specific project."""
        mock_settings.ADMIN_TOKEN = admin_token

        response = client.post(
            "/v1/admin/reload-secrets",
            json={"project": "test-project"},
            headers={"X-Admin-Token": admin_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "test-project" in data["message"]
        mock_secrets_manager.clear_cache.assert_called_once_with(project="test-project")

    @patch("app.api.v1.admin_endpoints.settings")
    def test_reload_secrets_invalid_token(self, mock_settings, client, admin_token):
        """Test reload with invalid admin token."""
        mock_settings.ADMIN_TOKEN = admin_token

        response = client.post(
            "/v1/admin/reload-secrets",
            json={"project": None},
            headers={"X-Admin-Token": "wrong-token"},
        )

        assert response.status_code == 401
        assert "Invalid or missing admin token" in response.json()["detail"]

    @patch("app.api.v1.admin_endpoints.settings")
    def test_reload_secrets_missing_token(self, mock_settings, client, admin_token):
        """Test reload without admin token."""
        mock_settings.ADMIN_TOKEN = admin_token

        response = client.post(
            "/v1/admin/reload-secrets",
            json={"project": None},
        )

        assert response.status_code == 401
        assert "Invalid or missing admin token" in response.json()["detail"]

    @patch("app.api.v1.admin_endpoints.settings")
    def test_reload_secrets_admin_token_not_configured(self, mock_settings, client):
        """Test reload when admin token is not configured."""
        mock_settings.ADMIN_TOKEN = ""

        response = client.post(
            "/v1/admin/reload-secrets",
            json={"project": None},
            headers={"X-Admin-Token": "any-token"},
        )

        assert response.status_code == 500
        assert "Admin token not configured" in response.json()["detail"]

    @patch("app.api.v1.admin_endpoints.settings")
    @patch("app.api.v1.admin_endpoints.secrets_manager")
    def test_reload_secrets_error_handling(
        self, mock_secrets_manager, mock_settings, client, admin_token
    ):
        """Test error handling during reload."""
        mock_settings.ADMIN_TOKEN = admin_token
        mock_secrets_manager.clear_cache.side_effect = Exception("Cache error")

        response = client.post(
            "/v1/admin/reload-secrets",
            json={"project": None},
            headers={"X-Admin-Token": admin_token},
        )

        assert response.status_code == 500
        assert "Failed to reload secrets" in response.json()["detail"]

    @patch("app.api.v1.admin_endpoints.settings")
    def test_admin_health_success(self, mock_settings, client, admin_token):
        """Test admin health check with valid token."""
        mock_settings.ADMIN_TOKEN = admin_token
        mock_settings.MYVAULT_ENABLED = True
        mock_settings.SECRETS_CACHE_TTL = 300

        response = client.get(
            "/v1/admin/health",
            headers={"X-Admin-Token": admin_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["myvault_enabled"] is True
        assert data["cache_ttl"] == 300

    @patch("app.api.v1.admin_endpoints.settings")
    def test_admin_health_invalid_token(self, mock_settings, client, admin_token):
        """Test admin health with invalid token."""
        mock_settings.ADMIN_TOKEN = admin_token

        response = client.get(
            "/v1/admin/health",
            headers={"X-Admin-Token": "wrong-token"},
        )

        assert response.status_code == 401
        assert "Invalid or missing admin token" in response.json()["detail"]

    @patch("app.api.v1.admin_endpoints.settings")
    def test_admin_health_no_token_configured(self, mock_settings, client):
        """Test admin health when token not configured."""
        mock_settings.ADMIN_TOKEN = ""

        response = client.get("/v1/admin/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "warning"
        assert "Admin token not configured" in data["message"]
