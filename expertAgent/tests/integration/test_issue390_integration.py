"""Integration tests for Issue #390: TaskMaster workflow field update.

Tests the integration between JobGenerationOrchestrator and workflow_registrar
to ensure TaskMaster workflow fields are properly updated after Phase 3.

Run these tests with:
    cd expertAgent
    uv run pytest tests/integration/test_issue390_integration.py -v
"""

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


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

    def get_error_summary(self) -> str | None:
        """Return error summary for failed tasks."""
        if not self.failed_tasks:
            return None
        return f"Failed tasks: {[t.task_id for t in self.failed_tasks]}"


class TestIssue390OrchestratorIntegration:
    """Integration tests for Issue #390 orchestrator and workflow_registrar."""

    @pytest.mark.asyncio
    async def test_orchestrator_calls_update_after_workflow_gen(self):
        """Orchestrator should call _update_task_masters_workflow after Phase 3.

        This test verifies the integration flow:
        1. Phase 3 generates workflows
        2. Orchestrator calls _update_task_masters_workflow
        3. Each TaskMaster's body_template.workflow is updated
        """
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )

        orchestrator = JobGenerationOrchestrator()

        # Simulate Phase 3 result with successful workflow generation
        workflow_result = MockParallelExecutionResult(
            successful_tasks=[
                MockTaskResult(
                    task_id="task_001",
                    workflow={
                        "task_master_id": "tm_001",
                        "workflow_name": "google_search_workflow",
                    },
                ),
            ],
            failed_tasks=[],
            all_succeeded=True,
        )

        # Track what update_task_master_body_template_taskflow was called with
        update_calls = []

        async def mock_update(task_master_id: str, workflow_name: str) -> bool:
            update_calls.append({
                "task_master_id": task_master_id,
                "workflow_name": workflow_name,
            })
            return True

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar"
            ".update_task_master_body_template_taskflow",
            side_effect=mock_update,
        ):
            await orchestrator._update_task_masters_workflow(workflow_result)

        # Verify the update was called with correct parameters
        assert len(update_calls) == 1
        assert update_calls[0]["task_master_id"] == "tm_001"
        assert update_calls[0]["workflow_name"] == "google_search_workflow"

    @pytest.mark.asyncio
    async def test_workflow_registrar_builds_correct_body_template(self):
        """workflow_registrar should build body_template with 'workflow' field.

        Issue #390: mySwiftAgentCore expects 'workflow' field, not 'workflow_name'.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar import (
            update_task_master_body_template_taskflow,
        )

        # Mock existing TaskMaster with __PENDING__ workflow
        existing_task_master = {
            "body_template": {
                "workflow": "__PENDING__",
                "inputs": "{{job.body}}",
                "project": "{{job.body.project}}",
                "job_params": "{{job.body}}",
            }
        }

        captured_body_template = None

        async def capture_update(*args, **kwargs):
            nonlocal captured_body_template
            captured_body_template = kwargs.get("body_template")

        mock_client = MagicMock()
        mock_client.get_task_master = AsyncMock(return_value=existing_task_master)
        mock_client.update_task_master = AsyncMock(side_effect=capture_update)

        with patch(
            "aiagent.langgraph.jobTaskGeneratorAgents.utils.jobqueue_client.JobqueueClient",
            return_value=mock_client,
        ):
            result = await update_task_master_body_template_taskflow(
                task_master_id="tm_001",
                workflow_name="google_search_workflow",
            )

        assert result is True
        assert captured_body_template is not None

        # Issue #390: Verify correct field name and value
        assert "workflow" in captured_body_template
        assert captured_body_template["workflow"] == "google_search_workflow"
        assert "workflow_name" not in captured_body_template

        # Verify other fields are preserved
        assert captured_body_template["inputs"] == "{{job.body}}"
        assert captured_body_template["project"] == "{{job.body.project}}"  # Issue #391

    @pytest.mark.asyncio
    async def test_multiple_tasks_update_in_parallel(self):
        """Multiple TaskMasters should be updated in parallel.

        When Phase 3 generates workflows for multiple tasks,
        all TaskMasters should be updated concurrently.
        """
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )

        orchestrator = JobGenerationOrchestrator()

        # Multiple successful tasks
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
                MockTaskResult(
                    task_id="task_003",
                    workflow={
                        "task_master_id": "tm_003",
                        "workflow_name": "notify_workflow",
                    },
                ),
            ],
            failed_tasks=[],
            all_succeeded=True,
        )

        update_calls = []

        async def mock_update(task_master_id: str, workflow_name: str) -> bool:
            update_calls.append({
                "task_master_id": task_master_id,
                "workflow_name": workflow_name,
            })
            return True

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar"
            ".update_task_master_body_template_taskflow",
            side_effect=mock_update,
        ):
            await orchestrator._update_task_masters_workflow(workflow_result)

        # All 3 tasks should be updated
        assert len(update_calls) == 3
        task_master_ids = [call["task_master_id"] for call in update_calls]
        assert "tm_001" in task_master_ids
        assert "tm_002" in task_master_ids
        assert "tm_003" in task_master_ids

    @pytest.mark.asyncio
    async def test_task_chaining_inputs_preserved(self):
        """Task chaining inputs should be preserved during workflow update.

        Issue #390: When updating body_template.workflow, the existing
        inputs field (used for task chaining) must be preserved.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar import (
            update_task_master_body_template_taskflow,
        )

        # Task 2's body_template uses previous task's output (task chaining)
        existing_task_master = {
            "body_template": {
                "workflow": "__PENDING__",
                "inputs": "{{tasks[0].output_data}}",  # Task chaining!
                "project": "{{job.body.project}}",
                "job_params": "{{job.body}}",
            }
        }

        captured_body_template = None

        async def capture_update(*args, **kwargs):
            nonlocal captured_body_template
            captured_body_template = kwargs.get("body_template")

        mock_client = MagicMock()
        mock_client.get_task_master = AsyncMock(return_value=existing_task_master)
        mock_client.update_task_master = AsyncMock(side_effect=capture_update)

        with patch(
            "aiagent.langgraph.jobTaskGeneratorAgents.utils.jobqueue_client.JobqueueClient",
            return_value=mock_client,
        ):
            result = await update_task_master_body_template_taskflow(
                task_master_id="tm_002",
                workflow_name="process_workflow",
            )

        assert result is True

        # Task chaining input must be preserved
        assert captured_body_template["inputs"] == "{{tasks[0].output_data}}"
        # Workflow should be updated
        assert captured_body_template["workflow"] == "process_workflow"

    @pytest.mark.asyncio
    async def test_partial_failure_raises_orchestrator_error(self):
        """Partial failure should raise OrchestratorError.

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
        call_count = 0

        async def mock_update_with_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return call_count != 2  # Fail on second call

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar"
            ".update_task_master_body_template_taskflow",
            side_effect=mock_update_with_failure,
        ):
            with pytest.raises(OrchestratorError) as exc_info:
                await orchestrator._update_task_masters_workflow(workflow_result)

            # Error should mention the failed task
            assert "task_002" in str(exc_info.value)


class TestIssue390EndToEndFlow:
    """End-to-end flow tests for Issue #390."""

    @pytest.mark.asyncio
    async def test_pending_workflow_replaced_with_actual_name(self):
        """__PENDING__ workflow value should be replaced with actual workflow name.

        This is the core fix for Issue #390:
        Before: body_template.workflow = "__PENDING__"
        After:  body_template.workflow = "actual_workflow_name"
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar import (
            update_task_master_body_template_taskflow,
        )

        # Simulate initial state with __PENDING__
        initial_state = {
            "body_template": {
                "workflow": "__PENDING__",
                "inputs": "{{job.body}}",
                "project": "{{job.body.project}}",
            }
        }

        final_body_template = None

        async def capture_final_state(*args, **kwargs):
            nonlocal final_body_template
            final_body_template = kwargs.get("body_template")

        mock_client = MagicMock()
        mock_client.get_task_master = AsyncMock(return_value=initial_state)
        mock_client.update_task_master = AsyncMock(side_effect=capture_final_state)

        with patch(
            "aiagent.langgraph.jobTaskGeneratorAgents.utils.jobqueue_client.JobqueueClient",
            return_value=mock_client,
        ):
            await update_task_master_body_template_taskflow(
                task_master_id="tm_001",
                workflow_name="email_summary_workflow",
            )

        # Verify __PENDING__ is replaced
        assert final_body_template["workflow"] != "__PENDING__"
        assert final_body_template["workflow"] == "email_summary_workflow"

    @pytest.mark.asyncio
    async def test_job_execution_no_pending_error(self):
        """After Issue #390 fix, Job execution should not encounter __PENDING__ error.

        This test simulates what mySwiftAgentCore would receive and verifies
        the workflow field contains a valid workflow name, not __PENDING__.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.workflow_registrar import (
            update_task_master_body_template_taskflow,
        )

        # Initial state before Issue #390 fix
        initial_body_template = {
            "workflow": "__PENDING__",
            "inputs": "{{job.body}}",
            "project": "default_project",
        }

        final_state = None

        async def capture_state(*args, **kwargs):
            nonlocal final_state
            final_state = kwargs.get("body_template")

        mock_client = MagicMock()
        mock_client.get_task_master = AsyncMock(
            return_value={"body_template": initial_body_template}
        )
        mock_client.update_task_master = AsyncMock(side_effect=capture_state)

        with patch(
            "aiagent.langgraph.jobTaskGeneratorAgents.utils.jobqueue_client.JobqueueClient",
            return_value=mock_client,
        ):
            await update_task_master_body_template_taskflow(
                task_master_id="tm_test",
                workflow_name="valid_workflow_name",
            )

        # Simulate what mySwiftAgentCore receives
        simulated_workflow_name = final_state["workflow"]

        # This is what was causing the error before Issue #390 fix
        # mySwiftAgentCore tried to load "__PENDING__" as a workflow
        assert simulated_workflow_name != "__PENDING__", (
            "workflow should not be __PENDING__ - "
            "this would cause mySwiftAgentCore to fail"
        )
        assert simulated_workflow_name == "valid_workflow_name"
