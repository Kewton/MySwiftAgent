"""TaskFlow V2 LLM Generator.

Issue #350 Task 2.6: TaskFlow generator implementation.

This module provides:
- TaskFlowLLMGenerator: LLM-based TaskFlow JSON generation
- TaskFlowGenerationResult: Result from generation

Uses the TaskFlow V2 schema and rules to generate
valid JSON workflows via structured LLM output.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from aiagent.langgraph.jobGeneratorV2.llm_utils import (
    StructuredLLMError,
    get_callbacks_from_context,
    invoke_structured_llm,
)

from .prompt_builder.few_shot.selector import FewShotSelector, TaskPattern
from .prompt_builder.rules.taskflow_rules import TASKFLOW_RULES_FULL
from .schemas.taskflow_schema import TaskFlowWorkflow

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
    from aiagent.langgraph.jobGeneratorV2.types_old import InterfaceSchema

logger = logging.getLogger(__name__)


# Environment variable names
MODEL_ENV_VAR = "WORKFLOW_GENERATOR_V2_MODEL"
TEMPERATURE_ENV_VAR = "WORKFLOW_GENERATOR_V2_TEMPERATURE"
DEFAULT_MODEL = "gemini-3-flash-preview"
DEFAULT_TEMPERATURE = 0.3


class TaskFlowResponse(BaseModel):
    """Response model for TaskFlow workflow generation.

    Uses the TaskFlowWorkflow Pydantic model for structured output.
    """

    workflow: TaskFlowWorkflow = Field(
        description="Complete TaskFlow V2 workflow definition"
    )
    reasoning: str = Field(
        default="",
        description="Brief explanation of the workflow design",
    )


@dataclass
class TaskFlowGenerationResult:
    """Result from TaskFlow LLM generation.

    Attributes:
        json_content: Generated JSON workflow string
        workflow_name: Name of the workflow
        step_count: Number of steps in the workflow
        model_name: LLM model used for generation
    """

    json_content: str
    workflow_name: str
    step_count: int
    model_name: str


class TaskFlowLLMGenerator:
    """LLM-based TaskFlow V2 workflow generator.

    Generates TaskFlow V2 JSON workflows using structured LLM output.
    Includes few-shot examples and TaskFlow-specific rules.
    """

    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
    ) -> None:
        """Initialize TaskFlowLLMGenerator.

        Args:
            model: LLM model name (uses env var or default if None)
            temperature: Sampling temperature (uses env var or default if None)
        """
        self._model = model or os.environ.get(MODEL_ENV_VAR, DEFAULT_MODEL)
        if temperature is not None:
            self._temperature = temperature
        else:
            temp_str = os.environ.get(TEMPERATURE_ENV_VAR, str(DEFAULT_TEMPERATURE))
            self._temperature = float(temp_str)

        self._few_shot_selector = FewShotSelector()

    async def generate(
        self,
        task_definitions: list[dict[str, Any]],
        interfaces: dict[str, "InterfaceSchema"],
        context: "ExecutionContext | None" = None,
    ) -> TaskFlowGenerationResult:
        """Generate TaskFlow V2 workflow from task definitions.

        Args:
            task_definitions: List of task definition dictionaries
            interfaces: Interface schemas for each task
            context: Execution context for LLM callbacks

        Returns:
            TaskFlowGenerationResult with generated JSON

        Raises:
            StructuredLLMError: If LLM generation fails
        """
        job_id = context.job_id if context else "unknown"
        logger.info(
            "Generating TaskFlow V2 workflow (model=%s, job=%s)",
            self._model,
            job_id,
        )

        # Detect patterns for few-shot selection
        patterns = self._few_shot_selector.detect_patterns(task_definitions)
        if not patterns:
            patterns = [TaskPattern.API_CALL]

        # Select few-shot examples
        examples = self._few_shot_selector.select_examples(
            engine="taskflow",
            task_patterns=patterns,
            max_examples=2,
        )

        # Build prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            task_definitions=task_definitions,
            interfaces=interfaces,
            examples=examples,
        )

        try:
            # Get callbacks from context
            callbacks = get_callbacks_from_context(context) if context else []

            # Generate using structured LLM
            result = await invoke_structured_llm(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response_model=TaskFlowWorkflow,
                model_name=self._model,
                temperature=self._temperature,
                context_label="taskflow_gen_v2",
                model_env_var=MODEL_ENV_VAR,
                default_model=DEFAULT_MODEL,
                callbacks=callbacks if callbacks else None,
            )

            workflow: TaskFlowWorkflow = result.result
            json_content = workflow.to_json()
            step_count = len(workflow.steps)

            logger.info(
                "TaskFlow workflow generated: %s (%d steps)",
                workflow.workflow_name,
                step_count,
            )

            return TaskFlowGenerationResult(
                json_content=json_content,
                workflow_name=workflow.workflow_name,
                step_count=step_count,
                model_name=result.model_name,
            )

        except StructuredLLMError:
            raise
        except Exception as e:
            logger.error("TaskFlow generation failed: %s", e)
            raise StructuredLLMError(
                f"TaskFlow workflow generation failed: {e}"
            ) from e

    def _build_system_prompt(self) -> str:
        """Build system prompt for TaskFlow generation."""
        return """You are a TaskFlow V2 workflow generator.

