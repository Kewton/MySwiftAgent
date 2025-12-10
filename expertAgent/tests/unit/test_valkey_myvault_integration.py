"""Tests for Valkey myVault integration (Issue #252).

Verifies that Valkey configuration is retrieved via secrets_manager.get_connection_config()
with myVault priority and environment variable fallback.
"""

import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestValkeyMyVaultIntegration:
    """Test suite for Valkey myVault integration."""

    # ========================================
    # main.py - lifespan Valkey initialization
    # ========================================

    def test_main_imports_secrets_manager(self) -> None:
        """main.py should import secrets_manager."""
        # Clear cached modules
        modules_to_clear = [
            key for key in sys.modules.keys() if key.startswith("app.main")
        ]
        for mod in modules_to_clear:
            del sys.modules[mod]

        from app import main

        # Check that secrets_manager is imported and available
        assert hasattr(main, "secrets_manager")

    @pytest.mark.asyncio
    async def test_main_lifespan_uses_get_connection_config_when_disabled(
        self,
    ) -> None:
        """Lifespan should use get_connection_config and not connect when disabled."""
        with (
            patch("app.main.secrets_manager.get_connection_config") as mock_get_config,
            patch("app.main.job_state_manager"),
            patch("app.main.ValkeyClient") as mock_valkey,
            patch("app.main.setup_logging"),
        ):
            # Configure mock to return False for VALKEY_ENABLED
            mock_get_config.return_value = False

            from app.main import lifespan

            # Create a mock app
            mock_app = MagicMock()

            # Run the lifespan
            async with lifespan(mock_app):
                pass

            # Verify get_connection_config was called for VALKEY_ENABLED
            mock_get_config.assert_called()
            calls = [call[0][0] for call in mock_get_config.call_args_list]
            assert "VALKEY_ENABLED" in calls

            # ValkeyClient should not be instantiated when disabled
            mock_valkey.assert_not_called()

    @pytest.mark.asyncio
    async def test_main_lifespan_uses_get_connection_config_when_enabled(self) -> None:
        """Lifespan should use get_connection_config for all Valkey settings."""
        with (
            patch("app.main.secrets_manager.get_connection_config") as mock_get_config,
            patch("app.main.job_state_manager") as mock_state_mgr,
            patch("app.main.ValkeyClient") as mock_valkey,
            patch("app.main.setup_logging"),
        ):
            # Configure mock to return values based on key
            def get_config_side_effect(key: str, **kwargs: Any) -> Any:
                config_map = {
                    "VALKEY_ENABLED": True,
                    "VALKEY_HOST": "test-host",
                    "VALKEY_PORT": 6380,
                    "VALKEY_DB": 1,
                    "VALKEY_TTL": 7200,
                }
                return config_map.get(key, kwargs.get("default"))

            mock_get_config.side_effect = get_config_side_effect

            # Mock async methods
            mock_state_mgr.connect_valkey = AsyncMock()
            mock_state_mgr.disconnect_valkey = AsyncMock()

            from app.main import lifespan

            # Create a mock app
            mock_app = MagicMock()

            # Run the lifespan
            async with lifespan(mock_app):
                pass

            # Verify get_connection_config was called for all config keys
            calls = [call[0][0] for call in mock_get_config.call_args_list]
            assert "VALKEY_ENABLED" in calls
            assert "VALKEY_HOST" in calls
            assert "VALKEY_PORT" in calls
            assert "VALKEY_DB" in calls
            assert "VALKEY_TTL" in calls

            # ValkeyClient should be instantiated with correct values
            mock_valkey.assert_called_once_with(
                host="test-host",
                port=6380,
                db=1,
            )

    # ========================================
    # ab_test_endpoints.py - get_ab_test_service
    # ========================================

    def test_ab_test_endpoints_imports_secrets_manager(self) -> None:
        """ab_test_endpoints.py should import secrets_manager."""
        from app.api.v1 import ab_test_endpoints

        assert hasattr(ab_test_endpoints, "secrets_manager")

    def test_ab_test_endpoints_uses_get_connection_config(self) -> None:
        """ab_test_endpoints.py should use get_connection_config for Valkey settings."""
        with (
            patch("app.api.v1.ab_test_endpoints.secrets_manager") as mock_secrets,
            patch("app.api.v1.ab_test_endpoints.ABTestService") as mock_service,
        ):

            def get_config_side_effect(key: str, **kwargs: Any) -> Any:
                config_map = {
                    "VALKEY_ENABLED": True,
                    "VALKEY_HOST": "ab-test-host",
                    "VALKEY_PORT": 6381,
                    "VALKEY_DB": 2,
                }
                return config_map.get(key, kwargs.get("default"))

            mock_secrets.get_connection_config.side_effect = get_config_side_effect

            # Reset the singleton for testing
            import app.api.v1.ab_test_endpoints as ab_test_module

            ab_test_module._ab_test_service = None

            # Get the service
            ab_test_module.get_ab_test_service()

            # Verify get_connection_config was called for each config
            calls = mock_secrets.get_connection_config.call_args_list
            call_keys = [call[0][0] for call in calls]
            assert "VALKEY_HOST" in call_keys
            assert "VALKEY_PORT" in call_keys
            assert "VALKEY_DB" in call_keys
            assert "VALKEY_ENABLED" in call_keys

            # Verify ABTestService was called with correct values
            mock_service.assert_called_once_with(
                valkey_host="ab-test-host",
                valkey_port=6381,
                valkey_db=2,
                use_valkey=True,
            )

    # ========================================
    # diagnostic_endpoints.py - get_conversation_service
    # ========================================

    def test_diagnostic_endpoints_imports_secrets_manager(self) -> None:
        """diagnostic_endpoints.py should import secrets_manager."""
        from app.api.v1 import diagnostic_endpoints

        assert hasattr(diagnostic_endpoints, "secrets_manager")

    @pytest.mark.asyncio
    async def test_diagnostic_endpoints_uses_get_connection_config(self) -> None:
        """diagnostic_endpoints.py should use get_connection_config for Valkey settings."""
        with (
            patch("app.api.v1.diagnostic_endpoints.secrets_manager") as mock_secrets,
            patch(
                "app.api.v1.diagnostic_endpoints.ConversationStoreValkey"
            ) as mock_store,
            patch("app.api.v1.diagnostic_endpoints.ValkeyClient") as mock_valkey,
            patch("app.api.v1.diagnostic_endpoints.IndexManager"),
            patch("app.api.v1.diagnostic_endpoints.ConversationService"),
        ):

            def get_config_side_effect(key: str, **kwargs: Any) -> Any:
                config_map = {
                    "VALKEY_HOST": "diagnostic-host",
                    "VALKEY_PORT": 6382,
                    "VALKEY_DB": 3,
                    "LANGFUSE_HOST": "http://langfuse:3000",
                }
                return config_map.get(key, kwargs.get("default"))

            mock_secrets.get_connection_config.side_effect = get_config_side_effect

            # Mock async methods
            mock_store_instance = MagicMock()
            mock_store_instance.connect = AsyncMock()
            mock_store.return_value = mock_store_instance

            mock_valkey_instance = MagicMock()
            mock_valkey_instance.connect = AsyncMock()
            mock_valkey.return_value = mock_valkey_instance

            from app.api.v1.diagnostic_endpoints import get_conversation_service

            # Call the function
            await get_conversation_service()

            # Verify get_connection_config was called
            calls = mock_secrets.get_connection_config.call_args_list
            call_keys = [call[0][0] for call in calls]
            assert "VALKEY_HOST" in call_keys
            assert "VALKEY_PORT" in call_keys
            assert "VALKEY_DB" in call_keys
            assert "LANGFUSE_HOST" in call_keys

            # Verify store and valkey client were created with correct values
            mock_store.assert_called_once_with(
                host="diagnostic-host",
                port=6382,
                db=3,
            )
            mock_valkey.assert_called_once_with(
                host="diagnostic-host",
                port=6382,
                db=3,
            )

    # ========================================
    # metrics_aggregation_service.py - MetricsAggregationService
    # ========================================

    def test_metrics_aggregation_service_imports_secrets_manager(self) -> None:
        """metrics_aggregation_service.py should import secrets_manager."""
        from app.services import metrics_aggregation_service

        assert hasattr(metrics_aggregation_service, "secrets_manager")

    def test_metrics_aggregation_service_code_uses_get_connection_config(self) -> None:
        """MetricsAggregationService code should call get_connection_config."""
        # Read the source file to verify the pattern is used
        import inspect

        from app.services.metrics_aggregation_service import MetricsAggregationService

        source = inspect.getsource(MetricsAggregationService.__init__)

        # Verify the code calls get_connection_config
        assert "secrets_manager.get_connection_config" in source
        assert "VALKEY_ENABLED" in source

    def test_metrics_aggregation_service_get_valkey_client_code_uses_get_connection_config(
        self,
    ) -> None:
        """MetricsAggregationService._get_valkey_client code should use get_connection_config."""
        # Read the source file to verify the pattern is used
        import inspect

        from app.services.metrics_aggregation_service import MetricsAggregationService

        source = inspect.getsource(MetricsAggregationService._get_valkey_client)

        # Verify the code calls get_connection_config
        assert "secrets_manager.get_connection_config" in source
        assert "VALKEY_HOST" in source
        assert "VALKEY_PORT" in source
        assert "VALKEY_DB" in source


