"""Tests for GraphAI workflow schemas.

Issue #342 Phase F: WorkflowGen V2 LLM Integration
"""

import pytest
from pydantic import ValidationError

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas import (
    AVAILABLE_AGENTS,
    GraphAIWorkflowSchema,
    NodeDefinition,
    is_valid_agent,
)


class TestNodeDefinition:
    """Tests for NodeDefinition Pydantic model."""

    def test_create_valid_node(self):
        """Test creating a valid node definition."""
        node = NodeDefinition(
            agent="fetchAgent",
            inputs={"url": "http://example.com"},
            params={"timeout": 30},
            isResult=False,
        )
        assert node.agent == "fetchAgent"
        assert node.inputs["url"] == "http://example.com"
        assert node.params["timeout"] == 30
        assert node.isResult is False

    def test_node_with_is_result(self):
        """Test node with isResult flag."""
        node = NodeDefinition(
            agent="copyAgent",
            isResult=True,
        )
        assert node.isResult is True

    def test_node_agent_not_empty(self):
        """Test that agent name cannot be empty."""
        with pytest.raises(ValidationError):
            NodeDefinition(agent="")

    def test_node_agent_whitespace_trimmed(self):
        """Test that agent name whitespace is trimmed."""
        node = NodeDefinition(agent="  fetchAgent  ")
        assert node.agent == "fetchAgent"

    def test_node_with_console(self):
        """Test node with console logging settings."""
        node = NodeDefinition(
            agent="fetchAgent",
            console={"after": True},
        )
        assert node.console == {"after": True}

    def test_node_with_timeout(self):
        """Test node with timeout setting."""
        node = NodeDefinition(
            agent="fetchAgent",
            timeout=180,
        )
        assert node.timeout == 180

    def test_node_with_nested_graph(self):
        """Test node with nested graph (for mapAgent)."""
        node = NodeDefinition(
            agent="mapAgent",
            inputs={"rows": ":source.items"},
            graph={"nodes": {"item_source": {}}},
        )
        assert node.graph is not None
        assert "nodes" in node.graph


class TestGraphAIWorkflowSchema:
    """Tests for GraphAIWorkflowSchema Pydantic model."""

    def test_create_valid_workflow(self):
        """Test creating a valid workflow schema."""
        workflow = GraphAIWorkflowSchema(
            version="0.5",
            nodes={
                "source": {},
                "output": NodeDefinition(agent="copyAgent", isResult=True),
            },
        )
        assert workflow.version == "0.5"
        assert "source" in workflow.nodes
        assert "output" in workflow.nodes

    def test_workflow_requires_source_node(self):
        """Test that source node is required."""
        with pytest.raises(ValidationError) as exc_info:
            GraphAIWorkflowSchema(
                version="0.5",
                nodes={
                    "output": NodeDefinition(agent="copyAgent", isResult=True),
                },
            )
        assert "source node is required" in str(exc_info.value)

    def test_workflow_requires_is_result_node(self):
        """Test that at least one isResult node is required."""
        with pytest.raises(ValidationError) as exc_info:
            GraphAIWorkflowSchema(
                version="0.5",
                nodes={
                    "source": {},
                    "process": NodeDefinition(agent="fetchAgent"),
                },
            )
        assert "isResult=True" in str(exc_info.value)

    def test_workflow_default_version(self):
        """Test workflow default version is 0.5."""
        workflow = GraphAIWorkflowSchema(
            nodes={
                "source": {},
                "output": NodeDefinition(agent="copyAgent", isResult=True),
            },
        )
        assert workflow.version == "0.5"

    def test_workflow_to_yaml(self):
        """Test converting workflow to YAML string."""
        workflow = GraphAIWorkflowSchema(
            version="0.5",
            nodes={
                "source": {},
                "output": NodeDefinition(agent="copyAgent", isResult=True),
            },
        )
        yaml_str = workflow.to_yaml()
        assert "version:" in yaml_str
        assert "0.5" in yaml_str
        assert "nodes:" in yaml_str
        assert "source:" in yaml_str
        assert "output:" in yaml_str
        assert "copyAgent" in yaml_str

    def test_workflow_to_yaml_includes_inputs(self):
        """Test that YAML includes inputs."""
        workflow = GraphAIWorkflowSchema(
            version="0.5",
            nodes={
                "source": {},
                "api_call": NodeDefinition(
                    agent="fetchAgent",
                    inputs={"url": "http://example.com", "method": "POST"},
                ),
                "output": NodeDefinition(
                    agent="copyAgent",
                    inputs={"data": ":api_call.result"},
                    isResult=True,
                ),
            },
        )
        yaml_str = workflow.to_yaml()
        assert "inputs:" in yaml_str
        assert "http://example.com" in yaml_str

    def test_workflow_with_dict_nodes(self):
        """Test workflow accepts raw dict nodes."""
        workflow = GraphAIWorkflowSchema(
            version="0.5",
            nodes={
                "source": {},
                "output": {"agent": "copyAgent", "isResult": True},
            },
        )
        assert workflow.version == "0.5"


class TestAvailableAgents:
    """Tests for AVAILABLE_AGENTS list."""

    def test_available_agents_not_empty(self):
        """Test that available agents list is not empty."""
        assert len(AVAILABLE_AGENTS) > 0

    def test_fetch_agent_available(self):
        """Test fetchAgent is in the list."""
        assert "fetchAgent" in AVAILABLE_AGENTS

    def test_copy_agent_available(self):
        """Test copyAgent is in the list."""
        assert "copyAgent" in AVAILABLE_AGENTS

    def test_map_agent_available(self):
        """Test mapAgent is in the list."""
        assert "mapAgent" in AVAILABLE_AGENTS

    def test_string_template_agent_available(self):
        """Test stringTemplateAgent is in the list."""
        assert "stringTemplateAgent" in AVAILABLE_AGENTS


class TestIsValidAgent:
    """Tests for is_valid_agent function."""

    def test_valid_agent(self):
        """Test valid agent returns True."""
        assert is_valid_agent("fetchAgent") is True

    def test_invalid_agent(self):
        """Test invalid agent returns False."""
        assert is_valid_agent("nonExistentAgent") is False

    def test_case_sensitive(self):
        """Test agent check is case sensitive."""
        assert is_valid_agent("FetchAgent") is False  # Wrong case
        assert is_valid_agent("fetchAgent") is True   # Correct case
