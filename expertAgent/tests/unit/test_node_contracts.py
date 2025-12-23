"""Node Contract Tests for Job Task Generator Workflow.

Issue #305: These tests verify the "contracts" between LangGraph nodes,
ensuring that the output of one node contains all fields required by
the next node in the workflow.

This prevents integration bugs that slip through isolated unit tests.

Contract verification strategy:
1. Define required fields for each node's input
2. Test that predecessor node's output contains those fields
3. Test the actual data flow between nodes
"""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation import (
    master_creation_node,
)
from aiagent.langgraph.jobTaskGeneratorAgents.nodes.workflow_generation import (
    workflow_generation_node,
)
from tests.utils.mock_helpers import (
    create_mock_task_breakdown,
    create_mock_workflow_state,
)

# ============================================================================
# Contract Definitions
# ============================================================================


class NodeContracts:
    """Define the contracts between nodes.

    Each contract specifies:
    - Required fields: Fields that MUST be present
    - Expected types: Type validation for fields
    - Expected structure: Structure validation for complex fields
    """

    @staticmethod
    def workflow_generation_node_requires() -> dict[str, Any]:
        """Fields required by workflow_generation_node.

        Based on workflow_generation.py:
        - task_masters: list[dict] with 'id' and 'name' keys
        - tracking_job_id: Optional[str] for progress tracking
        - task_breakdown: list[dict] for task info
        """
        return {
            "task_masters": {
                "type": list,
                "item_required_keys": ["id", "name"],
                "description": "List of TaskMaster dicts for workflow generation",
            },
            "task_breakdown": {
                "type": list,
                "optional": True,
                "description": "Task breakdown for saving to job state",
            },
            "tracking_job_id": {
                "type": (str, type(None)),
                "optional": True,
                "description": "Job ID for progress tracking",
            },
        }

    @staticmethod
    def job_registration_node_requires() -> dict[str, Any]:
        """Fields required by job_registration_node.

        Based on job_registration.py:
        - job_master_id: str
        - task_master_ids: list[str]
        """
        return {
            "job_master_id": {
                "type": str,
                "description": "JobMaster ID from master_creation",
            },
            "task_master_ids": {
                "type": list,
                "description": "List of TaskMaster IDs",
            },
        }


# ============================================================================
# Contract Test: master_creation_node → workflow_generation_node
# ============================================================================


