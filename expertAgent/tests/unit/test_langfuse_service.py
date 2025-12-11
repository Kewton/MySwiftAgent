"""Unit tests for LangfuseService."""

import logging
from unittest.mock import Mock, patch

from app.services.langfuse_service import LangfuseService, langfuse_service


class TestLangfuseService:
    """Test LangfuseService functionality."""

    def test_singleton_pattern(self):
        """Test that LangfuseService follows singleton pattern."""
        instance1 = LangfuseService()
        instance2 = LangfuseService()
        assert instance1 is instance2

    def test_singleton_instance_is_created(self):
        """Test that langfuse_service singleton instance is created."""
        assert langfuse_service is not None
        assert isinstance(langfuse_service, LangfuseService)

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    @patch("app.services.langfuse_service.Langfuse")
    def test_initialization_enabled(
        self, mock_langfuse_class, mock_secrets_manager, mock_settings_patch
    ):
        """Test successful client initialization when Langfuse is enabled."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-test-123",
            "LANGFUSE_SECRET_KEY": "sk-test-456",
        }[key]
        # Mock get_connection_config to return the host (myVault or fallback)
        mock_secrets_manager.get_connection_config.return_value = (
            "http://localhost:3001"
        )

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        # Execute
        service = LangfuseService()

        # Verify
        mock_langfuse_class.assert_called_once_with(
            secret_key="sk-test-456",
            public_key="pk-test-123",
            host="http://localhost:3001",
        )
        assert service._client == mock_client

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    def test_initialization_disabled(self, mock_secrets_manager, mock_settings_patch):
        """Test that client is not initialized when Langfuse is disabled."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        # Simulate myVault not having keys (raises ValueError)
        mock_secrets_manager.get_secret.side_effect = ValueError("Secret not found")

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        # Execute
        service = LangfuseService()

        # Verify
        assert service._client is None

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    @patch("app.services.langfuse_service.Langfuse")
    def test_initialization_failure(
        self, mock_langfuse_class, mock_secrets_manager, mock_settings_patch
    ):
        """Test graceful handling of initialization failure."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-test-123",
            "LANGFUSE_SECRET_KEY": "sk-test-456",
        }[key]

        mock_langfuse_class.side_effect = Exception("Connection error")

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        # Execute
        service = LangfuseService()

        # Verify - should handle exception gracefully
        assert service._client is None

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    def test_initialization_valueerror_in_initialize_client(
        self, mock_secrets_manager, mock_settings_patch
    ):
        """Test graceful handling of ValueError during client initialization.

        This covers lines 86-88: ValueError exception handling in _initialize_client.
        """
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"

        # _is_enabled() returns True (both keys present)
        # but _initialize_client() raises ValueError on get_connection_config
        call_count = [0]

        def get_secret_side_effect(key):
            call_count[0] += 1
            # First two calls (from _is_enabled): return valid keys
            # Third+ calls (from _initialize_client): raise ValueError
            if call_count[0] <= 2:
                return {
                    "LANGFUSE_PUBLIC_KEY": "pk-test",
                    "LANGFUSE_SECRET_KEY": "sk-test",
                }[key]
            raise ValueError("Secret not found in myVault")

        mock_secrets_manager.get_secret.side_effect = get_secret_side_effect

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        # Execute
        service = LangfuseService()

        # Verify - should handle ValueError gracefully
        assert service._client is None

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    @patch("app.services.langfuse_service.CallbackHandler")
    def test_get_callback_handler_success(
        self, mock_callback_handler_class, mock_secrets_manager, mock_settings_patch
    ):
        """Test successful CallbackHandler creation with explicit public_key.

        Issue #263: CallbackHandler must receive public_key from myVault explicitly.
        Note: Langfuse v3 CallbackHandler only accepts public_key; secret_key and host
        are configured via the Langfuse client initialization.
        """
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-test-123",
            "LANGFUSE_SECRET_KEY": "sk-test-456",
        }[key]
        mock_secrets_manager.get_connection_config.return_value = (
            "http://localhost:3001"
        )

        mock_handler = Mock()
        mock_callback_handler_class.return_value = mock_handler

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        with patch("app.services.langfuse_service.Langfuse"):
            service = LangfuseService()
            service._client = Mock()  # Ensure client is set

            # Execute (Note: trace_name etc. are reserved for future use)
            handler = service.get_callback_handler(
                trace_name="test_trace",
                user_id="user123",
                session_id="session456",
                tags=["production", "chat"],
                metadata={"model": "gpt-4", "temperature": 0.7},
            )

            # Verify - Issue #263: CallbackHandler MUST be called with explicit public_key
            assert handler == mock_handler
            mock_callback_handler_class.assert_called_once_with(
                public_key="pk-test-123",
            )

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    def test_get_callback_handler_disabled(
        self, mock_secrets_manager, mock_settings_patch
    ):
        """Test CallbackHandler returns None when Langfuse is disabled."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = ValueError("Secret not found")

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        service = LangfuseService()

        # Execute
        handler = service.get_callback_handler(trace_name="test")

        # Verify
        assert handler is None

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    @patch("app.services.langfuse_service.CallbackHandler")
    def test_get_callback_handler_failure(
        self, mock_callback_handler_class, mock_secrets_manager, mock_settings_patch
    ):
        """Test graceful handling of CallbackHandler creation failure."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-test-123",
            "LANGFUSE_SECRET_KEY": "sk-test-456",
        }[key]
        mock_secrets_manager.get_connection_config.return_value = (
            "http://localhost:3001"
        )

        mock_callback_handler_class.side_effect = Exception("Handler creation error")

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        with patch("app.services.langfuse_service.Langfuse"):
            service = LangfuseService()
            service._client = Mock()

            # Execute
            handler = service.get_callback_handler(trace_name="test")

            # Verify - should return None on error
            assert handler is None

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    @patch("app.services.langfuse_service.CallbackHandler")
    def test_get_callback_handler_with_defaults(
        self, mock_callback_handler_class, mock_secrets_manager, mock_settings_patch
    ):
        """Test CallbackHandler creation with default parameters.

        Issue #263: CallbackHandler receives explicit public_key regardless of other params.
        """
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-test-123",
            "LANGFUSE_SECRET_KEY": "sk-test-456",
        }[key]
        mock_secrets_manager.get_connection_config.return_value = (
            "http://localhost:3001"
        )

        mock_handler = Mock()
        mock_callback_handler_class.return_value = mock_handler

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        with patch("app.services.langfuse_service.Langfuse"):
            service = LangfuseService()
            service._client = Mock()

            # Execute - only trace_name provided
            handler = service.get_callback_handler(trace_name="test_trace")

            # Verify - Issue #263: CallbackHandler is created with explicit public_key
            assert handler == mock_handler
            mock_callback_handler_class.assert_called_once_with(
                public_key="pk-test-123",
            )

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    def test_score_trace_success(self, mock_secrets_manager, mock_settings_patch):
        """Test successful trace scoring."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-test-123",
            "LANGFUSE_SECRET_KEY": "sk-test-456",
        }[key]

        mock_client = Mock()

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        with patch("app.services.langfuse_service.Langfuse"):
            service = LangfuseService()
            service._client = mock_client

            # Execute
            result = service.score_trace(
                trace_id="trace-abc123",
                name="user_rating",
                value=0.9,
                comment="Very helpful response",
            )

            # Verify
            assert result is True
            mock_client.score.assert_called_once_with(
                trace_id="trace-abc123",
                name="user_rating",
                value=0.9,
                comment="Very helpful response",
            )

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    def test_score_trace_disabled(self, mock_secrets_manager, mock_settings_patch):
        """Test score_trace returns False when Langfuse is disabled."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = ValueError("Secret not found")

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        service = LangfuseService()

        # Execute
        result = service.score_trace(trace_id="trace-123", name="rating", value=0.8)

        # Verify
        assert result is False

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    def test_score_trace_failure(self, mock_secrets_manager, mock_settings_patch):
        """Test graceful handling of score_trace failure."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-test-123",
            "LANGFUSE_SECRET_KEY": "sk-test-456",
        }[key]

        mock_client = Mock()
        mock_client.score.side_effect = Exception("Score API error")

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        with patch("app.services.langfuse_service.Langfuse"):
            service = LangfuseService()
            service._client = mock_client

            # Execute
            result = service.score_trace(trace_id="trace-123", name="rating", value=0.8)

            # Verify - should return False on error
            assert result is False

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    def test_score_trace_without_comment(
        self, mock_secrets_manager, mock_settings_patch
    ):
        """Test score_trace without optional comment."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-test-123",
            "LANGFUSE_SECRET_KEY": "sk-test-456",
        }[key]

        mock_client = Mock()

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        with patch("app.services.langfuse_service.Langfuse"):
            service = LangfuseService()
            service._client = mock_client

            # Execute - no comment
            result = service.score_trace(trace_id="trace-123", name="rating", value=0.8)

            # Verify
            assert result is True
            mock_client.score.assert_called_once_with(
                trace_id="trace-123",
                name="rating",
                value=0.8,
                comment=None,
            )

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    def test_flush_success(self, mock_secrets_manager, mock_settings_patch):
        """Test successful flush of pending traces."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-test-123",
            "LANGFUSE_SECRET_KEY": "sk-test-456",
        }[key]

        mock_client = Mock()

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        with patch("app.services.langfuse_service.Langfuse"):
            service = LangfuseService()
            service._client = mock_client

            # Execute
            service.flush()

            # Verify
            mock_client.flush.assert_called_once()

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    def test_flush_no_client(self, mock_secrets_manager, mock_settings_patch):
        """Test flush when client is None."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = ValueError("Secret not found")

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        service = LangfuseService()

        # Execute - should not raise error
        service.flush()
        # No assertion needed - just verify no exception

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    def test_flush_failure(self, mock_secrets_manager, mock_settings_patch):
        """Test graceful handling of flush failure."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-test-123",
            "LANGFUSE_SECRET_KEY": "sk-test-456",
        }[key]

        mock_client = Mock()
        mock_client.flush.side_effect = Exception("Flush error")

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        with patch("app.services.langfuse_service.Langfuse"):
            service = LangfuseService()
            service._client = mock_client

            # Execute - should not raise error
            service.flush()
            # No assertion needed - just verify no exception

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    def test_shutdown_success(self, mock_secrets_manager, mock_settings_patch):
        """Test successful shutdown."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-test-123",
            "LANGFUSE_SECRET_KEY": "sk-test-456",
        }[key]

        mock_client = Mock()

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        with patch("app.services.langfuse_service.Langfuse"):
            service = LangfuseService()
            service._client = mock_client

            # Execute
            service.shutdown()

            # Verify - should call flush during shutdown
            mock_client.flush.assert_called_once()

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    def test_shutdown_no_client(self, mock_secrets_manager, mock_settings_patch):
        """Test shutdown when client is None."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = ValueError("Secret not found")

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        service = LangfuseService()

        # Execute - should not raise error
        service.shutdown()
        # No assertion needed - just verify no exception

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    def test_shutdown_failure(self, mock_secrets_manager, mock_settings_patch):
        """Test graceful handling of shutdown failure."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-test-123",
            "LANGFUSE_SECRET_KEY": "sk-test-456",
        }[key]

        mock_client = Mock()
        mock_client.flush.side_effect = Exception("Shutdown error")

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        with patch("app.services.langfuse_service.Langfuse"):
            service = LangfuseService()
            service._client = mock_client

            # Execute - should not raise error
            service.shutdown()
            # No assertion needed - just verify no exception

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    def test_shutdown_exception_in_flush_call(
        self, mock_secrets_manager, mock_settings_patch
    ):
        """Test shutdown handles exception from flush() call gracefully.

        This covers lines 218-219: Exception handling in shutdown method.
        The flush() method itself catches exceptions, but if flush() raises
        an exception that escapes, shutdown() should handle it.
        """
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-test-123",
            "LANGFUSE_SECRET_KEY": "sk-test-456",
        }[key]

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        with patch("app.services.langfuse_service.Langfuse"):
            service = LangfuseService()
            service._client = Mock()

            # Mock flush method on the service instance to raise exception
            with patch.object(service, "flush", side_effect=Exception("Flush error")):
                # Execute - should not raise error
                service.shutdown()
                # No assertion needed - just verify no exception

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    def test_is_enabled_with_keys(self, mock_secrets_manager, mock_settings_patch):
        """Test _is_enabled returns True when keys are set."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-test-123",
            "LANGFUSE_SECRET_KEY": "sk-test-456",
        }[key]

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        with patch("app.services.langfuse_service.Langfuse"):
            service = LangfuseService()

            # Execute
            result = service._is_enabled()

            # Verify
            assert result is True

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    def test_is_enabled_without_keys(self, mock_secrets_manager, mock_settings_patch):
        """Test _is_enabled returns False when keys are missing."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = ValueError("Secret not found")

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        service = LangfuseService()

        # Execute
        result = service._is_enabled()

        # Verify
        assert result is False

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    def test_is_enabled_with_partial_keys(
        self, mock_secrets_manager, mock_settings_patch
    ):
        """Test _is_enabled returns False when only one key is set."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"

        # Simulate only LANGFUSE_PUBLIC_KEY available
        def get_secret_side_effect(key):
            if key == "LANGFUSE_PUBLIC_KEY":
                return "pk-test-123"
            else:
                raise ValueError("Secret not found")

        mock_secrets_manager.get_secret.side_effect = get_secret_side_effect

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        service = LangfuseService()

        # Execute
        result = service._is_enabled()

        # Verify
        assert result is False

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    @patch("app.services.langfuse_service.Langfuse")
    def test_initialization_with_myvault_host(
        self, mock_langfuse_class, mock_secrets_manager, mock_settings_patch
    ):
        """Test initialization uses myVault LANGFUSE_HOST when available."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://env-fallback:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-test-123",
            "LANGFUSE_SECRET_KEY": "sk-test-456",
        }[key]
        # myVault returns custom host
        mock_secrets_manager.get_connection_config.return_value = (
            "http://myvault-host:3001"
        )

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        # Execute
        service = LangfuseService()

        # Verify - should use myVault host
        mock_secrets_manager.get_connection_config.assert_called_once_with(
            "LANGFUSE_HOST",
            value_type=str,
            default="http://env-fallback:3001",
        )
        mock_langfuse_class.assert_called_once_with(
            secret_key="sk-test-456",
            public_key="pk-test-123",
            host="http://myvault-host:3001",
        )
        assert service._client == mock_client

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    @patch("app.services.langfuse_service.Langfuse")
    def test_initialization_with_env_fallback(
        self, mock_langfuse_class, mock_secrets_manager, mock_settings_patch
    ):
        """Test initialization falls back to env LANGFUSE_HOST when myVault has no value."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://env-fallback:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-test-123",
            "LANGFUSE_SECRET_KEY": "sk-test-456",
        }[key]
        # myVault returns fallback (env var value)
        mock_secrets_manager.get_connection_config.return_value = (
            "http://env-fallback:3001"
        )

        mock_client = Mock()
        mock_langfuse_class.return_value = mock_client

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        # Execute
        service = LangfuseService()

        # Verify - should use env fallback
        mock_secrets_manager.get_connection_config.assert_called_once_with(
            "LANGFUSE_HOST",
            value_type=str,
            default="http://env-fallback:3001",
        )
        mock_langfuse_class.assert_called_once_with(
            secret_key="sk-test-456",
            public_key="pk-test-123",
            host="http://env-fallback:3001",
        )
        assert service._client == mock_client


