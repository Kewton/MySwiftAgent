"""Unit tests for validators.

Issue #359: Tests for TaskDependencyValidator and ValidationPipeline.

TDD Red Phase: These tests define the expected behavior of validators.
"""

import pytest

from aiagent.langgraph.jobGeneratorV2.validators.task_dependency import (
    TaskDependencyValidator,
    DependencyValidationResult,
)


class TestTaskDependencyValidator:
    """Test suite for TaskDependencyValidator."""

    def test_valid_linear_dependency(self):
        """Test valid linear dependency chain."""
        tasks = [
            {"task_id": "task_001", "dependencies": []},
            {"task_id": "task_002", "dependencies": ["task_001"]},
            {"task_id": "task_003", "dependencies": ["task_002"]},
        ]

        validator = TaskDependencyValidator()
        result = validator.validate(tasks)

        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_detect_circular_reference_direct(self):
        """Test detection of direct circular reference."""
        tasks = [
            {"task_id": "task_001", "dependencies": ["task_002"]},
            {"task_id": "task_002", "dependencies": ["task_001"]},
        ]

        validator = TaskDependencyValidator()
        result = validator.validate(tasks)

        assert result.is_valid is False
        assert len(result.circular_references) > 0
        assert "circular" in result.errors[0].lower()

    def test_detect_circular_reference_indirect(self):
        """Test detection of indirect circular reference."""
        tasks = [
            {"task_id": "task_001", "dependencies": ["task_003"]},
            {"task_id": "task_002", "dependencies": ["task_001"]},
            {"task_id": "task_003", "dependencies": ["task_002"]},
        ]

        validator = TaskDependencyValidator()
        result = validator.validate(tasks)

        assert result.is_valid is False
        assert len(result.circular_references) > 0

    def test_detect_self_reference(self):
        """Test detection of self-referencing task."""
        tasks = [
            {"task_id": "task_001", "dependencies": ["task_001"]},
        ]

        validator = TaskDependencyValidator()
        result = validator.validate(tasks)

        assert result.is_valid is False
        assert "self" in result.errors[0].lower() or "circular" in result.errors[0].lower()

    def test_detect_non_existent_dependency(self):
        """Test detection of reference to non-existent task."""
        tasks = [
            {"task_id": "task_001", "dependencies": []},
            {"task_id": "task_002", "dependencies": ["task_nonexistent"]},
        ]

        validator = TaskDependencyValidator()
        result = validator.validate(tasks)

        assert result.is_valid is False
        assert len(result.missing_dependencies) > 0
        assert "task_nonexistent" in result.missing_dependencies

    def test_empty_task_list_is_valid(self):
        """Test that empty task list is valid."""
        validator = TaskDependencyValidator()
        result = validator.validate([])

        assert result.is_valid is True

    def test_single_task_no_dependencies_is_valid(self):
        """Test single task with no dependencies is valid."""
        tasks = [
            {"task_id": "task_001", "dependencies": []},
        ]

        validator = TaskDependencyValidator()
        result = validator.validate(tasks)

        assert result.is_valid is True

    def test_complex_dag_is_valid(self):
        """Test complex but valid DAG structure."""
        # DAG structure:
        #     task_001
        #    /        \
        # task_002   task_003
        #    \        /
        #     task_004
        tasks = [
            {"task_id": "task_001", "dependencies": []},
            {"task_id": "task_002", "dependencies": ["task_001"]},
            {"task_id": "task_003", "dependencies": ["task_001"]},
            {"task_id": "task_004", "dependencies": ["task_002", "task_003"]},
        ]

        validator = TaskDependencyValidator()
        result = validator.validate(tasks)

        assert result.is_valid is True

    def test_get_execution_order(self):
        """Test that execution order respects dependencies."""
        tasks = [
            {"task_id": "task_003", "dependencies": ["task_002"]},
            {"task_id": "task_001", "dependencies": []},
            {"task_id": "task_002", "dependencies": ["task_001"]},
        ]

        validator = TaskDependencyValidator()
        result = validator.validate(tasks)

        assert result.is_valid is True
        # Execution order should have task_001 before task_002 before task_003
        order = result.execution_order
        assert order.index("task_001") < order.index("task_002")
        assert order.index("task_002") < order.index("task_003")

    def test_multiple_errors_detected(self):
        """Test that multiple errors are all reported."""
        tasks = [
            {"task_id": "task_001", "dependencies": ["task_nonexistent"]},
            {"task_id": "task_002", "dependencies": ["task_002"]},  # Self-reference
        ]

        validator = TaskDependencyValidator()
        result = validator.validate(tasks)

        assert result.is_valid is False
        # Should detect both the missing dependency and the self-reference
        assert len(result.errors) >= 2 or (
            len(result.missing_dependencies) > 0 and len(result.circular_references) > 0
        )


class TestDependencyValidationResult:
    """Test suite for DependencyValidationResult."""

    def test_create_valid_result(self):
        """Test creating a valid result."""
        result = DependencyValidationResult(
            is_valid=True,
            execution_order=["task_001", "task_002", "task_003"]
        )

        assert result.is_valid is True
        assert len(result.execution_order) == 3
        assert len(result.errors) == 0

    def test_create_invalid_result(self):
        """Test creating an invalid result."""
        result = DependencyValidationResult(
            is_valid=False,
            errors=["Circular reference detected"],
            circular_references=[["task_001", "task_002"]],
        )

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert len(result.circular_references) == 1

    def test_default_values(self):
        """Test default values for optional fields."""
        result = DependencyValidationResult(is_valid=True)

        assert result.errors == []
        assert result.circular_references == []
        assert result.missing_dependencies == []
        assert result.execution_order == []

    def test_to_error_message(self):
        """Test error message generation."""
        result = DependencyValidationResult(
            is_valid=False,
            errors=["Circular reference: task_001 -> task_002 -> task_001"],
            circular_references=[["task_001", "task_002", "task_001"]],
        )

        message = result.to_error_message()

        assert "task_001" in message
        assert "task_002" in message
