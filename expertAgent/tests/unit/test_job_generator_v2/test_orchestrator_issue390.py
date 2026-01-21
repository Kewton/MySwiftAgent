"""Unit tests for Issue #390: TaskMaster workflow field update.

This module tests the _update_task_masters_workflow method in JobGenerationOrchestrator.
Issue #390: After Phase 3 (WORKFLOW_GEN) completes, TaskMasters need their
workflow field updated from '__PENDING__' to the actual workflow name.
"""

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Patch path for the function imported locally in _update_task_masters_workflow
PATCH_UPDATE_TASKFLOW = (
    "aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar"
    ".update_task_master_body_template_taskflow"
)


@dataclass
class MockTaskResult:
    """Mock task result for testing."""

    task_id: str
    workflow: dict[str, Any] | None = None


@dataclass
class MockParallelExecutionResult:
    """Mock parallel execution result for testing."""

    successful_tasks: list[MockTaskResult]
    failed_tasks: list[MockTaskResult]
    all_succeeded: bool = True


class TestUpdateTaskMastersWorkflow:
    """Test cases for _update_task_masters_workflow method.

    Issue #390: Tests for TaskMaster workflow field update after Phase 3.
    Issue #360: Tests must verify all-or-nothing behavior (no partial success).
    """

    @pytest.mark.asyncio
    async def test_update_task_masters_success(self):
        """Should update all TaskMasters successfully.

        When all TaskMasters update successfully, the method should:
        1. Call update_task_master_body_template_taskflow for each task
        2. Not raise any exception
        3. Log success message
        """
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )

        orchestrator = JobGenerationOrchestrator()

        # Mock successful tasks with workflow info
        workflow_result = MockParallelExecutionResult(
            successful_tasks=[
                MockTaskResult(
                    task_id="task_001",
                    workflow={
                        "task_master_id": "tm_001",
                        "workflow_name": "search_workflow",
                    },
                ),
                MockTaskResult(
                    task_id="task_002",
                    workflow={
                        "task_master_id": "tm_002",
                        "workflow_name": "process_workflow",
                    },
                ),
            ],
            failed_tasks=[],
            all_succeeded=True,
        )

        with patch(
            PATCH_UPDATE_TASKFLOW,
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_update:
            await orchestrator._update_task_masters_workflow(workflow_result)

            # Should have been called for each task
            assert mock_update.call_count == 2
            mock_update.assert_any_call(
                task_master_id="tm_001",
                workflow_name="search_workflow",
            )
            mock_update.assert_any_call(
                task_master_id="tm_002",
                workflow_name="process_workflow",
            )

    @pytest.mark.asyncio
    async def test_update_task_masters_no_successful_tasks(self):
        """Should handle empty successful_tasks gracefully.

        When there are no successful tasks, the method should:
        1. Not call update function
        2. Return early without error
        """
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )

        orchestrator = JobGenerationOrchestrator()

        workflow_result = MockParallelExecutionResult(
            successful_tasks=[],
            failed_tasks=[],
            all_succeeded=True,
        )

        with patch(
            PATCH_UPDATE_TASKFLOW,
            new_callable=AsyncMock,
        ) as mock_update:
            await orchestrator._update_task_masters_workflow(workflow_result)

            # Should not call update since no successful tasks
            mock_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_task_masters_no_workflow(self):
        """Should skip tasks without workflow info.

        When a task result has no workflow, the method should:
        1. Skip that task (not call update)
        2. Continue with other tasks
        3. Not raise any exception
        """
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )

        orchestrator = JobGenerationOrchestrator()

        workflow_result = MockParallelExecutionResult(
            successful_tasks=[
                MockTaskResult(
                    task_id="task_001",
                    workflow=None,  # No workflow
                ),
                MockTaskResult(
                    task_id="task_002",
                    workflow={
                        "task_master_id": "tm_002",
                        "workflow_name": "process_workflow",
                    },
                ),
            ],
            failed_tasks=[],
            all_succeeded=True,
        )

        with patch(
            PATCH_UPDATE_TASKFLOW,
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_update:
            await orchestrator._update_task_masters_workflow(workflow_result)

            # Should only call for task_002 (task_001 has no workflow)
            assert mock_update.call_count == 1
            mock_update.assert_called_once_with(
                task_master_id="tm_002",
                workflow_name="process_workflow",
            )

    @pytest.mark.asyncio
    async def test_update_task_masters_missing_task_master_id(self):
        """Should handle missing task_master_id as failure.

        Issue #360: When task_master_id is missing, it counts as a failure.
        """
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
            OrchestratorError,
        )

        orchestrator = JobGenerationOrchestrator()

        workflow_result = MockParallelExecutionResult(
            successful_tasks=[
                MockTaskResult(
                    task_id="task_001",
                    workflow={
                        # Missing task_master_id
                        "workflow_name": "search_workflow",
                    },
                ),
            ],
            failed_tasks=[],
            all_succeeded=True,
        )

        with patch(
            PATCH_UPDATE_TASKFLOW,
            new_callable=AsyncMock,
        ) as mock_update:
            # Should raise error due to missing task_master_id
            with pytest.raises(OrchestratorError) as exc_info:
                await orchestrator._update_task_masters_workflow(workflow_result)

            assert "task_001" in str(exc_info.value)
            mock_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_task_masters_missing_workflow_name(self):
        """Should handle missing workflow_name as failure.

        Issue #360: When workflow_name is missing, it counts as a failure.
        """
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
            OrchestratorError,
        )

        orchestrator = JobGenerationOrchestrator()

        workflow_result = MockParallelExecutionResult(
            successful_tasks=[
                MockTaskResult(
                    task_id="task_001",
                    workflow={
                        "task_master_id": "tm_001",
                        # Missing workflow_name
                    },
                ),
            ],
            failed_tasks=[],
            all_succeeded=True,
        )

        with patch(
            PATCH_UPDATE_TASKFLOW,
            new_callable=AsyncMock,
        ) as mock_update:
            # Should raise error due to missing workflow_name
            with pytest.raises(OrchestratorError) as exc_info:
                await orchestrator._update_task_masters_workflow(workflow_result)

            assert "task_001" in str(exc_info.value)
            mock_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_task_masters_partial_failure_raises_error(self):
        """Should raise error when any update fails.

        Issue #360: No partial success allowed. If any TaskMaster
        fails to update, the entire operation should fail.
        """
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
            OrchestratorError,
        )

        orchestrator = JobGenerationOrchestrator()

        workflow_result = MockParallelExecutionResult(
            successful_tasks=[
                MockTaskResult(
                    task_id="task_001",
                    workflow={
                        "task_master_id": "tm_001",
                        "workflow_name": "search_workflow",
                    },
                ),
                MockTaskResult(
                    task_id="task_002",
                    workflow={
                        "task_master_id": "tm_002",
                        "workflow_name": "process_workflow",
                    },
                ),
            ],
            failed_tasks=[],
            all_succeeded=True,
        )

        # First succeeds, second fails
        with patch(
            PATCH_UPDATE_TASKFLOW,
            new_callable=AsyncMock,
            side_effect=[True, False],
        ):
            # Should raise error because task_002 failed
            with pytest.raises(OrchestratorError) as exc_info:
                await orchestrator._update_task_masters_workflow(workflow_result)

            assert "task_002" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_task_masters_all_fail_raises_error(self):
        """Should raise error when all updates fail.

        Issue #360: When all updates fail, the error message should
        include all failed task IDs.
        """
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
            OrchestratorError,
        )

        orchestrator = JobGenerationOrchestrator()

        workflow_result = MockParallelExecutionResult(
            successful_tasks=[
                MockTaskResult(
                    task_id="task_001",
                    workflow={
                        "task_master_id": "tm_001",
                        "workflow_name": "search_workflow",
                    },
                ),
                MockTaskResult(
                    task_id="task_002",
                    workflow={
                        "task_master_id": "tm_002",
                        "workflow_name": "process_workflow",
                    },
                ),
            ],
            failed_tasks=[],
            all_succeeded=True,
        )

        # Both fail
        with patch(
            PATCH_UPDATE_TASKFLOW,
            new_callable=AsyncMock,
            return_value=False,
        ):
            with pytest.raises(OrchestratorError) as exc_info:
                await orchestrator._update_task_masters_workflow(workflow_result)

            # Both tasks should be mentioned in error
            assert "task_001" in str(exc_info.value)
            assert "task_002" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_task_masters_handles_exception(self):
        """Should handle exceptions during update.

        When update_task_master_body_template_taskflow raises an exception,
        it should be caught and reported as a failure.
        """
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
            OrchestratorError,
        )

        orchestrator = JobGenerationOrchestrator()

        workflow_result = MockParallelExecutionResult(
            successful_tasks=[
                MockTaskResult(
                    task_id="task_001",
                    workflow={
                        "task_master_id": "tm_001",
                        "workflow_name": "search_workflow",
                    },
                ),
            ],
            failed_tasks=[],
            all_succeeded=True,
        )

        with patch(
            PATCH_UPDATE_TASKFLOW,
            new_callable=AsyncMock,
            side_effect=Exception("Connection error"),
        ):
            with pytest.raises(OrchestratorError) as exc_info:
                await orchestrator._update_task_masters_workflow(workflow_result)

            # Error should be reported
            assert "unknown" in str(exc_info.value) or "Failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_task_masters_parallel_execution(self):
        """Should execute updates in parallel.

        The method should use asyncio.gather to execute all updates
        concurrently for better performance.
        """
        import asyncio

        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )

        orchestrator = JobGenerationOrchestrator()

        # Track call order to verify parallel execution
        call_times = []

        async def mock_update(*args, **kwargs):
            call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.01)  # Small delay
            return True

        workflow_result = MockParallelExecutionResult(
            successful_tasks=[
                MockTaskResult(
                    task_id=f"task_{i:03d}",
                    workflow={
                        "task_master_id": f"tm_{i:03d}",
                        "workflow_name": f"workflow_{i}",
                    },
                )
                for i in range(3)
            ],
            failed_tasks=[],
            all_succeeded=True,
        )

        with patch(
            PATCH_UPDATE_TASKFLOW,
            new_callable=AsyncMock,
            side_effect=mock_update,
        ):
            await orchestrator._update_task_masters_workflow(workflow_result)

            # All 3 calls should have been made
            assert len(call_times) == 3


