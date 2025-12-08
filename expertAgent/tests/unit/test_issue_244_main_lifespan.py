"""Unit tests for Issue #244: Valkey initialization in main.py.

Tests for:
- JobCreationStateManager.configure_valkey() method
- JobCreationStateManager.is_valkey_connected property
- /health endpoint Valkey status
- main.py lifespan Valkey initialization
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.services.job_creation_state import (
    DEFAULT_TTL_SECONDS,
    JobCreationStateManager,
)


class TestConfigureValkey:
    """Test JobCreationStateManager.configure_valkey() method."""

    @pytest.mark.unit
    def test_configure_valkey_sets_client(self) -> None:
        """Test configure_valkey sets the Valkey client."""
        manager = JobCreationStateManager()
        mock_client = MagicMock()

        manager.configure_valkey(mock_client)

        assert manager._valkey_client is mock_client

    @pytest.mark.unit
    def test_configure_valkey_sets_default_ttl(self) -> None:
        """Test configure_valkey uses default TTL when not specified."""
        manager = JobCreationStateManager()
        mock_client = MagicMock()

        manager.configure_valkey(mock_client)

        assert manager._ttl_seconds == DEFAULT_TTL_SECONDS

    @pytest.mark.unit
    def test_configure_valkey_sets_custom_ttl(self) -> None:
        """Test configure_valkey sets custom TTL."""
        manager = JobCreationStateManager()
        mock_client = MagicMock()

        manager.configure_valkey(mock_client, ttl_seconds=3600)

        assert manager._ttl_seconds == 3600

    @pytest.mark.unit
    def test_configure_valkey_logs_message(self, caplog: pytest.LogCaptureFixture) -> None:
        """Test configure_valkey logs configuration message."""
        import logging

        caplog.set_level(logging.INFO)
        manager = JobCreationStateManager()
        mock_client = MagicMock()

        manager.configure_valkey(mock_client, ttl_seconds=7200)

        assert "Valkey client configured" in caplog.text
        assert "7200" in caplog.text


class TestIsValkeyConnected:
    """Test JobCreationStateManager.is_valkey_connected property."""

    @pytest.mark.unit
    def test_is_valkey_connected_initially_false(self) -> None:
        """Test is_valkey_connected is False initially."""
        manager = JobCreationStateManager()

        assert manager.is_valkey_connected is False

    @pytest.mark.unit
    async def test_is_valkey_connected_true_after_connect(self) -> None:
        """Test is_valkey_connected is True after successful connection."""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        manager = JobCreationStateManager(valkey_client=mock_client)

        await manager.connect_valkey()

        assert manager.is_valkey_connected is True

    @pytest.mark.unit
    async def test_is_valkey_connected_false_after_disconnect(self) -> None:
        """Test is_valkey_connected is False after disconnect."""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.disconnect = AsyncMock()
        manager = JobCreationStateManager(valkey_client=mock_client)

        await manager.connect_valkey()
        await manager.disconnect_valkey()

        assert manager.is_valkey_connected is False

    @pytest.mark.unit
    async def test_is_valkey_connected_false_on_connection_failure(self) -> None:
        """Test is_valkey_connected is False when connection fails."""
        mock_client = MagicMock()
        mock_client.connect = AsyncMock(side_effect=Exception("Connection failed"))
        manager = JobCreationStateManager(valkey_client=mock_client)

        await manager.connect_valkey()

        assert manager.is_valkey_connected is False


class TestHealthEndpoint:
    """Test /health endpoint with Valkey status."""

    @pytest.mark.unit
    async def test_health_includes_valkey_status_when_enabled(self) -> None:
        """Test /health returns Valkey status when enabled."""
        # Patch secrets_manager and job_state_manager
        with (
            patch(
                "app.main.secrets_manager.get_connection_config"
            ) as mock_get_config,
            patch("app.main.job_state_manager") as mock_manager,
        ):
            mock_get_config.return_value = True
            mock_manager.is_valkey_connected = True

            # Import app after patching
            from app.main import app

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "expertAgent"
            assert "valkey" in data
            assert data["valkey"]["enabled"] is True
            assert data["valkey"]["connected"] is True

    @pytest.mark.unit
    async def test_health_includes_valkey_status_when_disabled(self) -> None:
        """Test /health returns Valkey status when disabled."""
        with (
            patch(
                "app.main.secrets_manager.get_connection_config"
            ) as mock_get_config,
            patch("app.main.job_state_manager") as mock_manager,
        ):
            mock_get_config.return_value = False
            mock_manager.is_valkey_connected = False

            from app.main import app

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/health")

            assert response.status_code == 200
            data = response.json()
            assert "valkey" in data
            assert data["valkey"]["enabled"] is False
            assert data["valkey"]["connected"] is False


class TestLifespanValkeyInit:
    """Test main.py lifespan Valkey initialization."""

    @pytest.mark.unit
    async def test_lifespan_initializes_valkey_when_enabled(self) -> None:
        """Test lifespan initializes Valkey when VALKEY_ENABLED=true."""
        mock_valkey_client = MagicMock()
        mock_valkey_client.connect = AsyncMock()

        def get_config_side_effect(key, **kwargs):
            config_map = {
                "VALKEY_ENABLED": True,
                "VALKEY_HOST": "localhost",
                "VALKEY_PORT": 6379,
                "VALKEY_DB": 0,
                "VALKEY_TTL": 86400,
            }
            return config_map.get(key, kwargs.get("default"))

        with (
            patch(
                "app.main.secrets_manager.get_connection_config"
            ) as mock_get_config,
            patch(
                "app.main.ValkeyClient", return_value=mock_valkey_client
            ) as mock_valkey_class,
            patch("app.main.job_state_manager") as mock_manager,
            patch("app.main.setup_logging"),
        ):
            mock_get_config.side_effect = get_config_side_effect
            mock_manager.configure_valkey = MagicMock()
            mock_manager.connect_valkey = AsyncMock()
            mock_manager.disconnect_valkey = AsyncMock()

            from app.main import lifespan

            app = FastAPI()
            async with lifespan(app):
                # Verify ValkeyClient was created with correct params
                mock_valkey_class.assert_called_once_with(
                    host="localhost",
                    port=6379,
                    db=0,
                )
                # Verify configure_valkey was called
                mock_manager.configure_valkey.assert_called_once_with(
                    mock_valkey_client, 86400
                )
                # Verify connect_valkey was called
                mock_manager.connect_valkey.assert_awaited_once()

            # Verify disconnect_valkey was called on shutdown
            mock_manager.disconnect_valkey.assert_awaited_once()

    @pytest.mark.unit
    async def test_lifespan_skips_valkey_when_disabled(self) -> None:
        """Test lifespan skips Valkey when VALKEY_ENABLED=false."""
        with (
            patch(
                "app.main.secrets_manager.get_connection_config"
            ) as mock_get_config,
            patch("app.main.ValkeyClient") as mock_valkey_class,
            patch("app.main.job_state_manager") as mock_manager,
            patch("app.main.setup_logging"),
        ):
            mock_get_config.return_value = False
            mock_manager.configure_valkey = MagicMock()
            mock_manager.connect_valkey = AsyncMock()
            mock_manager.disconnect_valkey = AsyncMock()

            from app.main import lifespan

            app = FastAPI()
            async with lifespan(app):
                # ValkeyClient should NOT be created
                mock_valkey_class.assert_not_called()
                # configure_valkey should NOT be called
                mock_manager.configure_valkey.assert_not_called()
                # connect_valkey should NOT be called
                mock_manager.connect_valkey.assert_not_awaited()

            # disconnect_valkey should NOT be called
            mock_manager.disconnect_valkey.assert_not_awaited()

    @pytest.mark.unit
    async def test_lifespan_logs_valkey_disabled_message(self) -> None:
        """Test lifespan logs message when Valkey is disabled."""
        with (
            patch(
                "app.main.secrets_manager.get_connection_config"
            ) as mock_get_config,
            patch("app.main.job_state_manager") as mock_manager,
            patch("app.main.logger") as mock_logger,
            patch("app.main.setup_logging"),
        ):
            mock_get_config.return_value = False
            mock_manager.configure_valkey = MagicMock()
            mock_manager.connect_valkey = AsyncMock()
            mock_manager.disconnect_valkey = AsyncMock()

            from app.main import lifespan

            app = FastAPI()
            async with lifespan(app):
                pass

            # Verify that logger.info was called with the expected message
            mock_logger.info.assert_any_call(
                "Valkey disabled - JobCreationStateManager using L1 cache only"
            )