class TestValkeyConfigFallback:
    """Test environment variable fallback behavior."""

    def test_fallback_to_default_when_not_found(self) -> None:
        """Should use default value when config not found."""
        from core.secrets import SecretsManager

        with (
            patch.object(SecretsManager, "__init__", return_value=None),
            patch.object(SecretsManager, "_get_from_myvault", return_value=None),
        ):
            manager = SecretsManager.__new__(SecretsManager)
            manager.myvault_enabled = False
            manager.myvault_client = None
            manager.settings = MagicMock()
            manager.settings.VALKEY_HOST = ""  # Empty env var
            manager._cache = {}
            manager.cache_ttl = 300

            # Should return default
            result = manager.get_connection_config(
                "VALKEY_HOST", value_type=str, default="fallback-host"
            )
            assert result == "fallback-host"

    def test_type_conversion_for_port(self) -> None:
        """Port should be converted to int."""
        from core.secrets import SecretsManager

        with (
            patch.object(SecretsManager, "__init__", return_value=None),
            patch.object(SecretsManager, "_get_from_myvault", return_value="6380"),
            patch.object(
                SecretsManager, "_validate_connection_config", return_value=None
            ),
        ):
            manager = SecretsManager.__new__(SecretsManager)
            manager.myvault_enabled = True
            manager.myvault_client = MagicMock()
            manager.settings = MagicMock()
            manager._cache = {}
            manager.cache_ttl = 300

            result = manager.get_connection_config(
                "VALKEY_PORT", value_type=int, default=6379
            )
            assert isinstance(result, int)
            assert result == 6380

    def test_type_conversion_for_enabled(self) -> None:
        """VALKEY_ENABLED should be converted to bool."""
        from core.secrets import SecretsManager

        with (
            patch.object(SecretsManager, "__init__", return_value=None),
            patch.object(SecretsManager, "_get_from_myvault", return_value="true"),
            patch.object(
                SecretsManager, "_validate_connection_config", return_value=None
            ),
        ):
            manager = SecretsManager.__new__(SecretsManager)
            manager.myvault_enabled = True
            manager.myvault_client = MagicMock()
            manager.settings = MagicMock()
            manager._cache = {}
            manager.cache_ttl = 300

            result = manager.get_connection_config(
                "VALKEY_ENABLED", value_type=bool, default=False
            )
            assert isinstance(result, bool)
            assert result is True


