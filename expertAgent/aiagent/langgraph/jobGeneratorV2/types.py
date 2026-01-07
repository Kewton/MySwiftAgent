"""Type definitions for Job Generator V2.

This module defines all data types used across the job generation workflow:
- Enums for phases and statuses
- Dataclasses for state management
- Input/Output types for each workflow phase
- Pydantic models for LLM response parsing

Issue #342: These types support the new architecture with proper retry management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import logging
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
        input_schema: Expected input JSON Schema
        output_schema: Expected output JSON Schema
    """

    name: str
    description: str
    endpoint: str
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
    """

    model_config = ConfigDict(extra="forbid")

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
    """

    model_config = ConfigDict(extra="forbid")

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
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Parameter name (snake_case)")
    value: str = Field(description="Parameter value from requirements")
    description: str = Field(default="", description="Description of the parameter")


class RecommendedAPI(BaseModel):
    """Recommended API for a task."""

    model_config = ConfigDict(extra="forbid")

    api_name: str = Field(description="API name (e.g., 'fetchAgent')")
    endpoint: str | None = Field(
        default=None, description="API endpoint (e.g., '/v1/utility/gmail/send')"
    )
    method: str = Field(default="POST", description="HTTP method")
    reason: str = Field(default="", description="Reason for recommendation")


class TaskBreakdownItem(BaseModel):
    """Single task in the breakdown.

    This Pydantic model represents a task as returned by the LLM.
    """

    model_config = ConfigDict(extra="forbid")

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
    """

    user_requirement: str
    project_id: str
    max_tasks: int = 10


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
    """

    success: bool
    job_id: str | None = None
    job_master_id: str | None = None
    task_master_ids: list[str] = field(default_factory=list)
    workflow_yaml: str | None = None
    error: str | None = None
    relaxation_suggestions: list[RelaxationSuggestion] = field(default_factory=list)


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
    """

    task_master_ids: list[str]
    job_master_id: str
    interfaces: dict[str, InterfaceSchema]


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
    """

    status: PhaseStatus
    job_master_id: str | None = None
    task_master_ids: list[str] = field(default_factory=list)
    interface_master_ids: list[str] = field(default_factory=list)
    job_id: str | None = None


@dataclass
class WorkflowGenOutput:
    """Output from WorkflowGenWorkflow.

    Attributes:
        status: Phase status
        workflow_yaml: Generated GraphAI YAML
        test_result: Result of workflow test execution
    """

    status: PhaseStatus
    workflow_yaml: str | None = None
    test_result: dict[str, Any] | None = None
