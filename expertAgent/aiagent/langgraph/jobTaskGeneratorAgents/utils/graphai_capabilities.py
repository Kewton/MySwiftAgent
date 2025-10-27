"""GraphAI and expertAgent capability management for feasibility evaluation.

This module provides structured data about available GraphAI standard agents
and expertAgent Direct APIs, used for evaluating task feasibility.

Configuration is loaded from YAML files in utils/config/ directory:
- graphai_capabilities.yaml: GraphAI standard agents
- expert_agent_capabilities.yaml: expertAgent Direct APIs
- infeasible_tasks.yaml: Common infeasible tasks and alternatives
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml


def _load_yaml_config(filename: str) -> dict:
    """Load YAML configuration file from utils/config directory.

    Args:
        filename: YAML filename in utils/config/ directory

    Returns:
        Parsed YAML data
    """
    config_dir = Path(__file__).parent / "config"
    config_path = config_dir / filename
    with open(config_path, encoding="utf-8") as f:
        result = yaml.safe_load(f)
        return result if isinstance(result, dict) else {}


@dataclass
class GraphAIAgent:
    """GraphAI standard agent capability."""

    name: str
    category: Literal["llm", "http", "data_transform", "control_flow"]
    description: str
    requires_api_key: bool = False
    api_key_name: str | None = None


@dataclass
class ExpertAgentAPI:
    """expertAgent Direct API capability."""

    name: str
    endpoint: str
    category: Literal["utility", "ai_agent"]
    description: str
    use_cases: list[str]


@dataclass
class InfeasibleTaskAlternative:
    """Alternative solution for infeasible tasks."""

    task_type: str
    reason: str
    alternative_api: str
    priority: Literal["high", "medium", "low"]
    notes: str


def _load_graphai_agents() -> list[GraphAIAgent]:
    """Load GraphAI agents from YAML configuration.

    Returns:
        List of GraphAIAgent objects
    """
    config = _load_yaml_config("graphai_capabilities.yaml")
    agents = []

    # Load LLM agents
    for agent in config.get("llm_agents", []):
        agents.append(
            GraphAIAgent(
                name=agent["name"],
                category="llm",
                description=agent["description"],
                requires_api_key=agent.get("requires_api_key", False),
                api_key_name=agent.get("api_key_name"),
            )
        )

    # Load HTTP agents
    for agent in config.get("http_agents", []):
        agents.append(
            GraphAIAgent(
                name=agent["name"],
                category="http",
                description=agent["description"],
            )
        )

    # Load data transform agents
    for agent in config.get("data_transform_agents", []):
        agents.append(
            GraphAIAgent(
                name=agent["name"],
                category="data_transform",
                description=agent["description"],
            )
        )

    # Load control flow agents
    for agent in config.get("control_flow_agents", []):
        agents.append(
            GraphAIAgent(
                name=agent["name"],
                category="control_flow",
                description=agent["description"],
            )
        )

    return agents


# ===== GraphAI Standard Agents =====
# Loaded from YAML at module load time (cached)
GRAPHAI_AGENTS = _load_graphai_agents()


def _load_expert_agent_apis() -> list[ExpertAgentAPI]:
    """Load expertAgent APIs from YAML configuration.

    Returns:
        List of ExpertAgentAPI objects
    """
    config = _load_yaml_config("expert_agent_capabilities.yaml")
    apis = []

    # Load Utility APIs
    for api in config.get("utility_apis", []):
        apis.append(
            ExpertAgentAPI(
                name=api["name"],
                endpoint=api["endpoint"],
                category="utility",
                description=api["description"],
                use_cases=api.get("use_cases", []),
            )
        )

    # Load AI Agent APIs
    for api in config.get("ai_agent_apis", []):
        apis.append(
            ExpertAgentAPI(
                name=api["name"],
                endpoint=api["endpoint"],
                category="ai_agent",
                description=api["description"],
                use_cases=api.get("use_cases", []),
            )
        )

    return apis


def _load_infeasible_tasks() -> list[InfeasibleTaskAlternative]:
    """Load infeasible tasks from YAML configuration.

    Returns:
        List of InfeasibleTaskAlternative objects
    """
    config = _load_yaml_config("infeasible_tasks.yaml")
    tasks = []

    for task in config.get("infeasible_tasks", []):
        tasks.append(
            InfeasibleTaskAlternative(
                task_type=task["task_type"],
                reason=task["reason"],
                alternative_api=task["alternative_api"],
                priority=task["priority"],
                notes=task["notes"],
            )
        )

    return tasks


# ===== expertAgent Direct APIs =====
# Loaded from YAML at module load time (cached)
EXPERT_AGENT_APIS = _load_expert_agent_apis()

# ===== Common Infeasible Tasks and Alternatives =====
# Loaded from YAML at module load time (cached)
INFEASIBLE_TASKS = _load_infeasible_tasks()


# ===== Utility Functions =====


def get_agent_by_name(agent_name: str) -> GraphAIAgent | None:
    """Get GraphAI agent by name.

    Args:
        agent_name: Agent name to search for

    Returns:
        GraphAIAgent if found, None otherwise
    """
    for agent in GRAPHAI_AGENTS:
        if agent.name == agent_name:
            return agent
    return None


def get_api_by_name(api_name: str) -> ExpertAgentAPI | None:
    """Get expertAgent API by name.

    Args:
        api_name: API name to search for

    Returns:
        ExpertAgentAPI if found, None otherwise
    """
    for api in EXPERT_AGENT_APIS:
        if api.name == api_name:
            return api
    return None


def find_alternative_for_task(
    task_type: str,
) -> InfeasibleTaskAlternative | None:
    """Find alternative solution for infeasible task.

    Args:
        task_type: Task type (e.g., "Slack通知")

    Returns:
        InfeasibleTaskAlternative if found, None otherwise
    """
    for alt in INFEASIBLE_TASKS:
        if task_type.lower() in alt.task_type.lower():
            return alt
    return None


def list_agents_by_category(
    category: Literal["llm", "http", "data_transform", "control_flow"],
) -> list[GraphAIAgent]:
    """List GraphAI agents by category.

    Args:
        category: Agent category

    Returns:
        List of GraphAIAgents in the specified category
    """
    return [agent for agent in GRAPHAI_AGENTS if agent.category == category]


def list_apis_by_category(
    category: Literal["utility", "ai_agent"],
) -> list[ExpertAgentAPI]:
    """List expertAgent APIs by category.

    Args:
        category: API category

    Returns:
        List of ExpertAgentAPIs in the specified category
    """
    return [api for api in EXPERT_AGENT_APIS if api.category == category]


def get_all_capabilities_summary() -> dict:
    """Get summary of all available capabilities.

    Returns:
        Dictionary with GraphAI agents, expertAgent APIs,
        and infeasible task alternatives
    """
    return {
        "graphai_agents": {
            "total": len(GRAPHAI_AGENTS),
            "by_category": {
                "llm": len(list_agents_by_category("llm")),
                "http": len(list_agents_by_category("http")),
                "data_transform": len(list_agents_by_category("data_transform")),
                "control_flow": len(list_agents_by_category("control_flow")),
            },
        },
        "expert_agent_apis": {
            "total": len(EXPERT_AGENT_APIS),
            "by_category": {
                "utility": len(list_apis_by_category("utility")),
                "ai_agent": len(list_apis_by_category("ai_agent")),
            },
        },
        "infeasible_tasks": {
            "total": len(INFEASIBLE_TASKS),
            "by_priority": {
                "high": len([t for t in INFEASIBLE_TASKS if t.priority == "high"]),
                "medium": len([t for t in INFEASIBLE_TASKS if t.priority == "medium"]),
                "low": len([t for t in INFEASIBLE_TASKS if t.priority == "low"]),
            },
        },
    }
