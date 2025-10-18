"""Tests for CommonUI components."""

from unittest.mock import Mock, patch

import pytest

from components.http_client import HTTPClient
from components.interface_compatibility_checker import InterfaceCompatibilityChecker
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


class TestInterfaceCompatibilityChecker:
    """Test cases for InterfaceCompatibilityChecker."""

    def test_check_compatibility_empty_list(self) -> None:
        """Test compatibility check with empty task list."""
        result = InterfaceCompatibilityChecker.check_compatibility([])

        assert result["is_compatible"] is True
        assert result["issues"] == []
        assert result["summary"] == "No tasks to validate"

    def test_check_compatibility_single_task_with_interfaces(self) -> None:
        """Test compatibility check with single task having both interfaces."""
        tasks = [
            {
                "master_id": "tm_01ABC",
                "sequence": 0,
                "name": "Task A",
                "input_interface_id": "if_01XYZ",
                "output_interface_id": "if_01XYZ",
            },
        ]

        result = InterfaceCompatibilityChecker.check_compatibility(tasks)

        assert result["is_compatible"] is True
        assert len(result["issues"]) == 0
        assert "Single task" in result["summary"]

    def test_check_compatibility_single_task_missing_input(self) -> None:
        """Test compatibility check with single task missing input interface."""
        tasks = [
            {
                "master_id": "tm_01ABC",
                "sequence": 0,
                "name": "Task A",
                "input_interface_id": None,
                "output_interface_id": "if_01XYZ",
            },
        ]

        result = InterfaceCompatibilityChecker.check_compatibility(tasks)

        assert result["is_compatible"] is True
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "warning"
        assert result["issues"][0]["task_name"] == "Task A"
        assert "no input interface" in result["issues"][0]["message"]

    def test_check_compatibility_single_task_missing_output(self) -> None:
        """Test compatibility check with single task missing output interface."""
        tasks = [
            {
                "master_id": "tm_01ABC",
                "sequence": 0,
                "name": "Task A",
                "input_interface_id": "if_01XYZ",
                "output_interface_id": None,
            },
        ]

        result = InterfaceCompatibilityChecker.check_compatibility(tasks)

        assert result["is_compatible"] is True
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "warning"
        assert "no output interface" in result["issues"][0]["message"]

    def test_check_compatibility_two_tasks_compatible(self) -> None:
        """Test compatibility check with two compatible tasks."""
        tasks = [
            {
                "master_id": "tm_01ABC",
                "sequence": 0,
                "name": "Task A",
                "input_interface_id": "if_01IN",
                "output_interface_id": "if_01MID",
            },
            {
                "master_id": "tm_01DEF",
                "sequence": 1,
                "name": "Task B",
                "input_interface_id": "if_01MID",
                "output_interface_id": "if_01OUT",
            },
        ]

        result = InterfaceCompatibilityChecker.check_compatibility(tasks)

        assert result["is_compatible"] is True
        assert result["issues"] == []
        assert "✅" in result["summary"]
        assert "2 tasks are compatible" in result["summary"]

    def test_check_compatibility_two_tasks_incompatible(self) -> None:
        """Test compatibility check with two incompatible tasks."""
        tasks = [
            {
                "master_id": "tm_01ABC",
                "sequence": 0,
                "name": "Task A",
                "input_interface_id": "if_01IN",
                "output_interface_id": "if_01OUT1",
            },
            {
                "master_id": "tm_01DEF",
                "sequence": 1,
                "name": "Task B",
                "input_interface_id": "if_01OUT2",
                "output_interface_id": "if_01FINAL",
            },
        ]

        result = InterfaceCompatibilityChecker.check_compatibility(tasks)

        assert result["is_compatible"] is False
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "error"
        assert result["issues"][0]["task_index"] == 0
        assert "Task A → Task B" in result["issues"][0]["task_name"]
        assert "Interface mismatch" in result["issues"][0]["message"]
        assert "❌" in result["summary"]

    def test_check_compatibility_both_interfaces_missing(self) -> None:
        """Test compatibility check when both tasks have no interfaces."""
        tasks = [
            {
                "master_id": "tm_01ABC",
                "sequence": 0,
                "name": "Task A",
                "input_interface_id": None,
                "output_interface_id": None,
            },
            {
                "master_id": "tm_01DEF",
                "sequence": 1,
                "name": "Task B",
                "input_interface_id": None,
                "output_interface_id": None,
            },
        ]

        result = InterfaceCompatibilityChecker.check_compatibility(tasks)

        assert result["is_compatible"] is True
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "warning"
        assert (
            "Neither task has interface definitions" in result["issues"][0]["message"]
        )

    def test_check_compatibility_current_task_no_output(self) -> None:
        """Test compatibility check when current task has no output interface."""
        tasks = [
            {
                "master_id": "tm_01ABC",
                "sequence": 0,
                "name": "Task A",
                "input_interface_id": "if_01IN",
                "output_interface_id": None,
            },
            {
                "master_id": "tm_01DEF",
                "sequence": 1,
                "name": "Task B",
                "input_interface_id": "if_01MID",
                "output_interface_id": "if_01OUT",
            },
        ]

        result = InterfaceCompatibilityChecker.check_compatibility(tasks)

        assert result["is_compatible"] is True
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "warning"
        assert "Task A" in result["issues"][0]["task_name"]
        assert "no output interface" in result["issues"][0]["message"]

    def test_check_compatibility_next_task_no_input(self) -> None:
        """Test compatibility check when next task has no input interface."""
        tasks = [
            {
                "master_id": "tm_01ABC",
                "sequence": 0,
                "name": "Task A",
                "input_interface_id": "if_01IN",
                "output_interface_id": "if_01OUT",
            },
            {
                "master_id": "tm_01DEF",
                "sequence": 1,
                "name": "Task B",
                "input_interface_id": None,
                "output_interface_id": "if_01FINAL",
            },
        ]

        result = InterfaceCompatibilityChecker.check_compatibility(tasks)

        assert result["is_compatible"] is True
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "warning"
        assert "Task B" in result["issues"][0]["task_name"]
        assert "no input interface" in result["issues"][0]["message"]

    def test_check_compatibility_three_tasks_mixed(self) -> None:
        """Test compatibility check with three tasks with mixed compatibility."""
        tasks = [
            {
                "master_id": "tm_01ABC",
                "sequence": 0,
                "name": "Task A",
                "input_interface_id": "if_01IN",
                "output_interface_id": "if_01MID1",
            },
            {
                "master_id": "tm_01DEF",
                "sequence": 1,
                "name": "Task B",
                "input_interface_id": "if_01MID1",  # Compatible with Task A
                "output_interface_id": "if_01MID2",
            },
            {
                "master_id": "tm_01GHI",
                "sequence": 2,
                "name": "Task C",
                "input_interface_id": "if_01WRONG",  # Incompatible with Task B
                "output_interface_id": "if_01OUT",
            },
        ]

        result = InterfaceCompatibilityChecker.check_compatibility(tasks)

        assert result["is_compatible"] is False
        assert len(result["issues"]) == 1
        assert result["issues"][0]["type"] == "error"
        assert "Task B → Task C" in result["issues"][0]["task_name"]
        assert "Interface mismatch" in result["issues"][0]["message"]

    def test_check_compatibility_with_interface_names(self) -> None:
        """Test compatibility check with interface name resolution."""
        tasks = [
            {
                "master_id": "tm_01ABC",
                "sequence": 0,
                "name": "Task A",
                "input_interface_id": "if_01IN",
                "output_interface_id": "if_01OUT1",
            },
            {
                "master_id": "tm_01DEF",
                "sequence": 1,
                "name": "Task B",
                "input_interface_id": "if_01OUT2",
                "output_interface_id": "if_01FINAL",
            },
        ]

        interfaces = {
            "if_01IN": {"id": "if_01IN", "name": "Input Interface"},
            "if_01OUT1": {"id": "if_01OUT1", "name": "Output Interface 1"},
            "if_01OUT2": {"id": "if_01OUT2", "name": "Output Interface 2"},
            "if_01FINAL": {"id": "if_01FINAL", "name": "Final Interface"},
        }

        result = InterfaceCompatibilityChecker.check_compatibility(tasks, interfaces)

        assert result["is_compatible"] is False
        assert len(result["issues"]) == 1
        error_message = result["issues"][0]["message"]
        assert "Output Interface 1" in error_message
        assert "Output Interface 2" in error_message
        assert "if_01OUT1" in error_message
        assert "if_01OUT2" in error_message

    def test_check_compatibility_summary_with_errors_and_warnings(self) -> None:
        """Test summary generation with both errors and warnings."""
        tasks = [
            {
                "master_id": "tm_01ABC",
                "sequence": 0,
                "name": "Task A",
                "input_interface_id": "if_01IN",
                "output_interface_id": None,  # Warning: missing output
            },
            {
                "master_id": "tm_01DEF",
                "sequence": 1,
                "name": "Task B",
                "input_interface_id": "if_01MID",  # Present (for warning)
                "output_interface_id": "if_01OUT1",
            },
            {
                "master_id": "tm_01GHI",
                "sequence": 2,
                "name": "Task C",
                "input_interface_id": "if_01OUT2",  # Error: mismatch with Task B
                "output_interface_id": "if_01FINAL",
            },
        ]

        result = InterfaceCompatibilityChecker.check_compatibility(tasks)

        assert result["is_compatible"] is False
        assert "❌ 1 error(s)" in result["summary"]
        assert "⚠️ 1 warning(s)" in result["summary"]

        # Count error and warning types
        errors = [issue for issue in result["issues"] if issue["type"] == "error"]
        warnings = [issue for issue in result["issues"] if issue["type"] == "warning"]
        assert len(errors) == 1
        assert len(warnings) == 1