class TestUpdateTaskMastersWorkflowIntegration:
    """Integration tests for _update_task_masters_workflow with workflow_registrar.

    These tests verify the integration between orchestrator and
    update_task_master_body_template_taskflow function.
    """

    @pytest.mark.asyncio
    async def test_workflow_registrar_uses_correct_field_name(self):
        """Should use 'workflow' field (not 'workflow_name') in body_template.

        Issue #390: mySwiftAgentCore expects 'workflow' field.
        The update_task_master_body_template_taskflow function should
        set body_template.workflow = workflow_name.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar import (
            update_task_master_body_template_taskflow,
        )

        # Mock JobqueueClient
        mock_client = MagicMock()
        mock_client.get_task_master = AsyncMock(
            return_value={
                "body_template": {
                    "workflow": "__PENDING__",
                    "inputs": "{{job.body}}",
                    "project": "{{job.body.project}}",  # Issue #391
                }
            }
        )
        mock_client.update_task_master = AsyncMock()

        with patch(
            "aiagent.langgraph.jobTaskGeneratorAgents.utils.jobqueue_client.JobqueueClient",
            return_value=mock_client,
        ):
            result = await update_task_master_body_template_taskflow(
                task_master_id="tm_001",
                workflow_name="search_workflow",
            )

            assert result is True

            # Verify the body_template uses 'workflow' field
            call_args = mock_client.update_task_master.call_args
            body_template = call_args.kwargs["body_template"]

            # Issue #390: Should use "workflow" not "workflow_name"
            assert "workflow" in body_template
            assert body_template["workflow"] == "search_workflow"
            assert "workflow_name" not in body_template

    @pytest.mark.asyncio
    async def test_workflow_registrar_preserves_existing_fields(self):
        """Should preserve existing inputs and project fields.

        Issue #390: The update should not overwrite existing inputs
        and project values (important for task chaining).
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar import (
            update_task_master_body_template_taskflow,
        )

        # Existing body_template with custom inputs (task chaining)
        existing_body_template = {
            "workflow": "__PENDING__",
            "inputs": "{{tasks[0].output_data}}",  # Task chaining
            "project": "custom_project",
            "job_params": "{{job.body}}",
        }

        mock_client = MagicMock()
        mock_client.get_task_master = AsyncMock(
            return_value={"body_template": existing_body_template}
        )
        mock_client.update_task_master = AsyncMock()

        with patch(
            "aiagent.langgraph.jobTaskGeneratorAgents.utils.jobqueue_client.JobqueueClient",
            return_value=mock_client,
        ):
            result = await update_task_master_body_template_taskflow(
                task_master_id="tm_002",
                workflow_name="process_workflow",
            )

            assert result is True

            call_args = mock_client.update_task_master.call_args
            body_template = call_args.kwargs["body_template"]

            # Should preserve existing inputs (task chaining)
            assert body_template["inputs"] == "{{tasks[0].output_data}}"
            # Should preserve existing project
            assert body_template["project"] == "custom_project"
            # Should update workflow
            assert body_template["workflow"] == "process_workflow"
