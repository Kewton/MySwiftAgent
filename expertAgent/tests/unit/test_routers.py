"""Unit tests for workflow routers.

These tests verify that routers correctly handle different workflow states
and route to the appropriate next node based on validation/evaluation results,
retry counts, and error conditions.

Issue #111: Recursion limit bug - routers must properly handle retry_count
to prevent infinite loops.
"""

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents.agent import (
    MAX_RETRY_COUNT,
    evaluator_router,
    validation_router,
)
from tests.utils.mock_helpers import create_mock_workflow_state


@pytest.mark.unit
class TestEvaluatorRouter:
    """Unit tests for evaluator router conditional logic."""

    # ========================================================================
    # Error Handling Tests
    # ========================================================================

    def test_evaluator_router_with_error_message(self):
        """Test that router returns END when error_message exists."""
        state = create_mock_workflow_state(
            retry_count=0,
            error_message="Some error occurred",
            evaluation_result={"is_valid": True},
        )

        result = evaluator_router(state)

        assert result == "END"

    def test_evaluator_router_missing_evaluation_result(self):
        """Test that router returns END when evaluation_result is missing."""
        state = create_mock_workflow_state(
            retry_count=0,
            evaluator_stage="after_task_breakdown",
        )

        result = evaluator_router(state)

        assert result == "END"

    def test_evaluator_router_empty_task_breakdown(self):
        """Test that router returns END when task_breakdown is empty."""
        state = create_mock_workflow_state(
            retry_count=0,
            evaluator_stage="after_task_breakdown",
            evaluation_result={"is_valid": True},
            task_breakdown=[],  # Empty list
        )

        result = evaluator_router(state)

        assert result == "END"

    def test_evaluator_router_empty_interface_definitions(self):
        """Test that router returns END when interface_definitions is empty."""
        state = create_mock_workflow_state(
            retry_count=0,
            evaluator_stage="after_interface_definition",
            evaluation_result={"is_valid": True},
            interface_definitions=[],  # Empty list
        )

        result = evaluator_router(state)

        assert result == "END"

    def test_evaluator_router_unknown_stage(self):
        """Test that router returns END for unknown evaluator_stage."""
        state = create_mock_workflow_state(
            retry_count=0,
            evaluator_stage="unknown_stage",
            evaluation_result={"is_valid": True},
        )

        result = evaluator_router(state)

        assert result == "END"

    # ========================================================================
    # After Task Breakdown Tests
    # ========================================================================

    def test_evaluator_router_after_task_breakdown_valid(self):
        """Test routing to interface_definition after valid task breakdown."""
        state = create_mock_workflow_state(
            retry_count=0,
            evaluator_stage="after_task_breakdown",
            evaluation_result={"is_valid": True},
            task_breakdown=[{"task_id": "task_1"}],
        )

        result = evaluator_router(state)

        assert result == "interface_definition"

    def test_evaluator_router_after_task_breakdown_invalid_retry(self):
        """Test retry routing when task breakdown invalid and retry < max."""
        state = create_mock_workflow_state(
            retry_count=2,  # Less than MAX_RETRY_COUNT (5)
            evaluator_stage="after_task_breakdown",
            evaluation_result={"is_valid": False},
            task_breakdown=[{"task_id": "task_1"}],
        )

        result = evaluator_router(state)

        assert result == "requirement_analysis"

    def test_evaluator_router_after_task_breakdown_invalid_max_retries(self):
        """Test END routing when task breakdown invalid and retry >= max."""
        state = create_mock_workflow_state(
            retry_count=MAX_RETRY_COUNT,  # At max retries
            evaluator_stage="after_task_breakdown",
            evaluation_result={"is_valid": False},
            task_breakdown=[{"task_id": "task_1"}],
        )

        result = evaluator_router(state)

        assert result == "END"

    def test_evaluator_router_after_task_breakdown_with_infeasible_tasks(self):
        """Test routing when some tasks are infeasible."""
        state = create_mock_workflow_state(
            retry_count=0,
            evaluator_stage="after_task_breakdown",
            evaluation_result={
                "is_valid": True,
                "all_tasks_feasible": False,
                "infeasible_tasks": [
                    {
                        "task_name": "複雑なタスク",
                        "reason": "APIが対応していない",
                    }
                ],
            },
            task_breakdown=[{"task_id": "task_1"}],
        )

        result = evaluator_router(state)

        # Should still proceed to interface_definition if is_valid=True
        assert result == "interface_definition"

    # ========================================================================
    # After Interface Definition Tests
    # ========================================================================

    def test_evaluator_router_after_interface_definition_valid(self):
        """Test routing to master_creation after valid interface definition."""
        state = create_mock_workflow_state(
            retry_count=0,
            evaluator_stage="after_interface_definition",
            evaluation_result={"is_valid": True},
            interface_definitions=[{"interface_name": "Interface1"}],
        )

        result = evaluator_router(state)

        assert result == "master_creation"

    def test_evaluator_router_after_interface_definition_invalid_retry(self):
        """Test retry routing when interface definition invalid and retry < max."""
        state = create_mock_workflow_state(
            retry_count=3,  # Less than MAX_RETRY_COUNT (5)
            evaluator_stage="after_interface_definition",
            evaluation_result={"is_valid": False},
            interface_definitions=[{"interface_name": "Interface1"}],
        )

        result = evaluator_router(state)

        assert result == "interface_definition"

    def test_evaluator_router_after_interface_definition_invalid_max_retries(self):
        """Test END routing when interface definition invalid and retry >= max."""
        state = create_mock_workflow_state(
            retry_count=MAX_RETRY_COUNT,  # At max retries
            evaluator_stage="after_interface_definition",
            evaluation_result={"is_valid": False},
            interface_definitions=[{"interface_name": "Interface1"}],
        )

        result = evaluator_router(state)

        assert result == "END"

    # ========================================================================
    # Boundary Tests
    # ========================================================================

    def test_evaluator_router_retry_count_at_boundary(self):
        """Test retry behavior exactly at MAX_RETRY_COUNT - 1."""
        # This should allow ONE MORE retry
        state = create_mock_workflow_state(
            retry_count=MAX_RETRY_COUNT - 1,  # 4 (one below max)
            evaluator_stage="after_task_breakdown",
            evaluation_result={"is_valid": False},
            task_breakdown=[{"task_id": "task_1"}],
        )

        result = evaluator_router(state)

        # Should still retry (retry_count < MAX_RETRY_COUNT)
        assert result == "requirement_analysis"

    def test_evaluator_router_retry_count_exceeds_max(self):
        """Test that retry_count > MAX_RETRY_COUNT also triggers END."""
        state = create_mock_workflow_state(
            retry_count=MAX_RETRY_COUNT + 1,  # 6 (exceeds max)
            evaluator_stage="after_task_breakdown",
            evaluation_result={"is_valid": False},
            task_breakdown=[{"task_id": "task_1"}],
        )

        result = evaluator_router(state)

        assert result == "END"


