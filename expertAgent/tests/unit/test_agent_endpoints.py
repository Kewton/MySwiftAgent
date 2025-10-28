"""Tests for agent endpoints relying on the AiAgentService layer."""

from typing import Any, cast
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.v1.agent_endpoints import (
    aiagent_graph,
    exec_myllm,
    home_hello_world,
    myaiagents,
    remove_think_tags,
)
from app.exceptions import ServiceError
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

    @pytest.mark.asyncio
    async def test_home_hello_world(self):
        """Test that home endpoint returns correct message."""
        result = await home_hello_world()
        assert result == {"message": "Hello World"}


class TestExecMyllm:
    """Test exec_myllm endpoint."""

    @pytest.mark.asyncio
    async def test_exec_myllm_delegates_to_service(self):
        """Ensure the endpoint delegates work to the service layer."""

        request = ExpertAiAgentRequest(user_input="Hello")
        service = AsyncMock()
        expected = object()
        service.execute_myllm.return_value = expected

        result = await exec_myllm(request, service=service)

        service.execute_myllm.assert_awaited_once_with(request)
        assert result is expected

    @pytest.mark.asyncio
    async def test_exec_myllm_translates_service_error(self):
        """ServiceError should surface as HTTP 500 with details."""

        request = ExpertAiAgentRequest(user_input="Hello")
        service = AsyncMock()
        service.execute_myllm.side_effect = ServiceError(
            "Execution failed",
            context={"endpoint": "mylllm"},
        )

        with pytest.raises(HTTPException) as exc_info:
            await exec_myllm(request, service=service)

        assert exc_info.value.status_code == 500
        detail = cast(dict[str, Any], exc_info.value.detail)
        assert detail["message"] == "Execution failed"
        assert detail["context"] == {"endpoint": "mylllm"}


class TestAiagentGraph:
    """Test aiagent_graph endpoint."""

    @pytest.mark.asyncio
    async def test_aiagent_graph_delegates_to_service(self):
        """Ensure the graph endpoint delegates to the service layer."""

        request = ExpertAiAgentRequest(user_input="Test query")
        service = AsyncMock()
        expected = object()
        service.execute_sample_agent.return_value = expected

        result = await aiagent_graph(request, service=service)

        service.execute_sample_agent.assert_awaited_once_with(request)
        assert result is expected

    @pytest.mark.asyncio
    async def test_aiagent_graph_service_error(self):
        """Service errors should propagate as HTTP 500 responses."""

        request = ExpertAiAgentRequest(user_input="Test query")
        service = AsyncMock()
        service.execute_sample_agent.side_effect = ServiceError(
            "sample failure",
        )

        with pytest.raises(HTTPException) as exc_info:
            await aiagent_graph(request, service=service)

        assert exc_info.value.status_code == 500
        detail = cast(dict[str, Any], exc_info.value.detail)
        assert detail["message"] == "sample failure"


class TestMyaiagents:
    """Test myaiagents endpoint."""

    @pytest.mark.asyncio
    async def test_myaiagents_delegates_to_service(self):
        """Ensure utility agent endpoint defers to the service layer."""

        request = ExpertAiAgentRequest(user_input="Test query")
        service = AsyncMock()
        expected = object()
        service.execute_utility_agent.return_value = expected

        result = await myaiagents(request, "explorer", service=service)

        service.execute_utility_agent.assert_awaited_once_with(
            agent_name="explorer",
            request=request,
        )
        assert result is expected

    @pytest.mark.asyncio
    async def test_myaiagents_service_error(self):
        """Translate service errors into HTTP exceptions."""

        request = ExpertAiAgentRequest(user_input="Test query")
        service = AsyncMock()
        service.execute_utility_agent.side_effect = ServiceError(
            "utility failure",
        )

        with pytest.raises(HTTPException) as exc_info:
            await myaiagents(request, "explorer", service=service)

        assert exc_info.value.status_code == 500
        detail = cast(dict[str, Any], exc_info.value.detail)
        assert detail["message"] == "utility failure"
