"""Task Dependency Validator.

Issue #359: Validates task dependencies for circular references and missing tasks.

This module provides:
- TaskDependencyValidator: Validates task dependency graph
- DependencyValidationResult: Result with detailed error information

Key features:
- Circular reference detection (direct and indirect)
- Missing dependency detection
- Topological sort for execution order
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DependencyValidationResult:
    """Result of dependency validation.

    Attributes:
        is_valid: Whether the dependency graph is valid
        errors: List of error messages
        circular_references: List of circular reference paths
        missing_dependencies: List of missing dependency task_ids
        execution_order: Topologically sorted task order (if valid)
    """

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    circular_references: list[list[str]] = field(default_factory=list)
    missing_dependencies: list[str] = field(default_factory=list)
    execution_order: list[str] = field(default_factory=list)

    def to_error_message(self) -> str:
        """Generate a human-readable error message.

        Returns:
            Formatted error message string
        """
        if self.is_valid:
            return ""

        lines = ["Task dependency validation failed:"]

        for error in self.errors:
            lines.append(f"  - {error}")

        if self.circular_references:
            lines.append("\nCircular references found:")
            for cycle in self.circular_references:
                cycle_str = " -> ".join(cycle)
                lines.append(f"  - {cycle_str}")

        if self.missing_dependencies:
            lines.append("\nMissing dependencies:")
            for dep in self.missing_dependencies:
                lines.append(f"  - {dep}")

        return "\n".join(lines)


class TaskDependencyValidator:
    """Validates task dependency graphs.

    Checks for:
    - Circular references (direct and indirect)
    - Self-references
    - References to non-existent tasks
    - Provides topological sort order

    Example:
        validator = TaskDependencyValidator()
        result = validator.validate(tasks)
        if not result.is_valid:
            print(result.to_error_message())
    """

    def validate(self, tasks: list[dict[str, Any]]) -> DependencyValidationResult:
        """Validate task dependencies.

        Args:
            tasks: List of task dictionaries with task_id and dependencies

        Returns:
            DependencyValidationResult with validation details
        """
        if not tasks:
            return DependencyValidationResult(is_valid=True)

        # Build data structures
        task_ids = set()
        dependencies: dict[str, list[str]] = {}

        for task in tasks:
            task_id = task.get("task_id")
            deps = task.get("dependencies", [])

            if task_id:
                task_ids.add(task_id)
                dependencies[task_id] = deps

        # Collect all errors
        errors: list[str] = []
        circular_refs: list[list[str]] = []
        missing_deps: list[str] = []

        # Check for missing dependencies
        for task_id, deps in dependencies.items():
            for dep in deps:
                if dep not in task_ids:
                    missing_deps.append(dep)
                    errors.append(
                        f"Task '{task_id}' depends on non-existent task '{dep}'"
                    )

        # Check for circular references
        cycle = self._find_cycle(dependencies, task_ids)
        if cycle:
            circular_refs.append(cycle)
            cycle_str = " -> ".join(cycle)
            errors.append(f"Circular reference detected: {cycle_str}")

        # If valid, compute execution order
        execution_order: list[str] = []
        if not errors:
            execution_order = self._topological_sort(dependencies, task_ids)

        is_valid = len(errors) == 0

        return DependencyValidationResult(
            is_valid=is_valid,
            errors=errors,
            circular_references=circular_refs,
            missing_dependencies=list(set(missing_deps)),
            execution_order=execution_order,
        )

    def _find_cycle(
        self, dependencies: dict[str, list[str]], task_ids: set[str]
    ) -> list[str] | None:
        """Find a cycle in the dependency graph using DFS.

        Args:
            dependencies: Map of task_id to list of dependencies
            task_ids: Set of all task IDs

        Returns:
            List of task_ids forming a cycle, or None if no cycle
        """
        # Track visited state: 0=unvisited, 1=visiting, 2=visited
        state: dict[str, int] = dict.fromkeys(task_ids, 0)
        # Track path for cycle reconstruction
        path: list[str] = []

        def dfs(node: str) -> list[str] | None:
            if state[node] == 1:
                # Found cycle - extract it from path
                cycle_start = path.index(node)
                return path[cycle_start:] + [node]

            if state[node] == 2:
                return None

            state[node] = 1
            path.append(node)

            for dep in dependencies.get(node, []):
                if dep in task_ids:  # Only check existing tasks
                    result = dfs(dep)
                    if result:
                        return result

            state[node] = 2
            path.pop()
            return None

        for task_id in task_ids:
            if state[task_id] == 0:
                result = dfs(task_id)
                if result:
                    return result

        return None

    def _topological_sort(
        self, dependencies: dict[str, list[str]], task_ids: set[str]
    ) -> list[str]:
        """Perform topological sort on the dependency graph.

        Args:
            dependencies: Map of task_id to list of dependencies
            task_ids: Set of all task IDs

        Returns:
            List of task_ids in topologically sorted order

        Note:
            Assumes no cycles exist (should be checked first)
        """
        # Calculate in-degree for each node
        in_degree: dict[str, int] = dict.fromkeys(task_ids, 0)
        for deps in dependencies.values():
            for dep in deps:
                if dep in in_degree:
                    # Note: We count how many tasks depend on each task
                    pass

        # Build reverse dependency map (who depends on whom)
        dependents: dict[str, list[str]] = defaultdict(list)
        for task_id, deps in dependencies.items():
            for dep in deps:
                if dep in task_ids:
                    dependents[dep].append(task_id)
                    in_degree[task_id] = in_degree.get(task_id, 0) + 1

        # Reset in_degree properly
        in_degree = dict.fromkeys(task_ids, 0)
        for task_id, deps in dependencies.items():
            for dep in deps:
                if dep in task_ids:
                    in_degree[task_id] = in_degree.get(task_id, 0) + 1

        # Find all nodes with in_degree 0 (no dependencies)
        queue: list[str] = [
            task_id for task_id, degree in in_degree.items() if degree == 0
        ]
        queue.sort()  # Ensure deterministic order

        result: list[str] = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            # Reduce in_degree for dependents
            for dependent in dependents[current]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)
                    queue.sort()

        return result


# Export
__all__ = [
    "TaskDependencyValidator",
    "DependencyValidationResult",
]
