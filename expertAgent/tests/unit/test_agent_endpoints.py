"""Tests for agent endpoints."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.api.v1.agent_endpoints import (
    aiagent_graph,
    exec_myllm,
    home_hello_world,
    myaiagents,
    remove_think_tags,
)
from app.schemas.standardAiAgent import ExpertAiAgentRequest


class TestRemoveThinkTags:
    """Test remove_think_tags utility function."""

    def test_remove_think_tags_simple(self):
        """Test removing simple think tags."""
        text = "Hello <think>internal thought</think> World"
        result = remove_think_tags(text)
        assert result == "Hello  World"

    def test_remove_think_tags_multiline(self):
        """Test removing multiline think tags."""
        text = "Start <think>line1\nline2\nline3</think> End"
        result = remove_think_tags(text)
        assert result == "Start  End"

    def test_remove_think_tags_multiple(self):
        """Test removing multiple think tags."""
        text = "<think>first</think> Middle <think>second</think> End"
        result = remove_think_tags(text)
        assert result == " Middle  End"

    def test_remove_think_tags_no_tags(self):
        """Test with no think tags."""
        text = "No tags here"
        result = remove_think_tags(text)
        assert result == "No tags here"

    def test_remove_think_tags_empty(self):
        """Test with empty string."""
        result = remove_think_tags("")
        assert result == ""


class TestHomeHelloWorld:
    """Test home endpoint."""

    def test_home_hello_world(self):
        """Test that home endpoint returns correct message."""
        result = home_hello_world()
        assert result == {"message": "Hello World"}


class TestExecMyllm:
    """Test exec_myllm endpoint."""

    @patch("app.api.v1.agent_endpoints.chatOllama")
    def test_exec_myllm_with_system_message(self, mock_chat):
        """Test exec_myllm with system message."""
        mock_chat.return_value = "Test response"
        request = ExpertAiAgentRequest(
            user_input="Hello",
            system_imput="You are helpful",
            model_name="llama2"
        )

        result = exec_myllm(request)

        assert result.result == "Test response"
        assert result.text == "Test response"
        assert result.type == "exec_myllm"
        mock_chat.assert_called_once()

    @patch("app.api.v1.agent_endpoints.chatOllama")
    def test_exec_myllm_without_system_message(self, mock_chat):
        """Test exec_myllm without system message."""
        mock_chat.return_value = "Test response"
        request = ExpertAiAgentRequest(user_input="Hello")

        result = exec_myllm(request)

        assert result.result == "Test response"
        assert result.text == "Test response"
        mock_chat.assert_called_once()

    @patch("app.api.v1.agent_endpoints.chatOllama")
    def test_exec_myllm_removes_think_tags(self, mock_chat):
        """Test that exec_myllm removes think tags from response."""
        mock_chat.return_value = "Response <think>internal</think> text"
        request = ExpertAiAgentRequest(user_input="Hello")

        result = exec_myllm(request)

        assert result.result == "Response  text"
        assert result.text == "Response  text"


class TestAiagentGraph:
    """Test aiagent_graph endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.ainvoke_graphagent")
    async def test_aiagent_graph_success(self, mock_invoke):
        """Test successful aiagent_graph execution."""
        from app.schemas.standardAiAgent import ChatMessage

        chat_history = [
            ChatMessage(role="user", content="message1"),
            ChatMessage(role="assistant", content="message2"),
        ]
        mock_invoke.return_value = (chat_history, "AI Response")
        request = ExpertAiAgentRequest(user_input="Test query")

        result = await aiagent_graph(request)

        assert result.result == "AI Response"
        assert result.type == "sample"
        assert len(result.chathistory) == 2
        assert result.chathistory[0].content == "message1"
        assert result.chathistory[1].content == "message2"

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.ainvoke_graphagent")
    async def test_aiagent_graph_error(self, mock_invoke):
        """Test aiagent_graph error handling."""
        mock_invoke.side_effect = Exception("Test error")
        request = ExpertAiAgentRequest(user_input="Test query")

        with pytest.raises(HTTPException) as exc_info:
            await aiagent_graph(request)

        assert exc_info.value.status_code == 500
        assert "internal server error" in exc_info.value.detail.lower()


class TestMyaiagents:
    """Test myaiagents endpoint."""

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.jsonOutputagent")
    async def test_myaiagents_jsonoutput(self, mock_agent):
        """Test myaiagents with jsonoutput agent."""
        mock_agent.return_value = {"key": "value"}
        request = ExpertAiAgentRequest(user_input="Test query")

        result = await myaiagents(request, "jsonoutput")

        assert result.result == {"key": "value"}
        assert result.type == "jsonOutput"

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.exploreragent")
    async def test_myaiagents_explorer(self, mock_agent):
        """Test myaiagents with explorer agent."""
        mock_agent.return_value = "Explorer response <think>thought</think>"
        request = ExpertAiAgentRequest(user_input="Test query")

        result = await myaiagents(request, "explorer")

        assert result.result == "Explorer response "
        assert result.type == "explorer"

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.actionagent")
    async def test_myaiagents_action(self, mock_agent):
        """Test myaiagents with action agent."""
        mock_agent.return_value = "Action response"
        request = ExpertAiAgentRequest(user_input="Test query")

        result = await myaiagents(request, "action")

        assert result.result == "Action response"
        assert result.type == "action"

    @pytest.mark.asyncio
    async def test_myaiagents_unknown_agent(self):
        """Test myaiagents with unknown agent name."""
        request = ExpertAiAgentRequest(user_input="Test query")

        result = await myaiagents(request, "unknown")

        assert result == {"message": "No matching agent found."}

    @pytest.mark.asyncio
    @patch("app.api.v1.agent_endpoints.jsonOutputagent")
    async def test_myaiagents_error(self, mock_agent):
        """Test myaiagents error handling."""
        mock_agent.side_effect = Exception("Test error")
        request = ExpertAiAgentRequest(user_input="Test query")

        with pytest.raises(HTTPException) as exc_info:
            await myaiagents(request, "jsonoutput")

        assert exc_info.value.status_code == 500
        assert "internal server error" in exc_info.value.detail.lower()
