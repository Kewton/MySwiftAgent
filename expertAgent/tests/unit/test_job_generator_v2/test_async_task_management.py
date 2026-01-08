"""Unit tests for async task management (Issue #342 Bug #9).

This module tests:
- Bug #9: Async task exceptions not handled (fire-and-forget)

Issue #342:
- Bug #9: asyncio.create_task handles are not stored and exceptions are lost
"""

import asyncio

import pytest

from aiagent.langgraph.jobGeneratorV2.progress import (
    AsyncTaskManager,
    JobStateProgressReporter,
)


class TestAsyncTaskManager:
    """Test AsyncTaskManager for proper async task handling (Bug #9)."""

    def test_async_task_manager_exists(self) -> None:
        """Bug #9: AsyncTaskManager class should exist."""
        assert AsyncTaskManager is not None

    @pytest.mark.anyio
    async def test_async_task_manager_stores_task_handles(self) -> None:
        """Bug #9: AsyncTaskManager should store task handles."""
        manager = AsyncTaskManager()

        async def dummy_task() -> str:
            await asyncio.sleep(0.01)
            return "done"

        task = manager.create_task(dummy_task(), name="test_task")

        assert task is not None
        assert len(manager.tasks) == 1
        assert "test_task" in manager.task_names

        # Wait for completion
        await task
        assert task.done()

    @pytest.mark.anyio
    async def test_async_task_manager_exception_handler(self) -> None:
        """Bug #9: AsyncTaskManager should handle exceptions with callback."""
        manager = AsyncTaskManager()
        captured_exceptions: list[Exception] = []

        def exception_handler(task: asyncio.Task, exc: Exception) -> None:
            captured_exceptions.append(exc)

        manager.set_exception_handler(exception_handler)

        async def failing_task() -> None:
            await asyncio.sleep(0.01)
            raise ValueError("Test error")

        task = manager.create_task(failing_task(), name="failing_task")

        # Wait for task to complete (with exception)
        with pytest.raises(ValueError):
            await task

        # Give time for exception handler to be called
        await asyncio.sleep(0.05)

        # Exception should have been captured
        assert len(captured_exceptions) == 1
        assert isinstance(captured_exceptions[0], ValueError)
        assert "Test error" in str(captured_exceptions[0])

    @pytest.mark.anyio
    async def test_async_task_manager_wait_all(self) -> None:
        """Bug #9: AsyncTaskManager should support waiting for all tasks."""
        manager = AsyncTaskManager()
        results: list[str] = []

        async def task1() -> None:
            await asyncio.sleep(0.01)
            results.append("task1")

        async def task2() -> None:
            await asyncio.sleep(0.02)
            results.append("task2")

        manager.create_task(task1(), name="task1")
        manager.create_task(task2(), name="task2")

        await manager.wait_all()

        assert len(results) == 2
        assert "task1" in results
        assert "task2" in results

    @pytest.mark.anyio
    async def test_async_task_manager_cancel_all(self) -> None:
        """Bug #9: AsyncTaskManager should support cancelling all tasks."""
        manager = AsyncTaskManager()

        async def long_task() -> None:
            await asyncio.sleep(10)  # Long running task

        manager.create_task(long_task(), name="long_task1")
        manager.create_task(long_task(), name="long_task2")

        # Cancel all tasks
        cancelled_count = await manager.cancel_all()

        assert cancelled_count == 2
        assert all(task.cancelled() for task in manager.tasks)

    @pytest.mark.anyio
    async def test_async_task_manager_logging_on_exception(self) -> None:
        """Bug #9: Exceptions should be logged, not silently ignored."""

        manager = AsyncTaskManager()

        async def failing_task() -> None:
            raise RuntimeError("Fire-and-forget error")

        # Create task with exception
        task = manager.create_task(failing_task(), name="fire_and_forget")

        # Wait for task to complete
        with pytest.raises(RuntimeError):
            await task

        # The manager should have recorded the exception
        assert manager.has_exceptions
        assert len(manager.exceptions) == 1

    @pytest.mark.anyio
    async def test_async_task_manager_cleanup(self) -> None:
        """Bug #9: AsyncTaskManager should cleanup completed tasks."""
        manager = AsyncTaskManager()

        async def quick_task() -> str:
            return "done"

        task = manager.create_task(quick_task(), name="quick")
        await task

        # Cleanup completed tasks
        manager.cleanup_completed()

        assert len(manager.tasks) == 0


class TestProgressReporterAsyncTasks:
    """Test that JobStateProgressReporter properly manages async tasks."""

    @pytest.mark.anyio
    async def test_progress_reporter_uses_async_task_manager(self) -> None:
        """Bug #9: Progress reporter should use AsyncTaskManager."""
        # This test verifies integration between progress reporter and task manager
        # The actual implementation depends on JobStateProgressReporter internals

        # Create a mock job_state_manager
        from unittest.mock import AsyncMock, MagicMock

        mock_job_state_manager = MagicMock()
        mock_job_state_manager.update_progress_async = AsyncMock()
        mock_job_state_manager.update_phase_async = AsyncMock()

        reporter = JobStateProgressReporter(
            job_id="test-job",
            job_state_manager=mock_job_state_manager,
        )

        # Verify reporter has async task manager
        assert hasattr(reporter, "_async_task_manager") or hasattr(
            reporter, "async_task_manager"
        )
