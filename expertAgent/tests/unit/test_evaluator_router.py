"""Unit tests for evaluator_router.

These tests verify the evaluator router's behavior including:
- Error handling (error_message, missing evaluation_result, unknown stage)
- after_task_breakdown stage routing logic
- after_interface_definition stage routing logic
- Retry count boundary testing
- Empty task breakdown / interface definitions handling
- Infeasible tasks detection and logging

Issue #111: Comprehensive test coverage for all workflow nodes.
"""

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents.agent import evaluator_router
from tests.utils.mock_helpers import create_mock_workflow_state


@pytest.mark.unit
class TestEvaluatorRouter:
    """Unit tests for evaluator_router."""

    # ========================================================================
    # Error Handling Tests (3 tests)
    # ========================================================================

    def test_evaluator_router_error_message_exists(self):
        """Test that router returns END when error_message exists.

        Priority: High
        This tests error handling priority.
        """
        state = create_mock_workflow_state(
            retry_count=0,
            error_message="Some error occurred",
            evaluation_result={"is_valid": True},
            evaluator_stage="after_task_breakdown",
        )

        result = evaluator_router(state)

        assert result == "END"

    def test_evaluator_router_missing_evaluation_result(self):
        """Test that router returns END when evaluation_result is missing.

        Priority: High
        This tests required data validation.
        """
        state = create_mock_workflow_state(
            retry_count=0,
            evaluator_stage="after_task_breakdown",
            # evaluation_result is missing
        )

        result = evaluator_router(state)

        assert result == "END"

    def test_evaluator_router_unknown_evaluator_stage(self):
        """Test that router returns END for unknown evaluator_stage.

        Priority: Medium
        This tests edge case handling.
        """
        state = create_mock_workflow_state(
            retry_count=0,
            evaluation_result={"is_valid": True, "all_tasks_feasible": True},
            evaluator_stage="unknown_stage",  # Unknown stage
        )

        result = evaluator_router(state)

        assert result == "END"

    # ========================================================================
    # after_task_breakdown Stage Tests (5 tests)
    # ========================================================================

    def test_evaluator_router_after_task_breakdown_valid(self):
        """Test routing to interface_definition when task breakdown is valid.

        Priority: High
        This is the happy path for after_task_breakdown stage.
        """
        state = create_mock_workflow_state(
            retry_count=0,
            evaluation_result={"is_valid": True, "all_tasks_feasible": True},
            evaluator_stage="after_task_breakdown",
            task_breakdown=[{"task_id": "task_1", "name": "Task 1"}],
        )

        result = evaluator_router(state)

        assert result == "interface_definition"

    def test_evaluator_router_after_task_breakdown_invalid_retry(self):
        """Test routing to requirement_analysis when invalid and retry available.

        Priority: High
        This tests retry logic.
        """
        state = create_mock_workflow_state(
            retry_count=2,  # < MAX_RETRY_COUNT (5)
            evaluation_result={"is_valid": False, "all_tasks_feasible": True},
            evaluator_stage="after_task_breakdown",
            task_breakdown=[{"task_id": "task_1", "name": "Task 1"}],
        )

        result = evaluator_router(state)

        assert result == "requirement_analysis"

    def test_evaluator_router_after_task_breakdown_max_retries(self):
        """Test routing to END when max retries reached.

        Priority: High
        This tests max retry boundary.
        """
        state = create_mock_workflow_state(
            retry_count=5,  # = MAX_RETRY_COUNT
            evaluation_result={"is_valid": False, "all_tasks_feasible": True},
            evaluator_stage="after_task_breakdown",
            task_breakdown=[{"task_id": "task_1", "name": "Task 1"}],
        )

        result = evaluator_router(state)

        assert result == "END"

    def test_evaluator_router_after_task_breakdown_empty_tasks(self):
        """Test routing to END when task_breakdown is empty.

        Priority: Medium
        This tests empty result handling.
        """
        state = create_mock_workflow_state(
            retry_count=0,
            evaluation_result={"is_valid": True, "all_tasks_feasible": True},
            evaluator_stage="after_task_breakdown",
            task_breakdown=[],  # Empty
        )

        result = evaluator_router(state)

        assert result == "END"

    def test_evaluator_router_after_task_breakdown_retry_boundary(self):
        """Test routing at retry count boundary (retry_count = 4).

        Priority: Medium
        This tests boundary condition.
        """
        state = create_mock_workflow_state(
            retry_count=4,  # < MAX_RETRY_COUNT (5) by 1
            evaluation_result={"is_valid": False, "all_tasks_feasible": True},
            evaluator_stage="after_task_breakdown",
            task_breakdown=[{"task_id": "task_1", "name": "Task 1"}],
        )

        result = evaluator_router(state)

        # Should still retry (4 < 5)
        assert result == "requirement_analysis"

    # ========================================================================
    # after_interface_definition Stage Tests (5 tests)
    # ========================================================================

    def test_evaluator_router_after_interface_definition_valid(self):
        """Test routing to master_creation when interface definition is valid.

        Priority: High
        This is the happy path for after_interface_definition stage.
        """
        state = create_mock_workflow_state(
            retry_count=0,
            evaluation_result={"is_valid": True, "all_tasks_feasible": True},
            evaluator_stage="after_interface_definition",
            interface_definitions={"task_1": {"interface_name": "Interface 1"}},
        )

        result = evaluator_router(state)

        assert result == "master_creation"

    def test_evaluator_router_after_interface_definition_invalid_retry(self):
        """Test routing to interface_definition when invalid and retry available.

        Priority: High
        This tests retry logic for interface definition stage.
        """
        state = create_mock_workflow_state(
            retry_count=2,  # < MAX_RETRY_COUNT (5)
            evaluation_result={"is_valid": False, "all_tasks_feasible": True},
            evaluator_stage="after_interface_definition",
            interface_definitions={"task_1": {"interface_name": "Interface 1"}},
        )

        result = evaluator_router(state)

        assert result == "interface_definition"

    def test_evaluator_router_after_interface_definition_max_retries(self):
        """Test routing to END when max retries reached.

        Priority: High
        This tests max retry boundary for interface definition stage.
        """
        state = create_mock_workflow_state(
            retry_count=5,  # = MAX_RETRY_COUNT
            evaluation_result={"is_valid": False, "all_tasks_feasible": True},
            evaluator_stage="after_interface_definition",
            interface_definitions={"task_1": {"interface_name": "Interface 1"}},
        )

        result = evaluator_router(state)

        assert result == "END"

    def test_evaluator_router_after_interface_definition_empty_interfaces(self):
        """Test routing to END when interface_definitions is empty.

        Priority: Medium
        This tests empty result handling for interface definition stage.
        """
        state = create_mock_workflow_state(
            retry_count=0,
            evaluation_result={"is_valid": True, "all_tasks_feasible": True},
            evaluator_stage="after_interface_definition",
            interface_definitions={},  # Empty
        )

        result = evaluator_router(state)

        assert result == "END"

    def test_evaluator_router_after_interface_definition_retry_boundary(self):
        """Test routing at retry count boundary (retry_count = 4).

        Priority: Medium
        This tests boundary condition for interface definition stage.
        """
        state = create_mock_workflow_state(
            retry_count=4,  # < MAX_RETRY_COUNT (5) by 1
            evaluation_result={"is_valid": False, "all_tasks_feasible": True},
            evaluator_stage="after_interface_definition",
            interface_definitions={"task_1": {"interface_name": "Interface 1"}},
        )

        result = evaluator_router(state)

        # Should still retry (4 < 5)
        assert result == "interface_definition"

    # ========================================================================
    # Infeasible Tasks Handling Tests (2 tests)
    # ========================================================================

    def test_evaluator_router_with_infeasible_tasks(self):
        """Test router behavior when infeasible_tasks are present.

        Priority: Low
        This tests infeasible tasks logging (does not affect routing).
        """
        state = create_mock_workflow_state(
            retry_count=0,
            evaluation_result={
                "is_valid": False,  # Invalid due to infeasible tasks
                "all_tasks_feasible": False,
                "infeasible_tasks": [
                    {
                        "task_id": "task_2",
                        "task_name": "Send SMS",
                        "reason": "SMS API not available",
                        "required_functionality": "SMS sending capability",
                    }
                ],
            },
            evaluator_stage="after_task_breakdown",
            task_breakdown=[
                {"task_id": "task_1", "name": "Task 1"},
                {"task_id": "task_2", "name": "Send SMS"},
            ],
        )

        result = evaluator_router(state)

        # Router should still follow normal logic (invalid + retry available)
        assert result == "requirement_analysis"

    def test_evaluator_router_all_tasks_feasible_false(self):
        """Test router behavior when all_tasks_feasible is False.

        Priority: Low
        This tests all_tasks_feasible flag behavior.
        """
        state = create_mock_workflow_state(
            retry_count=0,
            evaluation_result={
                "is_valid": False,
                "all_tasks_feasible": False,  # Not all tasks feasible
                "infeasible_tasks": [
                    {"task_id": "task_1", "task_name": "Infeasible task"}
                ],
            },
            evaluator_stage="after_task_breakdown",
            task_breakdown=[{"task_id": "task_1", "name": "Infeasible task"}],
        )

        result = evaluator_router(state)

        # Router should route to requirement_analysis (retry)
        # all_tasks_feasible does not directly affect routing logic
        assert result == "requirement_analysis"
