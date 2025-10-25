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
    job_master = state.get("job_master")
    user_requirement = state["user_requirement"]

    if not job_master_id:
        logger.error("JobMaster ID is missing")
        return {
            **state,
            "error_message": "JobMaster ID is required for job registration",
        }

    if not job_master:
        logger.error("JobMaster data is missing in state")
        return {
            **state,
            "error_message": "JobMaster data is required for job registration",
        }

    logger.debug(f"Registering Job for JobMaster: {job_master_id}")
    logger.debug(
        f"JobMaster method: {job_master.get('method', 'POST')}, "
        f"url: {job_master.get('url', 'N/A')}"
    )

    try:
        # Get method and url from job_master with fallback defaults
        # This validation must happen BEFORE any API calls
        job_method = job_master.get("method", "POST")
        job_url = job_master.get("url")
        job_timeout_sec = job_master.get("timeout_sec", 120)

        if not job_url:
            logger.error("JobMaster url is missing")
            return {
                **state,
                "error_message": "JobMaster url is required for job registration",
            }

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

        # Create Job with method and url from JobMaster
        job_name = f"Job: {user_requirement[:50]} - {datetime.now().isoformat()}"
        priority = 5  # Default priority

        logger.info(f"Creating Job: {job_name}")
        logger.info(
            f"Job parameters: method={job_method}, url={job_url}, "
            f"timeout_sec={job_timeout_sec}"
        )

        job = await client.create_job(
            master_id=job_master_id,
            name=job_name,
            method=job_method,
            url=job_url,
            tasks=tasks,
            priority=priority,
            scheduled_at=None,  # Execute immediately
            timeout_sec=job_timeout_sec,
        )

        # JobResponse has 'job_id' field, not 'id'
        # Use defensive access to handle various response schemas
        job_id = job.get("job_id") or job.get("id")
        if not job_id:
            logger.error(
                f"Job creation response missing job_id field. "
                f"Response keys: {list(job.keys())}, "
                f"Response content: {job}"
            )
            raise ValueError(
                f"Job creation response missing job_id field. "
                f"Available keys: {list(job.keys())}"
            )
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
