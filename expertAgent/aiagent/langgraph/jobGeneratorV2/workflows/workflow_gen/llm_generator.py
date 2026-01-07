"""LLM Generator Sub-Workflow for Workflow Generator V2.

This module provides LLM-based YAML workflow generation.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from aiagent.langgraph.jobGeneratorV2.llm_utils import (
    StructuredLLMError,
    invoke_structured_llm,
)

from .prompt_builder import PromptBuilderSubWorkflow, WorkflowPrompt
from .schemas import GraphAIWorkflowSchema

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext

logger = logging.getLogger(__name__)


# Environment variable names
MODEL_ENV_VAR = "WORKFLOW_GENERATOR_V2_MODEL"
TEMPERATURE_ENV_VAR = "WORKFLOW_GENERATOR_V2_TEMPERATURE"
DEFAULT_MODEL = "gemini-3-flash-preview"
DEFAULT_TEMPERATURE = 0.3


class WorkflowYAMLResponse(BaseModel):
    """Response model for YAML workflow generation.

    This is a simpler model that just returns the YAML string,
    allowing for more flexible LLM output while still using
    structured output for consistency.
    """

    yaml_content: str = Field(
        description="Complete GraphAI workflow YAML content"
    )
    workflow_name: str = Field(
        default="generated_workflow",
        description="Name for the workflow"
    )


@dataclass
class LLMGenerationResult:
    """Result from LLM workflow generation.

    Attributes:
        yaml_content: Generated YAML workflow string
        workflow_name: Name of the workflow
        model_name: Name of the LLM model used
        node_count: Number of nodes in the workflow
    """

    yaml_content: str
    workflow_name: str
    model_name: str
    node_count: int = 0


class LLMGeneratorSubWorkflow:
    """Sub-workflow for LLM-based YAML generation.

    Uses structured output to generate GraphAI workflows from prompts.
    Supports both structured schema output and raw YAML output.
    """

    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
        use_structured_output: bool = True,
    ):
        """Initialize LLMGeneratorSubWorkflow.

        Args:
            model: LLM model name (uses env var or default if None)
            temperature: Sampling temperature (uses env var or default if None)
            use_structured_output: Whether to use Pydantic structured output
        """
        self._model = model or os.environ.get(MODEL_ENV_VAR, DEFAULT_MODEL)
        if temperature is not None:
            self._temperature: float = temperature
        else:
            temp_str = os.environ.get(TEMPERATURE_ENV_VAR, str(DEFAULT_TEMPERATURE))
            self._temperature = float(temp_str)
        self._use_structured_output = use_structured_output

    async def generate(
        self,
        prompt: WorkflowPrompt,
        context: "ExecutionContext | None" = None,
    ) -> LLMGenerationResult:
        """Generate workflow YAML using LLM.

        Args:
            prompt: WorkflowPrompt with system and user prompts
            context: Execution context for logging

        Returns:
            LLMGenerationResult with generated YAML

        Raises:
            StructuredLLMError: If LLM invocation fails
        """
        job_id = context.job_id if context else "unknown"
        logger.info(
            "Generating workflow with LLM (model=%s, job=%s)",
            self._model,
            job_id,
        )

        try:
            if self._use_structured_output:
                result = await self._generate_structured(prompt)
            else:
                result = await self._generate_raw(prompt)

            logger.info(
                "Workflow generated successfully: %s (%d nodes)",
                result.workflow_name,
                result.node_count,
            )
            return result

        except StructuredLLMError:
            raise
        except Exception as e:
            logger.error("LLM generation failed: %s", e)
            raise StructuredLLMError(f"Workflow generation failed: {e}") from e

    async def _generate_structured(
        self, prompt: WorkflowPrompt
    ) -> LLMGenerationResult:
        """Generate using Pydantic structured output.

        Args:
            prompt: WorkflowPrompt with prompts

        Returns:
            LLMGenerationResult with generated YAML
        """
        result = await invoke_structured_llm(
            system_prompt=prompt.system,
            user_prompt=prompt.render(),
            response_model=GraphAIWorkflowSchema,
            model_name=self._model,
            temperature=self._temperature,
            context_label="workflow_gen_v2",
            model_env_var=MODEL_ENV_VAR,
            default_model=DEFAULT_MODEL,
        )

        schema: GraphAIWorkflowSchema = result.result
        yaml_content = schema.to_yaml()
        node_count = len(schema.nodes)

        return LLMGenerationResult(
            yaml_content=yaml_content,
            workflow_name=f"workflow_{id(schema)}",
            model_name=result.model_name,
            node_count=node_count,
        )

    async def _generate_raw(
        self, prompt: WorkflowPrompt
    ) -> LLMGenerationResult:
        """Generate using raw YAML output.

        Args:
            prompt: WorkflowPrompt with prompts

        Returns:
            LLMGenerationResult with generated YAML
        """
        result = await invoke_structured_llm(
            system_prompt=prompt.system,
            user_prompt=prompt.render(),
            response_model=WorkflowYAMLResponse,
            model_name=self._model,
            temperature=self._temperature,
            context_label="workflow_gen_v2_raw",
            model_env_var=MODEL_ENV_VAR,
            default_model=DEFAULT_MODEL,
        )

        response: WorkflowYAMLResponse = result.result

        # Count nodes from YAML
        node_count = 0
        try:
            import yaml
            parsed = yaml.safe_load(response.yaml_content)
            if parsed and isinstance(parsed.get("nodes"), dict):
                node_count = len(parsed["nodes"])
        except Exception as e:
            logger.debug("Could not parse YAML for node count: %s", e)

        return LLMGenerationResult(
            yaml_content=response.yaml_content,
            workflow_name=response.workflow_name,
            model_name=result.model_name,
            node_count=node_count,
        )

    async def generate_from_task(
        self,
        task_name: str,
        task_description: str,
        input_schema: dict,
        output_schema: dict,
        recommended_apis: list[str] | None = None,
        dependencies: list[str] | None = None,
        context: "ExecutionContext | None" = None,
    ) -> LLMGenerationResult:
        """Generate workflow from task definition.

        Convenience method that builds prompt and generates in one call.

        Args:
            task_name: Name of the task
            task_description: Task description
            input_schema: Task input JSON Schema
            output_schema: Task output JSON Schema
            recommended_apis: List of recommended API names
            dependencies: List of dependent task IDs
            context: Execution context

        Returns:
            LLMGenerationResult with generated YAML
        """
        prompt_builder = PromptBuilderSubWorkflow()
        prompt = prompt_builder.build(
            task_name=task_name,
            task_description=task_description,
            input_schema=input_schema,
            output_schema=output_schema,
            recommended_apis=recommended_apis,
            dependencies=dependencies,
            context=context,
        )

        return await self.generate(prompt, context)
