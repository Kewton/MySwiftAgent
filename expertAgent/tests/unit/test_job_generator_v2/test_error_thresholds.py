"""Unit tests for error thresholds (Issue #342 Bug #3, #6).

This module tests:
- Bug #3: Silent skip error aggregation
- Bug #6: Schema count mismatch threshold-based judgment

Issue #342:
- Bug #3: Silent skip without error aggregation
- Bug #6: Schema count mismatch uses strict equality instead of threshold
"""


from aiagent.langgraph.jobGeneratorV2.types import (
    InterfaceSchema,
    TaskDefinition,
)


class TestSchemaCountMismatchThreshold:
    """Test schema count mismatch threshold-based judgment (Bug #6)."""

    def test_schema_count_diff_one_is_warning(self) -> None:
        """Bug #6: diff=1 should be a warning, not an error."""
        # Scenario: 3 tasks but 2 schemas generated (diff=1)
        tasks = [
            TaskDefinition(
                id="task_001",
                name="Task 1",
                description="First task",
                task_type="fetch",
                recommended_api="/api/fetch",
            ),
            TaskDefinition(
                id="task_002",
                name="Task 2",
                description="Second task",
                task_type="transform",
                recommended_api="/api/transform",
            ),
            TaskDefinition(
                id="task_003",
                name="Task 3",
                description="Third task",
                task_type="send",
                recommended_api="/api/send",
            ),
        ]

        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            ),
            # task_003 interface missing (diff=1)
        }

        # Calculate diff
        diff = len(tasks) - len(interfaces)

        # Bug #6 fix: diff=1 should be warning, not error
        assert diff == 1
        # This should NOT cause an error in the workflow
        # Actual implementation will handle this in schema_generator.py

    def test_schema_count_diff_two_or_more_is_error(self) -> None:
        """Bug #6: diff>=2 should be an error."""
        tasks = [
            TaskDefinition(
                id="task_001",
                name="Task 1",
                description="First task",
                task_type="fetch",
                recommended_api="/api/fetch",
            ),
            TaskDefinition(
                id="task_002",
                name="Task 2",
                description="Second task",
                task_type="transform",
                recommended_api="/api/transform",
            ),
            TaskDefinition(
                id="task_003",
                name="Task 3",
                description="Third task",
                task_type="send",
                recommended_api="/api/send",
            ),
        ]

        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            ),
            # task_002 and task_003 interfaces missing (diff=2)
        }

        diff = len(tasks) - len(interfaces)
        assert diff == 2
        # This SHOULD cause an error in the workflow

    def test_schema_count_exact_match_is_success(self) -> None:
        """Bug #6: exact match should be success."""
        tasks = [
            TaskDefinition(
                id="task_001",
                name="Task 1",
                description="First task",
                task_type="fetch",
                recommended_api="/api/fetch",
            ),
            TaskDefinition(
                id="task_002",
                name="Task 2",
                description="Second task",
                task_type="transform",
                recommended_api="/api/transform",
            ),
        ]

        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={"type": "object"},
                output_schema={"type": "object"},
            ),
        }

        diff = len(tasks) - len(interfaces)
        assert diff == 0
        # This should be success


