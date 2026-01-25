"""Topological sort utility for task dependencies.

Issue #402: Implements Kahn's algorithm for dependency-based task ordering.

This module provides:
- topological_sort_tasks: Main function to sort TaskDefinition list
- topological_sort_task_dicts: Function to sort dict-based tasks (legacy support)
- _build_dependency_graph: Internal helper to build adjacency list
- _topological_sort_with_priority: Internal Kahn's algorithm with priority tiebreaker

Algorithm: Kahn's Algorithm
- Time Complexity: O(V + E) where V = tasks, E = dependencies
- Space Complexity: O(V)
- Detects circular dependencies during sort

Example:
    tasks = [
        TaskDefinition(id="task_001", dependencies=[]),
        TaskDefinition(id="task_002", dependencies=["task_001"]),
    ]
    sorted_tasks = topological_sort_tasks(tasks)
    # sorted_tasks: [task_001, task_002]
"""

from __future__ import annotations

import heapq
import logging
from typing import TYPE_CHECKING, Any

from aiagent.langgraph.jobGeneratorV2.protocols import ErrorType, WorkflowError
from aiagent.langgraph.jobGeneratorV2.types_old import Phase

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.types_old import TaskDefinition

logger = logging.getLogger(__name__)


class _TaskDictWrapper:
    """Wrapper to make dict-based tasks compatible with topological sort.

    This wrapper provides a common interface for accessing task properties
    from dict-based task definitions (legacy format).
    """

    def __init__(self, task_dict: dict[str, Any]) -> None:
        """Initialize wrapper with task dict.

        Args:
            task_dict: Task definition as dict with keys:
                - task_id: Unique task identifier
                - dependencies: List of task_ids this task depends on
                - priority: Task priority (default: 5)
        """
        self._dict = task_dict

    @property
    def id(self) -> str:
        """Get task ID (uses 'task_id' key for legacy compatibility)."""
        return str(self._dict.get("task_id", ""))

    @property
    def dependencies(self) -> list[str]:
        """Get dependencies list."""
        deps = self._dict.get("dependencies", [])
        return deps if isinstance(deps, list) else []

    @property
    def priority(self) -> int:
        """Get priority (default: 5)."""
        return int(self._dict.get("priority", 5))


def topological_sort_tasks(tasks: list["TaskDefinition"]) -> list["TaskDefinition"]:
    """Sort tasks by their dependencies using topological sort.

    Uses Kahn's algorithm with priority as a tiebreaker for tasks
    at the same dependency level.

    Args:
        tasks: List of TaskDefinition objects to sort

    Returns:
        List of TaskDefinition objects in topological order

    Raises:
        WorkflowError: If circular dependencies are detected
            (ErrorType.VALIDATION, Phase.REGISTRATION)
        WorkflowError: If a dependency references a non-existent task

    Example:
        >>> tasks = [
        ...     TaskDefinition(id="A", dependencies=["B"]),
        ...     TaskDefinition(id="B", dependencies=[]),
        ... ]
        >>> sorted_tasks = topological_sort_tasks(tasks)
        >>> [t.id for t in sorted_tasks]
        ['B', 'A']
    """
    if not tasks:
        logger.debug("topological_sort_tasks: Empty task list, returning empty")
        return []

    if len(tasks) == 1:
        task = tasks[0]
        # Validate single task doesn't have missing dependencies
        if task.dependencies:
            for dep in task.dependencies:
                if dep != task.id:  # Self-dependency handled separately
                    raise WorkflowError(
                        f"Task '{task.id}' has dependency on non-existent task '{dep}'",
                        ErrorType.VALIDATION,
                        Phase.REGISTRATION,
                        {"task_id": task.id, "missing_dependency": dep},
                    )
                else:
                    # Self-dependency is a cycle
                    raise WorkflowError(
                        f"Circular dependency detected: task '{task.id}' depends on itself",
                        ErrorType.VALIDATION,
                        Phase.REGISTRATION,
                        {"cycle": [task.id]},
                    )
        logger.debug("topological_sort_tasks: Single task, returning as-is")
        return tasks

    # Build task map for O(1) lookup
    task_map: dict[str, TaskDefinition] = {t.id: t for t in tasks}

    # Validate all dependencies exist
    _validate_dependencies(task_map)

    # Build adjacency list and compute in-degrees
    graph, in_degree = _build_dependency_graph(task_map)

    # Run Kahn's algorithm with priority tiebreaker
    sorted_ids = _topological_sort_with_priority(graph, in_degree, task_map)

    # Convert IDs back to TaskDefinition objects
    result = [task_map[task_id] for task_id in sorted_ids]

    logger.info(
        "topological_sort_tasks: Sorted %d tasks -> %s",
        len(tasks),
        [t.id for t in result],
    )

    return result


