"""Adapter for Job Generator 3-Phase Architecture.

Issue #359: Adapter layer for 3-phase unified ID pattern.

This adapter:
- Creates and configures JobGenerationOrchestrator
- Maintains backward compatibility with existing API
- Converts results to JobGeneratorResponse format
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable

from core.config import settings

# Re-export from adapter_old for backward compatibility
from .adapter_old import JobGeneratorV2Adapter
from .error_recovery import ErrorRecoveryManager
from .llm_utils import invoke_structured_llm
from .nodes.job_analyzer import AnalyzedTask, InterfaceDefinition
from .orchestrator import (
    JobGenerationOrchestrator,
    JobGenerationRequest,
    JobGenerationResult,
)
from .protocols import ProgressReporter

if TYPE_CHECKING:
    from app.schemas.job_generator import JobGeneratorResponse

logger = logging.getLogger(__name__)


class JobGeneratorAdapter:
    """Adapter to connect Job Generator 3-phase to the existing API.

    This adapter:
    - Creates Orchestrator3-phase with proper configuration
    - Handles API compatibility layer
    - Converts 3-phase results to existing response format
    """

    def __init__(
        self,
        max_retry: int = 5,
        langfuse_handler: Any = None,
        model_name: str | None = None,
        progress_reporter: ProgressReporter | None = None,
        engine: str = "taskflow",
    ) -> None:
        """Initialize the 3-phase adapter.

        Args:
            max_retry: Maximum total retries across all phases
            langfuse_handler: Optional Langfuse callback handler
            model_name: Optional LLM model name override
            progress_reporter: Optional progress reporter
            engine: Workflow generation engine ('taskflow' or 'graphai')
        """
        self._max_retry = max_retry
        self._langfuse_handler = langfuse_handler
        self._model_name = (
            model_name or settings.JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL
        )
        self._progress_reporter = progress_reporter
        self._engine = engine

        # Create recovery manager and orchestrator
        self._recovery_manager = ErrorRecoveryManager(max_total_retries=max_retry)
        self._orchestrator = self._create_orchestrator()

    def _create_llm_client(self) -> Callable[..., Any]:
        """Create LLM client callable using existing invoke_structured_llm.

        Supports Claude/GPT/Gemini based on model_name setting.

        Returns:
            Callable that accepts (system_prompt, user_prompt, response_model)
            and returns the structured response.
        """

        async def llm_client(
            system_prompt: str,
            user_prompt: str,
            response_model: type,
        ) -> Any:
            # Build callbacks for Langfuse tracing
            callbacks = [self._langfuse_handler] if self._langfuse_handler else None

            # Use existing invoke_structured_llm (supports Claude/GPT/Gemini)
            result: Any = await invoke_structured_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=response_model,
                model_name=self._model_name,
                callbacks=callbacks,
            )

            return result.result  # StructuredCallResult.result

        return llm_client

    def _create_orchestrator(self) -> JobGenerationOrchestrator:
        """Create and configure the 3-phase orchestrator."""
        return JobGenerationOrchestrator(
            error_recovery_manager=self._recovery_manager,
            llm_client=self._create_llm_client(),
        )

    async def generate(
        self,
        user_requirement: str,
        project_id: str = "default_project",
        max_tasks: int = 10,
        job_id: str | None = None,
        engine: str | None = None,
    ) -> "JobGeneratorResponse":
        """Generate job using 3-phase architecture.

        Issue #386: Passes trace_id to run_workflow for observability propagation.

        Args:
            user_requirement: Natural language requirement
            project_id: Project ID for the job
            max_tasks: Maximum number of tasks
            job_id: Optional pre-generated job ID
            engine: Optional workflow engine override

        Returns:
            JobGeneratorResponse compatible with existing API
        """
        from app.services.langfuse_service import LangfuseService

        effective_engine = engine if engine is not None else self._engine

        logger.info(
            "JobGeneratorAdapter.generate (engine=%s): %s...",
            effective_engine,
            user_requirement[:100],
        )

        # Create request
        request = JobGenerationRequest(
            user_requirement=user_requirement,
            project_id=project_id,
            max_tasks=max_tasks,
            engine=effective_engine,
        )

        # Issue #386: Extract trace_id from langfuse_handler BEFORE run_workflow
        langfuse_trace_id = LangfuseService.extract_trace_id(self._langfuse_handler)

        # Run workflow with trace_id propagation (AC-6)
        import uuid

        actual_job_id = job_id or str(uuid.uuid4())
        result = await self._orchestrator.run_workflow(
            request,
            trace_id=langfuse_trace_id,
        )

        # Convert to response
        return self._convert_result(result, actual_job_id, langfuse_trace_id)

    def _convert_tasks_to_breakdown(
        self,
        tasks: list[AnalyzedTask],
    ) -> list[dict[str, Any]]:
        """Convert AnalyzedTask list to task_breakdown format.

        Args:
            tasks: List of AnalyzedTask objects

        Returns:
            List of dicts for JobGeneratorResponse.task_breakdown
        """
        import re

        def extract_sort_key(task_id: str) -> tuple[int, int]:
            """Extract sort key from task_id."""
            match = re.match(r"task_(\d+)(?:_alt)?", task_id)
            if match:
                num = int(match.group(1))
                is_alt = 1 if "_alt" in task_id else 0
                return (num, is_alt)
            return (999, 0)

        sorted_tasks = sorted(tasks, key=lambda t: extract_sort_key(t.task_id))

        return [
            {
                "task_id": task.task_id,
                "name": task.name,
                "description": task.description,
                "dependencies": task.dependencies,
                "priority": task.priority,
                "task_type": task.task_type,
                # Issue #396: Output as recommended_apis (plural list) for TaskBreakdownItem compatibility
                "recommended_apis": [task.recommended_api]
                if task.recommended_api
                else [],
            }
            for task in sorted_tasks
        ]

    def _convert_interfaces(
        self,
        interfaces: dict[str, InterfaceDefinition],
    ) -> dict[str, dict[str, Any]]:
        """Convert InterfaceDefinition dict to API format.

        Issue #404: Now includes derived_fields for downstream task requirements.

        Args:
            interfaces: Dict mapping task_id to InterfaceDefinition

        Returns:
            Dict for JobGeneratorResponse.interface_definitions
        """
        return {
            task_id: {
                "input_schema": interface.input_schema,
                "output_schema": interface.output_schema,
                "description": interface.description,
                "derived_fields": interface.derived_fields,  # Issue #404 AC-10
            }
            for task_id, interface in interfaces.items()
        }

    def _build_workflow_statuses(
        self,
        result: JobGenerationResult,
    ) -> list[dict[str, Any]] | None:
        """Build workflow_statuses from JobGenerationResult.

        Issue #396: Build workflow statuses for UI display.

        Args:
            result: 3-phase result containing tasks and workflows

        Returns:
            List of workflow status dicts for API response
        """
        if not result.tasks:
            return None

        workflow_statuses = []
        for task in result.tasks:
            workflow = result.workflows.get(task.task_id)
            if workflow:
                # Successful workflow
                workflow_statuses.append(
                    {
                        "task_id": task.task_id,
                        "task_name": task.name,
                        "status": "success",
                        "workflow_name": workflow.get("workflow_name", task.task_id),
                    }
                )
            else:
                # Failed or pending workflow
                workflow_statuses.append(
                    {
                        "task_id": task.task_id,
                        "task_name": task.name,
                        "status": "failed",
                        "error_message": f"Workflow not generated for {task.task_id}",
                    }
                )

        return workflow_statuses if workflow_statuses else None

    def _convert_result(
        self,
        result: JobGenerationResult,
        job_id: str,
        langfuse_trace_id: str | None = None,
    ) -> "JobGeneratorResponse":
        """Convert 3-phase result to JobGeneratorResponse.

        Args:
            result: 3-phase result from orchestrator
            job_id: Job ID
            langfuse_trace_id: Optional Langfuse trace ID

        Returns:
            JobGeneratorResponse for API
        """
        from app.schemas.job_generator import JobGeneratorResponse

        # Issue #396: Build workflow_statuses from result
        workflow_statuses = self._build_workflow_statuses(result)

        if result.success:
            task_breakdown = (
                self._convert_tasks_to_breakdown(result.tasks) if result.tasks else None
            )
            interface_definitions = (
                self._convert_interfaces(result.interfaces)
                if result.interfaces
                else None
            )

            return JobGeneratorResponse(
                status="success",
                job_id=result.job_id or job_id,
                job_master_id=result.job_master_id,
                task_breakdown=task_breakdown,
                interface_definitions=interface_definitions,
                evaluation_result=None,
                infeasible_tasks=[],
                alternative_proposals=[],
                api_extension_proposals=[],
                requirement_relaxation_suggestions=[],
                validation_errors=[],
                error_message=None,
                langfuse_trace_id=langfuse_trace_id,
                workflow_statuses=workflow_statuses,  # Issue #396
            )
        else:
            return JobGeneratorResponse(
                status="failed",
                job_id=result.job_id or job_id,
                job_master_id=result.job_master_id,
                task_breakdown=None,
                interface_definitions=None,
                evaluation_result=None,
                infeasible_tasks=[],
                alternative_proposals=[],
                api_extension_proposals=[],
                requirement_relaxation_suggestions=[],
                validation_errors=[],
                error_message=result.error,
                langfuse_trace_id=langfuse_trace_id,
                workflow_statuses=workflow_statuses,  # Issue #396
            )


__all__ = ["JobGeneratorAdapter", "JobGeneratorV2Adapter"]
