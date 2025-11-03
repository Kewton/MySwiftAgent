"""Unit tests for TraceService."""

from unittest.mock import MagicMock, Mock, patch

import httpx
import pytest

from app.services.trace_service import TraceService, trace_service


class TestTraceService:
    """Test TraceService functionality."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings with Langfuse enabled."""
        mock = Mock()
        mock.LANGFUSE_PUBLIC_KEY = "pk-test-123"
        mock.LANGFUSE_SECRET_KEY = "sk-test-456"
        mock.LANGFUSE_HOST = "http://localhost:3001"
        return mock

    @pytest.fixture
    def mock_settings_disabled(self):
        """Create mock settings with Langfuse disabled."""
        mock = Mock()
        mock.LANGFUSE_PUBLIC_KEY = ""
        mock.LANGFUSE_SECRET_KEY = ""
        mock.LANGFUSE_HOST = ""
        return mock

    def test_singleton_instance_is_created(self):
        """Test that trace_service singleton instance is created."""
        assert trace_service is not None
        assert isinstance(trace_service, TraceService)

    @patch("app.services.trace_service.settings")
    def test_is_enabled_with_keys(self, mock_settings_patch):
        """Test _is_enabled returns True when keys are set."""
        # Setup
        mock_settings_patch.LANGFUSE_PUBLIC_KEY = "pk-test-123"
        mock_settings_patch.LANGFUSE_SECRET_KEY = "sk-test-456"
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"

        service = TraceService()

        # Execute
        result = service._is_enabled()

        # Verify
        assert result is True

    @patch("app.services.trace_service.settings")
    def test_is_enabled_without_keys(self, mock_settings_patch):
        """Test _is_enabled returns False when keys are missing."""
        # Setup
        mock_settings_patch.LANGFUSE_PUBLIC_KEY = ""
        mock_settings_patch.LANGFUSE_SECRET_KEY = ""
        mock_settings_patch.LANGFUSE_HOST = ""

        service = TraceService()

        # Execute
        result = service._is_enabled()

        # Verify
        assert result is False

    @patch("app.services.trace_service.settings")
    def test_get_trace_url_success(self, mock_settings_patch):
        """Test successful trace URL generation."""
        # Setup
        mock_settings_patch.LANGFUSE_PUBLIC_KEY = "pk-test-123"
        mock_settings_patch.LANGFUSE_SECRET_KEY = "sk-test-456"
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"

        service = TraceService()

        # Execute
        url = service.get_trace_url("trace-abc123")

        # Verify
        assert (
            url
            == "http://localhost:3001/project/expertAgent-traces/traces/trace-abc123"
        )

    @patch("app.services.trace_service.settings")
    def test_get_trace_url_disabled(self, mock_settings_patch):
        """Test get_trace_url returns None when Langfuse is disabled."""
        # Setup
        mock_settings_patch.LANGFUSE_PUBLIC_KEY = ""
        mock_settings_patch.LANGFUSE_SECRET_KEY = ""
        mock_settings_patch.LANGFUSE_HOST = ""

        service = TraceService()

        # Execute
        url = service.get_trace_url("trace-abc123")

        # Verify
        assert url is None

    @patch("app.services.trace_service.settings")
    @patch("app.services.trace_service.httpx.Client")
    def test_get_traces_success(self, mock_client_class, mock_settings_patch):
        """Test successful traces retrieval."""
        # Setup
        mock_settings_patch.LANGFUSE_PUBLIC_KEY = "pk-test-123"
        mock_settings_patch.LANGFUSE_SECRET_KEY = "sk-test-456"
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"id": "trace-1", "name": "chat_api", "userId": "user123"},
                {"id": "trace-2", "name": "job_api", "userId": "user456"},
            ]
        }
        mock_response.raise_for_status = Mock()

        mock_instance = MagicMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.__exit__.return_value = None
        mock_client_class.return_value = mock_instance

        service = TraceService()

        # Execute
        traces = service.get_traces(limit=10, user_id="user123")

        # Verify
        assert traces is not None
        assert len(traces) == 2
        assert traces[0]["id"] == "trace-1"
        mock_instance.get.assert_called_once()

    @patch("app.services.trace_service.settings")
    def test_get_traces_disabled(self, mock_settings_patch):
        """Test get_traces returns None when Langfuse is disabled."""
        # Setup
        mock_settings_patch.LANGFUSE_PUBLIC_KEY = ""
        mock_settings_patch.LANGFUSE_SECRET_KEY = ""
        mock_settings_patch.LANGFUSE_HOST = ""

        service = TraceService()

        # Execute
        traces = service.get_traces()

        # Verify
        assert traces is None

    @patch("app.services.trace_service.settings")
    @patch("app.services.trace_service.httpx.Client")
    def test_get_traces_http_error(self, mock_client_class, mock_settings_patch):
        """Test graceful handling of HTTP error in get_traces."""
        # Setup
        mock_settings_patch.LANGFUSE_PUBLIC_KEY = "pk-test-123"
        mock_settings_patch.LANGFUSE_SECRET_KEY = "sk-test-456"
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=Mock(), response=mock_response
        )

        mock_instance = MagicMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.__exit__.return_value = None
        mock_client_class.return_value = mock_instance

        service = TraceService()

        # Execute
        traces = service.get_traces()

        # Verify - should return None on error
        assert traces is None

    @patch("app.services.trace_service.settings")
    @patch("app.services.trace_service.httpx.Client")
    def test_get_traces_with_filters(self, mock_client_class, mock_settings_patch):
        """Test get_traces with all filter parameters."""
        # Setup
        mock_settings_patch.LANGFUSE_PUBLIC_KEY = "pk-test-123"
        mock_settings_patch.LANGFUSE_SECRET_KEY = "sk-test-456"
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"

        mock_response = Mock()
        mock_response.json.return_value = {"data": []}
        mock_response.raise_for_status = Mock()

        mock_instance = MagicMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.__exit__.return_value = None
        mock_client_class.return_value = mock_instance

        service = TraceService()

        # Execute
        service.get_traces(
            limit=20,
            user_id="user123",
            tags=["production", "chat"],
            from_timestamp="2025-01-01T00:00:00Z",
            to_timestamp="2025-01-31T23:59:59Z",
        )

        # Verify - check that params were passed correctly
        call_args = mock_instance.get.call_args
        assert call_args[1]["params"]["limit"] == 20
        assert call_args[1]["params"]["userId"] == "user123"
        assert call_args[1]["params"]["tags"] == "production,chat"
        assert call_args[1]["params"]["fromTimestamp"] == "2025-01-01T00:00:00Z"
        assert call_args[1]["params"]["toTimestamp"] == "2025-01-31T23:59:59Z"

    @patch("app.services.trace_service.settings")
    @patch("app.services.trace_service.httpx.Client")
    def test_get_trace_by_id_success(self, mock_client_class, mock_settings_patch):
        """Test successful trace retrieval by ID."""
        # Setup
        mock_settings_patch.LANGFUSE_PUBLIC_KEY = "pk-test-123"
        mock_settings_patch.LANGFUSE_SECRET_KEY = "sk-test-456"
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"

        mock_response = Mock()
        mock_response.json.return_value = {
            "id": "trace-abc123",
            "name": "chat_api",
            "userId": "user123",
            "input": {"query": "Hello"},
            "output": {"response": "Hi there!"},
        }
        mock_response.raise_for_status = Mock()

        mock_instance = MagicMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.__exit__.return_value = None
        mock_client_class.return_value = mock_instance

        service = TraceService()

        # Execute
        trace = service.get_trace_by_id("trace-abc123")

        # Verify
        assert trace is not None
        assert trace["id"] == "trace-abc123"
        assert trace["name"] == "chat_api"

    @patch("app.services.trace_service.settings")
    def test_get_trace_by_id_disabled(self, mock_settings_patch):
        """Test get_trace_by_id returns None when Langfuse is disabled."""
        # Setup
        mock_settings_patch.LANGFUSE_PUBLIC_KEY = ""
        mock_settings_patch.LANGFUSE_SECRET_KEY = ""
        mock_settings_patch.LANGFUSE_HOST = ""

        service = TraceService()

        # Execute
        trace = service.get_trace_by_id("trace-abc123")

        # Verify
        assert trace is None

    @patch("app.services.trace_service.settings")
    @patch("app.services.trace_service.httpx.Client")
    def test_get_trace_by_id_not_found(self, mock_client_class, mock_settings_patch):
        """Test get_trace_by_id returns None when trace not found."""
        # Setup
        mock_settings_patch.LANGFUSE_PUBLIC_KEY = "pk-test-123"
        mock_settings_patch.LANGFUSE_SECRET_KEY = "sk-test-456"
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=Mock(), response=mock_response
        )

        mock_instance = MagicMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.__exit__.return_value = None
        mock_client_class.return_value = mock_instance

        service = TraceService()

        # Execute
        trace = service.get_trace_by_id("trace-nonexistent")

        # Verify
        assert trace is None

    @patch("app.services.trace_service.settings")
    @patch("app.services.trace_service.httpx.Client")
    def test_get_observations_by_trace_success(
        self, mock_client_class, mock_settings_patch
    ):
        """Test successful observations retrieval."""
        # Setup
        mock_settings_patch.LANGFUSE_PUBLIC_KEY = "pk-test-123"
        mock_settings_patch.LANGFUSE_SECRET_KEY = "sk-test-456"
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"id": "obs-1", "type": "generation", "name": "llm_call"},
                {"id": "obs-2", "type": "span", "name": "retrieval"},
            ]
        }
        mock_response.raise_for_status = Mock()

        mock_instance = MagicMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.__exit__.return_value = None
        mock_client_class.return_value = mock_instance

        service = TraceService()

        # Execute
        observations = service.get_observations_by_trace("trace-abc123")

        # Verify
        assert observations is not None
        assert len(observations) == 2
        assert observations[0]["type"] == "generation"

    @patch("app.services.trace_service.settings")
    def test_get_observations_by_trace_disabled(self, mock_settings_patch):
        """Test get_observations_by_trace returns None when Langfuse is disabled."""
        # Setup
        mock_settings_patch.LANGFUSE_PUBLIC_KEY = ""
        mock_settings_patch.LANGFUSE_SECRET_KEY = ""
        mock_settings_patch.LANGFUSE_HOST = ""

        service = TraceService()

        # Execute
        observations = service.get_observations_by_trace("trace-abc123")

        # Verify
        assert observations is None

    @patch("app.services.trace_service.settings")
    @patch("app.services.trace_service.httpx.Client")
    def test_get_scores_by_trace_success(self, mock_client_class, mock_settings_patch):
        """Test successful scores retrieval."""
        # Setup
        mock_settings_patch.LANGFUSE_PUBLIC_KEY = "pk-test-123"
        mock_settings_patch.LANGFUSE_SECRET_KEY = "sk-test-456"
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "score-1",
                    "name": "user_rating",
                    "value": 0.9,
                    "comment": "Great!",
                },
                {"id": "score-2", "name": "accuracy", "value": 0.85, "comment": None},
            ]
        }
        mock_response.raise_for_status = Mock()

        mock_instance = MagicMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.__exit__.return_value = None
        mock_client_class.return_value = mock_instance

        service = TraceService()

        # Execute
        scores = service.get_scores_by_trace("trace-abc123")

        # Verify
        assert scores is not None
        assert len(scores) == 2
        assert scores[0]["name"] == "user_rating"
        assert scores[0]["value"] == 0.9

    @patch("app.services.trace_service.settings")
    def test_get_scores_by_trace_disabled(self, mock_settings_patch):
        """Test get_scores_by_trace returns None when Langfuse is disabled."""
        # Setup
        mock_settings_patch.LANGFUSE_PUBLIC_KEY = ""
        mock_settings_patch.LANGFUSE_SECRET_KEY = ""
        mock_settings_patch.LANGFUSE_HOST = ""

        service = TraceService()

        # Execute
        scores = service.get_scores_by_trace("trace-abc123")

        # Verify
        assert scores is None

    @patch("app.services.trace_service.settings")
    @patch("app.services.trace_service.httpx.Client")
    def test_get_scores_by_trace_http_error(
        self, mock_client_class, mock_settings_patch
    ):
        """Test graceful handling of HTTP error in get_scores_by_trace."""
        # Setup
        mock_settings_patch.LANGFUSE_PUBLIC_KEY = "pk-test-123"
        mock_settings_patch.LANGFUSE_SECRET_KEY = "sk-test-456"
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"

        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=Mock(), response=mock_response
        )

        mock_instance = MagicMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.__exit__.return_value = None
        mock_client_class.return_value = mock_instance

        service = TraceService()

        # Execute
        scores = service.get_scores_by_trace("trace-abc123")

        # Verify - should return None on error
        assert scores is None

    @patch("app.services.trace_service.settings")
    @patch("app.services.trace_service.httpx.Client")
    def test_get_traces_unexpected_error(self, mock_client_class, mock_settings_patch):
        """Test graceful handling of unexpected error in get_traces."""
        # Setup
        mock_settings_patch.LANGFUSE_PUBLIC_KEY = "pk-test-123"
        mock_settings_patch.LANGFUSE_SECRET_KEY = "sk-test-456"
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"

        mock_instance = MagicMock()
        mock_instance.get.side_effect = Exception("Unexpected error")
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.__exit__.return_value = None
        mock_client_class.return_value = mock_instance

        service = TraceService()

        # Execute
        traces = service.get_traces()

        # Verify - should return None on error
        assert traces is None

    @patch("app.services.trace_service.settings")
    @patch("app.services.trace_service.httpx.Client")
    def test_get_trace_by_id_unexpected_error(
        self, mock_client_class, mock_settings_patch
    ):
        """Test graceful handling of unexpected error in get_trace_by_id."""
        # Setup
        mock_settings_patch.LANGFUSE_PUBLIC_KEY = "pk-test-123"
        mock_settings_patch.LANGFUSE_SECRET_KEY = "sk-test-456"
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"

        mock_instance = MagicMock()
        mock_instance.get.side_effect = Exception("Unexpected error")
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.__exit__.return_value = None
        mock_client_class.return_value = mock_instance

        service = TraceService()

        # Execute
        trace = service.get_trace_by_id("trace-abc123")

        # Verify - should return None on error
        assert trace is None


