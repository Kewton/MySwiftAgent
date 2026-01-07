"""YAML generator sub-workflow for WorkflowGen.

This module provides the YamlGeneratorSubWorkflow that:
1. Generates GraphAI YAML workflow definitions
2. Defines task chains based on dependencies
3. Uses LLM to generate workflow YAML when needed

Issue #342 Phase D.2: Migrated logic from jobTaskGeneratorAgents/nodes/workflow_generation.py
without importing from the old code.

Key design decisions:
- Uses ExecutionContext for LLM access (dependency injection)
- Does NOT import from langgraph or old jobTaskGeneratorAgents
- Supports both template-based and LLM-based YAML generation
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from aiagent.langgraph.jobGeneratorV2.protocols import (
    ErrorType,
    WorkflowError,
)
from aiagent.langgraph.jobGeneratorV2.types import (
    InterfaceSchema,
    Phase,
)

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext

logger = logging.getLogger(__name__)


# Prompt constants for YAML generation
YAML_GENERATION_SYSTEM_PROMPT = """You are an expert GraphAI workflow designer.
Your task is to generate GraphAI YAML workflow definitions.

## GraphAI YAML Structure
A GraphAI workflow YAML has:
- version: "0.6" (current version)
- nodes: Dict of node definitions
- Each node has:
  - agent: Agent type (e.g., "fetchAgent", "sleeperAgent")
  - inputs: Input mappings
  - params: Additional parameters

## Agent Types
Common agents:
- fetchAgent: HTTP API calls
- sleeperAgent: Delays/waits
- copyAgent: Data transformation
- nestedAgent: Sub-workflow execution

## Input Mappings
Use :source notation for data flow:
- :source.nodeId.fieldName - Reference another node's output
- :source.user_input.fieldName - Reference initial input
- :source.job_params.fieldName - Reference static job parameters

