"""Job Analyzer Node for 3-Phase Architecture.

Issue #359 Iteration 2 Task 1.2: Merged TASK_BREAKDOWN + INTERFACE_DESIGN.

This node performs task breakdown and interface design in a single LLM call,
producing UnifiedTaskIdentifier-compatible output.

Key features:
- Single LLM call for efficiency
- Task_id-based references (no indices)
- Interfaces defined alongside tasks
- Job body parameters extraction
"""

import logging
from typing import Any

from pydantic import BaseModel, Field

from ..types import UnifiedTaskIdentifier

logger = logging.getLogger(__name__)


class JobParameter(BaseModel):
    """Parameter extracted from user requirements for Job body.

    Attributes:
        name: Parameter name (snake_case)
        value: Parameter value from requirements
        description: Description of the parameter
    """

    name: str = Field(description="Parameter name (snake_case)")
    value: str = Field(description="Parameter value from requirements")
    description: str = Field(default="", description="Description of the parameter")


class InterfaceDefinition(BaseModel):
    """Interface definition for a task.

    Attributes:
        input_schema: JSON Schema for task input
        output_schema: JSON Schema for task output
        description: Human-readable description
        derived_fields: Optional derived field definitions
    """

    input_schema: dict[str, Any] = Field(description="JSON Schema for task input")
    output_schema: dict[str, Any] = Field(description="JSON Schema for task output")
    description: str = Field(default="", description="Interface description")
    derived_fields: dict[str, Any] = Field(
        default_factory=dict,
        description="Derived field definitions for downstream tasks",
    )


class AnalyzedTask(BaseModel):
    """Task definition from job analysis.

    Contains both task breakdown and interface design information.

    Attributes:
        task_id: Unique task identifier (e.g., 'task_001')
        name: Human-readable task name
        description: Detailed task description
        task_type: Type of task (fetch, transform, send, etc.)
        recommended_api: Recommended API endpoint
        dependencies: List of task_ids this task depends on
        input_schema: JSON Schema for task input
        output_schema: JSON Schema for task output
        priority: Task priority (1=highest, 10=lowest)
    """

    task_id: str = Field(description="Unique task identifier (e.g., 'task_001')")
    name: str = Field(description="Human-readable task name")
    description: str = Field(description="Detailed task description")
    task_type: str = Field(description="Type of task (fetch, transform, send)")
    recommended_api: str = Field(description="Recommended API endpoint")
    dependencies: list[str] = Field(
        default_factory=list, description="List of task_ids this task depends on"
    )
    input_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema for task input"
    )
    output_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema for task output"
    )
    priority: int = Field(default=5, ge=1, le=10, description="Task priority")

    def to_unified_identifier(self) -> UnifiedTaskIdentifier:
        """Convert to UnifiedTaskIdentifier for workflow tracking.

        Returns:
            UnifiedTaskIdentifier with task_id set
        """
        return UnifiedTaskIdentifier(task_id=self.task_id)


class JobAnalysisResponse(BaseModel):
    """Response from job analysis containing tasks and interfaces.

    This is the output of the merged TASK_BREAKDOWN + INTERFACE_DESIGN phase.

    Attributes:
        tasks: List of analyzed tasks with embedded interface info
        interfaces: Interface definitions keyed by task_id
        job_body_parameters: Parameters extracted from user requirements
        overall_summary: Summary of the workflow
    """

    tasks: list[AnalyzedTask] = Field(
        default_factory=list, description="List of analyzed tasks"
    )
    interfaces: dict[str, InterfaceDefinition] = Field(
        default_factory=dict, description="Interface definitions keyed by task_id"
    )
    job_body_parameters: list[JobParameter] = Field(
        default_factory=list, description="Parameters extracted from requirements"
    )
    overall_summary: str = Field(
        default="", description="Summary of the entire workflow"
    )

    def get_task_identifiers(self) -> list[UnifiedTaskIdentifier]:
        """Get UnifiedTaskIdentifier list for all tasks.

        Returns:
            List of UnifiedTaskIdentifier objects
        """
        return [task.to_unified_identifier() for task in self.tasks]


