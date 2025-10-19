"""Master creation node for job task generator.

This module provides the master creation node that creates TaskMasters,
JobMaster, and critically, JobMasterTask associations to link tasks to the workflow.
"""

import logging
from typing import Any

from core.config import settings

from ..state import JobTaskGeneratorState
from ..utils.jobqueue_client import JobqueueClient
from ..utils.schema_matcher import SchemaMatcher

logger = logging.getLogger(__name__)


async def master_creation_node(
    state: JobTaskGeneratorState,
) -> JobTaskGeneratorState:
    """Create TaskMasters, JobMaster, and JobMasterTask associations.

    This node performs the following:
    1. Creates TaskMasters for each task (or finds existing ones)
    2. Creates JobMaster for the workflow
    3. **Creates JobMasterTask associations** (critical!)
       - Links each TaskMaster to JobMaster with execution order
       - Sets is_required=True for all tasks
    4. Returns JobMaster ID and TaskMaster IDs

    Args:
        state: Current job task generator state

    Returns:
        Updated state with master IDs
    """
    logger.info("Starting master creation node")

    task_breakdown = state.get("task_breakdown", [])
    interface_definitions = state.get("interface_definitions", {})
    user_requirement = state["user_requirement"]

    if not task_breakdown:
        logger.error("Task breakdown is empty")
        return {
            **state,
            "error_message": "Task breakdown is required for master creation",
        }

    if not interface_definitions:
        logger.error("Interface definitions are empty")
        return {
            **state,
            "error_message": "Interface definitions are required for master creation",
        }

    logger.debug(f"Task breakdown count: {len(task_breakdown)}")
    logger.debug(f"Interface definitions count: {len(interface_definitions)}")

    try:
        # Initialize jobqueue client and schema matcher
        client = JobqueueClient()
        matcher = SchemaMatcher(client)

        # Step 1: Create TaskMasters
        task_masters: dict[str, dict[str, Any]] = {}

        for task in task_breakdown:
            task_id = task["task_id"]
            task_name = task["name"]

            logger.info(f"Creating TaskMaster for task {task_id}: {task_name}")

            # Get interface definitions
            if task_id not in interface_definitions:
                logger.error(f"Interface definition not found for task {task_id}")
                return {
                    **state,
                    "error_message": f"Interface definition not found for task {task_id}",
                }

            interface_def = interface_definitions[task_id]
            interface_master_id = interface_def["interface_master_id"]

            # For now, use the same interface for input and output
            # In a more sophisticated implementation, we would create separate interfaces
            input_interface_id = interface_master_id
            output_interface_id = interface_master_id

            # Get expertAgent base URL from settings
            # Falls back to http://localhost:8104 if not set
            task_url = f"{settings.EXPERTAGENT_BASE_URL}/api/v1/tasks/{task_id}"

            # Find or create TaskMaster
            task_master = await matcher.find_or_create_task_master(
                name=task_name,
                description=task["description"],
                method="POST",
                url=task_url,
                input_interface_id=input_interface_id,
                output_interface_id=output_interface_id,
                timeout_sec=60,
            )

            task_masters[task_id] = {
                "task_master_id": task_master["id"],
                "task_name": task_name,
                "order": task.get("priority", 5),  # Use priority as order hint
            }

            logger.info(
                f"TaskMaster created for task {task_id}: {task_master['id']} ({task_name})"
            )

        # Step 2: Create JobMaster
        job_name = f"Job: {user_requirement[:50]}"  # Truncate to 50 chars
        job_description = f"Auto-generated job from requirement: {user_requirement}"
        job_url = "http://localhost:8105/api/v1/graphai/execute"  # GraphAI execution endpoint

        logger.info(f"Creating JobMaster: {job_name}")

        job_master = await client.create_job_master(
            name=job_name,
            description=job_description,
            method="POST",
            url=job_url,
            timeout_sec=300,  # 5 minutes
        )

        job_master_id = job_master["id"]
        logger.info(f"JobMaster created: {job_master_id}")

        # Step 3: Create JobMasterTask associations (CRITICAL!)
        logger.info(f"Creating JobMasterTask associations for {len(task_masters)} tasks")

        # Sort tasks by their order (based on priority or dependency)
        sorted_tasks = sorted(
            task_masters.items(),
            key=lambda x: x[1]["order"]
        )

        for order, (task_id, task_info) in enumerate(sorted_tasks):
            task_master_id = task_info["task_master_id"]
            task_name = task_info["task_name"]

            logger.info(
                f"Adding task {task_id} ({task_name}) to workflow at order {order}"
            )

            # Add TaskMaster to JobMaster workflow
            job_master_task = await client.add_task_to_workflow(
                job_master_id=job_master_id,
                task_master_id=task_master_id,
                order=order,
                is_required=True,  # All tasks are required by default
                max_retries=3,
            )

            logger.info(
                f"JobMasterTask created: {job_master_task['id']} (order={order})"
            )

        # Update state
        return {
            **state,
            "job_master_id": job_master_id,
            "task_master_ids": [info["task_master_id"] for info in task_masters.values()],
            "retry_count": 0,
        }

    except Exception as e:
        logger.error(f"Failed to create masters: {e}", exc_info=True)
        return {
            **state,
            "error_message": f"Master creation failed: {str(e)}",
        }
