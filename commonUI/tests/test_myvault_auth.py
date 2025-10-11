"""Tests for MyVault authentication in HTTPClient."""

from unittest.mock import Mock, patch

from components.http_client import HTTPClient
from core.config import ExpertAgentConfig, GraphAiServerConfig, MyVaultConfig


class TestMyVaultAuthentication:
    """Test cases for MyVault authentication in HTTPClient."""

    @patch("components.http_client.httpx.Client")
    def test_myvault_auth_headers(self, mock_client_class) -> None:
        """Test MyVault authentication uses X-Service and X-Token headers."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        myvault_config = MyVaultConfig(
            base_url="http://localhost:8000",
            service_name="test-service",
            service_token="test-token",
        )

        HTTPClient(myvault_config, "MyVault")

        # Verify httpx.Client was called with correct headers
        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args[1]

        assert call_kwargs["base_url"] == "http://localhost:8000"
        assert call_kwargs["headers"]["X-Service"] == "test-service"
        assert call_kwargs["headers"]["X-Token"] == "test-token"
        assert "Authorization" not in call_kwargs["headers"]

    @patch("components.http_client.httpx.Client")
    def test_expertagent_auth_headers(self, mock_client_class) -> None:
        """Test ExpertAgent authentication uses X-Admin-Token header."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        expert_config = ExpertAgentConfig(
            base_url="http://localhost:8103",
            admin_token="expert-admin-token",
        )

        HTTPClient(expert_config, "ExpertAgent")

        # Verify httpx.Client was called with correct headers
        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args[1]

        assert call_kwargs["base_url"] == "http://localhost:8103"
        assert call_kwargs["headers"]["X-Admin-Token"] == "expert-admin-token"
        assert "Authorization" not in call_kwargs["headers"]
        assert "X-Service" not in call_kwargs["headers"]

    @patch("components.http_client.httpx.Client")
    def test_graphaiserver_auth_headers(self, mock_client_class) -> None:
        """Test GraphAiServer authentication uses X-Admin-Token header."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        graphai_config = GraphAiServerConfig(
            base_url="http://localhost:8100",
            admin_token="graphai-admin-token",
        )

        HTTPClient(graphai_config, "GraphAiServer")

        # Verify httpx.Client was called with correct headers
        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args[1]

        assert call_kwargs["base_url"] == "http://localhost:8100"
        assert call_kwargs["headers"]["X-Admin-Token"] == "graphai-admin-token"
        assert "Authorization" not in call_kwargs["headers"]
        assert "X-Service" not in call_kwargs["headers"]

    @patch("components.http_client.httpx.Client")
    def test_myvault_without_credentials(self, mock_client_class) -> None:
        """Test MyVault client initialization without credentials."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        myvault_config = MyVaultConfig(
            base_url="http://localhost:8000",
            service_name="",
            service_token="",
        )

        HTTPClient(myvault_config, "MyVault")

        # Verify no authentication headers are added when credentials are empty
        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args[1]

        assert "X-Service" not in call_kwargs["headers"]
        assert "X-Token" not in call_kwargs["headers"]

    @patch("components.http_client.httpx.Client")
    def test_expertagent_without_admin_token(self, mock_client_class) -> None:
        """Test ExpertAgent client initialization without admin token."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        expert_config = ExpertAgentConfig(
            base_url="http://localhost:8103",
            admin_token="",
        )

        HTTPClient(expert_config, "ExpertAgent")

        # Verify no X-Admin-Token header when token is empty
        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args[1]

        assert "X-Admin-Token" not in call_kwargs["headers"]

    @patch("components.http_client.httpx.Client")
    def test_myvault_partial_credentials(self, mock_client_class) -> None:
        """Test MyVault with partial credentials (only service name or token)."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        # Case 1: Only service_name provided
        myvault_config1 = MyVaultConfig(
            base_url="http://localhost:8000",
            service_name="test-service",
            service_token="",
        )

        HTTPClient(myvault_config1, "MyVault")

        call_kwargs = mock_client_class.call_args[1]
        assert "X-Service" not in call_kwargs["headers"]
        assert "X-Token" not in call_kwargs["headers"]

        mock_client_class.reset_mock()

        # Case 2: Only service_token provided
        myvault_config2 = MyVaultConfig(
            base_url="http://localhost:8000",
            service_name="",
            service_token="test-token",
        )

        HTTPClient(myvault_config2, "MyVault")

        call_kwargs = mock_client_class.call_args[1]
        assert "X-Service" not in call_kwargs["headers"]
        assert "X-Token" not in call_kwargs["headers"]

    @patch("components.http_client.httpx.Client")
    def test_http_client_request_with_myvault_auth(self, mock_client_class) -> None:
        """Test that MyVault authentication headers are used in requests."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_client.request.return_value = mock_response
        mock_client_class.return_value = mock_client

        myvault_config = MyVaultConfig(
            base_url="http://localhost:8000",
            service_name="test-service",
            service_token="test-token",
        )

        client = HTTPClient(myvault_config, "MyVault")
        result = client.get("/api/secrets")

        # Verify request was made and response was handled
        assert result == {"status": "success"}
        mock_client.request.assert_called_once()
        assert mock_client.request.call_args[0][0] == "GET"
        assert mock_client.request.call_args[0][1] == "/api/secrets"
