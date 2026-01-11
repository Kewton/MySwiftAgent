"""Pydantic schemas for GraphAI Workflow V2.

This module defines Pydantic models for structured LLM output,
ensuring generated workflows conform to GraphAI specifications.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

from __future__ import annotations

from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class NodeDefinition(BaseModel):
    """GraphAI node definition.

    Attributes:
        agent: Agent type (e.g., 'fetchAgent', 'stringTemplateAgent')
        inputs: Input definitions with :node.path references
        params: Agent-specific parameters
        isResult: Flag for final output node
        console: Debug logging settings
        timeout: Optional timeout in seconds
        retry: Optional retry count
    """

    model_config = ConfigDict(extra="allow")

    agent: str = Field(description="Agent type name")
    inputs: dict[str, Any] | None = Field(default=None, description="Input definitions")
    params: dict[str, Any] | None = Field(default=None, description="Agent parameters")
    isResult: bool = Field(default=False, description="Final output node flag")
    console: dict[str, Any] | None = Field(
        default=None, description="Debug logging settings"
    )
    timeout: int | None = Field(default=None, description="Timeout in seconds")
    retry: int | None = Field(default=None, description="Retry count")
    graph: dict[str, Any] | None = Field(
        default=None, description="Nested graph for mapAgent/nestedAgent"
    )

    @field_validator("agent")
    @classmethod
    def validate_agent_not_empty(cls, v: str) -> str:
        """Validate agent name is not empty."""
        if not v or not v.strip():
            raise ValueError("agent must not be empty")
        return v.strip()


class SourceNodeDefinition(BaseModel):
    """Source node definition (empty object).

    The source node is the entry point for user input.
    """

    model_config = ConfigDict(extra="allow")


class GraphAIWorkflowSchema(BaseModel):
    """GraphAI workflow schema for structured LLM output.

    This schema ensures LLM-generated workflows conform to GraphAI specs.
    Version 0.5 is the current GraphAI version.

    Attributes:
        version: GraphAI version (must be '0.5')
        nodes: Dictionary of node definitions
    """

    model_config = ConfigDict(extra="forbid")

    version: str = Field(default="0.5", description="GraphAI version")
    nodes: dict[str, NodeDefinition | SourceNodeDefinition | dict] = Field(
        description="Node definitions"
    )

    @field_validator("version", mode="before")
    @classmethod
    def coerce_version_to_string(cls, v: Any) -> str:
        """Coerce version to string (YAML parses 0.5 as float)."""
        if isinstance(v, float):
            return str(v)
        return str(v) if v is not None else "0.5"

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Validate version is supported."""
        supported_versions = {"0.5", "0.6"}
        if v not in supported_versions:
            raise ValueError(f"version must be one of {supported_versions}, got '{v}'")
        return v

    @model_validator(mode="after")
    def validate_workflow_structure(self) -> "GraphAIWorkflowSchema":
        """Validate workflow has source node and at least one isResult node.

        Auto-adds source node if missing (LLMs sometimes omit it).
        """
        # Auto-add source node if missing (LLMs sometimes forget it)
        if "source" not in self.nodes:
            # Create a new dict to avoid modifying during iteration
            self.nodes = {"source": SourceNodeDefinition(), **self.nodes}

        # Check for at least one isResult node
        has_result = False
        for name, node in self.nodes.items():
            if name == "source":
                continue
            if isinstance(node, NodeDefinition) and node.isResult:
                has_result = True
                break
            if isinstance(node, dict) and node.get("isResult"):
                has_result = True
                break

        if not has_result:
            raise ValueError("At least one node must have isResult=True")

        return self

    def to_yaml(self) -> str:
        """Convert to YAML string.

        Returns:
            YAML representation of the workflow.
        """
        # Convert to dict, handling nested models
        workflow_dict = self._to_clean_dict()

        return yaml.dump(
            workflow_dict,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    def _to_clean_dict(self) -> dict[str, Any]:
        """Convert to clean dictionary, removing None values.

        Returns:
            Dictionary representation with None values removed.
        """
        result: dict[str, Any] = {"version": self.version, "nodes": {}}
        nodes_dict: dict[str, Any] = result["nodes"]

        for name, node in self.nodes.items():
            if name == "source":
                # Source node is always empty dict
                nodes_dict["source"] = {}
            elif isinstance(node, NodeDefinition):
                node_dict: dict[str, Any] = {}
                if node.agent:
                    node_dict["agent"] = node.agent
                if node.inputs is not None:
                    node_dict["inputs"] = node.inputs
                if node.params is not None:
                    node_dict["params"] = node.params
                if node.isResult:
                    node_dict["isResult"] = True
                if node.console is not None:
                    node_dict["console"] = node.console
                if node.timeout is not None:
                    node_dict["timeout"] = node.timeout
                if node.retry is not None:
                    node_dict["retry"] = node.retry
                if node.graph is not None:
                    node_dict["graph"] = node.graph
                nodes_dict[name] = node_dict
            elif isinstance(node, dict):
                # Pass through raw dicts (e.g., source: {})
                nodes_dict[name] = {k: v for k, v in node.items() if v is not None}

        return result


# Available agents list for validation
AVAILABLE_AGENTS = [
    # LLM Agents
    "anthropicAgent",
    "geminiAgent",
    "openAIAgent",
    "groqAgent",
    "replicateAgent",
    # HTTP/Fetch Agents
    "fetchAgent",
    "openAIFetchAgent",
    "vanillaFetchAgent",
    # Data Transform Agents
    "arrayJoinAgent",
    "arrayFlatAgent",
    "arrayToObjectAgent",
    "arrayFindFirstExistsAgent",
    "copy2ArrayAgent",
    "copyAgent",
    "copyMessageAgent",
    "mergeObjectAgent",
    "mergeNodeIdAgent",
    "propertyFilterAgent",
    "popAgent",
    "pushAgent",
    "shiftAgent",
    # String Processing Agents
    "stringTemplateAgent",
    "stringSplitterAgent",
    "stringCaseVariantsAgent",
    "stringUpdateTextAgent",
    "stringEmbeddingsAgent",
    "jsonParserAgent",
    # Numeric Agents
    "totalAgent",
    "countingAgent",
    "dotProductAgent",
    "dataSumTemplateAgent",
    "dataObjectMergeTemplateAgent",
    # Control Flow Agents
    "mapAgent",
    "nestedAgent",
    "compareAgent",
    "sortByValuesAgent",
    # Utility Agents
    "echoAgent",
    "consoleAgent",
    "sleeperAgent",
    "sleeperAgentDebug",
    "sleepAndMergeAgent",
    "textInputAgent",
    "lookupDictionaryAgent",
    # External Service Agents
    "wikipediaAgent",
    "images2messageAgent",
    "openAIImageAgent",
    # Additional Agents
    "tokenBoundStringsAgent",
    "fileReadAgent",
    "fileWriteAgent",
    "pathUtilsAgent",
]


def is_valid_agent(agent_name: str) -> bool:
    """Check if an agent name is valid.

    Args:
        agent_name: Name of the agent to check.

    Returns:
        True if the agent is in the available agents list.
    """
    return agent_name in AVAILABLE_AGENTS
