"""Task data fetcher for Workflow Generator Agent.

This module fetches TaskMaster and InterfaceMaster data from jobqueue API.
"""

from typing import Any

from aiagent.langgraph.jobTaskGeneratorAgents.utils.jobqueue_client import (
    JobqueueClient,
)


class TaskDataFetcher:
    """Fetches TaskMaster and InterfaceMaster data from jobqueue API."""

    def __init__(self, jobqueue_client: JobqueueClient | None = None):
        """Initialize TaskDataFetcher.

        Args:
            jobqueue_client: JobqueueClient instance. If None, creates new instance.
        """
        self.jobqueue_client = jobqueue_client or JobqueueClient()

    async def fetch_task_masters_by_job_master_id(
        self, job_master_id: str
    ) -> list[dict[str, Any]]:
        """Fetch all TaskMasters associated with JobMaster.

        Args:
            job_master_id: JobMaster ID (ULID string format, e.g., 'jm_01K8K13NFD90PFCMB56C6EBKZQ')

        Returns:
            List of TaskMaster data with InterfaceMaster information

        Raises:
            JobqueueAPIError: If API returns error
        """
        # 1. Fetch JobMaster to verify existence
        _ = await self.jobqueue_client.get_job_master(job_master_id)

        # 2. Fetch workflow tasks (JobMasterTask)
        workflow_tasks = await self.jobqueue_client.list_workflow_tasks(job_master_id)

        # 3. Fetch each TaskMaster with InterfaceMasters
        task_data_list: list[dict[str, Any]] = []
        for workflow_task in workflow_tasks:
            task_master_id = workflow_task["task_master_id"]
            task_data = await self._fetch_task_master_with_interfaces(task_master_id)
            task_data["order"] = workflow_task[
                "order"
            ]  # Add execution order from JobMasterTask
            task_data["is_required"] = workflow_task.get("is_required", True)
            task_data["max_retries"] = workflow_task.get("max_retries", 3)
            task_data_list.append(task_data)

        # Sort by execution order
        task_data_list.sort(key=lambda x: x["order"])

        return task_data_list

    async def fetch_task_master_by_id(self, task_master_id: str) -> dict[str, Any]:
        """Fetch single TaskMaster by ID.

        Args:
            task_master_id: TaskMaster ID (ULID string format, e.g., 'tm_01K8K13NC8PRJ3V4R35C1AP2JP')

        Returns:
            TaskMaster data with InterfaceMaster information

        Raises:
            JobqueueAPIError: If API returns error
        """
        return await self._fetch_task_master_with_interfaces(task_master_id)

    async def _fetch_task_master_with_interfaces(
        self, task_master_id: str
    ) -> dict[str, Any]:
        """Fetch TaskMaster with its InterfaceMasters.

        Args:
            task_master_id: TaskMaster ID

        Returns:
            TaskMaster data with input_interface and output_interface details
        """
        # Fetch TaskMaster
        task_master = await self.jobqueue_client.get_task_master(task_master_id)

        # Fetch Input InterfaceMaster
        input_interface_id = task_master["input_interface_id"]
        input_interface = await self.jobqueue_client.get_interface_master(
            input_interface_id
        )

        # Fetch Output InterfaceMaster
        output_interface_id = task_master["output_interface_id"]
        output_interface = await self.jobqueue_client.get_interface_master(
            output_interface_id
        )

        # Combine data
        return {
            "task_master_id": task_master["id"],
            "name": task_master["name"],
            "description": task_master["description"],
            "method": task_master["method"],
            "url": task_master["url"],
            "headers": task_master.get("headers", {}),
            "body_template": task_master.get("body_template"),
            "timeout_sec": task_master.get("timeout_sec", 30),
            "input_interface": {
                "id": input_interface["id"],
                "name": input_interface["name"],
                "description": input_interface["description"],
                "schema": input_interface["input_schema"],
            },
            "output_interface": {
                "id": output_interface["id"],
                "name": output_interface["name"],
                "description": output_interface["description"],
                "schema": output_interface["output_schema"],
            },
        }
