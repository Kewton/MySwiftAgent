"""Unit tests for MyVault client."""

from unittest.mock import Mock, patch

import httpx
import pytest

from core.myvault_client import MyVaultClient, MyVaultError


class TestMyVaultClient:
    """Test MyVaultClient functionality."""

    @pytest.fixture
    def client(self):
        """Create test MyVault client."""
        return MyVaultClient(
            base_url="http://localhost:8000",
            service_name="test-service",
            token="test-token",
        )

    def test_client_initialization(self, client):
        """Test client initialization."""
        assert client.base_url == "http://localhost:8000"
        assert client.headers["X-Service"] == "test-service"
        assert client.headers["X-Token"] == "test-token"
        assert client.headers["Content-Type"] == "application/json"

    @patch("core.myvault_client.httpx.Client")
    def test_get_default_project_success(self, mock_client_class):
        """Test successful default project retrieval."""
        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = [
            {"name": "project1", "is_default": False},
            {"name": "project2", "is_default": True},
            {"name": "project3", "is_default": False},
        ]
        mock_response.raise_for_status = Mock()

        mock_instance = Mock()
        mock_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_instance

        client = MyVaultClient(
            base_url="http://localhost:8000",
            service_name="test",
            token="token",
        )

        # Execute
        result = client.get_default_project()

        # Verify
        assert result == "project2"
        mock_instance.get.assert_called_once_with("/api/projects")

    @patch("core.myvault_client.httpx.Client")
    def test_get_default_project_not_found(self, mock_client_class):
        """Test when no default project exists."""
        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = [
            {"name": "project1", "is_default": False},
            {"name": "project2", "is_default": False},
        ]
        mock_response.raise_for_status = Mock()

        mock_instance = Mock()
        mock_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_instance

        client = MyVaultClient(
            base_url="http://localhost:8000",
            service_name="test",
            token="token",
        )

        # Execute
        result = client.get_default_project()

        # Verify
        assert result is None

    @patch("core.myvault_client.httpx.Client")
    def test_get_default_project_http_error(self, mock_client_class):
        """Test HTTP error handling for get_default_project."""
        # Setup mock
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=Mock(), response=mock_response
        )

        mock_instance = Mock()
        mock_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_instance

        client = MyVaultClient(
            base_url="http://localhost:8000",
            service_name="test",
            token="token",
        )

        # Execute & Verify
        with pytest.raises(MyVaultError):
            client.get_default_project()

    @patch("core.myvault_client.httpx.Client")
    def test_get_secrets_success(self, mock_client_class):
        """Test successful secrets retrieval."""
        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = [
            {"path": "OPENAI_API_KEY", "value": "sk-test123"},
            {"path": "GOOGLE_API_KEY", "value": "goog-test456"},
        ]
        mock_response.raise_for_status = Mock()

        mock_instance = Mock()
        mock_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_instance

        client = MyVaultClient(
            base_url="http://localhost:8000",
            service_name="test",
            token="token",
        )

        # Execute
        result = client.get_secrets("test-project")

        # Verify
        assert result == {
            "OPENAI_API_KEY": "sk-test123",
            "GOOGLE_API_KEY": "goog-test456",
        }
        mock_instance.get.assert_called_once_with("/api/secrets/test-project")

    @patch("core.myvault_client.httpx.Client")
    def test_get_secrets_project_not_found(self, mock_client_class):
        """Test project not found error."""
        # Setup mock
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )

        mock_instance = Mock()
        mock_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_instance

        client = MyVaultClient(
            base_url="http://localhost:8000",
            service_name="test",
            token="token",
        )

        # Execute & Verify
        with pytest.raises(MyVaultError, match="Project 'test-project' not found"):
            client.get_secrets("test-project")

    @patch("core.myvault_client.httpx.Client")
    def test_get_secret_success(self, mock_client_class):
        """Test successful individual secret retrieval."""
        # Setup mock
        mock_response = Mock()
        mock_response.json.return_value = {"value": "sk-test123"}
        mock_response.raise_for_status = Mock()

        mock_instance = Mock()
        mock_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_instance

        client = MyVaultClient(
            base_url="http://localhost:8000",
            service_name="test",
            token="token",
        )

        # Execute
        result = client.get_secret("test-project", "OPENAI_API_KEY")

        # Verify
        assert result == "sk-test123"
        mock_instance.get.assert_called_once_with(
            "/api/secrets/test-project/OPENAI_API_KEY"
        )

    @patch("core.myvault_client.httpx.Client")
    def test_get_secret_not_found(self, mock_client_class):
        """Test secret not found error."""
        # Setup mock
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )

        mock_instance = Mock()
        mock_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_instance

        client = MyVaultClient(
            base_url="http://localhost:8000",
            service_name="test",
            token="token",
        )

        # Execute & Verify
        with pytest.raises(
            MyVaultError,
            match="Secret 'OPENAI_API_KEY' not found in project 'test-project'",
        ):
            client.get_secret("test-project", "OPENAI_API_KEY")

    @patch("core.myvault_client.httpx.Client")
    def test_health_check_success(self, mock_client_class):
        """Test successful health check."""
        # Setup mock
        mock_response = Mock()
        mock_response.status_code = 200

        mock_instance = Mock()
        mock_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_instance

        client = MyVaultClient(
            base_url="http://localhost:8000",
            service_name="test",
            token="token",
        )

        # Execute
        result = client.health_check()

        # Verify
        assert result is True
        mock_instance.get.assert_called_once_with("/health")

    @patch("core.myvault_client.httpx.Client")
    def test_health_check_failure(self, mock_client_class):
        """Test failed health check."""
        # Setup mock
        mock_instance = Mock()
        mock_instance.get.side_effect = Exception("Connection error")
        mock_client_class.return_value = mock_instance

        client = MyVaultClient(
            base_url="http://localhost:8000",
            service_name="test",
            token="token",
        )

        # Execute
        result = client.health_check()

        # Verify
        assert result is False

    def test_context_manager(self, client):
        """Test context manager functionality."""
        with client as c:
            assert c is client
        # Verify client is closed after context
        # (In real implementation, this would close the httpx.Client)

    @patch("core.myvault_client.httpx.Client")
    def test_get_default_project_unexpected_error(self, mock_client_class):
        """Test unexpected error in get_default_project."""
        # Setup mock
        mock_instance = Mock()
        mock_instance.get.side_effect = Exception("Unexpected error")
        mock_client_class.return_value = mock_instance

        client = MyVaultClient(
            base_url="http://localhost:8000",
            service_name="test",
            token="token",
        )

        # Execute & Verify
        with pytest.raises(MyVaultError, match="Unexpected error"):
            client.get_default_project()

    @patch("core.myvault_client.httpx.Client")
    def test_get_secrets_http_error_non_404(self, mock_client_class):
        """Test HTTP error (non-404) in get_secrets."""
        # Setup mock
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=Mock(), response=mock_response
        )

        mock_instance = Mock()
        mock_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_instance

        client = MyVaultClient(
            base_url="http://localhost:8000",
            service_name="test",
            token="token",
        )

        # Execute & Verify
        with pytest.raises(
            MyVaultError, match="Failed to get secrets for 'test-project'"
        ):
            client.get_secrets("test-project")

    @patch("core.myvault_client.httpx.Client")
    def test_get_secrets_unexpected_error(self, mock_client_class):
        """Test unexpected error in get_secrets."""
        # Setup mock
        mock_instance = Mock()
        mock_instance.get.side_effect = Exception("Unexpected error")
        mock_client_class.return_value = mock_instance

        client = MyVaultClient(
            base_url="http://localhost:8000",
            service_name="test",
            token="token",
        )

        # Execute & Verify
        with pytest.raises(MyVaultError, match="Unexpected error"):
            client.get_secrets("test-project")

    @patch("core.myvault_client.httpx.Client")
    def test_get_secret_http_error_non_404(self, mock_client_class):
        """Test HTTP error (non-404) in get_secret."""
        # Setup mock
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=Mock(), response=mock_response
        )

        mock_instance = Mock()
        mock_instance.get.return_value = mock_response
        mock_client_class.return_value = mock_instance

        client = MyVaultClient(
            base_url="http://localhost:8000",
            service_name="test",
            token="token",
        )

        # Execute & Verify
        with pytest.raises(MyVaultError, match="Failed to get secret 'SECRET_KEY'"):
            client.get_secret("test-project", "SECRET_KEY")

    @patch("core.myvault_client.httpx.Client")
    def test_get_secret_unexpected_error(self, mock_client_class):
        """Test unexpected error in get_secret."""
        # Setup mock
        mock_instance = Mock()
        mock_instance.get.side_effect = Exception("Unexpected error")
        mock_client_class.return_value = mock_instance

        client = MyVaultClient(
            base_url="http://localhost:8000",
            service_name="test",
            token="token",
        )

        # Execute & Verify
        with pytest.raises(MyVaultError, match="Unexpected error"):
            client.get_secret("test-project", "SECRET_KEY")

    @patch("core.myvault_client.httpx.Client")
    def test_update_secret_patch_success(self, mock_client_class):
        """Test successful secret update via PATCH."""
        # Setup mock
        mock_response = Mock()
        mock_response.raise_for_status = Mock()

        mock_instance = Mock()
        mock_instance.patch.return_value = mock_response
        mock_client_class.return_value = mock_instance

        client = MyVaultClient(
            base_url="http://localhost:8000",
            service_name="test",
            token="token",
        )

        # Execute
        client.update_secret("test-project", "SECRET_KEY", "new-value")

        # Verify
        mock_instance.patch.assert_called_once_with(
            "/api/secrets/test-project/SECRET_KEY", json={"value": "new-value"}
        )

    @patch("core.myvault_client.httpx.Client")
    def test_update_secret_create_on_404(self, mock_client_class):
        """Test secret creation via POST when PATCH returns 404."""
        # Setup mocks
        patch_response = Mock()
        patch_response.status_code = 404
        patch_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=patch_response
        )

        post_response = Mock()
        post_response.raise_for_status = Mock()

        mock_instance = Mock()
        mock_instance.patch.return_value = patch_response
        mock_instance.post.return_value = post_response
        mock_client_class.return_value = mock_instance

        client = MyVaultClient(
            base_url="http://localhost:8000",
            service_name="test",
            token="token",
        )

        # Execute
        client.update_secret("test-project", "NEW_SECRET", "value")

        # Verify PATCH was attempted
        mock_instance.patch.assert_called_once()

        # Verify POST was called to create new secret
        mock_instance.post.assert_called_once_with(
            "/api/secrets",
            json={"project": "test-project", "path": "NEW_SECRET", "value": "value"},
        )

    @patch("core.myvault_client.httpx.Client")
    def test_update_secret_patch_http_error(self, mock_client_class):
        """Test HTTP error (non-404) in update_secret PATCH."""
        # Setup mock
        patch_response = Mock()
        patch_response.status_code = 500
        patch_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=Mock(), response=patch_response
        )

        mock_instance = Mock()
        mock_instance.patch.return_value = patch_response
        mock_client_class.return_value = mock_instance

        client = MyVaultClient(
            base_url="http://localhost:8000",
            service_name="test",
            token="token",
        )

        # Execute & Verify
        with pytest.raises(MyVaultError, match="Failed to update secret 'SECRET_KEY'"):
            client.update_secret("test-project", "SECRET_KEY", "value")

    @patch("core.myvault_client.httpx.Client")
    def test_update_secret_post_http_error(self, mock_client_class):
        """Test HTTP error in POST after 404 PATCH."""
        # Setup mocks
        patch_response = Mock()
        patch_response.status_code = 404
        patch_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=patch_response
        )

        post_response = Mock()
        post_response.status_code = 500
        post_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=Mock(), response=post_response
        )

        mock_instance = Mock()
        mock_instance.patch.return_value = patch_response
        mock_instance.post.return_value = post_response
        mock_client_class.return_value = mock_instance

        client = MyVaultClient(
            base_url="http://localhost:8000",
            service_name="test",
            token="token",
        )

        # Execute & Verify
        with pytest.raises(MyVaultError, match="Failed to update secret 'SECRET_KEY'"):
            client.update_secret("test-project", "SECRET_KEY", "value")

    @patch("core.myvault_client.httpx.Client")
    def test_update_secret_unexpected_error(self, mock_client_class):
        """Test unexpected error in update_secret."""
        # Setup mock
        mock_instance = Mock()
        mock_instance.patch.side_effect = Exception("Unexpected error")
        mock_client_class.return_value = mock_instance

        client = MyVaultClient(
            base_url="http://localhost:8000",
            service_name="test",
            token="token",
        )

        # Execute & Verify
        with pytest.raises(MyVaultError, match="Unexpected error"):
            client.update_secret("test-project", "SECRET_KEY", "value")
