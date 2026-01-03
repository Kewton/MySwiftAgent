"""Unit tests for sample_input_router.

Issue #340: Test routing logic for object array detection with infinite loop prevention (MF-1).
"""

from aiagent.langgraph.workflowGeneratorAgents.routers.sample_input_router import (
    sample_input_router,
)


class TestSampleInputRouter:
    """Test sample_input_router routing logic."""

    # ========== Normal Flow Tests ==========

    def test_route_to_workflow_tester_when_no_errors(self) -> None:
        """No object array errors should route directly to workflow_tester."""
        state = {
            "has_object_array_errors": False,
            "object_array_issues": [],
            "object_array_regeneration_count": 0,
            "max_object_array_regeneration": 2,
        }
        result = sample_input_router(state)
        assert result == "workflow_tester"

    def test_route_to_workflow_tester_with_default_state(self) -> None:
        """Empty state (default values) should route to workflow_tester."""
        state: dict = {}
        result = sample_input_router(state)
        assert result == "workflow_tester"

    # ========== Error Flow Tests ==========

    def test_route_to_test_data_regenerator_on_first_error(self) -> None:
        """First object array error should route to test_data_regenerator."""
        state = {
            "has_object_array_errors": True,
            "object_array_issues": [{"field_name": "focus_points"}],
            "object_array_regeneration_count": 0,
            "max_object_array_regeneration": 2,
        }
        result = sample_input_router(state)
        assert result == "test_data_regenerator"

    def test_route_to_test_data_regenerator_on_second_attempt(self) -> None:
        """Second regeneration attempt should still route to test_data_regenerator."""
        state = {
            "has_object_array_errors": True,
            "object_array_issues": [{"field_name": "focus_points"}],
            "object_array_regeneration_count": 1,
            "max_object_array_regeneration": 2,
        }
        result = sample_input_router(state)
        assert result == "test_data_regenerator"

    # ========== Infinite Loop Prevention Tests (MF-1) ==========

    def test_route_to_workflow_tester_when_max_exceeded(self) -> None:
        """MF-1: When max regeneration exceeded, should continue to workflow_tester."""
        state = {
            "has_object_array_errors": True,
            "object_array_issues": [{"field_name": "focus_points"}],
            "object_array_regeneration_count": 2,
            "max_object_array_regeneration": 2,
        }
        result = sample_input_router(state)
        assert result == "workflow_tester"

    def test_route_to_workflow_tester_when_count_exceeds_max(self) -> None:
        """MF-1: When count > max, should continue to workflow_tester."""
        state = {
            "has_object_array_errors": True,
            "object_array_issues": [{"field_name": "focus_points"}],
            "object_array_regeneration_count": 5,  # Way over max
            "max_object_array_regeneration": 2,
        }
        result = sample_input_router(state)
        assert result == "workflow_tester"

    def test_custom_max_regeneration(self) -> None:
        """MF-1: Custom max_object_array_regeneration should be respected."""
        state = {
            "has_object_array_errors": True,
            "object_array_issues": [{"field_name": "focus_points"}],
            "object_array_regeneration_count": 3,
            "max_object_array_regeneration": 5,  # Custom higher limit
        }
        result = sample_input_router(state)
        assert result == "test_data_regenerator"  # Still under limit

    def test_max_regeneration_default_value(self) -> None:
        """MF-1: Missing max_object_array_regeneration should use default (2)."""
        state = {
            "has_object_array_errors": True,
            "object_array_issues": [{"field_name": "focus_points"}],
            "object_array_regeneration_count": 2,
            # max_object_array_regeneration is missing, defaults to 2
        }
        result = sample_input_router(state)
        assert result == "workflow_tester"  # 2 >= 2, so max exceeded

    # ========== Multiple Issues Tests ==========

    def test_route_with_multiple_object_array_issues(self) -> None:
        """Multiple object array issues should route to test_data_regenerator."""
        state = {
            "has_object_array_errors": True,
            "object_array_issues": [
                {"field_name": "focus_points"},
                {"field_name": "keywords"},
                {"field_name": "topics"},
            ],
            "object_array_regeneration_count": 0,
            "max_object_array_regeneration": 2,
        }
        result = sample_input_router(state)
        assert result == "test_data_regenerator"

    # ========== Edge Cases ==========

    def test_route_with_empty_issues_list_but_flag_true(self) -> None:
        """Empty issues list with flag true should route to regenerator."""
        state = {
            "has_object_array_errors": True,
            "object_array_issues": [],  # Empty but flag is True
            "object_array_regeneration_count": 0,
            "max_object_array_regeneration": 2,
        }
        result = sample_input_router(state)
        assert result == "test_data_regenerator"

    def test_route_with_zero_max_regeneration(self) -> None:
        """MF-1: Zero max_object_array_regeneration should immediately skip to workflow_tester."""
        state = {
            "has_object_array_errors": True,
            "object_array_issues": [{"field_name": "focus_points"}],
            "object_array_regeneration_count": 0,
            "max_object_array_regeneration": 0,  # Disable regeneration
        }
        result = sample_input_router(state)
        assert result == "workflow_tester"
