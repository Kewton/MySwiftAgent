"""Conversation service for diagnostic data access.

Issue #171: Diagnostic Information Retrieval API Implementation.
Provides data access layer for conversation diagnostic information.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.schemas.conversation_metadata import ConversationMetadata
from app.schemas.diagnostic import (
    DiagnosticInfo,
    DiagnosticListQuery,
    DiagnosticListResponse,
    LangfuseLink,
    MessageInfo,
    TokenUsage,
)
from app.services.index_manager import IndexManager
from app.stores.conversation_store_valkey import ConversationStoreValkey
from core.config import settings

logger = logging.getLogger(__name__)


class ConversationService:
    """Service for accessing conversation diagnostic data.

    Provides methods to retrieve diagnostic information for single conversations
    or lists of conversations with filtering and pagination support.

    Args:
        store: ConversationStoreValkey instance
        index_manager: IndexManager instance for filtering
        langfuse_host: Langfuse host URL for trace links

    Example:
        >>> async with ConversationStoreValkey() as store:
        ...     service = ConversationService(store)
        ...     info = await service.get_diagnostic_info("conv-123")
    """

    def __init__(
        self,
        store: ConversationStoreValkey,
        index_manager: Optional[IndexManager] = None,
        langfuse_host: Optional[str] = None,
    ):
        """Initialize conversation service.

        Args:
            store: ConversationStoreValkey instance
            index_manager: IndexManager instance (will be created if not provided)
            langfuse_host: Langfuse host URL
        """
        self._store = store
        self._index_manager = index_manager
        self._langfuse_host = langfuse_host or getattr(
            settings, "LANGFUSE_HOST", "http://localhost:3000"
        )

    async def get_diagnostic_info(
        self, conversation_id: str
    ) -> Optional[DiagnosticInfo]:
        """Get diagnostic information for a single conversation.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            DiagnosticInfo object or None if not found
        """
        conversation = await self._store.get_conversation(conversation_id)
        if not conversation:
            return None

        return self._build_diagnostic_info(conversation_id, conversation)

    async def list_diagnostics(
        self, query: DiagnosticListQuery
    ) -> DiagnosticListResponse:
        """Get list of diagnostic information with filtering and pagination.

        Args:
            query: Query parameters for filtering and pagination

        Returns:
            DiagnosticListResponse with items and pagination info
        """
        # Get conversation IDs matching filters
        conversation_ids = await self._get_filtered_conversation_ids(query)

        # Sort by ID (which typically includes timestamp)
        sorted_ids = sorted(conversation_ids, reverse=True)

        # Apply pagination
        total = len(sorted_ids)
        paginated_ids = sorted_ids[query.offset : query.offset + query.limit]

        # Fetch diagnostic info for each conversation
        items: List[DiagnosticInfo] = []
        for conv_id in paginated_ids:
            info = await self.get_diagnostic_info(conv_id)
            if info:
                # Apply date range filter if needed
                if self._matches_date_filter(info, query):
                    items.append(info)

        return DiagnosticListResponse(
            items=items,
            total=total,
            limit=query.limit,
            offset=query.offset,
            has_more=query.offset + len(items) < total,
        )

    async def save_with_metadata(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]],
        metadata: ConversationMetadata,
    ) -> bool:
        """Save a conversation with extended metadata and update indexes.

        Args:
            conversation_id: Unique conversation identifier
            messages: List of conversation messages
            metadata: Extended metadata including job_id, user_id, etc.

        Returns:
            True if successful
        """
        # Build kwargs from metadata, excluding trace_id and prompt_version
        # since they are passed as explicit arguments
        metadata_dict = metadata.to_dict()
        metadata_dict.pop("trace_id", None)
        metadata_dict.pop("prompt_version", None)

        # Save conversation with metadata
        result = await self._store.save_conversation(
            conversation_id=conversation_id,
            messages=messages,
            trace_id=metadata.trace_id,
            prompt_version=metadata.prompt_version,
            **metadata_dict,
        )

        # Update indexes if we have an index manager
        if self._index_manager and result:
            await self._index_manager.add_to_indexes(
                conversation_id=conversation_id,
                job_id=metadata.job_id,
                user_id=metadata.user_id,
                project_id=metadata.project_id,
                workflow_id=metadata.workflow_id,
                created_at=metadata.created_at,
            )

        return result

    async def _get_filtered_conversation_ids(
        self, query: DiagnosticListQuery
    ) -> List[str]:
        """Get conversation IDs matching query filters.

        Args:
            query: Query parameters

        Returns:
            List of matching conversation IDs
        """
        if not self._index_manager:
            # Without index manager, we can't filter efficiently
            # Return empty list
            logger.warning("No index manager available for filtering")
            return []

        # Check if any filters are specified
        has_filters = any(
            [
                query.job_id,
                query.user_id,
                query.project_id,
                query.workflow_id,
                query.start_date,
                query.end_date,
            ]
        )

        if not has_filters:
            # No filters - return all conversations (limited by scan)
            return await self._scan_all_conversations()

        # Use index intersection for filtering
        result = await self._index_manager.intersect_indexes(
            job_id=query.job_id,
            user_id=query.user_id,
            project_id=query.project_id,
            workflow_id=query.workflow_id,
            start_date=query.start_date,
            end_date=query.end_date,
        )

        return list(result)

    async def _scan_all_conversations(self, limit: int = 1000) -> List[str]:
        """Scan for all conversation IDs (limited).

        Args:
            limit: Maximum number of conversations to return

        Returns:
            List of conversation IDs
        """
        try:
            client = self._store._client._client
            if client is None:
                return []

            pattern = f"{self._store.key_prefix}*"
            conversation_ids: List[str] = []

            cursor = 0
            while True:
                cursor, keys = await client.scan(
                    cursor=cursor, match=pattern, count=100
                )
                for key in keys:
                    key_str = key.decode("utf-8") if isinstance(key, bytes) else key
                    # Extract conversation ID from key
                    conv_id = key_str.replace(self._store.key_prefix, "")
                    conversation_ids.append(conv_id)

                    if len(conversation_ids) >= limit:
                        return conversation_ids

                if cursor == 0:
                    break

            return conversation_ids
        except Exception as e:
            logger.error(f"Failed to scan conversations: {e}")
            return []

    def _build_diagnostic_info(
        self, conversation_id: str, conversation: Dict[str, Any]
    ) -> DiagnosticInfo:
        """Build DiagnosticInfo from conversation data.

        Args:
            conversation_id: Conversation ID
            conversation: Raw conversation data from store

        Returns:
            DiagnosticInfo object
        """
        metadata = conversation.get("metadata", {})
        messages_data = conversation.get("messages", [])

        # Build message info list
        messages = [
            MessageInfo(
                role=msg.get("role", "unknown"),
                content=msg.get("content", ""),
                timestamp=self._parse_datetime(msg.get("timestamp")),
                tokens=msg.get("tokens"),
            )
            for msg in messages_data
        ]

        # Build token usage
        token_usage = TokenUsage(
            total_tokens=metadata.get("total_tokens", 0),
            input_tokens=metadata.get("input_tokens", 0),
            output_tokens=metadata.get("output_tokens", 0),
        )

        # Build Langfuse link
        trace_id = metadata.get("trace_id")
        langfuse_link = LangfuseLink(
            trace_id=trace_id,
            trace_url=(f"{self._langfuse_host}/trace/{trace_id}" if trace_id else None),
            session_id=metadata.get("session_id"),
        )

        return DiagnosticInfo(
            conversation_id=conversation_id,
            job_id=metadata.get("job_id"),
            user_id=metadata.get("user_id"),
            project_id=metadata.get("project_id"),
            workflow_id=metadata.get("workflow_id"),
            system_prompt=metadata.get("system_prompt"),
            messages=messages,
            token_usage=token_usage,
            langfuse_link=langfuse_link,
            prompt_version=metadata.get("prompt_version"),
            created_at=self._parse_datetime(metadata.get("created_at")),
            updated_at=self._parse_datetime(metadata.get("updated_at")),
            metadata={
                k: v
                for k, v in metadata.items()
                if k
                not in {
                    "trace_id",
                    "prompt_version",
                    "job_id",
                    "user_id",
                    "project_id",
                    "workflow_id",
                    "system_prompt",
                    "total_tokens",
                    "input_tokens",
                    "output_tokens",
                    "session_id",
                    "created_at",
                    "updated_at",
                }
            },
        )

    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime from various formats.

        Args:
            value: Value to parse

        Returns:
            Parsed datetime or None
        """
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                return None
        return None

    def _matches_date_filter(
        self, info: DiagnosticInfo, query: DiagnosticListQuery
    ) -> bool:
        """Check if diagnostic info matches date filter.

        Args:
            info: DiagnosticInfo to check
            query: Query with date filters

        Returns:
            True if matches or no date filter specified
        """
        if not info.created_at:
            # If no created_at, include in results
            return True

        if query.start_date and info.created_at < query.start_date:
            return False

        if query.end_date and info.created_at > query.end_date:
            return False

        return True
