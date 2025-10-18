"""Job interface validation service.

This service validates interface compatibility between consecutive Tasks in a Job.
It checks if Task A's output interface is compatible with Task B's input interface
using containment-based compatibility checking (考慮①).
"""

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.interface_master import InterfaceMaster
from app.models.job import Job
from app.models.task import Task
from app.models.task_master import TaskMaster
from app.services.interface_validator import InterfaceValidator

logger = logging.getLogger(__name__)


class JobInterfaceValidationResult:
    """Result of Job interface validation."""

    def __init__(self) -> None:
        """Initialize validation result."""
        self.is_valid: bool = True
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.task_interfaces: list[dict[str, Any]] = []
        self.compatibility_checks: list[dict[str, Any]] = []

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "task_interfaces": self.task_interfaces,
            "compatibility_checks": self.compatibility_checks,
        }


class JobInterfaceValidator:
    """Service for validating Job interface compatibility."""

    @staticmethod
    async def validate_job_interfaces(
        db: AsyncSession, job_id: str
    ) -> JobInterfaceValidationResult:
        """
        Validate interface compatibility for all consecutive Tasks in a Job.

        This method:
        1. Loads Job and its Tasks (ordered by order field)
        2. For each Task, loads its TaskMaster and associated Interfaces
        3. Checks interface compatibility between consecutive Tasks
        4. Returns validation result with detailed error/warning messages

        考慮①対応: Uses containment-based compatibility checking where
        Task B's input properties must be contained in Task A's output.

        考慮②対応: If Job has no master_id (masterless execution),
        validation is still performed on the Task sequence.

        Args:
            db: Database session
            job_id: Job ID to validate

        Returns:
            JobInterfaceValidationResult with validation status and details

        Example:
            >>> result = await JobInterfaceValidator.validate_job_interfaces(db, "j_XXX")
            >>> if not result.is_valid:
            ...     print(result.errors)
        """
        result = JobInterfaceValidationResult()

        # Load Job
        job = await db.get(Job, job_id)
        if not job:
            result.is_valid = False
            result.errors.append(f"Job not found: {job_id}")
            return result

        # Load Tasks ordered by order field
        tasks_query = (
            select(Task)
            .where(Task.job_id == job_id)
            .order_by(Task.order)
            .join(TaskMaster, Task.master_id == TaskMaster.id)
        )
        tasks_result = await db.scalars(tasks_query)
        tasks = list(tasks_result.all())

        if not tasks:
            result.warnings.append(f"Job {job_id} has no tasks")
            return result

        if len(tasks) == 1:
            result.warnings.append(
                "Job has only one task, no compatibility check needed"
            )

        # Load TaskMaster and Interface information for each Task
        task_info_list = []
        for task in tasks:
            task_master = await db.get(TaskMaster, task.master_id)
            if not task_master:
                result.is_valid = False
                result.errors.append(
                    f"TaskMaster not found for Task {task.id} (master_id={task.master_id})"
                )
                continue

            # Load input interface
            input_interface = None
            if task_master.input_interface_id:
                input_interface = await db.get(
                    InterfaceMaster, task_master.input_interface_id
                )
                if not input_interface:
                    result.warnings.append(
                        f"Task {task.order} ({task_master.name}): "
                        f"Input interface not found: {task_master.input_interface_id}"
                    )

            # Load output interface
            output_interface = None
            if task_master.output_interface_id:
                output_interface = await db.get(
                    InterfaceMaster, task_master.output_interface_id
                )
                if not output_interface:
                    result.warnings.append(
                        f"Task {task.order} ({task_master.name}): "
                        f"Output interface not found: {task_master.output_interface_id}"
                    )

            task_info = {
                "task_id": task.id,
                "task_order": task.order,
                "task_master_id": task.master_id,
                "task_master_name": task_master.name,
                "input_interface_id": task_master.input_interface_id,
                "input_interface_name": input_interface.name
                if input_interface
                else None,
                "output_interface_id": task_master.output_interface_id,
                "output_interface_name": (
                    output_interface.name if output_interface else None
                ),
                "input_interface": input_interface,
                "output_interface": output_interface,
            }
            task_info_list.append(task_info)

            # Add to result
            result.task_interfaces.append(
                {
                    "task_order": task.order,
                    "task_master_name": task_master.name,
                    "input_interface": (
                        input_interface.name if input_interface else None
                    ),
                    "output_interface": (
                        output_interface.name if output_interface else None
                    ),
                }
            )

        # Check compatibility between consecutive Tasks
        for i in range(len(task_info_list) - 1):
            task_a = task_info_list[i]
            task_b = task_info_list[i + 1]

            check_result = {
                "task_a_order": task_a["task_order"],
                "task_a_name": task_a["task_master_name"],
                "task_b_order": task_b["task_order"],
                "task_b_name": task_b["task_master_name"],
                "is_compatible": False,
                "missing_properties": [],
            }

            # Skip if either task has no interface defined
            if not task_a["output_interface"] or not task_b["input_interface"]:
                check_result["is_compatible"] = None  # Unknown compatibility
                if not task_a["output_interface"]:
                    result.warnings.append(
                        f"Task {task_a['task_order']} ({task_a['task_master_name']}) "
                        f"has no output interface, cannot validate compatibility with Task {task_b['task_order']}"
                    )
                if not task_b["input_interface"]:
                    result.warnings.append(
                        f"Task {task_b['task_order']} ({task_b['task_master_name']}) "
                        f"has no input interface, cannot validate compatibility with Task {task_a['task_order']}"
                    )
                result.compatibility_checks.append(check_result)
                continue

            # Perform containment-based compatibility check (考慮①)
            task_a_output: InterfaceMaster = task_a["output_interface"]  # type: ignore[assignment]
            task_b_input: InterfaceMaster = task_b["input_interface"]  # type: ignore[assignment]
            output_schema = task_a_output.output_schema
            input_schema = task_b_input.input_schema

            if not output_schema or not input_schema:
                result.warnings.append(
                    f"Task {task_a['task_order']} → Task {task_b['task_order']}: "
                    f"Missing schema definition"
                )
                check_result["is_compatible"] = None
                result.compatibility_checks.append(check_result)
                continue

            is_compatible, missing_props = (
                InterfaceValidator.check_output_contains_input_properties(
                    output_schema, input_schema
                )
            )

            check_result["is_compatible"] = is_compatible
            check_result["missing_properties"] = missing_props

            if not is_compatible:
                result.is_valid = False
                error_msg = (
                    f"Incompatible interfaces: Task {task_a['task_order']} "
                    f"({task_a['task_master_name']}, output={task_a['output_interface_name']}) → "
                    f"Task {task_b['task_order']} ({task_b['task_master_name']}, "
                    f"input={task_b['input_interface_name']})"
                )
                result.errors.append(error_msg)

                for missing_prop in missing_props:
                    result.errors.append(f"  - {missing_prop}")

            result.compatibility_checks.append(check_result)

        logger.info(
            f"Job {job_id} interface validation: "
            f"valid={result.is_valid}, "
            f"errors={len(result.errors)}, "
            f"warnings={len(result.warnings)}"
        )

        return result
