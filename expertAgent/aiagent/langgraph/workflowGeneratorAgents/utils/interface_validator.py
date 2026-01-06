"""Interface validation utilities for task chain compatibility.

This module provides functions to validate interface compatibility
between consecutive tasks in a task chain.

Issue #338: Task chain interface contract enforcement.
"""

from typing import Any

from pydantic import BaseModel


class InterfaceIssue(BaseModel):
    """Represents an interface compatibility issue."""

    field: str
    issue_type: str  # "missing_required", "type_mismatch", "field_not_provided"
    message: str
    severity: str = "error"  # "error" or "warning"


class InterfaceValidationResult(BaseModel):
    """Result of interface validation."""

    is_compatible: bool
    issues: list[InterfaceIssue]

    def __bool__(self) -> bool:
        """Allow result to be used in boolean context."""
        return self.is_compatible


def validate_interface_compatibility(
    prev_output: dict[str, Any],
    next_input: dict[str, Any],
) -> InterfaceValidationResult:
    """Validate that previous task's output matches next task's input.

    This function checks that:
    1. All required fields in next_input are provided by prev_output
    2. Field types are compatible between output and input

    Args:
        prev_output: Previous task's output_interface
        next_input: Next task's input_interface

    Returns:
        InterfaceValidationResult with compatibility status and issues

    Example:
        >>> prev_output = {
        ...     "schema": {
        ...         "properties": {
        ...             "results": {"type": "array"},
        ...             "total": {"type": "integer"}
        ...         }
        ...     }
        ... }
        >>> next_input = {
        ...     "schema": {
        ...         "properties": {
        ...             "results": {"type": "array"}
        ...         },
        ...         "required": ["results"]
        ...     }
        ... }
        >>> result = validate_interface_compatibility(prev_output, next_input)
        >>> result.is_compatible
        True
    """
    issues: list[InterfaceIssue] = []

    # Extract schema properties
    prev_schema = prev_output.get("schema", {})
    next_schema = next_input.get("schema", {})

    prev_props = prev_schema.get("properties", {})
    next_props = next_schema.get("properties", {})
    next_required = next_schema.get("required", [])

    # Check required fields are provided
    for field in next_required:
        if field not in prev_props:
            issues.append(
                InterfaceIssue(
                    field=field,
                    issue_type="missing_required",
                    message=f"Required field '{field}' is not provided by previous task output",
                    severity="error",
                )
            )

    # Check type compatibility for common fields
    for field, next_field_schema in next_props.items():
        if field in prev_props:
            prev_type = prev_props[field].get("type")
            next_type = next_field_schema.get("type")

            if prev_type and next_type and prev_type != next_type:
                # Check for compatible types
                if not _are_types_compatible(prev_type, next_type):
                    issues.append(
                        InterfaceIssue(
                            field=field,
                            issue_type="type_mismatch",
                            message=(
                                f"Type mismatch for field '{field}': "
                                f"output type '{prev_type}' != input type '{next_type}'"
                            ),
                            severity="error",
                        )
                    )
        elif field not in next_required:
            # Optional field not provided - warning
            issues.append(
                InterfaceIssue(
                    field=field,
                    issue_type="field_not_provided",
                    message=f"Optional field '{field}' is not provided by previous task output",
                    severity="warning",
                )
            )

    # Determine if compatible (no errors)
    has_errors = any(issue.severity == "error" for issue in issues)

    return InterfaceValidationResult(
        is_compatible=not has_errors,
        issues=issues,
    )


def _are_types_compatible(prev_type: str, next_type: str) -> bool:
    """Check if two JSON schema types are compatible.

    Args:
        prev_type: Output field type
        next_type: Input field type

    Returns:
        True if types are compatible
    """
    # Exact match
    if prev_type == next_type:
        return True

    # Number/integer compatibility
    if {prev_type, next_type} == {"number", "integer"}:
        return True

    # Any/object compatibility (object can accept any structured data)
    if next_type == "object" and prev_type in ("object", "array"):
        return True

    return False


def validate_task_chain_interfaces(
    tasks: list[dict[str, Any]],
) -> list[tuple[int, int, InterfaceValidationResult]]:
    """Validate interfaces for all consecutive task pairs in a chain.

    Args:
        tasks: List of task dictionaries with input_interface and output_interface

    Returns:
        List of (prev_task_index, next_task_index, validation_result) tuples
        Only includes pairs with issues.
    """
    results: list[tuple[int, int, InterfaceValidationResult]] = []

    for i in range(len(tasks) - 1):
        prev_task = tasks[i]
        next_task = tasks[i + 1]

        prev_output = prev_task.get("output_interface", {})
        next_input = next_task.get("input_interface", {})

        result = validate_interface_compatibility(prev_output, next_input)

        if not result.is_compatible or result.issues:
            results.append((i, i + 1, result))

    return results


def format_interface_issues(
    issues: list[InterfaceIssue],
) -> str:
    """Format interface issues as a human-readable string.

    Args:
        issues: List of interface issues

    Returns:
        Formatted string describing all issues
    """
    if not issues:
        return "No interface issues found."

    lines = []
    errors = [i for i in issues if i.severity == "error"]
    warnings = [i for i in issues if i.severity == "warning"]

    if errors:
        lines.append(f"Errors ({len(errors)}):")
        for issue in errors:
            lines.append(f"  - [{issue.issue_type}] {issue.message}")

    if warnings:
        lines.append(f"Warnings ({len(warnings)}):")
        for issue in warnings:
            lines.append(f"  - [{issue.issue_type}] {issue.message}")

    return "\n".join(lines)