@pytest.mark.unit
class TestMasterCreationToWorkflowGenerationContract:
    """Verify master_creation_node output satisfies workflow_generation_node input contract."""

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.SchemaMatcher"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.JobqueueClient"
    )
    async def test_master_creation_output_contains_task_masters(
        self, mock_jobqueue_client, mock_schema_matcher
    ):
        """Verify master_creation_node outputs task_masters for workflow_generation_node.

        Contract: master_creation_node MUST output 'task_masters' field that contains
        a list of dicts with 'id' and 'name' keys.

        This test ensures the bug fixed in Issue #305 does not regress.
        """
        # Setup mock JobqueueClient
        mock_client_instance = AsyncMock()
        mock_client_instance.create_job_master = AsyncMock(
            return_value={"id": "jm_001", "name": "Test Job"}
        )
        mock_client_instance.add_task_to_workflow = AsyncMock(
            side_effect=[
                {"id": "jmt_001", "order": 0},
                {"id": "jmt_002", "order": 1},
            ]
        )
        mock_jobqueue_client.return_value = mock_client_instance

        # Setup mock SchemaMatcher
        mock_matcher_instance = AsyncMock()
        mock_matcher_instance.find_or_create_task_master = AsyncMock(
            side_effect=[
                {"id": "tm_001", "name": "Task 1"},
                {"id": "tm_002", "name": "Task 2"},
            ]
        )
        mock_schema_matcher.return_value = mock_matcher_instance

        # Create test state
        task_breakdown = create_mock_task_breakdown(2)
        interface_definitions = {
            "task_1": {
                "interface_master_id": "im_001",
                "interface_name": "gmail_search_interface",
            },
            "task_2": {
                "interface_master_id": "im_002",
                "interface_name": "email_extract_interface",
            },
        }
        state = create_mock_workflow_state(
            user_requirement="Search Gmail and extract content",
            task_breakdown=task_breakdown,
            interface_definitions=interface_definitions,
        )

        # Execute master_creation_node
        result = await master_creation_node(state)

        # ===== CONTRACT VERIFICATION =====

        # 1. task_masters MUST be present
        assert "task_masters" in result, (
            "CONTRACT VIOLATION: master_creation_node must output 'task_masters' "
            "for workflow_generation_node"
        )

        # 2. task_masters MUST be a list
        assert isinstance(result["task_masters"], list), (
            f"CONTRACT VIOLATION: task_masters must be a list, "
            f"got {type(result['task_masters'])}"
        )

        # 3. task_masters MUST have correct count
        assert len(result["task_masters"]) == 2, (
            f"CONTRACT VIOLATION: task_masters should have 2 items, "
            f"got {len(result['task_masters'])}"
        )

        # 4. Each task_master MUST have 'id' and 'name' keys
        for i, tm in enumerate(result["task_masters"]):
            assert "id" in tm, (
                f"CONTRACT VIOLATION: task_masters[{i}] must have 'id' key"
            )
            assert "name" in tm, (
                f"CONTRACT VIOLATION: task_masters[{i}] must have 'name' key"
            )

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.SchemaMatcher"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.JobqueueClient"
    )
    async def test_master_creation_output_usable_by_workflow_generation(
        self, mock_jobqueue_client, mock_schema_matcher
    ):
        """Integration test: Pass master_creation output directly to workflow_generation.

        This test simulates the actual data flow between nodes to ensure
        they work together correctly.
        """
        # Setup mock JobqueueClient for master_creation
        mock_client_instance = AsyncMock()
        mock_client_instance.create_job_master = AsyncMock(
            return_value={"id": "jm_001", "name": "Test Job"}
        )
        mock_client_instance.add_task_to_workflow = AsyncMock(
            side_effect=[
                {"id": "jmt_001", "order": 0},
                {"id": "jmt_002", "order": 1},
            ]
        )
        mock_jobqueue_client.return_value = mock_client_instance

        # Setup mock SchemaMatcher
        mock_matcher_instance = AsyncMock()
        mock_matcher_instance.find_or_create_task_master = AsyncMock(
            side_effect=[
                {"id": "tm_001", "name": "Task 1"},
                {"id": "tm_002", "name": "Task 2"},
            ]
        )
        mock_schema_matcher.return_value = mock_matcher_instance

        # Create test state
        task_breakdown = create_mock_task_breakdown(2)
        interface_definitions = {
            "task_1": {
                "interface_master_id": "im_001",
                "interface_name": "gmail_search_interface",
            },
            "task_2": {
                "interface_master_id": "im_002",
                "interface_name": "email_extract_interface",
            },
        }
        initial_state = create_mock_workflow_state(
            user_requirement="Search Gmail and extract content",
            task_breakdown=task_breakdown,
            interface_definitions=interface_definitions,
        )

        # Step 1: Execute master_creation_node
        master_creation_result = await master_creation_node(initial_state)

        # Step 2: Pass result to workflow_generation_node
        # Mock the job_state_manager and generate_workflow_for_task
        mock_job_state_manager = AsyncMock()
        mock_job_state_manager.update_phase_async = AsyncMock()
        mock_job_state_manager.set_task_breakdown_async = AsyncMock()
        mock_job_state_manager.init_workflow_statuses_async = AsyncMock()
        mock_job_state_manager.update_workflow_status_async = AsyncMock()
        mock_job_state_manager.update_progress_async = AsyncMock()

        with patch(
            "aiagent.langgraph.jobTaskGeneratorAgents.nodes.workflow_generation.job_state_manager",
            mock_job_state_manager,
        ):
            with patch(
                "aiagent.langgraph.jobTaskGeneratorAgents.nodes.workflow_generation.generate_workflow_for_task"
            ) as mock_generate:
                mock_generate.return_value = {
                    "status": "success",
                    "workflow_name": "test_workflow",
                    "yaml_content": "version: 0.6",
                }

                # Execute workflow_generation_node with master_creation output
                workflow_result = await workflow_generation_node(master_creation_result)

        # ===== INTEGRATION VERIFICATION =====

        # 1. workflow_generation_node should have processed task_masters
        assert workflow_result["phase"] == "complete", (
            "workflow_generation_node should complete successfully"
        )

        # 2. workflow_results should have entries for each task_master
        assert len(workflow_result["workflow_results"]) == 2, (
            "Should have workflow results for each task_master"
        )

        # 3. Verify generate_workflow_for_task was called for each task_master
        assert mock_generate.call_count == 2, (
            "generate_workflow_for_task should be called for each task_master"
        )


# ============================================================================
# Contract Test: master_creation_node → job_registration_node
# ============================================================================


