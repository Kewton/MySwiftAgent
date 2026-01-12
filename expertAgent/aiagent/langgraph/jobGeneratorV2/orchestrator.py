"""Orchestrator for Job Generator V2.

This module provides the main orchestrator that coordinates the execution
of all workflow phases with proper error recovery.

Issue #342: The orchestrator uses ErrorRecoveryManager to make intelligent
decisions about retry, rollback, and relaxation, preventing infinite loops.

Issue #342-V2-UX: Added integration with JobStateProgressReporter for
real-time progress tracking during polling (same UX as V1).

Key responsibilities:
1. Execute phases in correct order
2. Handle errors with recovery manager
3. Transform outputs between phases
4. Report progress to job_state_manager via progress reporter
"""

import logging
import uuid
from typing import Any

from .context import ContextBuilder, ExecutionContext
from .protocols import ProgressReporter, WorkflowError, WorkflowProtocol
from .recovery import ErrorRecoveryManager, ErrorRecoveryStrategy
from .types import (
    InterfaceDesignInput,
    InterfaceDesignOutput,
    JobGenerationRequest,
    JobGenerationResult,
    Phase,
    PhaseStatus,
    RegistrationInput,
    RegistrationOutput,
    SkipAggregator,
    SkipInfo,
    TaskBreakdownInput,
    TaskBreakdownOutput,
    TaskIdMapping,
    WorkflowGenInput,
    WorkflowGenOutput,
    WorkflowGenPhaseOutput,
)

logger = logging.getLogger(__name__)


