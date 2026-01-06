"""Orchestrator for Job Generator V2.

This module provides the main orchestrator that coordinates the execution
of all workflow phases with proper error recovery.

Issue #342: The orchestrator uses ErrorRecoveryManager to make intelligent
decisions about retry, rollback, and relaxation, preventing infinite loops.

Key responsibilities:
1. Execute phases in correct order
2. Handle errors with recovery manager
3. Transform outputs between phases
4. Report progress
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
    TaskBreakdownInput,
    TaskBreakdownOutput,
    WorkflowGenInput,
    WorkflowGenOutput,
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
    ) -> JobGenerationResult:
        """Run the complete job generation workflow.

        Args:
            request: The job generation request

        Returns:
            JobGenerationResult with the outcome
        """
        job_id = str(uuid.uuid4())
        logger.info("Starting job generation workflow: %s", job_id)

        # Create execution context
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
                            "aiagent.langgraph.jobGeneratorV2.protocols", fromlist=["ErrorType"]
                        ).ErrorType.FATAL,
                        phase=phase,
                    )

                # Transform input from previous phase
                phase_input = self._create_phase_input(
                    phase, request, phase_outputs
                )

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

    def _create_result(
        self,
        phase_outputs: dict[Phase, Any],
    ) -> JobGenerationResult:
        """Create final result from all phase outputs.

        Args:
            phase_outputs: Outputs from all phases

        Returns:
            JobGenerationResult
        """
        registration_output: RegistrationOutput = phase_outputs[Phase.REGISTRATION]
        workflow_output: WorkflowGenOutput = phase_outputs[Phase.WORKFLOW_GEN]

        return JobGenerationResult(
            success=True,
            job_id=registration_output.job_id,
            job_master_id=registration_output.job_master_id,
            task_master_ids=registration_output.task_master_ids,
            workflow_yaml=workflow_output.workflow_yaml,
        )