class TestValkeyConnectionLogging:
    """Test logging for Valkey connection configuration."""

    def test_logs_myvault_source_when_available(self) -> None:
        """Should log 'myvault' as source when value comes from myVault."""
        with patch("core.secrets.logger") as mock_logger:
            from core.secrets import SecretsManager

            with (
                patch.object(SecretsManager, "__init__", return_value=None),
                patch.object(
                    SecretsManager, "_get_from_myvault", return_value="myvault-host"
                ),
                patch.object(
                    SecretsManager, "_validate_connection_config", return_value=None
                ),
            ):
                manager = SecretsManager.__new__(SecretsManager)
                manager.myvault_enabled = True
                manager.myvault_client = MagicMock()
                manager.settings = MagicMock()
                manager.settings.VALKEY_HOST = ""
                manager._cache = {}
                manager.cache_ttl = 300

                # Call get_connection_config
                manager.get_connection_config("VALKEY_HOST", value_type=str)

                # Verify logging was called with myvault source
                mock_logger.info.assert_called()
                log_calls = [str(call) for call in mock_logger.info.call_args_list]
                # At least one call should mention myvault
                assert any("myvault" in call for call in log_calls)

    def test_logs_env_source_when_fallback(self) -> None:
        """Should log 'env' as source when value comes from environment."""
        with patch("core.secrets.logger") as mock_logger:
            from core.secrets import SecretsManager

            with (
                patch.object(SecretsManager, "__init__", return_value=None),
                patch.object(SecretsManager, "_get_from_myvault", return_value=None),
                patch.object(
                    SecretsManager, "_validate_connection_config", return_value=None
                ),
            ):
                manager = SecretsManager.__new__(SecretsManager)
                manager.myvault_enabled = True
                manager.myvault_client = MagicMock()
                # Create a real Settings-like object
                mock_settings = MagicMock()
                mock_settings.VALKEY_HOST = "env-host"
                manager.settings = mock_settings
                manager._cache = {}
                manager.cache_ttl = 300

                # Call get_connection_config
                result = manager.get_connection_config("VALKEY_HOST", value_type=str)

                # Value should be from env
                assert result == "env-host"

                # Verify logging was called with env source
                mock_logger.info.assert_called()
                log_calls = [str(call) for call in mock_logger.info.call_args_list]
                # At least one call should mention env
                assert any("env" in call for call in log_calls)


class TestHealthEndpointUsesSecretsManager:
    """Test that health endpoint uses secrets_manager."""

    @pytest.mark.asyncio
    async def test_health_check_uses_get_connection_config(self) -> None:
        """Health check should use secrets_manager for VALKEY_ENABLED."""
        with (
            patch("app.main.secrets_manager.get_connection_config") as mock_get_config,
            patch("app.main.job_state_manager") as mock_state_manager,
        ):
            mock_get_config.return_value = True
            mock_state_manager.is_valkey_connected = True

            from app.main import health_check

            result = await health_check()

            # Verify get_connection_config was called
            mock_get_config.assert_called()

            # Verify the response structure
            assert result["status"] == "healthy"
            assert result["valkey"]["enabled"] is True
            assert result["valkey"]["connected"] is True
