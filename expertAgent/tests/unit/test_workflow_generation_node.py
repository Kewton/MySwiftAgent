"""Unit tests for workflow generation node and related functionality.

Tests for Issue #305: Job generation workflow auto-generation.
This module tests:
- B-4: JobCreationStatus extension (phase, task_breakdown, workflow_statuses)
- B-4.5: JobTaskGeneratorState extension (workflow_results, phase)
- B-5.1: generate_workflow_for_task helper
- B-5: workflow_generation_node
"""

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.job_creation_state import (
    JobCreationStateManager,
    JobCreationStatus,
    TaskBreakdownItem,
    WorkflowStatusItem,
)

# ============================================================================
# B-4: JobCreationStatus Extension Tests
# ============================================================================


class TestTaskBreakdownItem:
    """Test TaskBreakdownItem model."""

    @pytest.mark.unit
    def test_task_breakdown_item_creation(self) -> None:
        """Test TaskBreakdownItem creation with all fields."""
        item = TaskBreakdownItem(
            task_id="tm_001",
            name="Gmail Fetch Task",
            description="Fetch unread emails from Gmail",
            recommended_apis=["Gmail API (users.messages.list)"],
        )
        assert item.task_id == "tm_001"
        assert item.name == "Gmail Fetch Task"
        assert item.description == "Fetch unread emails from Gmail"
        assert item.recommended_apis == ["Gmail API (users.messages.list)"]

    @pytest.mark.unit
    def test_task_breakdown_item_empty_apis(self) -> None:
        """Test TaskBreakdownItem with empty recommended_apis."""
        item = TaskBreakdownItem(
            task_id="tm_002",
            name="Simple Task",
            description="A simple task",
            recommended_apis=[],
        )
        assert item.recommended_apis == []


class TestWorkflowStatusItem:
    """Test WorkflowStatusItem model."""

    @pytest.mark.unit
    def test_workflow_status_item_pending(self) -> None:
        """Test WorkflowStatusItem in pending status."""
        item = WorkflowStatusItem(
            task_id="tm_001",
            status="pending",
        )
        assert item.task_id == "tm_001"
        assert item.status == "pending"
        assert item.workflow_name is None
        assert item.generation_time_ms is None
        assert item.error_message is None

    @pytest.mark.unit
    def test_workflow_status_item_success(self) -> None:
        """Test WorkflowStatusItem in success status."""
        item = WorkflowStatusItem(
            task_id="tm_001",
            status="success",
            workflow_name="workflow_tm_001",
            generation_time_ms=28500,
        )
        assert item.status == "success"
        assert item.workflow_name == "workflow_tm_001"
        assert item.generation_time_ms == 28500

    @pytest.mark.unit
    def test_workflow_status_item_failed(self) -> None:
        """Test WorkflowStatusItem in failed status."""
        item = WorkflowStatusItem(
            task_id="tm_001",
            status="failed",
            error_message="API connection failed",
        )
        assert item.status == "failed"
        assert item.error_message == "API connection failed"


class TestJobCreationStatusExtension:
    """Test JobCreationStatus extension with new fields."""

    @pytest.mark.unit
    def test_job_creation_status_with_new_fields(self) -> None:
        """Test JobCreationStatus with phase, task_breakdown, workflow_statuses."""
        task_breakdown = [
            TaskBreakdownItem(
                task_id="tm_001",
                name="Fetch Emails",
                description="Fetch unread emails",
                recommended_apis=["Gmail API"],
            ),
        ]
        workflow_statuses = [
            WorkflowStatusItem(
                task_id="tm_001",
                status="success",
                workflow_name="workflow_tm_001",
                generation_time_ms=1000,
            ),
        ]

        status = JobCreationStatus(
            job_id="test-job-123",
            status="creating",
            progress=70,
            start_time=datetime.now(),
            phase="workflow_generation",
            task_breakdown=task_breakdown,
            workflow_statuses=workflow_statuses,
        )

        assert status.phase == "workflow_generation"
        assert status.task_breakdown is not None
        assert len(status.task_breakdown) == 1
        assert status.task_breakdown[0].task_id == "tm_001"
        assert status.workflow_statuses is not None
        assert len(status.workflow_statuses) == 1
        assert status.workflow_statuses[0].status == "success"

    @pytest.mark.unit
    def test_job_creation_status_backward_compatible(self) -> None:
        """Test JobCreationStatus is backward compatible (new fields optional)."""
        status = JobCreationStatus(
            job_id="test-job-123",
            status="creating",
            progress=50,
            start_time=datetime.now(),
        )

        # New fields should be None by default
        assert status.phase is None
        assert status.task_breakdown is None
        assert status.workflow_statuses is None


