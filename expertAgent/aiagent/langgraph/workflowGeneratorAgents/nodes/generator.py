"""Generator node for GraphAI workflow YAML generation.

Issue #338: Added structural completeness validation to detect and reject
incomplete workflows early in the generation process.
"""

import logging
from pathlib import Path
from typing import Any

import yaml

from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
    StructuredLLMError,
    invoke_structured_llm,
)
from aiagent.langgraph.jobTaskGeneratorAgents.utils.workflow_helper import (
    get_api_response_schemas,
)

from ..prompts.workflow_generation import (
    WORKFLOW_GENERATION_SYSTEM_PROMPT,
    WorkflowGenerationResponse,
    create_workflow_generation_prompt,
    create_workflow_generation_prompt_with_feedback,
)
from ..state import WorkflowGeneratorState

logger = logging.getLogger(__name__)


def _validate_workflow_completeness(yaml_content: str) -> tuple[bool, list[str]]:
    """Validate that the generated workflow is structurally complete.

    Issue #338: This function checks for common incompleteness patterns
    that cause workflow execution failures.

    Args:
        yaml_content: Generated YAML content

    Returns:
        Tuple of (is_complete, list of issues)
    """
    if not yaml_content or not yaml_content.strip():
        return False, ["YAML content is empty"]

    issues: list[str] = []

    # Try to parse the YAML
    try:
        workflow: dict[str, Any] = yaml.safe_load(yaml_content)
        if not isinstance(workflow, dict):
            return False, ["YAML content is not a valid workflow dictionary"]
    except yaml.YAMLError as e:
        return False, [f"YAML parse error: {e}"]

    # Check for required top-level fields
    if "version" not in workflow:
        issues.append("Missing 'version' field at top level")

    if "nodes" not in workflow:
        issues.append("Missing 'nodes' section")
        return False, issues

    nodes = workflow.get("nodes", {})
    if not isinstance(nodes, dict) or not nodes:
        issues.append("'nodes' section is empty or invalid")
        return False, issues

    # Check for source node
    if "source" not in nodes:
        issues.append("Missing required 'source' node")

    # Check for output node with isResult: true
    has_result_node = False
    for _node_id, node_def in nodes.items():
        if isinstance(node_def, dict) and node_def.get("isResult") is True:
            has_result_node = True
            break

    if not has_result_node:
        issues.append("Missing output node with 'isResult: true'")

    # Check for truncated template blocks
    # Pattern: template: |- followed by incomplete content
    if "template: |-" in yaml_content or "template: |" in yaml_content:
        # Check if the YAML ends abruptly in a template block
        lines = yaml_content.strip().split("\n")
        last_lines = lines[-5:] if len(lines) >= 5 else lines
        last_content = "\n".join(last_lines)

        # Signs of truncation:
        # - Ends with an incomplete line (no proper closing)
        # - Ends mid-sentence without JSON closing brace
        if last_content.strip().endswith("|-") or last_content.strip().endswith("|"):
            issues.append("Template block appears truncated (ends with '|-' or '|')")
        elif "# RESPONSE_FORMAT:" in yaml_content:
            # If there's a RESPONSE_FORMAT section, check it has closing braces
            if yaml_content.count("{") > yaml_content.count("}"):
                issues.append(
                    "Template block may be truncated (unbalanced braces in RESPONSE_FORMAT)"
                )

    # Check minimum node count (source + at least one processing node + output)
    if len(nodes) < 2:
        issues.append(
            f"Workflow has only {len(nodes)} node(s), minimum 2 required (source + output)"
        )

    is_complete = len(issues) == 0
    return is_complete, issues


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

    # Issue #338 Phase 3: Get API response schemas for recommended APIs
    recommended_apis = task_data.get("recommended_apis", [])
    api_schemas: dict = {}
    if recommended_apis:
        try:
            api_schemas = await get_api_response_schemas(recommended_apis)
            logger.info(
                "Retrieved API schemas for %d APIs: %s",
                len(api_schemas),
                list(api_schemas.keys()),
            )
        except Exception as e:
            logger.warning(f"Failed to get API schemas: {e}")
            # Continue without schemas (non-blocking)

    # Create prompt (with feedback and API schemas if available)
    if error_feedback:
        user_prompt = create_workflow_generation_prompt_with_feedback(
            task_data,
            graphai_capabilities,
            expert_agent_capabilities,
            error_feedback,
            api_schemas=api_schemas,
        )
    else:
        user_prompt = create_workflow_generation_prompt(
            task_data, graphai_capabilities, expert_agent_capabilities, api_schemas
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

        # Issue #338: Validate workflow structural completeness
        is_complete, completeness_issues = _validate_workflow_completeness(
            response.yaml_content
        )

        if not is_complete:
            logger.warning(
                "Generated workflow is structurally incomplete: %s",
                completeness_issues,
            )
            # Add completeness issues to error_feedback for self-repair
            completeness_feedback = (
                "WORKFLOW COMPLETENESS ERRORS:\n"
                + "\n".join(f"- {issue}" for issue in completeness_issues)
                + "\n\nYou MUST generate a COMPLETE workflow with all required components."
            )

            generation_attempts = state.get("generation_retry_count", 0) + 1
            return {
                **state,
                "yaml_content": response.yaml_content,
                "workflow_name": response.workflow_name,
                "generation_retry_count": generation_attempts,
                "generation_model": call_result.model_name,
                "status": "incomplete_workflow",
                "error_feedback": completeness_feedback,
                "validation_errors": completeness_issues,
                "has_schema_errors": True,  # Trigger self-repair via schema_validator_router
            }

        logger.info("Workflow completeness validation passed")
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