@pytest.mark.unit
class TestValidationRouter:
    """Unit tests for validation router conditional logic."""

    # ========================================================================
    # Error Handling Tests
    # ========================================================================

    def test_validation_router_with_error_message(self):
        """Test that router returns END when error_message exists."""
        state = create_mock_workflow_state(
            retry_count=0,
            error_message="Validation API error",
            validation_result={"is_valid": True, "errors": []},
        )

        result = validation_router(state)

        assert result == "END"

    def test_validation_router_missing_validation_result(self):
        """Test that router returns END when validation_result is missing."""
        state = create_mock_workflow_state(
            retry_count=0,
        )

        result = validation_router(state)

        assert result == "END"

    # ========================================================================
    # Success Tests
    # ========================================================================

    def test_validation_router_success(self):
        """Test routing to job_registration when validation succeeds."""
        state = create_mock_workflow_state(
            retry_count=0,
            validation_result={"is_valid": True, "errors": []},
        )

        result = validation_router(state)

        assert result == "job_registration"

    def test_validation_router_success_after_retries(self):
        """Test routing to job_registration even if retry_count > 0."""
        state = create_mock_workflow_state(
            retry_count=3,  # Had retries before, but now succeeded
            validation_result={"is_valid": True, "errors": []},
        )

        result = validation_router(state)

        assert result == "job_registration"

    # ========================================================================
    # Retry Tests
    # ========================================================================

    def test_validation_router_failure_retry(self):
        """Test retry routing when validation fails and retry < max."""
        state = create_mock_workflow_state(
            retry_count=2,  # Less than MAX_RETRY_COUNT (5)
            validation_result={
                "is_valid": False,
                "errors": ["Interface mismatch error"],
            },
        )

        result = validation_router(state)

        assert result == "interface_definition"

    def test_validation_router_failure_max_retries(self):
        """Test END routing when validation fails and retry >= max."""
        state = create_mock_workflow_state(
            retry_count=MAX_RETRY_COUNT,  # At max retries
            validation_result={
                "is_valid": False,
                "errors": ["Interface mismatch error"],
            },
        )

        result = validation_router(state)

        assert result == "END"

    def test_validation_router_failure_with_warnings_only(self):
        """Test that warnings don't affect routing if is_valid=True."""
        state = create_mock_workflow_state(
            retry_count=0,
            validation_result={
                "is_valid": True,
                "errors": [],
                "warnings": ["Optional field 'cc' rarely used"],
            },
        )

        result = validation_router(state)

        # Warnings should not prevent success routing
        assert result == "job_registration"

    # ========================================================================
    # Boundary Tests
    # ========================================================================

    def test_validation_router_retry_count_at_boundary(self):
        """Test retry behavior exactly at MAX_RETRY_COUNT - 1."""
        state = create_mock_workflow_state(
            retry_count=MAX_RETRY_COUNT - 1,  # 4 (one below max)
            validation_result={
                "is_valid": False,
                "errors": ["Interface mismatch"],
            },
        )

        result = validation_router(state)

        # Should still retry (retry_count < MAX_RETRY_COUNT)
        assert result == "interface_definition"

    def test_validation_router_retry_count_exceeds_max(self):
        """Test that retry_count > MAX_RETRY_COUNT also triggers END."""
        state = create_mock_workflow_state(
            retry_count=MAX_RETRY_COUNT + 1,  # 6 (exceeds max)
            validation_result={
                "is_valid": False,
                "errors": ["Interface mismatch"],
            },
        )

        result = validation_router(state)

        assert result == "END"

    def test_validation_router_multiple_errors(self):
        """Test routing when validation has multiple errors."""
        state = create_mock_workflow_state(
            retry_count=1,
            validation_result={
                "is_valid": False,
                "errors": [
                    "Missing required field 'file_path'",
                    "Schema type mismatch",
                    "Invalid enum value",
                ],
            },
        )

        result = validation_router(state)

        # Should retry to fix multiple errors
        assert result == "interface_definition"