def _validate_dependencies(task_map: dict[str, "TaskDefinition"]) -> None:
    """Validate that all dependencies reference existing tasks.

    Args:
        task_map: Mapping of task ID to TaskDefinition

    Raises:
        WorkflowError: If a task references a non-existent dependency
    """
    for task_id, task in task_map.items():
        for dep in task.dependencies:
            if dep not in task_map:
                raise WorkflowError(
                    f"Task '{task_id}' has dependency on non-existent task '{dep}'",
                    ErrorType.VALIDATION,
                    Phase.REGISTRATION,
                    {"task_id": task_id, "missing_dependency": dep},
                )


def _build_dependency_graph(
    task_map: dict[str, "TaskDefinition"],
) -> tuple[dict[str, list[str]], dict[str, int]]:
    """Build adjacency list and in-degree map from task definitions.

    The graph represents which tasks depend on which other tasks:
    - If task B depends on task A, then graph[A] contains B
    - in_degree[B] is incremented

    Args:
        task_map: Mapping of task ID to TaskDefinition

    Returns:
        Tuple of (adjacency_list, in_degree_map)
        - adjacency_list[task_id] = list of tasks that depend on task_id
        - in_degree_map[task_id] = number of dependencies for task_id

    Example:
        If task_002 depends on task_001:
        - graph["task_001"] = ["task_002"]
        - in_degree["task_001"] = 0
        - in_degree["task_002"] = 1
    """
    # Initialize adjacency list and in-degree for all tasks
    graph: dict[str, list[str]] = {task_id: [] for task_id in task_map}
    in_degree: dict[str, int] = dict.fromkeys(task_map, 0)

    # Build edges: if B depends on A, add edge A -> B
    for task_id, task in task_map.items():
        # Use set to handle duplicate dependencies
        seen_deps: set[str] = set()
        for dep in task.dependencies:
            if dep in seen_deps:
                logger.debug(
                    "Skipping duplicate dependency: %s -> %s",
                    dep,
                    task_id,
                )
                continue
            seen_deps.add(dep)

            # dep must exist (validated earlier) but check anyway
            if dep in task_map:
                graph[dep].append(task_id)
                in_degree[task_id] += 1

    logger.debug(
        "_build_dependency_graph: Built graph with %d nodes",
        len(graph),
    )

    return graph, in_degree


def _topological_sort_with_priority(
    graph: dict[str, list[str]],
    in_degree: dict[str, int],
    task_map: dict[str, "TaskDefinition"],
) -> list[str]:
    """Run Kahn's algorithm with priority as tiebreaker.

    Uses a min-heap to select the next task based on priority when
    multiple tasks have in_degree = 0.

    Args:
        graph: Adjacency list (task_id -> list of dependent task_ids)
        in_degree: In-degree for each task
        task_map: Mapping of task ID to TaskDefinition (for priority lookup)

    Returns:
        List of task IDs in topological order

    Raises:
        WorkflowError: If circular dependencies are detected
            (some tasks remain with in_degree > 0 after processing)
    """
    # Priority queue: (priority, task_id)
    # Python heapq is a min-heap, so lower priority comes first
    heap: list[tuple[int, str]] = []

    # Initialize heap with all tasks having in_degree = 0
    for task_id, degree in in_degree.items():
        if degree == 0:
            priority = task_map[task_id].priority
            heapq.heappush(heap, (priority, task_id))

    result: list[str] = []
    processed_count = 0

    while heap:
        # Pop task with lowest priority (tiebreaker for same dependency level)
        priority, task_id = heapq.heappop(heap)
        result.append(task_id)
        processed_count += 1

        # Reduce in_degree for all dependents
        for dependent in graph[task_id]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                dep_priority = task_map[dependent].priority
                heapq.heappush(heap, (dep_priority, dependent))

    # Check for cycle: if we didn't process all tasks, there's a cycle
    total_tasks = len(task_map)
    if processed_count != total_tasks:
        # Find tasks in the cycle (those with remaining in_degree > 0)
        remaining = [tid for tid, deg in in_degree.items() if deg > 0]

        logger.error(
            "Circular dependency detected among tasks: %s",
            remaining,
        )

        raise WorkflowError(
            f"Circular dependency detected among tasks: {remaining}",
            ErrorType.VALIDATION,
            Phase.REGISTRATION,
            {"cycle_tasks": remaining, "processed": processed_count},
        )

    return result


