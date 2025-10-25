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
    # interface_definitions is expected to be a dict mapping task_id to interface data
    interface_definitions_raw: Any = state.get("interface_definitions", {})
    interface_definitions: dict = (
        interface_definitions_raw if isinstance(interface_definitions_raw, dict) else {}
    )
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

        # Step 1: Create TaskMasters with interface chaining
        task_masters: dict[str, dict[str, Any]] = {}

        # Sort tasks by priority to establish execution order
        sorted_tasks = sorted(task_breakdown, key=lambda t: t.get("priority", 5))
        logger.info(
            f"Sorted {len(sorted_tasks)} tasks by priority for interface chaining"
        )

        # Initialize prev_output_interface_id for chaining
        prev_output_interface_id: str | None = None

        for order, task in enumerate(sorted_tasks):
            task_id = task["task_id"]
            task_name = task["name"]

            logger.info(
                f"Creating TaskMaster for task {task_id}: {task_name} (order={order})"
            )

            # Get interface definitions
            if task_id not in interface_definitions:
                logger.error(f"Interface definition not found for task {task_id}")
                return {
                    **state,
                    "error_message": f"Interface definition not found for task {task_id}",
                }

            interface_def = interface_definitions[task_id]

            # Get interface IDs with fallback to interface_master_id (backward compatibility)
            interface_master_id = interface_def["interface_master_id"]
            interface_input_id = interface_def.get(
                "input_interface_id", interface_master_id
            )
            interface_output_id = interface_def.get(
                "output_interface_id", interface_master_id
            )

            # Implement task chaining logic
            if order == 0:
                # First task: use its own input/output interface IDs
                input_interface_id = interface_input_id
                output_interface_id = interface_output_id
                logger.info(
                    f"  First task: input={input_interface_id}, output={output_interface_id}"
                )
            else:
                # Subsequent tasks: chain from previous task's output
                input_interface_id = prev_output_interface_id
                output_interface_id = interface_output_id
                logger.info(
                    f"  Chained task: input={input_interface_id} (from prev task), "
                    f"output={output_interface_id}"
                )

            # Get expertAgent base URL from settings
            # Falls back to http://localhost:8104 if not set
            task_url = f"{settings.EXPERTAGENT_BASE_URL}/api/v1/tasks/{task_id}"

            # Find or create TaskMaster with strict interface matching
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
                "order": order,
                "input_interface_id": input_interface_id,
                "output_interface_id": output_interface_id,
            }

            logger.info(
                f"TaskMaster created for task {task_id}: {task_master['id']} ({task_name})\n"
                f"  Interface chain: input={input_interface_id} → output={output_interface_id}"
            )

            # Update prev_output_interface_id for next task
            prev_output_interface_id = output_interface_id
            logger.debug(
                f"  Updated prev_output_interface_id: {prev_output_interface_id}"
            )

        # Step 2: Create JobMaster
        job_name = f"Job: {user_requirement[:50]}"  # Truncate to 50 chars
        job_description = f"Auto-generated job from requirement: {user_requirement}"
        job_method = "POST"
        job_url = (
            "http://localhost:8105/api/v1/graphai/execute"  # GraphAI execution endpoint
        )
        job_timeout_sec = 300  # 5 minutes

        logger.info(f"Creating JobMaster: {job_name}")

        job_master = await client.create_job_master(
            name=job_name,
            description=job_description,
            method=job_method,
            url=job_url,
            timeout_sec=job_timeout_sec,
        )

        job_master_id = job_master["id"]
        logger.info(f"JobMaster created: {job_master_id}")

        # Step 3: Create JobMasterTask associations (CRITICAL!)
        logger.info(
            f"Creating JobMasterTask associations for {len(task_masters)} tasks"
        )

        # Sort tasks by their order (already determined in Step 1)
        sorted_task_items = sorted(task_masters.items(), key=lambda x: x[1]["order"])

        for task_id, task_info in sorted_task_items:
            task_master_id = task_info["task_master_id"]
            task_name = task_info["task_name"]
            order = task_info["order"]

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

        # Update state with job_master data for job_registration
        # Note: job_master API response only includes id/name/is_active,
        # so we use the parameters we sent during creation
        return {
            **state,
            "job_master": {
                "id": job_master_id,
                "name": job_name,
                "method": job_method,
                "url": job_url,
                "timeout_sec": job_timeout_sec,
            },
            "job_master_id": job_master_id,
            "task_master_ids": [
                info["task_master_id"] for info in task_masters.values()
            ],
            "retry_count": 0,
        }

    except Exception as e:
        # Provide detailed error information for debugging
        logger.error(f"Failed to create masters: {e}", exc_info=True)
        logger.error(
            f"Master creation context: "
            f"task_breakdown_count={len(task_breakdown)}, "
            f"interface_definitions_count={len(interface_definitions)}, "
            f"task_masters_created={len(task_masters) if 'task_masters' in locals() else 0}, "
            f"job_master_id={'set' if 'job_master_id' in locals() else 'not_set'}"
        )
        return {
            **state,
            "error_message": f"Master creation failed: {str(e)}. "
            f"Task masters created: {len(task_masters) if 'task_masters' in locals() else 0}/{len(task_breakdown)}",
        }
