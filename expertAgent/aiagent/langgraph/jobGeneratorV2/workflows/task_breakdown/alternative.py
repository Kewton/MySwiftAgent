"""AlternativeSubWorkflow for Job Generator V2.

This module implements the alternative generation sub-workflow that:
1. Takes infeasible tasks as input
2. Uses LLM to generate alternative tasks using available capabilities
3. Returns alternative tasks or relaxation suggestions

Issue #342 Phase B.3: Generate alternatives for infeasible tasks

Key design decisions:
- Uses LLM for intelligent alternative generation
- Returns RelaxationSuggestion when no alternatives exist
- Maintains task dependencies when creating alternatives
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from aiagent.langgraph.jobGeneratorV2.llm_utils import (
    StructuredLLMError,
    get_callbacks_from_context,
    invoke_structured_llm,
)
from aiagent.langgraph.jobGeneratorV2.types_old import (
    Capability,
    RelaxationSuggestion,
    TaskDefinition,
)

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext

logger = logging.getLogger(__name__)


# Pydantic models for LLM structured output


class AlternativeTaskItem(BaseModel):
    """Alternative task definition from LLM."""

    task_id: str = Field(description="Task ID for alternative (e.g., 'task_001_alt')")
    name: str = Field(description="Task name")
    description: str = Field(description="Task description")
    dependencies: list[str] = Field(
        default_factory=list, description="Task dependencies"
    )
    expected_output: str = Field(description="Expected output")
    priority: int = Field(default=5, description="Task priority (1-10)")
    recommended_apis: list[dict] = Field(
        default_factory=list,
        description="Recommended APIs",
    )


class AlternativeProposal(BaseModel):
    """Alternative proposal for an infeasible task."""

    original_task_id: str = Field(description="Original infeasible task ID")
    alternative_task: AlternativeTaskItem = Field(description="Alternative task")
    reason: str = Field(description="Reason for this alternative")


class AlternativeResponse(BaseModel):
    """Response from LLM for alternative generation."""

    alternatives: list[AlternativeProposal] = Field(
        default_factory=list,
        description="List of alternative proposals",
    )
    relaxation_needed: bool = Field(
        default=False,
        description="Whether relaxation is needed for some tasks",
    )
    relaxation_reason: str = Field(
        default="",
        description="Reason why relaxation is needed",
    )
    tasks_needing_relaxation: list[str] = Field(
        default_factory=list,
        description="Task IDs that need relaxation",
    )


def _build_alternative_system_prompt(capabilities: list[Capability]) -> str:
    """Build system prompt for alternative generation.

    Args:
        capabilities: Available capabilities

    Returns:
        System prompt string
    """
    cap_list = "\n".join(
        f"- {cap.name}: {cap.endpoint} - {cap.description}" for cap in capabilities
    )

    return f"""You are an expert at finding alternative implementations for workflows.

Given a list of infeasible tasks, your job is to suggest alternative tasks that can
achieve similar goals using the available capabilities.

## Available Capabilities

{cap_list}

## Rules

1. Each alternative must use only the available capabilities above
2. Maintain the same intent and purpose as the original task
3. Keep dependencies consistent with the workflow
4. If no alternative exists, mark relaxation_needed as true
5. Provide clear reasoning for each alternative

## Output Format

Return a JSON object with:
- alternatives: List of alternative proposals
- relaxation_needed: true if some tasks cannot be replaced
- relaxation_reason: Why relaxation is needed
- tasks_needing_relaxation: List of task IDs that need relaxation

Example alternative:
{{
  "original_task_id": "task_001",
  "alternative_task": {{
    "task_id": "task_001_alt",
    "name": "Email Notification",
    "description": "Send notification via email instead of Slack",
    "dependencies": [],
    "expected_output": "Send confirmation",
    "priority": 1,
    "recommended_apis": [{{
      "api_name": "Gmail Send",
      "endpoint": "/v1/utility/gmail/send",
      "method": "POST",
      "reason": "Available alternative for notification"
    }}]
  }},
  "reason": "Gmail is available and can serve the same notification purpose"
}}
"""


def _build_alternative_user_prompt(infeasible_tasks: list[TaskDefinition]) -> str:
    """Build user prompt for alternative generation.

    Args:
        infeasible_tasks: Tasks that need alternatives

    Returns:
        User prompt string
    """
    task_list = "\n".join(
        f"- {task.id}: {task.name}\n  Description: {task.description}\n  "
        f"Original API: {task.recommended_api}\n  Dependencies: {task.dependencies}"
        for task in infeasible_tasks
    )

    return f"""Please find alternatives for the following infeasible tasks:

