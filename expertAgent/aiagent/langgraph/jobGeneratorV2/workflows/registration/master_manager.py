"""Master manager sub-workflow for Registration.

This module provides the MasterManagerSubWorkflow that creates:
1. InterfaceMasters for each task's input/output schemas
2. TaskMasters for each task
3. JobMaster for the workflow
4. JobMasterTask associations linking tasks to the workflow

Issue #342 Phase D.1: Migrated logic from jobTaskGeneratorAgents/nodes/master_creation.py
without importing from the old code.

Key design decisions:
- Uses ExecutionContext for API access (dependency injection)
- Does NOT import from langgraph or old jobTaskGeneratorAgents
- All external API calls are abstracted through context.storage
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from aiagent.langgraph.jobGeneratorV2.protocols import (
    ErrorType,
    WorkflowError,
)
from aiagent.langgraph.jobGeneratorV2.types import (
    InterfaceSchema,
    Phase,
    TaskDefinition,
)

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext

logger = logging.getLogger(__name__)


@dataclass
class InterfaceMasterInfo:
    """Information about a created InterfaceMaster.

    Attributes:
        id: InterfaceMaster ID
        name: Interface name
        task_id: Associated task ID
        is_input: Whether this is an input interface
    """

    id: str
    name: str
    task_id: str
    is_input: bool


@dataclass
class TaskMasterInfo:
    """Information about a created TaskMaster.

    Attributes:
        id: TaskMaster ID
        name: Task name
        task_id: Original task ID from TaskDefinition
        order: Execution order in workflow
        input_interface_id: Input InterfaceMaster ID
        output_interface_id: Output InterfaceMaster ID
    """

    id: str
    name: str
    task_id: str
    order: int
    input_interface_id: str
    output_interface_id: str


@dataclass
class JobMasterInfo:
    """Information about a created JobMaster.

    Attributes:
        id: JobMaster ID
        name: Job name
        method: HTTP method
        url: Target URL
        timeout_sec: Timeout in seconds
    """

    id: str
    name: str
    method: str
    url: str
    timeout_sec: int


@dataclass
class MasterCreationResult:
    """Result from master creation sub-workflow.

    Attributes:
        job_master: Created JobMaster info
        task_masters: List of created TaskMaster info
        interface_masters: List of created InterfaceMaster info
        job_master_task_ids: List of created JobMasterTask association IDs
    """

    job_master: JobMasterInfo
    task_masters: list[TaskMasterInfo] = field(default_factory=list)
    interface_masters: list[InterfaceMasterInfo] = field(default_factory=list)
    job_master_task_ids: list[str] = field(default_factory=list)


class MasterManagerSubWorkflow:
    """Sub-workflow for creating and managing masters.

    This sub-workflow handles the creation of:
    1. InterfaceMasters for each task's I/O schemas
    2. TaskMasters for each task
    3. JobMaster for the overall workflow
    4. JobMasterTask associations

    Example:
        manager = MasterManagerSubWorkflow()
        result = await manager.create_masters(tasks, interfaces, project_id, context)
    """

    def __init__(
        self,
        graphai_server_url: str = "http://localhost:8005",
        default_timeout_sec: int = 60,
    ) -> None:
        """Initialize MasterManagerSubWorkflow.

        Args:
            graphai_server_url: Base URL for GraphAI server
            default_timeout_sec: Default timeout for tasks
        """
        self._graphai_server_url = graphai_server_url
        self._default_timeout_sec = default_timeout_sec

    async def create_masters(
        self,
        tasks: list[TaskDefinition],
        interfaces: dict[str, InterfaceSchema],
        project_id: str,
        context: "ExecutionContext",
    ) -> MasterCreationResult:
        """Create all masters for the workflow.

        Args:
            tasks: List of task definitions
            interfaces: Interface schemas for each task
            project_id: Project ID for registration
            context: Execution context with API access

        Returns:
            MasterCreationResult with created master information

        Raises:
            WorkflowError: If master creation fails
        """
        logger.info(
            "Starting master creation for job %s with %d tasks",
            context.job_id,
            len(tasks),
        )

        if not tasks:
            raise WorkflowError(
                "No tasks provided for master creation",
                ErrorType.VALIDATION,
                Phase.REGISTRATION,
            )

        if not interfaces:
            raise WorkflowError(
                "No interfaces provided for master creation",
                ErrorType.VALIDATION,
                Phase.REGISTRATION,
            )

        # Sort tasks by priority for execution order
        sorted_tasks = sorted(tasks, key=lambda t: t.priority)

        # Step 1: Create InterfaceMasters
        interface_masters: list[InterfaceMasterInfo] = []
        task_interface_mapping: dict[str, dict[str, str]] = {}

        for task in sorted_tasks:
            if task.id not in interfaces:
                logger.warning("No interface found for task %s, skipping", task.id)
                continue

            interface = interfaces[task.id]

            # Create input InterfaceMaster
            input_interface_id = await self._create_interface_master(
                task_id=task.id,
                name=f"{task.name}_input",
                schema=interface.input_schema,
                is_input=True,
                context=context,
            )
            interface_masters.append(
                InterfaceMasterInfo(
                    id=input_interface_id,
                    name=f"{task.name}_input",
                    task_id=task.id,
                    is_input=True,
                )
            )

            # Create output InterfaceMaster
            output_interface_id = await self._create_interface_master(
                task_id=task.id,
                name=f"{task.name}_output",
                schema=interface.output_schema,
                is_input=False,
                context=context,
            )
            interface_masters.append(
                InterfaceMasterInfo(
                    id=output_interface_id,
                    name=f"{task.name}_output",
                    task_id=task.id,
                    is_input=False,
                )
            )

            task_interface_mapping[task.id] = {
                "input_id": input_interface_id,
                "output_id": output_interface_id,
            }

        logger.info("Created %d interface masters", len(interface_masters))

        # Step 2: Create TaskMasters with interface chaining
        task_masters: list[TaskMasterInfo] = []
        prev_output_interface_id: str | None = None

        for order, task in enumerate(sorted_tasks):
            if task.id not in task_interface_mapping:
                continue

            mapping = task_interface_mapping[task.id]

            # Apply interface chaining
            if order == 0:
                input_interface_id = mapping["input_id"]
            else:
                # Use previous task's output as this task's input
                input_interface_id = prev_output_interface_id or mapping["input_id"]

            output_interface_id = mapping["output_id"]

            # Build body template for task chaining
            body_template = self._build_body_template(order)

            task_master_id = await self._create_task_master(
                task=task,
                input_interface_id=input_interface_id,
                output_interface_id=output_interface_id,
                body_template=body_template,
                context=context,
            )

            task_masters.append(
                TaskMasterInfo(
                    id=task_master_id,
                    name=task.name,
                    task_id=task.id,
                    order=order,
                    input_interface_id=input_interface_id,
                    output_interface_id=output_interface_id,
                )
            )

            prev_output_interface_id = output_interface_id

        logger.info("Created %d task masters", len(task_masters))

        # Step 3: Create JobMaster
        job_master = await self._create_job_master(
            user_requirement=context.user_requirement,
            context=context,
        )
        logger.info("Created job master: %s", job_master.id)

        # Step 4: Create JobMasterTask associations
        job_master_task_ids: list[str] = []
        for task_master in task_masters:
            assoc_id = await self._create_job_master_task(
                job_master_id=job_master.id,
                task_master_id=task_master.id,
                order=task_master.order,
                context=context,
            )
            job_master_task_ids.append(assoc_id)

        logger.info("Created %d job master task associations", len(job_master_task_ids))

        return MasterCreationResult(
            job_master=job_master,
            task_masters=task_masters,
            interface_masters=interface_masters,
            job_master_task_ids=job_master_task_ids,
        )

    def _build_body_template(self, order: int) -> dict[str, Any]:
        """Build body template for task chaining.

        Args:
            order: Task execution order (0-indexed)

        Returns:
            Body template dict
        """
        if order == 0:
            # First task uses job.body
            return {
                "user_input": "{{job.body}}",
                "job_params": "{{job.body}}",
            }
        else:
            # Subsequent tasks use previous task's output
            return {
                "user_input": f"{{{{tasks[{order - 1}].output_data}}}}",
                "job_params": "{{job.body}}",
            }

    async def _create_interface_master(
        self,
        task_id: str,
        name: str,
        schema: dict[str, Any],
        is_input: bool,
        context: "ExecutionContext",
    ) -> str:
        """Create an InterfaceMaster.

        Args:
            task_id: Associated task ID
            name: Interface name
            schema: JSON Schema definition
            is_input: Whether this is an input interface
            context: Execution context

        Returns:
            Created InterfaceMaster ID
        """
        # Placeholder implementation - will be connected to real API in Phase E
        # For now, generate a unique ID
        interface_type = "input" if is_input else "output"
        placeholder_id = f"im_{task_id}_{interface_type}"

        logger.debug(
            "Creating InterfaceMaster: %s (placeholder: %s)",
            name,
            placeholder_id,
        )

        # In Phase E, this will call:
        # context.storage.jobqueue_client.create_interface_master(...)
        return placeholder_id

    async def _create_task_master(
        self,
        task: TaskDefinition,
        input_interface_id: str,
        output_interface_id: str,
        body_template: dict[str, Any],
        context: "ExecutionContext",
    ) -> str:
        """Create a TaskMaster.

        Args:
            task: Task definition
            input_interface_id: Input InterfaceMaster ID
            output_interface_id: Output InterfaceMaster ID
            body_template: Body template for request
            context: Execution context

        Returns:
            Created TaskMaster ID
        """
        placeholder_id = f"tm_{task.id}"

        logger.debug(
            "Creating TaskMaster: %s -> %s (placeholder: %s)",
            task.name,
            task.recommended_api,
            placeholder_id,
        )

        # In Phase E, this will call:
        # context.storage.jobqueue_client.create_task_master(...)
        return placeholder_id

    async def _create_job_master(
        self,
        user_requirement: str,
        context: "ExecutionContext",
    ) -> JobMasterInfo:
        """Create a JobMaster.

        Args:
            user_requirement: Original user requirement
            context: Execution context

        Returns:
            Created JobMasterInfo
        """
        job_name = f"Job: {user_requirement[:50]}"
        job_url = f"{self._graphai_server_url}/api/v1/myagent"
        placeholder_id = f"jm_{context.job_id}"

        logger.debug(
            "Creating JobMaster: %s (placeholder: %s)",
            job_name,
            placeholder_id,
        )

        # In Phase E, this will call:
        # context.storage.jobqueue_client.create_job_master(...)
        return JobMasterInfo(
            id=placeholder_id,
            name=job_name,
            method="POST",
            url=job_url,
            timeout_sec=300,
        )

    async def _create_job_master_task(
        self,
        job_master_id: str,
        task_master_id: str,
        order: int,
        context: "ExecutionContext",
    ) -> str:
        """Create a JobMasterTask association.

        Args:
            job_master_id: JobMaster ID
            task_master_id: TaskMaster ID
            order: Execution order
            context: Execution context

        Returns:
            Created JobMasterTask ID
        """
        placeholder_id = f"jmt_{job_master_id}_{task_master_id}"

        logger.debug(
            "Creating JobMasterTask: %s <- %s (order=%d, placeholder: %s)",
            job_master_id,
            task_master_id,
            order,
            placeholder_id,
        )

        # In Phase E, this will call:
        # context.storage.jobqueue_client.add_task_to_workflow(...)
        return placeholder_id
