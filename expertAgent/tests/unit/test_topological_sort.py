"""Unit tests for topological sort utility.

Issue #402: Tests for dependency-based task ordering using Kahn's algorithm.

Test Categories:
1. Linear dependencies (A -> B -> C)
2. Branch dependencies (A -> B, A -> C)
3. Independent tasks (no dependencies)
4. Circular dependency detection
5. Priority sub-sort within same dependency level
6. Edge cases (empty list, single task)
7. Integration with TaskDefinition
"""

import pytest

from aiagent.langgraph.jobGeneratorV2.protocols import ErrorType, WorkflowError
from aiagent.langgraph.jobGeneratorV2.types_old import Phase, TaskDefinition
from aiagent.langgraph.jobGeneratorV2.utils.topological_sort import (
    _build_dependency_graph,
    _topological_sort_with_priority,
    topological_sort_task_dicts,
    topological_sort_tasks,
)

# ============================================================
# Test Fixtures
# ============================================================


@pytest.fixture
def linear_dependency_tasks() -> list[TaskDefinition]:
    """Tasks with linear dependencies: task_001 -> task_002 -> task_003."""
    return [
        TaskDefinition(
            id="task_001",
            name="First Task",
            description="First in chain",
            task_type="fetch",
            recommended_api="/api/v1/fetch",
            priority=3,
            dependencies=[],
        ),
        TaskDefinition(
            id="task_002",
            name="Second Task",
            description="Depends on first",
            task_type="transform",
            recommended_api="/api/v1/transform",
            priority=2,
            dependencies=["task_001"],
        ),
        TaskDefinition(
            id="task_003",
            name="Third Task",
            description="Depends on second",
            task_type="send",
            recommended_api="/api/v1/send",
            priority=1,
            dependencies=["task_002"],
        ),
    ]


@pytest.fixture
def branch_dependency_tasks() -> list[TaskDefinition]:
    """Tasks with branch dependencies: task_001 -> task_002, task_001 -> task_003."""
    return [
        TaskDefinition(
            id="task_001",
            name="Root Task",
            description="Root of branch",
            task_type="fetch",
            recommended_api="/api/v1/fetch",
            priority=1,
            dependencies=[],
        ),
        TaskDefinition(
            id="task_002",
            name="Branch A",
            description="First branch",
            task_type="transform",
            recommended_api="/api/v1/transform",
            priority=3,
            dependencies=["task_001"],
        ),
        TaskDefinition(
            id="task_003",
            name="Branch B",
            description="Second branch",
            task_type="transform",
            recommended_api="/api/v1/transform",
            priority=2,
            dependencies=["task_001"],
        ),
    ]


@pytest.fixture
def independent_tasks() -> list[TaskDefinition]:
    """Tasks with no dependencies - sorted by priority."""
    return [
        TaskDefinition(
            id="task_001",
            name="Task A",
            description="Independent A",
            task_type="fetch",
            recommended_api="/api/v1/fetch",
            priority=3,
            dependencies=[],
        ),
        TaskDefinition(
            id="task_002",
            name="Task B",
            description="Independent B",
            task_type="fetch",
            recommended_api="/api/v1/fetch",
            priority=1,
            dependencies=[],
        ),
        TaskDefinition(
            id="task_003",
            name="Task C",
            description="Independent C",
            task_type="fetch",
            recommended_api="/api/v1/fetch",
            priority=2,
            dependencies=[],
        ),
    ]


@pytest.fixture
def circular_dependency_tasks() -> list[TaskDefinition]:
    """Tasks with circular dependencies: task_001 -> task_002 -> task_003 -> task_001."""
    return [
        TaskDefinition(
            id="task_001",
            name="Cycle Start",
            description="Depends on task_003 (cycle)",
            task_type="fetch",
            recommended_api="/api/v1/fetch",
            priority=1,
            dependencies=["task_003"],
        ),
        TaskDefinition(
            id="task_002",
            name="Cycle Mid",
            description="Depends on task_001",
            task_type="transform",
            recommended_api="/api/v1/transform",
            priority=2,
            dependencies=["task_001"],
        ),
        TaskDefinition(
            id="task_003",
            name="Cycle End",
            description="Depends on task_002",
            task_type="send",
            recommended_api="/api/v1/send",
            priority=3,
            dependencies=["task_002"],
        ),
    ]


