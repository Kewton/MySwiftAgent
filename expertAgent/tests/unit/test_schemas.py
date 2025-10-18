"""Tests for app schemas."""

from app.schemas.standardAiAgent import (
    ChatMessage,
    ExpertAiAgentRequest,
    ExpertAiAgentResponse,
    ExpertAiAgentResponseJson,
)
from app.schemas.utilitySchemas import (
    SearchUtilityRequest,
    SearchUtilityResponse,
    UtilityRequest,
    UtilityResponse,
)


class TestStandardAiAgentSchemas:
    """Test StandardAiAgent schemas."""

    def test_chat_message_creation(self):
        """Test ChatMessage model creation."""
        msg = ChatMessage(role="user", content="test")
        assert msg.role == "user"
        assert msg.content == "test"

    def test_expert_ai_agent_request_minimal(self):
        """Test ExpertAiAgentRequest with minimal fields."""
        req = ExpertAiAgentRequest(user_input="test query")
        assert req.user_input == "test query"
        assert req.system_imput is None
        assert req.model_name is None

    def test_expert_ai_agent_request_full(self):
        """Test ExpertAiAgentRequest with all fields."""
        req = ExpertAiAgentRequest(
            user_input="test query",
            system_imput="system message",
            model_name="gpt-4",
        )
        assert req.user_input == "test query"
        assert req.system_imput == "system message"
        assert req.model_name == "gpt-4"

    def test_expert_ai_agent_response(self):
        """Test ExpertAiAgentResponse model."""
        resp = ExpertAiAgentResponse(result="test response", type="test")
        assert resp.result == "test response"
        assert resp.type == "test"

    def test_expert_ai_agent_response_json(self):
        """Test ExpertAiAgentResponseJson model with dict."""
        resp = ExpertAiAgentResponseJson(result={"key": "value"}, type="json")
        assert resp.result == {"key": "value"}
        assert resp.type == "json"

    def test_expert_ai_agent_response_json_with_list(self):
        """Test ExpertAiAgentResponseJson model with list (JSON array)."""
        resp = ExpertAiAgentResponseJson(
            result=["url1", "url2", "url3"], type="jsonOutput"
        )
        assert resp.result == ["url1", "url2", "url3"]
        assert resp.type == "jsonOutput"

    def test_expert_ai_agent_response_json_with_empty_list(self):
        """Test ExpertAiAgentResponseJson model with empty list."""
        resp = ExpertAiAgentResponseJson(result=[], type="jsonOutput")
        assert resp.result == []
        assert resp.type == "jsonOutput"


class TestUtilitySchemas:
    """Test Utility schemas."""

    def test_utility_request(self):
        """Test UtilityRequest model."""
        req = UtilityRequest(user_input="test input")
        assert req.user_input == "test input"

    def test_utility_response(self):
        """Test UtilityResponse model."""
        resp = UtilityResponse(result="test result")
        assert resp.result == "test result"

    def test_search_utility_request_minimal(self):
        """Test SearchUtilityRequest with minimal fields."""
        req = SearchUtilityRequest(queries=["query1", "query2"])
        assert req.queries == ["query1", "query2"]
        assert req.num is None

    def test_search_utility_request_full(self):
        """Test SearchUtilityRequest with all fields."""
        req = SearchUtilityRequest(queries=["query1"], num=10)
        assert req.queries == ["query1"]
        assert req.num == 10

    def test_search_utility_response(self):
        """Test SearchUtilityResponse model."""
        resp = SearchUtilityResponse(result={"data": "search result"})
        assert resp.result == {"data": "search result"}