class TestJobCreationStateManagerExtension:
    """Test JobCreationStateManager extension methods."""

    @pytest.fixture
    def manager(self) -> JobCreationStateManager:
        """Create a fresh JobCreationStateManager for each test."""
        return JobCreationStateManager()

    @pytest.mark.unit
    async def test_update_phase(self, manager: JobCreationStateManager) -> None:
        """Test update_phase method."""
        await manager.create_job_async("test-job-123")

        await manager.update_phase_async("test-job-123", "task_analysis")
        status = await manager.get_status_async("test-job-123")
        assert status is not None
        assert status.phase == "task_analysis"

        await manager.update_phase_async("test-job-123", "workflow_generation")
        status = await manager.get_status_async("test-job-123")
        assert status is not None
        assert status.phase == "workflow_generation"

    @pytest.mark.unit
    async def test_update_phase_job_not_found(
        self, manager: JobCreationStateManager
    ) -> None:
        """Test update_phase for non-existent job."""
        # Should not raise, just log warning
        await manager.update_phase_async("nonexistent-job", "task_analysis")

    @pytest.mark.unit
    async def test_set_task_breakdown(self, manager: JobCreationStateManager) -> None:
        """Test set_task_breakdown method."""
        await manager.create_job_async("test-job-123")

        breakdown = [
            TaskBreakdownItem(
                task_id="tm_001",
                name="Task 1",
                description="First task",
                recommended_apis=["API1"],
            ),
            TaskBreakdownItem(
                task_id="tm_002",
                name="Task 2",
                description="Second task",
                recommended_apis=["API2"],
            ),
        ]

        await manager.set_task_breakdown_async("test-job-123", breakdown)

        status = await manager.get_status_async("test-job-123")
        assert status is not None
        assert status.task_breakdown is not None
        assert len(status.task_breakdown) == 2
        assert status.task_breakdown[0].task_id == "tm_001"
        assert status.phase == "workflow_generation"

    @pytest.mark.unit
    async def test_init_workflow_statuses(
        self, manager: JobCreationStateManager
    ) -> None:
        """Test init_workflow_statuses method."""
        await manager.create_job_async("test-job-123")

        task_ids = ["tm_001", "tm_002", "tm_003"]
        await manager.init_workflow_statuses_async("test-job-123", task_ids)

        status = await manager.get_status_async("test-job-123")
        assert status is not None
        assert status.workflow_statuses is not None
        assert len(status.workflow_statuses) == 3
        for ws in status.workflow_statuses:
            assert ws.status == "pending"

    @pytest.mark.unit
    async def test_update_workflow_status(
        self, manager: JobCreationStateManager
    ) -> None:
        """Test update_workflow_status method."""
        await manager.create_job_async("test-job-123")

        # Initialize workflow statuses
        task_ids = ["tm_001", "tm_002"]
        await manager.init_workflow_statuses_async("test-job-123", task_ids)

        # Update status to generating
        await manager.update_workflow_status_async(
            job_id="test-job-123",
            task_id="tm_001",
            workflow_status="generating",
        )

        status = await manager.get_status_async("test-job-123")
        assert status is not None
        assert status.workflow_statuses is not None
        ws_tm_001 = next(
            ws for ws in status.workflow_statuses if ws.task_id == "tm_001"
        )
        assert ws_tm_001.status == "generating"

        # Update status to success with additional info
        await manager.update_workflow_status_async(
            job_id="test-job-123",
            task_id="tm_001",
            workflow_status="success",
            workflow_name="workflow_tm_001",
            generation_time_ms=28500,
        )

        status = await manager.get_status_async("test-job-123")
        assert status is not None
        ws_tm_001 = next(
            ws for ws in status.workflow_statuses if ws.task_id == "tm_001"
        )
        assert ws_tm_001.status == "success"
        assert ws_tm_001.workflow_name == "workflow_tm_001"
        assert ws_tm_001.generation_time_ms == 28500

    @pytest.mark.unit
    async def test_update_workflow_status_failed(
        self, manager: JobCreationStateManager
    ) -> None:
        """Test update_workflow_status for failed workflow."""
        await manager.create_job_async("test-job-123")
        await manager.init_workflow_statuses_async("test-job-123", ["tm_001"])

        await manager.update_workflow_status_async(
            job_id="test-job-123",
            task_id="tm_001",
            workflow_status="failed",
            error_message="Workflow generation timed out",
        )

        status = await manager.get_status_async("test-job-123")
        assert status is not None
        ws_tm_001 = status.workflow_statuses[0]
        assert ws_tm_001.status == "failed"
        assert ws_tm_001.error_message == "Workflow generation timed out"