@pytest.fixture
def complex_dag_tasks() -> list[TaskDefinition]:
    r"""Complex DAG with multiple dependencies.

    Structure:
        task_001 (no deps, priority=1)
           |
        task_002 (deps=[001], priority=2)
         /   \
    task_003  task_004 (deps=[002], priority 3 and 4)
         \   /
        task_005 (deps=[003, 004], priority=5)
    """
    return [
        TaskDefinition(
            id="task_001",
            name="Root",
            description="Root node",
            task_type="fetch",
            recommended_api="/api/v1/fetch",
            priority=1,
            dependencies=[],
        ),
        TaskDefinition(
            id="task_002",
            name="Level 1",
            description="First level",
            task_type="transform",
            recommended_api="/api/v1/transform",
            priority=2,
            dependencies=["task_001"],
        ),
        TaskDefinition(
            id="task_003",
            name="Level 2 Left",
            description="Left branch",
            task_type="transform",
            recommended_api="/api/v1/transform",
            priority=3,
            dependencies=["task_002"],
        ),
        TaskDefinition(
            id="task_004",
            name="Level 2 Right",
            description="Right branch",
            task_type="transform",
            recommended_api="/api/v1/transform",
            priority=4,
            dependencies=["task_002"],
        ),
        TaskDefinition(
            id="task_005",
            name="Merge",
            description="Merge node",
            task_type="send",
            recommended_api="/api/v1/send",
            priority=5,
            dependencies=["task_003", "task_004"],
        ),
    ]


# ============================================================
# Tests for topological_sort_tasks
# ============================================================


class TestTopologicalSortTasks:
    """Tests for the main topological_sort_tasks function."""

    def test_linear_dependency_order(
        self, linear_dependency_tasks: list[TaskDefinition]
    ) -> None:
        """AC-1: Linear dependencies should maintain order."""
        result = topological_sort_tasks(linear_dependency_tasks)

        # Extract IDs for comparison
        result_ids = [t.id for t in result]

        # task_001 must come before task_002, task_002 must come before task_003
        assert result_ids.index("task_001") < result_ids.index("task_002")
        assert result_ids.index("task_002") < result_ids.index("task_003")

    def test_branch_dependency_order(
        self, branch_dependency_tasks: list[TaskDefinition]
    ) -> None:
        """AC-1: Branch dependencies respect parent first."""
        result = topological_sort_tasks(branch_dependency_tasks)

        result_ids = [t.id for t in result]

        # task_001 must come before both task_002 and task_003
        assert result_ids.index("task_001") < result_ids.index("task_002")
        assert result_ids.index("task_001") < result_ids.index("task_003")

    def test_branch_priority_subsort(
        self, branch_dependency_tasks: list[TaskDefinition]
    ) -> None:
        """AC-4: Same dependency level sorted by priority."""
        result = topological_sort_tasks(branch_dependency_tasks)

        result_ids = [t.id for t in result]

        # task_002 (priority=3) should come after task_003 (priority=2)
        # at the same dependency level
        assert result_ids.index("task_003") < result_ids.index("task_002")

    def test_empty_dependencies_priority_sort(
        self, independent_tasks: list[TaskDefinition]
    ) -> None:
        """AC-5: Empty dependencies sorted by priority."""
        result = topological_sort_tasks(independent_tasks)

        result_ids = [t.id for t in result]

        # Order should be: task_002 (p=1), task_003 (p=2), task_001 (p=3)
        assert result_ids == ["task_002", "task_003", "task_001"]

    def test_circular_dependency_raises_error(
        self, circular_dependency_tasks: list[TaskDefinition]
    ) -> None:
        """AC-2, AC-6: Circular dependencies raise WorkflowError."""
        with pytest.raises(WorkflowError) as exc_info:
            topological_sort_tasks(circular_dependency_tasks)

        # Check error type and phase
        assert exc_info.value.error_type == ErrorType.VALIDATION
        assert exc_info.value.phase == Phase.REGISTRATION

        # Check message contains cycle information
        assert "circular dependency" in str(exc_info.value).lower()

    def test_empty_task_list(self) -> None:
        """Edge case: Empty task list returns empty list."""
        result = topological_sort_tasks([])
        assert result == []

    def test_single_task(self) -> None:
        """Edge case: Single task returns that task."""
        task = TaskDefinition(
            id="task_001",
            name="Single Task",
            description="Only task",
            task_type="fetch",
            recommended_api="/api/v1/fetch",
            priority=1,
            dependencies=[],
        )
        result = topological_sort_tasks([task])

        assert len(result) == 1
        assert result[0].id == "task_001"

    def test_complex_dag_ordering(
        self, complex_dag_tasks: list[TaskDefinition]
    ) -> None:
        """Complex DAG maintains topological order."""
        result = topological_sort_tasks(complex_dag_tasks)

        result_ids = [t.id for t in result]

        # Verify order constraints
        assert result_ids.index("task_001") < result_ids.index("task_002")
        assert result_ids.index("task_002") < result_ids.index("task_003")
        assert result_ids.index("task_002") < result_ids.index("task_004")
        assert result_ids.index("task_003") < result_ids.index("task_005")
        assert result_ids.index("task_004") < result_ids.index("task_005")

    def test_preserves_task_definition_attributes(
        self, linear_dependency_tasks: list[TaskDefinition]
    ) -> None:
        """Sorted tasks maintain all original attributes."""
        result = topological_sort_tasks(linear_dependency_tasks)

        # Find task_001 in result
        task_001 = next(t for t in result if t.id == "task_001")

        assert task_001.name == "First Task"
        assert task_001.description == "First in chain"
        assert task_001.task_type == "fetch"
        assert task_001.recommended_api == "/api/v1/fetch"
        assert task_001.priority == 3
        assert task_001.dependencies == []


