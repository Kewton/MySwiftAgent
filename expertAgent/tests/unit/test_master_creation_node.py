"""Unit tests for master_creation_node.

These tests verify the master creation node's behavior including:
- Successful TaskMaster and JobMaster creation
- JobMasterTask association creation (linking tasks to workflow)
- Error handling for missing data
- Edge cases (empty task breakdown, missing interface definitions)

Issue #111: Comprehensive test coverage for all workflow nodes.
"""

from unittest.mock import AsyncMock, patch

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation import (
    master_creation_node,
)
from tests.utils.mock_helpers import (
    create_mock_task_breakdown,
    create_mock_workflow_state,
)


@pytest.mark.unit
class TestMasterCreationNode:
    """Unit tests for master_creation_node."""

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.SchemaMatcher"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.JobqueueClient"
    )
    async def test_master_creation_success(
        self, mock_jobqueue_client, mock_schema_matcher
    ):
        """Test successful master creation with valid data.

        Priority: High
        This is the happy path test case.
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

        # Execute node
        result = await master_creation_node(state)

        # Verify JobMaster creation
        assert "job_master_id" in result
        assert result["job_master_id"] == "jm_001"

        # Verify TaskMaster IDs
        assert "task_master_ids" in result
        assert len(result["task_master_ids"]) == 2
        assert "tm_001" in result["task_master_ids"]
        assert "tm_002" in result["task_master_ids"]

        # Issue #305: Verify task_masters list for workflow_generation_node
        assert "task_masters" in result
        assert len(result["task_masters"]) == 2
        # Verify task_masters are sorted by order
        assert result["task_masters"][0]["order"] == 0
        assert result["task_masters"][1]["order"] == 1
        # Verify task_masters have required fields for workflow_generation_node
        for tm in result["task_masters"]:
            assert "id" in tm
            assert "name" in tm
            assert "order" in tm

        # Verify retry_count is reset to 0
        assert result["retry_count"] == 0

        # Verify JobqueueClient methods were called
        mock_client_instance.create_job_master.assert_called_once()
        assert mock_client_instance.add_task_to_workflow.call_count == 2

        # Verify SchemaMatcher was called for each task
        assert mock_matcher_instance.find_or_create_task_master.call_count == 2

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.SchemaMatcher"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.JobqueueClient"
    )
    async def test_master_creation_empty_task_breakdown(
        self, mock_jobqueue_client, mock_schema_matcher
    ):
        """Test error handling when task_breakdown is empty.

        Priority: Medium
        This tests edge case where no tasks are provided.
        """
        # Create test state with empty task_breakdown
        state = create_mock_workflow_state(
            user_requirement="Some requirement",
            task_breakdown=[],  # Empty
            interface_definitions={},
        )

        # Execute node
        result = await master_creation_node(state)

        # Verify error handling
        assert "error_message" in result
        assert (
            "Task breakdown is required for master creation" in result["error_message"]
        )

        # Verify JobqueueClient was NOT called (early return)
        mock_jobqueue_client.assert_not_called()
        mock_schema_matcher.assert_not_called()

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.SchemaMatcher"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.JobqueueClient"
    )
    async def test_master_creation_empty_interface_definitions(
        self, mock_jobqueue_client, mock_schema_matcher
    ):
        """Test error handling when interface_definitions is empty.

        Priority: Medium
        This tests validation of required interface definitions.
        """
        # Create test state with empty interface_definitions
        task_breakdown = create_mock_task_breakdown(2)
        state = create_mock_workflow_state(
            user_requirement="Some requirement",
            task_breakdown=task_breakdown,
            interface_definitions={},  # Empty
        )

        # Execute node
        result = await master_creation_node(state)

        # Verify error handling
        assert "error_message" in result
        assert (
            "Interface definitions are required for master creation"
            in result["error_message"]
        )

        # Verify JobqueueClient was NOT called (early return)
        mock_jobqueue_client.assert_not_called()
        mock_schema_matcher.assert_not_called()

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.SchemaMatcher"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.JobqueueClient"
    )
    async def test_master_creation_missing_interface_for_task(
        self, mock_jobqueue_client, mock_schema_matcher
    ):
        """Test error handling when interface definition is missing for a specific task.

        Priority: Medium
        This tests validation of interface definitions for each task.
        """
        # Setup mock JobqueueClient and SchemaMatcher (won't be called due to early return)
        mock_client_instance = AsyncMock()
        mock_jobqueue_client.return_value = mock_client_instance

        mock_matcher_instance = AsyncMock()
        mock_schema_matcher.return_value = mock_matcher_instance

        # Create test state with missing interface definition for task_2
        task_breakdown = create_mock_task_breakdown(2)
        interface_definitions = {
            "task_1": {
                "interface_master_id": "im_001",
                "interface_name": "gmail_search_interface",
            },
            # task_2 is missing!
        }
        state = create_mock_workflow_state(
            user_requirement="Some requirement",
            task_breakdown=task_breakdown,
            interface_definitions=interface_definitions,
        )

        # Execute node
        result = await master_creation_node(state)

        # Verify error handling
        assert "error_message" in result
        assert (
            "Interface definition not found for task task_2" in result["error_message"]
        )

        # Verify find_or_create_task_master was called once (for task_1) but not for task_2
        assert mock_matcher_instance.find_or_create_task_master.call_count == 1

        # Verify create_job_master was NOT called (error occurred before that step)
        mock_client_instance.create_job_master.assert_not_called()

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.SchemaMatcher"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.JobqueueClient"
    )
    async def test_master_creation_exception(
        self, mock_jobqueue_client, mock_schema_matcher
    ):
        """Test error handling when exception occurs during master creation.

        Priority: Medium
        This tests exception handling and error message propagation.
        """
        # Setup mock SchemaMatcher to raise exception
        mock_matcher_instance = AsyncMock()
        mock_matcher_instance.find_or_create_task_master = AsyncMock(
            side_effect=Exception("Database connection failed")
        )
        mock_schema_matcher.return_value = mock_matcher_instance

        mock_client_instance = AsyncMock()
        mock_jobqueue_client.return_value = mock_client_instance

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
            user_requirement="Some requirement",
            task_breakdown=task_breakdown,
            interface_definitions=interface_definitions,
        )

        # Execute node
        result = await master_creation_node(state)

        # Verify error handling
        assert "error_message" in result
        assert "Master creation failed" in result["error_message"]
        assert "Database connection failed" in result["error_message"]

        # job_master_id and task_master_ids should not be in result
        assert "job_master_id" not in result
        assert "task_master_ids" not in result

        # Verify SchemaMatcher was called
        mock_matcher_instance.find_or_create_task_master.assert_called_once()

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.SchemaMatcher"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.JobqueueClient"
    )
    async def test_master_creation_workflow_association(
        self, mock_jobqueue_client, mock_schema_matcher
    ):
        """Test JobMasterTask association creation.

        Priority: High
        This tests the critical step of linking tasks to the workflow.
        """
        # Setup mock JobqueueClient
        mock_client_instance = AsyncMock()
        mock_client_instance.create_job_master = AsyncMock(
            return_value={"id": "jm_001", "name": "Test Job"}
        )

        # Mock add_task_to_workflow to track calls
        workflow_associations = []

        async def mock_add_task(
            job_master_id, task_master_id, order, is_required, max_retries
        ):
            workflow_associations.append(
                {
                    "job_master_id": job_master_id,
                    "task_master_id": task_master_id,
                    "order": order,
                    "is_required": is_required,
                    "max_retries": max_retries,
                }
            )
            return {"id": f"jmt_{order:03d}", "order": order}

        mock_client_instance.add_task_to_workflow = AsyncMock(side_effect=mock_add_task)
        mock_jobqueue_client.return_value = mock_client_instance

        # Setup mock SchemaMatcher
        mock_matcher_instance = AsyncMock()
        mock_matcher_instance.find_or_create_task_master = AsyncMock(
            side_effect=[
                {"id": "tm_001", "name": "Task 1"},
                {"id": "tm_002", "name": "Task 2"},
                {"id": "tm_003", "name": "Task 3"},
            ]
        )
        mock_schema_matcher.return_value = mock_matcher_instance

        # Create test state with 3 tasks
        task_breakdown = create_mock_task_breakdown(3)
        interface_definitions = {
            "task_1": {"interface_master_id": "im_001"},
            "task_2": {"interface_master_id": "im_002"},
            "task_3": {"interface_master_id": "im_003"},
        }
        state = create_mock_workflow_state(
            user_requirement="Multi-task workflow",
            task_breakdown=task_breakdown,
            interface_definitions=interface_definitions,
        )

        # Execute node
        result = await master_creation_node(state)

        # Verify JobMasterTask associations were created
        assert len(workflow_associations) == 3

        # Verify each association has correct structure
        for i, assoc in enumerate(workflow_associations):
            assert assoc["job_master_id"] == "jm_001"
            assert assoc["task_master_id"] in ["tm_001", "tm_002", "tm_003"]
            assert assoc["order"] == i  # Order should be sequential
            assert assoc["is_required"] is True  # All tasks are required
            assert assoc["max_retries"] == 3  # Default max_retries

        # Verify add_task_to_workflow was called 3 times
        assert mock_client_instance.add_task_to_workflow.call_count == 3

        # Verify results
        assert result["job_master_id"] == "jm_001"
        assert len(result["task_master_ids"]) == 3
        assert result["retry_count"] == 0

        # Issue #305: Verify task_masters list for workflow_generation_node
        assert "task_masters" in result
        assert len(result["task_masters"]) == 3
        # Verify sorted by order
        for i, tm in enumerate(result["task_masters"]):
            assert tm["order"] == i
            assert "id" in tm
            assert "name" in tm

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.SchemaMatcher"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.JobqueueClient"
    )
    async def test_body_template_task_chaining_first_task(
        self, mock_jobqueue_client, mock_schema_matcher
    ):
        """Test that first task (order=0) receives {{job.body}} in body_template.

        Priority: High
        Issue: TaskMaster body_template task chaining implementation.
        """
        # Setup mock JobqueueClient
        mock_client_instance = AsyncMock()
        mock_client_instance.create_job_master = AsyncMock(
            return_value={"id": "jm_001", "name": "Test Job"}
        )
        mock_client_instance.add_task_to_workflow = AsyncMock(
            return_value={"id": "jmt_001", "order": 0}
        )
        mock_jobqueue_client.return_value = mock_client_instance

        # Track body_template passed to find_or_create_task_master
        captured_body_templates = []

        async def mock_find_or_create(*args, **kwargs):
            captured_body_templates.append(kwargs.get("body_template"))
            return {"id": "tm_001", "name": "Task 1"}

        mock_matcher_instance = AsyncMock()
        mock_matcher_instance.find_or_create_task_master = AsyncMock(
            side_effect=mock_find_or_create
        )
        mock_schema_matcher.return_value = mock_matcher_instance

        # Create test state with single task
        task_breakdown = create_mock_task_breakdown(1)
        interface_definitions = {
            "task_1": {
                "interface_master_id": "im_001",
                "interface_name": "search_interface",
            },
        }
        state = create_mock_workflow_state(
            user_requirement="Single task workflow",
            task_breakdown=task_breakdown,
            interface_definitions=interface_definitions,
        )

        # Execute node
        result = await master_creation_node(state)

        # Verify success
        assert "error_message" not in result
        assert result["job_master_id"] == "jm_001"

        # Verify first task body_template uses {{job.body}}
        assert len(captured_body_templates) == 1
        first_task_template = captured_body_templates[0]
        assert first_task_template is not None
        assert "user_input" in first_task_template
        assert first_task_template["user_input"] == "{{job.body}}"

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.SchemaMatcher"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.JobqueueClient"
    )
    async def test_body_template_task_chaining_subsequent_tasks(
        self, mock_jobqueue_client, mock_schema_matcher
    ):
        """Test that subsequent tasks (order>0) receive {{tasks[N-1].output_data}}.

        Priority: High
        Issue: TaskMaster body_template task chaining implementation.
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
                {"id": "jmt_003", "order": 2},
            ]
        )
        mock_jobqueue_client.return_value = mock_client_instance

        # Track body_template passed to find_or_create_task_master
        captured_body_templates = []

        async def mock_find_or_create(*args, **kwargs):
            captured_body_templates.append(kwargs.get("body_template"))
            task_idx = len(captured_body_templates)
            return {"id": f"tm_00{task_idx}", "name": f"Task {task_idx}"}

        mock_matcher_instance = AsyncMock()
        mock_matcher_instance.find_or_create_task_master = AsyncMock(
            side_effect=mock_find_or_create
        )
        mock_schema_matcher.return_value = mock_matcher_instance

        # Create test state with 3 tasks
        task_breakdown = create_mock_task_breakdown(3)
        interface_definitions = {
            "task_1": {"interface_master_id": "im_001"},
            "task_2": {"interface_master_id": "im_002"},
            "task_3": {"interface_master_id": "im_003"},
        }
        state = create_mock_workflow_state(
            user_requirement="Multi-task workflow",
            task_breakdown=task_breakdown,
            interface_definitions=interface_definitions,
        )

        # Execute node
        result = await master_creation_node(state)

        # Verify success
        assert "error_message" not in result
        assert result["job_master_id"] == "jm_001"

        # Verify body_template for each task
        assert len(captured_body_templates) == 3

        # Task 0 (first): should use {{job.body}}
        assert captured_body_templates[0]["user_input"] == "{{job.body}}"

        # Task 1 (second): should use {{tasks[0].output_data}}
        assert captured_body_templates[1]["user_input"] == "{{tasks[0].output_data}}"

        # Task 2 (third): should use {{tasks[1].output_data}}
        assert captured_body_templates[2]["user_input"] == "{{tasks[1].output_data}}"

    @pytest.mark.asyncio
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.SchemaMatcher"
    )
    @patch(
        "aiagent.langgraph.jobTaskGeneratorAgents.nodes.master_creation.JobqueueClient"
    )
    async def test_body_template_preserves_model_name_placeholder(
        self, mock_jobqueue_client, mock_schema_matcher
    ):
        """Test that body_template structure is preserved for model_name injection.

        Priority: Medium
        The workflow_tester sets model_name after workflow registration.
        """
        # Setup mocks
        mock_client_instance = AsyncMock()
        mock_client_instance.create_job_master = AsyncMock(
            return_value={"id": "jm_001", "name": "Test Job"}
        )
        mock_client_instance.add_task_to_workflow = AsyncMock(
            return_value={"id": "jmt_001", "order": 0}
        )
        mock_jobqueue_client.return_value = mock_client_instance

        captured_body_templates = []

        async def mock_find_or_create(*args, **kwargs):
            captured_body_templates.append(kwargs.get("body_template"))
            return {"id": "tm_001", "name": "Task 1"}

        mock_matcher_instance = AsyncMock()
        mock_matcher_instance.find_or_create_task_master = AsyncMock(
            side_effect=mock_find_or_create
        )
        mock_schema_matcher.return_value = mock_matcher_instance

        # Create test state
        task_breakdown = create_mock_task_breakdown(1)
        interface_definitions = {
            "task_1": {"interface_master_id": "im_001"},
        }
        state = create_mock_workflow_state(
            user_requirement="Test workflow",
            task_breakdown=task_breakdown,
            interface_definitions=interface_definitions,
        )

        # Execute node
        await master_creation_node(state)

        # Verify body_template has only user_input (model_name set later)
        assert len(captured_body_templates) == 1
        template = captured_body_templates[0]
        assert "user_input" in template
        # model_name should not be in the template (set by workflow_tester)
        assert "model_name" not in template or template.get("model_name") is None
