"""Centralized dependencies for API v1 endpoints.

Issue #194: Provides shared dependency injection functions for services.
"""

import logging
from dataclasses import dataclass

from fastapi import HTTPException, status

from app.services.conversation_service import ConversationService
from app.services.index_manager import IndexManager
from app.services.valkey_client import ValkeyClient, ValkeyConnectionError
from app.stores.conversation_store_valkey import ConversationStoreValkey
from core.secrets import secrets_manager

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ValkeyConfig:
    """Valkey connection configuration.

    Immutable dataclass for Valkey connection parameters.
    """

    host: str
    port: int
    db: int


def _get_valkey_config() -> ValkeyConfig:
    """Get Valkey connection configuration from secrets_manager.

    Returns:
        ValkeyConfig with host, port, and db from myVault or defaults.
    """
    return ValkeyConfig(
        host=secrets_manager.get_connection_config(
            "VALKEY_HOST", value_type=str, default="localhost"
        ),
        port=secrets_manager.get_connection_config(
            "VALKEY_PORT", value_type=int, default=6379
        ),
        db=secrets_manager.get_connection_config(
            "VALKEY_DB", value_type=int, default=0
        ),
    )


async def get_conversation_service() -> ConversationService:
    """Dependency to get ConversationService instance.

    Uses secrets_manager.get_connection_config() for myVault priority (Issue #252).
    Centralized from diagnostic_endpoints.py to be reused in chat_endpoints.py.

    Returns:
        ConversationService instance with connected store and index manager

    Raises:
        HTTPException: If unable to connect to Valkey

    Example:
        >>> @router.post("/chat")
        ... async def chat(
        ...     service: ConversationService = Depends(get_conversation_service)
        ... ):
        ...     await service.save_with_metadata(...)
    """
    # Get Valkey connection settings via secrets_manager (DRY)
    config = _get_valkey_config()

    try:
        # Create and connect store
        store = ConversationStoreValkey(
            host=config.host,
            port=config.port,
            db=config.db,
        )
        await store.connect()

        # Create index manager with same connection settings
        valkey_client = ValkeyClient(
            host=config.host,
            port=config.port,
            db=config.db,
        )
        await valkey_client.connect()
        index_manager = IndexManager(valkey_client)

        # Create service - also use secrets_manager for LANGFUSE_HOST
        langfuse_host = secrets_manager.get_connection_config(
            "LANGFUSE_HOST", value_type=str, default="http://localhost:3000"
        )
        service = ConversationService(
            store=store,
            index_manager=index_manager,
            langfuse_host=langfuse_host,
        )

        return service

    except ValkeyConnectionError as e:
        logger.error(f"Failed to connect to Valkey: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Storage service unavailable: {e}",
        ) from e