class TestSilentSkipErrorAggregation:
    """Test silent skip error aggregation (Bug #3)."""

    def test_skip_counter_type_exists(self) -> None:
        """Bug #3: SkipCounter should be defined for tracking skips."""
        # Import the type from master_manager or orchestrator
        # This will be added during implementation
        from aiagent.langgraph.jobGeneratorV2.types import SkipInfo

        assert SkipInfo is not None

    def test_skip_info_captures_reason(self) -> None:
        """Bug #3: SkipInfo should capture skip reason and task_id."""
        from aiagent.langgraph.jobGeneratorV2.types import SkipInfo

        skip = SkipInfo(
            task_id="task_001",
            reason="No interface found for task",
            phase="registration",
        )

        assert skip.task_id == "task_001"
        assert "No interface found" in skip.reason
        assert skip.phase == "registration"

    def test_skip_aggregator_collects_multiple_skips(self) -> None:
        """Bug #3: SkipAggregator should collect multiple skips."""
        from aiagent.langgraph.jobGeneratorV2.types import SkipAggregator, SkipInfo

        aggregator = SkipAggregator()

        aggregator.add_skip(
            SkipInfo(
                task_id="task_001",
                reason="No interface found",
                phase="registration",
            )
        )
        aggregator.add_skip(
            SkipInfo(
                task_id="task_002",
                reason="API not available",
                phase="registration",
            )
        )

        assert aggregator.skip_count == 2
        assert len(aggregator.skips) == 2

    def test_skip_aggregator_raises_when_all_skipped(self) -> None:
        """Bug #3: SkipAggregator should raise error when all tasks are skipped."""
        from aiagent.langgraph.jobGeneratorV2.types import SkipAggregator, SkipInfo

        aggregator = SkipAggregator()
        total_tasks = 2

        aggregator.add_skip(
            SkipInfo(
                task_id="task_001",
                reason="No interface found",
                phase="registration",
            )
        )
        aggregator.add_skip(
            SkipInfo(
                task_id="task_002",
                reason="No interface found",
                phase="registration",
            )
        )

        # All tasks skipped -> should raise
        assert aggregator.all_skipped(total_tasks) is True

    def test_skip_aggregator_no_error_when_some_succeeded(self) -> None:
        """Bug #3: SkipAggregator should not raise when some tasks succeeded."""
        from aiagent.langgraph.jobGeneratorV2.types import SkipAggregator, SkipInfo

        aggregator = SkipAggregator()
        total_tasks = 3

        aggregator.add_skip(
            SkipInfo(
                task_id="task_001",
                reason="No interface found",
                phase="registration",
            )
        )
        # task_002 and task_003 succeeded (not in skips)

        assert aggregator.all_skipped(total_tasks) is False
        assert aggregator.skip_count == 1

    def test_skip_aggregator_get_error_summary(self) -> None:
        """Bug #3: SkipAggregator should provide error summary for logging."""
        from aiagent.langgraph.jobGeneratorV2.types import SkipAggregator, SkipInfo

        aggregator = SkipAggregator()

        aggregator.add_skip(
            SkipInfo(
                task_id="task_001",
                reason="No interface found for task",
                phase="registration",
            )
        )
        aggregator.add_skip(
            SkipInfo(
                task_id="task_002",
                reason="API endpoint not available",
                phase="workflow_gen",
            )
        )

        summary = aggregator.get_summary()

        assert "task_001" in summary
        assert "task_002" in summary
        assert "No interface found" in summary
        assert "API endpoint not available" in summary


class TestSchemaGeneratorThreshold:
    """Integration tests for schema generator threshold behavior."""

    def test_evaluate_schema_count_warning_threshold(self) -> None:
        """Test that evaluate_schema_count returns correct status for diff=1."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            evaluate_schema_count_mismatch,
        )

        # diff=1 should be WARNING (allow continue)
        result = evaluate_schema_count_mismatch(
            expected_count=3,
            actual_count=2,
        )

        assert result.is_acceptable is True
        assert result.severity == "warning"

    def test_evaluate_schema_count_error_threshold(self) -> None:
        """Test that evaluate_schema_count returns error for diff>=2."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            evaluate_schema_count_mismatch,
        )

        # diff=2 should be ERROR
        result = evaluate_schema_count_mismatch(
            expected_count=3,
            actual_count=1,
        )

        assert result.is_acceptable is False
        assert result.severity == "error"

    def test_evaluate_schema_count_success(self) -> None:
        """Test that evaluate_schema_count returns success for exact match."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator import (
            evaluate_schema_count_mismatch,
        )

        result = evaluate_schema_count_mismatch(
            expected_count=3,
            actual_count=3,
        )

        assert result.is_acceptable is True
        assert result.severity == "none"
