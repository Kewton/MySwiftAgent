"""TaskBreakdownWorkflow for Job Generator V2.

This module implements the main TaskBreakdownWorkflow that:
1. Orchestrates sub-workflows (decomposer, feasibility, alternative)
2. Implements WorkflowProtocol for orchestrator integration
3. Returns TaskBreakdownOutput with appropriate PhaseStatus

Issue #342 Phase B.4: Main workflow orchestrating sub-workflows

Key design decisions:
- Implements WorkflowProtocol for use with JobGenerationOrchestrator
- Orchestrates: decomposer -> feasibility -> alternative (if needed)
- Returns NEEDS_RELAXATION when no alternatives found
- Handles errors from sub-workflows appropriately
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
    TaskBreakdownInput,
    TaskBreakdownOutput,
    TaskDefinition,
)

from .alternative import AlternativeSubWorkflow
from .decomposer import TaskDecomposerSubWorkflow
from .feasibility import FeasibilitySubWorkflow, load_capabilities_from_yaml

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext

logger = logging.getLogger(__name__)


class TaskBreakdownWorkflow:
    """Main workflow for task breakdown phase.

    This workflow orchestrates the task breakdown process:
    1. Decompose user requirements into tasks
    2. Check feasibility of each task
    3. Generate alternatives for infeasible tasks (if any)
    4. Return appropriate output based on results

    Implements WorkflowProtocol for use with JobGenerationOrchestrator.

    Example:
        workflow = TaskBreakdownWorkflow()
        output = await workflow.execute(input_data, context)
    """

    def __init__(self) -> None:
        """Initialize TaskBreakdownWorkflow."""
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
        input_data: TaskBreakdownInput,
        context: "ExecutionContext",
    ) -> TaskBreakdownOutput:
        """Execute the task breakdown workflow.

        Args:
            input_data: TaskBreakdownInput with requirements
            context: Execution context

        Returns:
            TaskBreakdownOutput with results

        Raises:
            WorkflowError: If a recoverable error occurs
        """
        logger.info(
            "Starting TaskBreakdownWorkflow for job %s",
            context.job_id,
        )

        # Step 1: Decompose requirements into tasks
        decomposer = TaskDecomposerSubWorkflow()
        try:
            tasks = await decomposer.decompose(input_data, context)
        except WorkflowError:
            # Re-raise WorkflowError for recovery handling
            raise
        except Exception as e:
            logger.error("Unexpected error in decomposer: %s", e, exc_info=True)
            raise WorkflowError(
                f"Task decomposition failed: {e}",
                ErrorType.TRANSIENT,
                Phase.TASK_BREAKDOWN,
            ) from e

        if not tasks:
            logger.error("Decomposer returned no tasks")
            raise WorkflowError(
                "Task decomposition produced no tasks",
                ErrorType.VALIDATION,
                Phase.TASK_BREAKDOWN,
            )

        logger.info("Decomposed into %d tasks", len(tasks))

        # Step 2: Check feasibility
        capabilities = input_data.available_capabilities
        if not capabilities:
            capabilities = load_capabilities_from_yaml()

        feasibility = FeasibilitySubWorkflow(capabilities=capabilities)
        feasibility_report = await feasibility.check(tasks, context)

        logger.info(
            "Feasibility check: is_feasible=%s, infeasible_count=%d",
            feasibility_report.is_feasible,
            len(feasibility_report.infeasible_tasks),
        )

        # Step 3: If all tasks are feasible, return success
        if feasibility_report.is_feasible:
            return TaskBreakdownOutput(
                status=PhaseStatus.SUCCESS,
                tasks=tasks,
                feasibility_report=feasibility_report,
                relaxation_suggestions=[],
            )

        # Step 4: Generate alternatives for infeasible tasks
        infeasible_task_ids = set(feasibility_report.infeasible_tasks)
        feasible_tasks = [t for t in tasks if t.id not in infeasible_task_ids]
        infeasible_tasks = [t for t in tasks if t.id in infeasible_task_ids]

        alternative = AlternativeSubWorkflow(capabilities=capabilities)
        alternative_tasks, relaxation_suggestions = await alternative.generate(
            infeasible_tasks, context
        )

        logger.info(
            "Alternative generation: %d alternatives, %d relaxations",
            len(alternative_tasks),
            len(relaxation_suggestions),
        )

        # Step 5: Determine final output
        if alternative_tasks:
            # Replace infeasible tasks with alternatives
            final_tasks = feasible_tasks + alternative_tasks
            # Sort by priority (lower number = higher priority)
            final_tasks.sort(key=lambda t: t.priority)
            # Update dependency references
            final_tasks = _update_dependencies(
                final_tasks, infeasible_tasks, alternative_tasks
            )

            return TaskBreakdownOutput(
                status=PhaseStatus.SUCCESS,
                tasks=final_tasks,
                feasibility_report=feasibility_report,
                relaxation_suggestions=[],
            )

        # No alternatives found - need relaxation
        if relaxation_suggestions:
            return TaskBreakdownOutput(
                status=PhaseStatus.NEEDS_RELAXATION,
                tasks=feasible_tasks,
                feasibility_report=feasibility_report,
                relaxation_suggestions=relaxation_suggestions,
            )

        # No alternatives and no relaxation suggestions - fallback
        logger.warning(
            "No alternatives or relaxation suggestions generated"
        )
        return TaskBreakdownOutput(
            status=PhaseStatus.NEEDS_RELAXATION,
            tasks=feasible_tasks,
            feasibility_report=feasibility_report,
            relaxation_suggestions=[],
        )


def _update_dependencies(
    tasks: list[TaskDefinition],
    original_tasks: list[TaskDefinition],
    alternative_tasks: list[TaskDefinition],
) -> list[TaskDefinition]:
    """Update task dependencies after replacing tasks.

    Args:
        tasks: All tasks (feasible + alternatives)
        original_tasks: Original infeasible tasks
        alternative_tasks: Alternative tasks

    Returns:
        Tasks with updated dependencies
    """
    # Build mapping from original ID to alternative ID
    id_mapping: dict[str, str] = {}
    for orig, alt in zip(original_tasks, alternative_tasks, strict=False):
        id_mapping[orig.id] = alt.id

    # Update dependencies
    updated_tasks: list[TaskDefinition] = []
    for task in tasks:
        new_deps = [id_mapping.get(dep, dep) for dep in task.dependencies]
        if new_deps != task.dependencies:
            # Create new task with updated dependencies
            updated_task = TaskDefinition(
                id=task.id,
                name=task.name,
                description=task.description,
                task_type=task.task_type,
                recommended_api=task.recommended_api,
                priority=task.priority,
                dependencies=new_deps,
            )
            updated_tasks.append(updated_task)
        else:
            updated_tasks.append(task)

    return updated_tasks
