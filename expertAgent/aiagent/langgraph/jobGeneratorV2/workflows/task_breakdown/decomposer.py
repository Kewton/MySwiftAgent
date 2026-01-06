"""TaskDecomposerSubWorkflow for Job Generator V2.

This module implements the task decomposition sub-workflow that:
1. Takes user requirements as input
2. Uses LLM to decompose into executable tasks
3. Returns a list of TaskDefinition

Issue #342 Phase B.1: Migrate logic from requirement_analysis.py

Key design decisions:
- Uses structured LLM output for reliability
- Validates requirements before processing
- Respects max_tasks limit
- Converts LLM response to internal TaskDefinition type
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiagent.langgraph.jobGeneratorV2.protocols import ErrorType, WorkflowError
from aiagent.langgraph.jobGeneratorV2.types import (
    Phase,
    TaskBreakdownInput,
    TaskDefinition,
)
from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
    TaskBreakdownResponse,
    _build_task_breakdown_system_prompt,
    create_task_breakdown_prompt,
)
from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
    StructuredLLMError,
    invoke_structured_llm,
)

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext

logger = logging.getLogger(__name__)


def _validate_task_breakdown_response(
    response: TaskBreakdownResponse | None,
) -> TaskBreakdownResponse:
    """Validate that the LLM response contains a usable task list.

    Args:
        response: The LLM response to validate

    Returns:
        The validated response

    Raises:
        ValueError: If response is None or missing required fields
    """
    if response is None:
        logger.error("LLM structured output returned None")
        raise ValueError(
            "Task breakdown failed: LLM returned None response. "
            "This may indicate structured output parsing failure."
        )

    if response.tasks is None:
        logger.error("LLM structured output missing 'tasks' field")
        raise ValueError(
            "Task breakdown failed: LLM response missing 'tasks' field. "
            "This may indicate the structured schema was not followed."
        )

    if not response.tasks:
        logger.error("LLM response.tasks is empty - no tasks generated")
        raise ValueError(
            "Task breakdown failed: LLM returned empty task list. "
            "User requirement may be too vague or ambiguous."
        )

    return response


def _convert_to_task_definition(task_item: object) -> TaskDefinition:
    """Convert LLM task item to internal TaskDefinition.

    Args:
        task_item: Task item from LLM response (TaskBreakdownItem)

    Returns:
        TaskDefinition instance
    """
    # Extract recommended API from first recommendation if available
    recommended_api = ""
    if hasattr(task_item, "recommended_apis") and getattr(task_item, "recommended_apis"):
        first_api = getattr(task_item, "recommended_apis")[0]
        if hasattr(first_api, "endpoint"):
            recommended_api = getattr(first_api, "endpoint", "")

    task_id: str = getattr(task_item, "task_id", "")
    task_name: str = getattr(task_item, "name", "")
    task_description: str = getattr(task_item, "description", "")
    task_priority: int = getattr(task_item, "priority", 5)
    task_dependencies: list[str] = getattr(task_item, "dependencies", [])

    return TaskDefinition(
        id=task_id,
        name=task_name,
        description=task_description,
        task_type=_infer_task_type(task_description, recommended_api),
        recommended_api=recommended_api,
        priority=task_priority,
        dependencies=task_dependencies,
    )


def _infer_task_type(description: str, api: str) -> str:
    """Infer task type from description and API.

    Args:
        description: Task description
        api: Recommended API endpoint

    Returns:
        Inferred task type string
    """
    description_lower = description.lower()
    api_lower = api.lower()

    if "gmail" in api_lower:
        if "search" in api_lower:
            return "gmail_search"
        if "send" in api_lower:
            return "email_send"
        return "gmail"

    if "drive" in api_lower:
        return "file_upload"

    if "jsonoutput" in api_lower or "llm" in api_lower:
        return "llm_processing"

    if "text_to_speech" in api_lower:
        return "tts"

    if "google_search" in api_lower:
        return "web_search"

    # Default based on description
    if "search" in description_lower:
        return "search"
    if "send" in description_lower or "email" in description_lower:
        return "notification"
    if "upload" in description_lower:
        return "file_upload"
    if "summarize" in description_lower or "analyze" in description_lower:
        return "llm_processing"

    return "general"


class TaskDecomposerSubWorkflow:
    """Sub-workflow for decomposing user requirements into tasks.

    This class handles the LLM-based decomposition of natural language
    requirements into structured task definitions.

    Example:
        decomposer = TaskDecomposerSubWorkflow()
        tasks = await decomposer.decompose(input_data, context)
    """

    async def decompose(
        self,
        input_data: TaskBreakdownInput,
        context: "ExecutionContext",
    ) -> list[TaskDefinition]:
        """Decompose user requirements into task definitions.

        Args:
            input_data: TaskBreakdownInput with requirements
            context: Execution context with LLM configuration

        Returns:
            List of TaskDefinition

        Raises:
            WorkflowError: If decomposition fails
        """
        logger.info(
            "Starting task decomposition for job %s",
            context.job_id,
        )

        # Validate input
        if not input_data.user_requirement or not input_data.user_requirement.strip():
            raise WorkflowError(
                "User requirement is empty or whitespace only",
                ErrorType.VALIDATION,
                Phase.TASK_BREAKDOWN,
            )

        # Build prompts
        system_prompt = _build_task_breakdown_system_prompt()
        user_prompt = create_task_breakdown_prompt(input_data.user_requirement)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            call_result = await invoke_structured_llm(
                messages=messages,
                response_model=TaskBreakdownResponse,
                context_label="task_decomposer",
                model_env_var="JOB_GENERATOR_REQUIREMENT_ANALYSIS_MODEL",
                default_model=context.llm.model_name,
                validator=_validate_task_breakdown_response,
            )
        except StructuredLLMError as exc:
            logger.error("Task decomposition failed: %s", exc)
            raise WorkflowError(
                f"LLM decomposition failed: {exc}",
                ErrorType.TRANSIENT,
                Phase.TASK_BREAKDOWN,
            ) from exc

        response = call_result.result
        logger.info(
            "Task decomposition produced %d tasks",
            len(response.tasks),
        )

        # Convert to TaskDefinition and respect max_tasks
        tasks = [_convert_to_task_definition(task) for task in response.tasks]

        if len(tasks) > input_data.max_tasks:
            logger.warning(
                "Limiting tasks from %d to max_tasks=%d",
                len(tasks),
                input_data.max_tasks,
            )
            tasks = tasks[: input_data.max_tasks]

        return tasks
