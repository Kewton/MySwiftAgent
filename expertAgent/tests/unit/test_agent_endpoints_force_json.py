"""Tests for force_json functionality in agent_endpoints."""

from unittest.mock import patch

import pytest
from fastapi.responses import JSONResponse

from app.api.v1.agent_endpoints import aiagent_graph, myaiagents
from app.schemas.standardAiAgent import ExpertAiAgentRequest


class TestAiagentGraphForceJson:
    """Test aiagent_graph with force_json functionality."""

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.ainvoke_graphagent")
    async def test_force_json_with_dict_response(self, mock_invoke):
        """Test force_json with dict response."""
        mock_invoke.return_value = ([], {"result": "data"})
        request = ExpertAiAgentRequest(user_input="test", force_json=True)

        result = await aiagent_graph(request)

        assert result.result == {"result": "data"}
        assert result.type == "sample"

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.ainvoke_graphagent")
    async def test_force_json_with_json_string(self, mock_invoke):
        """Test force_json with JSON string response."""
        mock_invoke.return_value = ([], '{"result": "success"}')
        request = ExpertAiAgentRequest(user_input="test", force_json=True)

        result = await aiagent_graph(request)

        assert result.result == {"result": "success"}
        assert result.type == "sample"

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.ainvoke_graphagent")
    async def test_force_json_with_code_block(self, mock_invoke):
        """Test force_json with ```json``` code block."""
        mock_invoke.return_value = ([], '```json\n{"data": "value"}\n```')
        request = ExpertAiAgentRequest(user_input="test", force_json=True)

        result = await aiagent_graph(request)

        assert result.result == {"data": "value"}
        assert result.type == "sample"

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.ainvoke_graphagent")
    async def test_force_json_with_retry_success(self, mock_invoke):
        """Test force_json with retry succeeding."""
        # First call returns non-JSON, second call returns JSON
        mock_invoke.side_effect = [
            ([], "plain text"),
            ([], '{"result": "success"}'),
        ]
        request = ExpertAiAgentRequest(
            user_input="test", force_json=True, max_retries=1
        )

        result = await aiagent_graph(request)

        assert result.result == {"result": "success"}
        assert result.attempts == 2
        assert mock_invoke.call_count == 2

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.ainvoke_graphagent")
    async def test_force_json_max_retries_forced_conversion(self, mock_invoke):
        """Test force_json with max retries forcing conversion."""
        # All calls return non-JSON
        mock_invoke.return_value = ([], "plain text response")
        request = ExpertAiAgentRequest(
            user_input="test", force_json=True, max_retries=2
        )

        result = await aiagent_graph(request)

        assert isinstance(result, JSONResponse)
        # JSONResponse doesn't have direct attribute access, need to parse
        assert result.status_code == 200
        assert mock_invoke.call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.ainvoke_graphagent")
    async def test_force_json_exception_with_retry(self, mock_invoke):
        """Test force_json with exception and retry."""
        # First call raises exception, second call succeeds
        mock_invoke.side_effect = [
            Exception("Test error"),
            ([], '{"result": "recovered"}'),
        ]
        request = ExpertAiAgentRequest(
            user_input="test", force_json=True, max_retries=1
        )

        result = await aiagent_graph(request)

        assert result.result == {"result": "recovered"}
        assert result.attempts == 2

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.ainvoke_graphagent")
    async def test_force_json_exception_max_retries(self, mock_invoke):
        """Test force_json with exception after max retries."""
        # All calls raise exception
        mock_invoke.side_effect = Exception("Persistent error")
        request = ExpertAiAgentRequest(
            user_input="test", force_json=True, max_retries=2
        )

        result = await aiagent_graph(request)

        assert isinstance(result, JSONResponse)
        assert result.status_code == 500
        assert mock_invoke.call_count == 3