@pytest.mark.unit
class TestMasterCreationToJobRegistrationContract:
    """Verify master_creation_node output satisfies job_registration_node input contract."""

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.SchemaMatcher"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.JobqueueClient"
    )
    async def test_master_creation_output_contains_job_registration_fields(
        self, mock_jobqueue_client, mock_schema_matcher
    ):
        """Verify master_creation_node outputs fields required by job_registration_node.

        Contract: master_creation_node MUST output:
        - job_master_id: str
        - task_master_ids: list[str]
        """
        # Setup mock JobqueueClient
        mock_client_instance = AsyncMock()
        mock_client_instance.create_job_master = AsyncMock(
            return_value={"id": "jm_001", "name": "Test Job"}
        )
        mock_client_instance.add_task_to_workflow = AsyncMock(
            side_effect=[
                {"id": "jmt_001", "order": 0},
                {"id": "jmt_002", "order": 1},
            ]
        )
        mock_jobqueue_client.return_value = mock_client_instance

        # Setup mock SchemaMatcher
        mock_matcher_instance = AsyncMock()
        mock_matcher_instance.find_or_create_task_master = AsyncMock(
            side_effect=[
                {"id": "tm_001", "name": "Task 1"},
                {"id": "tm_002", "name": "Task 2"},
            ]
        )
        mock_schema_matcher.return_value = mock_matcher_instance

        # Create test state
        task_breakdown = create_mock_task_breakdown(2)
        interface_definitions = {
            "task_1": {"interface_master_id": "im_001"},
            "task_2": {"interface_master_id": "im_002"},
        }
        state = create_mock_workflow_state(
            user_requirement="Test workflow",
            task_breakdown=task_breakdown,
            interface_definitions=interface_definitions,
        )

        # Execute master_creation_node
        result = await master_creation_node(state)

        # ===== CONTRACT VERIFICATION =====

        # 1. job_master_id MUST be present
        assert "job_master_id" in result, (
            "CONTRACT VIOLATION: master_creation_node must output 'job_master_id' "
            "for job_registration_node"
        )
        assert isinstance(result["job_master_id"], str), (
            f"CONTRACT VIOLATION: job_master_id must be str, "
            f"got {type(result['job_master_id'])}"
        )

        # 2. task_master_ids MUST be present
        assert "task_master_ids" in result, (
            "CONTRACT VIOLATION: master_creation_node must output 'task_master_ids' "
            "for job_registration_node"
        )
        assert isinstance(result["task_master_ids"], list), (
            f"CONTRACT VIOLATION: task_master_ids must be list, "
            f"got {type(result['task_master_ids'])}"
        )

        # 3. task_master_ids should match task_masters count
        assert len(result["task_master_ids"]) == len(result["task_masters"]), (
            "CONTRACT VIOLATION: task_master_ids count should match task_masters count"
        )


# ============================================================================
# State Schema Validation Tests
# ============================================================================


@pytest.mark.unit
class TestJobTaskGeneratorStateSchema:
    """Verify JobTaskGeneratorState schema contains all required fields."""

    def test_state_schema_has_task_masters_field(self):
        """Verify JobTaskGeneratorState TypedDict includes task_masters."""
        from aiagent.langgraph.jobTaskGeneratorAgents.state import (
            JobTaskGeneratorState,
        )

        # Check TypedDict annotations
        annotations = JobTaskGeneratorState.__annotations__

        assert "task_masters" in annotations, (
            "SCHEMA VIOLATION: JobTaskGeneratorState must include 'task_masters' field"
        )
        # The type should be list[dict[str, Any]]
        task_masters_type = str(annotations["task_masters"])
        assert "list" in task_masters_type.lower(), (
            f"task_masters should be a list type, got {task_masters_type}"
        )

    def test_state_schema_has_workflow_results_field(self):
        """Verify JobTaskGeneratorState TypedDict includes workflow_results."""
        from aiagent.langgraph.jobTaskGeneratorAgents.state import (
            JobTaskGeneratorState,
        )

        annotations = JobTaskGeneratorState.__annotations__

        assert "workflow_results" in annotations, (
            "SCHEMA VIOLATION: JobTaskGeneratorState must include 'workflow_results' field"
        )

    def test_create_initial_state_includes_task_masters(self):
        """Verify create_initial_state includes task_masters with default value."""
        from aiagent.langgraph.jobTaskGeneratorAgents.state import (
            create_initial_state,
        )

        state = create_initial_state("Test requirement")

        assert "task_masters" in state, (
            "create_initial_state must include 'task_masters' field"
        )
        assert state["task_masters"] == [], (
            "task_masters default should be empty list"
        )
