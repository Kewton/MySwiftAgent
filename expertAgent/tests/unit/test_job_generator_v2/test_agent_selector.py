"""Unit tests for AgentSelector - Issue #342 V2 Workflow Quality Improvement.

This module tests the AgentSelector class that maps API names to GraphAI agents.

Test Coverage Target: 95%
"""

from __future__ import annotations

import pytest


class TestAgentMapping:
    """Tests for AgentMapping dataclass."""

    def test_agent_mapping_creation(self) -> None:
        """Test AgentMapping dataclass can be created."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentMapping,
        )

        mapping = AgentMapping(
            api_name="gmail_send",
            agent_type="fetchAgent",
            endpoint_path="/v1/utility/gmail/send",
            http_method="POST",
        )

        assert mapping.api_name == "gmail_send"
        assert mapping.agent_type == "fetchAgent"
        assert mapping.endpoint_path == "/v1/utility/gmail/send"
        assert mapping.http_method == "POST"

    def test_agent_mapping_with_all_fields(self) -> None:
        """Test AgentMapping with description and default params."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentMapping,
        )

        mapping = AgentMapping(
            api_name="google_search",
            agent_type="fetchAgent",
            endpoint_path="/v1/utility/google_search",
            http_method="POST",
            description="Execute Google search",
            default_params={"timeout": 180},
        )

        assert mapping.description == "Execute Google search"
        assert mapping.default_params == {"timeout": 180}

    def test_agent_mapping_default_values(self) -> None:
        """Test AgentMapping default values."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentMapping,
        )

        mapping = AgentMapping(
            api_name="test_api",
            agent_type="fetchAgent",
            endpoint_path="/v1/test",
            http_method="GET",
        )

        assert mapping.description == ""
        assert mapping.default_params == {}


class TestAPIMappingsConstant:
    """Tests for API_AGENT_MAPPINGS constant."""

    def test_api_agent_mappings_exists(self) -> None:
        """Test API_AGENT_MAPPINGS constant exists."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            API_AGENT_MAPPINGS,
        )

        assert API_AGENT_MAPPINGS is not None
        assert isinstance(API_AGENT_MAPPINGS, dict)

    def test_gmail_send_mapping(self) -> None:
        """Test gmail_send mapping exists and is correct."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            API_AGENT_MAPPINGS,
        )

        assert "gmail_send" in API_AGENT_MAPPINGS
        mapping = API_AGENT_MAPPINGS["gmail_send"]
        assert mapping.agent_type == "fetchAgent"
        assert mapping.http_method == "POST"
        assert "/gmail" in mapping.endpoint_path.lower()

    def test_google_search_mapping(self) -> None:
        """Test google_search mapping exists and is correct."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            API_AGENT_MAPPINGS,
        )

        assert "google_search" in API_AGENT_MAPPINGS
        mapping = API_AGENT_MAPPINGS["google_search"]
        assert mapping.agent_type == "fetchAgent"
        assert mapping.http_method == "POST"
        assert "search" in mapping.endpoint_path.lower()

    def test_slack_notify_mapping(self) -> None:
        """Test slack_notify mapping exists and is correct."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            API_AGENT_MAPPINGS,
        )

        assert "slack_notify" in API_AGENT_MAPPINGS
        mapping = API_AGENT_MAPPINGS["slack_notify"]
        assert mapping.agent_type == "fetchAgent"
        assert mapping.http_method == "POST"

    def test_text_to_speech_mapping(self) -> None:
        """Test text_to_speech mapping exists and is correct."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            API_AGENT_MAPPINGS,
        )

        assert "text_to_speech" in API_AGENT_MAPPINGS
        mapping = API_AGENT_MAPPINGS["text_to_speech"]
        assert mapping.agent_type == "fetchAgent"

    def test_drive_upload_mapping(self) -> None:
        """Test drive_upload mapping exists and is correct."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            API_AGENT_MAPPINGS,
        )

        assert "drive_upload" in API_AGENT_MAPPINGS
        mapping = API_AGENT_MAPPINGS["drive_upload"]
        assert mapping.agent_type == "fetchAgent"


class TestAgentSelectorClass:
    """Tests for AgentSelector class."""

    def test_agent_selector_creation(self) -> None:
        """Test AgentSelector can be instantiated."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )

        selector = AgentSelector()
        assert selector is not None

    def test_select_agent_gmail_send(self) -> None:
        """Test select_agent returns correct mapping for gmail_send."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )

        selector = AgentSelector()
        result = selector.select_agent("gmail_send")

        assert result is not None
        assert result.api_name == "gmail_send"
        assert result.agent_type == "fetchAgent"
        assert result.http_method == "POST"

    def test_select_agent_google_search(self) -> None:
        """Test select_agent returns correct mapping for google_search."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )

        selector = AgentSelector()
        result = selector.select_agent("google_search")

        assert result is not None
        assert result.api_name == "google_search"
        assert result.agent_type == "fetchAgent"

    def test_select_agent_unknown_api(self) -> None:
        """Test select_agent returns None for unknown API."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )

        selector = AgentSelector()
        result = selector.select_agent("unknown_api_name")

        assert result is None

    def test_select_agent_case_insensitive(self) -> None:
        """Test select_agent is case insensitive."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )

        selector = AgentSelector()

        # Test uppercase
        result1 = selector.select_agent("GMAIL_SEND")
        assert result1 is not None
        assert result1.api_name == "gmail_send"

        # Test mixed case
        result2 = selector.select_agent("Gmail_Send")
        assert result2 is not None
        assert result2.api_name == "gmail_send"

    def test_select_agent_slack_notify(self) -> None:
        """Test select_agent returns correct mapping for slack_notify."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )

        selector = AgentSelector()
        result = selector.select_agent("slack_notify")

        assert result is not None
        assert result.api_name == "slack_notify"
        assert result.agent_type == "fetchAgent"

    def test_get_available_apis(self) -> None:
        """Test get_available_apis returns list of all API names."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )

        selector = AgentSelector()
        apis = selector.get_available_apis()

        assert isinstance(apis, list)
        assert "gmail_send" in apis
        assert "google_search" in apis
        assert "slack_notify" in apis

    def test_get_agent_type_for_api(self) -> None:
        """Test get_agent_type returns agent type for known API."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )

        selector = AgentSelector()

        agent_type = selector.get_agent_type("gmail_send")
        assert agent_type == "fetchAgent"

    def test_get_agent_type_unknown(self) -> None:
        """Test get_agent_type returns default for unknown API."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )

        selector = AgentSelector()

        agent_type = selector.get_agent_type("unknown_api")
        assert agent_type == "fetchAgent"  # Default agent

    def test_build_endpoint_url(self) -> None:
        """Test build_endpoint_url constructs full URL."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )

        selector = AgentSelector()
        url = selector.build_endpoint_url("gmail_send")

        assert "${EXPERTAGENT_BASE_URL}" in url
        assert "gmail" in url.lower()

    def test_build_endpoint_url_unknown(self) -> None:
        """Test build_endpoint_url returns None for unknown API."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )

        selector = AgentSelector()
        url = selector.build_endpoint_url("unknown_api")

        assert url is None


class TestAgentSelectorIntegration:
    """Integration tests for AgentSelector with real use cases."""

    def test_select_agents_for_workflow(self) -> None:
        """Test selecting multiple agents for a workflow."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            AgentSelector,
        )

        selector = AgentSelector()
        apis = ["google_search", "gmail_send"]

        results = [selector.select_agent(api) for api in apis]

        assert all(r is not None for r in results)
        assert results[0].api_name == "google_search"
        assert results[1].api_name == "gmail_send"

    def test_all_mappings_have_required_fields(self) -> None:
        """Test all mappings have required fields."""
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.agent_selector import (
            API_AGENT_MAPPINGS,
        )

        for api_name, mapping in API_AGENT_MAPPINGS.items():
            assert mapping.api_name == api_name
            assert mapping.agent_type, f"Missing agent_type for {api_name}"
            assert mapping.endpoint_path, f"Missing endpoint_path for {api_name}"
            assert mapping.http_method in [
                "GET",
                "POST",
                "PUT",
                "DELETE",
            ], f"Invalid http_method for {api_name}"
