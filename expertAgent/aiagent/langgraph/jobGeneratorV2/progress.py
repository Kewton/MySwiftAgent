"""Progress reporter implementation for Job Generator V2.

This module provides a ProgressReporter implementation that integrates
with job_state_manager for real-time progress tracking during polling.

Issue #342-V2-UX: Ensure V2 provides the same UX as V1 for progress tracking.

Key features:
1. Reports phase transitions to job_state_manager
2. Sets task_breakdown when TASK_BREAKDOWN phase completes
3. Initializes and updates workflow_statuses for WORKFLOW_GEN phase
"""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .protocols import ProgressReporter
from .types import Phase, TaskDefinition

if TYPE_CHECKING:
    from app.services.job_creation_state import (
        JobCreationStateManager,
        WorkflowGenerationSummary,
    )

logger = logging.getLogger(__name__)


# Phase to progress percentage mapping
PHASE_PROGRESS_MAP: dict[Phase, int] = {
    Phase.TASK_BREAKDOWN: 30,
    Phase.INTERFACE_DESIGN: 50,
    Phase.REGISTRATION: 70,
    Phase.WORKFLOW_GEN: 90,
}

# Phase to job_state_manager phase name mapping
PHASE_NAME_MAP: dict[Phase, str] = {
    Phase.TASK_BREAKDOWN: "task_analysis",
    Phase.INTERFACE_DESIGN: "task_analysis",  # Still in analysis phase
    Phase.REGISTRATION: "workflow_generation",
    Phase.WORKFLOW_GEN: "workflow_generation",
}


@dataclass
class PhaseResult:
    """Result data from a completed phase.

    Used to pass task breakdown and other data to the progress reporter.
    """

    tasks: list[TaskDefinition] | None = None
    workflow_statuses: list[dict[str, Any]] | None = None


class JobStateProgressReporter(ProgressReporter):
    """Progress reporter that updates job_state_manager.

    This implementation reports V2 workflow progress to job_state_manager
    for real-time polling updates, providing the same UX as V1.

    Example:
        reporter = JobStateProgressReporter(
            job_id="job-123",
            job_state_manager=job_state_manager,
        )
        orchestrator = JobGenerationOrchestrator(
            recovery_manager=recovery_manager,
            progress_reporter=reporter,
        )
    """

    def __init__(
        self,
        job_id: str,
        job_state_manager: "JobCreationStateManager",
    ) -> None:
        """Initialize the progress reporter.

        Args:
            job_id: The job ID for tracking
            job_state_manager: The job state manager instance
        """
        self._job_id = job_id
        self._job_state_manager = job_state_manager
        self._task_breakdown_set = False
        self._workflow_statuses_initialized = False

    @property
    def job_id(self) -> str:
        """Get the job ID."""
        return self._job_id

    def report(
        self,
        phase: Phase,
        context: Any,
    ) -> None:
        """Report progress on a phase completion.

        This is called synchronously by the orchestrator but we need to
        make async calls. We'll use run_coroutine_threadsafe for this.

        Args:
            phase: The phase that completed
            context: Current execution context
        """
        import asyncio

        # Get or create event loop
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._report_async(phase, context))
            return

        # Schedule the coroutine
        asyncio.create_task(self._report_async(phase, context))

    async def _report_async(
        self,
        phase: Phase,
        context: Any,
    ) -> None:
        """Async implementation of progress reporting.

        Args:
            phase: The phase that completed
            context: Current execution context
        """
        # Update progress percentage
        progress = PHASE_PROGRESS_MAP.get(phase, 50)
        await self._job_state_manager.update_progress_async(self._job_id, progress)

        # Update phase name
        phase_name = PHASE_NAME_MAP.get(phase, "task_analysis")
        await self._job_state_manager.update_phase_async(self._job_id, phase_name)

        logger.info(
            "Progress reported for job %s: phase=%s, progress=%d%%",
            self._job_id,
            phase.value,
            progress,
        )

    def report_recovery(
        self,
        phase: Phase,
        decision: Any,
        context: Any,
    ) -> None:
        """Report an error recovery decision.

        Args:
            phase: The phase where recovery is happening
            decision: The recovery decision made
            context: Current execution context
        """
        logger.info(
            "Recovery reported for job %s: phase=%s, strategy=%s",
            self._job_id,
            phase.value,
            getattr(decision, "strategy", "unknown"),
        )

    async def set_task_breakdown(
        self,
        tasks: list[TaskDefinition],
    ) -> None:
        """Set task breakdown in job_state_manager.

        This should be called after TASK_BREAKDOWN phase completes.

        Args:
            tasks: List of TaskDefinition from the breakdown phase
        """
        from app.services.job_creation_state import TaskBreakdownItem

        if self._task_breakdown_set:
            logger.debug("Task breakdown already set for job %s", self._job_id)
            return

        # Convert V2 TaskDefinition to job_state_manager's TaskBreakdownItem
        breakdown_items = [
            TaskBreakdownItem(
                task_id=task.id,
                name=task.name,
                description=task.description,
                recommended_apis=[task.recommended_api] if task.recommended_api else [],
            )
            for task in tasks
        ]

        await self._job_state_manager.set_task_breakdown_async(
            self._job_id,
            breakdown_items,
        )

        self._task_breakdown_set = True
        logger.info(
            "Task breakdown set for job %s: %d tasks",
            self._job_id,
            len(tasks),
        )

    async def init_workflow_statuses(
        self,
        tasks: list[TaskDefinition],
    ) -> None:
        """Initialize workflow statuses for all tasks.

        This should be called before WORKFLOW_GEN phase starts.

        Args:
            tasks: List of TaskDefinition to initialize statuses for
        """
        if self._workflow_statuses_initialized:
            logger.debug(
                "Workflow statuses already initialized for job %s", self._job_id
            )
            return

        task_ids = [task.id for task in tasks]
        task_names = [task.name for task in tasks]

        await self._job_state_manager.init_workflow_statuses_async(
            self._job_id,
            task_ids,
            task_names,
        )

        self._workflow_statuses_initialized = True
        logger.info(
            "Workflow statuses initialized for job %s: %d tasks",
            self._job_id,
            len(tasks),
        )

    async def update_workflow_status(
        self,
        task_id: str,
        status: str,
        workflow_name: str | None = None,
        generation_time_ms: int | None = None,
        error_message: str | None = None,
        langfuse_trace_id: str | None = None,
        summary: "WorkflowGenerationSummary | None" = None,
    ) -> None:
        """Update status for a single workflow.

        Args:
            task_id: The task ID
            status: Status ('pending' | 'generating' | 'success' | 'failed')
            workflow_name: Workflow name if success
            generation_time_ms: Generation time in ms
            error_message: Error message if failed
            langfuse_trace_id: Langfuse trace ID for this task
            summary: Workflow generation summary for UI display
        """
        await self._job_state_manager.update_workflow_status_async(
            self._job_id,
            task_id,
            status,
            workflow_name=workflow_name,
            generation_time_ms=generation_time_ms,
            error_message=error_message,
            langfuse_trace_id=langfuse_trace_id,
            summary=summary,
        )

        logger.debug(
            "Workflow status updated for job %s, task %s: %s",
            self._job_id,
            task_id,
            status,
        )

    async def mark_complete(self) -> None:
        """Mark the job as complete.

        This should be called after all phases complete successfully.
        """
        await self._job_state_manager.update_phase_async(self._job_id, "complete")
        await self._job_state_manager.update_progress_async(self._job_id, 100)
        logger.info("Job %s marked as complete", self._job_id)
