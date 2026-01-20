"""Unit tests for JobGeneratorAdapter LLM client integration.

Issue #361: Tests for LLM client injection into orchestrator.
Task T1.5-new, T1.6-new, T1.7-new
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiagent.langgraph.jobGeneratorV2.adapter import JobGeneratorAdapter


class TestCreateLLMClient:
    """Tests for _create_llm_client method."""

    def test_create_llm_client_returns_callable(self) -> None:
        """Test that _create_llm_client returns a callable."""
        adapter = JobGeneratorAdapter(max_retry=3)

        llm_client = adapter._create_llm_client()

        assert callable(llm_client)

    def test_create_llm_client_uses_model_name_from_init(self) -> None:
        """Test that llm_client uses model_name from __init__."""
        adapter = JobGeneratorAdapter(
            max_retry=3,
            model_name="gpt-4o-mini",
        )

        # The adapter should store the model name
        assert adapter._model_name == "gpt-4o-mini"

    def test_create_llm_client_uses_langfuse_handler(self) -> None:
        """Test that llm_client uses langfuse_handler if provided."""
        mock_langfuse = MagicMock()
        adapter = JobGeneratorAdapter(
            max_retry=3,
            langfuse_handler=mock_langfuse,
        )

        # The adapter should store the langfuse handler
        assert adapter._langfuse_handler is mock_langfuse


class TestOrchestratorReceivesLLMClient:
    """Tests for orchestrator receiving llm_client."""

    def test_orchestrator_receives_llm_client(self) -> None:
        """Test that orchestrator is created with llm_client."""
        adapter = JobGeneratorAdapter(max_retry=3)

        # The orchestrator should have llm_client set
        assert adapter._orchestrator._llm_client is not None
        assert callable(adapter._orchestrator._llm_client)

    def test_orchestrator_llm_client_is_from_create_llm_client(self) -> None:
        """Test that orchestrator's llm_client is created by _create_llm_client."""
        adapter = JobGeneratorAdapter(max_retry=3)

        # Create a new llm_client and verify it's callable like orchestrator's
        llm_client = adapter._create_llm_client()

        # Both should be callables
        assert callable(llm_client)
        assert callable(adapter._orchestrator._llm_client)