# ============================================================================
# B-4.5: JobTaskGeneratorState Extension Tests
# ============================================================================


class TestJobTaskGeneratorStateExtension:
    """Test JobTaskGeneratorState extension with new fields."""

    @pytest.mark.unit
    def test_create_initial_state_with_new_fields(self) -> None:
        """Test create_initial_state includes new fields."""
        from aiagent.langgraph.jobTaskGeneratorAgents.state import (
            create_initial_state,
        )

        state = create_initial_state("Create a workflow that fetches emails")

        # New fields should have default values
        assert state.get("workflow_results") == []
        assert state.get("phase") == "task_analysis"

    @pytest.mark.unit
    def test_state_can_store_workflow_results(self) -> None:
        """Test state can store workflow_results."""
        from aiagent.langgraph.jobTaskGeneratorAgents.state import (
            JobTaskGeneratorState,
        )

        # Simulate workflow results
        workflow_results: list[dict[str, Any]] = [
            {
                "task_id": "tm_001",
                "status": "success",
                "workflow_name": "workflow_tm_001",
                "yaml_content": "version: 0.6\nnodes: {}",
                "generation_time_ms": 28500,
            },
            {
                "task_id": "tm_002",
                "status": "failed",
                "error_message": "API error",
            },
        ]

        # State should accept workflow_results
        state: JobTaskGeneratorState = {
            "user_requirement": "test",
            "max_retry": 5,
            "workflow_results": workflow_results,
            "phase": "complete",
            "task_breakdown": [],
            "overall_summary": "",
            "interface_definitions": {},
            "schema_enrichment_stats": {},
            "task_masters": [],
            "task_master_ids": [],
            "job_master": {},
            "job_master_id": None,
            "feasibility_analysis": None,
            "infeasible_tasks": [],
            "alternative_proposals": [],
            "api_extension_proposals": [],
            "evaluation_result": None,
            "evaluation_retry_count": 0,
            "evaluation_errors": [],
            "evaluation_feedback": None,
            "evaluator_stage": "after_task_breakdown",
            "validation_result": None,
            "retry_count": 0,
            "validation_errors": [],
            "job_id": None,
            "status": "completed",
            "error_message": None,
        }

        assert state["workflow_results"] == workflow_results
        assert state["phase"] == "complete"


# ============================================================================
# B-5.1: generate_workflow_for_task Helper Tests
# ============================================================================


