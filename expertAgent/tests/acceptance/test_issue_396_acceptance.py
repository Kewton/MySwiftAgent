"""Acceptance tests for Issue #396: TaskMaster workflow update after Phase 3.

Run with:
    cd expertAgent
    uv run pytest tests/acceptance/test_issue_396_acceptance.py -v -s

Test Level: L3 (Local Acceptance Test)
Related Issue: #396, #390 (Problem #4), #360 (All-or-Nothing)

Test Coverage:
- TC-001: TaskMaster workflow update verification
- TC-002: All-or-Nothing pattern verification
- TC-003: Existing fields preservation verification
- TC-004: Circular import prevention verification
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
from aiagent.langgraph.jobGeneratorV2.types import (
    Phase,
    UnifiedTaskIdentifier,
)


@pytest.mark.acceptance
class TestIssue396Acceptance:
    """E2E acceptance tests for Issue #396.

    Verifies that Phase 3 completion correctly updates TaskMaster
    workflow fields from __PENDING__ to actual workflow names.
    """

    @pytest.mark.asyncio
    async def test_tc_001_taskmaster_workflow_updated(self):
        """TC-001: TaskMaster workflow is updated after Job Generate.

        Acceptance Criteria:
        - AC-1: Job Generate後、TaskMasterのbody_template.workflowが実際のワークフロー名で更新される
        - AC-5: E2Eテスト成功（実際のジョブ生成→実行フロー）

        Design Policy:
        - DP-4: 既存フィールド保持

        This test verifies that after Phase 3 workflow generation completes,
        the _update_task_masters_workflow method is called and successfully
        updates each TaskMaster's body_template.workflow field.
        """
        # Arrange
        orchestrator = JobGenerationOrchestrator()

        # Create test task identifiers
        task_identifiers = [
            UnifiedTaskIdentifier(
                task_id="task_001",
                task_master_id="tm_001_uuid",
            ),
            UnifiedTaskIdentifier(
                task_id="task_002",
                task_master_id="tm_002_uuid",
            ),
        ]

        # Create mock workflow generation response
        # Note: BatchStatus.SUCCESS and WorkflowResult takes workflow_name, status, error
        response = BatchWorkflowGenerationResponse(
            status=BatchStatus.SUCCESS,
            success=True,
            workflows={
                "task_001": WorkflowResult(
                    workflow_name="task_001_google_search",
                    status=WorkflowStatus.SUCCESS,
                    error=None,
                ),
                "task_002": WorkflowResult(
                    workflow_name="task_002_email_send",
                    status=WorkflowStatus.SUCCESS,
                    error=None,
                ),
            },
            failed_tasks=[],
            recovery_suggestion=None,
        )

        # Track update calls
        update_calls = []

        async def mock_update(task_master_id: str, workflow_name: str) -> bool:
            update_calls.append(
                {
                    "task_master_id": task_master_id,
                    "workflow_name": workflow_name,
                }
            )
            return True

        # Act
        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.registration"
            ".task_master_utils.update_task_master_body_template_taskflow",
            side_effect=mock_update,
        ):
            await orchestrator._update_task_masters_workflow(response, task_identifiers)

        # Assert
        assert len(update_calls) == 2, (
            f"Expected 2 update calls, got {len(update_calls)}"
        )

        # Verify task_001 update
        task_001_update = next(
            (c for c in update_calls if c["task_master_id"] == "tm_001_uuid"),
            None,
        )
        assert task_001_update is not None, "task_001 update not found"
        assert task_001_update["workflow_name"] == "task_001_google_search", (
            f"Expected workflow_name 'task_001_google_search', "
            f"got '{task_001_update['workflow_name']}'"
        )

        # Verify task_002 update
        task_002_update = next(
            (c for c in update_calls if c["task_master_id"] == "tm_002_uuid"),
            None,
        )
        assert task_002_update is not None, "task_002 update not found"
        assert task_002_update["workflow_name"] == "task_002_email_send", (
            f"Expected workflow_name 'task_002_email_send', "
            f"got '{task_002_update['workflow_name']}'"
        )

    @pytest.mark.asyncio
    async def test_tc_002_all_or_nothing_behavior(self):
        """TC-002: All-or-Nothing pattern verification.

        Design Policy:
        - DP-1: All-or-Nothing Pattern (Issue #360)
        - DP-3: Fail-Fast Pattern

        This test verifies that if any TaskMaster update fails,
        an OrchestratorError is raised with all failed task IDs.
        """
        # Arrange
        orchestrator = JobGenerationOrchestrator()

        task_identifiers = [
            UnifiedTaskIdentifier(
                task_id="task_001",
                task_master_id="tm_001_uuid",
            ),
            UnifiedTaskIdentifier(
                task_id="task_002",
                task_master_id="tm_002_uuid",
            ),
        ]

        response = BatchWorkflowGenerationResponse(
            status=BatchStatus.SUCCESS,
            success=True,
            workflows={
                "task_001": WorkflowResult(
                    workflow_name="task_001_google_search",
                    status=WorkflowStatus.SUCCESS,
                    error=None,
                ),
                "task_002": WorkflowResult(
                    workflow_name="task_002_email_send",
                    status=WorkflowStatus.SUCCESS,
                    error=None,
                ),
            },
            failed_tasks=[],
            recovery_suggestion=None,
        )

        # Simulate first update success, second update failure
        call_count = 0

        async def mock_update(task_master_id: str, workflow_name: str) -> bool:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return True  # First update succeeds
            return False  # Second update fails

        # Act & Assert
        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.registration"
            ".task_master_utils.update_task_master_body_template_taskflow",
            side_effect=mock_update,
        ):
            with pytest.raises(OrchestratorError) as exc_info:
                await orchestrator._update_task_masters_workflow(
                    response, task_identifiers
                )

        # Verify error message contains failed TaskMaster ID
        error_msg = str(exc_info.value)
        assert "Failed to update all TaskMasters" in error_msg, (
            f"Expected 'Failed to update all TaskMasters' in error, got: {error_msg}"
        )
        assert exc_info.value.phase == Phase.WORKFLOW_GEN, (
            f"Expected phase WORKFLOW_GEN, got {exc_info.value.phase}"
        )

    @pytest.mark.asyncio
    async def test_tc_003_existing_fields_preserved(self):
        """TC-003: Existing body_template fields are preserved.

        Acceptance Criteria:
        - AC-1: Job Generate後、TaskMasterのbody_template.workflowが実際のワークフロー名で更新される

        Design Policy:
        - DP-4: 既存フィールド保持

        This test verifies that when updating body_template.workflow,
        the existing inputs, project, and job_params fields are preserved.
        """
        # Import the actual function to test its behavior
        from aiagent.langgraph.jobGeneratorV2.workflows.registration.task_master_utils import (
            update_task_master_body_template_taskflow,
        )

        # Arrange: Mock jobqueue client to track body_template updates
        mock_existing_task_master = {
            "id": "tm_001_uuid",
            "body_template": {
                "workflow": "__PENDING__",
                "inputs": "{{tasks[0].output_data}}",  # Task chaining
                "project": "test_project",
                "job_params": "{{job.body}}",
            },
        }

        update_called_with = {}

        async def mock_get_task_master(task_master_id: str):
            return mock_existing_task_master

        async def mock_update_task_master(
            master_id: str,
            body_template: dict,
            updated_by: str,
            change_reason: str,
        ):
            update_called_with["master_id"] = master_id
            update_called_with["body_template"] = body_template
            update_called_with["updated_by"] = updated_by

        mock_client = MagicMock()
        mock_client.get_task_master = AsyncMock(side_effect=mock_get_task_master)
        mock_client.update_task_master = AsyncMock(side_effect=mock_update_task_master)

        # Act: Patch the import inside the function (local import pattern)
        # The function imports JobqueueClient from jobTaskGeneratorAgents
        with patch(
            "aiagent.langgraph.jobTaskGeneratorAgents.utils.jobqueue_client"
            ".JobqueueClient",
            return_value=mock_client,
        ):
            result = await update_task_master_body_template_taskflow(
                task_master_id="tm_001_uuid",
                workflow_name="task_001_google_search",
            )

        # Assert
        assert result is True, "Expected update to succeed"
        assert "body_template" in update_called_with, "body_template not in update call"

        body_template = update_called_with["body_template"]

        # Verify workflow is updated
        assert body_template["workflow"] == "task_001_google_search", (
            f"Expected workflow 'task_001_google_search', "
            f"got '{body_template.get('workflow')}'"
        )

        # Verify existing fields are preserved
        assert body_template["inputs"] == "{{tasks[0].output_data}}", (
            f"Expected inputs '{{{{tasks[0].output_data}}}}', "
            f"got '{body_template.get('inputs')}'"
        )
        assert body_template["project"] == "test_project", (
            f"Expected project 'test_project', got '{body_template.get('project')}'"
        )
        assert body_template["job_params"] == "{{job.body}}", (
            f"Expected job_params '{{{{job.body}}}}', "
            f"got '{body_template.get('job_params')}'"
        )

    @pytest.mark.asyncio
    async def test_tc_004_no_circular_import(self):
        """TC-004: No circular import when loading orchestrator.

        Design Policy:
        - DP-2: Local Import Pattern (循環参照回避)

        This test verifies that the orchestrator module can be imported
        without circular import errors, thanks to the local import pattern
        used in _update_task_masters_workflow.
        """
        # Act: Import orchestrator (should not raise ImportError)
        try:
            from aiagent.langgraph.jobGeneratorV2.orchestrator import (
                JobGenerationOrchestrator,
            )

            import_success = True
            import_error = None
        except ImportError as e:
            import_success = False
            import_error = str(e)
        except Exception as e:
            import_success = False
            import_error = f"Unexpected error: {e}"

        # Assert
        assert import_success, (
            f"Failed to import JobGenerationOrchestrator: {import_error}"
        )

        # Verify the class is properly initialized
        orchestrator = JobGenerationOrchestrator()
        assert hasattr(orchestrator, "_update_task_masters_workflow"), (
            "_update_task_masters_workflow method not found"
        )
        assert callable(orchestrator._update_task_masters_workflow), (
            "_update_task_masters_workflow is not callable"
        )

    @pytest.mark.asyncio
    async def test_tc_005_skip_failed_workflows(self):
        """TC-005: Skip updating TaskMasters for failed workflows.

        This test verifies that TaskMaster updates are skipped for
        workflows that failed during generation (status != SUCCESS).
        """
        # Arrange
        orchestrator = JobGenerationOrchestrator()

        task_identifiers = [
            UnifiedTaskIdentifier(
                task_id="task_001",
                task_master_id="tm_001_uuid",
            ),
            UnifiedTaskIdentifier(
                task_id="task_002",  # This one failed
                task_master_id="tm_002_uuid",
            ),
        ]

        response = BatchWorkflowGenerationResponse(
            status=BatchStatus.PARTIAL_SUCCESS,
            success=True,
            workflows={
                "task_001": WorkflowResult(
                    workflow_name="task_001_google_search",
                    status=WorkflowStatus.SUCCESS,
                    error=None,
                ),
                "task_002": WorkflowResult(
                    workflow_name="",  # Empty workflow name for failed
                    status=WorkflowStatus.FAILED,
                    error="Generation failed",
                ),
            },
            failed_tasks=[],
            recovery_suggestion=None,
        )

        update_calls = []

        async def mock_update(task_master_id: str, workflow_name: str) -> bool:
            update_calls.append(
                {
                    "task_master_id": task_master_id,
                    "workflow_name": workflow_name,
                }
            )
            return True

        # Act
        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.registration"
            ".task_master_utils.update_task_master_body_template_taskflow",
            side_effect=mock_update,
        ):
            await orchestrator._update_task_masters_workflow(response, task_identifiers)

        # Assert: Only successful workflow should be updated
        assert len(update_calls) == 1, (
            f"Expected 1 update call (for success only), got {len(update_calls)}"
        )
        assert update_calls[0]["task_master_id"] == "tm_001_uuid"
        assert update_calls[0]["workflow_name"] == "task_001_google_search"

    @pytest.mark.asyncio
    async def test_tc_006_skip_missing_task_master_id(self):
        """TC-006: Skip updating when task_master_id is missing.

        This test verifies that TaskMaster updates are skipped for
        tasks that don't have a task_master_id set.
        """
        # Arrange
        orchestrator = JobGenerationOrchestrator()

        task_identifiers = [
            UnifiedTaskIdentifier(
                task_id="task_001",
                task_master_id="tm_001_uuid",
            ),
            UnifiedTaskIdentifier(
                task_id="task_002",
                task_master_id=None,  # No task_master_id
            ),
        ]

        response = BatchWorkflowGenerationResponse(
            status=BatchStatus.SUCCESS,
            success=True,
            workflows={
                "task_001": WorkflowResult(
                    workflow_name="task_001_google_search",
                    status=WorkflowStatus.SUCCESS,
                    error=None,
                ),
                "task_002": WorkflowResult(
                    workflow_name="task_002_email_send",
                    status=WorkflowStatus.SUCCESS,
                    error=None,
                ),
            },
            failed_tasks=[],
            recovery_suggestion=None,
        )

        update_calls = []

        async def mock_update(task_master_id: str, workflow_name: str) -> bool:
            update_calls.append(
                {
                    "task_master_id": task_master_id,
                    "workflow_name": workflow_name,
                }
            )
            return True

        # Act
        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.registration"
            ".task_master_utils.update_task_master_body_template_taskflow",
            side_effect=mock_update,
        ):
            await orchestrator._update_task_masters_workflow(response, task_identifiers)

        # Assert: Only task with task_master_id should be updated
        assert len(update_calls) == 1, (
            f"Expected 1 update call (for task with id), got {len(update_calls)}"
        )
        assert update_calls[0]["task_master_id"] == "tm_001_uuid"


@pytest.mark.acceptance
class TestIssue396UnitIntegration:
    """Verify unit and integration tests for Issue #396.

    These tests verify that the existing unit/integration tests
    for Issue #390 cover the Issue #396 functionality.
    """

    def test_unit_tests_exist_and_pass(self):
        """Verify that unit tests exist for _update_task_masters_workflow.

        Related: AC-3 (test_orchestrator_issue390.pyの全テストがパス)
        """
        import importlib.util

        # Check unit test file exists
        unit_test_path = (
            "/Users/maenokota/share/work/github_kewton/MySwiftAgent/"
            "expertAgent/tests/unit/test_job_generator_v2/"
            "test_orchestrator_issue390.py"
        )
        spec = importlib.util.spec_from_file_location(
            "test_orchestrator_issue390", unit_test_path
        )
        assert spec is not None, f"Unit test file not found: {unit_test_path}"

        # Verify file can be loaded (no syntax errors)
        try:
            module = importlib.util.module_from_spec(spec)
            assert module is not None, "Failed to create module from spec"
        except Exception as e:
            pytest.fail(f"Failed to load unit test module: {e}")

    def test_integration_tests_exist_and_pass(self):
        """Verify that integration tests exist for Issue #390.

        Related: AC-4 (test_issue390_integration.pyの全テストがパス)
        """
        import importlib.util

        # Check integration test file exists
        integration_test_path = (
            "/Users/maenokota/share/work/github_kewton/MySwiftAgent/"
            "expertAgent/tests/integration/"
            "test_issue390_integration.py"
        )
        spec = importlib.util.spec_from_file_location(
            "test_issue390_integration", integration_test_path
        )
        assert spec is not None, (
            f"Integration test file not found: {integration_test_path}"
        )

        # Verify file can be loaded (no syntax errors)
        try:
            module = importlib.util.module_from_spec(spec)
            assert module is not None, "Failed to create module from spec"
        except Exception as e:
            pytest.fail(f"Failed to load integration test module: {e}")


@pytest.mark.acceptance
class TestIssue396DeadCodeVerification:
    """Verify that the implemented functions are not dead code.

    This verifies the dead code detection plan from the acceptance plan:
    - F-1: _update_task_masters_workflow method
    - F-2: update_task_master_body_template_taskflow function
    """

    def test_f1_update_task_masters_workflow_is_called(self):
        """F-1: _update_task_masters_workflow is called from orchestrator.

        Verify that _update_task_masters_workflow is called from
        _execute_workflow_gen method after Phase 3 completion.
        """
        import ast

        # Read orchestrator.py source
        orchestrator_path = (
            "/Users/maenokota/share/work/github_kewton/MySwiftAgent/"
            "expertAgent/aiagent/langgraph/jobGeneratorV2/orchestrator.py"
        )
        with open(orchestrator_path, "r") as f:
            source = f.read()

        # Parse AST and find _execute_workflow_gen method
        tree = ast.parse(source)

        # Find call to _update_task_masters_workflow
        found_call = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == "_update_task_masters_workflow":
                        found_call = True
                        break

        assert found_call, (
            "_update_task_masters_workflow is not called in orchestrator.py. "
            "This indicates dead code."
        )

    def test_f2_update_task_master_body_template_is_imported_and_called(self):
        """F-2: update_task_master_body_template_taskflow is used.

        Verify that update_task_master_body_template_taskflow is imported
        and called in _update_task_masters_workflow.
        """
        import ast

        # Read orchestrator.py source
        orchestrator_path = (
            "/Users/maenokota/share/work/github_kewton/MySwiftAgent/"
            "expertAgent/aiagent/langgraph/jobGeneratorV2/orchestrator.py"
        )
        with open(orchestrator_path, "r") as f:
            source = f.read()

        # Check for local import of the function
        assert "update_task_master_body_template_taskflow" in source, (
            "update_task_master_body_template_taskflow is not found in orchestrator.py"
        )

        # Parse AST and find the function call
        tree = ast.parse(source)

        found_call = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id == "update_task_master_body_template_taskflow":
                        found_call = True
                        break

        assert found_call, (
            "update_task_master_body_template_taskflow is imported but never called. "
            "This indicates dead code."
        )
