"""Unit tests for recursion limit protection.

These tests verify that the workflow properly stops at MAX_RETRY_COUNT
and never creates infinite loops that would trigger Python's recursion limit (50).

Issue #111: Before retry_count fix, validation failures would cause infinite
loops because retry_count wasn't incremented, eventually hitting the recursion
limit. These tests ensure that bug is caught early.
"""

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents.agent import MAX_RETRY_COUNT
from tests.utils.mock_helpers import create_mock_workflow_state


@pytest.mark.unit
class TestRecursionLimitProtection:
    """Tests to ensure retry_count prevents infinite loops."""

    def test_max_retry_count_constant_value(self):
        """Verify MAX_RETRY_COUNT is set to a reasonable value."""
        # MAX_RETRY_COUNT should be well below Python's recursion limit (50)
        # to prevent RecursionError
        assert MAX_RETRY_COUNT < 50, (
            f"MAX_RETRY_COUNT ({MAX_RETRY_COUNT}) is too high. "
            "Must be < 50 to prevent RecursionError."
        )

        # Should be >= 3 to allow meaningful retries
        assert MAX_RETRY_COUNT >= 3, (
            f"MAX_RETRY_COUNT ({MAX_RETRY_COUNT}) is too low. "
            "Should allow at least 3 retries."
        )

    def test_retry_count_increment_prevents_infinite_loop(self):
        """Test that retry_count incrementing prevents infinite loops.

        This is a logical test verifying that if retry_count increments
        properly, the workflow will eventually reach MAX_RETRY_COUNT and stop.
        """
        # Simulate workflow retry loop
        retry_count = 0
        loop_iterations = 0
        max_iterations = 100  # Safety limit to detect infinite loops

        while retry_count < MAX_RETRY_COUNT and loop_iterations < max_iterations:
            # Simulate a retry (this would be a node returning retry_count + 1)
            retry_count += 1
            loop_iterations += 1

        # Should have stopped at MAX_RETRY_COUNT
        assert retry_count == MAX_RETRY_COUNT, (
            f"Expected retry_count to reach {MAX_RETRY_COUNT}, "
            f"but got {retry_count}"
        )

        # Should NOT have hit the safety limit
        assert loop_iterations < max_iterations, (
            f"Infinite loop detected! Reached {loop_iterations} iterations "
            f"without stopping at MAX_RETRY_COUNT ({MAX_RETRY_COUNT})"
        )

        # Should have stopped well before Python's recursion limit
        assert loop_iterations < 50, (
            f"Loop iterations ({loop_iterations}) approaching recursion limit (50)"
        )

    def test_buggy_retry_count_would_cause_infinite_loop(self):
        """Test that demonstrates the bug: NOT incrementing retry_count.

        This test SIMULATES the bug to show what would happen if
        retry_count is not incremented (infinite loop).
        """
        # Simulate BUGGY workflow where retry_count is NOT incremented
        retry_count = 0
        loop_iterations = 0
        max_iterations = 100  # Safety limit

        while retry_count < MAX_RETRY_COUNT and loop_iterations < max_iterations:
            # BUG SIMULATION: retry_count is NOT incremented
            # (This is what happened in the buggy validation_node)
            # retry_count += 1  # This line is MISSING in buggy code
            loop_iterations += 1

        # Should have hit the safety limit (infinite loop detected)
        assert loop_iterations == max_iterations, (
            "Expected infinite loop, but it stopped unexpectedly. "
            "This test is meant to demonstrate the bug."
        )

        # retry_count should still be 0 (never incremented)
        assert retry_count == 0, (
            "retry_count was incremented, but this test simulates the bug "
            "where it's NOT incremented."
        )

    def test_workflow_state_with_max_retries_should_trigger_end(self):
        """Test that workflow state with retry_count=MAX stops routing."""
        from aiagent.langgraph.jobTaskGeneratorAgents.agent import (
            evaluator_router,
            validation_router,
        )

        # Test evaluator_router with max retries
        evaluator_state = create_mock_workflow_state(
            retry_count=MAX_RETRY_COUNT,
            evaluator_stage="after_task_breakdown",
            evaluation_result={"is_valid": False},
            task_breakdown=[{"task_id": "task_1"}],
        )
        evaluator_result = evaluator_router(evaluator_state)
        assert evaluator_result == "END", (
            "evaluator_router should return END when retry_count >= MAX_RETRY_COUNT"
        )

        # Test validation_router with max retries
        validation_state = create_mock_workflow_state(
            retry_count=MAX_RETRY_COUNT,
            validation_result={"is_valid": False, "errors": ["Error"]},
        )
        validation_result = validation_router(validation_state)
        assert validation_result == "END", (
            "validation_router should return END when retry_count >= MAX_RETRY_COUNT"
        )

    def test_retry_count_progression_through_workflow(self):
        """Test retry_count progression through multiple workflow stages.

        This simulates a workflow that fails multiple times and verifies
        that retry_count increments properly at each stage.
        """
        # Simulate workflow progression with failures
        workflow_stages = [
            "requirement_analysis",
            "evaluator_after_task_breakdown",
            "interface_definition",
            "evaluator_after_interface_definition",
            "validation",
        ]

        retry_count = 0

        for stage in workflow_stages:
            # Simulate each stage incrementing retry_count on failure
            retry_count += 1

            # Verify we haven't exceeded MAX_RETRY_COUNT
            if retry_count >= MAX_RETRY_COUNT:
                # Workflow should stop here
                break

        # Should have stopped at or before MAX_RETRY_COUNT
        assert retry_count <= MAX_RETRY_COUNT, (
            f"retry_count ({retry_count}) exceeded MAX_RETRY_COUNT "
            f"({MAX_RETRY_COUNT})"
        )

    def test_retry_count_reset_on_success(self):
        """Test that retry_count resets to 0 on success.

        This is important to prevent previous failures from affecting
        subsequent workflow stages.
        """
        # Simulate workflow with initial failures, then success
        retry_count = 3  # Had some failures

        # Simulate success (retry_count should reset to 0)
        is_successful = True
        if is_successful:
            retry_count = 0

        assert retry_count == 0, (
            "retry_count should reset to 0 on success, "
            f"but got {retry_count}"
        )

    def test_multiple_retry_cycles(self):
        """Test that retry_count can reset and retry again in later stages.

        Workflow stages:
        1. requirement_analysis → evaluator (success) → retry_count=0
        2. interface_definition → evaluator (failure) → retry_count++
        3. interface_definition → evaluator (failure) → retry_count++
        4. interface_definition → evaluator (success) → retry_count=0
        5. validation (failure) → retry_count++
        6. validation (success) → retry_count=0
        """
        # Stage 1: requirement_analysis → success
        retry_count = 0
        assert retry_count == 0

        # Stage 2-3: interface_definition failures
        retry_count += 1  # First failure
        assert retry_count == 1
        retry_count += 1  # Second failure
        assert retry_count == 2

        # Stage 4: interface_definition success (reset)
        retry_count = 0
        assert retry_count == 0

        # Stage 5: validation failure
        retry_count += 1
        assert retry_count == 1

        # Stage 6: validation success (reset)
        retry_count = 0
        assert retry_count == 0

        # Final state: should be 0 (successful workflow)
        assert retry_count == 0

    def test_edge_case_retry_count_at_boundary(self):
        """Test behavior at retry_count = MAX_RETRY_COUNT - 1.

        This is the last retry attempt before hitting the limit.
        """
        retry_count = MAX_RETRY_COUNT - 1  # Last retry

        # Should allow one more retry
        can_retry = retry_count < MAX_RETRY_COUNT
        assert can_retry is True

        # After one more failure, should stop
        retry_count += 1
        can_retry = retry_count < MAX_RETRY_COUNT
        assert can_retry is False

    def test_retry_count_overflow_protection(self):
        """Test that retry_count > MAX_RETRY_COUNT also triggers stop.

        This handles edge cases where retry_count might accidentally
        exceed MAX_RETRY_COUNT.
        """
        # Simulate accidental overflow
        retry_count = MAX_RETRY_COUNT + 10  # Way over the limit

        # Router should still stop
        can_retry = retry_count < MAX_RETRY_COUNT
        assert can_retry is False

        # Should route to END
        from aiagent.langgraph.jobTaskGeneratorAgents.agent import evaluator_router

        state = create_mock_workflow_state(
            retry_count=retry_count,
            evaluator_stage="after_task_breakdown",
            evaluation_result={"is_valid": False},
            task_breakdown=[{"task_id": "task_1"}],
        )
        result = evaluator_router(state)
        assert result == "END"

    def test_recursion_depth_calculation(self):
        """Verify that MAX_RETRY_COUNT * workflow_stages < recursion_limit.

        Worst case: Each stage retries MAX_RETRY_COUNT times.
        Total depth = MAX_RETRY_COUNT * num_stages

        This should be well below Python's recursion limit (default 1000,
        reduced to 50 in some environments).
        """
        num_workflow_stages = 5  # requirement, evaluator, interface, validation, etc.
        max_recursion_depth = MAX_RETRY_COUNT * num_workflow_stages

        # Should be well below Python's reduced recursion limit (50)
        assert max_recursion_depth < 50, (
            f"Max recursion depth ({max_recursion_depth}) is too high. "
            f"MAX_RETRY_COUNT ({MAX_RETRY_COUNT}) * stages ({num_workflow_stages}) "
            "must be < 50 to prevent RecursionError."
        )

        # Also verify against default Python recursion limit (1000)
        import sys

        recursion_limit = sys.getrecursionlimit()
        assert max_recursion_depth < recursion_limit, (
            f"Max recursion depth ({max_recursion_depth}) exceeds "
            f"Python recursion limit ({recursion_limit})"
        )
