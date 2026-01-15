"""LLM Generator Sub-Workflow for Workflow Generator V2.

This module provides LLM-based YAML workflow generation.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
Issue #342 V2 Workflow Quality Improvement: AgentSelector/ParameterMapper integration
"""

from __future__ import annotations

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

from .agent_selector import AgentSelector
from .parameter_mapper import ParameterMapper
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

    yaml_content: str = Field(description="Complete GraphAI workflow YAML content")
    workflow_name: str = Field(
        default="generated_workflow", description="Name for the workflow"
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

    Issue #342 V2: Integrates AgentSelector and ParameterMapper for
    improved workflow quality and GraphAI spec compliance.
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

        # Issue #342 V2: Initialize AgentSelector and ParameterMapper
        self._agent_selector = AgentSelector()
        self._parameter_mapper = ParameterMapper()

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
                result = await self._generate_structured(prompt, context)
            else:
                result = await self._generate_raw(prompt, context)

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
        self,
        prompt: WorkflowPrompt,
        context: "ExecutionContext | None" = None,
    ) -> LLMGenerationResult:
        """Generate using Pydantic structured output.

        Args:
            prompt: WorkflowPrompt with prompts
            context: Optional ExecutionContext for callbacks

        Returns:
            LLMGenerationResult with generated YAML
        """
        # Issue #342 V2: Extract callbacks for Langfuse tracing
        callbacks = get_callbacks_from_context(context) if context else []

        result = await invoke_structured_llm(
            system_prompt=prompt.system,
            user_prompt=prompt.render(),
            response_model=GraphAIWorkflowSchema,
            model_name=self._model,
            temperature=self._temperature,
            context_label="workflow_gen_v2",
            model_env_var=MODEL_ENV_VAR,
            default_model=DEFAULT_MODEL,
            callbacks=callbacks if callbacks else None,
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
        self,
        prompt: WorkflowPrompt,
        context: "ExecutionContext | None" = None,
    ) -> LLMGenerationResult:
        """Generate using raw YAML output.

        Args:
            prompt: WorkflowPrompt with prompts
            context: Optional ExecutionContext for callbacks

        Returns:
            LLMGenerationResult with generated YAML
        """
        # Issue #342 V2: Extract callbacks for Langfuse tracing
        callbacks = get_callbacks_from_context(context) if context else []

        result = await invoke_structured_llm(
            system_prompt=prompt.system,
            user_prompt=prompt.render(),
            response_model=WorkflowYAMLResponse,
            model_name=self._model,
            temperature=self._temperature,
            context_label="workflow_gen_v2_raw",
            model_env_var=MODEL_ENV_VAR,
            default_model=DEFAULT_MODEL,
            callbacks=callbacks if callbacks else None,
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
        error_feedback: str = "",
    ) -> LLMGenerationResult:
        """Generate workflow from task definition.

        Convenience method that builds prompt and generates in one call.

        Issue #342 V2: Enhanced with AgentSelector and ParameterMapper
        to provide better API mapping information to LLM.

        Issue #343: Added error_feedback parameter for retry with
        previous validation errors.

        Args:
            task_name: Name of the task
            task_description: Task description
            input_schema: Task input JSON Schema
            output_schema: Task output JSON Schema
            recommended_apis: List of recommended API names
            dependencies: List of dependent task IDs
            context: Execution context
            error_feedback: Previous validation error feedback for retries

        Returns:
            LLMGenerationResult with generated YAML
        """
        # Issue #342 V2: Enrich prompt with AgentSelector information
        api_mappings = self._get_api_mappings(recommended_apis)

        prompt_builder = PromptBuilderSubWorkflow()
        prompt = prompt_builder.build(
            task_name=task_name,
            task_description=task_description,
            input_schema=input_schema,
            output_schema=output_schema,
            recommended_apis=recommended_apis,
            dependencies=dependencies,
            context=context,
            api_mappings=api_mappings,
            error_feedback=error_feedback,
        )

        return await self.generate(prompt, context)

    def _get_api_mappings(
        self,
        recommended_apis: list[str] | None,
    ) -> list[dict[str, Any]]:
        """Get API mapping information for recommended APIs.

        Issue #342 V2: Uses AgentSelector to get endpoint and method info.

        Args:
            recommended_apis: List of recommended API names

        Returns:
            List of API mapping dictionaries with url, method info
        """
        if not recommended_apis:
            return []

        mappings = []
        for api_name in recommended_apis:
            mapping = self._agent_selector.select_agent(api_name)
            if mapping:
                mappings.append(
                    {
                        "api_name": api_name,
                        "agent_type": mapping.agent_type,
                        "endpoint_url": f"${{EXPERTAGENT_BASE_URL}}{mapping.endpoint_path}",
                        "http_method": mapping.http_method,
                        "description": mapping.description,
                    }
                )
            else:
                # Unknown API - provide generic mapping
                mappings.append(
                    {
                        "api_name": api_name,
                        "agent_type": "fetchAgent",
                        "endpoint_url": f"${{EXPERTAGENT_BASE_URL}}/aiagent-api/v1/utility/{api_name}",  # noqa: E501
                        "http_method": "POST",
                        "description": f"API call to {api_name}",
                    }
                )

        return mappings

    def get_parameter_mapping(
        self,
        api_name: str,
        interface_inputs: dict[str, Any],
        source_node: str = "user_input",
    ) -> dict[str, Any]:
        """Get parameter mapping for API inputs block.

        Issue #342 V2: Uses ParameterMapper to create GraphAI-compliant
        inputs block with url, method, body.

        Args:
            api_name: API name
            interface_inputs: Input field definitions
            source_node: Source node name for references

        Returns:
            GraphAI inputs block dictionary
        """
        return self._parameter_mapper.create_fetchagent_inputs(
            api_name=api_name,
            input_params=interface_inputs,
            source_node=source_node,
        )
