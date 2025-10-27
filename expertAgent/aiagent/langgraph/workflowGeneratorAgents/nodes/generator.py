"""Generator node for GraphAI workflow YAML generation."""

import logging
from pathlib import Path

import yaml

from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
    StructuredLLMError,
    invoke_structured_llm,
)

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

    task_data = state.get("task_data")
    if task_data is None:
        message = "Workflow generation failed: task_data missing from state"
        logger.error(message)
        return {
            **state,
            "status": "failed",
            "error_message": message,
        }
    error_feedback = state.get("error_feedback")

    logger.debug(f"Generating workflow for task: {task_data.get('name')}")
    if error_feedback:
        logger.info("Error feedback detected - using feedback-enhanced prompt")
        logger.debug(f"Feedback: {error_feedback}")

    # Load capabilities
    logger.debug("Loading GraphAI and ExpertAgent capabilities")
    graphai_capabilities, expert_agent_capabilities = _load_capabilities()

    # Create prompt (with feedback if available)
    if error_feedback:
        user_prompt = create_workflow_generation_prompt_with_feedback(
            task_data,
            graphai_capabilities,
            expert_agent_capabilities,
            error_feedback,
        )
    else:
        user_prompt = create_workflow_generation_prompt(
            task_data, graphai_capabilities, expert_agent_capabilities
        )

    logger.debug(
        "Created workflow generation prompt (length: %s)",
        len(user_prompt),
    )

    try:
        messages = [
            {"role": "system", "content": WORKFLOW_GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        logger.info("Invoking LLM for workflow generation")
        call_result = await invoke_structured_llm(
            messages=messages,
            response_model=WorkflowGenerationResponse,
            context_label="workflow_generation",
            model_env_var="WORKFLOW_GENERATOR_MODEL",
            default_model="gemini-2.0-flash-exp",
            max_tokens_env_var="WORKFLOW_GENERATOR_MAX_TOKENS",
            default_max_tokens=8192,
        )

        response = call_result.result

        logger.info(
            "Workflow generation completed: %s (model=%s)",
            response.workflow_name,
            call_result.model_name,
        )
        logger.debug("YAML length: %s characters", len(response.yaml_content))
        logger.debug("Reasoning: %s", response.reasoning)
        if call_result.recovered_via_json:
            logger.info("Workflow generation succeeded via JSON fallback")

        generation_attempts = state.get("generation_retry_count", 0) + 1
        return {
            **state,
            "yaml_content": response.yaml_content,
            "workflow_name": response.workflow_name,
            "generation_retry_count": generation_attempts,
            "generation_model": call_result.model_name,
            "status": "yaml_generated",
        }

    except StructuredLLMError as exc:
        logger.error("Workflow generation failed: %s", exc)
        return {
            **state,
            "status": "failed",
            "error_message": str(exc),
        }

    except Exception as err:  # pragma: no cover - defensive logging
        logger.error(
            "Error during workflow generation: %s",
            err,
            exc_info=True,
        )
        return {
            **state,
            "status": "failed",
            "error_message": f"Workflow generation failed: {err}",
        }
