"""Strategy Pattern for Workflow Generation Engine.

Issue #350 Task 1.1: Strategy Pattern base classes.

This module provides:
- EngineType enum for engine selection
- WorkflowGeneratorStrategy abstract base class
- create_strategy factory function
- GraphAIGeneratorStrategy - existing YAML generation
- TaskFlowGeneratorStrategy - new JSON generation (placeholder)

The Strategy Pattern enables runtime switching between GraphAI YAML
and TaskFlow V2 JSON generation while maintaining a consistent interface.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
    from aiagent.langgraph.jobGeneratorV2.validators import WorkflowValidator

logger = logging.getLogger(__name__)


class EngineType(str, Enum):
    """Workflow generation engine type.

    Determines which format the workflow will be generated in.
    """

    GRAPHAI = "graphai"  # GraphAI YAML format (legacy)
    TASKFLOW = "taskflow"  # TaskFlow V2 JSON format (new default)


@dataclass
class WorkflowOutput:
    """Output from workflow generation strategy.

    Attributes:
        content: Generated workflow content (YAML or JSON string)
        format: Output format ('yaml' or 'json')
        workflow_name: Name of the generated workflow
        node_count: Number of nodes/steps in the workflow
        metadata: Additional metadata about the generation
        raw_result: Parsed workflow data (dict for JSON, None for YAML)
    """

    content: str
    format: str  # 'yaml' or 'json'
    workflow_name: str
    node_count: int = 0
    metadata: dict[str, Any] | None = None
    raw_result: dict[str, Any] | None = None  # Issue #350: For TaskFlow registration


class WorkflowGeneratorStrategy(ABC):
    """Abstract base class for workflow generation strategies.

    All workflow generators must implement this interface to enable
    runtime engine switching via the Strategy Pattern.

    Attributes:
        engine_type: The engine type this strategy implements
        output_format: The output format this strategy produces
    """

    @property
    @abstractmethod
    def engine_type(self) -> EngineType:
        """Get the engine type for this strategy."""
        ...

    @property
    @abstractmethod
    def output_format(self) -> str:
        """Get the output format ('yaml' or 'json')."""
        ...

    @abstractmethod
    async def generate(
        self,
        task_definitions: list[dict[str, Any]],
        interfaces: dict[str, Any],
        context: "ExecutionContext",
    ) -> WorkflowOutput:
        """Generate workflow from task definitions.

        Args:
            task_definitions: List of task definition dictionaries
            interfaces: Interface schemas for each task
            context: Execution context with LLM and configuration

        Returns:
            WorkflowOutput with generated workflow content
        """
        ...

    @abstractmethod
    def get_prompt_rules(self) -> list[str]:
        """Get prompt rules for this engine.

        Returns:
            List of rule strings to include in LLM prompts
        """
        ...

    @abstractmethod
    def get_validator(self) -> "WorkflowValidator":
        """Get the validator for this engine's output.

        Returns:
            WorkflowValidator instance for validating generated workflows
        """
        ...


class GraphAIGeneratorStrategy(WorkflowGeneratorStrategy):
    """Strategy for GraphAI YAML generation.

    This strategy wraps the existing YAML generation logic and provides
    a consistent interface via the Strategy Pattern.
    """

    @property
    def engine_type(self) -> EngineType:
        """Get the engine type."""
        return EngineType.GRAPHAI

    @property
    def output_format(self) -> str:
        """Get the output format."""
        return "yaml"

    async def generate(
        self,
        task_definitions: list[dict[str, Any]],
        interfaces: dict[str, Any],
        context: "ExecutionContext",
    ) -> WorkflowOutput:
        """Generate GraphAI YAML workflow.

        This delegates to the existing LLMGeneratorSubWorkflow for
        backward compatibility.
        """
        from .llm_generator import LLMGeneratorSubWorkflow
        from .prompt_builder import PromptBuilderSubWorkflow

        logger.info("Generating GraphAI YAML workflow via Strategy")

        # Build prompt using existing prompt builder
        prompt_builder = PromptBuilderSubWorkflow()

        # Extract first task for now (simplified)
        first_task = task_definitions[0] if task_definitions else {}
        task_name = first_task.get("name", "generated_task")
        task_description = first_task.get("description", "")

        # Get first interface
        first_interface: Any = next(iter(interfaces.values()), {})
        input_schema = (
            first_interface.input_schema
            if hasattr(first_interface, "input_schema")
            else {}
        )
        output_schema = (
            first_interface.output_schema
            if hasattr(first_interface, "output_schema")
            else {}
        )

        prompt = prompt_builder.build(
            task_name=task_name,
            task_description=task_description,
            input_schema=input_schema,
            output_schema=output_schema,
            context=context,
        )

        # Generate using LLM
        llm_generator = LLMGeneratorSubWorkflow()
        result = await llm_generator.generate(prompt, context)

        return WorkflowOutput(
            content=result.yaml_content,
            format="yaml",
            workflow_name=result.workflow_name,
            node_count=result.node_count,
        )

    def get_prompt_rules(self) -> list[str]:
        """Get GraphAI-specific prompt rules."""
        from .prompt_builder.rules import (
            get_agent_rules,
            get_api_rules,
            get_base_rules,
            get_reference_rules,
        )

        return [
            get_base_rules(),
            get_agent_rules(),
            get_reference_rules(),
            get_api_rules(),
        ]

    def get_validator(self) -> "WorkflowValidator":
        """Get GraphAI workflow validator."""
        from aiagent.langgraph.jobGeneratorV2.validators.source_path_rule_engine import (
            SourcePathRuleEngine,
        )

        return SourcePathRuleEngine()


class TaskFlowGeneratorStrategy(WorkflowGeneratorStrategy):
    """Strategy for TaskFlow V2 JSON generation.

    This strategy generates TaskFlow V2 JSON workflows with:
    - Sequential, parallel, and conditional step execution
    - Strict schema validation
    - Security enforcement (HTTPS, SSRF protection)
    """

    @property
    def engine_type(self) -> EngineType:
        """Get the engine type."""
        return EngineType.TASKFLOW

    @property
    def output_format(self) -> str:
        """Get the output format."""
        return "json"

    async def generate(
        self,
        task_definitions: list[dict[str, Any]],
        interfaces: dict[str, Any],
        context: "ExecutionContext",
    ) -> WorkflowOutput:
        """Generate TaskFlow V2 JSON workflow.

        This uses the TaskFlow-specific prompt rules and generates
        JSON output instead of YAML.
        """
        from .taskflow_generator import TaskFlowLLMGenerator

        import json

        logger.info("Generating TaskFlow V2 JSON workflow via Strategy")

        generator = TaskFlowLLMGenerator()
        result = await generator.generate(
            task_definitions=task_definitions,
            interfaces=interfaces,
            context=context,
        )

        # Issue #350: Parse JSON content to raw_result for registration
        try:
            raw_result = json.loads(result.json_content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON content for raw_result")
            raw_result = {}

        return WorkflowOutput(
            content=result.json_content,
            format="json",
            workflow_name=result.workflow_name,
            node_count=result.step_count,
            raw_result=raw_result,
        )

    def get_prompt_rules(self) -> list[str]:
        """Get TaskFlow-specific prompt rules."""
        from .prompt_builder.rules.taskflow_rules import get_taskflow_rules

        return get_taskflow_rules()

    def get_validator(self) -> "WorkflowValidator":
        """Get TaskFlow workflow validator."""
        from aiagent.langgraph.jobGeneratorV2.validators.taskflow_validator import (
            TaskFlowSchemaValidator,
        )

        return TaskFlowSchemaValidator()


def create_strategy(
    engine: EngineType | str = EngineType.TASKFLOW,
) -> WorkflowGeneratorStrategy:
    """Factory function to create workflow generation strategy.

    Args:
        engine: Engine type to use. Defaults to TaskFlow V2.
            Can be EngineType enum or string value.

    Returns:
        WorkflowGeneratorStrategy instance for the specified engine

    Raises:
        ValueError: If unknown engine type is specified
    """
    # Convert string to enum if needed
    if isinstance(engine, str):
        try:
            engine = EngineType(engine)
        except ValueError as e:
            raise ValueError(
                f"Unknown engine: {engine}. "
                f"Valid engines: {[e.value for e in EngineType]}"
            ) from e

    if engine == EngineType.GRAPHAI:
        logger.debug("Creating GraphAI generator strategy")
        return GraphAIGeneratorStrategy()
    elif engine == EngineType.TASKFLOW:
        logger.debug("Creating TaskFlow generator strategy")
        return TaskFlowGeneratorStrategy()
    else:
        raise ValueError(
            f"Unknown engine: {engine}. "
            f"Valid engines: {[e.value for e in EngineType]}"
        )


__all__ = [
    "EngineType",
    "WorkflowOutput",
    "WorkflowGeneratorStrategy",
    "GraphAIGeneratorStrategy",
    "TaskFlowGeneratorStrategy",
    "create_strategy",
]