class TestMyaiagentsForceJson:
    """Test myaiagents with force_json functionality."""

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.filereaderagent")
    async def test_file_reader_force_json_success(self, mock_agent):
        """Test file_reader agent with force_json."""
        mock_agent.return_value = '{"content": "file data"}'
        request = ExpertAiAgentRequest(user_input="test", force_json=True)

        result = await myaiagents(request, "file_reader")

        assert result.result == {"content": "file data"}
        assert result.type == "file_reader"

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.filereaderagent")
    async def test_file_reader_force_json_with_retry(self, mock_agent):
        """Test file_reader with force_json retry."""
        # First call returns non-JSON, second returns JSON
        mock_agent.side_effect = [
            "plain text",
            '{"content": "file data"}',
        ]
        request = ExpertAiAgentRequest(
            user_input="test", force_json=True, max_retries=1
        )

        result = await myaiagents(request, "file_reader")

        assert result.result == {"content": "file data"}
        assert result.attempts == 2

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.filereaderagent")
    async def test_file_reader_force_json_max_retries(self, mock_agent):
        """Test file_reader with max retries forcing conversion."""
        # All calls return non-JSON
        mock_agent.return_value = "plain text"
        request = ExpertAiAgentRequest(
            user_input="test", force_json=True, max_retries=2
        )

        result = await myaiagents(request, "file_reader")

        assert isinstance(result, JSONResponse)
        assert result.status_code == 200

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.exploreragent")
    async def test_explorer_force_json_with_think_tags(self, mock_agent):
        """Test explorer agent with <think> tags and force_json."""
        mock_agent.return_value = (
            '<think>internal</think>```json\n{"result": "data"}\n```'
        )
        request = ExpertAiAgentRequest(user_input="test", force_json=True)

        result = await myaiagents(request, "explorer")

        # <think> tags should be removed
        assert result.result == {"result": "data"}
        assert result.type == "explorer"

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.actionagent")
    async def test_action_force_json_error_handling(self, mock_agent):
        """Test action agent with force_json error handling."""
        mock_agent.side_effect = Exception("Action failed")
        request = ExpertAiAgentRequest(
            user_input="test", force_json=True, max_retries=1
        )

        result = await myaiagents(request, "action")

        assert isinstance(result, JSONResponse)
        assert result.status_code == 500

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.playwrightagent")
    async def test_playwright_force_json(self, mock_agent):
        """Test playwright agent with force_json."""
        mock_agent.return_value = '{"action": "completed"}'
        request = ExpertAiAgentRequest(user_input="test", force_json=True)

        result = await myaiagents(request, "playwright")

        assert result.result == {"action": "completed"}
        assert result.type == "playwright"

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.wikipediaagent")
    async def test_wikipedia_force_json_with_language(self, mock_agent):
        """Test wikipedia agent with force_json and language param."""
        mock_agent.return_value = '{"article": "content"}'
        request = ExpertAiAgentRequest(
            user_input="test", force_json=True, language="en"
        )

        result = await myaiagents(request, "wikipedia")

        assert result.result == {"article": "content"}
        assert result.type == "wikipedia"
        # Verify language parameter was passed
        mock_agent.assert_called_once()
        call_args = mock_agent.call_args[0]
        assert call_args[2] == "en"  # Third argument is language

    @pytest.mark.asyncio
    async def test_unknown_agent_force_json(self):
        """Test unknown agent with force_json."""
        request = ExpertAiAgentRequest(user_input="test", force_json=True)

        result = await myaiagents(request, "unknown_agent")

        assert result == {"message": "No matching agent found."}

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.jsonOutputagent")
    async def test_jsonoutput_agent_force_json(self, mock_agent):
        """Test jsonoutput agent (always returns JSON)."""
        mock_agent.return_value = {"structured": "data"}
        request = ExpertAiAgentRequest(user_input="test", force_json=True)

        result = await myaiagents(request, "jsonoutput")

        assert result.result == {"structured": "data"}
        assert result.type == "jsonOutput"
