"""Tests for force_json behaviour using the service-backed endpoints."""

from typing import Any, cast
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.api.v1.agent_endpoints import aiagent_graph, myaiagents
from app.schemas.standardAiAgent import (
    ExpertAiAgentRequest,
    ExpertAiAgentResponseJson,
)
from app.services.ai_agent_service import AiAgentService


class TestSampleAgentForceJson:
    """Force JSON handling for the sample agent endpoint."""

    @pytest.mark.asyncio
    @patch("app.services.ai_agent_service.ainvoke_graphagent")
    async def test_returns_dict_response(self, mock_invoke):
        """Agent returning a dict should passthrough unchanged."""

        mock_invoke.return_value = ([], {"result": {"value": "data"}})
        request = ExpertAiAgentRequest(user_input="test", force_json=True)
        service = AiAgentService()

        response = await aiagent_graph(request, service=service)

        assert isinstance(response, ExpertAiAgentResponseJson)
        assert response.result == {"value": "data"}
        assert response.type == "sample"
        assert response.attempts is None

    @pytest.mark.asyncio
    @patch("app.services.ai_agent_service.ainvoke_graphagent")
    async def test_parses_json_string(self, mock_invoke):
        """JSON strings should be parsed into dictionaries."""

        mock_invoke.return_value = ([], '{"result": {"value": "success"}}')
        request = ExpertAiAgentRequest(user_input="test", force_json=True)
        service = AiAgentService()

        response = await aiagent_graph(request, service=service)

        assert isinstance(response, ExpertAiAgentResponseJson)
        assert response.result == {"result": {"value": "success"}}
        assert response.type == "sample"

    @pytest.mark.asyncio
    @patch("app.services.ai_agent_service.ainvoke_graphagent")
    async def test_force_to_json_on_plain_text(self, mock_invoke):
        """Plain text should be wrapped via force_to_json_response."""

        mock_invoke.return_value = ([], "plain text response")
        request = ExpertAiAgentRequest(user_input="test", force_json=True)
        service = AiAgentService()

        response = await aiagent_graph(request, service=service)

        assert isinstance(response, ExpertAiAgentResponseJson)
        result_body = cast(dict[str, Any], response.result)
        assert result_body["result"] == "plain text response"
        assert result_body["is_json_guaranteed"] is True

    @pytest.mark.asyncio
    @patch("app.services.ai_agent_service.ainvoke_graphagent")
    async def test_agent_error_translates_to_http_error(self, mock_invoke):
        """Agent exceptions should surface as HTTP 500 responses."""

        mock_invoke.side_effect = Exception("agent failed")
        request = ExpertAiAgentRequest(user_input="test", force_json=True)
        service = AiAgentService()

        with pytest.raises(HTTPException) as exc_info:
            await aiagent_graph(request, service=service)

        assert exc_info.value.status_code == 500


class TestUtilityAgentForceJson:
    """Force JSON handling for utility agent endpoint."""

    @pytest.mark.asyncio
    @patch("app.services.ai_agent_service.jsonOutputagent")
    async def test_jsonoutput_passthrough(self, mock_agent):
        """jsonoutput agent already returns JSON structures."""

        mock_agent.return_value = {"result": {"structured": "data"}}
        request = ExpertAiAgentRequest(user_input="test", force_json=True)
        service = AiAgentService()

        response = await myaiagents(request, "jsonoutput", service=service)

        assert isinstance(response, ExpertAiAgentResponseJson)
        assert response.result == {"structured": "data"}
        assert response.type == "jsonOutput"

    @pytest.mark.asyncio
    @patch("app.services.ai_agent_service.exploreragent")
    async def test_explorer_force_json_plain_text(self, mock_agent):
        """Explorer agent plain text should be coerced into JSON."""

        mock_agent.return_value = "explorer output"
        request = ExpertAiAgentRequest(user_input="test", force_json=True)
        service = AiAgentService()

        response = await myaiagents(request, "explorer", service=service)

        assert isinstance(response, ExpertAiAgentResponseJson)
        result_body = cast(dict[str, Any], response.result)
        assert result_body["result"] == "explorer output"
        assert result_body["is_json_guaranteed"] is True
        assert response.type == "explorer"

    @pytest.mark.asyncio
    async def test_unknown_agent_returns_message(self):
        """Unknown agents should return a friendly message."""

        request = ExpertAiAgentRequest(user_input="test", force_json=True)
        service = AiAgentService()

        response = await myaiagents(request, "unknown", service=service)

        assert response == {"message": "No matching agent found."}

    @pytest.mark.asyncio
    @patch("app.services.ai_agent_service.exploreragent")
    async def test_agent_exception_translates_to_http_error(self, mock_agent):
        """Exceptions from utility agents should bubble as ServiceError."""

        mock_agent.side_effect = Exception("utility failed")
        request = ExpertAiAgentRequest(user_input="test", force_json=True)
        service = AiAgentService()

        with pytest.raises(HTTPException) as exc_info:
            await myaiagents(request, "explorer", service=service)

        assert exc_info.value.status_code == 500
