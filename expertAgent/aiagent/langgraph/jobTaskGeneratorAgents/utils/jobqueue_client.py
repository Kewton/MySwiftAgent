"""Jobqueue API client for Job/Task auto-generation agent.

This module provides a comprehensive client for interacting with jobqueue APIs:
- InterfaceMaster CRUD
- TaskMaster CRUD
- JobMaster CRUD
- JobMasterTask CRUD
- Workflow validation
- Job creation
"""

import os
from typing import Any

import httpx


class JobqueueAPIError(Exception):
    """Exception raised when jobqueue API returns an error."""

    def __init__(
        self, status_code: int, message: str, response_body: dict | None = None
    ):
        self.status_code = status_code
        self.message = message
        self.response_body = response_body
        super().__init__(f"Jobqueue API error ({status_code}): {message}")


class JobqueueClient:
    """Client for jobqueue API operations.

    This client provides methods for all CRUD operations on jobqueue entities:
    - InterfaceMaster
    - TaskMaster
    - JobMaster
    - JobMasterTask
    - Job

    Plus workflow validation functionality.

    Attributes:
        base_url: Base URL for jobqueue API (from JOBQUEUE_API_URL env var)
        timeout: Request timeout in seconds (default: 30)
    """

    def __init__(self, base_url: str | None = None, timeout: float = 30.0):
        """Initialize jobqueue client.

        Args:
            base_url: Base URL for jobqueue API. If None, reads from JOBQUEUE_API_URL env var
            timeout: Request timeout in seconds
        """
        self.base_url = (
            base_url or os.getenv("JOBQUEUE_API_URL") or "http://localhost:8101"
        )
        self.timeout = timeout

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        """Execute HTTP request to jobqueue API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (e.g., '/api/v1/interface-masters')
            json: Request body (for POST/PUT)
            params: Query parameters (for GET)

        Returns:
            Response JSON

        Raises:
            JobqueueAPIError: If API returns error status
        """
        url = f"{self.base_url}{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                json=json,
                params=params,
            )

            if response.status_code >= 400:
                try:
                    error_body = response.json()
                except Exception:
                    error_body = None
                raise JobqueueAPIError(
                    status_code=response.status_code,
                    message=response.text,
                    response_body=error_body,
                )

            return response.json()

    # ===== InterfaceMaster =====

    async def create_interface_master(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        output_schema: dict[str, Any],
        created_by: str = "job_task_generator",
    ) -> dict:
        """Create new InterfaceMaster.

        Args:
            name: Interface name
            description: Interface description
            input_schema: JSON Schema for input
            output_schema: JSON Schema for output
            created_by: Creator identifier

        Returns:
            Created InterfaceMaster
        """
        return await self._request(
            "POST",
            "/api/v1/interface-masters",
            json={
                "name": name,
                "description": description,
                "input_schema": input_schema,
                "output_schema": output_schema,
                "created_by": created_by,
            },
        )

    async def list_interface_masters(
        self, name: str | None = None, page: int = 1, size: int = 100
    ) -> dict:
        """List InterfaceMasters with pagination.

        Args:
            name: Filter by name (optional)
            page: Page number (1-indexed)
            size: Page size

        Returns:
            Paginated list of InterfaceMasters
        """
        params: dict = {"page": page, "size": size}
        if name:
            params["name"] = name
        return await self._request("GET", "/api/v1/interface-masters", params=params)

    async def get_interface_master(self, master_id: str) -> dict:
        """Get InterfaceMaster by ID.

        Args:
            master_id: InterfaceMaster ID

        Returns:
            InterfaceMaster details
        """
        return await self._request("GET", f"/api/v1/interface-masters/{master_id}")

    # ===== TaskMaster =====

    async def create_task_master(
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
    ) -> dict:
        """Create new TaskMaster.

        Args:
            name: Task name
            description: Task description
            method: HTTP method (GET, POST, etc.)
            url: API endpoint URL
            input_interface_id: Input InterfaceMaster ID
            output_interface_id: Output InterfaceMaster ID
            headers: HTTP headers (optional)
            body_template: Request body template (optional)
            timeout_sec: Timeout in seconds
            created_by: Creator identifier

        Returns:
            Created TaskMaster
        """
        return await self._request(
            "POST",
            "/api/v1/task-masters",
            json={
                "name": name,
                "description": description,
                "method": method,
                "url": url,
                "input_interface_id": input_interface_id,
                "output_interface_id": output_interface_id,
                "headers": headers or {},
                "body_template": body_template,
                "timeout_sec": timeout_sec,
                "created_by": created_by,
            },
        )

    async def list_task_masters(
        self,
        name: str | None = None,
        url: str | None = None,
        page: int = 1,
        size: int = 100,
    ) -> dict:
        """List TaskMasters with pagination.

        Args:
            name: Filter by name (optional)
            url: Filter by URL (optional)
            page: Page number (1-indexed)
            size: Page size

        Returns:
            Paginated list of TaskMasters
        """
        params: dict = {"page": page, "size": size}
        if name:
            params["name"] = name
        if url:
            params["url"] = url
        return await self._request("GET", "/api/v1/task-masters", params=params)

    async def get_task_master(self, master_id: str) -> dict:
        """Get TaskMaster by ID.

        Args:
            master_id: TaskMaster ID

        Returns:
            TaskMaster details
        """
        return await self._request("GET", f"/api/v1/task-masters/{master_id}")

    # ===== JobMaster =====

    async def create_job_master(
        self,
        name: str,
        description: str,
        method: str,
        url: str,
        timeout_sec: int = 120,
        created_by: str = "job_task_generator",
    ) -> dict:
        """Create new JobMaster.

        Args:
            name: Job name
            description: Job description
            method: HTTP method (typically "POST")
            url: Workflow entry point URL
            timeout_sec: Timeout in seconds
            created_by: Creator identifier

        Returns:
            Created JobMaster
        """
        return await self._request(
            "POST",
            "/api/v1/job-masters",
            json={
                "name": name,
                "description": description,
                "method": method,
                "url": url,
                "timeout_sec": timeout_sec,
                "created_by": created_by,
            },
        )

    async def list_job_masters(
        self, name: str | None = None, page: int = 1, size: int = 100
    ) -> dict:
        """List JobMasters with pagination.

        Args:
            name: Filter by name (optional)
            page: Page number (1-indexed)
            size: Page size

        Returns:
            Paginated list of JobMasters
        """
        params: dict = {"page": page, "size": size}
        if name:
            params["name"] = name
        return await self._request("GET", "/api/v1/job-masters", params=params)

    async def get_job_master(self, master_id: str) -> dict:
        """Get JobMaster by ID.

        Args:
            master_id: JobMaster ID

        Returns:
            JobMaster details
        """
        return await self._request("GET", f"/api/v1/job-masters/{master_id}")

    # ===== JobMasterTask =====

    async def add_task_to_workflow(
        self,
        job_master_id: str,
        task_master_id: str,
        order: int,
        is_required: bool = True,
        max_retries: int = 3,
    ) -> dict:
        """Add TaskMaster to JobMaster workflow.

        Args:
            job_master_id: JobMaster ID
            task_master_id: TaskMaster ID to add
            order: Execution order (0-indexed)
            is_required: Whether task is required for Job success
            max_retries: Maximum retry count on failure

        Returns:
            Created JobMasterTask
        """
        return await self._request(
            "POST",
            f"/api/v1/job-masters/{job_master_id}/tasks",
            json={
                "task_master_id": task_master_id,
                "order": order,
                "is_required": is_required,
                "max_retries": max_retries,
            },
        )

    async def list_workflow_tasks(self, job_master_id: str) -> list[dict]:
        """List all tasks in JobMaster workflow.

        Args:
            job_master_id: JobMaster ID

        Returns:
            List of JobMasterTasks in execution order
        """
        response = await self._request(
            "GET", f"/api/v1/job-masters/{job_master_id}/tasks"
        )
        return response.get("tasks", [])

    # ===== Workflow Validation =====

    async def validate_workflow(self, job_master_id: str) -> dict:
        """Validate workflow interface compatibility.

        Args:
            job_master_id: JobMaster ID to validate

        Returns:
            Validation result with errors and warnings
        """
        return await self._request(
            "GET", f"/api/v1/job-masters/{job_master_id}/validate-workflow"
        )

    # ===== Job =====

    async def create_job(
        self,
        master_id: str,
        name: str,
        tasks: list[dict] | None = None,
        priority: int = 5,
        scheduled_at: str | None = None,
    ) -> dict:
        """Create new Job.

        Args:
            master_id: JobMaster ID
            name: Job name
            tasks: Task parameters (optional, if None, will be auto-generated from JobMasterTask)
            priority: Job priority (1=highest, 10=lowest)
            scheduled_at: Scheduled execution time (ISO 8601 format, optional)

        Returns:
            Created Job
        """
        return await self._request(
            "POST",
            "/api/v1/jobs",
            json={
                "master_id": master_id,
                "name": name,
                "tasks": tasks,
                "priority": priority,
                "scheduled_at": scheduled_at,
            },
        )

    async def get_job(self, job_id: str) -> dict:
        """Get Job by ID.

        Args:
            job_id: Job ID

        Returns:
            Job details
        """
        return await self._request("GET", f"/api/v1/jobs/{job_id}")
