"""Adapter for Job Generator V2.

This module provides an adapter that connects the V2 architecture to the
existing job_generator_endpoints.py API, ensuring backward compatibility
while using the improved V2 implementation.

Issue #342 Phase E: Integration and Migration
Issue #342-V2-UX: Added progress_reporter support for real-time tracking

Key responsibilities:
1. Create ExecutionContext with real LLM clients
2. Instantiate Orchestrator with all workflows
3. Convert V2 output to existing JobGeneratorResponse format
4. Report progress to job_state_manager via progress_reporter
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from core.config import settings

from .context import (
    ContextBuilder,
    IntegrationContext,
    LLMContext,
    ObservabilityContext,
    StorageContext,
)
from .orchestrator import JobGenerationOrchestrator
from .protocols import ProgressReporter
from .recovery import ErrorRecoveryManager
from .types import (
    InterfaceSchema,
    JobGenerationRequest,
    JobGenerationResult,
    Phase,
    TaskDefinition,
)
from .workflows.interface_design import InterfaceDesignWorkflow
from .workflows.registration import RegistrationWorkflow
from .workflows.task_breakdown import TaskBreakdownWorkflow
from .workflows.workflow_gen import WorkflowGenWorkflow

if TYPE_CHECKING:
    from app.schemas.job_generator import JobGeneratorResponse

logger = logging.getLogger(__name__)


class JobGeneratorV2Adapter:
    """Adapter to connect Job Generator V2 to the existing API.

    This adapter creates and configures all V2 components:
    - ExecutionContext with LLM, storage, and observability
    - Orchestrator with all 4 workflow phases
    - Converts V2 outputs to existing response format

    Example:
        adapter = JobGeneratorV2Adapter(
            max_retry=5,
            langfuse_handler=callback_handler,
        )
        response = await adapter.generate(user_requirement)
    """

    def __init__(
        self,
        max_retry: int = 5,
        langfuse_handler: Any = None,
        model_name: str | None = None,
        progress_reporter: ProgressReporter | None = None,
    ) -> None:
        """Initialize the V2 adapter.

        Args:
            max_retry: Maximum total retries across all phases
            langfuse_handler: Optional Langfuse callback handler
            model_name: Optional LLM model name override
            progress_reporter: Optional progress reporter for real-time tracking
        """
        self._max_retry = max_retry
        self._langfuse_handler = langfuse_handler
        self._model_name = (
            model_name or settings.JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL
        )
        self._progress_reporter = progress_reporter

        # Create recovery manager
        self._recovery_manager = ErrorRecoveryManager()

        # Create orchestrator with progress reporter
        self._orchestrator = self._create_orchestrator()

    def _create_orchestrator(self) -> JobGenerationOrchestrator:
        """Create and configure the orchestrator with all workflows.

        Returns:
            Configured JobGenerationOrchestrator
        """
        # Issue #342-V2-UX: Pass progress_reporter to orchestrator
        orchestrator = JobGenerationOrchestrator(
            recovery_manager=self._recovery_manager,
            progress_reporter=self._progress_reporter,
        )

        # Register all workflows
        orchestrator.register_workflow(
            Phase.TASK_BREAKDOWN,
            TaskBreakdownWorkflow(),
        )
        orchestrator.register_workflow(
            Phase.INTERFACE_DESIGN,
            InterfaceDesignWorkflow(),
        )
        orchestrator.register_workflow(
            Phase.REGISTRATION,
            RegistrationWorkflow(
                graphai_server_url=settings.GRAPHAISERVER_BASE_URL,
            ),
        )
        orchestrator.register_workflow(
            Phase.WORKFLOW_GEN,
            WorkflowGenWorkflow(
                enable_testing=False,  # Disable testing in API context
                graphai_version="0.6",
            ),
        )

        return orchestrator

    def _create_context_builder(
        self,
        job_id: str,
        user_requirement: str,
    ) -> ContextBuilder:
        """Create a context builder with all required contexts.

        Args:
            job_id: Unique job identifier
            user_requirement: User's requirement string

        Returns:
            Configured ContextBuilder
        """
        builder = ContextBuilder()
        builder.with_job_id(job_id)
        builder.with_user_requirement(user_requirement)
        builder.with_max_retries(
            total=self._max_retry,
            per_phase=3,  # Default per-phase limit
        )

        # Configure LLM context
        llm_context = LLMContext(
            model_name=self._model_name,
            temperature=0.7,
            max_tokens=settings.JOB_GENERATOR_MAX_TOKENS,
        )
        builder.with_llm_context(llm_context)

        # Configure storage context (jobqueue client)
        storage_context = StorageContext(
            jobqueue_client=None,  # Will be created on-demand by workflows
        )
        builder.with_storage_context(storage_context)

        # Configure integration context
        integration_context = IntegrationContext(
            graphai_client=None,  # Will be created on-demand by workflows
            myvault_client=None,  # Will use secrets_manager
        )
        builder.with_integration_context(integration_context)

        # Configure observability context
        observability_context = ObservabilityContext(
            tracer=self._langfuse_handler,
            metrics_client=None,
        )
        builder.with_observability_context(observability_context)

        return builder

    async def generate(
        self,
        user_requirement: str,
        project_id: str = "default",
        max_tasks: int = 10,
        job_id: str | None = None,
    ) -> "JobGeneratorResponse":
        """Generate job and tasks using V2 architecture.

        Args:
            user_requirement: Natural language requirement
            project_id: Project ID for the job
            max_tasks: Maximum number of tasks to generate
            job_id: Optional pre-generated job ID

        Returns:
            JobGeneratorResponse compatible with existing API
        """
        from app.services.langfuse_service import LangfuseService

        logger.info(
            "JobGeneratorV2Adapter.generate called: %s...",
            user_requirement[:100],
        )

        # Create request
        request = JobGenerationRequest(
            user_requirement=user_requirement,
            project_id=project_id,
            max_tasks=max_tasks,
        )

        # Create and build context
        import uuid

        actual_job_id = job_id or str(uuid.uuid4())
        # Issue #342 V2: Build context with Langfuse tracer and pass to orchestrator
        context = self._create_context_builder(actual_job_id, user_requirement).build()

        # Run workflow with context for Langfuse tracing
        result = await self._orchestrator.run_workflow(request, context=context)

        # Issue #342: Extract trace_id from Langfuse handler for response
        langfuse_trace_id = LangfuseService.extract_trace_id(self._langfuse_handler)

        # Convert result to response with trace_id
        return self._convert_result(result, actual_job_id, langfuse_trace_id)

    def _convert_tasks_to_breakdown(
        self,
        tasks: list[TaskDefinition],
    ) -> list[dict[str, Any]]:
        """Convert V2 TaskDefinition list to list[dict] for JobGeneratorResponse.

        Issue #342: This method converts internal V2 task definitions to the
        format expected by JobGeneratorResponse.task_breakdown.

        Args:
            tasks: List of V2 TaskDefinition objects

        Returns:
            List of dicts compatible with JobGeneratorResponse.task_breakdown
        """
        return [
            {
                "task_id": task.id,
                "name": task.name,
                "description": task.description,
                "dependencies": task.dependencies,
                "priority": task.priority,
                "task_type": task.task_type,
                "recommended_api": task.recommended_api,
            }
            for task in tasks
        ]

    def _convert_interfaces(
        self,
        interfaces: dict[str, InterfaceSchema],
    ) -> dict[str, dict[str, Any]]:
        """Convert V2 InterfaceSchema dict to dict[str, dict] for JobGeneratorResponse.

        Issue #342: This method converts internal V2 interface schemas to the
        format expected by JobGeneratorResponse.interface_definitions.

        Args:
            interfaces: Dict mapping task_id to InterfaceSchema

        Returns:
            Dict compatible with JobGeneratorResponse.interface_definitions
        """
        return {
            task_id: {
                "input_schema": schema.input_schema,
                "output_schema": schema.output_schema,
                "description": schema.description,
            }
            for task_id, schema in interfaces.items()
        }

    def _convert_result(
        self,
        result: JobGenerationResult,
        job_id: str,
        langfuse_trace_id: str | None = None,
    ) -> "JobGeneratorResponse":
        """Convert V2 result to existing response format.

        Args:
            result: V2 JobGenerationResult
            job_id: Job ID used for tracking
            langfuse_trace_id: Optional Langfuse trace ID for observability

        Returns:
            JobGeneratorResponse compatible with existing API

        Issue #342: Extended to include task_breakdown and interface_definitions
        from the V2 result. Also now propagates langfuse_trace_id for tracing.
        """
        from app.schemas.job_generator import JobGeneratorResponse

        if result.success:
            # Issue #342: Convert V2 task/interface data to response format
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
                evaluation_result=None,  # V2 handles evaluation internally
                infeasible_tasks=[],
                alternative_proposals=[],
                api_extension_proposals=[],
                requirement_relaxation_suggestions=[
                    {
                        "original_requirement": s.original_requirement,
                        "suggested_alternative": s.suggested_alternative,
                        "reason": s.reason,
                    }
                    for s in result.relaxation_suggestions
                ],
                validation_errors=[],
                error_message=None,
                langfuse_trace_id=langfuse_trace_id,
            )
        else:
            # Handle failure or relaxation needed
            status = "failed"
            if result.relaxation_suggestions:
                status = "partial_success"

            return JobGeneratorResponse(
                status=status,
                job_id=result.job_id or job_id,
                job_master_id=result.job_master_id,
                task_breakdown=None,
                interface_definitions=None,
                evaluation_result=None,
                infeasible_tasks=[],
                alternative_proposals=[],
                api_extension_proposals=[],
                requirement_relaxation_suggestions=[
                    {
                        "original_requirement": s.original_requirement,
                        "suggested_alternative": s.suggested_alternative,
                        "reason": s.reason,
                    }
                    for s in result.relaxation_suggestions
                ],
                validation_errors=[],
                error_message=result.error,
                langfuse_trace_id=langfuse_trace_id,
            )


async def invoke_structured_llm_real(
    system_prompt: str,
    user_prompt: str,
    response_model: type,
    model_name: str = "claude-haiku-4-5",
    temperature: float = 0.7,
    **kwargs: Any,
) -> Any:
    """Invoke LLM with structured output using real LLM client.

    This function connects the placeholder invoke_structured_llm to real
    LLM services for Phase E integration.

    Args:
        system_prompt: System prompt for the LLM
        user_prompt: User prompt with the request
        response_model: Pydantic model class for the response
        model_name: Name of the model to use
        temperature: Sampling temperature
        **kwargs: Additional arguments

    Returns:
        StructuredCallResult with the parsed response

    Note:
        This implementation uses LangChain's ChatAnthropic with structured output.
        Future work could add support for other providers (Gemini, OpenAI).
    """
    from langchain_anthropic import ChatAnthropic
    from langchain_core.messages import HumanMessage, SystemMessage

    from .llm_utils import StructuredCallResult, StructuredLLMError

    try:
        # Create LLM client
        # Note: mypy reports false positive for ChatAnthropic due to langchain's
        # dynamic signature definition. Runtime tests confirm this works correctly.
        llm = ChatAnthropic(  # type: ignore[call-arg]
            model_name=model_name,
            temperature=temperature,
            max_tokens_to_sample=kwargs.get("max_tokens", 4096),
        )

        # Create structured output LLM
        structured_llm = llm.with_structured_output(response_model)

        # Create messages
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]

        # Invoke LLM
        result = await structured_llm.ainvoke(messages)

        return StructuredCallResult(
            result=result,
            recovered_via_json=False,
            model_name=model_name,
        )

    except Exception as e:
        logger.error("LLM invocation failed: %s", e, exc_info=True)
        raise StructuredLLMError(f"LLM invocation failed: {e}") from e
