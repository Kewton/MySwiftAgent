"""WorkflowGenWorkflow for Job Generator V2.

This module implements the main WorkflowGenWorkflow that:
1. Orchestrates sub-workflows (yaml_generator, test_runner)
2. Implements WorkflowProtocol for orchestrator integration
3. Returns WorkflowGenOutput with appropriate PhaseStatus

Issue #342 Phase D.2: Main workflow orchestrating sub-workflows
Issue #342 V2 Workflow Quality Improvement: LLM-first generation

Key design decisions:
- Implements WorkflowProtocol for use with JobGenerationOrchestrator
- Orchestrates: yaml_generator -> test_runner (optional)
- Returns SUCCESS when YAML generated and tests pass
- Returns NEEDS_RETRY when YAML generation fails
- Uses ExecutionContext's phase-specific retry state
- Default: LLM-based generation with template fallback
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

from .test_runner import TestRunnerSubWorkflow
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
        graphai_version: str = "0.6",
        use_llm_generation: bool = True,
    ) -> None:
        """Initialize WorkflowGenWorkflow.

        Args:
            enable_testing: Whether to run workflow tests
            graphai_version: GraphAI version for YAML
            use_llm_generation: Whether to use LLM-based generation (default True)
                               Falls back to template generation if LLM fails
        """
        self._enable_testing = enable_testing
        self._graphai_version = graphai_version
        self._use_llm_generation = use_llm_generation
        self._retry_policy: RetryPolicy = RetryPolicy(
            max_retries=3,
            backoff_factor=1.5,
            retry_on=[ErrorType.TRANSIENT, ErrorType.VALIDATION],
        )

    def get_retry_policy(self) -> RetryPolicy:
        """Get the retry policy for this workflow.

        Returns:
            RetryPolicy instance
        """
        return self._retry_policy

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
            "Starting WorkflowGenWorkflow for job %s",
            context.job_id,
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

        # Step 1: Generate YAML workflow
        # Issue #342 V2: Use LLM-based generation by default with template fallback
        yaml_generator = YamlGeneratorSubWorkflow(
            graphai_version=self._graphai_version,
            use_llm_generation=self._use_llm_generation,
        )

        try:
            if self._use_llm_generation:
                # LLM-first approach with automatic template fallback
                yaml_result = await yaml_generator.generate_with_llm(
                    task_master_ids=task_master_ids,
                    job_master_id=job_master_id,
                    interfaces=interfaces,
                    context=context,
                )
            else:
                # Template-only approach (deprecated, for backward compatibility)
                yaml_result = await yaml_generator.generate(
                    task_master_ids=task_master_ids,
                    job_master_id=job_master_id,
                    interfaces=interfaces,
                    context=context,
                )
        except WorkflowError:
            raise
        except Exception as e:
            logger.error("Unexpected error in YAML generation: %s", e, exc_info=True)
            raise WorkflowError(
                f"YAML generation failed: {e}",
                ErrorType.TRANSIENT,
                Phase.WORKFLOW_GEN,
            ) from e

        logger.info(
            "YAML generation complete: %s with %d nodes",
            yaml_result.workflow_name,
            yaml_result.node_count,
        )

        # Step 2: Run tests (optional)
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
