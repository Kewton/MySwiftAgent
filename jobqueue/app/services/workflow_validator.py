"""Workflow validation service for interface compatibility checking."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.interface_master import InterfaceMaster
from app.models.job_master import JobMaster
from app.models.job_master_task import JobMasterTask


class WorkflowValidationError(Exception):
    """Exception raised when workflow validation fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        """Initialize validation error.

        Args:
            message: Error message
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class WorkflowValidator:
    """Service for validating workflow interface compatibility."""

    @staticmethod
    async def validate_workflow_interfaces(
        db: AsyncSession,
        job_master: JobMaster,
    ) -> None:
        """Validate that all tasks in a workflow have compatible interfaces.

        Validation rules:
        1. JobMaster input_interface_id must match first task's input_interface_id
        2. Each task's output_interface_id must match next task's input_interface_id
        3. Last task's output_interface_id must match JobMaster output_interface_id

        Args:
            db: Database session
            job_master: JobMaster to validate

        Raises:
            WorkflowValidationError: If interface compatibility is broken
        """
        # Load workflow tasks in order
        query = (
            select(JobMasterTask)
            .where(JobMasterTask.job_master_id == job_master.id)
            .options(selectinload(JobMasterTask.task_master))
            .order_by(JobMasterTask.order)
        )
        result = await db.execute(query)
        tasks = result.scalars().all()

        if not tasks:
            # No tasks in workflow - skip validation
            return

        # Rule 1: JobMaster input must match first task input
        first_task = tasks[0]
        if job_master.input_interface_id:
            if (
                first_task.task_master.input_interface_id
                != job_master.input_interface_id
            ):
                raise WorkflowValidationError(
                    "JobMaster input interface does not match first task",
                    details={
                        "job_master_input_interface_id": job_master.input_interface_id,
                        "first_task_input_interface_id": first_task.task_master.input_interface_id,
                        "first_task_name": first_task.task_master.name,
                        "first_task_order": first_task.order,
                    },
                )

        # Rule 2: Each task's output must match next task's input
        for i in range(len(tasks) - 1):
            current_task = tasks[i]
            next_task = tasks[i + 1]

            if (
                current_task.task_master.output_interface_id
                != next_task.task_master.input_interface_id
            ):
                raise WorkflowValidationError(
                    f"Interface mismatch between tasks at order {current_task.order} and {next_task.order}",
                    details={
                        "current_task_name": current_task.task_master.name,
                        "current_task_order": current_task.order,
                        "current_task_output_interface_id": current_task.task_master.output_interface_id,
                        "next_task_name": next_task.task_master.name,
                        "next_task_order": next_task.order,
                        "next_task_input_interface_id": next_task.task_master.input_interface_id,
                    },
                )

        # Rule 3: Last task output must match JobMaster output
        last_task = tasks[-1]
        if job_master.output_interface_id:
            if (
                last_task.task_master.output_interface_id
                != job_master.output_interface_id
            ):
                raise WorkflowValidationError(
                    "Last task output interface does not match JobMaster output",
                    details={
                        "job_master_output_interface_id": job_master.output_interface_id,
                        "last_task_output_interface_id": last_task.task_master.output_interface_id,
                        "last_task_name": last_task.task_master.name,
                        "last_task_order": last_task.order,
                    },
                )

    @staticmethod
    async def validate_interface_exists(
        db: AsyncSession,
        interface_id: str,
    ) -> InterfaceMaster:
        """Validate that an interface exists and is active.

        Args:
            db: Database session
            interface_id: Interface ID to validate

        Returns:
            InterfaceMaster: The interface master

        Raises:
            WorkflowValidationError: If interface not found or inactive
        """
        interface = await db.get(InterfaceMaster, interface_id)
        if not interface:
            raise WorkflowValidationError(
                f"Interface not found: {interface_id}",
                details={"interface_id": interface_id},
            )

        if not interface.is_active:
            raise WorkflowValidationError(
                f"Interface is inactive: {interface_id}",
                details={
                    "interface_id": interface_id,
                    "interface_name": interface.name,
                },
            )

        return interface

    @staticmethod
    async def get_workflow_validation_report(
        db: AsyncSession,
        job_master: JobMaster,
    ) -> dict[str, Any]:
        """Get a detailed validation report for a workflow.

        This is a non-throwing version of validate_workflow_interfaces that
        returns a detailed report of the validation status.

        Args:
            db: Database session
            job_master: JobMaster to validate

        Returns:
            dict with validation status and details:
            {
                "is_valid": bool,
                "errors": list[dict],
                "warnings": list[dict],
                "task_chain": list[dict],
            }
        """
        report: dict[str, Any] = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "task_chain": [],
        }

        # Load workflow tasks
        query = (
            select(JobMasterTask)
            .where(JobMasterTask.job_master_id == job_master.id)
            .options(selectinload(JobMasterTask.task_master))
            .order_by(JobMasterTask.order)
        )
        result = await db.execute(query)
        tasks = result.scalars().all()

        if not tasks:
            report["warnings"].append(
                {
                    "type": "empty_workflow",
                    "message": "Workflow has no tasks",
                }
            )
            return report

        # Build task chain for visualization
        for task in tasks:
            report["task_chain"].append(
                {
                    "order": task.order,
                    "task_name": task.task_master.name,
                    "input_interface_id": task.task_master.input_interface_id,
                    "output_interface_id": task.task_master.output_interface_id,
                }
            )

        # Validate using the main validation method
        try:
            await WorkflowValidator.validate_workflow_interfaces(db, job_master)
        except WorkflowValidationError as e:
            report["is_valid"] = False
            report["errors"].append(
                {
                    "type": "interface_mismatch",
                    "message": e.message,
                    "details": e.details,
                }
            )

        return report