## Output Format
Return valid YAML that can be parsed directly.
"""


@dataclass
class WorkflowNodeDefinition:
    """Definition of a node in the GraphAI workflow.

    Attributes:
        node_id: Unique node identifier
        agent: Agent type name
        inputs: Input mappings
        params: Additional parameters
        is_result: Whether this is a result node
    """

    node_id: str
    agent: str
    inputs: dict[str, Any] = field(default_factory=dict)
    params: dict[str, Any] = field(default_factory=dict)
    is_result: bool = False


@dataclass
class YamlGenerationResult:
    """Result from YAML generation sub-workflow.

    Attributes:
        yaml_content: Generated YAML string
        workflow_name: Name of the workflow
        node_count: Number of nodes in workflow
        generation_method: How the YAML was generated (template/llm)
    """

    yaml_content: str
    workflow_name: str
    node_count: int
    generation_method: str = "template"


class YamlGeneratorSubWorkflow:
    """Sub-workflow for generating GraphAI YAML workflows.

    This sub-workflow handles:
    1. Analyzing task chains and dependencies
    2. Generating workflow node definitions
    3. Producing valid GraphAI YAML

    Example:
        generator = YamlGeneratorSubWorkflow()
        result = await generator.generate(task_master_ids, interfaces, context)
    """

    def __init__(
        self,
        graphai_version: str = "0.6",
        use_llm_generation: bool = False,
    ) -> None:
        """Initialize YamlGeneratorSubWorkflow.

        Args:
            graphai_version: GraphAI version for YAML
            use_llm_generation: Whether to use LLM for generation
        """
        self._graphai_version = graphai_version
        self._use_llm_generation = use_llm_generation

    async def generate(
        self,
        task_master_ids: list[str],
        job_master_id: str,
        interfaces: dict[str, InterfaceSchema],
        context: "ExecutionContext",
    ) -> YamlGenerationResult:
        """Generate GraphAI YAML workflow.

        Args:
            task_master_ids: List of TaskMaster IDs (in execution order)
            job_master_id: JobMaster ID
            interfaces: Interface schemas for each task
            context: Execution context

        Returns:
            YamlGenerationResult with YAML content

        Raises:
            WorkflowError: If YAML generation fails
        """
        logger.info(
            "Generating GraphAI YAML for job %s with %d tasks",
            context.job_id,
            len(task_master_ids),
        )

        if not task_master_ids:
            raise WorkflowError(
                "No task masters provided for YAML generation",
                ErrorType.VALIDATION,
                Phase.WORKFLOW_GEN,
            )

        # Build workflow node definitions
        nodes = self._build_workflow_nodes(task_master_ids, interfaces)

        # Generate YAML content
        workflow_name = f"workflow_{job_master_id}"
        yaml_content = self._generate_yaml(workflow_name, nodes)

        logger.info(
            "Generated YAML workflow: %s with %d nodes",
            workflow_name,
            len(nodes),
        )

        return YamlGenerationResult(
            yaml_content=yaml_content,
            workflow_name=workflow_name,
            node_count=len(nodes),
            generation_method="template",
        )

    def _build_workflow_nodes(
        self,
        task_master_ids: list[str],
        interfaces: dict[str, InterfaceSchema],
    ) -> list[WorkflowNodeDefinition]:
        """Build workflow node definitions from task masters.

        Args:
            task_master_ids: List of TaskMaster IDs
            interfaces: Interface schemas

        Returns:
            List of WorkflowNodeDefinition
        """
        nodes: list[WorkflowNodeDefinition] = []

        for idx, tm_id in enumerate(task_master_ids):
            # Extract task_id from tm_id (assumes format "tm_<task_id>")
            task_id = tm_id.replace("tm_", "") if tm_id.startswith("tm_") else tm_id

            # Build inputs based on position in chain
            if idx == 0:
                # First node receives user_input
                inputs = {
                    "data": ":source.user_input",
                }
            else:
                # Subsequent nodes receive from previous node
                prev_node_id = task_master_ids[idx - 1]
                prev_task_id = (
                    prev_node_id.replace("tm_", "")
                    if prev_node_id.startswith("tm_")
                    else prev_node_id
                )
                inputs = {
                    "data": f":source.{prev_task_id}",
                }

            # Determine if this is a result node (last in chain)
            is_result = idx == len(task_master_ids) - 1

            node = WorkflowNodeDefinition(
                node_id=task_id,
                agent="fetchAgent",
                inputs=inputs,
                params={
                    "task_master_id": tm_id,
                },
                is_result=is_result,
            )
            nodes.append(node)

        return nodes

    def _generate_yaml(
        self,
        workflow_name: str,
        nodes: list[WorkflowNodeDefinition],
    ) -> str:
        """Generate YAML string from node definitions.

        Args:
            workflow_name: Name of the workflow
            nodes: List of node definitions

        Returns:
            YAML string
        """
        # Build YAML manually (avoiding yaml dependency for simplicity)
        lines = [
            f"# GraphAI Workflow: {workflow_name}",
            f"version: \"{self._graphai_version}\"",
            "",
            "nodes:",
        ]

        for node in nodes:
            lines.append(f"  {node.node_id}:")
            lines.append(f"    agent: {node.agent}")

            if node.inputs:
                lines.append("    inputs:")
                for key, value in node.inputs.items():
                    lines.append(f"      {key}: {value}")

            if node.params:
                lines.append("    params:")
                for key, value in node.params.items():
                    lines.append(f"      {key}: {value}")

            if node.is_result:
                lines.append("    isResult: true")

            lines.append("")

        return "\n".join(lines)

    async def generate_with_llm(
        self,
        task_master_ids: list[str],
        job_master_id: str,
        interfaces: dict[str, InterfaceSchema],
        context: "ExecutionContext",
    ) -> YamlGenerationResult:
        """Generate GraphAI YAML workflow using LLM.

        This method uses LLM to generate more sophisticated workflows
        based on the task descriptions and interfaces.

        Args:
            task_master_ids: List of TaskMaster IDs
            job_master_id: JobMaster ID
            interfaces: Interface schemas
            context: Execution context

        Returns:
            YamlGenerationResult with LLM-generated YAML

        Raises:
            WorkflowError: If LLM generation fails
        """
        # Placeholder - will be connected to LLM in Phase E
        logger.info(
            "LLM-based YAML generation requested for job %s",
            context.job_id,
        )

        # Fall back to template generation for now
        return await self.generate(
            task_master_ids=task_master_ids,
            job_master_id=job_master_id,
            interfaces=interfaces,
            context=context,
        )


def create_yaml_generation_prompt(
    task_descriptions: list[dict[str, Any]],
    interfaces: dict[str, InterfaceSchema],
) -> str:
    """Create prompt for LLM-based YAML generation.

    Args:
        task_descriptions: List of task description dicts
        interfaces: Interface schemas

    Returns:
        Formatted prompt string
    """
    task_info_lines = []
    for task in task_descriptions:
        task_info_lines.append(f"Task: {task.get('name', 'Unknown')}")
        task_info_lines.append(f"  Description: {task.get('description', 'N/A')}")
        task_info_lines.append(f"  API: {task.get('recommended_api', 'N/A')}")

    return f"""## Tasks
{chr(10).join(task_info_lines)}

## Requirements
Generate a GraphAI YAML workflow that:
1. Chains the tasks in order
2. Maps data flow correctly between nodes
3. Uses appropriate agents for each task type
4. Returns the final result

Please generate valid GraphAI YAML.
"""
