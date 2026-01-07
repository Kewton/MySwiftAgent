"""PromptBuilder for Workflow Generator V2.

This package provides modular prompt building for LLM workflow generation.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.prompt_builder.assembler import (
    WorkflowPrompt,
    assemble_prompt,
    build_task_context,
)

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
    from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.errors import (
        ValidationError,
    )

logger = logging.getLogger(__name__)


class PromptBuilderSubWorkflow:
    """Sub-workflow for building LLM prompts.

    This class coordinates prompt assembly from modular components:
    - System prompts
    - Rule sections
    - API constraints
    - Few-shot examples
    - Task context
    - Error feedback (for retries)
    """

    def __init__(self, verbose: bool = True):
        """Initialize PromptBuilderSubWorkflow.

        Args:
            verbose: Use verbose prompts with detailed rules
        """
        self._verbose = verbose

    def build(
        self,
        task_name: str,
        task_description: str,
        input_schema: dict[str, Any],
        output_schema: dict[str, Any],
        recommended_apis: list[str] | None = None,
        dependencies: list[str] | None = None,
        context: "ExecutionContext | None" = None,
        api_mappings: list[dict[str, Any]] | None = None,
    ) -> WorkflowPrompt:
        """Build workflow generation prompt.

        Args:
            task_name: Name of the task
            task_description: Task description
            input_schema: Task input JSON Schema
            output_schema: Task output JSON Schema
            recommended_apis: List of recommended API names
            dependencies: List of dependent task IDs
            context: Execution context (for logging)
            api_mappings: Issue #342 V2 - API mapping info from AgentSelector

        Returns:
            WorkflowPrompt with all components assembled
        """
        logger.info("Building workflow prompt for task: %s", task_name)

        return assemble_prompt(
            task_name=task_name,
            task_description=task_description,
            input_schema=input_schema,
            output_schema=output_schema,
            recommended_apis=recommended_apis,
            dependencies=dependencies,
            error_feedback="",
            verbose=self._verbose,
            api_mappings=api_mappings,
        )

    def build_with_errors(
        self,
        task_name: str,
        task_description: str,
        input_schema: dict[str, Any],
        output_schema: dict[str, Any],
        previous_errors: list["ValidationError"],
        recommended_apis: list[str] | None = None,
        dependencies: list[str] | None = None,
        context: "ExecutionContext | None" = None,
    ) -> WorkflowPrompt:
        """Build prompt with previous error feedback for retry.

        Args:
            task_name: Name of the task
            task_description: Task description
            input_schema: Task input JSON Schema
            output_schema: Task output JSON Schema
            previous_errors: List of previous validation errors
            recommended_apis: List of recommended API names
            dependencies: List of dependent task IDs
            context: Execution context (for logging)

        Returns:
            WorkflowPrompt with error feedback included
        """
        logger.info(
            "Building retry prompt for task: %s with %d errors",
            task_name,
            len(previous_errors),
        )

        # Build error feedback section
        error_feedback = self._build_error_feedback(previous_errors)

        return assemble_prompt(
            task_name=task_name,
            task_description=task_description,
            input_schema=input_schema,
            output_schema=output_schema,
            recommended_apis=recommended_apis,
            dependencies=dependencies,
            error_feedback=error_feedback,
            verbose=self._verbose,
        )

    def _build_error_feedback(self, errors: list["ValidationError"]) -> str:
        """Build error feedback section.

        Args:
            errors: List of validation errors

        Returns:
            Formatted error feedback string
        """
        if not errors:
            return ""

        lines = [
            "",
            "## Previous Generation Errors (MUST FIX)",
            "",
        ]
        for error in errors:
            lines.append(error.to_prompt_section())

        lines.append("")
        lines.append("Please generate corrected YAML fixing the above errors.")

        return "\n".join(lines)


__all__ = [
    "PromptBuilderSubWorkflow",
    "WorkflowPrompt",
    "assemble_prompt",
    "build_task_context",
]
