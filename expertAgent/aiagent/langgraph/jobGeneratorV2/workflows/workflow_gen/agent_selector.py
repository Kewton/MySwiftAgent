"""AgentSelector for Workflow Generator V2.

This module provides the AgentSelector class that maps API names to GraphAI agents.

Issue #342 V2 Workflow Quality Improvement

Key responsibilities:
- Map API names (gmail_send, google_search, etc.) to GraphAI agents (fetchAgent)
- Provide endpoint URLs with EXPERTAGENT_BASE_URL environment variable
- Support case-insensitive API name matching
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AgentMapping:
    """Mapping configuration for an API to GraphAI agent.

    Attributes:
        api_name: API name (e.g., 'gmail_send', 'google_search')
        agent_type: GraphAI agent type (e.g., 'fetchAgent')
        endpoint_path: API endpoint path (e.g., '/v1/utility/gmail/send')
        http_method: HTTP method (GET, POST, PUT, DELETE)
        description: Human-readable description of the API
        default_params: Default parameters for the agent
    """

    api_name: str
    agent_type: str
    endpoint_path: str
    http_method: str
    description: str = ""
    default_params: dict = field(default_factory=dict)


# API to Agent mapping table
# All endpoints use EXPERTAGENT_BASE_URL as the base URL prefix
API_AGENT_MAPPINGS: dict[str, AgentMapping] = {
    "gmail_send": AgentMapping(
        api_name="gmail_send",
        agent_type="fetchAgent",
        endpoint_path="/aiagent-api/v1/utility/gmail/send",
        http_method="POST",
        description="Send email via Gmail API",
    ),
    "google_search": AgentMapping(
        api_name="google_search",
        agent_type="fetchAgent",
        endpoint_path="/aiagent-api/v1/utility/google_search",
        http_method="POST",
        description="Execute Google search",
        default_params={"timeout": 180},
    ),
    "google_search_overview": AgentMapping(
        api_name="google_search_overview",
        agent_type="fetchAgent",
        endpoint_path="/aiagent-api/v1/utility/google_search_overview",
        http_method="POST",
        description="Execute Google search with overview",
        default_params={"timeout": 180},
    ),
    "slack_notify": AgentMapping(
        api_name="slack_notify",
        agent_type="fetchAgent",
        endpoint_path="/aiagent-api/v1/utility/slack/notify",
        http_method="POST",
        description="Send Slack notification",
    ),
    "text_to_speech": AgentMapping(
        api_name="text_to_speech",
        agent_type="fetchAgent",
        endpoint_path="/aiagent-api/v1/utility/text_to_speech",
        http_method="POST",
        description="Convert text to speech audio",
    ),
    "text_to_speech_drive": AgentMapping(
        api_name="text_to_speech_drive",
        agent_type="fetchAgent",
        endpoint_path="/aiagent-api/v1/utility/text_to_speech_drive",
        http_method="POST",
        description="Convert text to speech and save to Google Drive",
    ),
    "drive_upload": AgentMapping(
        api_name="drive_upload",
        agent_type="fetchAgent",
        endpoint_path="/aiagent-api/v1/utility/drive/upload",
        http_method="POST",
        description="Upload file to Google Drive",
    ),
    "gmail_search": AgentMapping(
        api_name="gmail_search",
        agent_type="fetchAgent",
        endpoint_path="/aiagent-api/v1/utility/gmail/search",
        http_method="POST",
        description="Search emails in Gmail",
    ),
    "explorer_gemini": AgentMapping(
        api_name="explorer_gemini",
        agent_type="fetchAgent",
        endpoint_path="/aiagent-api/v1/utility/explorer/gemini",
        http_method="POST",
        description="Execute Gemini LLM exploration",
    ),
    "explorer_gemini_jsonoutput": AgentMapping(
        api_name="explorer_gemini_jsonoutput",
        agent_type="fetchAgent",
        endpoint_path="/aiagent-api/v1/utility/explorer/gemini/jsonoutput",
        http_method="POST",
        description="Execute Gemini LLM with JSON output",
    ),
}


class AgentSelector:
    """Selector for GraphAI agents based on API name.

    This class provides methods to select appropriate GraphAI agents
    and build endpoint URLs for API calls.

    Example:
        selector = AgentSelector()
        mapping = selector.select_agent("gmail_send")
        if mapping:
            print(f"Agent: {mapping.agent_type}")
            print(f"URL: {selector.build_endpoint_url('gmail_send')}")
    """

    def __init__(self) -> None:
        """Initialize AgentSelector with API mappings."""
        self._mappings = API_AGENT_MAPPINGS.copy()
        # Build lowercase lookup table for case-insensitive matching
        self._lowercase_lookup: dict[str, str] = {
            k.lower(): k for k in self._mappings
        }

    def select_agent(self, api_name: str) -> AgentMapping | None:
        """Select agent mapping for an API name.

        Args:
            api_name: API name (case-insensitive)

        Returns:
            AgentMapping if found, None otherwise
        """
        # Case-insensitive lookup
        normalized_name = api_name.lower()
        original_name = self._lowercase_lookup.get(normalized_name)

        if original_name:
            return self._mappings.get(original_name)
        return None

    def get_available_apis(self) -> list[str]:
        """Get list of all available API names.

        Returns:
            List of API names
        """
        return list(self._mappings.keys())

    def get_agent_type(self, api_name: str) -> str:
        """Get agent type for an API.

        Args:
            api_name: API name

        Returns:
            Agent type string, defaults to 'fetchAgent' for unknown APIs
        """
        mapping = self.select_agent(api_name)
        if mapping:
            return mapping.agent_type
        return "fetchAgent"  # Default agent

    def build_endpoint_url(self, api_name: str) -> str | None:
        """Build full endpoint URL for an API.

        Args:
            api_name: API name

        Returns:
            Full URL with ${EXPERTAGENT_BASE_URL} prefix, or None if not found
        """
        mapping = self.select_agent(api_name)
        if mapping:
            return f"${{EXPERTAGENT_BASE_URL}}{mapping.endpoint_path}"
        return None
