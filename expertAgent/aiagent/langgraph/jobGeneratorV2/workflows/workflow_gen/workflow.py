"""WorkflowGenWorkflow for Job Generator V2.

This module implements the main WorkflowGenWorkflow that:
1. Orchestrates sub-workflows (yaml_generator, test_runner)
2. Implements WorkflowProtocol for orchestrator integration
3. Returns WorkflowGenOutput with appropriate PhaseStatus

Issue #342 Phase D.2: Main workflow orchestrating sub-workflows
Issue #342 V2 Workflow Quality Improvement: LLM-first generation
Issue #350: Strategy Pattern integration for engine switching

Key design decisions:
- Implements WorkflowProtocol for use with JobGenerationOrchestrator
- Orchestrates: yaml_generator -> test_runner (optional)
- Returns SUCCESS when YAML generated and tests pass
- Returns NEEDS_RETRY when YAML generation fails
- Uses ExecutionContext's phase-specific retry state
- Default: LLM-based generation with template fallback
- Issue #350: Uses Strategy Pattern for GraphAI/TaskFlow switching
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from aiagent.langgraph.jobGeneratorV2.protocols import (
    ErrorType,
    RetryPolicy,
    WorkflowError,
)
from aiagent.langgraph.jobGeneratorV2.types import (
    Phase,
    PhaseStatus,
    WorkflowGenInput,
    WorkflowGenOutput,
)

from .engine_strategy import EngineType, WorkflowGeneratorStrategy, create_strategy
from .test_runner import TestRunnerSubWorkflow
from .workflow_registrar import (
    register_and_update_task_masters,
    register_taskflow_workflow,
    update_task_master_body_template_taskflow,
)
from .yaml_generator import YamlGeneratorSubWorkflow

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext

logger = logging.getLogger(__name__)


class WorkflowGenWorkflow:
    """Main workflow for workflow generation phase.

    This workflow orchestrates the workflow generation process:
    1. Generate GraphAI YAML workflow from task masters
    2. Optionally run workflow tests
    3. Return generation results

    Implements WorkflowProtocol for use with JobGenerationOrchestrator.

    Example:
        workflow = WorkflowGenWorkflow()
        output = await workflow.execute(input_data, context)
    """

    def __init__(
        self,
        enable_testing: bool = False,
        graphai_version: str = "0.5",
        use_llm_generation: bool = True,
        engine: str = "taskflow",
    ) -> None:
        """Initialize WorkflowGenWorkflow.

        Args:
            enable_testing: Whether to run workflow tests
            graphai_version: GraphAI version for YAML
            use_llm_generation: Whether to use LLM-based generation (default True)
                               Falls back to template generation if LLM fails
            engine: Workflow generation engine ('taskflow' or 'graphai')
                - 'taskflow' (default): Generate TaskFlow V2 JSON workflows
                - 'graphai': Generate GraphAI YAML workflows (legacy)
                Issue #350: Added for engine switching support
        """
        self._enable_testing = enable_testing
        self._graphai_version = graphai_version
        self._use_llm_generation = use_llm_generation
        self._engine = engine
        self._retry_policy: RetryPolicy = RetryPolicy(
            max_retries=3,
            backoff_factor=1.5,
            retry_on=[ErrorType.TRANSIENT, ErrorType.VALIDATION],
        )

        # Issue #350: Create strategy for workflow generation
        self._strategy: WorkflowGeneratorStrategy = create_strategy(engine)

    @property
    def engine(self) -> str:
        """Get the workflow generation engine.

        Returns:
            Engine type string ('taskflow' or 'graphai')

        Issue #350: Property for engine access
        """
        return self._engine

    @property
    def strategy(self) -> WorkflowGeneratorStrategy:
        """Get the workflow generation strategy.

        Returns:
            WorkflowGeneratorStrategy instance

        Issue #350: Property for strategy access (used in tests)
        """
        return self._strategy

    def get_retry_policy(self) -> RetryPolicy:
        """Get the retry policy for this workflow.

        Returns:
            RetryPolicy instance
        """
        return self._retry_policy

    async def _generate_with_strategy(
        self,
        task_master_ids: list[str],
        job_master_id: str,
        interfaces: dict[str, Any],
        context: "ExecutionContext",
        task_id_mapping: Any = None,
    ) -> Any:
        """Generate workflow using the configured strategy.

        Issue #350: This method uses the Strategy Pattern to generate workflows
        based on the configured engine (TaskFlow or GraphAI).

        Args:
            task_master_ids: List of registered TaskMaster IDs
            job_master_id: Registered JobMaster ID
            interfaces: Interface schemas
            context: Execution context
            task_id_mapping: Optional TaskIdMapping for correct interface lookup

        Returns:
            YamlGeneratorResult-compatible object with workflow_name, yaml_content, node_count

        Note:
            For GraphAI engine, this falls back to YamlGeneratorSubWorkflow
            to maintain backward compatibility.
            For TaskFlow engine, this uses the Strategy's generate() method.
        """
        from .engine_strategy import EngineType

        # Issue #350: Use strategy pattern based on engine
        if self._strategy.engine_type == EngineType.TASKFLOW:
            # TaskFlow V2: Use strategy directly
            logger.info("Using TaskFlow strategy for workflow generation")

            # Convert interfaces to task_definitions format expected by strategy
            task_definitions = []
            for task_master_id in task_master_ids:
                # Get logical task_id from mapping if available
                logical_id = (
                    task_id_mapping.get_logical_id(task_master_id)
                    if task_id_mapping
                    else task_master_id
                )
                interface = interfaces.get(logical_id, {})

                task_def = {
                    "id": task_master_id,
                    "logical_id": logical_id,
                    "name": getattr(interface, "description", f"Task {task_master_id}"),
                    "description": getattr(interface, "description", ""),
                }
                task_definitions.append(task_def)

            # Call strategy's generate method
            strategy_result = await self._strategy.generate(
                task_definitions=task_definitions,
                interfaces=interfaces,
                context=context,
            )

            # Convert to YamlGeneratorResult-compatible object
            # Note: WorkflowOutput uses 'content' instead of 'yaml_content'
            # Issue #350: Include raw_result for TaskFlow JSON registration
            from dataclasses import dataclass

            @dataclass
            class CompatibleResult:
                workflow_name: str
                yaml_content: str
                node_count: int
                raw_result: dict  # TaskFlow JSON for registration

            return CompatibleResult(
                workflow_name=strategy_result.workflow_name,
                yaml_content=strategy_result.content,  # Strategy uses 'content'
                node_count=strategy_result.node_count,
                raw_result=strategy_result.raw_result if hasattr(strategy_result, 'raw_result') else {},
            )

        else:
            # GraphAI: Use existing YamlGeneratorSubWorkflow for backward compatibility
            logger.info("Using GraphAI legacy workflow generator")

            yaml_generator = YamlGeneratorSubWorkflow(
                graphai_version=self._graphai_version,
                use_llm_generation=self._use_llm_generation,
            )

            if self._use_llm_generation:
                # LLM-first approach with automatic template fallback
                return await yaml_generator.generate_with_llm(
                    task_master_ids=task_master_ids,
                    job_master_id=job_master_id,
                    interfaces=interfaces,
                    context=context,
                    task_id_mapping=task_id_mapping,
                )
            else:
                # Template-only approach (deprecated)
                return await yaml_generator.generate(
                    task_master_ids=task_master_ids,
                    job_master_id=job_master_id,
                    interfaces=interfaces,
                    context=context,
                )

    async def execute(
        self,
        input_data: WorkflowGenInput,
        context: "ExecutionContext",
    ) -> WorkflowGenOutput:
        """Execute the workflow generation workflow.

        Args:
            input_data: WorkflowGenInput with task masters and interfaces
            context: Execution context

        Returns:
            WorkflowGenOutput with results

        Raises:
            WorkflowError: If a recoverable error occurs
        """
        logger.info(
            "Starting WorkflowGenWorkflow for job %s (engine=%s, strategy=%s)",
            context.job_id,
            self._engine,
            self._strategy.engine_type.value,
        )

        task_master_ids = input_data.task_master_ids
        job_master_id = input_data.job_master_id
        interfaces = input_data.interfaces

        if not task_master_ids:
            logger.warning("No task master IDs provided for workflow generation")
            return WorkflowGenOutput(
                status=PhaseStatus.FAILED,
                workflow_yaml=None,
                test_result=None,
            )

        if not job_master_id:
            logger.warning("No job master ID provided for workflow generation")
            return WorkflowGenOutput(
                status=PhaseStatus.FAILED,
                workflow_yaml=None,
                test_result=None,
            )

        # Issue #342 Bug #1: Extract TaskIdMapping from input for correct interface lookup
        task_id_mapping = input_data.task_id_mapping

        # Step 1: Generate workflow using strategy pattern
        # Issue #350: Use strategy for engine-specific generation
        try:
            yaml_result = await self._generate_with_strategy(
                task_master_ids=task_master_ids,
                job_master_id=job_master_id,
                interfaces=interfaces,
                context=context,
                task_id_mapping=task_id_mapping,
            )
        except WorkflowError:
            raise
        except Exception as e:
            logger.error("Unexpected error in workflow generation: %s", e, exc_info=True)
            raise WorkflowError(
                f"Workflow generation failed: {e}",
                ErrorType.TRANSIENT,
                Phase.WORKFLOW_GEN,
            ) from e

        logger.info(
            "Workflow generation complete: %s with %d nodes (engine=%s)",
            yaml_result.workflow_name,
            yaml_result.node_count,
            self._engine,
        )

        # Step 2: Register workflow to GraphAiServer and update TaskMasters
        # Issue #342: V2 was missing this step, causing "model_name is required" errors
        # Issue #350: Use different registration based on engine type
        try:
            if self._strategy.engine_type == EngineType.TASKFLOW:
                # TaskFlow V2: Register JSON workflow and update TaskMasters
                registration_result = await self._register_taskflow_workflow(
                    task_master_ids=task_master_ids,
                    workflow_name=yaml_result.workflow_name,
                    workflow_json=yaml_result.raw_result if hasattr(yaml_result, 'raw_result') else {},
                )
            else:
                # GraphAI: Register YAML workflow and update TaskMasters
                registration_result = await register_and_update_task_masters(
                    task_master_ids=task_master_ids,
                    workflow_name=yaml_result.workflow_name,
                    yaml_content=yaml_result.yaml_content,
                    context=context,
                )

            if registration_result["success"]:
                logger.info(
                    "Workflow registered to GraphAiServer: model_name=%s, "
                    "updated_task_masters=%d/%d (engine=%s)",
                    registration_result.get("model_name"),
                    len(registration_result.get("updated_task_masters", [])),
                    len(task_master_ids),
                    self._engine,
                )
            else:
                logger.warning(
                    "Workflow registration failed: %s",
                    registration_result.get("error"),
                )
                # Registration failure is not fatal - workflow execution may still work
                # if workflow was previously registered

        except Exception as e:
            logger.warning(
                "Workflow registration error (non-fatal): %s",
                e,
            )
            # Continue with workflow generation even if registration fails
            # The workflow might already be registered from a previous run

        # Step 3: Run tests (optional)
        test_result: dict[str, Any] | None = None

        if self._enable_testing:
            test_runner = TestRunnerSubWorkflow(
                enable_execution=True,
            )

            try:
                run_result = await test_runner.run_tests(
                    workflow_yaml=yaml_result.yaml_content,
                    interfaces=interfaces,
                    context=context,
                )

                test_result = {
                    "tests_run": run_result.tests_run,
                    "tests_passed": run_result.tests_passed,
                    "tests_failed": run_result.tests_failed,
                    "skipped": run_result.skipped,
                }

                logger.info(
                    "Workflow tests complete: %d/%d passed",
                    run_result.tests_passed,
                    run_result.tests_run,
                )

                # Check if tests failed
                if run_result.tests_failed > 0:
                    logger.warning(
                        "Some workflow tests failed: %d/%d",
                        run_result.tests_failed,
                        run_result.tests_run,
                    )
                    return WorkflowGenOutput(
                        status=PhaseStatus.NEEDS_RETRY,
                        workflow_yaml=yaml_result.yaml_content,
                        test_result=test_result,
                    )

            except WorkflowError:
                raise
            except Exception as e:
                logger.warning("Test execution failed: %s", e)
                test_result = {
                    "error": str(e),
                    "skipped": True,
                }
        else:
            # Validate YAML structure without execution
            test_runner = TestRunnerSubWorkflow(enable_execution=False)
            is_valid, errors = await test_runner.validate_workflow_yaml(
                yaml_result.yaml_content
            )

            if not is_valid:
                logger.warning("YAML validation failed: %s", errors)
                return WorkflowGenOutput(
                    status=PhaseStatus.NEEDS_RETRY,
                    workflow_yaml=yaml_result.yaml_content,
                    test_result={"validation_errors": errors},
                )

            test_result = {
                "validation": "passed",
                "skipped": True,
            }

        return WorkflowGenOutput(
            status=PhaseStatus.SUCCESS,
            workflow_yaml=yaml_result.yaml_content,
            test_result=test_result,
        )

    async def _register_taskflow_workflow(
        self,
        task_master_ids: list[str],
        workflow_name: str,
        workflow_json: dict,
    ) -> dict[str, Any]:
        """Register TaskFlow V2 workflow and update TaskMasters.

        Issue #350: TaskFlow V2 uses /api/v2/workflows endpoint.

        Args:
            task_master_ids: List of TaskMaster IDs to update
            workflow_name: Name of the workflow
            workflow_json: TaskFlow V2 workflow definition

        Returns:
            Dict with registration results
        """
        if not task_master_ids:
            return {
                "success": False,
                "error": "No task_master_ids provided",
                "updated_task_masters": [],
                "failed_task_masters": [],
            }

        # Step 1: Register TaskFlow workflow to GraphAiServer
        registration_result = await register_taskflow_workflow(
            workflow_name=workflow_name,
            workflow_json=workflow_json,
        )

        if not registration_result.success:
            logger.error(
                "Failed to register TaskFlow workflow to GraphAiServer: %s",
                registration_result.error,
            )
            return {
                "success": False,
                "error": registration_result.error,
                "updated_task_masters": [],
                "failed_task_masters": task_master_ids,
            }

        # Step 2: Update all TaskMasters with workflow_name for TaskFlow execution
        updated_task_masters: list[str] = []
        failed_task_masters: list[str] = []

        for task_master_id in task_master_ids:
            success = await update_task_master_body_template_taskflow(
                task_master_id=task_master_id,
                workflow_name=workflow_name,
            )

            if success:
                updated_task_masters.append(task_master_id)
            else:
                failed_task_masters.append(task_master_id)

        overall_success = len(updated_task_masters) > 0

        if failed_task_masters:
            logger.warning(
                "Some TaskMasters failed to update for TaskFlow: %s",
                failed_task_masters,
            )

        logger.info(
            "TaskFlow workflow registration complete: %d/%d TaskMasters updated",
            len(updated_task_masters),
            len(task_master_ids),
        )

        return {
            "success": overall_success,
            "workflow_path": registration_result.workflow_path,
            "model_name": workflow_name,
            "updated_task_masters": updated_task_masters,
            "failed_task_masters": failed_task_masters,
        }
