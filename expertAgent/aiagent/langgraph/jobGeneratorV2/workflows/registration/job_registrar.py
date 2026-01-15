"""Job registrar sub-workflow for Registration.

This module provides the JobRegistrarSubWorkflow that:
1. Retrieves JobMasterTasks for execution order
2. Builds Job body from parameters
3. Creates Job via jobqueue API
4. Returns Job ID for tracking

Issue #342 Phase D.1: Migrated logic from jobTaskGeneratorAgents/nodes/job_registration.py
without importing from the old code.

Key design decisions:
- Uses ExecutionContext for API access (dependency injection)
- Does NOT import from langgraph or old jobTaskGeneratorAgents
- All external API calls are abstracted through context.storage
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING, Any

from aiagent.langgraph.jobGeneratorV2.protocols import (
    ErrorType,
    WorkflowError,
)
from aiagent.langgraph.jobGeneratorV2.types_old import (
    Phase,
)

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
    from aiagent.langgraph.jobGeneratorV2.workflows.registration.master_manager import (
        JobMasterInfo,
    )

logger = logging.getLogger(__name__)


@dataclass
class JobBodyParameter:
    """Parameter for Job body.

    Attributes:
        name: Parameter name (snake_case)
        value: Parameter value
        description: Optional description
    """

    name: str
    value: Any
    description: str = ""


@dataclass
class JobRegistrationResult:
    """Result from job registration sub-workflow.

    Attributes:
        job_id: Created Job ID
        job_name: Job name
        status: Registration status
        workflow_task_count: Number of tasks in workflow
        body_parameters: Parameters passed to job body
    """

    job_id: str
    job_name: str
    status: str = "registered"
    workflow_task_count: int = 0
    body_parameters: list[str] = field(default_factory=list)


class JobRegistrarSubWorkflow:
    """Sub-workflow for registering Jobs in jobqueue.

    This sub-workflow handles:
    1. Building Job body from extracted parameters
    2. Creating Job via jobqueue API
    3. Returning Job ID for execution

    Example:
        registrar = JobRegistrarSubWorkflow()
        result = await registrar.register_job(job_master, parameters, context)
    """

    def __init__(self, default_priority: int = 5) -> None:
        """Initialize JobRegistrarSubWorkflow.

        Args:
            default_priority: Default job priority (1-10)
        """
        self._default_priority = default_priority

    async def register_job(
        self,
        job_master: "JobMasterInfo",
        body_parameters: list[JobBodyParameter] | None,
        context: "ExecutionContext",
    ) -> JobRegistrationResult:
        """Register a Job in jobqueue.

        Args:
            job_master: JobMaster information
            body_parameters: Optional parameters for job body
            context: Execution context with API access

        Returns:
            JobRegistrationResult with job ID

        Raises:
            WorkflowError: If job registration fails
        """
        logger.info(
            "Starting job registration for job master %s",
            job_master.id,
        )

        if not job_master.id:
            raise WorkflowError(
                "JobMaster ID is required for job registration",
                ErrorType.VALIDATION,
                Phase.REGISTRATION,
            )

        if not job_master.url:
            raise WorkflowError(
                "JobMaster URL is required for job registration",
                ErrorType.VALIDATION,
                Phase.REGISTRATION,
            )

        # Build job body from parameters
        job_body = self._build_job_body(body_parameters)
        param_names = list(job_body.keys()) if job_body else []

        if job_body:
            logger.info("Job body parameters: %s", param_names)

        # Get workflow tasks (for logging)
        workflow_task_count = await self._get_workflow_task_count(
            job_master.id, context
        )

        # Create job name with timestamp
        job_name = f"{job_master.name} - {datetime.now().isoformat()}"

        # Register job
        job_id = await self._create_job(
            job_master=job_master,
            job_name=job_name,
            job_body=job_body,
            context=context,
        )

        logger.info(
            "Job registered: %s with %d tasks",
            job_id,
            workflow_task_count,
        )

        return JobRegistrationResult(
            job_id=job_id,
            job_name=job_name,
            status="registered",
            workflow_task_count=workflow_task_count,
            body_parameters=param_names,
        )

    def _build_job_body(
        self,
        parameters: list[JobBodyParameter] | None,
    ) -> dict[str, Any] | None:
        """Build Job body from parameters.

        Args:
            parameters: List of job body parameters

        Returns:
            Dict of parameter name to value, or None if no parameters
        """
        if not parameters:
            return None

        body: dict[str, Any] = {}
        for param in parameters:
            if param.name and param.value is not None:
                body[param.name] = param.value

        return body if body else None

    async def _get_workflow_task_count(
        self,
        job_master_id: str,
        context: "ExecutionContext",
    ) -> int:
        """Get count of workflow tasks for a JobMaster.

        Args:
            job_master_id: JobMaster ID
            context: Execution context

        Returns:
            Number of tasks in workflow
        """
        # Placeholder - will be connected to real API in Phase E
        logger.debug("Getting workflow task count for %s", job_master_id)
        return 0

    async def _create_job(
        self,
        job_master: "JobMasterInfo",
        job_name: str,
        job_body: dict[str, Any] | None,
        context: "ExecutionContext",
    ) -> str:
        """Create a Job in jobqueue.

        Args:
            job_master: JobMaster information
            job_name: Job name with timestamp
            job_body: Optional job body parameters
            context: Execution context

        Returns:
            Created Job ID
        """
        placeholder_id = f"job_{context.job_id}"

        logger.debug(
            "Creating Job: %s (master: %s, placeholder: %s)",
            job_name,
            job_master.id,
            placeholder_id,
        )

        # In Phase E, this will call:
        # context.storage.jobqueue_client.create_job(
        #     master_id=job_master.id,
        #     name=job_name,
        #     method=job_master.method,
        #     url=job_master.url,
        #     priority=self._default_priority,
        #     body=job_body,
        #     timeout_sec=job_master.timeout_sec,
        # )

        return placeholder_id


def build_job_body_parameters(
    parameters: list[dict[str, Any]],
) -> list[JobBodyParameter]:
    """Convert raw parameter dicts to JobBodyParameter list.

    Args:
        parameters: List of parameter dicts with name, value, description

    Returns:
        List of JobBodyParameter instances
    """
    result: list[JobBodyParameter] = []
    for param in parameters:
        name = param.get("name")
        value = param.get("value")
        if name:
            result.append(
                JobBodyParameter(
                    name=name,
                    value=value,
                    description=param.get("description", ""),
                )
            )
    return result