# ============================================================
# Tests for _build_dependency_graph
# ============================================================


class TestBuildDependencyGraph:
    """Tests for the internal _build_dependency_graph function."""

    def test_builds_adjacency_list(
        self, linear_dependency_tasks: list[TaskDefinition]
    ) -> None:
        """Builds correct adjacency list from tasks."""
        task_map = {t.id: t for t in linear_dependency_tasks}
        graph, in_degree = _build_dependency_graph(task_map)

        # task_001 has outgoing edge to nothing (it has no dependents in adjacency)
        # Actually, we need to track who depends on whom
        # If task_002 depends on task_001, then graph[task_001] should contain task_002
        assert "task_002" in graph["task_001"]
        assert "task_003" in graph["task_002"]
        assert graph["task_003"] == []

    def test_computes_in_degrees(
        self, linear_dependency_tasks: list[TaskDefinition]
    ) -> None:
        """Computes correct in-degrees."""
        task_map = {t.id: t for t in linear_dependency_tasks}
        graph, in_degree = _build_dependency_graph(task_map)

        assert in_degree["task_001"] == 0  # No dependencies
        assert in_degree["task_002"] == 1  # Depends on task_001
        assert in_degree["task_003"] == 1  # Depends on task_002

    def test_branch_in_degrees(
        self, branch_dependency_tasks: list[TaskDefinition]
    ) -> None:
        """Branch dependencies compute correct in-degrees."""
        task_map = {t.id: t for t in branch_dependency_tasks}
        graph, in_degree = _build_dependency_graph(task_map)

        assert in_degree["task_001"] == 0  # No dependencies
        assert in_degree["task_002"] == 1  # Depends on task_001
        assert in_degree["task_003"] == 1  # Depends on task_001

    def test_multiple_in_degrees(self, complex_dag_tasks: list[TaskDefinition]) -> None:
        """Multiple dependencies compute correct in-degrees."""
        task_map = {t.id: t for t in complex_dag_tasks}
        graph, in_degree = _build_dependency_graph(task_map)

        assert in_degree["task_005"] == 2  # Depends on task_003 and task_004


# ============================================================
# Tests for _topological_sort_with_priority
# ============================================================


