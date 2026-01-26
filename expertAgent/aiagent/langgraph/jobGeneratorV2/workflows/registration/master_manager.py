"""Master manager sub-workflow for Registration.

This module provides the MasterManagerSubWorkflow that creates:
1. InterfaceMasters for each task's input/output schemas
2. TaskMasters for each task
3. JobMaster for the workflow
4. JobMasterTask associations linking tasks to the workflow

Issue #342 Phase D.1: Migrated logic from jobTaskGeneratorAgents/nodes/master_creation.py
without importing from the old code.

Issue #342: Now uses actual jobqueue API calls instead of placeholders.

Issue #402: Changed task sorting from priority-based to dependency-based
topological sort using Kahn's algorithm.

Issue #403: Extended _build_body_template to support multi-dependency field aggregation.
- Added _find_field_source method for field-to-task resolution
- body_template.inputs now supports dict format with field-level references

Key design decisions:
- Uses ExecutionContext for API access (dependency injection)
- Uses JobqueueClient for actual API calls to jobqueue service
- All external API calls create real resources in jobqueue
- Uses topological sort for dependency-respecting execution order
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from aiagent.langgraph.jobGeneratorV2.protocols import (
    ErrorType,
    WorkflowError,
)
from aiagent.langgraph.jobGeneratorV2.types_old import (
    InterfaceSchema,
    Phase,
    TaskDefinition,
)
from aiagent.langgraph.jobGeneratorV2.utils.topological_sort import (
    topological_sort_tasks,
)
from aiagent.langgraph.jobGeneratorV2.validators.body_template_validator import (
    BodyTemplateValidator,
    GraphAIValidationStrategy,
    TaskFlowValidationStrategy,
)
from aiagent.langgraph.jobTaskGeneratorAgents.utils.jobqueue_client import (
    JobqueueClient,
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

    Issue #350: Added engine parameter for GraphAI/TaskFlow URL switching.
    - graphai: Uses /api/v1/myagent endpoint
    - taskflow: Uses /api/v2/workflows endpoint

    Example:
        manager = MasterManagerSubWorkflow(engine="taskflow")
        result = await manager.create_masters(tasks, interfaces, project_id, context)
    """

    def __init__(
        self,
        graphai_server_url: str = "http://localhost:8005",
        myswiftagentcore_url: str = "http://localhost:8006",
        default_timeout_sec: int = 60,
        jobqueue_client: JobqueueClient | None = None,
        engine: str = "taskflow",
    ) -> None:
        """Initialize MasterManagerSubWorkflow.

        Args:
            graphai_server_url: Base URL for GraphAI server
            myswiftagentcore_url: Base URL for mySwiftAgentCore (Issue #390)
            default_timeout_sec: Default timeout for tasks
            jobqueue_client: Optional pre-configured jobqueue client
            engine: Workflow engine type ('graphai' or 'taskflow')
        """
        self._graphai_server_url = graphai_server_url
        self._myswiftagentcore_url = myswiftagentcore_url
        self._default_timeout_sec = default_timeout_sec
        self._jobqueue_client = jobqueue_client
        self._engine = engine

        # Issue #358: Initialize BodyTemplateValidator with engine-specific strategy
        strategy = (
            TaskFlowValidationStrategy()
            if engine == "taskflow"
            else GraphAIValidationStrategy()
        )
        self._body_template_validator = BodyTemplateValidator(strategy=strategy)

    def _get_task_url(self) -> str:
        """Get the task URL based on engine type.

        Issue #350: Different engines use different endpoints.
        Issue #390: TaskFlow uses mySwiftAgentCore for execution.

        Returns:
            Task execution URL
        """
        if self._engine == "taskflow":
            # Issue #390: Use mySwiftAgentCore for TaskFlow execution
            return f"{self._myswiftagentcore_url}/api/v1/taskflow/execute"
        else:
            return f"{self._graphai_server_url}/api/v1/myagent"

    def _get_job_url(self) -> str:
        """Get the job URL based on engine type.

        Issue #350: Different engines use different endpoints.
        Issue #390: TaskFlow uses mySwiftAgentCore for execution.

        Returns:
            Job execution URL
        """
        if self._engine == "taskflow":
            # Issue #390: Use mySwiftAgentCore for TaskFlow execution
            return f"{self._myswiftagentcore_url}/api/v1/taskflow/execute"
        else:
            return f"{self._graphai_server_url}/api/v1/myagent"

    def _get_jobqueue_client(self, context: "ExecutionContext") -> JobqueueClient:
        """Get or create JobqueueClient.

        Args:
            context: Execution context (may have client in storage)

        Returns:
            JobqueueClient instance
        """
        # Use pre-configured client if available
        if self._jobqueue_client is not None:
            return self._jobqueue_client

        # Check context storage for client
        if context.storage.jobqueue_client is not None:
            return context.storage.jobqueue_client

        # Create new client (uses JOBQUEUE_API_URL env var or default)
        logger.info("Creating new JobqueueClient for master creation")
        return JobqueueClient()

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

        # Issue #402: Sort tasks by dependencies using topological sort
        # Within same dependency level, tasks are sub-sorted by priority
        sorted_tasks = topological_sort_tasks(tasks)

        # Issue #408: Get user_input_schema for validation
        # The first task receives user input directly, so its input_schema
        # reflects what the user provides. Used to validate field names.
        user_input_schema = self._get_user_input_schema(sorted_tasks, interfaces)
        logger.debug("Issue #408: Retrieved user_input_schema for validation")

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

        # Issue #403: Build task_order_map for multi-dependency body_template generation
        task_order_map: dict[str, int] = {
            task.id: order for order, task in enumerate(sorted_tasks)
        }

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
            # Issue #403: Pass task, interfaces, and task_order_map for multi-dependency support
            # Issue #408: Pass user_input_schema for fallback field validation
            body_template = self._build_body_template(
                order=order,
                task=task,
                interfaces=interfaces,
                task_order_map=task_order_map,
                user_input_schema=user_input_schema,
            )

            # Issue #358: Validate body_template before creating TaskMaster
            if task.id in interfaces:
                interface = interfaces[task.id]
                # Collect output schemas from all preceding tasks
                preceding_output_schemas = [
                    interfaces[t.id].output_schema
                    for t in sorted_tasks[:order]
                    if t.id in interfaces
                ]
                # Issue #408: Pass user_input_schema for user input field validation
                validation_result = self._body_template_validator.validate(
                    body_template=body_template,
                    input_schema=interface.input_schema,
                    task_count=order,
                    task_output_schemas=preceding_output_schemas,
                    user_input_schema=user_input_schema,
                )
                if not validation_result.is_valid:
                    error_messages = "; ".join(
                        f"{e.error_type}: {e.message}" for e in validation_result.errors
                    )
                    raise WorkflowError(
                        f"Body template validation failed for task '{task.name}': "
                        f"{error_messages}",
                        ErrorType.VALIDATION,
                        Phase.REGISTRATION,
                    )
                if validation_result.warnings:
                    for warning in validation_result.warnings:
                        logger.warning(
                            "Body template warning for task '%s': %s",
                            task.name,
                            warning.message,
                        )

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
        # Issue #391: Pass project_id to include in JobMaster.body
        job_master = await self._create_job_master(
            user_requirement=context.user_requirement,
            context=context,
            project_id=project_id,
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

    def _find_field_source(
        self,
        field: str,
        dependencies: list[str],
        interfaces: dict[str, InterfaceSchema],
        task_order_map: dict[str, int],
    ) -> str | None:
        """Find the source task for a required field.

        Issue #403: Determine which dependency task outputs the requested field.
        Uses dependencies list order for priority when multiple tasks output same field.

        Args:
            field: Field name to find
            dependencies: List of dependency task IDs (in order of priority)
            interfaces: Interface schemas for all tasks
            task_order_map: Mapping from task_id to execution order

        Returns:
            Task ID that outputs the field, or None if not found
        """
        for dep_task_id in dependencies:
            if dep_task_id not in interfaces:
                continue

            output_schema = interfaces[dep_task_id].output_schema
            properties = output_schema.get("properties", {})

            if field in properties:
                logger.debug(
                    "Issue #403: Field '%s' found in task '%s' output",
                    field,
                    dep_task_id,
                )
                return dep_task_id

        return None

    def _build_body_template(
        self,
        order: int,
        task: TaskDefinition | None = None,
        interfaces: dict[str, InterfaceSchema] | None = None,
        task_order_map: dict[str, int] | None = None,
        user_input_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build body template for task chaining.

        Issue #342 Phase 1: Fix body_template double nesting.
        Issue #350: Engine-aware body_template for TaskFlow V2.
        Issue #391: Use {{job.body.project}} instead of {{job.project}}.
        Issue #403: Support multi-dependency field aggregation.

        For GraphAI engine:
        - user_input references {{job.body.user_input}} directly
        - job_params references {{job.body}} for static parameters

        For TaskFlow engine:
        - workflow: placeholder (updated after workflow generation)
        - inputs: {{job.body}} for workflow inputs OR dict of field references
        - project: {{job.body.project}} for secrets resolution

        Args:
            order: Task execution order (0-indexed)
            task: Optional TaskDefinition for interface-aware template generation
            interfaces: Optional interface schemas for field resolution
            task_order_map: Optional mapping from task_id to execution order
            user_input_schema: Optional user input schema for validating fallback
                field references (Issue #408)

        Returns:
            Body template dict
        """
        if self._engine == "taskflow":
            # Issue #350: TaskFlow V2 body_template format
            # Issue #390: Use "workflow" field name (mySwiftAgentCore API expects "workflow")
            # Issue #391: Use {{job.body.project}} (Job model has no project attribute)
            # workflow will be set to placeholder - updated after workflow generation
            # Issue #409: Independent tasks (dependencies=[]) use user_input directly
            if order == 0 or (task is not None and not task.dependencies):
                # Issue #396: Use user_input instead of entire body for inputs
                # mySwiftAgentCore expects inputs to match workflow's input_schema
                # job.body = {"project": "...", "user_input": {"keyword": "...", ...}}
                # workflow expects inputs = {"keyword": "...", ...}
                # Issue #409: Any independent task (dependencies=[]) uses user_input
                return {
                    "workflow": "__PENDING__",  # Updated by workflow_gen phase
                    "inputs": "{{job.body.user_input}}",  # Issue #396: User input data
                    "project": "{{job.body.project}}",  # Issue #391: From job.body
                }

            # Issue #403: Check if we have interface info for multi-dependency support
            if (
                task is not None
                and interfaces is not None
                and task_order_map is not None
                and task.dependencies
                and task.id in interfaces
            ):
                # Build field-level inputs dict
                # Issue #408: Pass user_input_schema for fallback field validation
                return self._build_multi_dependency_template(
                    task=task,
                    interfaces=interfaces,
                    task_order_map=task_order_map,
                    user_input_schema=user_input_schema,
                )

            # Legacy behavior: subsequent tasks receive previous task's output
            return {
                "workflow": "__PENDING__",
                "inputs": f"{{{{tasks[{order - 1}].output_data}}}}",
                "project": "{{job.body.project}}",  # Issue #391: From job.body
            }
        else:
            # GraphAI (legacy) body_template format
            if order == 0:
                # Issue #342: First task extracts user_input from job.body to avoid
                # double nesting. job.body = {"user_input": {...}}, so we access
                # job.body.user_input directly for the user_input field.
                return {
                    "user_input": "{{job.body.user_input}}",
                    "job_params": "{{job.body}}",
                }
            else:
                # Subsequent tasks use previous task's output
                return {
                    "user_input": f"{{{{tasks[{order - 1}].output_data}}}}",
                    "job_params": "{{job.body}}",
                }

    def _build_multi_dependency_template(
        self,
        task: TaskDefinition,
        interfaces: dict[str, InterfaceSchema],
        task_order_map: dict[str, int],
        user_input_schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build body template with multi-dependency field aggregation.

        Issue #403: Creates inputs dict where each field references its source task.
        Issue #408: Added user_input_schema for field validation on fallback.

        Args:
            task: Task definition with dependencies
            interfaces: Interface schemas for all tasks
            task_order_map: Mapping from task_id to execution order
            user_input_schema: Optional user input schema for validating fallback
                field references. When provided, logs warning if fallback field
                does not exist in user_input_schema.

        Returns:
            Body template with field-level input references
        """
        input_schema = interfaces[task.id].input_schema
        required_fields = list(input_schema.get("properties", {}).keys())

        # Issue #403: System fields that are handled separately (not part of inputs)
        system_fields = {"project"}

        # Issue #408: Get valid user input fields for validation
        valid_user_input_fields = set()
        if user_input_schema is not None:
            valid_user_input_fields = set(
                user_input_schema.get("properties", {}).keys()
            )

        inputs: dict[str, str] = {}

        for field_name in required_fields:
            # Skip system-injected fields
            if field_name in system_fields:
                logger.debug(
                    "Issue #403: Skipping system field '%s' in inputs for task '%s'",
                    field_name,
                    task.id,
                )
                continue

            source_task_id = self._find_field_source(
                field=field_name,
                dependencies=task.dependencies,
                interfaces=interfaces,
                task_order_map=task_order_map,
            )

            if source_task_id is not None:
                source_order = task_order_map[source_task_id]
                inputs[field_name] = (
                    f"{{{{tasks[{source_order}].output_data.{field_name}}}}}"
                )
            else:
                # Fallback to user_input
                logger.warning(
                    "Issue #403: Field '%s' not found in dependencies for task '%s', "
                    "fallback to user_input",
                    field_name,
                    task.id,
                )

                # Issue #408: Check if fallback field exists in user_input_schema
                if user_input_schema is not None:
                    if field_name not in valid_user_input_fields:
                        logger.warning(
                            "Issue #408: Fallback field '%s' not found in "
                            "user_input_schema. Available fields: %s. "
                            "The LLM may have changed the field name.",
                            field_name,
                            sorted(valid_user_input_fields),
                        )

                inputs[field_name] = f"{{{{job.body.user_input.{field_name}}}}}"

        return {
            "workflow": "__PENDING__",
            "inputs": inputs,
            "project": "{{job.body.project}}",
        }

    def _get_user_input_schema(
        self,
        sorted_tasks: list[TaskDefinition],
        interfaces: dict[str, InterfaceSchema],
    ) -> dict[str, Any] | None:
        """Get merged user input schema from all independent tasks.

        Issue #408: The first task receives user input directly, so its input_schema
        reflects what the user provides. This is used to validate field names in
        subsequent tasks.

        Issue #409: Merge input schemas from all independent tasks (dependencies=[])
        to ensure all user input fields are captured.

        Args:
            sorted_tasks: Tasks sorted by topological order
            interfaces: Interface schemas for all tasks

        Returns:
            Merged input schema from all independent tasks, or None if not available

        Raises:
            ValueError: If same field has different types in different tasks
        """
        if not sorted_tasks:
            return None

        merged_properties: dict[str, Any] = {}
        merged_required: list[str] = []

        for task in sorted_tasks:
            # Issue #409: Only merge schemas from independent tasks (dependencies=[])
            if task.dependencies:
                continue

            if task.id not in interfaces:
                logger.warning(
                    "Issue #409: Independent task '%s' not found in interfaces",
                    task.id,
                )
                continue

            schema = interfaces[task.id].input_schema
            if not schema:
                continue

            props = schema.get("properties", {})
            required = schema.get("required", [])

            for field_name, field_schema in props.items():
                if field_name in merged_properties:
                    # Issue #409: Check for type conflicts
                    existing_type = merged_properties[field_name].get("type")
                    new_type = field_schema.get("type")

                    if existing_type != new_type:
                        # Issue #409 AC-7: Type mismatch raises ValueError
                        raise ValueError(
                            f"Field '{field_name}' has conflicting types: "
                            f"'{existing_type}' vs '{new_type}' (task: {task.name})"
                        )

                    # Issue #409 AC-6: Type match logs warning with both type info
                    logger.warning(
                        "Field '%s' from task '%s' overrides previous definition. "
                        "Existing type: %s, New type: %s",
                        field_name,
                        task.name,
                        existing_type,
                        new_type,
                    )

                merged_properties[field_name] = field_schema

            # Merge required fields
            for req_field in required:
                if req_field not in merged_required:
                    merged_required.append(req_field)

        if not merged_properties:
            return None

        return {
            "type": "object",
            "properties": merged_properties,
            "required": merged_required,
        }

    async def _create_interface_master(
        self,
        task_id: str,
        name: str,
        schema: dict[str, Any],
        is_input: bool,
        context: "ExecutionContext",
    ) -> str:
        """Create an InterfaceMaster via jobqueue API.

        Args:
            task_id: Associated task ID
            name: Interface name
            schema: JSON Schema definition
            is_input: Whether this is an input interface
            context: Execution context

        Returns:
            Created InterfaceMaster ID
        """
        client = self._get_jobqueue_client(context)
        interface_type = "input" if is_input else "output"

        logger.info(
            "Creating InterfaceMaster via API: %s (%s)",
            name,
            interface_type,
        )

        try:
            # For input interface: use schema as input_schema, empty for output
            # For output interface: use schema as output_schema, empty for input
            if is_input:
                result = await client.create_interface_master(
                    name=name,
                    description=f"Input interface for task {task_id}",
                    input_schema=schema,
                    output_schema={},  # Input interface has no output
                    created_by="job_generator_v2",
                )
            else:
                result = await client.create_interface_master(
                    name=name,
                    description=f"Output interface for task {task_id}",
                    input_schema={},  # Output interface has no input
                    output_schema=schema,
                    created_by="job_generator_v2",
                )

            interface_id = result["id"]
            logger.info(
                "Created InterfaceMaster: %s -> %s",
                name,
                interface_id,
            )
            return interface_id

        except Exception as e:
            logger.error(
                "Failed to create InterfaceMaster %s: %s",
                name,
                str(e),
            )
            raise WorkflowError(
                f"Failed to create InterfaceMaster {name}: {e}",
                ErrorType.API,
                Phase.REGISTRATION,
            ) from e

    async def _create_task_master(
        self,
        task: TaskDefinition,
        input_interface_id: str,
        output_interface_id: str,
        body_template: dict[str, Any],
        context: "ExecutionContext",
    ) -> str:
        """Create a TaskMaster via jobqueue API.

        Args:
            task: Task definition
            input_interface_id: Input InterfaceMaster ID
            output_interface_id: Output InterfaceMaster ID
            body_template: Body template for request
            context: Execution context

        Returns:
            Created TaskMaster ID
        """
        client = self._get_jobqueue_client(context)

        logger.info(
            "Creating TaskMaster via API: %s -> %s",
            task.name,
            task.recommended_api,
        )

        try:
            # Build task URL based on engine type
            # Issue #350: Use _get_task_url() for engine-specific endpoint
            task_url = self._get_task_url()

            result = await client.create_task_master(
                name=task.name,
                description=task.description or f"Task: {task.name}",
                method="POST",
                url=task_url,
                input_interface_id=input_interface_id,
                output_interface_id=output_interface_id,
                body_template=body_template,
                timeout_sec=self._default_timeout_sec,
                created_by="job_generator_v2",
            )

            task_master_id = result["id"]
            logger.info(
                "Created TaskMaster: %s -> %s",
                task.name,
                task_master_id,
            )
            return task_master_id

        except Exception as e:
            logger.error(
                "Failed to create TaskMaster %s: %s",
                task.name,
                str(e),
            )
            raise WorkflowError(
                f"Failed to create TaskMaster {task.name}: {e}",
                ErrorType.API,
                Phase.REGISTRATION,
            ) from e

    async def _create_job_master(
        self,
        user_requirement: str,
        context: "ExecutionContext",
        project_id: str,
    ) -> JobMasterInfo:
        """Create a JobMaster via jobqueue API.

        Issue #391: Added project_id parameter to set body.project.

        Args:
            user_requirement: Original user requirement
            context: Execution context
            project_id: Project ID for secrets resolution

        Returns:
            Created JobMasterInfo

        Raises:
            WorkflowError: If master creation fails or project_id is invalid
        """
        # Issue #391: Input validation - project_id is required
        if not project_id or not project_id.strip():
            raise WorkflowError(
                "project_id is required for JobMaster creation",
                ErrorType.VALIDATION,
                Phase.REGISTRATION,
            )

        client = self._get_jobqueue_client(context)

        job_name = f"Job: {user_requirement[:50]}"
        job_description = f"Auto-generated job from requirement: {user_requirement}"
        # Issue #350: Use _get_job_url() for engine-specific endpoint
        job_url = self._get_job_url()
        job_timeout_sec = 300

        # Issue #391: Initialize body with project
        body: dict[str, Any] = {"project": project_id.strip()}

        logger.info(
            "Creating JobMaster via API: %s (project: %s)",
            job_name,
            project_id,
        )
        logger.debug(
            "JobMaster body: %s",
            body,
        )

        try:
            result = await client.create_job_master(
                name=job_name,
                description=job_description,
                method="POST",
                url=job_url,
                timeout_sec=job_timeout_sec,
                created_by="job_generator_v2",
                body=body,  # Issue #391: Include project in body
            )

            job_master_id = result["id"]
            logger.info(
                "Created JobMaster: %s -> %s (body.project: %s)",
                job_name,
                job_master_id,
                project_id,
            )

            return JobMasterInfo(
                id=job_master_id,
                name=job_name,
                method="POST",
                url=job_url,
                timeout_sec=job_timeout_sec,
            )

        except Exception as e:
            logger.error(
                "Failed to create JobMaster %s: %s",
                job_name,
                str(e),
            )
            raise WorkflowError(
                f"Failed to create JobMaster: {e}",
                ErrorType.API,
                Phase.REGISTRATION,
            ) from e

    async def _create_job_master_task(
        self,
        job_master_id: str,
        task_master_id: str,
        order: int,
        context: "ExecutionContext",
    ) -> str:
        """Create a JobMasterTask association via jobqueue API.

        Args:
            job_master_id: JobMaster ID
            task_master_id: TaskMaster ID
            order: Execution order
            context: Execution context

        Returns:
            Created JobMasterTask ID
        """
        client = self._get_jobqueue_client(context)

        logger.info(
            "Creating JobMasterTask via API: %s <- %s (order=%d)",
            job_master_id,
            task_master_id,
            order,
        )

        try:
            result = await client.add_task_to_workflow(
                job_master_id=job_master_id,
                task_master_id=task_master_id,
                order=order,
                is_required=True,
                max_retries=3,
            )

            job_master_task_id = result["id"]
            logger.info(
                "Created JobMasterTask: %s (order=%d)",
                job_master_task_id,
                order,
            )
            return job_master_task_id

        except Exception as e:
            logger.error(
                "Failed to create JobMasterTask for %s: %s",
                task_master_id,
                str(e),
            )
            raise WorkflowError(
                f"Failed to create JobMasterTask: {e}",
                ErrorType.API,
                Phase.REGISTRATION,
            ) from e
