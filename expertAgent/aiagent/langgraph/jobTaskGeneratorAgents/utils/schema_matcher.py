"""Schema matching utilities for finding existing InterfaceMasters and TaskMasters.

This module provides functions to search for existing schemas in jobqueue
to avoid creating duplicates. Initial implementation uses exact name/URL matching.
"""

from typing import Any

from aiagent.langgraph.jobTaskGeneratorAgents.utils.jobqueue_client import (
    JobqueueClient,
)


class SchemaMatcher:
    """Utility for matching and searching existing schemas in jobqueue.

    This class provides methods to find existing InterfaceMasters and TaskMasters
    by name and URL, helping to reuse existing definitions when possible.
    """

    def __init__(self, client: JobqueueClient):
        """Initialize schema matcher.

        Args:
            client: Jobqueue API client
        """
        self.client = client

    async def find_interface_master_by_name(
        self, name: str
    ) -> dict[str, Any] | None:
        """Find InterfaceMaster by exact name match.

        Args:
            name: Interface name to search for

        Returns:
            InterfaceMaster dict if found, None otherwise
        """
        try:
            result = await self.client.list_interface_masters(name=name, page=1, size=1)
            masters = result.get("masters", [])
            if masters:
                # Return first exact match
                for master in masters:
                    if master.get("name") == name:
                        return master
            return None
        except Exception:
            # If search fails, return None (will create new)
            return None

    async def find_task_master_by_name_and_url(
        self, name: str, url: str
    ) -> dict[str, Any] | None:
        """Find TaskMaster by exact name and URL match.

        Args:
            name: Task name to search for
            url: Task URL to search for

        Returns:
            TaskMaster dict if found, None otherwise
        """
        try:
            # First try to filter by name
            result = await self.client.list_task_masters(name=name, page=1, size=10)
            masters = result.get("masters", [])

            # Then check URL exact match
            for master in masters:
                if master.get("name") == name and master.get("url") == url:
                    return master

            return None
        except Exception:
            # If search fails, return None (will create new)
            return None

    async def find_or_create_interface_master(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        output_schema: dict[str, Any],
        created_by: str = "job_task_generator",
    ) -> dict[str, Any]:
        """Find existing InterfaceMaster or create new one.

        This is a convenience method that searches for existing InterfaceMaster
        and creates a new one if not found.

        Args:
            name: Interface name
            description: Interface description
            input_schema: JSON Schema for input
            output_schema: JSON Schema for output
            created_by: Creator identifier

        Returns:
            InterfaceMaster (existing or newly created)
        """
        # Try to find existing
        existing = await self.find_interface_master_by_name(name)
        if existing:
            return existing

        # Create new if not found
        return await self.client.create_interface_master(
            name=name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            created_by=created_by,
        )

    async def find_or_create_task_master(
        self,
        name: str,
        description: str,
        method: str,
        url: str,
        input_interface_id: str,
        output_interface_id: str,
        headers: dict | None = None,
        body_template: dict | None = None,
        timeout_sec: int = 30,
        created_by: str = "job_task_generator",
    ) -> dict[str, Any]:
        """Find existing TaskMaster or create new one.

        This is a convenience method that searches for existing TaskMaster
        by name and URL, and creates a new one if not found.

        Args:
            name: Task name
            description: Task description
            method: HTTP method
            url: API endpoint URL
            input_interface_id: Input InterfaceMaster ID
            output_interface_id: Output InterfaceMaster ID
            headers: HTTP headers (optional)
            body_template: Request body template (optional)
            timeout_sec: Timeout in seconds
            created_by: Creator identifier

        Returns:
            TaskMaster (existing or newly created)
        """
        # Try to find existing
        existing = await self.find_task_master_by_name_and_url(name, url)
        if existing:
            return existing

        # Create new if not found
        return await self.client.create_task_master(
            name=name,
            description=description,
            method=method,
            url=url,
            input_interface_id=input_interface_id,
            output_interface_id=output_interface_id,
            headers=headers,
            body_template=body_template,
            timeout_sec=timeout_sec,
            created_by=created_by,
        )

    async def batch_find_or_create_interfaces(
        self,
        interface_definitions: list[dict[str, Any]],
        created_by: str = "job_task_generator",
    ) -> list[dict[str, Any]]:
        """Batch process interface definitions, finding existing or creating new.

        Args:
            interface_definitions: List of interface definitions
            created_by: Creator identifier

        Returns:
            List of InterfaceMasters (existing or newly created)
        """
        results = []
        for interface_def in interface_definitions:
            result = await self.find_or_create_interface_master(
                name=interface_def["interface_name"],
                description=interface_def["description"],
                input_schema=interface_def["input_schema"],
                output_schema=interface_def["output_schema"],
                created_by=created_by,
            )
            results.append(result)
        return results
