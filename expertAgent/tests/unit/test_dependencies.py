"""Unit tests for API v1 dependencies.

Issue #194: Centralized DI for ConversationService.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.conversation_service import ConversationService


class TestGetConversationService:
    """Tests for get_conversation_service dependency."""

    @pytest.mark.asyncio
    async def test_get_conversation_service_success(self):
        """Test successful creation of ConversationService."""
        from app.api.v1.dependencies import get_conversation_service

        with patch(
            "app.api.v1.dependencies.secrets_manager"
        ) as mock_secrets, patch(
            "app.api.v1.dependencies.ConversationStoreValkey"
        ) as mock_store_class, patch(
            "app.api.v1.dependencies.ValkeyClient"
        ) as mock_valkey_class, patch(
            "app.api.v1.dependencies.IndexManager"
        ) as mock_index_manager_class:
            # Setup mocks
            mock_secrets.get_connection_config.side_effect = lambda key, **kwargs: {
                "VALKEY_HOST": "localhost",
                "VALKEY_PORT": 6379,
                "VALKEY_DB": 0,
                "LANGFUSE_HOST": "http://localhost:3000",
            }.get(key, kwargs.get("default"))

            mock_store = AsyncMock()
            mock_store_class.return_value = mock_store

            mock_valkey = AsyncMock()
            mock_valkey_class.return_value = mock_valkey

            mock_index_manager = MagicMock()
            mock_index_manager_class.return_value = mock_index_manager

            # Execute
            service = await get_conversation_service()

            # Verify
            assert isinstance(service, ConversationService)
            mock_store.connect.assert_awaited_once()
            mock_valkey.connect.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_conversation_service_valkey_error(self):
        """Test handling of Valkey connection error."""
        from fastapi import HTTPException

        from app.api.v1.dependencies import get_conversation_service
        from app.services.valkey_client import ValkeyConnectionError

        with patch(
            "app.api.v1.dependencies.secrets_manager"
        ) as mock_secrets, patch(
            "app.api.v1.dependencies.ConversationStoreValkey"
        ) as mock_store_class:
            # Setup mocks
            mock_secrets.get_connection_config.side_effect = lambda key, **kwargs: {
                "VALKEY_HOST": "localhost",
                "VALKEY_PORT": 6379,
                "VALKEY_DB": 0,
            }.get(key, kwargs.get("default"))

            mock_store = AsyncMock()
            mock_store.connect.side_effect = ValkeyConnectionError(
                "Connection refused"
            )
            mock_store_class.return_value = mock_store

            # Execute and verify exception
            with pytest.raises(HTTPException) as exc_info:
                await get_conversation_service()

            assert exc_info.value.status_code == 503
            assert "unavailable" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_get_conversation_service_uses_myvault_config(self):
        """Test that secrets_manager is used for configuration."""
        from app.api.v1.dependencies import get_conversation_service

        with patch(
            "app.api.v1.dependencies.secrets_manager"
        ) as mock_secrets, patch(
            "app.api.v1.dependencies.ConversationStoreValkey"
        ) as mock_store_class, patch(
            "app.api.v1.dependencies.ValkeyClient"
        ) as mock_valkey_class, patch(
            "app.api.v1.dependencies.IndexManager"
        ):
            # Setup mocks with custom values from myVault
            mock_secrets.get_connection_config.side_effect = lambda key, **kwargs: {
                "VALKEY_HOST": "myvault-valkey-host",
                "VALKEY_PORT": 6380,
                "VALKEY_DB": 1,
                "LANGFUSE_HOST": "http://myvault-langfuse:3001",
            }.get(key, kwargs.get("default"))

            mock_store = AsyncMock()
            mock_store_class.return_value = mock_store

            mock_valkey = AsyncMock()
            mock_valkey_class.return_value = mock_valkey

            # Execute
            await get_conversation_service()

            # Verify secrets_manager was called for all configs
            calls = mock_secrets.get_connection_config.call_args_list
            keys_called = [call[0][0] for call in calls]

            assert "VALKEY_HOST" in keys_called
            assert "VALKEY_PORT" in keys_called
            assert "VALKEY_DB" in keys_called
            assert "LANGFUSE_HOST" in keys_called

            # Verify store was created with myVault values
            mock_store_class.assert_called_once_with(
                host="myvault-valkey-host",
                port=6380,
                db=1,
            )
