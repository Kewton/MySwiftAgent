"""Job registration node for job task generator.

This module provides the job registration node that creates a Job instance
from the validated JobMaster, making it executable.
"""

import logging
from datetime import datetime

from ..state import JobTaskGeneratorState
from ..utils.jobqueue_client import JobqueueClient

logger = logging.getLogger(__name__)


async def job_registration_node(
    state: JobTaskGeneratorState,
) -> JobTaskGeneratorState:
    """Register Job and make it executable.

    This node:
    1. Retrieves JobMasterTasks to get task execution order
    2. Constructs tasks parameter for Job creation
    3. Creates Job via jobqueue API
    4. Returns Job ID

    Args:
        state: Current job task generator state

    Returns:
        Updated state with job ID
    """
    logger.info("Starting job registration node")

    job_master_id = state.get("job_master_id")
    user_requirement = state["user_requirement"]

    if not job_master_id:
        logger.error("JobMaster ID is missing")
        return {
            **state,
            "error_message": "JobMaster ID is required for job registration",
        }

    logger.debug(f"Registering Job for JobMaster: {job_master_id}")

    try:
        # Initialize jobqueue client
        client = JobqueueClient()

        # Get JobMasterTasks to understand task execution order
        logger.info(f"Retrieving JobMasterTasks for JobMaster {job_master_id}")
        workflow_tasks = await client.list_workflow_tasks(job_master_id)

        if not workflow_tasks:
            logger.warning(
                "No workflow tasks found, creating Job without tasks parameter"
            )
            workflow_tasks = []

        logger.info(f"Found {len(workflow_tasks)} tasks in workflow")

        # Construct tasks parameter (optional, jobqueue can auto-generate from JobMasterTasks)
        # For now, we'll let jobqueue auto-generate tasks from JobMasterTasks
        # In a more sophisticated implementation, we would pass initial parameters here
        tasks = None

        # Create Job
        job_name = f"Job: {user_requirement[:50]} - {datetime.now().isoformat()}"
        priority = 5  # Default priority

        logger.info(f"Creating Job: {job_name}")

        job = await client.create_job(
            master_id=job_master_id,
            name=job_name,
            tasks=tasks,
            priority=priority,
            scheduled_at=None,  # Execute immediately
        )

        job_id = job["id"]
        logger.info(f"Job created successfully: {job_id}")

        # Return updated state with job ID
        return {
            **state,
            "job_id": job_id,
            "status": "completed",
            "retry_count": 0,
        }

    except Exception as e:
        logger.error(f"Failed to register job: {e}", exc_info=True)
        return {
            **state,
            "error_message": f"Job registration failed: {str(e)}",
        }
