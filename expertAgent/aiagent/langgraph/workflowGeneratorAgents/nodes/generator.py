"""Generator node for GraphAI workflow YAML generation.

This module provides the generator node that creates GraphAI workflow YAML
files from TaskMaster metadata using LLM (Gemini 2.5 Flash).
"""

import logging
import os
from pathlib import Path

import yaml

from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_factory import create_llm

from ..prompts.workflow_generation import (
    WORKFLOW_GENERATION_SYSTEM_PROMPT,
    WorkflowGenerationResponse,
    create_workflow_generation_prompt,
    create_workflow_generation_prompt_with_feedback,
)
from ..state import WorkflowGeneratorState

logger = logging.getLogger(__name__)


def _load_capabilities() -> tuple[dict, dict]:
    """Load GraphAI and ExpertAgent capabilities from YAML files.

    Returns:
        Tuple of (graphai_capabilities, expert_agent_capabilities)
    """
    # Path to capabilities files (shared with jobTaskGeneratorAgents)
    base_path = (
        Path(__file__).parent.parent.parent
        / "jobTaskGeneratorAgents"
        / "utils"
        / "config"
    )

    graphai_path = base_path / "graphai_capabilities.yaml"
    expert_agent_path = base_path / "expert_agent_capabilities.yaml"

    # Load GraphAI capabilities
    with open(graphai_path, "r", encoding="utf-8") as f:
        graphai_capabilities = yaml.safe_load(f)

    # Load ExpertAgent capabilities
    with open(expert_agent_path, "r", encoding="utf-8") as f:
        expert_agent_capabilities = yaml.safe_load(f)

    return graphai_capabilities, expert_agent_capabilities


async def generator_node(
    state: WorkflowGeneratorState,
) -> WorkflowGeneratorState:
    """Generate GraphAI workflow YAML from TaskMaster metadata using LLM.

    This node:
    1. Loads available GraphAI agents and expertAgent APIs
    2. Creates prompt with task metadata and capabilities
    3. Invokes Gemini 2.5 Flash to generate YAML
    4. Updates state with generated YAML and workflow name

    Args:
        state: Current workflow generator state

    Returns:
        Updated state with generated YAML
    """
    logger.info("Starting generator node")

    task_data = state["task_data"]
    error_feedback = state.get("error_feedback")

    logger.debug(f"Generating workflow for task: {task_data.get('name')}")
    if error_feedback:
        logger.info("Error feedback detected - using feedback-enhanced prompt")
        logger.debug(f"Feedback: {error_feedback}")

    # Load capabilities
    logger.debug("Loading GraphAI and ExpertAgent capabilities")
    graphai_capabilities, expert_agent_capabilities = _load_capabilities()

    # Initialize LLM (Gemini 2.0 Flash) using llm_factory
    # This automatically retrieves API key from MyVault or environment variables
    max_tokens = int(os.getenv("WORKFLOW_GENERATOR_MAX_TOKENS", "8192"))
    model_name = os.getenv("WORKFLOW_GENERATOR_MODEL", "gemini-2.0-flash-exp")
    model = create_llm(
        model_name=model_name,
        temperature=0.0,
        max_tokens=max_tokens,
    )
    logger.debug(f"Using {model_name} with max_tokens={max_tokens} (API key retrieved from MyVault/env)")

    # Create structured output model
    structured_model = model.with_structured_output(WorkflowGenerationResponse)

    # Create prompt (with feedback if available)
    if error_feedback:
        user_prompt = create_workflow_generation_prompt_with_feedback(
            task_data, graphai_capabilities, expert_agent_capabilities, error_feedback
        )
    else:
        user_prompt = create_workflow_generation_prompt(
            task_data, graphai_capabilities, expert_agent_capabilities
        )

    logger.debug(f"Created workflow generation prompt (length: {len(user_prompt)})")

    try:
        # Invoke LLM
        messages = [
            {"role": "system", "content": WORKFLOW_GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        logger.info("Invoking LLM for workflow generation")
        response = await structured_model.ainvoke(messages)

        logger.info(f"Workflow generation completed: {response.workflow_name}")
        logger.debug(f"YAML length: {len(response.yaml_content)} characters")
        logger.debug(f"Reasoning: {response.reasoning}")

        # Update state
        return {
            **state,
            "yaml_content": response.yaml_content,
            "workflow_name": response.workflow_name,
            "generation_retry_count": state.get("generation_retry_count", 0) + 1,
            "status": "yaml_generated",
        }

    except Exception as e:
        logger.error(f"Error during workflow generation: {e}", exc_info=True)
        return {
            **state,
            "status": "failed",
            "error_message": f"Workflow generation failed: {str(e)}",
        }
