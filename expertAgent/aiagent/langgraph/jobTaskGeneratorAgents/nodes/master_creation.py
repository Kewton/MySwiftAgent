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
            logger.debug(f"Calling find_or_create_task_master for task {task_id}")
            task_master = await matcher.find_or_create_task_master(
                name=task_name,
                description=task["description"],
                method="POST",
                url=task_url,
                input_interface_id=input_interface_id,
                output_interface_id=output_interface_id,
                timeout_sec=60,
            )

            logger.debug(f"TaskMaster response for task {task_id}: {task_master}")

            # Validate response has 'id' field
            if "id" not in task_master:
                error_msg = (
                    f"TaskMaster response missing 'id' field for task {task_id}.\n"
                    f"Task name: {task_name}\n"
                    f"Response content: {task_master}\n"
                    f"Response keys: {list(task_master.keys()) if isinstance(task_master, dict) else 'Not a dict'}"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

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
        job_url = (
            "http://localhost:8105/api/v1/graphai/execute"  # GraphAI execution endpoint
        )

        logger.info(f"Creating JobMaster: {job_name}")

        job_master = await client.create_job_master(
            name=job_name,
            description=job_description,
            method="POST",
            url=job_url,
            timeout_sec=300,  # 5 minutes
        )

        logger.debug(f"JobMaster response: {job_master}")

        # Validate response has 'id' field
        if "id" not in job_master:
            error_msg = (
                f"JobMaster response missing 'id' field.\n"
                f"Job name: {job_name}\n"
                f"Response content: {job_master}\n"
                f"Response keys: {list(job_master.keys()) if isinstance(job_master, dict) else 'Not a dict'}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        job_master_id = job_master["id"]
        logger.info(f"JobMaster created successfully: {job_master_id}")

        # Step 3: Create JobMasterTask associations (CRITICAL!)
        logger.info(
            f"Creating JobMasterTask associations for {len(task_masters)} tasks"
        )

        # Sort tasks by their order (based on priority or dependency)
        sorted_tasks = sorted(task_masters.items(), key=lambda x: x[1]["order"])

        for order, (task_id, task_info) in enumerate(sorted_tasks):
            task_master_id = task_info["task_master_id"]
            task_name = task_info["task_name"]

            logger.info(
                f"Adding task {task_id} ({task_name}) to workflow at order {order}"
            )

            # Add TaskMaster to JobMaster workflow
            logger.debug(
                f"Calling add_task_to_workflow for task {task_id} "
                f"(job_master_id={job_master_id}, task_master_id={task_master_id}, order={order})"
            )
            job_master_task = await client.add_task_to_workflow(
                job_master_id=job_master_id,
                task_master_id=task_master_id,
                order=order,
                is_required=True,  # All tasks are required by default
                max_retries=3,
            )

            logger.debug(f"JobMasterTask response for task {task_id}: {job_master_task}")

            # Validate response has required fields
            # JobMasterTask may not have 'id', but should have task_master_id and job_master_id
            required_fields = ["task_master_id", "job_master_id"]
            missing_fields = [f for f in required_fields if f not in job_master_task]

            if missing_fields:
                error_msg = (
                    f"JobMasterTask response missing required fields {missing_fields} for task {task_id}.\n"
                    f"Response content: {job_master_task}\n"
                    f"Response keys: {list(job_master_task.keys()) if isinstance(job_master_task, dict) else 'Not a dict'}"
                )
                logger.error(error_msg)
                raise ValueError(error_msg)

            # Use task_master_id + order as identifier since JobMasterTask may not have separate 'id'
            task_identifier = f"{job_master_task['task_master_id']}@order{order}"
            logger.info(
                f"JobMasterTask created: {task_identifier} (task_master_id={job_master_task['task_master_id']}, order={order})"
            )

        # Update state
        logger.info("Master creation completed successfully")
        logger.info(f"Setting job_master_id={job_master_id} (type: {type(job_master_id).__name__})")
        logger.info(f"Setting task_master_ids count: {len(task_masters)}")

        updated_state = {
            **state,
            "job_master_id": job_master_id,
            "task_master_ids": [
                info["task_master_id"] for info in task_masters.values()
            ],
            "retry_count": 0,
        }
        logger.debug(f"Updated state job_master_id: {updated_state.get('job_master_id')}")
        return updated_state

    except Exception as e:
        logger.error(f"Failed to create masters: {e}", exc_info=True)
        logger.error(f"Exception type: {type(e).__name__}")
        logger.error(f"Exception args: {e.args}")
        return {
            **state,
            "error_message": f"Master creation failed: {type(e).__name__}: {str(e)}",
        }
