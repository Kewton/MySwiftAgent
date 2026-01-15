"""Unit tests for parallel_executor.

Issue #359: Tests for parallel workflow generation.

TDD Red Phase: These tests define the expected behavior of parallel execution.
"""

import asyncio

import pytest
from aiagent.langgraph.jobGeneratorV2.error_recovery_v3 import ErrorRecoveryManager
from aiagent.langgraph.jobGeneratorV2.types_v3 import (
    ErrorType,
    ParallelExecutionResult,
    TaskExecutionError,
    TaskResult,
    UnifiedTaskIdentifier,
)

from aiagent.langgraph.jobGeneratorV2.parallel_executor import (
    AggregatedRecoveryDecision,
    ParallelExecutionErrorAggregator,
    parallel_workflow_generation,
)


class TestParallelWorkflowGeneration:
    """Test suite for parallel_workflow_generation function."""

    @pytest.mark.asyncio
    async def test_empty_task_list_returns_empty_result(self):
        """Test that empty task list returns empty result."""
        result = await parallel_workflow_generation(
            tasks=[],
            generate_func=self._mock_generator,
        )

        assert isinstance(result, ParallelExecutionResult)
        assert len(result.successful_tasks) == 0
        assert len(result.failed_tasks) == 0

    @pytest.mark.asyncio
    async def test_single_task_success(self):
        """Test single task execution succeeds."""
        tasks = [UnifiedTaskIdentifier(task_id="task_001")]

        result = await parallel_workflow_generation(
            tasks=tasks,
            generate_func=self._mock_generator,
        )

        assert len(result.successful_tasks) == 1
        assert len(result.failed_tasks) == 0
        assert result.successful_tasks[0].task_id == "task_001"
        assert result.all_succeeded is True

    @pytest.mark.asyncio
    async def test_multiple_tasks_parallel_execution(self):
        """Test multiple tasks execute in parallel."""
        tasks = [
            UnifiedTaskIdentifier(task_id="task_001"),
            UnifiedTaskIdentifier(task_id="task_002"),
            UnifiedTaskIdentifier(task_id="task_003"),
        ]

        result = await parallel_workflow_generation(
            tasks=tasks,
            generate_func=self._mock_generator,
            max_concurrent=3,
        )

        assert len(result.successful_tasks) == 3
        assert len(result.failed_tasks) == 0
        assert result.all_succeeded is True

    @pytest.mark.asyncio
    async def test_partial_failure_handling(self):
        """Test handling of partial failures."""
        tasks = [
            UnifiedTaskIdentifier(task_id="task_001"),
            UnifiedTaskIdentifier(task_id="task_fail"),  # Will fail
            UnifiedTaskIdentifier(task_id="task_003"),
        ]

        result = await parallel_workflow_generation(
            tasks=tasks,
            generate_func=self._mock_generator_with_failure,
        )

        assert len(result.successful_tasks) == 2
        assert len(result.failed_tasks) == 1
        assert result.partial_success is True
        assert result.failed_tasks[0].task_id == "task_fail"

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test that task timeouts are handled properly."""
        tasks = [
            UnifiedTaskIdentifier(task_id="task_slow"),  # Will timeout
        ]

        result = await parallel_workflow_generation(
            tasks=tasks,
            generate_func=self._mock_slow_generator,
            timeout_per_task=0.1,  # Very short timeout
        )

        assert len(result.failed_tasks) == 1
        assert result.failed_tasks[0].error is not None
        assert result.failed_tasks[0].error.error_type == ErrorType.TRANSIENT
        assert "timed out" in result.failed_tasks[0].error.message.lower()

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        """Test that semaphore properly limits concurrency."""
        tasks = [
            UnifiedTaskIdentifier(task_id=f"task_{i}")
            for i in range(10)
        ]

        # Track max concurrent executions
        execution_count = {"current": 0, "max": 0}

        async def tracking_generator(task: UnifiedTaskIdentifier) -> dict:
            execution_count["current"] += 1
            execution_count["max"] = max(
                execution_count["max"],
                execution_count["current"]
            )
            await asyncio.sleep(0.05)  # Small delay
            execution_count["current"] -= 1
            return {"workflow_name": f"workflow_{task.task_id}"}

        result = await parallel_workflow_generation(
            tasks=tasks,
            generate_func=tracking_generator,
            max_concurrent=3,
        )

        assert result.all_succeeded is True
        # Max concurrent should not exceed semaphore limit
        assert execution_count["max"] <= 3

    @pytest.mark.asyncio
    async def test_execution_time_tracking(self):
        """Test that execution time is tracked."""
        tasks = [UnifiedTaskIdentifier(task_id="task_001")]

        result = await parallel_workflow_generation(
            tasks=tasks,
            generate_func=self._mock_generator,
        )

        assert result.total_execution_time_ms > 0
        assert result.successful_tasks[0].execution_time_ms > 0

    @pytest.mark.asyncio
    async def test_validation_error_captured(self):
        """Test that validation errors are captured with details."""
        tasks = [UnifiedTaskIdentifier(task_id="task_validation_error")]

        result = await parallel_workflow_generation(
            tasks=tasks,
            generate_func=self._mock_validation_error,
        )

        assert len(result.failed_tasks) == 1
        assert result.failed_tasks[0].error.error_type == ErrorType.VALIDATION
        assert result.failed_tasks[0].error.recoverable is True

    # Helper methods for mocking

    async def _mock_generator(self, task: UnifiedTaskIdentifier) -> dict:
        """Mock successful workflow generation."""
        return {"workflow_name": f"workflow_{task.task_id}"}

    async def _mock_generator_with_failure(self, task: UnifiedTaskIdentifier) -> dict:
        """Mock generator that fails for specific task."""
        if "fail" in task.task_id:
            raise ValueError("Intentional failure for testing")
        return {"workflow_name": f"workflow_{task.task_id}"}

    async def _mock_slow_generator(self, task: UnifiedTaskIdentifier) -> dict:
        """Mock slow generator that will timeout."""
        await asyncio.sleep(10)  # Long delay
        return {"workflow_name": f"workflow_{task.task_id}"}

    async def _mock_validation_error(self, task: UnifiedTaskIdentifier) -> dict:
        """Mock generator that raises validation error."""
        from pydantic import BaseModel

        class TestModel(BaseModel):
            required_field: str

        # This will raise ValidationError
        TestModel.model_validate({})


class TestParallelExecutionErrorAggregator:
    """Test suite for ParallelExecutionErrorAggregator."""

    def test_all_succeeded(self):
        """Test aggregation when all tasks succeed."""
        manager = ErrorRecoveryManager()
        aggregator = ParallelExecutionErrorAggregator(manager)

        result = ParallelExecutionResult(
            successful_tasks=[
                TaskResult(task_id="task_001", success=True, workflow={"name": "wf1"}),
                TaskResult(task_id="task_002", success=True, workflow={"name": "wf2"}),
            ],
            failed_tasks=[],
        )

        decision = aggregator.aggregate_and_decide(result)

        assert decision.overall_status == "success"
        assert decision.proceed is True
        assert len(decision.successful_workflows) == 2

    def test_partial_success_with_retryable_errors(self):
        """Test aggregation with partial success and retryable errors."""
        manager = ErrorRecoveryManager()
        aggregator = ParallelExecutionErrorAggregator(manager)

        result = ParallelExecutionResult(
            successful_tasks=[
                TaskResult(task_id="task_001", success=True, workflow={"name": "wf1"}),
            ],
            failed_tasks=[
                TaskResult(
                    task_id="task_002",
                    success=False,
                    error=TaskExecutionError(
                        error_type=ErrorType.TRANSIENT,
                        message="Timeout",
                        recoverable=True
                    )
                ),
            ],
        )

        decision = aggregator.aggregate_and_decide(result)

        assert decision.overall_status == "partial_retry"
        assert decision.proceed is False
        assert "task_002" in decision.tasks_to_retry

    def test_partial_success_with_non_retryable_errors(self):
        """Test aggregation with partial success and non-retryable errors."""
        manager = ErrorRecoveryManager()
        aggregator = ParallelExecutionErrorAggregator(manager)

        result = ParallelExecutionResult(
            successful_tasks=[
                TaskResult(task_id="task_001", success=True, workflow={"name": "wf1"}),
            ],
            failed_tasks=[
                TaskResult(
                    task_id="task_002",
                    success=False,
                    error=TaskExecutionError(
                        error_type=ErrorType.FATAL,
                        message="Fatal error",
                        recoverable=False
                    )
                ),
            ],
        )

        decision = aggregator.aggregate_and_decide(result)

        assert decision.overall_status == "partial_success"
        assert decision.proceed is True
        assert "task_002" in decision.failed_task_ids

    def test_all_failed(self):
        """Test aggregation when all tasks fail."""
        manager = ErrorRecoveryManager()
        aggregator = ParallelExecutionErrorAggregator(manager)

        result = ParallelExecutionResult(
            successful_tasks=[],
            failed_tasks=[
                TaskResult(
                    task_id="task_001",
                    success=False,
                    error=TaskExecutionError(
                        error_type=ErrorType.FATAL,
                        message="Fatal error",
                        recoverable=False
                    )
                ),
            ],
        )

        decision = aggregator.aggregate_and_decide(result)

        assert decision.overall_status == "all_failed"
        assert decision.proceed is False


class TestAggregatedRecoveryDecision:
    """Test suite for AggregatedRecoveryDecision."""

    def test_create_success_decision(self):
        """Test creating a success decision."""
        decision = AggregatedRecoveryDecision(
            overall_status="success",
            proceed=True,
            successful_workflows=[{"name": "wf1"}, {"name": "wf2"}]
        )

        assert decision.overall_status == "success"
        assert decision.proceed is True
        assert len(decision.successful_workflows) == 2

    def test_create_partial_retry_decision(self):
        """Test creating a partial retry decision."""
        decision = AggregatedRecoveryDecision(
            overall_status="partial_retry",
            proceed=False,
            tasks_to_retry=["task_001", "task_002"],
            successful_workflows=[{"name": "wf1"}]
        )

        assert decision.overall_status == "partial_retry"
        assert decision.proceed is False
        assert len(decision.tasks_to_retry) == 2

    def test_default_values(self):
        """Test default values for optional fields."""
        decision = AggregatedRecoveryDecision(
            overall_status="success",
            proceed=True
        )

        assert decision.successful_workflows == []
        assert decision.failed_task_ids == []
        assert decision.tasks_to_retry == []
        assert decision.recovery_strategy is None
        assert decision.error_summary is None
