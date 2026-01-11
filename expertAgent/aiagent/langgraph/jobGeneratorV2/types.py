"""Type definitions for Job Generator V2.

This module defines all data types used across the job generation workflow:
- Enums for phases and statuses
- Dataclasses for state management
- Input/Output types for each workflow phase
- Pydantic models for LLM response parsing

Issue #342: These types support the new architecture with proper retry management.
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = logging.getLogger(__name__)

# Counter for derived_fields degradation events (Issue #338)
_derived_fields_degradation_count = 0


def get_derived_fields_degradation_count() -> int:
    """Get the current count of derived_fields degradation events."""
    return _derived_fields_degradation_count


def reset_derived_fields_degradation_count() -> None:
    """Reset the degradation counter (for testing)."""
    global _derived_fields_degradation_count
    _derived_fields_degradation_count = 0


class Phase(Enum):
    """Job generation phases.

    The workflow proceeds through these phases in order:
    1. TASK_BREAKDOWN - Decompose requirements into tasks
    2. INTERFACE_DESIGN - Define I/O schemas for tasks
    3. REGISTRATION - Register masters in jobqueue
    4. WORKFLOW_GEN - Generate GraphAI YAML workflow
    """

    TASK_BREAKDOWN = "task_breakdown"
    INTERFACE_DESIGN = "interface_design"
    REGISTRATION = "registration"
    WORKFLOW_GEN = "workflow_gen"


class PhaseStatus(Enum):
    """Status of a phase execution.

    - SUCCESS: Phase completed successfully
    - FAILED: Phase failed (cannot recover)
    - NEEDS_RETRY: Phase needs to be retried (recoverable error)
    - NEEDS_RELAXATION: Requirements need to be relaxed (business constraint)
    """

    SUCCESS = "success"
    FAILED = "failed"
    NEEDS_RETRY = "needs_retry"
    NEEDS_RELAXATION = "needs_relaxation"


@dataclass
class RetryAttempt:
    """Record of a single retry attempt.

    Attributes:
        attempt: The attempt number (1-indexed)
        reason: Why the retry was needed
        error: Error message if any
        timestamp: When the retry occurred
    """

    attempt: int
    reason: str
    error: str | None
    timestamp: datetime


@dataclass
class RetryState:
    """Retry state for a phase.

    Each phase has its own RetryState to prevent the global retry_count bug
    where retry_count was reset incorrectly.

    Attributes:
        count: Current retry count
        max_count: Maximum allowed retries (default: 3)
        history: List of retry attempts
    """

    count: int = 0
    max_count: int = 3
    history: list[RetryAttempt] = field(default_factory=list)

    def can_retry(self) -> bool:
        """Check if more retries are allowed.

        Returns:
            True if count < max_count, False otherwise
        """
        return self.count < self.max_count

    def record(self, reason: str, error: Exception | None = None) -> None:
        """Record a retry attempt.

        Args:
            reason: Why the retry is needed
            error: Optional exception that caused the retry
        """
        self.count += 1
        self.history.append(
            RetryAttempt(
                attempt=self.count,
                reason=reason,
                error=str(error) if error else None,
                timestamp=datetime.now(),
            )
        )


@dataclass
class TaskDefinition:
    """Definition of a single task in the workflow.

    Attributes:
        id: Unique task identifier
        name: Human-readable task name
        description: Detailed description of the task
        task_type: Type of task (e.g., "fetch", "transform", "send")
        recommended_api: API endpoint to use
        priority: Execution priority (1-10)
        dependencies: List of task IDs this task depends on
    """

    id: str
    name: str
    description: str
    task_type: str
    recommended_api: str
    priority: int = 5
    dependencies: list[str] = field(default_factory=list)


@dataclass
class Capability:
    """Available capability from GraphAI or Direct API.

    Attributes:
        name: Capability name
        description: What the capability does
        endpoint: API endpoint
        use_cases: List of use case descriptions (Issue #342)
        method: HTTP method (default: POST) (Issue #342)
        input_schema: Expected input JSON Schema
        output_schema: Expected output JSON Schema
    """

    name: str
    description: str
    endpoint: str
    use_cases: list[str] = field(default_factory=list)
    method: str = "POST"
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)


@dataclass
class InterfaceSchema:
    """JSON Schema definitions for a task's I/O.

    Attributes:
        task_id: ID of the task this schema belongs to
        input_schema: JSON Schema for task input
        output_schema: JSON Schema for task output
        description: Optional description of the interface
    """

    task_id: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    description: str = ""


@dataclass
class RelaxationSuggestion:
    """Suggestion for relaxing infeasible requirements.

    Attributes:
        original_requirement: The original requirement that cannot be met
        suggested_alternative: Suggested alternative approach
        reason: Why relaxation is needed
    """

    original_requirement: str
    suggested_alternative: str
    reason: str


@dataclass
class FeasibilityReport:
    """Report on task feasibility analysis.

    Attributes:
        is_feasible: Whether all tasks are feasible
        infeasible_tasks: List of infeasible task IDs
        recommendations: Recommendations for making tasks feasible
    """

    is_feasible: bool
    infeasible_tasks: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class CompatibilityReport:
    """Report on interface compatibility between tasks.

    Attributes:
        is_compatible: Whether all interfaces are compatible
        issues: List of compatibility issues found
    """

    is_compatible: bool
    issues: list[str] = field(default_factory=list)


@dataclass
class EnrichmentReport:
    """Report on schema enrichment with OpenAPI specs.

    Attributes:
        enriched_count: Number of schemas enriched
        skipped_count: Number of schemas skipped
        details: Details of enrichment process
    """

    enriched_count: int = 0
    skipped_count: int = 0
    details: list[str] = field(default_factory=list)


# ----- Pydantic Models for LLM Response Parsing -----


class DerivedFieldDefinition(BaseModel):
    """Derived field definition for downstream tasks.

    Derived fields are pre-processed data outputs that downstream tasks can use
    directly without additional string manipulation. This supports the
    "Ready-to-Use Output" principle (Issue #337).

    Example:
        email_subject:
            template: "Search results: {query}"
            type: string
            description: "Email subject line"
            source_mapping:
                query: "source.user_input.query"

    Note: extra="ignore" allows LLM to generate additional fields without
    causing validation errors (Issue #342 fix for Gemini structured output).
    """

    model_config = ConfigDict(extra="ignore")

    template: str = Field(
        description="Template string. Use {field_name} to reference source data"
    )
    type: str = Field(default="string", description="Type of the generated value")
    description: str | None = Field(
        default=None, description="Description of the derived field"
    )
    source_mapping: dict[str, str] | None = Field(
        default=None,
        description="Explicit mapping of variable names to source paths (optional)",
    )


class InterfaceSchemaDefinition(BaseModel):
    """Interface schema for a single task (Pydantic model for LLM parsing).

    This is the Pydantic version of InterfaceSchema, used for parsing LLM
    responses with validation.

    Note: extra="ignore" allows LLM to generate additional fields without
    causing validation errors (Issue #342 fix for Gemini structured output).
    """

    model_config = ConfigDict(extra="ignore")

    task_id: str = Field(description="Task ID to define interface for")
    interface_name: str = Field(
        description="Interface name (e.g., 'gmail_search_interface')"
    )
    description: str = Field(description="Description of the interface")
    input_schema: dict[str, Any] = Field(
        description="JSON Schema for input (must be valid JSON Schema)"
    )
    output_schema: dict[str, Any] = Field(
        description="JSON Schema for output (must be valid JSON Schema)"
    )
    derived_fields: dict[str, DerivedFieldDefinition] = Field(
        default_factory=dict,
        description="Derived field definitions for downstream tasks",
    )

    @field_validator("input_schema", "output_schema", mode="before")
    @classmethod
    def parse_json_schema(cls, value: Any) -> dict[str, Any]:
        """Parse JSON string to dict if needed.

        Gemini's structured output may return nested dicts as JSON strings.
        This validator handles both dict and str inputs.
        """
        if isinstance(value, str):
            try:
                parsed: dict[str, Any] = json.loads(value)
                return parsed
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON schema string: {e}") from e
        elif isinstance(value, dict):
            return value
        else:
            raise ValueError(
                f"Expected dict or JSON string, got {type(value).__name__}"
            )

    @field_validator("derived_fields", mode="before")
    @classmethod
    def parse_derived_fields(cls, value: Any) -> dict[str, Any]:
        """Parse derived_fields with graceful degradation.

        Issue #338: If the LLM outputs invalid format, return empty dict
        to allow the workflow to continue.
        """
        global _derived_fields_degradation_count

        if value is None:
            return {}

        if isinstance(value, dict):
            return value

        if isinstance(value, str):
            _derived_fields_degradation_count += 1
            preview = value[:50] if len(value) > 50 else value
            logger.warning(
                "Issue #338: derived_fields received as string (%s...), "
                "using empty dict for graceful degradation. [degradation_count=%d]",
                preview,
                _derived_fields_degradation_count,
            )
            return {}

        _derived_fields_degradation_count += 1
        logger.warning(
            "Issue #338: derived_fields has unexpected type %s, "
            "using empty dict for graceful degradation. [degradation_count=%d]",
            type(value).__name__,
            _derived_fields_degradation_count,
        )
        return {}


class InterfaceSchemaResponse(BaseModel):
    """Interface schema response from LLM.

    This is the container for multiple interface definitions returned by the LLM.
    """

    interfaces: list[InterfaceSchemaDefinition] = Field(
        default_factory=list,
        description="List of interface schemas for all tasks",
    )


class JobBodyParameter(BaseModel):
    """Parameter extracted from user requirements for Job body.

    Issue #321: Parameters extracted from user requirements to be included
    in Job body (e.g., email addresses, search queries).

    Note: extra="ignore" allows LLM to generate additional fields without
    causing validation errors (Issue #342 fix for Gemini structured output).
    """

    model_config = ConfigDict(extra="ignore")

    name: str = Field(description="Parameter name (snake_case)")
    value: str = Field(description="Parameter value from requirements")
    description: str = Field(default="", description="Description of the parameter")


class RecommendedAPI(BaseModel):
    """Recommended API for a task.

    Note: extra="ignore" allows LLM to generate additional fields without
    causing validation errors (Issue #342 fix for Gemini structured output).
    """

    model_config = ConfigDict(extra="ignore")

    api_name: str = Field(description="API name (e.g., 'fetchAgent')")
    endpoint: str | None = Field(
        default=None, description="API endpoint (e.g., '/v1/utility/gmail/send')"
    )
    method: str = Field(default="POST", description="HTTP method")
    reason: str = Field(default="", description="Reason for recommendation")


class TaskBreakdownItem(BaseModel):
    """Single task in the breakdown.

    This Pydantic model represents a task as returned by the LLM.

    Note: extra="ignore" allows LLM to generate additional fields without
    causing validation errors (Issue #342 fix for Gemini structured output).
    """

    model_config = ConfigDict(extra="ignore")

    task_id: str = Field(description="Unique task identifier (e.g., 'task_001')")
    name: str = Field(description="Short task name (e.g., 'Search Gmail')")
    description: str = Field(
        description="Detailed task description with specific requirements"
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of task_ids that must complete before this task",
    )
    expected_output: str = Field(
        default="",
        description="Expected output format and content",
    )
    priority: int = Field(
        default=5, ge=1, le=10, description="Task priority (1=highest, 10=lowest)"
    )
    recommended_apis: list[RecommendedAPI] = Field(
        default_factory=list,
        description="Recommended APIs for this task",
    )


class TaskBreakdownResponse(BaseModel):
    """Task breakdown response from LLM.

    Issue #321: Extended with job_body_parameters field for automatic
    parameter extraction from user requirements.
    """

    tasks: list[TaskBreakdownItem] = Field(
        default_factory=list,
        description="List of tasks decomposed from requirements",
    )
    overall_summary: str = Field(
        default="",
        description="Summary of the entire workflow and task relationships",
    )
    job_body_parameters: list[JobBodyParameter] = Field(
        default_factory=list,
        description="Parameters extracted from user requirements",
    )


# ----- Request/Result Types -----


@dataclass
class JobGenerationRequest:
    """Request to generate a job from requirements.

    Attributes:
        user_requirement: Natural language description of the workflow
        project_id: Project ID for the job
        max_tasks: Maximum number of tasks to generate
        engine: Workflow generation engine ('taskflow' or 'graphai')
            - 'taskflow' (default): Generate TaskFlow V2 JSON workflows
            - 'graphai': Generate GraphAI YAML workflows (legacy)
            Issue #350: Added for engine switching support
    """

    user_requirement: str
    project_id: str
    max_tasks: int = 10
    engine: str = "taskflow"  # Issue #350: Default to TaskFlow V2


@dataclass
class JobGenerationResult:
    """Result of job generation.

    Attributes:
        success: Whether job generation succeeded
        job_id: Generated job ID (if successful)
        job_master_id: Generated JobMaster ID
        task_master_ids: List of generated TaskMaster IDs
        workflow_yaml: Generated GraphAI YAML workflow
        error: Error message if failed
        relaxation_suggestions: Suggestions if requirements need relaxation
        tasks: List of task definitions (Issue #342: V2 adapter task_breakdown support)
        interfaces: Interface schemas keyed by task_id (Issue #342: V2 adapter support)
    """

    success: bool
    job_id: str | None = None
    job_master_id: str | None = None
    task_master_ids: list[str] = field(default_factory=list)
    workflow_yaml: str | None = None
    error: str | None = None
    relaxation_suggestions: list[RelaxationSuggestion] = field(default_factory=list)
    # Issue #342: Add task/interface info for adapter conversion
    tasks: list[TaskDefinition] = field(default_factory=list)
    interfaces: dict[str, InterfaceSchema] = field(default_factory=dict)


# ----- Phase Input Types -----


@dataclass
class TaskBreakdownInput:
    """Input for TaskBreakdownWorkflow.

    Attributes:
        user_requirement: Natural language requirement
        available_capabilities: List of available APIs/capabilities
        max_tasks: Maximum tasks to generate
    """

    user_requirement: str
    available_capabilities: list[Capability] = field(default_factory=list)
    max_tasks: int = 10


@dataclass
class InterfaceDesignInput:
    """Input for InterfaceDesignWorkflow.

    Attributes:
        tasks: List of task definitions
        openapi_specs: OpenAPI specifications for enrichment
    """

    tasks: list[TaskDefinition]
    openapi_specs: dict[str, Any] = field(default_factory=dict)


@dataclass
class RegistrationInput:
    """Input for RegistrationWorkflow.

    Attributes:
        tasks: List of task definitions
        interfaces: Interface schemas for each task
        project_id: Project ID for registration
    """

    tasks: list[TaskDefinition]
    interfaces: dict[str, InterfaceSchema]
    project_id: str


@dataclass
class WorkflowGenInput:
    """Input for WorkflowGenWorkflow.

    Attributes:
        task_master_ids: List of registered TaskMaster IDs
        job_master_id: Registered JobMaster ID
        interfaces: Interface schemas
        task_id_mapping: Optional TaskIdMapping for correct interface lookup
            (Issue #342 Bug #1: Required for proper task_id -> task_master_id mapping)
    """

    task_master_ids: list[str]
    job_master_id: str
    interfaces: dict[str, InterfaceSchema]
    task_id_mapping: "TaskIdMapping | None" = None


# ----- Phase Output Types -----


@dataclass
class TaskBreakdownOutput:
    """Output from TaskBreakdownWorkflow.

    Attributes:
        status: Phase status
        tasks: Generated task definitions
        feasibility_report: Report on task feasibility
        relaxation_suggestions: Suggestions if relaxation needed
    """

    status: PhaseStatus
    tasks: list[TaskDefinition] = field(default_factory=list)
    feasibility_report: FeasibilityReport | None = None
    relaxation_suggestions: list[RelaxationSuggestion] = field(default_factory=list)


@dataclass
class InterfaceDesignOutput:
    """Output from InterfaceDesignWorkflow.

    Attributes:
        status: Phase status
        interfaces: Generated interface schemas
        compatibility_report: Report on interface compatibility
        enrichment_report: Report on OpenAPI enrichment
    """

    status: PhaseStatus
    interfaces: dict[str, InterfaceSchema] = field(default_factory=dict)
    compatibility_report: CompatibilityReport | None = None
    enrichment_report: EnrichmentReport | None = None


@dataclass
class RegistrationOutput:
    """Output from RegistrationWorkflow.

    Attributes:
        status: Phase status
        job_master_id: Registered JobMaster ID
        task_master_ids: List of registered TaskMaster IDs
        interface_master_ids: List of registered InterfaceMaster IDs
        job_id: Registered Job ID
        task_id_to_master_id: Mapping from logical task_id to task_master_id
            (Issue #342 Bug #5: Required for correct interface lookup)
    """

    status: PhaseStatus
    job_master_id: str | None = None
    task_master_ids: list[str] = field(default_factory=list)
    interface_master_ids: list[str] = field(default_factory=list)
    job_id: str | None = None
    task_id_to_master_id: dict[str, str] = field(default_factory=dict)


@dataclass
class TaskIdMapping:
    """Mapping between logical task_ids and task_master_ids.

    Issue #342 Bug #1: This class solves the task_id vs task_master_id confusion.
    Interfaces are keyed by logical task_id (e.g., 'task_001'), but workflows
    use task_master_id (e.g., 'tm_xxx'). This mapping enables correct lookup.

    Attributes:
        logical_to_master: Maps logical task_id -> task_master_id
        master_to_logical: Maps task_master_id -> logical task_id

    Example:
        mapping = TaskIdMapping.from_registration(registration_output)
        # Given task_master_id = 'tm_001', find the interface
        logical_id = mapping.get_logical_id('tm_001')  # Returns 'task_001'
        interface = interfaces.get(logical_id)  # Correct interface lookup
    """

    logical_to_master: dict[str, str] = field(default_factory=dict)
    master_to_logical: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_registration(cls, registration_output: "RegistrationOutput") -> "TaskIdMapping":
        """Create TaskIdMapping from RegistrationOutput.

        Args:
            registration_output: Output from registration workflow with
                task_id_to_master_id mapping

        Returns:
            TaskIdMapping with bidirectional mappings
        """
        mapping = registration_output.task_id_to_master_id
        return cls(
            logical_to_master=dict(mapping),
            master_to_logical={v: k for k, v in mapping.items()},
        )

    def get_master_id(self, logical_id: str) -> str | None:
        """Get task_master_id for a logical task_id.

        Args:
            logical_id: Logical task ID (e.g., 'task_001')

        Returns:
            Task master ID or None if not found
        """
        return self.logical_to_master.get(logical_id)

    def get_logical_id(self, master_id: str) -> str | None:
        """Get logical task_id for a task_master_id.

        Args:
            master_id: Task master ID (e.g., 'tm_001')

        Returns:
            Logical task ID or None if not found
        """
        return self.master_to_logical.get(master_id)


@dataclass
class WorkflowGenOutput:
    """Output from WorkflowGenWorkflow (single task).

    Issue #342 V2 Fix: Now represents a single task's workflow output.

    Attributes:
        status: Phase status
        task_id: Task ID this workflow is for
        workflow_yaml: Generated GraphAI YAML for this task
        test_result: Result of workflow test execution
    """

    status: PhaseStatus
    task_id: str = ""
    workflow_yaml: str | None = None
    test_result: dict[str, Any] | None = None


@dataclass
class WorkflowGenPhaseOutput:
    """Output from WORKFLOW_GEN phase (all tasks).

    Issue #342 V2 Fix: Contains workflow outputs for ALL tasks.

    Attributes:
        status: Overall phase status
        task_workflows: Dict mapping task_id to WorkflowGenOutput
    """

    status: PhaseStatus
    task_workflows: dict[str, WorkflowGenOutput] = field(default_factory=dict)


# ----- Skip Tracking Types (Issue #342 Bug #3) -----


@dataclass
class SkipInfo:
    """Information about a skipped task.

    Issue #342 Bug #3: Used to track when tasks are silently skipped instead
    of just using 'continue' and losing the skip information.

    Attributes:
        task_id: ID of the skipped task
        reason: Why the task was skipped
        phase: Phase where the skip occurred
    """

    task_id: str
    reason: str
    phase: str


@dataclass
class SkipAggregator:
    """Aggregator for tracking skipped tasks.

    Issue #342 Bug #3: Collects all skipped tasks and provides methods to:
    - Track total skip count
    - Check if all tasks were skipped (error condition)
    - Generate summary for logging/error messages

    Example:
        aggregator = SkipAggregator()
        for task in tasks:
            if not task.interface:
                aggregator.add_skip(SkipInfo(
                    task_id=task.id,
                    reason="No interface found",
                    phase="registration",
                ))
                continue
            # process task...

        if aggregator.all_skipped(len(tasks)):
            raise WorkflowError(aggregator.get_summary())
    """

    skips: list[SkipInfo] = field(default_factory=list)

    @property
    def skip_count(self) -> int:
        """Get the number of skipped tasks."""
        return len(self.skips)

    def add_skip(self, skip_info: SkipInfo) -> None:
        """Add a skip record.

        Args:
            skip_info: Information about the skipped task
        """
        self.skips.append(skip_info)
        logger.warning(
            "Task %s skipped in phase %s: %s",
            skip_info.task_id,
            skip_info.phase,
            skip_info.reason,
        )

    def all_skipped(self, total_tasks: int) -> bool:
        """Check if all tasks were skipped.

        Args:
            total_tasks: Total number of tasks in the workflow

        Returns:
            True if skip_count >= total_tasks (all skipped)
        """
        return self.skip_count >= total_tasks

    def get_summary(self) -> str:
        """Get a summary of all skipped tasks for error messages.

        Returns:
            Human-readable summary of all skips
        """
        if not self.skips:
            return "No tasks were skipped."

        lines = [f"Skipped {self.skip_count} task(s):"]
        for skip in self.skips:
            lines.append(f"  - {skip.task_id} ({skip.phase}): {skip.reason}")

        return "\n".join(lines)


# ----- Schema Count Mismatch Evaluation (Issue #342 Bug #6) -----


@dataclass
class SchemaCountMismatchResult:
    """Result of schema count mismatch evaluation.

    Issue #342 Bug #6: Provides threshold-based judgment instead of strict equality.

    Attributes:
        is_acceptable: Whether the mismatch is acceptable (can continue)
        severity: Severity level ('none', 'warning', 'error')
        message: Human-readable message about the mismatch
        expected_count: Expected number of schemas
        actual_count: Actual number of schemas generated
    """

    is_acceptable: bool
    severity: str  # 'none', 'warning', 'error'
    message: str = ""
    expected_count: int = 0
    actual_count: int = 0