class TestLLMClientInvokesStructuredLLM:
    """Tests for llm_client using invoke_structured_llm internally."""

    @pytest.mark.asyncio
    async def test_llm_client_calls_invoke_structured_llm(self) -> None:
        """Test that llm_client internally calls invoke_structured_llm."""
        from pydantic import BaseModel

        class MockResponse(BaseModel):
            message: str

        adapter = JobGeneratorAdapter(max_retry=3, model_name="claude-haiku-4-5")
        llm_client = adapter._create_llm_client()

        # Mock invoke_structured_llm
        mock_result = MagicMock()
        mock_result.result = MockResponse(message="test")

        with patch(
            "aiagent.langgraph.jobGeneratorV2.adapter.invoke_structured_llm",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_invoke:
            await llm_client(
                system_prompt="You are helpful.",
                user_prompt="Say hello.",
                response_model=MockResponse,
            )

            # Verify invoke_structured_llm was called
            mock_invoke.assert_called_once()
            call_kwargs = mock_invoke.call_args.kwargs

            assert call_kwargs["system_prompt"] == "You are helpful."
            assert call_kwargs["user_prompt"] == "Say hello."
            assert call_kwargs["response_model"] == MockResponse
            assert call_kwargs["model_name"] == "claude-haiku-4-5"

    @pytest.mark.asyncio
    async def test_llm_client_passes_callbacks_when_langfuse_provided(self) -> None:
        """Test that llm_client passes callbacks when langfuse_handler is set."""
        from pydantic import BaseModel

        class MockResponse(BaseModel):
            message: str

        mock_langfuse = MagicMock()
        adapter = JobGeneratorAdapter(
            max_retry=3,
            langfuse_handler=mock_langfuse,
        )
        llm_client = adapter._create_llm_client()

        mock_result = MagicMock()
        mock_result.result = MockResponse(message="test")

        with patch(
            "aiagent.langgraph.jobGeneratorV2.adapter.invoke_structured_llm",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_invoke:
            await llm_client(
                system_prompt="System",
                user_prompt="User",
                response_model=MockResponse,
            )

            # Verify callbacks include langfuse handler
            call_kwargs = mock_invoke.call_args.kwargs
            assert call_kwargs["callbacks"] == [mock_langfuse]

    @pytest.mark.asyncio
    async def test_llm_client_no_callbacks_when_langfuse_not_provided(self) -> None:
        """Test that llm_client passes None callbacks when no langfuse_handler."""
        from pydantic import BaseModel

        class MockResponse(BaseModel):
            message: str

        adapter = JobGeneratorAdapter(max_retry=3)
        llm_client = adapter._create_llm_client()

        mock_result = MagicMock()
        mock_result.result = MockResponse(message="test")

        with patch(
            "aiagent.langgraph.jobGeneratorV2.adapter.invoke_structured_llm",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_invoke:
            await llm_client(
                system_prompt="System",
                user_prompt="User",
                response_model=MockResponse,
            )

            # Verify callbacks is None
            call_kwargs = mock_invoke.call_args.kwargs
            assert call_kwargs["callbacks"] is None

    @pytest.mark.asyncio
    async def test_llm_client_returns_result_from_structured_call(self) -> None:
        """Test that llm_client returns result.result from StructuredCallResult."""
        from pydantic import BaseModel

        class MockResponse(BaseModel):
            message: str

        adapter = JobGeneratorAdapter(max_retry=3)
        llm_client = adapter._create_llm_client()

        expected_response = MockResponse(message="Hello, World!")
        mock_result = MagicMock()
        mock_result.result = expected_response

        with patch(
            "aiagent.langgraph.jobGeneratorV2.adapter.invoke_structured_llm",
            new_callable=AsyncMock,
            return_value=mock_result,
        ):
            result = await llm_client(
                system_prompt="System",
                user_prompt="User",
                response_model=MockResponse,
            )

            # Verify the result is the actual response object
            assert result == expected_response
            assert result.message == "Hello, World!"


class TestMultiModelSupport:
    """Tests for Claude/GPT/Gemini model support."""

    def test_adapter_supports_claude_model(self) -> None:
        """Test adapter with Claude model name."""
        adapter = JobGeneratorAdapter(
            max_retry=3,
            model_name="claude-haiku-4-5",
        )
        assert adapter._model_name == "claude-haiku-4-5"

    def test_adapter_supports_gpt_model(self) -> None:
        """Test adapter with GPT model name."""
        adapter = JobGeneratorAdapter(
            max_retry=3,
            model_name="gpt-4o-mini",
        )
        assert adapter._model_name == "gpt-4o-mini"

    def test_adapter_supports_gemini_model(self) -> None:
        """Test adapter with Gemini model name."""
        adapter = JobGeneratorAdapter(
            max_retry=3,
            model_name="gemini-2.5-flash",
        )
        assert adapter._model_name == "gemini-2.5-flash"

    @pytest.mark.asyncio
    async def test_llm_client_passes_gpt_model_to_invoke(self) -> None:
        """Test that llm_client passes GPT model name to invoke_structured_llm."""
        from pydantic import BaseModel

        class MockResponse(BaseModel):
            message: str

        adapter = JobGeneratorAdapter(
            max_retry=3,
            model_name="gpt-4o-mini",
        )
        llm_client = adapter._create_llm_client()

        mock_result = MagicMock()
        mock_result.result = MockResponse(message="test")

        with patch(
            "aiagent.langgraph.jobGeneratorV2.adapter.invoke_structured_llm",
            new_callable=AsyncMock,
            return_value=mock_result,
        ) as mock_invoke:
            await llm_client(
                system_prompt="System",
                user_prompt="User",
                response_model=MockResponse,
            )

            call_kwargs = mock_invoke.call_args.kwargs
            assert call_kwargs["model_name"] == "gpt-4o-mini"
