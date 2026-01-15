"""Parallel Workflow Generation Executor.

Issue #359: Parallel execution mechanism for Phase 3 (WORKFLOW_GEN).

This module provides:
- parallel_workflow_generation(): Execute workflow generation for multiple tasks
- ParallelExecutionErrorAggregator: Aggregate results and decide recovery
- AggregatedRecoveryDecision: Recovery decision for parallel results

Key features:
- Semaphore-based concurrency control
- Per-task timeout handling
- Error isolation (one failure doesn't stop others)
- Result aggregation and classification
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from pydantic import ValidationError

from .error_recovery import ErrorRecoveryManager
from .types import (
    ErrorType,
    ParallelExecutionResult,
    RecoveryStrategy,
    TaskExecutionError,
    TaskResult,
    UnifiedTaskIdentifier,
)

logger = logging.getLogger(__name__)

# Type alias for workflow generation function
GenerateFunc = Callable[[UnifiedTaskIdentifier], Awaitable[dict[str, Any]]]


async def parallel_workflow_generation(
    tasks: list[UnifiedTaskIdentifier],
    generate_func: GenerateFunc,
    max_concurrent: int = 5,
    timeout_per_task: float = 60.0,
) -> ParallelExecutionResult:
    """Execute workflow generation for multiple tasks in parallel.

    This function orchestrates parallel execution with:
    - Semaphore-based concurrency limiting
    - Per-task timeout handling
    - Error isolation (failures don't affect other tasks)
    - Result aggregation

    Args:
        tasks: List of task identifiers to process
        generate_func: Async function to generate workflow for a task
        max_concurrent: Maximum concurrent executions (default: 5)
        timeout_per_task: Timeout per task in seconds (default: 60)

    Returns:
        ParallelExecutionResult with successful and failed tasks

    Example:
        async def generate_workflow(task):
            # Generate workflow logic
            return {"workflow_name": f"workflow_{task.task_id}"}

        result = await parallel_workflow_generation(
            tasks=[task1, task2],
            generate_func=generate_workflow,
        )
    """
    if not tasks:
        return ParallelExecutionResult(
            successful_tasks=[],
            failed_tasks=[],
            total_execution_time_ms=0.0
        )

    start_time = time.monotonic()
    semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_with_timeout(task: UnifiedTaskIdentifier) -> TaskResult:
        """Execute a single task with timeout and error handling."""
        async with semaphore:
            task_start = time.monotonic()
            try:
                workflow = await asyncio.wait_for(
                    generate_func(task),
                    timeout=timeout_per_task
                )
                return TaskResult(
                    task_id=task.task_id,
                    success=True,
                    workflow=workflow,
                    execution_time_ms=(time.monotonic() - task_start) * 1000
                )
            except asyncio.TimeoutError:
                logger.warning(
                    "Task %s timed out after %.1fs",
                    task.task_id,
                    timeout_per_task
                )
                return TaskResult(
                    task_id=task.task_id,
                    success=False,
                    error=TaskExecutionError(
                        error_type=ErrorType.TRANSIENT,
                        message=f"Task execution timed out after {timeout_per_task}s",
                        recoverable=True
                    ),
                    execution_time_ms=(time.monotonic() - task_start) * 1000
                )
            except ValidationError as e:
                logger.warning(
                    "Task %s validation error: %s",
                    task.task_id,
                    str(e)
                )
                return TaskResult(
                    task_id=task.task_id,
                    success=False,
                    error=TaskExecutionError(
                        error_type=ErrorType.VALIDATION,
                        message=str(e),
                        recoverable=True,
                        details={"errors": e.errors()} if hasattr(e, "errors") else None
                    ),
                    execution_time_ms=(time.monotonic() - task_start) * 1000
                )
            except Exception as e:
                # Determine error type based on exception
                error_type = _classify_exception(e)
                logger.exception(
                    "Task %s failed with %s error: %s",
                    task.task_id,
                    error_type.value,
                    str(e)
                )
                return TaskResult(
                    task_id=task.task_id,
                    success=False,
                    error=TaskExecutionError(
                        error_type=error_type,
                        message=str(e),
                        recoverable=error_type != ErrorType.FATAL
                    ),
                    execution_time_ms=(time.monotonic() - task_start) * 1000
                )

    # Execute all tasks in parallel
    results = await asyncio.gather(
        *[execute_with_timeout(task) for task in tasks]
    )

    # Classify results
    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    total_time = (time.monotonic() - start_time) * 1000

    logger.info(
        "Parallel execution complete: %d/%d successful in %.1fms",
        len(successful),
        len(tasks),
        total_time
    )

    return ParallelExecutionResult(
        successful_tasks=successful,
        failed_tasks=failed,
        total_execution_time_ms=total_time
    )


def _classify_exception(e: Exception) -> ErrorType:
    """Classify an exception into an ErrorType.

    Args:
        e: The exception to classify

    Returns:
        Appropriate ErrorType
    """
    # Common transient errors
    transient_types = (
        TimeoutError,
        ConnectionError,
        asyncio.TimeoutError,
    )
    if isinstance(e, transient_types):
        return ErrorType.TRANSIENT

    # Validation errors
    if isinstance(e, (ValueError, TypeError)):
        return ErrorType.VALIDATION

    # API errors (check for common API error patterns)
    error_str = str(e).lower()
    if any(term in error_str for term in ["rate limit", "api error", "http error"]):
        return ErrorType.API

    # Default to transient for unknown errors (can be retried)
    return ErrorType.TRANSIENT


@dataclass
class AggregatedRecoveryDecision:
    """Aggregated recovery decision for parallel execution results.

    Attributes:
        overall_status: Overall status (success, partial_success, partial_retry, all_failed)
        proceed: Whether to proceed to next phase
        successful_workflows: List of successfully generated workflows
        failed_task_ids: List of task IDs that failed permanently
        tasks_to_retry: List of task IDs to retry
        recovery_strategy: Recovery strategy if needed
        error_summary: Summary of errors
    """

    overall_status: str
    proceed: bool
    successful_workflows: list[dict[str, Any]] = field(default_factory=list)
    failed_task_ids: list[str] = field(default_factory=list)
    tasks_to_retry: list[str] = field(default_factory=list)
    recovery_strategy: Optional[RecoveryStrategy] = None
    error_summary: Optional[str] = None


class ParallelExecutionErrorAggregator:
    """Aggregator for parallel execution errors.

    Analyzes parallel execution results and produces an aggregated
    recovery decision.

    Example:
        aggregator = ParallelExecutionErrorAggregator(recovery_manager)
        decision = aggregator.aggregate_and_decide(parallel_result)
        if decision.proceed:
            # Continue to next phase
            pass
        elif decision.tasks_to_retry:
            # Retry failed tasks
            pass
    """

    def __init__(self, recovery_manager: ErrorRecoveryManager):
        """Initialize the aggregator.

        Args:
            recovery_manager: Error recovery manager for strategy decisions
        """
        self.recovery_manager = recovery_manager

    def aggregate_and_decide(
        self,
        result: ParallelExecutionResult
    ) -> AggregatedRecoveryDecision:
        """Aggregate parallel results and decide on recovery action.

        Args:
            result: Parallel execution result to analyze

        Returns:
            AggregatedRecoveryDecision with action to take
        """
        # All succeeded
        if result.all_succeeded:
            workflows = [r.workflow for r in result.successful_tasks if r.workflow]
            return AggregatedRecoveryDecision(
                overall_status="success",
                proceed=True,
                successful_workflows=workflows
            )

        # Partial success - check if failed tasks can be retried
        if result.partial_success:
            retryable = [
                f for f in result.failed_tasks
                if f.error and f.error.recoverable
            ]

            successful_workflows = [
                r.workflow for r in result.successful_tasks if r.workflow
            ]

            if retryable:
                # Some tasks can be retried
                return AggregatedRecoveryDecision(
                    overall_status="partial_retry",
                    proceed=False,
                    tasks_to_retry=[f.task_id for f in retryable],
                    successful_workflows=successful_workflows,
                    error_summary=result.get_error_summary()
                )

            # Non-retryable failures - proceed with partial success
            return AggregatedRecoveryDecision(
                overall_status="partial_success",
                proceed=True,
                successful_workflows=successful_workflows,
                failed_task_ids=[f.task_id for f in result.failed_tasks],
                error_summary=result.get_error_summary()
            )

        # All failed
        if result.all_failed:
            return AggregatedRecoveryDecision(
                overall_status="all_failed",
                proceed=False,
                recovery_strategy=RecoveryStrategy.ROLLBACK_TO_ANALYSIS,
                error_summary=result.get_error_summary()
            )

        # Default case (shouldn't reach here normally)
        return AggregatedRecoveryDecision(
            overall_status="unknown",
            proceed=False,
            recovery_strategy=RecoveryStrategy.FAIL_FAST
        )


# Export all
__all__ = [
    "parallel_workflow_generation",
    "ParallelExecutionErrorAggregator",
    "AggregatedRecoveryDecision",
]