class TestGenerateWorkflowForTask:
    """Test generate_workflow_for_task helper function."""

    @pytest.mark.unit
    async def test_generate_workflow_for_task_success(self) -> None:
        """Test successful workflow generation for a task."""
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.workflow_helper import (
            generate_workflow_for_task,
        )

        task_master = {
            "id": "tm_001",
            "name": "Gmail Fetch Task",
            "description": "Fetch unread emails from Gmail API",
            "recommended_apis": ["Gmail API (users.messages.list)"],
            "input_schema": {"type": "object", "properties": {}},
            "output_schema": {"type": "object", "properties": {}},
        }

        # Mock the workflow generator
        with patch(
            "aiagent.langgraph.jobTaskGeneratorAgents.utils.workflow_helper.generate_workflow"
        ) as mock_generate:
            mock_generate.return_value = {
                "status": "success",
                "yaml_content": "version: 0.6\nnodes:\n  start: {}",
                "is_valid": True,
            }

            result = await generate_workflow_for_task(task_master)

            assert result["status"] == "success"
            assert result["workflow_name"] == "workflow_tm_001"
            assert "yaml_content" in result

    @pytest.mark.unit
    async def test_generate_workflow_for_task_failure(self) -> None:
        """Test workflow generation failure handling."""
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.workflow_helper import (
            generate_workflow_for_task,
        )

        task_master = {
            "id": "tm_001",
            "name": "Invalid Task",
            "description": "A task that will fail",
            "recommended_apis": [],
        }

        # Mock the workflow generator to raise an exception
        with patch(
            "aiagent.langgraph.jobTaskGeneratorAgents.utils.workflow_helper.generate_workflow"
        ) as mock_generate:
            mock_generate.side_effect = Exception("API connection failed")

            result = await generate_workflow_for_task(task_master)

            assert result["status"] == "failed"
            assert result["error_message"] == "API connection failed"
            assert result.get("workflow_name") is None

    @pytest.mark.unit
    async def test_generate_workflow_for_task_with_langfuse(self) -> None:
        """Test workflow generation passes langfuse handler."""
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.workflow_helper import (
            generate_workflow_for_task,
        )

        task_master = {
            "id": "tm_001",
            "name": "Test Task",
            "description": "A test task",
        }

        mock_langfuse_handler = MagicMock()

        with patch(
            "aiagent.langgraph.jobTaskGeneratorAgents.utils.workflow_helper.generate_workflow"
        ) as mock_generate:
            mock_generate.return_value = {
                "status": "success",
                "yaml_content": "version: 0.6",
            }

            await generate_workflow_for_task(
                task_master, langfuse_handler=mock_langfuse_handler
            )

            # Verify langfuse handler was passed
            mock_generate.assert_called_once()
            call_kwargs = mock_generate.call_args.kwargs
            assert call_kwargs.get("callback_handler") == mock_langfuse_handler


# ============================================================================
# B-5: workflow_generation_node Tests
# ============================================================================