class TestCallbackHandlerWithMyVaultKeys:
    """Tests for Issue #263: CallbackHandler with myVault API keys."""

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    @patch("app.services.langfuse_service.CallbackHandler")
    def test_callback_handler_with_myvault_public_key(
        self, mock_callback_handler_class, mock_secrets_manager, mock_settings_patch
    ):
        """Test CallbackHandler receives public_key explicitly from myVault.

        Issue #263: CallbackHandler must use myVault public_key explicitly.
        Note: Langfuse v3 CallbackHandler only accepts public_key; secret_key and host
        are configured via the Langfuse client initialization.
        """
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-lf-myvault-12345678",
            "LANGFUSE_SECRET_KEY": "sk-lf-myvault-87654321",
        }[key]
        mock_secrets_manager.get_connection_config.return_value = (
            "http://localhost:3001"
        )

        mock_handler = Mock()
        mock_callback_handler_class.return_value = mock_handler

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        with patch("app.services.langfuse_service.Langfuse"):
            service = LangfuseService()
            service._client = Mock()

            # Execute
            handler = service.get_callback_handler()

            # Verify - CallbackHandler MUST be called with explicit public_key
            assert handler == mock_handler
            mock_callback_handler_class.assert_called_once_with(
                public_key="pk-lf-myvault-12345678",
            )

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    def test_callback_handler_disabled_when_no_keys(
        self, mock_secrets_manager, mock_settings_patch
    ):
        """Test CallbackHandler returns None when no API keys are available.

        Issue #263: When myVault and env vars have no keys, should not error.
        """
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = ValueError("Secret not found")

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        service = LangfuseService()

        # Execute
        handler = service.get_callback_handler()

        # Verify - should return None, no errors
        assert handler is None

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    @patch("app.services.langfuse_service.CallbackHandler")
    def test_callback_handler_logs_partial_key(
        self,
        mock_callback_handler_class,
        mock_secrets_manager,
        mock_settings_patch,
        caplog,
    ):
        """Test CallbackHandler creation logs partial API key for debugging.

        Issue #263: Log first 8 characters of public_key for debugging.
        """
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-lf-test-abcd1234",
            "LANGFUSE_SECRET_KEY": "sk-lf-test-efgh5678",
        }[key]
        mock_secrets_manager.get_connection_config.return_value = (
            "http://localhost:3001"
        )

        mock_handler = Mock()
        mock_callback_handler_class.return_value = mock_handler

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        with patch("app.services.langfuse_service.Langfuse"):
            service = LangfuseService()
            service._client = Mock()

            # Execute with log capture
            with caplog.at_level(logging.DEBUG):
                handler = service.get_callback_handler()

            # Verify - log should contain partial key (first 8 chars)
            assert handler == mock_handler
            # Check that log contains masked key information
            log_messages = [record.message for record in caplog.records]
            assert any("pk-lf-te" in msg for msg in log_messages), (
                f"Expected partial key 'pk-lf-te' in logs, got: {log_messages}"
            )

    @patch("app.services.langfuse_service.settings")
    @patch("app.services.langfuse_service.secrets_manager")
    @patch("app.services.langfuse_service.CallbackHandler")
    def test_callback_handler_with_different_public_keys(
        self, mock_callback_handler_class, mock_secrets_manager, mock_settings_patch
    ):
        """Test CallbackHandler uses the correct public_key from myVault.

        Issue #263: Verify public_key is correctly passed to CallbackHandler.
        Note: In Langfuse v3, host is configured via Langfuse client, not CallbackHandler.
        """
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://env-default:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-custom-12345678",
            "LANGFUSE_SECRET_KEY": "sk-custom-87654321",
        }[key]
        # myVault returns custom host (used by Langfuse client, not CallbackHandler)
        mock_secrets_manager.get_connection_config.return_value = (
            "http://myvault-langfuse:3001"
        )

        mock_handler = Mock()
        mock_callback_handler_class.return_value = mock_handler

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        with patch("app.services.langfuse_service.Langfuse"):
            service = LangfuseService()
            service._client = Mock()

            # Execute
            handler = service.get_callback_handler()

            # Verify - CallbackHandler receives the correct public_key
            assert handler == mock_handler
            mock_callback_handler_class.assert_called_once_with(
                public_key="pk-custom-12345678",
            )