class JobGenerationOrchestrator:
    """Orchestrates the job generation workflow.

    This class coordinates the execution of all workflow phases:
    1. TaskBreakdownWorkflow
    2. InterfaceDesignWorkflow
    3. RegistrationWorkflow
    4. WorkflowGenWorkflow

    It handles:
    - Phase ordering and execution
    - Error recovery decisions
    - Output transformation between phases
    - Progress reporting

    Example:
        orchestrator = JobGenerationOrchestrator(
            recovery_manager=ErrorRecoveryManager()
        )
        orchestrator.register_workflow(Phase.TASK_BREAKDOWN, breakdown_workflow)
        orchestrator.register_workflow(Phase.INTERFACE_DESIGN, interface_workflow)
        ...
        result = await orchestrator.run_workflow(request)
    """

    # Phase execution order
    PHASE_ORDER = [
        Phase.TASK_BREAKDOWN,
        Phase.INTERFACE_DESIGN,
        Phase.REGISTRATION,
        Phase.WORKFLOW_GEN,
    ]

    def __init__(
        self,
        recovery_manager: ErrorRecoveryManager,
        progress_reporter: ProgressReporter | None = None,
    ):
        """Initialize the orchestrator.

        Args:
            recovery_manager: Manager for error recovery decisions
            progress_reporter: Optional reporter for progress updates
        """
        self.recovery_manager = recovery_manager
        self.progress_reporter = progress_reporter
        self._workflows: dict[Phase, WorkflowProtocol] = {}

    def register_workflow(self, phase: Phase, workflow: WorkflowProtocol) -> None:
        """Register a workflow for a phase.

        Args:
            phase: The phase this workflow handles
            workflow: The workflow implementation
        """
        logger.info("Registering workflow for phase %s", phase.value)
        self._workflows[phase] = workflow

    def get_workflow(self, phase: Phase) -> WorkflowProtocol | None:
        """Get the workflow for a phase.

        Args:
            phase: The phase to get workflow for

        Returns:
            The workflow or None if not registered
        """
        return self._workflows.get(phase)

    def get_phase_order(self) -> list[Phase]:
        """Get the phase execution order.

        Returns:
            List of phases in execution order
        """
        return list(self.PHASE_ORDER)

    def get_next_phase(self, current: Phase) -> Phase | None:
        """Get the next phase after the current one.

        Args:
            current: The current phase

        Returns:
            Next phase or None if at the end
        """
        try:
            idx = self.PHASE_ORDER.index(current)
            if idx < len(self.PHASE_ORDER) - 1:
                return self.PHASE_ORDER[idx + 1]
            return None
        except ValueError:
            return None

    async def run_workflow(
        self,
        request: JobGenerationRequest,
        context: ExecutionContext | None = None,
    ) -> JobGenerationResult:
        """Run the complete job generation workflow.

        Args:
            request: The job generation request
            context: Optional ExecutionContext (created if not provided).
                     Issue #342 V2: When provided, enables Langfuse tracing
                     through the observability.tracer field.

        Returns:
            JobGenerationResult with the outcome
        """
        # Issue #342 V2: Use provided context or create default
        if context is not None:
            job_id = context.job_id
            logger.info("Using provided context for job: %s", job_id)
        else:
            job_id = str(uuid.uuid4())
            logger.info("Creating default context for job: %s", job_id)
            context = (
                ContextBuilder()
                .with_job_id(job_id)
                .with_user_requirement(request.user_requirement)
                .build()
            )

        try:
            # Execute phases in order
            phase_outputs: dict[Phase, Any] = {}

            for phase in self.PHASE_ORDER:
                workflow = self.get_workflow(phase)
                if workflow is None:
                    raise WorkflowError(
                        f"No workflow registered for phase {phase.value}",
                        error_type=__import__(
                            "aiagent.langgraph.jobGeneratorV2.protocols",
                            fromlist=["ErrorType"],
                        ).ErrorType.FATAL,
                        phase=phase,
                    )

                # Issue #342 V2 Fix: Handle WORKFLOW_GEN specially - per-task generation
                if phase == Phase.WORKFLOW_GEN:
                    await self._init_workflow_statuses(phase_outputs)
                    output = await self._execute_workflow_gen_per_task(
                        phase_outputs=phase_outputs,
                        context=context,
                    )
                else:
                    # Transform input from previous phase
                    phase_input = self._create_phase_input(phase, request, phase_outputs)

                    # Execute phase
                    output = await self.execute_phase(
                        phase=phase,
                        input=phase_input,
                        context=context,
                    )

                # Check output status
                if output.status == PhaseStatus.NEEDS_RELAXATION:
                    return JobGenerationResult(
                        success=False,
                        relaxation_suggestions=getattr(
                            output, "relaxation_suggestions", []
                        ),
                        error="Requirements need relaxation",
                    )

                if output.status == PhaseStatus.FAILED:
                    return JobGenerationResult(
                        success=False,
                        error=f"Phase {phase.value} failed",
                    )

                phase_outputs[phase] = output

                # Issue #342-V2-UX: Update task breakdown after TASK_BREAKDOWN phase
                if phase == Phase.TASK_BREAKDOWN:
                    await self._set_task_breakdown(output)

            # Issue #342 V2 Fix: Mark workflow statuses with individual YAMLs
            await self._mark_workflow_statuses_complete(phase_outputs, context)

            # Issue #342-V2-UX: Mark complete
            await self._mark_complete()

            # Extract final result
            return self._create_result(phase_outputs)

        except WorkflowError as e:
            logger.error("Workflow failed: %s", e)
            return JobGenerationResult(
                success=False,
                error=str(e),
            )
        except Exception as e:
            logger.exception("Unexpected error in workflow: %s", e)
            return JobGenerationResult(
                success=False,
                error=f"Unexpected error: {e}",
            )

    async def execute_phase(
        self,
        phase: Phase,
        input: Any,
        context: ExecutionContext,
    ) -> Any:
        """Execute a single phase with error recovery.

        Args:
            phase: The phase to execute
            input: Input for the phase
            context: Execution context

        Returns:
            Phase output

        Raises:
            WorkflowError: If phase fails after all recovery attempts
        """
        from .protocols import ErrorType

        workflow = self.get_workflow(phase)
        if workflow is None:
            raise WorkflowError(
                f"No workflow registered for phase {phase.value}",
                ErrorType.FATAL,
                phase=phase,
            )

        logger.info("Executing phase: %s", phase.value)

        while True:
            try:
                output = await workflow.execute(input, context)

                # Report progress
                if self.progress_reporter:
                    self.progress_reporter.report(phase, context)

                return output

            except WorkflowError as e:
                logger.warning(
                    "Phase %s failed: %s (type=%s)",
                    phase.value,
                    e,
                    e.error_type.value,
                )

                # Get recovery decision
                decision = self.recovery_manager.decide_recovery(
                    phase=phase,
                    error=e,
                    context=context,
                )

                logger.info(
                    "Recovery decision: %s",
                    decision.strategy.value,
                )

                if self.progress_reporter:
                    self.progress_reporter.report_recovery(phase, decision, context)

                # Handle based on strategy
                if decision.strategy == ErrorRecoveryStrategy.FAIL_FAST:
                    raise

                if decision.strategy == ErrorRecoveryStrategy.RETRY_CURRENT:
                    if not context.can_retry(phase):
                        raise
                    context.record_retry(phase, str(e), e)
                    # Continue loop to retry
                    continue

                if decision.strategy in (
                    ErrorRecoveryStrategy.ROLLBACK_ONE,
                    ErrorRecoveryStrategy.ROLLBACK_TO_BREAKDOWN,
                ):
                    # Rollback requires re-executing from earlier phase
                    # This is handled by the run_workflow method
                    raise

                if decision.strategy == ErrorRecoveryStrategy.RELAXATION:
                    # Relaxation requires user intervention
                    raise

                # Unknown strategy - fail
                raise

    def _create_phase_input(
        self,
        phase: Phase,
        request: JobGenerationRequest,
        phase_outputs: dict[Phase, Any],
    ) -> Any:
        """Create input for a phase from request and previous outputs.

        Args:
            phase: The phase to create input for
            request: Original request
            phase_outputs: Outputs from previous phases

        Returns:
            Appropriate input type for the phase
        """
        if phase == Phase.TASK_BREAKDOWN:
            return TaskBreakdownInput(
                user_requirement=request.user_requirement,
                max_tasks=request.max_tasks,
            )

        if phase == Phase.INTERFACE_DESIGN:
            breakdown_out: TaskBreakdownOutput = phase_outputs[Phase.TASK_BREAKDOWN]
            return InterfaceDesignInput(
                tasks=breakdown_out.tasks,
            )

        if phase == Phase.REGISTRATION:
            reg_breakdown_out: TaskBreakdownOutput = phase_outputs[Phase.TASK_BREAKDOWN]
            reg_interface_out: InterfaceDesignOutput = phase_outputs[
                Phase.INTERFACE_DESIGN
            ]
            return RegistrationInput(
                tasks=reg_breakdown_out.tasks,
                interfaces=reg_interface_out.interfaces,
                project_id=request.project_id,
            )

        if phase == Phase.WORKFLOW_GEN:
            wf_interface_out: InterfaceDesignOutput = phase_outputs[
                Phase.INTERFACE_DESIGN
            ]
            registration_output: RegistrationOutput = phase_outputs[Phase.REGISTRATION]
            return WorkflowGenInput(
                task_master_ids=registration_output.task_master_ids,
                job_master_id=registration_output.job_master_id or "",
                interfaces=wf_interface_out.interfaces,
            )

        raise ValueError(f"Unknown phase: {phase}")

    async def _execute_workflow_gen_per_task(
        self,
        phase_outputs: dict[Phase, Any],
        context: "ExecutionContext",
    ) -> WorkflowGenPhaseOutput:
        """Execute WorkflowGenWorkflow for each task individually.

        Issue #342 V2 Fix: Generate separate workflows for each task instead of
        one integrated workflow for all tasks.

        Issue #342 Bug #1: Now creates TaskIdMapping for correct interface lookup.
        Issue #342 Bug #3: Now uses SkipAggregator to track skipped tasks.

        Args:
            phase_outputs: Outputs from previous phases
            context: Execution context

        Returns:
            WorkflowGenPhaseOutput with workflow for each task

        Raises:
            WorkflowError: If all tasks are skipped (Bug #3 fix)
        """
        from .protocols import ErrorType

        breakdown_output: TaskBreakdownOutput = phase_outputs[Phase.TASK_BREAKDOWN]
        interface_output: InterfaceDesignOutput = phase_outputs[Phase.INTERFACE_DESIGN]
        registration_output: RegistrationOutput = phase_outputs[Phase.REGISTRATION]

        workflow = self.get_workflow(Phase.WORKFLOW_GEN)
        if workflow is None:
            raise WorkflowError(
                "No workflow registered for WORKFLOW_GEN phase",
                ErrorType.FATAL,
                phase=Phase.WORKFLOW_GEN,
            )

        # Issue #342 Bug #1: Create TaskIdMapping for correct interface lookup
        task_id_mapping = TaskIdMapping.from_registration(registration_output)
        logger.info(
            "Created TaskIdMapping with %d entries for interface lookup",
            len(task_id_mapping.logical_to_master),
        )

        # Store TaskIdMapping in context for downstream use
        context.storage.task_id_mapping = task_id_mapping

        task_workflows: dict[str, WorkflowGenOutput] = {}
        overall_status = PhaseStatus.SUCCESS

        # Issue #342 Bug #3: Use SkipAggregator to track skipped tasks
        skip_aggregator = SkipAggregator()
        total_tasks = len(breakdown_output.tasks)

        # Execute workflow generation for each task
        for idx, task in enumerate(breakdown_output.tasks):
            task_id = task.id
            logger.info(
                "Generating workflow for task %d/%d: %s",
                idx + 1,
                total_tasks,
                task_id,
            )

            # Get the task_master_id for this task (same order as tasks list)
            if idx >= len(registration_output.task_master_ids):
                # Issue #342 Bug #3: Track skip instead of silent continue
                skip_aggregator.add_skip(
                    SkipInfo(
                        task_id=task_id,
                        reason=f"No task_master_id found for task index {idx}",
                        phase=Phase.WORKFLOW_GEN.value,
                    )
                )
                continue

            task_master_id = registration_output.task_master_ids[idx]

            # Get interface for this task
            interface = interface_output.interfaces.get(task_id)
            if interface is None:
                logger.warning(
                    "No interface found for task %s, using empty interface",
                    task_id,
                )
                interface_for_task = {}
            else:
                interface_for_task = {task_id: interface}

            # Create single-task input with TaskIdMapping
            single_task_input = WorkflowGenInput(
                task_master_ids=[task_master_id],
                job_master_id=registration_output.job_master_id or "",
                interfaces=interface_for_task,
                task_id_mapping=task_id_mapping,  # Bug #1 fix: Pass mapping
            )

            try:
                # Execute workflow generation for this task
                output = await self.execute_phase(
                    phase=Phase.WORKFLOW_GEN,
                    input=single_task_input,
                    context=context,
                )

                # Store result with task_id
                output.task_id = task_id
                task_workflows[task_id] = output

                # Track overall status
                if output.status == PhaseStatus.FAILED:
                    overall_status = PhaseStatus.FAILED
                elif output.status == PhaseStatus.NEEDS_RELAXATION:
                    overall_status = PhaseStatus.NEEDS_RELAXATION

                logger.info(
                    "Workflow generated for task %s: status=%s",
                    task_id,
                    output.status.value,
                )

            except WorkflowError as e:
                logger.error(
                    "Workflow generation failed for task %s: %s",
                    task_id,
                    e,
                )
                # Store failed result
                task_workflows[task_id] = WorkflowGenOutput(
                    status=PhaseStatus.FAILED,
                    task_id=task_id,
                    workflow_yaml=None,
                    test_result={"error": str(e)},
                )
                overall_status = PhaseStatus.FAILED

        # Issue #342 Bug #3: Check if all tasks were skipped
        # Only check if there were tasks to process (avoid false positive)
        if total_tasks > 0 and skip_aggregator.all_skipped(total_tasks):
            error_msg = (
                f"All {total_tasks} tasks were skipped during workflow generation.\n"
                f"{skip_aggregator.get_summary()}"
            )
            logger.error(error_msg)
            raise WorkflowError(
                error_msg,
                ErrorType.FATAL,
                phase=Phase.WORKFLOW_GEN,
            )

        # Log skip summary if any tasks were skipped
        if skip_aggregator.skip_count > 0:
            logger.warning(
                "Workflow generation completed with %d/%d tasks skipped:\n%s",
                skip_aggregator.skip_count,
                total_tasks,
                skip_aggregator.get_summary(),
            )

        return WorkflowGenPhaseOutput(
            status=overall_status,
            task_workflows=task_workflows,
        )

    def _create_result(
        self,
        phase_outputs: dict[Phase, Any],
    ) -> JobGenerationResult:
        """Create final result from all phase outputs.

        Args:
            phase_outputs: Outputs from all phases

        Returns:
            JobGenerationResult

        Issue #342: Extended to include tasks and interfaces for adapter conversion.
        Issue #342 V2 Fix: Handle WorkflowGenPhaseOutput with per-task workflows.
        """
        # Extract outputs from all phases
        breakdown_output: TaskBreakdownOutput = phase_outputs[Phase.TASK_BREAKDOWN]
        interface_output: InterfaceDesignOutput = phase_outputs[Phase.INTERFACE_DESIGN]
        registration_output: RegistrationOutput = phase_outputs[Phase.REGISTRATION]
        workflow_phase_output: WorkflowGenPhaseOutput = phase_outputs[Phase.WORKFLOW_GEN]

        # Issue #342 V2 Fix: Combine all task workflows into one summary YAML
        # Individual task YAMLs are stored separately in job_state_manager
        combined_yaml = None
        task_yamls = []
        for task in breakdown_output.tasks:
            task_workflow = workflow_phase_output.task_workflows.get(task.id)
            if task_workflow and task_workflow.workflow_yaml:
                task_yamls.append(f"# --- Task: {task.id} ({task.name}) ---\n{task_workflow.workflow_yaml}")

        if task_yamls:
            combined_yaml = "\n\n".join(task_yamls)

        return JobGenerationResult(
            success=True,
            job_id=registration_output.job_id,
            job_master_id=registration_output.job_master_id,
            task_master_ids=registration_output.task_master_ids,
            workflow_yaml=combined_yaml,
            # Issue #342: Include task/interface info for adapter conversion
            tasks=breakdown_output.tasks,
            interfaces=interface_output.interfaces,
        )

    # Issue #342-V2-UX: Helper methods for progress reporting

    async def _set_task_breakdown(
        self,
        breakdown_output: TaskBreakdownOutput,
    ) -> None:
        """Set task breakdown in progress reporter.

        Args:
            breakdown_output: Output from TASK_BREAKDOWN phase
        """
        if self.progress_reporter is None:
            return

        # Check if reporter is JobStateProgressReporter
        from .progress import JobStateProgressReporter

        if isinstance(self.progress_reporter, JobStateProgressReporter):
            await self.progress_reporter.set_task_breakdown(breakdown_output.tasks)
            logger.info(
                "Task breakdown set via progress reporter: %d tasks",
                len(breakdown_output.tasks),
            )

    async def _init_workflow_statuses(
        self,
        phase_outputs: dict[Phase, Any],
    ) -> None:
        """Initialize workflow statuses before WORKFLOW_GEN phase.

        Args:
            phase_outputs: Outputs from previous phases
        """
        if self.progress_reporter is None:
            return

        # Check if reporter is JobStateProgressReporter
        from .progress import JobStateProgressReporter

        if isinstance(self.progress_reporter, JobStateProgressReporter):
            breakdown_output: TaskBreakdownOutput = phase_outputs[Phase.TASK_BREAKDOWN]
            await self.progress_reporter.init_workflow_statuses(breakdown_output.tasks)
            logger.info(
                "Workflow statuses initialized via progress reporter: %d tasks",
                len(breakdown_output.tasks),
            )

    async def _mark_workflow_statuses_complete(
        self,
        phase_outputs: dict[Phase, Any],
        context: "ExecutionContext",
    ) -> None:
        """Mark all workflow statuses as success after WORKFLOW_GEN phase.

        Issue #342: Extended to include langfuse_trace_id and summary (YAML)
        for each task's workflow status.

        Issue #342 V2 Fix: Use individual task YAML instead of copying same YAML.

        Args:
            phase_outputs: Outputs from all phases
            context: Execution context with observability info
        """
        if self.progress_reporter is None:
            return

        # Check if reporter is JobStateProgressReporter
        from .progress import JobStateProgressReporter

        if isinstance(self.progress_reporter, JobStateProgressReporter):
            from app.services.job_creation_state import WorkflowGenerationSummary
            from app.services.langfuse_service import LangfuseService

            breakdown_output: TaskBreakdownOutput = phase_outputs[Phase.TASK_BREAKDOWN]

            # Issue #342 V2 Fix: Get WorkflowGenPhaseOutput with per-task workflows
            workflow_phase_output: WorkflowGenPhaseOutput | None = phase_outputs.get(
                Phase.WORKFLOW_GEN
            )

            # Issue #342: Extract langfuse_trace_id from context
            langfuse_trace_id = None
            if context.observability and context.observability.tracer:
                langfuse_trace_id = LangfuseService.extract_trace_id(
                    context.observability.tracer
                )

            # Mark each task's workflow status with its individual YAML
            for task in breakdown_output.tasks:
                # Issue #342 V2 Fix: Get individual workflow for this task
                task_workflow = None
                task_yaml = None
                task_status = "success"

                if workflow_phase_output:
                    task_workflow = workflow_phase_output.task_workflows.get(task.id)
                    if task_workflow:
                        task_yaml = task_workflow.workflow_yaml
                        if task_workflow.status == PhaseStatus.FAILED:
                            task_status = "failed"
                        elif task_workflow.status == PhaseStatus.NEEDS_RETRY:
                            task_status = "pending"

                # Create summary with YAML content for UI display
                summary = None
                if task_yaml:
                    yaml_preview = (
                        task_yaml[:500] if len(task_yaml) > 500 else task_yaml
                    )
                    summary = WorkflowGenerationSummary(
                        yaml_preview=yaml_preview,
                        yaml_content=task_yaml,
                    )

                await self.progress_reporter.update_workflow_status(
                    task_id=task.id,
                    status=task_status,
                    workflow_name=f"workflow_{task.id}",
                    langfuse_trace_id=langfuse_trace_id,
                    summary=summary,
                )

                logger.debug(
                    "Task %s workflow status updated: status=%s, has_yaml=%s",
                    task.id,
                    task_status,
                    task_yaml is not None,
                )

            logger.info(
                "Workflow statuses marked: %d tasks (trace_id: %s)",
                len(breakdown_output.tasks),
                langfuse_trace_id,
            )

    async def _mark_complete(self) -> None:
        """Mark job as complete via progress reporter."""
        if self.progress_reporter is None:
            return

        # Check if reporter is JobStateProgressReporter
        from .progress import JobStateProgressReporter

        if isinstance(self.progress_reporter, JobStateProgressReporter):
            await self.progress_reporter.mark_complete()
            logger.info("Job marked as complete via progress reporter")

    async def _can_proceed_to_finalization(
        self,
        phase_outputs: dict[Phase, Any],
        context: "ExecutionContext",
    ) -> tuple[bool, str | None]:
        """Check if workflow can proceed to finalization.

        Issue #353: Validates that WORKFLOW_GEN phase completed successfully
        before allowing transition to finalization. This prevents jobs with
        __PENDING__ workflow_names from being marked as complete.

        Args:
            phase_outputs: Outputs from all executed phases
            context: Execution context

        Returns:
            Tuple of (can_proceed, error_message)
            - can_proceed: True if finalization can proceed
            - error_message: Error message if cannot proceed, None otherwise
        """
        # Check if WORKFLOW_GEN output exists
        workflow_gen_output = phase_outputs.get(Phase.WORKFLOW_GEN)
        if workflow_gen_output is None:
            return False, "WORKFLOW_GEN phase output not found"

        # Check for incomplete workflows (tasks without workflow_yaml)
        # Do this before checking overall status to get more specific error messages
        incomplete_tasks: list[str] = []

        task_workflows = getattr(workflow_gen_output, "task_workflows", {})
        for task_id, task_output in task_workflows.items():
            if task_output.workflow_yaml is None:
                incomplete_tasks.append(task_id)
            elif task_output.status == PhaseStatus.FAILED:
                incomplete_tasks.append(task_id)

        if incomplete_tasks:
            error_msg = (
                f"WORKFLOW_GEN phase incomplete: {len(incomplete_tasks)} task(s) "
                f"have missing or failed workflows. Task IDs: {', '.join(incomplete_tasks[:5])}"
            )
            if len(incomplete_tasks) > 5:
                error_msg += f" (and {len(incomplete_tasks) - 5} more)"
            logger.error(error_msg)
            return False, error_msg

        # Check overall status after checking individual tasks
        if workflow_gen_output.status == PhaseStatus.FAILED:
            return False, "WORKFLOW_GEN phase failed"

        logger.info("WORKFLOW_GEN phase complete, can proceed to finalization")
        return True, None
