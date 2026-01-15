"""CompatibilityCheckerSubWorkflow for Job Generator V2.

This module implements the compatibility checking sub-workflow that:
1. Takes generated interfaces and task definitions
2. Validates that dependent tasks have compatible I/O schemas
3. Returns CompatibilityReport with any issues found

Issue #342 Phase C.2: Migrate logic from interface_definition.py validation

Key design decisions:
- Checks output -> input compatibility for dependent tasks
- Validates required fields are present in source schema
- Returns detailed issues for debugging
- Uses ExecutionContext's phase-specific retry state
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from aiagent.langgraph.jobGeneratorV2.types_old import (
    CompatibilityReport,
    InterfaceSchema,
    InterfaceSchemaResponse,
    TaskDefinition,
)

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext

logger = logging.getLogger(__name__)


def validate_interface_response(
    response: InterfaceSchemaResponse | None,
) -> InterfaceSchemaResponse:
    """Ensure the LLM response contains interface definitions.

    Args:
        response: The response to validate

    Returns:
        The validated response

    Raises:
        ValueError: If response is invalid
    """
    if response is None:
        logger.error("LLM structured output returned None for interface definition")
        raise ValueError("Interface definition failed: structured output was empty.")

    if not response.interfaces:
        logger.error("LLM structured output missing interfaces array")
        raise ValueError("Interface definition failed: no interfaces were generated.")

    return response


def _get_output_properties(schema: dict[str, Any]) -> dict[str, Any]:
    """Extract properties from an output schema.

    Args:
        schema: JSON Schema dictionary

    Returns:
        Dict of property names to their definitions
    """
    if not isinstance(schema, dict):
        return {}
    properties: dict[str, Any] = schema.get("properties", {})
    return properties


def _get_required_inputs(schema: dict[str, Any]) -> list[str]:
    """Extract required field names from an input schema.

    Args:
        schema: JSON Schema dictionary

    Returns:
        List of required field names
    """
    if not isinstance(schema, dict):
        return []
    required: list[str] = schema.get("required", [])
    return required


def _check_type_compatibility(
    source_type: str | None,
    target_type: str | None,
) -> bool:
    """Check if source type is compatible with target type.

    Args:
        source_type: Type from source schema
        target_type: Type from target schema

    Returns:
        True if compatible, False otherwise
    """
    if source_type is None or target_type is None:
        # Missing type info - assume compatible
        return True

    if source_type == target_type:
        return True

    # Integer is compatible with number
    if source_type == "integer" and target_type == "number":
        return True

    # Any type can go to any target (permissive matching)
    if source_type == "any" or target_type == "any":
        return True

    return False


def _check_interface_compatibility(
    source_interface: InterfaceSchema,
    target_interface: InterfaceSchema,
    source_task: TaskDefinition,
    target_task: TaskDefinition,
) -> list[str]:
    """Check compatibility between two interfaces.

    Args:
        source_interface: Output interface (from dependency)
        target_interface: Input interface (to dependent task)
        source_task: Source task definition
        target_task: Target task definition

    Returns:
        List of compatibility issues (empty if compatible)
    """
    issues: list[str] = []

    source_output = _get_output_properties(source_interface.output_schema)
    target_input_props = _get_output_properties(target_interface.input_schema)
    target_required = _get_required_inputs(target_interface.input_schema)

    # Check that all required inputs are available from source output
    for required_field in target_required:
        if required_field not in source_output:
            # The required field is not provided by the dependency's output
            # This is an incompatibility - dependent task needs this field
            issues.append(
                f"Task '{target_task.name}' ({target_task.id}) requires field '{required_field}' "
                f"but task '{source_task.name}' ({source_task.id}) does not output it"
            )

    # Check type compatibility for overlapping fields
    for field_name, source_def in source_output.items():
        if field_name in target_input_props:
            target_def = target_input_props[field_name]
            source_type = (
                source_def.get("type") if isinstance(source_def, dict) else None
            )
            target_type = (
                target_def.get("type") if isinstance(target_def, dict) else None
            )

            if not _check_type_compatibility(source_type, target_type):
                issues.append(
                    f"Type mismatch for field '{field_name}' between "
                    f"'{source_task.name}' (outputs {source_type}) and "
                    f"'{target_task.name}' (expects {target_type})"
                )

    return issues


class CompatibilityCheckerSubWorkflow:
    """Sub-workflow for checking interface compatibility.

    This class validates that dependent tasks have compatible I/O schemas,
    ensuring data can flow correctly through the workflow.

    Example:
        checker = CompatibilityCheckerSubWorkflow()
        report = await checker.check(tasks, interfaces, context)
    """

    async def check(
        self,
        tasks: list[TaskDefinition],
        interfaces: dict[str, InterfaceSchema],
        context: "ExecutionContext",
    ) -> CompatibilityReport:
        """Check compatibility between task interfaces.

        Args:
            tasks: List of task definitions
            interfaces: Dict mapping task_id to InterfaceSchema
            context: Execution context

        Returns:
            CompatibilityReport with results
        """
        logger.info(
            "Checking interface compatibility for %d tasks (job %s)",
            len(tasks),
            context.job_id,
        )

        if not interfaces:
            logger.warning("No interfaces provided for compatibility check")
            return CompatibilityReport(
                is_compatible=False,
                issues=["No interfaces generated - cannot verify compatibility"],
            )

        if not tasks:
            return CompatibilityReport(
                is_compatible=True,
                issues=[],
            )

        # Build task lookup
        task_lookup = {t.id: t for t in tasks}
        all_issues: list[str] = []

        # Check each task's dependencies
        for task in tasks:
            if not task.dependencies:
                continue

            target_interface = interfaces.get(task.id)
            if not target_interface:
                all_issues.append(
                    f"Missing interface for task '{task.name}' ({task.id})"
                )
                continue

            for dep_id in task.dependencies:
                source_task = task_lookup.get(dep_id)
                if not source_task:
                    all_issues.append(
                        f"Task '{task.name}' depends on unknown task '{dep_id}'"
                    )
                    continue

                source_interface = interfaces.get(dep_id)
                if not source_interface:
                    all_issues.append(
                        f"Missing interface for dependency '{source_task.name}' ({dep_id})"
                    )
                    continue

                # Check compatibility
                issues = _check_interface_compatibility(
                    source_interface,
                    target_interface,
                    source_task,
                    task,
                )
                all_issues.extend(issues)

        is_compatible = len(all_issues) == 0

        logger.info(
            "Compatibility check complete: %s (issues: %d)",
            "compatible" if is_compatible else "incompatible",
            len(all_issues),
        )

        return CompatibilityReport(
            is_compatible=is_compatible,
            issues=all_issues,
        )