class JobAnalysisInput(BaseModel):
    """Input for job analysis.

    Attributes:
        user_requirement: Natural language requirement
        max_tasks: Maximum number of tasks to generate
        retry_feedback: Optional feedback from previous failed attempt
        available_apis: Optional list of available APIs
    """

    user_requirement: str = Field(description="Natural language requirement")
    max_tasks: int = Field(default=10, description="Maximum tasks to generate")
    retry_feedback: str | None = Field(
        default=None, description="Feedback from previous failed attempt"
    )
    available_apis: list[str] = Field(
        default_factory=list, description="List of available API endpoints"
    )


# System prompt for job analysis
JOB_ANALYSIS_SYSTEM_PROMPT = """You are an expert workflow designer. Analyze the user's requirement and produce:

1. **Tasks**: Break down the requirement into discrete tasks. Each task should:
   - Have a unique task_id (e.g., task_001, task_002)
   - Be atomic and focused on a single responsibility
   - Reference dependencies using task_id (NOT indices)
   - Include input/output JSON schemas

2. **Interfaces**: Define clear input/output schemas for each task.

3. **Parameters**: Extract any specific values from the requirement (emails, queries, etc.)

## Rules:
- Use task_id for ALL references (dependencies MUST use task_id like "task_001")
- NEVER use indices or positions (e.g., "depends on task 0" is WRONG)
- Tasks should be ordered by dependency (independent tasks first)
- Each task's output_schema should match the input_schema of dependent tasks

## Output Format:
Provide a JSON response with:
- tasks: Array of task definitions
- interfaces: Object mapping task_id to interface definition
- job_body_parameters: Array of extracted parameters
- overall_summary: Brief workflow summary
"""


async def analyze_job(
    input_data: JobAnalysisInput,
    llm_client: Any | None = None,
) -> JobAnalysisResponse:
    """Analyze job requirements and produce task breakdown with interfaces.

    This function performs merged TASK_BREAKDOWN + INTERFACE_DESIGN in one call.

    Args:
        input_data: Job analysis input with user requirement
        llm_client: Optional LLM client (for testing)

    Returns:
        JobAnalysisResponse with tasks, interfaces, and parameters
    """
    logger.info("Analyzing job requirement: %s...", input_data.user_requirement[:100])

    # Build user prompt
    user_prompt_parts = [
        f"## User Requirement\n{input_data.user_requirement}",
        f"\n## Constraints\n- Maximum {input_data.max_tasks} tasks",
    ]

    if input_data.available_apis:
        user_prompt_parts.append(
            f"\n## Available APIs\n{', '.join(input_data.available_apis)}"
        )

    if input_data.retry_feedback:
        user_prompt_parts.append(
            f"\n## Previous Attempt Feedback (MUST FIX)\n{input_data.retry_feedback}"
        )

    user_prompt = "\n".join(user_prompt_parts)

    # If no LLM client provided, return empty response (for testing)
    if llm_client is None:
        logger.warning("No LLM client provided, returning empty response")
        return JobAnalysisResponse(
            tasks=[],
            interfaces={},
            job_body_parameters=[],
            overall_summary="No LLM client provided",
        )

    # Call LLM with structured output
    try:
        response: JobAnalysisResponse = await llm_client(
            system_prompt=JOB_ANALYSIS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            response_model=JobAnalysisResponse,
        )

        logger.info(
            "Job analysis complete: %d tasks, %d interfaces",
            len(response.tasks),
            len(response.interfaces),
        )

        return response

    except Exception as e:
        logger.error("Job analysis failed: %s", e)
        raise


# Export
__all__ = [
    "analyze_job",
    "JobAnalysisInput",
    "JobAnalysisResponse",
    "AnalyzedTask",
    "InterfaceDefinition",
    "JobParameter",
    "JOB_ANALYSIS_SYSTEM_PROMPT",
]
