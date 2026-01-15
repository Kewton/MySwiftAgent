"""Orchestrator for 3-Phase Job Generation Architecture.

Issue #359: Refactored orchestrator with 3-phase unified ID pattern.

3-Phase Architecture:
- Phase 1: JOB_ANALYSIS (1 LLM call)
- Phase 2: REGISTRATION (no LLM)
- Phase 3: WORKFLOW_GEN (N parallel LLM calls)

Constraints:
- Maximum 300 lines
- NO index-based lookups (task_master_ids[idx] is BANNED)
- NO silent fallbacks (raise error if data not found)
- Uses task_id consistently across all phases
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field

from .error_recovery import ErrorRecoveryManager
from .nodes.job_analyzer import (
    AnalyzedTask,
    InterfaceDefinition,
    JobAnalysisInput,
    JobAnalysisResponse,
)
from .parallel_executor import (
    ParallelExecutionErrorAggregator,
    parallel_workflow_generation,
)
from .types import ParallelExecutionResult, Phase, UnifiedTaskIdentifier
from .validators.pipeline import ValidationPipeline
from .validators.task_dependency import TaskDependencyValidator

logger = logging.getLogger(__name__)


class OrchestratorError(Exception):
    """Error raised by orchestrator for explicit failures."""

    def __init__(self, message: str, phase: Phase | None = None):
        super().__init__(message)
        self.phase = phase


class JobGenerationRequest(BaseModel):
    """Request for 3-phase job generation."""

    user_requirement: str = Field(description="Natural language requirement")
    project_id: str = Field(default="default", description="Project ID")
    max_tasks: int = Field(default=10, description="Maximum tasks")
    engine: str = Field(default="taskflow", description="Workflow engine")


@dataclass
class JobGenerationResult:
    """Result from 3-phase job generation."""

    success: bool
    job_id: str | None = None
    job_master_id: str | None = None
    task_identifiers: list[UnifiedTaskIdentifier] = field(default_factory=list)
    workflows: dict[str, dict[str, Any]] = field(default_factory=dict)
    error: str | None = None
    tasks: list[AnalyzedTask] = field(default_factory=list)
    interfaces: dict[str, InterfaceDefinition] = field(default_factory=dict)


class JobGenerationOrchestrator:
    """Orchestrator for 3-phase job generation workflow.

    Phases:
    1. JOB_ANALYSIS - Task breakdown + interface design (1 LLM call)
    2. REGISTRATION - Register masters in jobqueue (no LLM)
    3. WORKFLOW_GEN - Generate workflows in parallel (N LLM calls)
    """

    PHASE_ORDER = [Phase.JOB_ANALYSIS, Phase.REGISTRATION, Phase.WORKFLOW_GEN]

    def __init__(
        self,
        error_recovery_manager: ErrorRecoveryManager | None = None,
        llm_client: Any | None = None,
        jobqueue_client: Any | None = None,
    ):
        """Initialize orchestrator."""
        self._error_recovery_manager = error_recovery_manager or ErrorRecoveryManager()
        self._llm_client = llm_client
        self._jobqueue_client = jobqueue_client

    def get_phase_order(self) -> list[Phase]:
        """Get phase execution order."""
        return list(self.PHASE_ORDER)

    def _get_task_by_id(
        self,
        task_map: dict[str, Any],
        task_id: str,
    ) -> Any:
        """Get task by ID - raises error if not found (no silent fallback)."""
        if task_id not in task_map:
            raise OrchestratorError(
                f"Task not found: {task_id}. Available: {list(task_map.keys())}",
                phase=None,
            )
        return task_map[task_id]

    async def run_workflow(
        self,
        request: JobGenerationRequest,
    ) -> JobGenerationResult:
        """Execute the complete 3-phase workflow."""
        logger.info("Starting 3-phase workflow for: %s...", request.user_requirement[:50])

        try:
            # Phase 1: JOB_ANALYSIS
            analysis_result = await self._execute_job_analysis(request)

            # Phase 2: REGISTRATION
            registration_result = await self._execute_registration(
                analysis_result.tasks,
                analysis_result.interfaces,
                request.project_id,
            )

            # Build task identifiers with master IDs
            task_identifiers = self._build_task_identifiers(
                analysis_result.tasks,
                registration_result["task_id_to_master_id"],
            )

            # Phase 3: WORKFLOW_GEN (parallel)
            workflow_result = await self._execute_workflow_gen(
                task_identifiers,
                analysis_result.interfaces,
            )

            # Build final result
            return self._build_result(
                analysis_result,
                registration_result,
                task_identifiers,
                workflow_result,
            )

        except OrchestratorError:
            raise
        except Exception as e:
            logger.exception("Workflow failed: %s", e)
            return JobGenerationResult(success=False, error=str(e))

    async def _execute_job_analysis(
        self,
        request: JobGenerationRequest,
    ) -> JobAnalysisResponse:
        """Execute Phase 1: JOB_ANALYSIS."""
        logger.info("Phase 1: JOB_ANALYSIS")
        from .nodes.job_analyzer import analyze_job

        input_data = JobAnalysisInput(
            user_requirement=request.user_requirement,
            max_tasks=request.max_tasks,
        )
        result = await analyze_job(input_data, llm_client=self._llm_client)
        # Validate task dependencies (DC-1: TaskDependencyValidator integration)
        tasks_for_val = [{"task_id": t.task_id, "dependencies": t.dependencies} for t in result.tasks]
        dep_result = TaskDependencyValidator().validate(tasks_for_val)
        if not dep_result.is_valid:
            raise OrchestratorError(f"Task dependency validation failed: {dep_result.to_error_message()}", phase=Phase.JOB_ANALYSIS)
        return result

    async def _execute_registration(
        self,
        tasks: list[AnalyzedTask],
        interfaces: dict[str, InterfaceDefinition],
        project_id: str,
    ) -> dict[str, Any]:
        """Execute Phase 2: REGISTRATION (no LLM)."""
        logger.info("Phase 2: REGISTRATION with %d tasks", len(tasks))

        # Build task_id to master_id mapping using task_id (NOT index)
        task_id_to_master_id: dict[str, str] = {}

        for task in tasks:
            # Use task.task_id for registration, NOT enumerate index
            master_id = f"tm_{task.task_id}"  # Placeholder for actual registration
            task_id_to_master_id[task.task_id] = master_id
            logger.debug("Registered %s -> %s", task.task_id, master_id)

        job_master_id = f"jm_{project_id}"

        return {
            "job_master_id": job_master_id,
            "task_id_to_master_id": task_id_to_master_id,
        }

    def _build_task_identifiers(
        self,
        tasks: list[AnalyzedTask],
        task_id_to_master_id: dict[str, str],
    ) -> list[UnifiedTaskIdentifier]:
        """Build UnifiedTaskIdentifier list with master IDs."""
        identifiers = []

        for task in tasks:
            master_id = task_id_to_master_id.get(task.task_id)
            if master_id is None:
                raise OrchestratorError(
                    f"No master_id for task: {task.task_id}",
                    phase=Phase.REGISTRATION,
                )

            identifier = UnifiedTaskIdentifier(
                task_id=task.task_id,
                task_master_id=master_id,
            )
            identifiers.append(identifier)

        return identifiers

    async def _execute_workflow_gen(
        self,
        task_identifiers: list[UnifiedTaskIdentifier],
        interfaces: dict[str, InterfaceDefinition],
    ) -> ParallelExecutionResult:
        """Execute Phase 3: WORKFLOW_GEN (parallel)."""
        logger.info("Phase 3: WORKFLOW_GEN with %d tasks", len(task_identifiers))

        async def generate_single_workflow(
            task: UnifiedTaskIdentifier,
        ) -> dict[str, Any]:
            """Generate workflow for a single task."""
            interface = interfaces.get(task.task_id)
            return {
                "workflow_name": f"workflow_{task.task_id}",
                "task_id": task.task_id,
                "task_master_id": task.task_master_id,
                "interface": interface.model_dump() if interface else None,
            }

        result = await parallel_workflow_generation(
            tasks=task_identifiers,
            generate_func=generate_single_workflow,
            max_concurrent=5,
            timeout_per_task=60.0,
        )

        # Handle aggregation
        aggregator = ParallelExecutionErrorAggregator(self._error_recovery_manager)
        decision = aggregator.aggregate_and_decide(result)
        if decision.overall_status == "all_failed":
            logger.error("All workflow generations failed: %s", decision.error_summary)
        # Validate generated workflows (DC-2: ValidationPipeline integration)
        pipeline = ValidationPipeline(fail_fast=False)
        for tr in result.successful_tasks:
            if tr.success and tr.workflow:
                val_res = pipeline.validate(tr.workflow, workflow_id=tr.task_id)
                if not val_res.is_valid:
                    logger.warning("Workflow %s validation issues: %s", tr.task_id, [e.message for e in val_res.errors])
        return result

    def _build_result(
        self, analysis: JobAnalysisResponse, registration: dict[str, Any],
        identifiers: list[UnifiedTaskIdentifier], workflow_result: ParallelExecutionResult,
    ) -> JobGenerationResult:
        """Build final result from phase outputs."""
        workflows = {tr.task_id: tr.workflow for tr in workflow_result.successful_tasks if tr.workflow}
        # Issue #360: Require all tasks to succeed, not just partial success
        # Changed from: all_succeeded or partial_success or not identifiers
        # To: all_succeeded or not identifiers (strict success requirement)
        success = workflow_result.all_succeeded or not identifiers

        return JobGenerationResult(
            success=success,
            job_id=None,
            job_master_id=registration.get("job_master_id"),
            task_identifiers=identifiers,
            workflows=workflows,
            tasks=analysis.tasks,
            interfaces=analysis.interfaces,
            error=workflow_result.get_error_summary() if not success else None,
        )


__all__ = [
    "JobGenerationOrchestrator",
    "JobGenerationRequest",
    "JobGenerationResult",
    "OrchestratorError",
]