{task_list}

Provide alternatives using only the available capabilities, or indicate which
tasks need requirement relaxation.
"""


def _convert_alternative_to_task(alt: AlternativeProposal) -> TaskDefinition:
    """Convert AlternativeProposal to TaskDefinition.

    Args:
        alt: Alternative proposal from LLM

    Returns:
        TaskDefinition instance
    """
    alt_task = alt.alternative_task

    # Extract endpoint from recommended_apis
    recommended_api = ""
    if alt_task.recommended_apis:
        first_api = alt_task.recommended_apis[0]
        if isinstance(first_api, dict):
            recommended_api = first_api.get("endpoint", "")

    return TaskDefinition(
        id=alt_task.task_id,
        name=alt_task.name,
        description=alt_task.description,
        task_type="alternative",
        recommended_api=recommended_api,
        priority=alt_task.priority,
        dependencies=alt_task.dependencies,
    )


class AlternativeSubWorkflow:
    """Sub-workflow for generating alternative tasks.

    This class generates alternatives for infeasible tasks or
    returns relaxation suggestions when no alternatives exist.

    Example:
        alternative = AlternativeSubWorkflow(capabilities=caps)
        alt_tasks, suggestions = await alternative.generate(
            infeasible_tasks, context
        )
    """

    def __init__(self, capabilities: list[Capability]):
        """Initialize AlternativeSubWorkflow.

        Args:
            capabilities: List of available capabilities
        """
        self._capabilities = capabilities

    async def generate(
        self,
        infeasible_tasks: list[TaskDefinition],
        context: "ExecutionContext",
    ) -> tuple[list[TaskDefinition], list[RelaxationSuggestion]]:
        """Generate alternatives for infeasible tasks.

        Args:
            infeasible_tasks: Tasks that need alternatives
            context: Execution context

        Returns:
            Tuple of (alternative_tasks, relaxation_suggestions)
        """
        logger.info(
            "Generating alternatives for %d infeasible tasks (job %s)",
            len(infeasible_tasks),
            context.job_id,
        )

        if not infeasible_tasks:
            return [], []

        # Build prompts
        system_prompt = _build_alternative_system_prompt(self._capabilities)
        user_prompt = _build_alternative_user_prompt(infeasible_tasks)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Issue #342 V2: Extract callbacks for Langfuse tracing
        callbacks = get_callbacks_from_context(context)

        try:
            call_result = await invoke_structured_llm(
                messages=messages,
                response_model=AlternativeResponse,
                context_label="alternative_generator",
                model_env_var="JOB_GENERATOR_EVALUATOR_MODEL",
                default_model=context.llm.model_name,
                callbacks=callbacks,
            )
        except StructuredLLMError as exc:
            logger.error("Alternative generation failed: %s", exc)
            # On LLM failure, return relaxation suggestions for all tasks
            error_suggestions = [
                RelaxationSuggestion(
                    original_requirement=task.description,
                    suggested_alternative="Unable to find alternative due to LLM error",
                    reason=str(exc),
                )
                for task in infeasible_tasks
            ]
            return [], error_suggestions

        response = call_result.result

        # Convert alternatives to TaskDefinition
        alternative_tasks = [
            _convert_alternative_to_task(alt) for alt in response.alternatives
        ]

        # Create relaxation suggestions
        result_suggestions: list[RelaxationSuggestion] = []

        if response.relaxation_needed:
            # Create suggestions for tasks that need relaxation
            tasks_needing_relaxation = set(response.tasks_needing_relaxation)

            for task in infeasible_tasks:
                if task.id in tasks_needing_relaxation:
                    result_suggestions.append(
                        RelaxationSuggestion(
                            original_requirement=task.description,
                            suggested_alternative=(
                                f"Consider simplifying: {task.name}"
                            ),
                            reason=response.relaxation_reason,
                        )
                    )
            # If no specific tasks listed but relaxation needed, create general suggestion
            if not result_suggestions and response.relaxation_reason:
                result_suggestions.append(
                    RelaxationSuggestion(
                        original_requirement="Multiple tasks",
                        suggested_alternative="Consider using available APIs",
                        reason=response.relaxation_reason,
                    )
                )

        logger.info(
            "Generated %d alternatives and %d relaxation suggestions",
            len(alternative_tasks),
            len(result_suggestions),
        )

        return alternative_tasks, result_suggestions
