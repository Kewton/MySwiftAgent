"""Extended unit tests for CompatibilityCheckerSubWorkflow.

Issue #342 Phase C.2: Additional tests for coverage improvement.
"""

import pytest

from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
from aiagent.langgraph.jobGeneratorV2.types import (
    InterfaceSchema,
    TaskDefinition,
)


class TestGetOutputProperties:
    """Tests for _get_output_properties helper function."""

    def test_get_output_properties_from_dict(self):
        """Should extract properties from dict schema."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            _get_output_properties,
        )

        schema = {"type": "object", "properties": {"name": {"type": "string"}}}
        result = _get_output_properties(schema)

        assert result == {"name": {"type": "string"}}

    def test_get_output_properties_empty_schema(self):
        """Should return empty dict for schema without properties."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            _get_output_properties,
        )

        schema = {"type": "object"}
        result = _get_output_properties(schema)

        assert result == {}

    def test_get_output_properties_non_dict(self):
        """Should return empty dict for non-dict schema."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            _get_output_properties,
        )

        result = _get_output_properties("not a dict")
        assert result == {}


class TestGetRequiredInputs:
    """Tests for _get_required_inputs helper function."""

    def test_get_required_inputs_from_schema(self):
        """Should extract required list from schema."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            _get_required_inputs,
        )

        schema = {"type": "object", "required": ["name", "email"]}
        result = _get_required_inputs(schema)

        assert result == ["name", "email"]

    def test_get_required_inputs_no_required(self):
        """Should return empty list if no required field."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            _get_required_inputs,
        )

        schema = {"type": "object"}
        result = _get_required_inputs(schema)

        assert result == []

    def test_get_required_inputs_non_dict(self):
        """Should return empty list for non-dict schema."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            _get_required_inputs,
        )

        result = _get_required_inputs("not a dict")
        assert result == []


class TestCheckTypeCompatibility:
    """Tests for _check_type_compatibility helper function."""

    def test_check_type_same_type(self):
        """Should return True for same type."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            _check_type_compatibility,
        )

        assert _check_type_compatibility("string", "string") is True
        assert _check_type_compatibility("integer", "integer") is True

    def test_check_type_integer_to_number(self):
        """Should allow integer to number."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            _check_type_compatibility,
        )

        assert _check_type_compatibility("integer", "number") is True

    def test_check_type_any_source(self):
        """Should allow any source type."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            _check_type_compatibility,
        )

        assert _check_type_compatibility("any", "string") is True

    def test_check_type_any_target(self):
        """Should allow any target type."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            _check_type_compatibility,
        )

        assert _check_type_compatibility("string", "any") is True

    def test_check_type_none_values(self):
        """Should return True for None values (missing type info)."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            _check_type_compatibility,
        )

        assert _check_type_compatibility(None, "string") is True
        assert _check_type_compatibility("string", None) is True
        assert _check_type_compatibility(None, None) is True

    def test_check_type_incompatible(self):
        """Should return False for incompatible types."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            _check_type_compatibility,
        )

        assert _check_type_compatibility("string", "integer") is False
        assert _check_type_compatibility("array", "object") is False


class TestCheckInterfaceCompatibility:
    """Tests for _check_interface_compatibility helper function."""

    def test_check_interface_type_mismatch(self):
        """Should detect type mismatch between interfaces."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            _check_interface_compatibility,
        )

        source_interface = InterfaceSchema(
            task_id="task_001",
            input_schema={},
            output_schema={
                "type": "object",
                "properties": {"data": {"type": "string"}},
            },
        )
        target_interface = InterfaceSchema(
            task_id="task_002",
            input_schema={
                "type": "object",
                "properties": {"data": {"type": "integer"}},  # Type mismatch!
            },
            output_schema={},
        )
        source_task = TaskDefinition(
            id="task_001", name="Source", description="", task_type="", recommended_api=""
        )
        target_task = TaskDefinition(
            id="task_002", name="Target", description="", task_type="", recommended_api=""
        )

        issues = _check_interface_compatibility(
            source_interface, target_interface, source_task, target_task
        )

        assert len(issues) == 1
        assert "Type mismatch" in issues[0]


class TestCompatibilityCheckerMissingInterfaces:
    """Tests for compatibility checker with missing interfaces."""

    @pytest.fixture
    def tasks_with_deps(self) -> list[TaskDefinition]:
        """Create tasks with dependencies."""
        return [
            TaskDefinition(
                id="task_001",
                name="Task 1",
                description="",
                task_type="",
                recommended_api="",
                dependencies=[],
            ),
            TaskDefinition(
                id="task_002",
                name="Task 2",
                description="",
                task_type="",
                recommended_api="",
                dependencies=["task_001"],
            ),
        ]

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock context."""
        return ExecutionContext(
            job_id="test-job",
            user_requirement="Test",
        )

    @pytest.mark.asyncio
    async def test_check_missing_target_interface(
        self, tasks_with_deps: list[TaskDefinition], mock_context: ExecutionContext
    ):
        """Should report missing target interface."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            CompatibilityCheckerSubWorkflow,
        )

        # Only provide interface for task_001, missing task_002
        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={},
                output_schema={"type": "object"},
            )
        }

        checker = CompatibilityCheckerSubWorkflow()
        result = await checker.check(tasks_with_deps, interfaces, mock_context)

        assert result.is_compatible is False
        assert any("Missing interface for task" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_check_missing_dependency_interface(
        self, tasks_with_deps: list[TaskDefinition], mock_context: ExecutionContext
    ):
        """Should report missing dependency interface."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            CompatibilityCheckerSubWorkflow,
        )

        # Only provide interface for task_002, missing task_001 (dependency)
        interfaces = {
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={"required": ["data"]},
                output_schema={},
            )
        }

        checker = CompatibilityCheckerSubWorkflow()
        result = await checker.check(tasks_with_deps, interfaces, mock_context)

        assert result.is_compatible is False
        assert any("Missing interface for dependency" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_check_unknown_dependency(
        self, mock_context: ExecutionContext
    ):
        """Should report unknown dependency task."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            CompatibilityCheckerSubWorkflow,
        )

        tasks = [
            TaskDefinition(
                id="task_002",
                name="Task 2",
                description="",
                task_type="",
                recommended_api="",
                dependencies=["unknown_task"],  # This task doesn't exist
            )
        ]
        interfaces = {
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={},
                output_schema={},
            )
        }

        checker = CompatibilityCheckerSubWorkflow()
        result = await checker.check(tasks, interfaces, mock_context)

        assert result.is_compatible is False
        assert any("unknown task" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_check_no_dependencies(
        self, mock_context: ExecutionContext
    ):
        """Should pass for task with no dependencies."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            CompatibilityCheckerSubWorkflow,
        )

        tasks = [
            TaskDefinition(
                id="task_001",
                name="Task 1",
                description="",
                task_type="",
                recommended_api="",
                dependencies=[],  # No dependencies
            )
        ]
        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={},
                output_schema={},
            )
        }

        checker = CompatibilityCheckerSubWorkflow()
        result = await checker.check(tasks, interfaces, mock_context)

        assert result.is_compatible is True

    @pytest.mark.asyncio
    async def test_check_empty_tasks(
        self, mock_context: ExecutionContext
    ):
        """Should pass for empty tasks list."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.compatibility import (
            CompatibilityCheckerSubWorkflow,
        )

        checker = CompatibilityCheckerSubWorkflow()
        result = await checker.check([], {"task_001": InterfaceSchema(task_id="task_001", input_schema={}, output_schema={})}, mock_context)

        assert result.is_compatible is True
