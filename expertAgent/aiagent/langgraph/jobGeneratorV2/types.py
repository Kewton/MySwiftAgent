"""Type definitions for Job Generator V2.

This module defines all data types used across the job generation workflow:
- Enums for phases and statuses
- Dataclasses for state management
- Input/Output types for each workflow phase

Issue #342: These types support the new architecture with proper retry management.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


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
