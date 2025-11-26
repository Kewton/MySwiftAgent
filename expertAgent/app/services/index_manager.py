"""Secondary index manager for conversation filtering.

Issue #171: Diagnostic Information Retrieval API Implementation.
Manages Redis SET-based secondary indexes for efficient conversation lookup.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from app.services.valkey_client import ValkeyClient

logger = logging.getLogger(__name__)


class IndexManager:
    """Manages secondary indexes for conversation data in Valkey.

    Uses Redis SET data structures to maintain indexes by:
    - job_id: job_index:{job_id}
    - user_id: user_index:{user_id}
    - project_id: project_index:{project_id}
    - workflow_id: workflow_index:{workflow_id}
    - date: date_index:{YYYY-MM-DD}

    Each SET contains conversation_ids that match the filter criteria.

    Args:
        client: ValkeyClient instance for Redis operations
        index_prefix: Prefix for all index keys (default: "idx:")
        index_ttl: TTL for index entries in seconds (default: 7 days)

    Example:
        >>> async with ValkeyClient() as client:
        ...     manager = IndexManager(client)
        ...     await manager.add_to_indexes("conv-123", job_id="job-456")
        ...     conv_ids = await manager.get_by_job_id("job-456")
    """

    def __init__(
        self,
        client: ValkeyClient,
        index_prefix: str = "idx:",
        index_ttl: int = 604800,  # 7 days default
    ):
        """Initialize index manager.

        Args:
            client: ValkeyClient instance
            index_prefix: Prefix for all index keys
            index_ttl: TTL for index entries in seconds
        """
        self._client = client
        self.index_prefix = index_prefix
        self.index_ttl = index_ttl

    def _get_index_key(self, index_type: str, value: str) -> str:
        """Build the full index key name.

        Args:
            index_type: Type of index (job, user, project, workflow, date)
            value: Value to index by

        Returns:
            Full key name with prefix
        """
        return f"{self.index_prefix}{index_type}:{value}"

    async def add_to_indexes(
        self,
        conversation_id: str,
        job_id: Optional[str] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> int:
        """Add a conversation to all relevant indexes.

        Args:
            conversation_id: Conversation ID to index
            job_id: Job ID to index by
            user_id: User ID to index by
            project_id: Project ID to index by
            workflow_id: Workflow ID to index by
            created_at: Creation timestamp for date indexing

        Returns:
            Number of indexes the conversation was added to
        """
        indexes_added = 0

        if job_id:
            key = self._get_index_key("job", job_id)
            await self._add_to_set(key, conversation_id)
            indexes_added += 1

        if user_id:
            key = self._get_index_key("user", user_id)
            await self._add_to_set(key, conversation_id)
            indexes_added += 1

        if project_id:
            key = self._get_index_key("project", project_id)
            await self._add_to_set(key, conversation_id)
            indexes_added += 1

        if workflow_id:
            key = self._get_index_key("workflow", workflow_id)
            await self._add_to_set(key, conversation_id)
            indexes_added += 1

        if created_at:
            date_str = created_at.strftime("%Y-%m-%d")
            key = self._get_index_key("date", date_str)
            await self._add_to_set(key, conversation_id)
            indexes_added += 1

        logger.debug(
            f"Added conversation {conversation_id} to {indexes_added} indexes"
        )
        return indexes_added

    async def remove_from_indexes(
        self,
        conversation_id: str,
        job_id: Optional[str] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        created_at: Optional[datetime] = None,
    ) -> int:
        """Remove a conversation from all relevant indexes.

        Args:
            conversation_id: Conversation ID to remove
            job_id: Job ID to remove from
            user_id: User ID to remove from
            project_id: Project ID to remove from
            workflow_id: Workflow ID to remove from
            created_at: Creation timestamp for date index removal

        Returns:
            Number of indexes the conversation was removed from
        """
        indexes_removed = 0

        if job_id:
            key = self._get_index_key("job", job_id)
            await self._remove_from_set(key, conversation_id)
            indexes_removed += 1

        if user_id:
            key = self._get_index_key("user", user_id)
            await self._remove_from_set(key, conversation_id)
            indexes_removed += 1

        if project_id:
            key = self._get_index_key("project", project_id)
            await self._remove_from_set(key, conversation_id)
            indexes_removed += 1

        if workflow_id:
            key = self._get_index_key("workflow", workflow_id)
            await self._remove_from_set(key, conversation_id)
            indexes_removed += 1

        if created_at:
            date_str = created_at.strftime("%Y-%m-%d")
            key = self._get_index_key("date", date_str)
            await self._remove_from_set(key, conversation_id)
            indexes_removed += 1

        logger.debug(
            f"Removed conversation {conversation_id} from {indexes_removed} indexes"
        )
        return indexes_removed

    async def get_by_job_id(self, job_id: str) -> Set[str]:
        """Get all conversation IDs for a job.

        Args:
            job_id: Job ID to filter by

        Returns:
            Set of conversation IDs
        """
        key = self._get_index_key("job", job_id)
        return await self._get_set_members(key)

    async def get_by_user_id(self, user_id: str) -> Set[str]:
        """Get all conversation IDs for a user.

        Args:
            user_id: User ID to filter by

        Returns:
            Set of conversation IDs
        """
        key = self._get_index_key("user", user_id)
        return await self._get_set_members(key)

    async def get_by_project_id(self, project_id: str) -> Set[str]:
        """Get all conversation IDs for a project.

        Args:
            project_id: Project ID to filter by

        Returns:
            Set of conversation IDs
        """
        key = self._get_index_key("project", project_id)
        return await self._get_set_members(key)

    async def get_by_workflow_id(self, workflow_id: str) -> Set[str]:
        """Get all conversation IDs for a workflow.

        Args:
            workflow_id: Workflow ID to filter by

        Returns:
            Set of conversation IDs
        """
        key = self._get_index_key("workflow", workflow_id)
        return await self._get_set_members(key)

    async def get_by_date(self, date: datetime) -> Set[str]:
        """Get all conversation IDs for a specific date.

        Args:
            date: Date to filter by

        Returns:
            Set of conversation IDs
        """
        date_str = date.strftime("%Y-%m-%d")
        key = self._get_index_key("date", date_str)
        return await self._get_set_members(key)

    async def get_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> Set[str]:
        """Get all conversation IDs within a date range.

        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)

        Returns:
            Set of conversation IDs
        """
        result: Set[str] = set()
        current = start_date

        while current <= end_date:
            date_set = await self.get_by_date(current)
            result.update(date_set)
            current = datetime(
                current.year,
                current.month,
                current.day + 1,
                tzinfo=current.tzinfo,
            )
            # Handle month overflow
            try:
                current = current.replace(day=current.day)
            except ValueError:
                # Move to next month
                if current.month == 12:
                    current = current.replace(year=current.year + 1, month=1, day=1)
                else:
                    current = current.replace(month=current.month + 1, day=1)

        return result

    async def intersect_indexes(
        self,
        job_id: Optional[str] = None,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Set[str]:
        """Get conversation IDs that match ALL specified filters.

        Args:
            job_id: Filter by job ID
            user_id: Filter by user ID
            project_id: Filter by project ID
            workflow_id: Filter by workflow ID
            start_date: Filter by start date (inclusive)
            end_date: Filter by end date (inclusive)

        Returns:
            Set of conversation IDs matching all filters
        """
        sets: List[Set[str]] = []

        if job_id:
            sets.append(await self.get_by_job_id(job_id))

        if user_id:
            sets.append(await self.get_by_user_id(user_id))

        if project_id:
            sets.append(await self.get_by_project_id(project_id))

        if workflow_id:
            sets.append(await self.get_by_workflow_id(workflow_id))

        if start_date and end_date:
            sets.append(await self.get_by_date_range(start_date, end_date))

        if not sets:
            return set()

        # Return intersection of all sets
        result = sets[0]
        for s in sets[1:]:
            result = result.intersection(s)

        return result

    async def _add_to_set(self, key: str, member: str) -> bool:
        """Add a member to a SET and refresh TTL.

        Args:
            key: SET key
            member: Member to add

        Returns:
            True if successful
        """
        try:
            client = self._client._client
            if client is None:
                logger.error("Valkey client not connected")
                return False

            await client.sadd(key, member.encode("utf-8"))  # type: ignore[misc]
            await client.expire(key, self.index_ttl)
            return True
        except Exception as e:
            logger.error(f"Failed to add to set {key}: {e}")
            return False

    async def _remove_from_set(self, key: str, member: str) -> bool:
        """Remove a member from a SET.

        Args:
            key: SET key
            member: Member to remove

        Returns:
            True if successful
        """
        try:
            client = self._client._client
            if client is None:
                logger.error("Valkey client not connected")
                return False

            await client.srem(key, member.encode("utf-8"))  # type: ignore[misc]
            return True
        except Exception as e:
            logger.error(f"Failed to remove from set {key}: {e}")
            return False

    async def _get_set_members(self, key: str) -> Set[str]:
        """Get all members of a SET.

        Args:
            key: SET key

        Returns:
            Set of members
        """
        try:
            client = self._client._client
            if client is None:
                logger.error("Valkey client not connected")
                return set()

            members = await client.smembers(key)  # type: ignore[misc]
            return {
                m.decode("utf-8") if isinstance(m, bytes) else m
                for m in members
            }
        except Exception as e:
            logger.error(f"Failed to get set members for {key}: {e}")
            return set()

    async def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about indexes.

        Returns:
            Dictionary with index statistics
        """
        try:
            client = self._client._client
            if client is None:
                return {"error": "Client not connected"}

            # Get all index keys
            pattern = f"{self.index_prefix}*"
            keys = await client.keys(pattern)

            stats: Dict[str, int] = {
                "job_indexes": 0,
                "user_indexes": 0,
                "project_indexes": 0,
                "workflow_indexes": 0,
                "date_indexes": 0,
                "total_indexes": len(keys),
            }

            for key in keys:
                key_str = key.decode("utf-8") if isinstance(key, bytes) else key
                if ":job:" in key_str:
                    stats["job_indexes"] += 1
                elif ":user:" in key_str:
                    stats["user_indexes"] += 1
                elif ":project:" in key_str:
                    stats["project_indexes"] += 1
                elif ":workflow:" in key_str:
                    stats["workflow_indexes"] += 1
                elif ":date:" in key_str:
                    stats["date_indexes"] += 1

            return stats
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            return {"error": str(e)}
