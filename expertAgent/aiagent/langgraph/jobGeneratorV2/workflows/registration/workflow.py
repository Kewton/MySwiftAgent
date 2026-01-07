"""RegistrationWorkflow for Job Generator V2.

This module implements the main RegistrationWorkflow that:
1. Orchestrates sub-workflows (master_manager, job_registrar)
2. Implements WorkflowProtocol for orchestrator integration
3. Returns RegistrationOutput with appropriate PhaseStatus

Issue #342 Phase D.1: Main workflow orchestrating sub-workflows

Key design decisions:
- Implements WorkflowProtocol for use with JobGenerationOrchestrator
- Orchestrates: master_manager -> job_registrar
- Returns NEEDS_RETRY when registration fails transiently
- Returns FAILED when registration fails permanently
- Uses ExecutionContext's phase-specific retry state
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiagent.langgraph.jobGeneratorV2.protocols import (
    ErrorType,
    RetryPolicy,
    WorkflowError,
)
from aiagent.langgraph.jobGeneratorV2.types import (
    Phase,
    PhaseStatus,
    RegistrationInput,
    RegistrationOutput,
)

from .job_registrar import JobBodyParameter, JobRegistrarSubWorkflow
from .master_manager import MasterManagerSubWorkflow

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext

logger = logging.getLogger(__name__)


class RegistrationWorkflow:
    """Main workflow for registration phase.

    This workflow orchestrates the registration process:
    1. Create InterfaceMasters, TaskMasters, and JobMaster
    2. Create JobMasterTask associations
    3. Register Job in jobqueue
    4. Return registration results

    Implements WorkflowProtocol for use with JobGenerationOrchestrator.

    Example:
        workflow = RegistrationWorkflow()
        output = await workflow.execute(input_data, context)
    """

    def __init__(
        self,
        graphai_server_url: str = "http://localhost:8005",
    ) -> None:
        """Initialize RegistrationWorkflow.

        Args:
            graphai_server_url: Base URL for GraphAI server
        """
        self._graphai_server_url = graphai_server_url
        self._retry_policy: RetryPolicy = RetryPolicy(
            max_retries=3,
            backoff_factor=1.5,
            retry_on=[ErrorType.TRANSIENT],
        )

    def get_retry_policy(self) -> RetryPolicy:
        """Get the retry policy for this workflow.

        Returns:
            RetryPolicy instance
        """
        return self._retry_policy

    async def execute(
        self,
        input_data: RegistrationInput,
        context: "ExecutionContext",
    ) -> RegistrationOutput:
        """Execute the registration workflow.

        Args:
            input_data: RegistrationInput with tasks and interfaces
            context: Execution context

        Returns:
            RegistrationOutput with results

        Raises:
            WorkflowError: If a recoverable error occurs
        """
        logger.info(
            "Starting RegistrationWorkflow for job %s",
            context.job_id,
        )

        tasks = input_data.tasks
        interfaces = input_data.interfaces
        project_id = input_data.project_id

        if not tasks:
            logger.warning("No tasks provided for registration")
            return RegistrationOutput(
                status=PhaseStatus.FAILED,
                job_master_id=None,
                task_master_ids=[],
                interface_master_ids=[],
                job_id=None,
            )

        if not interfaces:
            logger.warning("No interfaces provided for registration")
            return RegistrationOutput(
                status=PhaseStatus.FAILED,
                job_master_id=None,
                task_master_ids=[],
                interface_master_ids=[],
                job_id=None,
            )

        # Step 1: Create masters
        master_manager = MasterManagerSubWorkflow(
            graphai_server_url=self._graphai_server_url,
        )

        try:
            master_result = await master_manager.create_masters(
                tasks=tasks,
                interfaces=interfaces,
                project_id=project_id,
                context=context,
            )
        except WorkflowError:
            raise
        except Exception as e:
            logger.error("Unexpected error in master creation: %s", e, exc_info=True)
            raise WorkflowError(
                f"Master creation failed: {e}",
                ErrorType.TRANSIENT,
                Phase.REGISTRATION,
            ) from e

        logger.info(
            "Master creation complete: job_master=%s, task_masters=%d, interface_masters=%d",
            master_result.job_master.id,
            len(master_result.task_masters),
            len(master_result.interface_masters),
        )

        # Step 2: Register job
        job_registrar = JobRegistrarSubWorkflow()

        # Extract body parameters if available (from task breakdown phase)
        body_parameters: list[JobBodyParameter] = []
        # In production, body_parameters would come from the orchestrator
        # passing data from the TaskBreakdown phase

        try:
            job_result = await job_registrar.register_job(
                job_master=master_result.job_master,
                body_parameters=body_parameters if body_parameters else None,
                context=context,
            )
        except WorkflowError:
            raise
        except Exception as e:
            logger.error("Unexpected error in job registration: %s", e, exc_info=True)
            raise WorkflowError(
                f"Job registration failed: {e}",
                ErrorType.TRANSIENT,
                Phase.REGISTRATION,
            ) from e

        logger.info(
            "Job registration complete: job_id=%s",
            job_result.job_id,
        )

        # Build output
        task_master_ids = [tm.id for tm in master_result.task_masters]
        interface_master_ids = [im.id for im in master_result.interface_masters]

        return RegistrationOutput(
            status=PhaseStatus.SUCCESS,
            job_master_id=master_result.job_master.id,
            task_master_ids=task_master_ids,
            interface_master_ids=interface_master_ids,
            job_id=job_result.job_id,
        )