class TestTraceServiceMyVaultIntegration:
    """Test TraceService with myVault integration."""

    @patch("app.services.trace_service.secrets_manager")
    @patch("app.services.trace_service.settings")
    def test_initialize_keys_from_myvault(
        self, mock_settings_patch, mock_secrets_manager
    ):
        """Test successful key initialization from myVault."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-myvault-123",
            "LANGFUSE_SECRET_KEY": "sk-myvault-456",
        }[key]
        mock_secrets_manager.myvault_enabled = True

        # Execute
        service = TraceService()

        # Verify
        assert service._public_key == "pk-myvault-123"
        assert service._secret_key == "sk-myvault-456"
        assert service._is_enabled() is True
        mock_secrets_manager.get_secret.assert_any_call("LANGFUSE_PUBLIC_KEY")
        mock_secrets_manager.get_secret.assert_any_call("LANGFUSE_SECRET_KEY")

    @patch("app.services.trace_service.secrets_manager")
    @patch("app.services.trace_service.settings")
    def test_initialize_keys_fallback_to_env(
        self, mock_settings_patch, mock_secrets_manager
    ):
        """Test key initialization falls back to environment variables."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = ValueError(
            "Key not found in myVault"
        )
        mock_secrets_manager.myvault_enabled = False

        # Execute
        service = TraceService()

        # Verify - keys should be None when myVault fails and env vars not set
        assert service._public_key is None
        assert service._secret_key is None
        assert service._is_enabled() is False

    @patch("app.services.trace_service.secrets_manager")
    @patch("app.services.trace_service.settings")
    def test_initialize_keys_myvault_priority(
        self, mock_settings_patch, mock_secrets_manager
    ):
        """Test myVault takes priority over environment variables."""
        # Setup - myVault有効 + 環境変数も設定
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_settings_patch.LANGFUSE_PUBLIC_KEY = "pk-env-999"
        mock_settings_patch.LANGFUSE_SECRET_KEY = "sk-env-999"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-myvault-123",
            "LANGFUSE_SECRET_KEY": "sk-myvault-456",
        }[key]
        mock_secrets_manager.myvault_enabled = True

        # Execute
        service = TraceService()

        # Verify - myVaultの値が優先される
        assert service._public_key == "pk-myvault-123"
        assert service._secret_key == "sk-myvault-456"
        assert service._is_enabled() is True

    @patch("app.services.trace_service.secrets_manager")
    @patch("app.services.trace_service.settings")
    def test_get_trace_url_with_myvault_keys(
        self, mock_settings_patch, mock_secrets_manager
    ):
        """Test trace URL generation with myVault keys."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-myvault-123",
            "LANGFUSE_SECRET_KEY": "sk-myvault-456",
        }[key]
        mock_secrets_manager.myvault_enabled = True

        service = TraceService()

        # Execute
        url = service.get_trace_url("trace-xyz789")

        # Verify
        assert (
            url
            == "http://localhost:3001/project/expertAgent-traces/traces/trace-xyz789"
        )

    @patch("app.services.trace_service.secrets_manager")
    @patch("app.services.trace_service.settings")
    @patch("app.services.trace_service.httpx.Client")
    def test_get_traces_with_myvault_keys(
        self, mock_client_class, mock_settings_patch, mock_secrets_manager
    ):
        """Test traces retrieval with myVault keys."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-myvault-123",
            "LANGFUSE_SECRET_KEY": "sk-myvault-456",
        }[key]
        mock_secrets_manager.myvault_enabled = True

        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"id": "trace-1", "name": "myvault_test"},
            ]
        }
        mock_response.raise_for_status = Mock()

        mock_instance = MagicMock()
        mock_instance.get.return_value = mock_response
        mock_instance.__enter__.return_value = mock_instance
        mock_instance.__exit__.return_value = None
        mock_client_class.return_value = mock_instance

        service = TraceService()

        # Execute
        traces = service.get_traces(limit=5)

        # Verify
        assert traces is not None
        assert len(traces) == 1
        assert traces[0]["name"] == "myvault_test"
        # Verify Basic Auth credentials were used
        call_args = mock_instance.get.call_args
        assert call_args[1]["auth"] == ("pk-myvault-123", "sk-myvault-456")
