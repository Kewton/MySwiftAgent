"""YAML generator sub-workflow for WorkflowGen.

This module provides the YamlGeneratorSubWorkflow that:
1. Generates GraphAI YAML workflow definitions
2. Defines task chains based on dependencies
3. Uses LLM to generate workflow YAML when needed
4. Validates generated YAML using ValidationPipeline (Issue #342 INT-1)

Issue #342 Phase D.2: Migrated logic from jobTaskGeneratorAgents
without importing from the old code.

Issue #342 V2 Workflow Quality Improvement:
- LLM-first generation with template fallback
- Deprecated template-only methods (generate, _build_workflow_nodes, _generate_yaml)
- Removed dead code (create_yaml_generation_prompt)

Issue #342 Iteration 2: Dead code integration
- INT-1: ValidationPipeline integration for LLM output validation

Key design decisions:
- Uses ExecutionContext for LLM access (dependency injection)
- Does NOT import from langgraph or old jobTaskGeneratorAgents
- Default: LLM-based generation with automatic template fallback
- Validates LLM output with ValidationPipeline before returning
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from aiagent.langgraph.jobGeneratorV2.pipeline import ValidationPipeline
from aiagent.langgraph.jobGeneratorV2.protocols import (
    ErrorType,
    WorkflowError,
)
from aiagent.langgraph.jobGeneratorV2.types import (
    InterfaceSchema,
    Phase,
    TaskIdMapping,
)

# Phase F imports for LLM-based generation
from .llm_generator import LLMGeneratorSubWorkflow
from .yaml_validator import YamlValidatorSubWorkflow

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext

logger = logging.getLogger(__name__)


def _normalize_task_id(
    task_master_id: str,
    task_id_mapping: TaskIdMapping | None = None,
) -> str:
    """Normalize task_master_id to task_id using mapping or prefix removal.

    Issue #342 Bug #1/12: This function now supports TaskIdMapping for correct
    interface lookup instead of relying on prefix removal which may fail for
    non-standard task IDs.

    Args:
        task_master_id: Task master ID (e.g., 'tm_task_001' or 'tm_01KEC...')
        task_id_mapping: Optional TaskIdMapping for proper reverse lookup

    Returns:
        Task ID without prefix (e.g., 'task_001')
    """
    # Bug #1/12 fix: Use TaskIdMapping if available
    if task_id_mapping is not None:
        logical_id = task_id_mapping.get_logical_id(task_master_id)
        if logical_id is not None:
            return logical_id
        # Fall back to prefix removal if not found in mapping
        logger.warning(
            "TaskIdMapping does not contain master_id %s, falling back to prefix removal",
            task_master_id,
        )

    # Legacy behavior: Remove 'tm_' prefix
    if task_master_id.startswith("tm_"):
        return task_master_id[3:]
    return task_master_id


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
    4. Validating output using ValidationPipeline (Issue #342 INT-1)

    Example:
        generator = YamlGeneratorSubWorkflow()
        result = await generator.generate(task_master_ids, interfaces, context)
    """

    def __init__(
        self,
        graphai_version: str = "0.6",
        use_llm_generation: bool = False,
        validation_pipeline: ValidationPipeline | None = None,
    ) -> None:
        """Initialize YamlGeneratorSubWorkflow.

        Args:
            graphai_version: GraphAI version for YAML
            use_llm_generation: Whether to use LLM for generation
            validation_pipeline: Optional ValidationPipeline for output validation.
                               Issue #342 INT-1: If None, a default pipeline is created.
        """
        self._graphai_version = graphai_version
        self._use_llm_generation = use_llm_generation

        # Issue #342 INT-1: Initialize validation pipeline
        self.validation_pipeline = validation_pipeline or ValidationPipeline()

    async def generate(
        self,
        task_master_ids: list[str],
        job_master_id: str,
        interfaces: dict[str, InterfaceSchema],
        context: "ExecutionContext",
    ) -> YamlGenerationResult:
        """Generate GraphAI YAML workflow using template-based approach.

        .. deprecated::
            Issue #342 V2: This method is deprecated. Use `generate_with_llm()`
            instead for LLM-first generation with automatic template fallback.
            This method is kept for backward compatibility only.

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
        import warnings

        warnings.warn(
            "generate() is deprecated. Use generate_with_llm() instead. "
            "Issue #342 V2 Workflow Quality Improvement.",
            DeprecationWarning,
            stacklevel=2,
        )

        logger.info(
            "Generating GraphAI YAML for job %s with %d tasks (DEPRECATED template)",
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

        .. deprecated::
            Issue #342 V2: This method is deprecated as part of template-based
            generation. LLM-based generation is now preferred.

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

        .. deprecated::
            Issue #342 V2: This method is deprecated as part of template-based
            generation. LLM-based generation is now preferred.

        Args:
            workflow_name: Name of the workflow
            nodes: List of node definitions

        Returns:
            YAML string
        """
        # Build YAML manually (avoiding yaml dependency for simplicity)
        lines = [
            f"# GraphAI Workflow: {workflow_name}",
            f'version: "{self._graphai_version}"',
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
        *,
        max_retries: int = 2,
        task_id_mapping: TaskIdMapping | None = None,
    ) -> YamlGenerationResult:
        """Generate GraphAI YAML workflow using LLM.

        This method uses LLM to generate more sophisticated workflows
        based on the task descriptions and interfaces.

        Issue #342 Phase F: Uses PromptBuilderSubWorkflow, LLMGeneratorSubWorkflow,
        and YamlValidatorSubWorkflow for high-quality YAML generation.

        Issue #342 Bug #1/12: Now accepts optional TaskIdMapping for correct
        interface lookup instead of relying on prefix removal.

        Args:
            task_master_ids: List of TaskMaster IDs
            job_master_id: JobMaster ID
            interfaces: Interface schemas
            context: Execution context
            max_retries: Maximum retry attempts for validation errors
            task_id_mapping: Optional TaskIdMapping for correct interface lookup

        Returns:
            YamlGenerationResult with LLM-generated YAML

        Raises:
            WorkflowError: If LLM generation fails after retries
        """
        logger.info(
            "LLM-based YAML generation for job %s with %d tasks",
            context.job_id,
            len(task_master_ids),
        )

        if not task_master_ids:
            raise WorkflowError(
                "No task masters provided for LLM YAML generation",
                ErrorType.VALIDATION,
                Phase.WORKFLOW_GEN,
            )

        # Build task definition from interfaces for the first task
        # In a chain, we generate for the last task (result node)
        result_task_id = task_master_ids[-1]
        # Issue #342 Bug #1/12: Use TaskIdMapping for correct interface lookup
        normalized_task_id = _normalize_task_id(result_task_id, task_id_mapping)
        result_interface = interfaces.get(normalized_task_id)

        if not result_interface:
            logger.warning(
                "No interface found for task %s, falling back to template",
                result_task_id,
            )
            return await self.generate(
                task_master_ids=task_master_ids,
                job_master_id=job_master_id,
                interfaces=interfaces,
                context=context,
            )

        # Initialize Phase F workflows
        llm_generator = LLMGeneratorSubWorkflow()
        yaml_validator = YamlValidatorSubWorkflow()

        # Build task context from all interfaces
        # Issue #342 Bug #12: Use TaskIdMapping for correct interface lookup
        task_description = self._build_task_description_from_chain(
            task_master_ids, interfaces, task_id_mapping
        )
        recommended_apis = self._extract_recommended_apis(interfaces)
        dependencies = task_master_ids[:-1] if len(task_master_ids) > 1 else []

        previous_errors: list = []
        attempt = 0

        while attempt <= max_retries:
            try:
                # Generate using LLMGeneratorSubWorkflow
                task_name = result_interface.task_id or f"task_{result_task_id}"
                llm_result = await llm_generator.generate_from_task(
                    task_name=task_name,
                    task_description=task_description,
                    input_schema=result_interface.input_schema or {},
                    output_schema=result_interface.output_schema or {},
                    recommended_apis=recommended_apis,
                    dependencies=dependencies,
                    context=context,
                )

                # Validate using YamlValidatorSubWorkflow (sync method)
                yaml_content = llm_result.yaml_content
                validation_result = yaml_validator.validate(yaml_content)

                if validation_result.is_valid:
                    # Issue #342 INT-1: Additional validation with ValidationPipeline
                    # Parse YAML to dict for pipeline validation
                    import yaml as yaml_lib

                    try:
                        workflow_dict = yaml_lib.safe_load(yaml_content)
                        if workflow_dict:
                            pipeline_result = self.validation_pipeline.validate(
                                workflow_dict,
                                workflow_id=f"{context.job_id}_{job_master_id}",
                            )
                            if not pipeline_result.is_valid:
                                # Use pipeline feedback for retry
                                logger.warning(
                                    "Pipeline validation failed (attempt %d/%d): %d errors",
                                    attempt + 1,
                                    max_retries + 1,
                                    len(pipeline_result.errors),
                                )
                                previous_errors = pipeline_result.errors
                                attempt += 1
                                continue
                    except Exception as parse_err:
                        logger.debug(
                            "Could not parse YAML for pipeline validation: %s",
                            parse_err,
                        )

                    logger.info(
                        "LLM YAML generation successful: %s (%d nodes, attempt %d)",
                        llm_result.workflow_name,
                        llm_result.node_count,
                        attempt + 1,
                    )
                    return YamlGenerationResult(
                        yaml_content=llm_result.yaml_content,
                        workflow_name=f"workflow_{job_master_id}",
                        node_count=llm_result.node_count,
                        generation_method="llm",
                    )

                # Validation failed - store errors for retry
                previous_errors = validation_result.errors
                logger.warning(
                    "LLM YAML validation failed (attempt %d/%d): %d errors",
                    attempt + 1,
                    max_retries + 1,
                    len(previous_errors),
                )
                attempt += 1

            except Exception as e:
                logger.error(
                    "LLM generation error (attempt %d/%d): %s",
                    attempt + 1,
                    max_retries + 1,
                    e,
                )
                attempt += 1
                # Don't raise - let loop continue or fall through to template fallback

        # All retries exhausted - fall back to template
        logger.warning(
            "LLM generation exhausted retries, falling back to template generation"
        )
        return await self.generate(
            task_master_ids=task_master_ids,
            job_master_id=job_master_id,
            interfaces=interfaces,
            context=context,
        )

    def _build_task_description_from_chain(
        self,
        task_master_ids: list[str],
        interfaces: dict[str, InterfaceSchema],
        task_id_mapping: TaskIdMapping | None = None,
    ) -> str:
        """Build combined task description from chain interfaces.

        Issue #342 Bug #12: Now accepts optional TaskIdMapping for correct
        interface lookup instead of relying on prefix removal.

        Args:
            task_master_ids: Task master IDs in execution order
            interfaces: Interface schemas
            task_id_mapping: Optional TaskIdMapping for correct interface lookup

        Returns:
            Combined task description
        """
        descriptions = []
        for idx, tm_id in enumerate(task_master_ids, 1):
            # Issue #342 Bug #12: Use TaskIdMapping for correct interface lookup
            task_id = _normalize_task_id(tm_id, task_id_mapping)
            interface = interfaces.get(task_id)
            if interface:
                name = interface.task_id or tm_id
                desc = interface.description or "No description"
                descriptions.append(f"{idx}. {name}: {desc}")
        return "\n".join(descriptions) if descriptions else "Workflow task chain"

    def _extract_recommended_apis(
        self,
        interfaces: dict[str, InterfaceSchema],
    ) -> list[str]:
        """Extract recommended APIs from all interfaces.

        Args:
            interfaces: Interface schemas

        Returns:
            List of unique recommended API names
        """
        apis: set[str] = set()
        for interface in interfaces.values():
            # Check for recommended_api field in interface
            if hasattr(interface, "recommended_api") and interface.recommended_api:
                apis.add(interface.recommended_api)
        return list(apis)


# Issue #342 V2: Dead code removed - create_yaml_generation_prompt()
# This function was superseded by PromptBuilderSubWorkflow.build()
# in Issue #342 Phase F: WorkflowGen V2 LLM Integration