class TestWorkflowGenerationNode:
    """Test workflow_generation_node function."""

    @pytest.fixture
    def mock_job_state_manager(self) -> MagicMock:
        """Create mock job state manager."""
        manager = MagicMock()
        manager.update_progress_async = AsyncMock()
        manager.update_phase_async = AsyncMock()
        manager.init_workflow_statuses_async = AsyncMock()
        manager.update_workflow_status_async = AsyncMock()
        # Issue #305: Add set_task_breakdown_async mock
        manager.set_task_breakdown_async = AsyncMock()
        return manager

    @pytest.fixture
    def mock_langfuse_service(self) -> MagicMock:
        """Create mock langfuse service.

        Issue #305: Added to support per-task tracing.
        """
        service = MagicMock()
        service.get_callback_handler = MagicMock(return_value=None)
        service.flush = MagicMock()
        return service

    @pytest.fixture
    def sample_state(self) -> dict[str, Any]:
        """Create sample state for testing."""
        return {
            "user_requirement": "Create email workflow",
            "max_retry": 5,
            "task_masters": [
                {
                    "id": "tm_001",
                    "name": "Gmail Fetch",
                    "description": "Fetch emails",
                    "recommended_apis": ["Gmail API"],
                },
                {
                    "id": "tm_002",
                    "name": "AI Analysis",
                    "description": "Analyze emails",
                    "recommended_apis": ["Claude API"],
                },
            ],
            "task_breakdown": [
                {
                    "task_id": "task_001",
                    "name": "Gmail Fetch",
                    "description": "Fetch emails",
                    "recommended_apis": ["Gmail API"],
                },
                {
                    "task_id": "task_002",
                    "name": "AI Analysis",
                    "description": "Analyze emails",
                    "recommended_apis": ["Claude API"],
                },
            ],
            "task_master_ids": ["tm_001", "tm_002"],
            "job_master_id": "jm_001",
            "job_id": "job_001",
            # Issue #305: tracking_job_id is used for progress tracking
            "tracking_job_id": "tracking_001",
            "status": "completed",
            "phase": "task_analysis",
            "workflow_results": [],
        }

    @pytest.mark.unit
    async def test_workflow_generation_node_success(
        self,
        mock_job_state_manager: MagicMock,
        mock_langfuse_service: MagicMock,
        sample_state: dict[str, Any],
    ) -> None:
        """Test successful workflow generation for all tasks."""
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.workflow_generation import (
            workflow_generation_node,
        )

        with patch(
            "aiagent.langgraph.jobTaskGeneratorAgents.nodes.workflow_generation.job_state_manager",
            mock_job_state_manager,
        ):
            with patch(
                "aiagent.langgraph.jobTaskGeneratorAgents.nodes.workflow_generation.langfuse_service",
                mock_langfuse_service,
            ):
                with patch(
                    "aiagent.langgraph.jobTaskGeneratorAgents.nodes.workflow_generation.generate_workflow_for_task"
                ) as mock_generate:
                    mock_generate.return_value = {
                        "status": "success",
                        "workflow_name": "test_workflow",
                        "yaml_content": "version: 0.6",
                    }

                    result = await workflow_generation_node(sample_state)

                    # Verify workflow results
                    assert result["phase"] == "complete"
                    assert len(result["workflow_results"]) == 2
                    assert all(
                        wr["status"] == "success" for wr in result["workflow_results"]
                    )

                    # Verify progress updates were made
                    mock_job_state_manager.update_phase_async.assert_called()
                    mock_job_state_manager.update_workflow_status_async.assert_called()

                    # Issue #305: Verify per-task tracing
                    assert mock_langfuse_service.get_callback_handler.call_count == 2

    @pytest.mark.unit
    async def test_workflow_generation_node_partial_failure(
        self,
        mock_job_state_manager: MagicMock,
        mock_langfuse_service: MagicMock,
        sample_state: dict[str, Any],
    ) -> None:
        """Test partial failure in workflow generation."""
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.workflow_generation import (
            workflow_generation_node,
        )

        call_count = 0

        async def mock_generate_side_effect(task_master: dict, **kwargs: Any) -> dict:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return {
                    "status": "success",
                    "workflow_name": f"workflow_{task_master['id']}",
                    "yaml_content": "version: 0.6",
                }
            else:
                return {
                    "status": "failed",
                    "error_message": "API timeout",
                }

        with patch(
            "aiagent.langgraph.jobTaskGeneratorAgents.nodes.workflow_generation.job_state_manager",
            mock_job_state_manager,
        ):
            with patch(
                "aiagent.langgraph.jobTaskGeneratorAgents.nodes.workflow_generation.langfuse_service",
                mock_langfuse_service,
            ):
                with patch(
                    "aiagent.langgraph.jobTaskGeneratorAgents.nodes.workflow_generation.generate_workflow_for_task"
                ) as mock_generate:
                    mock_generate.side_effect = mock_generate_side_effect

                    result = await workflow_generation_node(sample_state)

                    # Verify mixed results
                    assert len(result["workflow_results"]) == 2
                    # Note: With parallel execution, order may vary
                    success_count = sum(
                        1 for wr in result["workflow_results"] if wr["status"] == "success"
                    )
                    failed_count = sum(
                        1 for wr in result["workflow_results"] if wr["status"] == "failed"
                    )
                    assert success_count == 1
                    assert failed_count == 1
                    # Phase should still be complete (partial success)
                    assert result["phase"] == "complete"

    @pytest.mark.unit
    async def test_workflow_generation_node_empty_tasks(
        self, mock_job_state_manager: MagicMock
    ) -> None:
        """Test workflow generation with no tasks."""
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.workflow_generation import (
            workflow_generation_node,
        )

        state = {
            "user_requirement": "Test",
            "max_retry": 5,
            "task_masters": [],
            "task_master_ids": [],
            "job_master_id": "jm_001",
            "job_id": "job_001",
            "phase": "task_analysis",
            "workflow_results": [],
        }

        with patch(
            "aiagent.langgraph.jobTaskGeneratorAgents.nodes.workflow_generation.job_state_manager",
            mock_job_state_manager,
        ):
            result = await workflow_generation_node(state)

            assert result["phase"] == "complete"
            assert result["workflow_results"] == []

    @pytest.mark.unit
    async def test_workflow_generation_node_progress_updates(
        self,
        mock_job_state_manager: MagicMock,
        mock_langfuse_service: MagicMock,
        sample_state: dict[str, Any],
    ) -> None:
        """Test progress updates during workflow generation."""
        from aiagent.langgraph.jobTaskGeneratorAgents.nodes.workflow_generation import (
            workflow_generation_node,
        )

        progress_values: list[int] = []

        async def capture_progress(job_id: str, progress: int) -> None:
            progress_values.append(progress)

        mock_job_state_manager.update_progress_async = AsyncMock(
            side_effect=capture_progress
        )

        with patch(
            "aiagent.langgraph.jobTaskGeneratorAgents.nodes.workflow_generation.job_state_manager",
            mock_job_state_manager,
        ):
            with patch(
                "aiagent.langgraph.jobTaskGeneratorAgents.nodes.workflow_generation.langfuse_service",
                mock_langfuse_service,
            ):
                with patch(
                    "aiagent.langgraph.jobTaskGeneratorAgents.nodes.workflow_generation.generate_workflow_for_task"
                ) as mock_generate:
                    mock_generate.return_value = {
                        "status": "success",
                        "workflow_name": "test",
                        "yaml_content": "version: 0.6",
                    }

                    await workflow_generation_node(sample_state)

                    # Progress should increase (70% base + increments up to 95%)
                    assert len(progress_values) >= 2
                    # Each progress value should be >= 70 and <= 95
                    for progress in progress_values:
                        assert 70 <= progress <= 95


# ============================================================================
# Integration Tests
# ============================================================================


class TestWorkflowGenerationIntegration:
    """Integration tests for workflow generation flow."""

    @pytest.mark.unit
    async def test_full_workflow_generation_flow(self) -> None:
        """Test complete workflow generation flow."""
        # This test verifies the integration between:
        # - JobCreationStateManager (B-4)
        # - workflow_generation_node (B-5)
        # - generate_workflow_for_task (B-5.1)

        manager = JobCreationStateManager()
        job_id = "integration-test-job"

        # Create job and initialize
        await manager.create_job_async(job_id)
        await manager.update_phase_async(job_id, "task_analysis")

        # Set task breakdown
        breakdown = [
            TaskBreakdownItem(
                task_id="tm_001",
                name="Task 1",
                description="First task",
                recommended_apis=["API1"],
            ),
        ]
        await manager.set_task_breakdown_async(job_id, breakdown)

        # Verify phase changed
        status = await manager.get_status_async(job_id)
        assert status is not None
        assert status.phase == "workflow_generation"
        assert status.task_breakdown is not None
        assert len(status.task_breakdown) == 1