Your task is to generate a valid TaskFlow V2 JSON workflow based on:
1. Task definitions provided by the user
2. Input/output interface schemas
3. TaskFlow V2 rules and syntax

IMPORTANT:
- Generate ONLY valid TaskFlow V2 JSON
- Use HTTPS for all URLs
- Follow the variable reference syntax: ${step_id.field}
- Use only allowed code_js functions

""" + TASKFLOW_RULES_FULL

    def _build_user_prompt(
        self,
        task_definitions: list[dict[str, Any]],
        interfaces: dict[str, Any],
        examples: list[dict[str, Any]],
    ) -> str:
        """Build user prompt with task context."""
        sections = []

        # Add task definitions
        sections.append("## Task Definitions\n")
        for i, task in enumerate(task_definitions):
            sections.append(f"### Task {i + 1}: {task.get('name', 'Unnamed')}")
            sections.append(f"Description: {task.get('description', '')}")
            sections.append(f"Type: {task.get('task_type', 'unknown')}")
            if task.get("recommended_api"):
                sections.append(f"Recommended API: {task.get('recommended_api')}")
            sections.append("")

        # Add interface schemas
        sections.append("## Interface Schemas\n")
        for task_id, interface in interfaces.items():
            sections.append(f"### {task_id}")
            input_schema = (
                interface.input_schema
                if hasattr(interface, "input_schema")
                else interface.get("input_schema", {})
            )
            output_schema = (
                interface.output_schema
                if hasattr(interface, "output_schema")
                else interface.get("output_schema", {})
            )
            sections.append(
                f"Input: {json.dumps(input_schema, ensure_ascii=False)}"
            )
            sections.append(
                f"Output: {json.dumps(output_schema, ensure_ascii=False)}"
            )
            sections.append("")

        # Add examples
        if examples:
            sections.append("## Examples\n")
            for i, example in enumerate(examples):
                sections.append(f"### Example {i + 1}: {example.get('name', '')}")
                sections.append(f"Description: {example.get('description', '')}")
                if "example" in example:
                    sections.append("```json")
                    sections.append(json.dumps(example["example"], indent=2))
                    sections.append("```")
                sections.append("")

        # Add instructions
        sections.append("## Instructions")
        sections.append("Generate a TaskFlow V2 workflow that:")
        sections.append("1. Accepts input matching the input schema")
        sections.append("2. Produces output matching the output schema")
        sections.append("3. Uses api_rest, transform, or code_js steps as needed")
        sections.append("4. Uses HTTPS for all URLs")
        sections.append("5. Follows variable reference syntax: ${step_id.field}")
        sections.append("")
        sections.append("Return a valid TaskFlowWorkflow JSON object.")

        return "\n".join(sections)


__all__ = [
    "TaskFlowLLMGenerator",
    "TaskFlowGenerationResult",
    "TaskFlowResponse",
]