class TestTopologicalSortWithPriority:
    """Tests for the internal _topological_sort_with_priority function."""

    def test_uses_priority_as_tiebreaker(
        self, independent_tasks: list[TaskDefinition]
    ) -> None:
        """AC-4, AC-5: Priority used as tiebreaker for same level."""
        task_map = {t.id: t for t in independent_tasks}
        graph, in_degree = _build_dependency_graph(task_map)

        result = _topological_sort_with_priority(graph, in_degree, task_map)

        # All have in_degree=0, so sorted by priority
        assert result == ["task_002", "task_003", "task_001"]

    def test_detects_cycle(
        self, circular_dependency_tasks: list[TaskDefinition]
    ) -> None:
        """Detects cycles and raises WorkflowError."""
        task_map = {t.id: t for t in circular_dependency_tasks}
        graph, in_degree = _build_dependency_graph(task_map)

        with pytest.raises(WorkflowError) as exc_info:
            _topological_sort_with_priority(graph, in_degree, task_map)

        assert exc_info.value.error_type == ErrorType.VALIDATION


# ============================================================
# Tests for edge cases
# ============================================================


class TestEdgeCases:
    """Edge case tests for topological sort."""

    def test_missing_dependency_ignored(self) -> None:
        """Tasks with references to non-existent dependencies should fail."""
        tasks = [
            TaskDefinition(
                id="task_001",
                name="Task",
                description="Has missing dependency",
                task_type="fetch",
                recommended_api="/api/v1/fetch",
                priority=1,
                dependencies=["task_999"],  # Does not exist
            ),
        ]

        # This should raise an error because the dependency doesn't exist
        with pytest.raises(WorkflowError) as exc_info:
            topological_sort_tasks(tasks)

        assert "task_999" in str(exc_info.value)

    def test_self_dependency_is_cycle(self) -> None:
        """Self-referencing task is a cycle."""
        tasks = [
            TaskDefinition(
                id="task_001",
                name="Self Ref",
                description="Depends on itself",
                task_type="fetch",
                recommended_api="/api/v1/fetch",
                priority=1,
                dependencies=["task_001"],
            ),
        ]

        with pytest.raises(WorkflowError) as exc_info:
            topological_sort_tasks(tasks)

        assert exc_info.value.error_type == ErrorType.VALIDATION

    def test_duplicate_dependencies_handled(self) -> None:
        """Duplicate dependencies in list should be handled."""
        tasks = [
            TaskDefinition(
                id="task_001",
                name="Root",
                description="Root task",
                task_type="fetch",
                recommended_api="/api/v1/fetch",
                priority=1,
                dependencies=[],
            ),
            TaskDefinition(
                id="task_002",
                name="Dependent",
                description="Has duplicate dependency",
                task_type="transform",
                recommended_api="/api/v1/transform",
                priority=2,
                dependencies=["task_001", "task_001"],  # Duplicate
            ),
        ]

        result = topological_sort_tasks(tasks)
        result_ids = [t.id for t in result]

        assert result_ids.index("task_001") < result_ids.index("task_002")


# ============================================================
# Tests for topological_sort_task_dicts (dict-based tasks)
# ============================================================


