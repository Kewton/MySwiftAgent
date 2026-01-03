"""Integration tests for object array routing in workflow generator.

Issue #340: Test the full routing flow for object array detection,
including the sample_input_generator -> router -> workflow_tester/test_data_regenerator flow.
"""

from typing import Any

from aiagent.langgraph.workflowGeneratorAgents.nodes.sample_input_generator import (
    _enum_or_default,
    _get_string_template_input_fields,
    _validate_primitive_arrays,
)
from aiagent.langgraph.workflowGeneratorAgents.routers.sample_input_router import (
    sample_input_router,
)
from aiagent.langgraph.workflowGeneratorAgents.state import (
    create_initial_state,
)


class TestObjectArrayRoutingIntegration:
    """Integration tests for object array detection and routing."""

    # ========== State Initialization Tests ==========

    def test_initial_state_has_object_array_fields(self) -> None:
        """MF-1: Initial state should include object_array_regeneration_count and max."""
        state = create_initial_state(
            task_master_id="tm_test_001",
            task_data={"name": "Test Task", "description": "Test"},
        )
        assert "object_array_regeneration_count" in state
        assert "max_object_array_regeneration" in state
        assert state["object_array_regeneration_count"] == 0
        assert state["max_object_array_regeneration"] == 2

    def test_initial_state_object_array_validation_fields(self) -> None:
        """State should have object_array_issues and has_object_array_errors."""
        state = create_initial_state(
            task_master_id="tm_test_001",
            task_data={"name": "Test Task", "description": "Test"},
        )
        assert "object_array_issues" in state
        assert "has_object_array_errors" in state
        assert state["object_array_issues"] == []
        assert state["has_object_array_errors"] is False

    # ========== Normal Flow Integration ==========

    def test_normal_flow_no_object_arrays(self) -> None:
        """Test normal flow: no object arrays -> workflow_tester."""
        # Simulate sample_input_generator output (no object arrays)
        state: dict[str, Any] = {
            "sample_input": {"query": "test query", "max_results": 10},
            "object_array_issues": [],
            "has_object_array_errors": False,
            "object_array_regeneration_count": 0,
            "max_object_array_regeneration": 2,
        }

        # Router should direct to workflow_tester
        next_node = sample_input_router(state)
        assert next_node == "workflow_tester"

    def test_string_array_with_valid_default_flow(self) -> None:
        """Test flow: valid string array default -> workflow_tester."""
        # Schema with valid string array default
        schema = {
            "type": "array",
            "items": {"type": "string"},
            "default": ["item1", "item2"],
        }

        # _enum_or_default should return the valid default
        result = _enum_or_default(schema)
        assert result == ["item1", "item2"]

        # State after sample_input_generator (no issues detected)
        state: dict[str, Any] = {
            "sample_input": {"focus_points": ["item1", "item2"]},
            "object_array_issues": [],
            "has_object_array_errors": False,
            "object_array_regeneration_count": 0,
            "max_object_array_regeneration": 2,
        }

        next_node = sample_input_router(state)
        assert next_node == "workflow_tester"

    # ========== Error Flow Integration ==========

    def test_error_flow_object_array_detected(self) -> None:
        """Test error flow: object array detected -> test_data_regenerator."""
        # Schema with invalid object array default
        schema = {
            "type": "array",
            "items": {"type": "string"},
            "default": [{"type": "string", "description": "news"}],
        }

        # _enum_or_default should return None (invalid default rejected)
        result = _enum_or_default(schema)
        assert result is None

        # Simulate state after sample_input_generator detects object arrays
        state: dict[str, Any] = {
            "sample_input": {
                "focus_points": [{"type": "string", "description": "news"}]
            },
            "object_array_issues": [
                {
                    "field_name": "focus_points",
                    "issue_type": "object_in_array",
                    "message": "Array field 'focus_points' contains object",
                }
            ],
            "has_object_array_errors": True,
            "object_array_regeneration_count": 0,
            "max_object_array_regeneration": 2,
        }

        next_node = sample_input_router(state)
        assert next_node == "test_data_regenerator"

    def test_regeneration_increments_count(self) -> None:
        """Test that regeneration count is tracked correctly."""
        # Initial state with error
        initial_count = 0

        # Simulate test_data_regenerator incrementing count
        new_count = initial_count + 1

        # State after first regeneration
        state: dict[str, Any] = {
            "has_object_array_errors": True,  # Still has errors after regeneration
            "object_array_issues": [{"field_name": "focus_points"}],
            "object_array_regeneration_count": new_count,  # Incremented
            "max_object_array_regeneration": 2,
        }

        # Should still route to regenerator (count < max)
        next_node = sample_input_router(state)
        assert next_node == "test_data_regenerator"
        assert state["object_array_regeneration_count"] == 1

    # ========== Max Regeneration Exceeded Flow (MF-1) ==========

    def test_max_regeneration_exceeded_flow(self) -> None:
        """MF-1: Test flow when max regeneration exceeded -> workflow_tester."""
        # State after max regeneration attempts
        state: dict[str, Any] = {
            "sample_input": {
                "focus_points": [{"type": "string"}]  # Still invalid
            },
            "object_array_issues": [
                {
                    "field_name": "focus_points",
                    "issue_type": "object_in_array",
                    "message": "Array field 'focus_points' contains object",
                }
            ],
            "has_object_array_errors": True,
            "object_array_regeneration_count": 2,  # Reached max
            "max_object_array_regeneration": 2,
        }

        # Should route to workflow_tester despite errors (max exceeded)
        next_node = sample_input_router(state)
        assert next_node == "workflow_tester"

    def test_full_regeneration_cycle(self) -> None:
        """Test complete regeneration cycle from error to success."""
        # Cycle 1: Initial error detection
        state1: dict[str, Any] = {
            "has_object_array_errors": True,
            "object_array_issues": [{"field_name": "focus_points"}],
            "object_array_regeneration_count": 0,
            "max_object_array_regeneration": 2,
        }
        assert sample_input_router(state1) == "test_data_regenerator"

        # Cycle 2: After first regeneration (still has errors)
        state2: dict[str, Any] = {
            "has_object_array_errors": True,
            "object_array_issues": [{"field_name": "focus_points"}],
            "object_array_regeneration_count": 1,
            "max_object_array_regeneration": 2,
        }
        assert sample_input_router(state2) == "test_data_regenerator"

        # Cycle 3: After second regeneration (max exceeded, must continue)
        state3: dict[str, Any] = {
            "has_object_array_errors": True,
            "object_array_issues": [{"field_name": "focus_points"}],
            "object_array_regeneration_count": 2,
            "max_object_array_regeneration": 2,
        }
        assert sample_input_router(state3) == "workflow_tester"

    def test_successful_regeneration_flow(self) -> None:
        """Test flow when regeneration successfully fixes the issue."""
        # After successful regeneration (errors cleared)
        state: dict[str, Any] = {
            "sample_input": {"focus_points": ["news", "topics"]},  # Now valid
            "object_array_issues": [],  # Cleared
            "has_object_array_errors": False,  # Cleared
            "object_array_regeneration_count": 1,  # One regeneration happened
            "max_object_array_regeneration": 2,
        }

        # Should route to workflow_tester (no more errors)
        next_node = sample_input_router(state)
        assert next_node == "workflow_tester"

    # ========== Validation Helper Integration ==========

    def test_validate_primitive_arrays_detects_objects(self) -> None:
        """Test _validate_primitive_arrays correctly detects object arrays."""
        sample_input = {
            "focus_points": [{"type": "string", "description": "news"}],
            "keywords": ["valid", "strings"],
            "count": 10,
        }
        target_fields = {"focus_points", "keywords"}

        issues = _validate_primitive_arrays(sample_input, target_fields)

        # Should detect issue in focus_points only
        assert len(issues) == 1
        assert issues[0]["field_name"] == "focus_points"
        assert issues[0]["issue_type"] == "object_in_array"

    def test_validate_primitive_arrays_no_issues(self) -> None:
        """Test _validate_primitive_arrays returns empty when no issues."""
        sample_input = {
            "focus_points": ["news", "topics"],
            "keywords": ["valid", "strings"],
            "count": 10,
        }
        target_fields = {"focus_points", "keywords"}

        issues = _validate_primitive_arrays(sample_input, target_fields)
        assert issues == []

    def test_get_string_template_input_fields(self) -> None:
        """Test _get_string_template_input_fields extracts correct fields."""
        yaml_content = """
nodes:
  format_output:
    agent: stringTemplateAgent
    inputs:
      focus_points: :source.user_input.focus_points
      query: :source.user_input.query
  other_agent:
    agent: copyAgent
    inputs:
      data: :source.user_input.data
"""
        fields = _get_string_template_input_fields(yaml_content)

        # Should only include fields used by stringTemplateAgent
        assert "focus_points" in fields
        assert "query" in fields
        assert "data" not in fields  # Not used by stringTemplateAgent

    def test_validate_only_string_template_fields(self) -> None:
        """Integration: Only validate arrays used by stringTemplateAgent."""
        sample_input = {
            "focus_points": [{"type": "string"}],  # Used by stringTemplateAgent
            "data": [{"nested": "object"}],  # NOT used by stringTemplateAgent
        }
        target_fields = {"focus_points"}  # Only focus_points is a target

        issues = _validate_primitive_arrays(sample_input, target_fields)

        # Should only detect issue in focus_points (data is not a target)
        assert len(issues) == 1
        assert issues[0]["field_name"] == "focus_points"
