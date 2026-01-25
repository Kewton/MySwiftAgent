"""Unit tests for Issue #390: TaskMaster workflow field update.

This module tests the _update_task_masters_workflow method in JobGenerationOrchestrator.
Issue #390: After Phase 3 (WORKFLOW_GEN) completes, TaskMasters need their
workflow field updated from '__PENDING__' to the actual workflow name.

Issue #396: Updated tests to match new implementation signature that accepts
BatchWorkflowGenerationResponse and list[UnifiedTaskIdentifier].
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiagent.clients.types.workflow_generator import (
    BatchStatus,
    BatchWorkflowGenerationResponse,
    WorkflowResult,
    WorkflowStatus,
)
from aiagent.langgraph.jobGeneratorV2.orchestrator import (
    JobGenerationOrchestrator,
    OrchestratorError,
)
from aiagent.langgraph.jobGeneratorV2.types import UnifiedTaskIdentifier

# Patch path for the function imported locally in _update_task_masters_workflow
PATCH_UPDATE_TASKFLOW = (
    "aiagent.langgraph.jobGeneratorV2.workflows.registration.task_master_utils"
    ".update_task_master_body_template_taskflow"
)


def create_mock_response(
    workflows: dict[str, WorkflowResult],
    status: BatchStatus = BatchStatus.SUCCESS,
) -> BatchWorkflowGenerationResponse:
    """Create a mock BatchWorkflowGenerationResponse for testing."""
    return BatchWorkflowGenerationResponse(
        status=status,
        success=(status != BatchStatus.FAILED),
        workflows=workflows,
        failed_tasks=None,
        recovery_suggestion=None,
        total_tasks=len(workflows),
        succeeded_tasks=sum(
            1 for w in workflows.values() if w.status == WorkflowStatus.SUCCESS
        ),
        failed_task_count=sum(
            1 for w in workflows.values() if w.status == WorkflowStatus.FAILED
        ),
    )


class TestUpdateTaskMastersWorkflow:
    """Test cases for _update_task_masters_workflow method.

    Issue #390: Tests for TaskMaster workflow field update after Phase 3.
    Issue #360: Tests must verify all-or-nothing behavior (no partial success).
    Issue #396: Tests updated to match new implementation signature.
    """

    @pytest.mark.asyncio
    async def test_update_task_masters_success(self):
        """Should update all TaskMasters successfully.

        When all TaskMasters update successfully, the method should:
        1. Call update_task_master_body_template_taskflow for each task
        2. Not raise any exception
        3. Log success message
        """
        orchestrator = JobGenerationOrchestrator()

        # Create mock response with successful workflows
        response = create_mock_response(
            workflows={
                "task_001": WorkflowResult(
                    workflow_name="search_workflow",
                    status=WorkflowStatus.SUCCESS,
                ),
                "task_002": WorkflowResult(
                    workflow_name="process_workflow",
                    status=WorkflowStatus.SUCCESS,
                ),
            }
        )

        # Create task identifiers with task_master_ids
        task_identifiers = [
            UnifiedTaskIdentifier(task_id="task_001", task_master_id="tm_001"),
            UnifiedTaskIdentifier(task_id="task_002", task_master_id="tm_002"),
        ]

        with patch(
            PATCH_UPDATE_TASKFLOW,
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_update:
            await orchestrator._update_task_masters_workflow(response, task_identifiers)

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
    async def test_update_task_masters_no_workflows(self):
        """Should handle empty workflows gracefully.

        When there are no workflows in the response, the method should:
        1. Not call update function
        2. Return early without error
        """
        orchestrator = JobGenerationOrchestrator()

        response = create_mock_response(workflows={})
        task_identifiers = [
            UnifiedTaskIdentifier(task_id="task_001", task_master_id="tm_001"),
        ]

        with patch(
            PATCH_UPDATE_TASKFLOW,
            new_callable=AsyncMock,
        ) as mock_update:
            await orchestrator._update_task_masters_workflow(response, task_identifiers)

            # Should not call update since no workflows
            mock_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_task_masters_no_task_identifiers(self):
        """Should handle empty task_identifiers gracefully.

        When there are no task identifiers, the method should:
        1. Not call update function
        2. Return early without error
        """
        orchestrator = JobGenerationOrchestrator()

        response = create_mock_response(
            workflows={
                "task_001": WorkflowResult(
                    workflow_name="search_workflow",
                    status=WorkflowStatus.SUCCESS,
                ),
            }
        )

        with patch(
            PATCH_UPDATE_TASKFLOW,
            new_callable=AsyncMock,
        ) as mock_update:
            await orchestrator._update_task_masters_workflow(response, [])

            # Should not call update since no task identifiers
            mock_update.assert_not_called()

    @pytest.mark.asyncio
    async def test_update_task_masters_skip_missing_task_master_id(self):
        """Should skip tasks without task_master_id.

        When a task identifier has no task_master_id, the method should:
        1. Skip that task (not call update)
        2. Continue with other tasks
        3. Not raise any exception
        """
        orchestrator = JobGenerationOrchestrator()

        response = create_mock_response(
            workflows={
                "task_001": WorkflowResult(
                    workflow_name="search_workflow",
                    status=WorkflowStatus.SUCCESS,
                ),
                "task_002": WorkflowResult(
                    workflow_name="process_workflow",
                    status=WorkflowStatus.SUCCESS,
                ),
            }
        )

        # First task has no task_master_id
        task_identifiers = [
            UnifiedTaskIdentifier(task_id="task_001", task_master_id=None),
            UnifiedTaskIdentifier(task_id="task_002", task_master_id="tm_002"),
        ]

        with patch(
            PATCH_UPDATE_TASKFLOW,
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_update:
            await orchestrator._update_task_masters_workflow(response, task_identifiers)

            # Should only call for task_002 (task_001 has no task_master_id)
            assert mock_update.call_count == 1
            mock_update.assert_called_once_with(
                task_master_id="tm_002",
                workflow_name="process_workflow",
            )

    @pytest.mark.asyncio
    async def test_update_task_masters_skip_missing_workflow(self):
        """Should skip tasks without workflow in response.

        When a task has no workflow in the response, the method should:
        1. Skip that task (not call update)
        2. Continue with other tasks
        """
        orchestrator = JobGenerationOrchestrator()

        # Only task_002 has a workflow
        response = create_mock_response(
            workflows={
                "task_002": WorkflowResult(
                    workflow_name="process_workflow",
                    status=WorkflowStatus.SUCCESS,
                ),
            }
        )

        task_identifiers = [
            UnifiedTaskIdentifier(task_id="task_001", task_master_id="tm_001"),
            UnifiedTaskIdentifier(task_id="task_002", task_master_id="tm_002"),
        ]

        with patch(
            PATCH_UPDATE_TASKFLOW,
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_update:
            await orchestrator._update_task_masters_workflow(response, task_identifiers)

            # Should only call for task_002 (task_001 has no workflow)
            assert mock_update.call_count == 1
            mock_update.assert_called_once_with(
                task_master_id="tm_002",
                workflow_name="process_workflow",
            )

    @pytest.mark.asyncio
    async def test_update_task_masters_skip_failed_workflows(self):
        """Should skip failed workflows.

        When a workflow has FAILED status, the method should:
        1. Skip that task (not call update)
        2. Continue with other tasks
        """
        orchestrator = JobGenerationOrchestrator()

        response = create_mock_response(
            workflows={
                "task_001": WorkflowResult(
                    workflow_name="search_workflow",
                    status=WorkflowStatus.FAILED,
                    error="Generation failed",
                ),
                "task_002": WorkflowResult(
                    workflow_name="process_workflow",
                    status=WorkflowStatus.SUCCESS,
                ),
            },
            status=BatchStatus.PARTIAL_SUCCESS,
        )

        task_identifiers = [
            UnifiedTaskIdentifier(task_id="task_001", task_master_id="tm_001"),
            UnifiedTaskIdentifier(task_id="task_002", task_master_id="tm_002"),
        ]

        with patch(
            PATCH_UPDATE_TASKFLOW,
            new_callable=AsyncMock,
            return_value=True,
        ) as mock_update:
            await orchestrator._update_task_masters_workflow(response, task_identifiers)

            # Should only call for task_002 (task_001 workflow failed)
            assert mock_update.call_count == 1
            mock_update.assert_called_once_with(
                task_master_id="tm_002",
                workflow_name="process_workflow",
            )

    @pytest.mark.asyncio
    async def test_update_task_masters_partial_failure_raises_error(self):
        """Should raise error when any update fails.

        Issue #360: No partial success allowed. If any TaskMaster
        fails to update, the entire operation should fail.
        """
        orchestrator = JobGenerationOrchestrator()

        response = create_mock_response(
            workflows={
                "task_001": WorkflowResult(
                    workflow_name="search_workflow",
                    status=WorkflowStatus.SUCCESS,
                ),
                "task_002": WorkflowResult(
                    workflow_name="process_workflow",
                    status=WorkflowStatus.SUCCESS,
                ),
            }
        )

        task_identifiers = [
            UnifiedTaskIdentifier(task_id="task_001", task_master_id="tm_001"),
            UnifiedTaskIdentifier(task_id="task_002", task_master_id="tm_002"),
        ]

        # First succeeds, second fails
        with patch(
            PATCH_UPDATE_TASKFLOW,
            new_callable=AsyncMock,
            side_effect=[True, False],
        ):
            # Should raise error because task_002 failed
            with pytest.raises(OrchestratorError) as exc_info:
                await orchestrator._update_task_masters_workflow(
                    response, task_identifiers
                )

            assert "tm_002" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_task_masters_all_fail_raises_error(self):
        """Should raise error when all updates fail.

        Issue #360: When all updates fail, the error message should
        include all failed task IDs.
        """
        orchestrator = JobGenerationOrchestrator()

        response = create_mock_response(
            workflows={
                "task_001": WorkflowResult(
                    workflow_name="search_workflow",
                    status=WorkflowStatus.SUCCESS,
                ),
                "task_002": WorkflowResult(
                    workflow_name="process_workflow",
                    status=WorkflowStatus.SUCCESS,
                ),
            }
        )

        task_identifiers = [
            UnifiedTaskIdentifier(task_id="task_001", task_master_id="tm_001"),
            UnifiedTaskIdentifier(task_id="task_002", task_master_id="tm_002"),
        ]

        # Both fail
        with patch(
            PATCH_UPDATE_TASKFLOW,
            new_callable=AsyncMock,
            return_value=False,
        ):
            with pytest.raises(OrchestratorError) as exc_info:
                await orchestrator._update_task_masters_workflow(
                    response, task_identifiers
                )

            # Both tasks should be mentioned in error
            assert "tm_001" in str(exc_info.value)
            assert "tm_002" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_update_task_masters_handles_exception(self):
        """Should handle exceptions during update.

        When update_task_master_body_template_taskflow raises an exception,
        it should be caught and reported as a failure.
        """
        orchestrator = JobGenerationOrchestrator()

        response = create_mock_response(
            workflows={
                "task_001": WorkflowResult(
                    workflow_name="search_workflow",
                    status=WorkflowStatus.SUCCESS,
                ),
            }
        )

        task_identifiers = [
            UnifiedTaskIdentifier(task_id="task_001", task_master_id="tm_001"),
        ]

        with patch(
            PATCH_UPDATE_TASKFLOW,
            new_callable=AsyncMock,
            side_effect=Exception("Connection error"),
        ):
            with pytest.raises(OrchestratorError) as exc_info:
                await orchestrator._update_task_masters_workflow(
                    response, task_identifiers
                )

            # Error should be reported
            assert "Connection error" in str(exc_info.value) or "tm_001" in str(
                exc_info.value
            )


class TestUpdateTaskMastersWorkflowIntegration:
    """Integration tests for _update_task_masters_workflow with task_master_utils.

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
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.task_master_utils import (
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
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.task_master_utils import (
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