class TestTopologicalSortTaskDicts:
    """Tests for the topological_sort_task_dicts function (legacy dict format)."""

    def test_linear_dependency_order_dict(self) -> None:
        """AC-1: Linear dependencies with dict format."""
        task_dicts = [
            {
                "task_id": "task_001",
                "name": "First Task",
                "dependencies": [],
                "priority": 3,
            },
            {
                "task_id": "task_002",
                "name": "Second Task",
                "dependencies": ["task_001"],
                "priority": 2,
            },
            {
                "task_id": "task_003",
                "name": "Third Task",
                "dependencies": ["task_002"],
                "priority": 1,
            },
        ]

        result = topological_sort_task_dicts(task_dicts)
        result_ids = [t["task_id"] for t in result]

        assert result_ids.index("task_001") < result_ids.index("task_002")
        assert result_ids.index("task_002") < result_ids.index("task_003")

    def test_branch_priority_subsort_dict(self) -> None:
        """AC-4: Same dependency level sorted by priority (dict format)."""
        task_dicts = [
            {"task_id": "task_001", "dependencies": [], "priority": 1},
            {"task_id": "task_002", "dependencies": ["task_001"], "priority": 3},
            {"task_id": "task_003", "dependencies": ["task_001"], "priority": 2},
        ]

        result = topological_sort_task_dicts(task_dicts)
        result_ids = [t["task_id"] for t in result]

        # task_003 (priority=2) should come before task_002 (priority=3)
        assert result_ids.index("task_003") < result_ids.index("task_002")

    def test_empty_dependencies_priority_sort_dict(self) -> None:
        """AC-5: Empty dependencies sorted by priority (dict format)."""
        task_dicts = [
            {"task_id": "task_001", "dependencies": [], "priority": 3},
            {"task_id": "task_002", "dependencies": [], "priority": 1},
            {"task_id": "task_003", "dependencies": [], "priority": 2},
        ]

        result = topological_sort_task_dicts(task_dicts)
        result_ids = [t["task_id"] for t in result]

        assert result_ids == ["task_002", "task_003", "task_001"]

    def test_circular_dependency_raises_error_dict(self) -> None:
        """AC-2, AC-6: Circular dependencies raise WorkflowError (dict format)."""
        task_dicts = [
            {"task_id": "task_001", "dependencies": ["task_003"], "priority": 1},
            {"task_id": "task_002", "dependencies": ["task_001"], "priority": 2},
            {"task_id": "task_003", "dependencies": ["task_002"], "priority": 3},
        ]

        with pytest.raises(WorkflowError) as exc_info:
            topological_sort_task_dicts(task_dicts)

        assert exc_info.value.error_type == ErrorType.VALIDATION
        assert exc_info.value.phase == Phase.REGISTRATION

    def test_empty_task_list_dict(self) -> None:
        """Edge case: Empty task list returns empty list (dict format)."""
        result = topological_sort_task_dicts([])
        assert result == []

    def test_single_task_dict(self) -> None:
        """Edge case: Single task returns that task (dict format)."""
        task_dicts = [{"task_id": "task_001", "dependencies": [], "priority": 1}]

        result = topological_sort_task_dicts(task_dicts)

        assert len(result) == 1
        assert result[0]["task_id"] == "task_001"

    def test_missing_dependency_dict(self) -> None:
        """Missing dependency raises WorkflowError (dict format)."""
        task_dicts = [
            {"task_id": "task_001", "dependencies": ["task_999"], "priority": 1},
        ]

        with pytest.raises(WorkflowError) as exc_info:
            topological_sort_task_dicts(task_dicts)

        assert "task_999" in str(exc_info.value)

    def test_self_dependency_dict(self) -> None:
        """Self-referencing task is a cycle (dict format)."""
        task_dicts = [
            {"task_id": "task_001", "dependencies": ["task_001"], "priority": 1},
        ]

        with pytest.raises(WorkflowError) as exc_info:
            topological_sort_task_dicts(task_dicts)

        assert exc_info.value.error_type == ErrorType.VALIDATION

    def test_default_priority_dict(self) -> None:
        """Tasks without priority default to 5."""
        task_dicts = [
            {"task_id": "task_001", "dependencies": []},  # No priority
            {"task_id": "task_002", "dependencies": [], "priority": 3},
            {"task_id": "task_003", "dependencies": [], "priority": 7},
        ]

        result = topological_sort_task_dicts(task_dicts)
        result_ids = [t["task_id"] for t in result]

        # task_002 (p=3) < task_001 (p=5 default) < task_003 (p=7)
        assert result_ids == ["task_002", "task_001", "task_003"]

    def test_preserves_dict_attributes(self) -> None:
        """Sorted dicts maintain all original attributes."""
        task_dicts = [
            {
                "task_id": "task_001",
                "name": "Original Name",
                "description": "Original Desc",
                "dependencies": [],
                "priority": 1,
                "extra_field": "preserved",
            },
        ]

        result = topological_sort_task_dicts(task_dicts)

        assert result[0]["name"] == "Original Name"
        assert result[0]["description"] == "Original Desc"
        assert result[0]["extra_field"] == "preserved"
