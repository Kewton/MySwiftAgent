"""Diagnostic API endpoints.

Issue #171: Diagnostic Information Retrieval API Implementation.
Provides REST endpoints for retrieving conversation diagnostic information.
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.schemas.diagnostic import (
    DiagnosticInfo,
    DiagnosticListQuery,
    DiagnosticListResponse,
)
from app.services.conversation_service import ConversationService
from app.services.index_manager import IndexManager
from app.services.valkey_client import ValkeyClient, ValkeyConnectionError
from app.stores.conversation_store_valkey import ConversationStoreValkey
from core.secrets import secrets_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat/diagnostics", tags=["Diagnostics"])


async def get_conversation_service() -> ConversationService:
    """Dependency to get ConversationService instance.

    Uses secrets_manager.get_connection_config() for myVault priority (Issue #252).

    Returns:
        ConversationService instance with connected store and index manager

    Raises:
        HTTPException: If unable to connect to Valkey
    """
    # Get Valkey connection settings via secrets_manager
    valkey_host = secrets_manager.get_connection_config(
        "VALKEY_HOST", value_type=str, default="localhost"
    )
    valkey_port = secrets_manager.get_connection_config(
        "VALKEY_PORT", value_type=int, default=6379
    )
    valkey_db = secrets_manager.get_connection_config(
        "VALKEY_DB", value_type=int, default=0
    )

    try:
        # Create and connect store
        store = ConversationStoreValkey(
            host=valkey_host,
            port=valkey_port,
            db=valkey_db,
        )
        await store.connect()

        # Create index manager
        valkey_client = ValkeyClient(
            host=valkey_host,
            port=valkey_port,
            db=valkey_db,
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


@router.get(
    "/{conversation_id}",
    response_model=DiagnosticInfo,
    summary="Get diagnostic info for a conversation",
    description="Retrieve diagnostic information for a single conversation by ID.",
    responses={
        200: {"description": "Diagnostic information retrieved successfully"},
        404: {"description": "Conversation not found"},
        503: {"description": "Storage service unavailable"},
    },
)
async def get_diagnostic_info(
    conversation_id: str,
    service: ConversationService = Depends(get_conversation_service),
) -> DiagnosticInfo:
    """Get diagnostic information for a single conversation.

    Args:
        conversation_id: Unique conversation identifier
        service: ConversationService (injected)

    Returns:
        DiagnosticInfo for the conversation

    Raises:
        HTTPException: 404 if conversation not found
    """
    try:
        info = await service.get_diagnostic_info(conversation_id)

        if not info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation not found: {conversation_id}",
            )

        return info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving diagnostic info: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve diagnostic info: {e}",
        ) from e


@router.get(
    "",
    response_model=DiagnosticListResponse,
    summary="List diagnostic info with filtering",
    description="Retrieve a list of diagnostic information with optional filtering and pagination.",
    responses={
        200: {"description": "List of diagnostic information retrieved successfully"},
        400: {"description": "Invalid query parameters"},
        503: {"description": "Storage service unavailable"},
    },
)
async def list_diagnostics(
    job_id: Optional[str] = Query(
        None,
        description="Filter by job ID",
        examples=["job-12345"],
    ),
    user_id: Optional[str] = Query(
        None,
        description="Filter by user ID",
        examples=["user-789"],
    ),
    project_id: Optional[str] = Query(
        None,
        description="Filter by project ID",
        examples=["project-456"],
    ),
    workflow_id: Optional[str] = Query(
        None,
        description="Filter by workflow ID",
        examples=["workflow-321"],
    ),
    start_date: Optional[datetime] = Query(
        None,
        description="Filter by start date (ISO format)",
        examples=["2025-01-01T00:00:00Z"],
    ),
    end_date: Optional[datetime] = Query(
        None,
        description="Filter by end date (ISO format)",
        examples=["2025-12-31T23:59:59Z"],
    ),
    limit: int = Query(
        100,
        description="Maximum number of results",
        ge=1,
        le=1000,
    ),
    offset: int = Query(
        0,
        description="Number of results to skip",
        ge=0,
    ),
    service: ConversationService = Depends(get_conversation_service),
) -> DiagnosticListResponse:
    """List diagnostic information with filtering and pagination.

    Args:
        job_id: Filter by job ID
        user_id: Filter by user ID
        project_id: Filter by project ID
        workflow_id: Filter by workflow ID
        start_date: Filter by start date
        end_date: Filter by end date
        limit: Maximum results
        offset: Pagination offset
        service: ConversationService (injected)

    Returns:
        DiagnosticListResponse with items and pagination info
    """
    # Validate date range
    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date",
        )

    try:
        query = DiagnosticListQuery(
            job_id=job_id,
            user_id=user_id,
            project_id=project_id,
            workflow_id=workflow_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )

        response = await service.list_diagnostics(query)
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing diagnostics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list diagnostics: {e}",
        ) from e
