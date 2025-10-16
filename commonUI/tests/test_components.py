"""Tests for CommonUI components."""

from unittest.mock import Mock, patch

import pytest

from components.http_client import HTTPClient
from components.notifications import NotificationManager
from core.config import APIConfig
from core.exceptions import APIError, AuthenticationError, ServiceUnavailableError


class TestHTTPClient:
    """Test cases for HTTPClient."""

    def test_init(self) -> None:
        """Test HTTPClient initialization."""
        api_config = APIConfig(base_url="http://localhost:8001", token="test-token")
        client = HTTPClient(api_config, "TestService")

        assert client.api_config == api_config
        assert client.service_name == "TestService"

    @patch("components.http_client.httpx.Client")
    def test_context_manager(self, mock_client_class) -> None:
        """Test HTTPClient context manager behavior."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        api_config = APIConfig(base_url="http://localhost:8001", token="test-token")

        with HTTPClient(api_config, "TestService") as client:
            assert client.client == mock_client

        mock_client.close.assert_called_once()

    def test_handle_response_success(self) -> None:
        """Test successful response handling."""
        api_config = APIConfig(base_url="http://localhost:8001", token="test-token")
        client = HTTPClient(api_config, "TestService")

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}

        result = client._handle_response(mock_response)
        assert result == {"status": "success"}

    def test_handle_response_authentication_error(self) -> None:
        """Test 401 authentication error handling."""
        api_config = APIConfig(base_url="http://localhost:8001", token="test-token")
        client = HTTPClient(api_config, "TestService")

        mock_response = Mock()
        mock_response.status_code = 401

        with pytest.raises(AuthenticationError) as exc_info:
            client._handle_response(mock_response)

        assert exc_info.value.service_name == "TestService"

    def test_handle_response_server_error(self) -> None:
        """Test 500 server error handling."""
        api_config = APIConfig(base_url="http://localhost:8001", token="test-token")
        client = HTTPClient(api_config, "TestService")

        mock_response = Mock()
        mock_response.status_code = 500

        with pytest.raises(ServiceUnavailableError) as exc_info:
            client._handle_response(mock_response)

        assert exc_info.value.service_name == "TestService"

    def test_handle_response_client_error(self) -> None:
        """Test 400 client error handling."""
        api_config = APIConfig(base_url="http://localhost:8001", token="test-token")
        client = HTTPClient(api_config, "TestService")

        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.reason_phrase = "Bad Request"
        mock_response.json.return_value = {"error": "Invalid request"}

        with pytest.raises(APIError) as exc_info:
            client._handle_response(mock_response)

        assert exc_info.value.status_code == 400
        assert "Bad Request" in str(exc_info.value)

    @patch("components.http_client.httpx.Client")
    def test_health_check_success(self, mock_client_class) -> None:
        """Test successful health check."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "healthy"}

        mock_client.request.return_value = mock_response
        mock_client_class.return_value = mock_client

        api_config = APIConfig(base_url="http://localhost:8001", token="test-token")
        client = HTTPClient(api_config, "TestService")

        result = client.health_check()
        assert result is True

    @patch("components.http_client.httpx.Client")
    def test_health_check_failure(self, mock_client_class) -> None:
        """Test failed health check."""
        mock_client = Mock()
        mock_client.request.side_effect = Exception("Connection failed")
        mock_client_class.return_value = mock_client

        api_config = APIConfig(base_url="http://localhost:8001", token="test-token")
        client = HTTPClient(api_config, "TestService")

        result = client.health_check()
        assert result is False


class TestNotificationManager:
    """Test cases for NotificationManager."""

    @patch("components.notifications.st")
    @patch("components.notifications.logger")
    def test_success_notification(self, mock_logger, mock_st) -> None:
        """Test success notification."""
        NotificationManager.success("Test success message")

        mock_st.success.assert_called_once_with("Test success message")
        mock_st.toast.assert_called_once_with("Test success message", icon="✅")
        mock_logger.info.assert_called_once()

    @patch("components.notifications.st")
    @patch("components.notifications.logger")
    def test_error_notification(self, mock_logger, mock_st) -> None:
        """Test error notification."""
        NotificationManager.error("Test error message")

        mock_st.error.assert_called_once_with("Test error message")
        mock_st.toast.assert_called_once_with("Test error message", icon="❌")
        mock_logger.error.assert_called_once()

    @patch("components.notifications.st")
    @patch("components.notifications.logger")
    def test_handle_service_unavailable_exception(self, mock_logger, mock_st) -> None:
        """Test handling ServiceUnavailableError."""
        exc = ServiceUnavailableError("TestService", "http://localhost:8001")
        NotificationManager.handle_exception(exc, "Test Context")

        mock_st.error.assert_called_once()
        mock_st.toast.assert_called_once()
        call_args = mock_st.error.call_args[0][0]
        assert "TestService" in call_args
        assert "Test Context" in call_args

    @patch("components.notifications.st")
    @patch("components.notifications.logger")
    def test_handle_authentication_exception(self, mock_logger, mock_st) -> None:
        """Test handling AuthenticationError."""
        exc = AuthenticationError("TestService")
        NotificationManager.handle_exception(exc)

        mock_st.error.assert_called_once()
        call_args = mock_st.error.call_args[0][0]
        assert "Authentication failed" in call_args
        assert "TestService" in call_args

    @patch("components.notifications.st")
    @patch("components.notifications.logger")
    def test_handle_generic_exception(self, mock_logger, mock_st) -> None:
        """Test handling generic exceptions."""
        exc = ValueError("Generic error message")
        NotificationManager.handle_exception(exc, "Test Context")

        mock_st.error.assert_called_once()
        mock_st.toast.assert_called_once()
        call_args = mock_st.error.call_args[0][0]
        assert "Test Context" in call_args
        assert "Unexpected error" in call_args

    @patch("components.notifications.st")
    @patch("components.notifications.logger")
    def test_operation_started(self, mock_logger, mock_st) -> None:
        """Test operation started notification."""
        NotificationManager.operation_started("Test Operation")

        mock_st.toast.assert_called_once_with("Test Operation started...", icon="🔄")
        mock_logger.info.assert_called_once()

    @patch("components.notifications.st")
    @patch("components.notifications.logger")
    def test_operation_completed(self, mock_logger, mock_st) -> None:
        """Test operation completed notification."""
        NotificationManager.operation_completed("Test Operation", duration=1.5)

        mock_st.success.assert_called_once_with("Test Operation completed (1.50s)")
        mock_st.toast.assert_called_once_with(
            "Test Operation completed (1.50s)",
            icon="✅",
        )

    @patch("components.notifications.st")
    @patch("components.notifications.logger")
    def test_connection_status_connected(self, mock_logger, mock_st) -> None:
        """Test connection status when connected."""
        NotificationManager.connection_status("TestService", True)

        mock_st.success.assert_called_once_with(
            "✅ Connected to TestService",
            show_toast=False,
        )

    @patch("components.notifications.st")
    @patch("components.notifications.logger")
    def test_connection_status_disconnected(self, mock_logger, mock_st) -> None:
        """Test connection status when disconnected."""
        NotificationManager.connection_status("TestService", False)

        mock_st.error.assert_called_once_with(
            "❌ Cannot connect to TestService",
            show_toast=False,
        )
