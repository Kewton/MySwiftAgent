"""Unit tests for LangfuseService."""

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
        mock_secrets_manager.get_connection_config.return_value = "http://localhost:3001"

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
    @patch("app.services.langfuse_service.CallbackHandler")
    def test_get_callback_handler_success(
        self, mock_callback_handler_class, mock_secrets_manager, mock_settings_patch
    ):
        """Test successful CallbackHandler creation (Langfuse v3 - no args)."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-test-123",
            "LANGFUSE_SECRET_KEY": "sk-test-456",
        }[key]

        mock_handler = Mock()
        mock_callback_handler_class.return_value = mock_handler

        # Reset singleton instance
        LangfuseService._instance = None
        LangfuseService._client = None

        with patch("app.services.langfuse_service.Langfuse"):
            service = LangfuseService()
            service._client = Mock()  # Ensure client is set

            # Execute (Note: Langfuse v3 ignores these parameters)
            handler = service.get_callback_handler(
                trace_name="test_trace",
                user_id="user123",
                session_id="session456",
                tags=["production", "chat"],
                metadata={"model": "gpt-4", "temperature": 0.7},
            )

            # Verify - Langfuse v3 CallbackHandler is created without arguments
            assert handler == mock_handler
            mock_callback_handler_class.assert_called_once_with()

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
        """Test CallbackHandler creation with default parameters (v3 - no args)."""
        # Setup
        mock_settings_patch.LANGFUSE_HOST = "http://localhost:3001"
        mock_secrets_manager.get_secret.side_effect = lambda key: {
            "LANGFUSE_PUBLIC_KEY": "pk-test-123",
            "LANGFUSE_SECRET_KEY": "sk-test-456",
        }[key]

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

            # Verify - Langfuse v3 ignores parameters and creates without args
            assert handler == mock_handler
            mock_callback_handler_class.assert_called_once_with()

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
