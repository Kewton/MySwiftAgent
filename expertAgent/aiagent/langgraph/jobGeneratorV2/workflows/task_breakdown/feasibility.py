"""FeasibilitySubWorkflow for Job Generator V2.

This module implements the feasibility checking sub-workflow that:
1. Loads available capabilities from YAML config
2. Checks each task against available capabilities
3. Returns FeasibilityReport with feasible/infeasible tasks

Issue #342 Phase B.2: Migrate logic from evaluator.py (feasibility check part)

Key design decisions:
- Capabilities are loaded from expert_agent_capabilities.yaml
- Matching is done by endpoint prefix comparison
- Recommendations are provided for infeasible tasks
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from aiagent.langgraph.jobGeneratorV2.types_old import (
    Capability,
    FeasibilityReport,
    TaskDefinition,
)

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext

logger = logging.getLogger(__name__)

# Path to capabilities config
_CAPABILITIES_YAML_PATH = (
    Path(__file__).parent.parent.parent.parent
    / "jobTaskGeneratorAgents"
    / "utils"
    / "config"
    / "expert_agent_capabilities.yaml"
)


def load_capabilities_from_yaml(
    config_path: Path | None = None,
) -> list[Capability]:
    """Load capabilities from YAML configuration file.

    Args:
        config_path: Optional path to config file. Uses default if not provided.

    Returns:
        List of Capability instances
    """
    path = config_path or _CAPABILITIES_YAML_PATH

    if not path.exists():
        logger.warning("Capabilities config not found at %s", path)
        return []

    try:
        with open(path, encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logger.error("Failed to load capabilities config: %s", e)
        return []

    capabilities: list[Capability] = []

    # Parse utility APIs
    for api in config.get("utility_apis", []):
        cap = _parse_api_to_capability(api)
        if cap:
            capabilities.append(cap)

    # Parse AI agent APIs
    for api in config.get("ai_agent_apis", []):
        cap = _parse_api_to_capability(api)
        if cap:
            capabilities.append(cap)

    logger.info("Loaded %d capabilities from config", len(capabilities))
    return capabilities


def _parse_api_to_capability(api: dict) -> Capability | None:
    """Parse API definition to Capability.

    Args:
        api: API definition dict from YAML

    Returns:
        Capability instance or None if invalid
    """
    name = api.get("name")
    endpoint = api.get("endpoint")

    if not name or not endpoint:
        return None

    # Build input schema from request_schema
    input_schema: dict = {"type": "object", "properties": {}}
    if request_schema := api.get("request_schema"):
        properties = {}
        required = []
        for key, value in request_schema.items():
            prop = {"type": value.get("type", "string")}
            if desc := value.get("description"):
                prop["description"] = desc
            properties[key] = prop
            if value.get("required"):
                required.append(key)
        input_schema["properties"] = properties
        if required:
            input_schema["required"] = required

    # Build output schema from response_schema
    output_schema: dict = {"type": "object", "properties": {}}
    if response_schema := api.get("response_schema"):
        properties = {}
        for key, value in response_schema.items():
            prop = {"type": value.get("type", "string")}
            if desc := value.get("description"):
                prop["description"] = desc
            properties[key] = prop
        output_schema["properties"] = properties

    return Capability(
        name=name,
        description=api.get("description", ""),
        endpoint=endpoint,
        input_schema=input_schema,
        output_schema=output_schema,
    )


def _is_api_available(
    task_api: str,
    capabilities: list[Capability],
) -> bool:
    """Check if a task's recommended API is available.

    Args:
        task_api: The task's recommended API endpoint
        capabilities: Available capabilities

    Returns:
        True if API is available
    """
    if not task_api:
        # No specific API recommended - might be generic
        return True

    task_api_lower = task_api.lower()

    for cap in capabilities:
        # Check exact match
        if cap.endpoint.lower() == task_api_lower:
            return True

        # Check if task API is a prefix match (e.g., /v1/utility vs /v1/utility/gmail/send)
        if task_api_lower.startswith(cap.endpoint.lower()):
            return True

        # Check if capability endpoint contains task API
        if cap.endpoint.lower().startswith(task_api_lower):
            return True

    return False


def _generate_recommendations(
    infeasible_tasks: list[TaskDefinition],
    capabilities: list[Capability],
) -> list[str]:
    """Generate recommendations for infeasible tasks.

    Args:
        infeasible_tasks: List of infeasible task definitions
        capabilities: Available capabilities

    Returns:
        List of recommendation strings
    """
    recommendations: list[str] = []

    for task in infeasible_tasks:
        task_type = task.task_type.lower()
        api = task.recommended_api.lower()

        # Suggest alternatives based on task type
        if "slack" in api or "slack" in task_type:
            recommendations.append(
                f"Task '{task.name}' uses Slack API which is not available. "
                f"Consider using Gmail send (/v1/utility/gmail/send) instead."
            )
        elif "notification" in task_type:
            recommendations.append(
                f"Task '{task.name}' requires notification. "
                f"Available options: Gmail send (/v1/utility/gmail/send)."
            )
        else:
            # Find similar capabilities
            similar = _find_similar_capabilities(task, capabilities)
            if similar:
                similar_names = ", ".join(s.name for s in similar[:3])
                recommendations.append(
                    f"Task '{task.name}' uses unavailable API '{task.recommended_api}'. "
                    f"Similar capabilities: {similar_names}"
                )
            else:
                recommendations.append(
                    f"Task '{task.name}' uses unavailable API '{task.recommended_api}'. "
                    f"No similar capabilities found."
                )

    return recommendations


def _find_similar_capabilities(
    task: TaskDefinition,
    capabilities: list[Capability],
) -> list[Capability]:
    """Find capabilities similar to a task.

    Args:
        task: Task to find alternatives for
        capabilities: Available capabilities

    Returns:
        List of similar capabilities
    """
    similar: list[Capability] = []
    task_words = set(task.description.lower().split())

    for cap in capabilities:
        cap_words = set(cap.description.lower().split())
        # Check word overlap
        overlap = task_words & cap_words
        if len(overlap) >= 2:
            similar.append(cap)

    return similar


class FeasibilitySubWorkflow:
    """Sub-workflow for checking task feasibility.

    This class checks whether each task can be executed with
    available capabilities.

    Example:
        capabilities = load_capabilities_from_yaml()
        feasibility = FeasibilitySubWorkflow(capabilities=capabilities)
        report = await feasibility.check(tasks, context)
    """

    def __init__(self, capabilities: list[Capability] | None = None):
        """Initialize FeasibilitySubWorkflow.

        Args:
            capabilities: List of available capabilities. If None, loads from YAML.
        """
        if capabilities is None:
            self._capabilities = load_capabilities_from_yaml()
        else:
            self._capabilities = capabilities

    async def check(
        self,
        tasks: list[TaskDefinition],
        context: "ExecutionContext",
    ) -> FeasibilityReport:
        """Check feasibility of tasks.

        Args:
            tasks: List of tasks to check
            context: Execution context

        Returns:
            FeasibilityReport with results
        """
        logger.info(
            "Checking feasibility for %d tasks (job %s)",
            len(tasks),
            context.job_id,
        )

        if not tasks:
            return FeasibilityReport(
                is_feasible=True,
                infeasible_tasks=[],
                recommendations=[],
            )

        infeasible_task_ids: list[str] = []
        infeasible_tasks: list[TaskDefinition] = []

        for task in tasks:
            if not _is_api_available(task.recommended_api, self._capabilities):
                infeasible_task_ids.append(task.id)
                infeasible_tasks.append(task)
                logger.warning(
                    "Task '%s' (%s) uses unavailable API: %s",
                    task.name,
                    task.id,
                    task.recommended_api,
                )

        recommendations = _generate_recommendations(
            infeasible_tasks, self._capabilities
        )

        is_feasible = len(infeasible_task_ids) == 0

        logger.info(
            "Feasibility check complete: %d/%d tasks feasible",
            len(tasks) - len(infeasible_task_ids),
            len(tasks),
        )

        return FeasibilityReport(
            is_feasible=is_feasible,
            infeasible_tasks=infeasible_task_ids,
            recommendations=recommendations,
        )