def topological_sort_task_dicts(
    task_dicts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Sort dict-based tasks by their dependencies using topological sort.

    This function is for legacy code that uses dict-based task definitions
    instead of TaskDefinition dataclasses.

    Uses Kahn's algorithm with priority as a tiebreaker for tasks
    at the same dependency level.

    Args:
        task_dicts: List of task dicts with keys:
            - task_id: Unique task identifier (string)
            - dependencies: List of task_ids this task depends on
            - priority: Task priority (default: 5)

    Returns:
        List of task dicts in topological order

    Raises:
        WorkflowError: If circular dependencies are detected
            (ErrorType.VALIDATION, Phase.REGISTRATION)
        WorkflowError: If a dependency references a non-existent task

    Example:
        >>> tasks = [
        ...     {"task_id": "A", "dependencies": ["B"], "priority": 1},
        ...     {"task_id": "B", "dependencies": [], "priority": 2},
        ... ]
        >>> sorted_tasks = topological_sort_task_dicts(tasks)
        >>> [t["task_id"] for t in sorted_tasks]
        ['B', 'A']
    """
    if not task_dicts:
        logger.debug("topological_sort_task_dicts: Empty task list, returning empty")
        return []

    # Wrap dicts to provide common interface
    wrappers = [_TaskDictWrapper(t) for t in task_dicts]
    task_map: dict[str, _TaskDictWrapper] = {w.id: w for w in wrappers}
    dict_map: dict[str, dict[str, Any]] = {
        str(t.get("task_id", "")): t for t in task_dicts
    }

    if len(task_dicts) == 1:
        wrapper = wrappers[0]
        # Validate single task doesn't have missing dependencies
        if wrapper.dependencies:
            for dep in wrapper.dependencies:
                if dep != wrapper.id:
                    raise WorkflowError(
                        f"Task '{wrapper.id}' has dependency on non-existent "
                        f"task '{dep}'",
                        ErrorType.VALIDATION,
                        Phase.REGISTRATION,
                        {"task_id": wrapper.id, "missing_dependency": dep},
                    )
                else:
                    raise WorkflowError(
                        f"Circular dependency detected: task '{wrapper.id}' "
                        "depends on itself",
                        ErrorType.VALIDATION,
                        Phase.REGISTRATION,
                        {"cycle": [wrapper.id]},
                    )
        logger.debug("topological_sort_task_dicts: Single task, returning as-is")
        return task_dicts

    # Validate all dependencies exist
    _validate_dependencies_dict(task_map)

    # Build adjacency list and compute in-degrees
    graph, in_degree = _build_dependency_graph_dict(task_map)

    # Run Kahn's algorithm with priority tiebreaker
    sorted_ids = _topological_sort_with_priority_dict(graph, in_degree, task_map)

    # Convert IDs back to original dicts
    result = [dict_map[task_id] for task_id in sorted_ids]

    logger.info(
        "topological_sort_task_dicts: Sorted %d tasks -> %s",
        len(task_dicts),
        sorted_ids,
    )

    return result


def _validate_dependencies_dict(task_map: dict[str, _TaskDictWrapper]) -> None:
    """Validate that all dependencies reference existing tasks.

    Args:
        task_map: Mapping of task ID to _TaskDictWrapper

    Raises:
        WorkflowError: If a task references a non-existent dependency
    """
    for task_id, wrapper in task_map.items():
        for dep in wrapper.dependencies:
            if dep not in task_map:
                raise WorkflowError(
                    f"Task '{task_id}' has dependency on non-existent task '{dep}'",
                    ErrorType.VALIDATION,
                    Phase.REGISTRATION,
                    {"task_id": task_id, "missing_dependency": dep},
                )


def _build_dependency_graph_dict(
    task_map: dict[str, _TaskDictWrapper],
) -> tuple[dict[str, list[str]], dict[str, int]]:
    """Build adjacency list and in-degree map from task dict wrappers.

    Args:
        task_map: Mapping of task ID to _TaskDictWrapper

    Returns:
        Tuple of (adjacency_list, in_degree_map)
    """
    graph: dict[str, list[str]] = {task_id: [] for task_id in task_map}
    in_degree: dict[str, int] = dict.fromkeys(task_map, 0)

    for task_id, wrapper in task_map.items():
        seen_deps: set[str] = set()
        for dep in wrapper.dependencies:
            if dep in seen_deps:
                continue
            seen_deps.add(dep)

            if dep in task_map:
                graph[dep].append(task_id)
                in_degree[task_id] += 1

    return graph, in_degree


def _topological_sort_with_priority_dict(
    graph: dict[str, list[str]],
    in_degree: dict[str, int],
    task_map: dict[str, _TaskDictWrapper],
) -> list[str]:
    """Run Kahn's algorithm with priority as tiebreaker for dict-based tasks.

    Args:
        graph: Adjacency list
        in_degree: In-degree for each task
        task_map: Mapping of task ID to _TaskDictWrapper

    Returns:
        List of task IDs in topological order

    Raises:
        WorkflowError: If circular dependencies are detected
    """
    heap: list[tuple[int, str]] = []

    for task_id, degree in in_degree.items():
        if degree == 0:
            priority = task_map[task_id].priority
            heapq.heappush(heap, (priority, task_id))

    result: list[str] = []
    processed_count = 0

    while heap:
        priority, task_id = heapq.heappop(heap)
        result.append(task_id)
        processed_count += 1

        for dependent in graph[task_id]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                dep_priority = task_map[dependent].priority
                heapq.heappush(heap, (dep_priority, dependent))

    total_tasks = len(task_map)
    if processed_count != total_tasks:
        remaining = [tid for tid, deg in in_degree.items() if deg > 0]

        logger.error(
            "Circular dependency detected among tasks: %s",
            remaining,
        )

        raise WorkflowError(
            f"Circular dependency detected among tasks: {remaining}",
            ErrorType.VALIDATION,
            Phase.REGISTRATION,
            {"cycle_tasks": remaining, "processed": processed_count},
        )

    return result
