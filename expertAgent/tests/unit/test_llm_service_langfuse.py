"""Unit tests for Langfuse integration in llm_service.

Tests verify that:
- Langfuse CallbackHandler is properly created and passed to LLM
- flush() is called after LLM invocation
- System works correctly when Langfuse is disabled
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.chat import RequirementState


@pytest.fixture
def mock_requirement_state():
    """Create a mock RequirementState for testing."""
    return RequirementState(
        data_source="テスト用データソース",
        process_description="テスト処理",
        output_format="Excel",
        schedule=None,
        completeness=0.5,
    )


@pytest.fixture
def mock_llm_response():
    """Create a mock LLM response."""
    mock = MagicMock()
    mock.content = "テストレスポンスです。詳しく教えてください。"
    return mock


class TestStreamRequirementClarificationLangfuse:
    """Tests for Langfuse integration in stream_requirement_clarification."""

    @pytest.mark.asyncio
    async def test_langfuse_handler_created_with_conversation_id(
        self, mock_requirement_state
    ):
        """Test that Langfuse handler is created with conversation_id."""
        with (
            patch(
                "app.services.conversation.llm_service.langfuse_service"
            ) as mock_langfuse,
            patch(
                "app.services.conversation.llm_service.create_llm_with_fallback"
            ) as mock_llm_factory,
            patch(
                "app.services.conversation.llm_service.extract_requirement_with_llm"
            ) as mock_extract,
        ):
            # Setup mocks
            mock_handler = MagicMock()
            mock_langfuse.get_callback_handler.return_value = mock_handler
            mock_langfuse.flush = MagicMock()

            mock_model = MagicMock()
            mock_perf_tracker = MagicMock()
            mock_cost_tracker = MagicMock()
            mock_llm_factory.return_value = (
                mock_model,
                mock_perf_tracker,
                mock_cost_tracker,
            )

            # Mock async stream
            async def mock_astream(*args, **kwargs):
                mock_chunk = MagicMock()
                mock_chunk.content = "テスト"
                yield mock_chunk

            mock_model.astream = mock_astream

            # Mock extract_requirement_with_llm
            mock_extract.return_value = mock_requirement_state

            # Import and call the function
            from app.services.conversation.llm_service import (
                stream_requirement_clarification,
            )

            # Consume the generator
            results = []
            async for event in stream_requirement_clarification(
                user_message="テストメッセージ",
                previous_messages=[],
                current_requirements=mock_requirement_state,
                conversation_id="test_conv_123",
                user_id="test_user_456",
            ):
                results.append(event)

            # Verify Langfuse handler was created with correct parameters
            mock_langfuse.get_callback_handler.assert_called_once()
            call_kwargs = mock_langfuse.get_callback_handler.call_args.kwargs
            assert call_kwargs["session_id"] == "test_conv_123"
            assert call_kwargs["user_id"] == "test_user_456"
            assert call_kwargs["trace_name"] == "requirement_clarification"
            assert "streaming" in call_kwargs["tags"]

            # Verify flush was called
            mock_langfuse.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_langfuse_disabled_still_works(self, mock_requirement_state):
        """Test that streaming works when Langfuse is disabled."""
        with (
            patch(
                "app.services.conversation.llm_service.langfuse_service"
            ) as mock_langfuse,
            patch(
                "app.services.conversation.llm_service.create_llm_with_fallback"
            ) as mock_llm_factory,
            patch(
                "app.services.conversation.llm_service.extract_requirement_with_llm"
            ) as mock_extract,
        ):
            # Setup mocks - Langfuse returns None (disabled)
            mock_langfuse.get_callback_handler.return_value = None

            mock_model = MagicMock()
            mock_perf_tracker = MagicMock()
            mock_cost_tracker = MagicMock()
            mock_llm_factory.return_value = (
                mock_model,
                mock_perf_tracker,
                mock_cost_tracker,
            )

            # Mock async stream
            async def mock_astream(*args, **kwargs):
                mock_chunk = MagicMock()
                mock_chunk.content = "テスト応答"
                yield mock_chunk

            mock_model.astream = mock_astream

            # Mock extract_requirement_with_llm
            mock_extract.return_value = mock_requirement_state

            # Import and call the function
            from app.services.conversation.llm_service import (
                stream_requirement_clarification,
            )

            # Consume the generator - should not raise
            results = []
            async for event in stream_requirement_clarification(
                user_message="テストメッセージ",
                previous_messages=[],
                current_requirements=mock_requirement_state,
                conversation_id="test_conv",
            ):
                results.append(event)

            # Verify we got results
            assert len(results) >= 1
            assert results[0]["type"] == "message"

            # Verify flush was NOT called (since handler is None)
            mock_langfuse.flush.assert_not_called()


class TestNonStreamingClarificationLangfuse:
    """Tests for Langfuse integration in non_streaming_clarification."""

    @pytest.mark.asyncio
    async def test_langfuse_handler_created_for_non_streaming(
        self, mock_requirement_state, mock_llm_response
    ):
        """Test that Langfuse handler is created for non-streaming mode."""
        with (
            patch(
                "app.services.conversation.llm_service.langfuse_service"
            ) as mock_langfuse,
            patch(
                "app.services.conversation.llm_service.create_llm_with_fallback"
            ) as mock_llm_factory,
            patch(
                "app.services.conversation.llm_service.extract_requirement_with_llm"
            ) as mock_extract,
        ):
            # Setup mocks
            mock_handler = MagicMock()
            mock_langfuse.get_callback_handler.return_value = mock_handler
            mock_langfuse.flush = MagicMock()

            mock_model = MagicMock()
            mock_perf_tracker = MagicMock()
            mock_cost_tracker = MagicMock()
            mock_llm_factory.return_value = (
                mock_model,
                mock_perf_tracker,
                mock_cost_tracker,
            )

            # Mock async invoke
            mock_model.ainvoke = AsyncMock(return_value=mock_llm_response)

            # Mock extract_requirement_with_llm
            mock_extract.return_value = mock_requirement_state

            # Import and call the function
            from app.services.conversation.llm_service import (
                non_streaming_clarification,
            )

            response, updated_requirements = await non_streaming_clarification(
                user_message="テストメッセージ",
                previous_messages=[],
                current_requirements=mock_requirement_state,
                conversation_id="test_conv_789",
                user_id="test_user_abc",
            )

            # Verify Langfuse handler was created with correct parameters
            mock_langfuse.get_callback_handler.assert_called_once()
            call_kwargs = mock_langfuse.get_callback_handler.call_args.kwargs
            assert call_kwargs["session_id"] == "test_conv_789"
            assert call_kwargs["user_id"] == "test_user_abc"
            assert call_kwargs["trace_name"] == "requirement_clarification"
            assert "non_streaming" in call_kwargs["tags"]

            # Verify ainvoke was called with config containing callbacks
            mock_model.ainvoke.assert_called_once()
            call_args = mock_model.ainvoke.call_args
            assert "config" in call_args.kwargs or len(call_args.args) > 1

            # Verify flush was called
            mock_langfuse.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_non_streaming_langfuse_disabled(
        self, mock_requirement_state, mock_llm_response
    ):
        """Test that non-streaming works when Langfuse is disabled."""
        with (
            patch(
                "app.services.conversation.llm_service.langfuse_service"
            ) as mock_langfuse,
            patch(
                "app.services.conversation.llm_service.create_llm_with_fallback"
            ) as mock_llm_factory,
            patch(
                "app.services.conversation.llm_service.extract_requirement_with_llm"
            ) as mock_extract,
        ):
            # Setup mocks - Langfuse returns None (disabled)
            mock_langfuse.get_callback_handler.return_value = None

            mock_model = MagicMock()
            mock_perf_tracker = MagicMock()
            mock_cost_tracker = MagicMock()
            mock_llm_factory.return_value = (
                mock_model,
                mock_perf_tracker,
                mock_cost_tracker,
            )

            # Mock async invoke
            mock_model.ainvoke = AsyncMock(return_value=mock_llm_response)

            # Mock extract_requirement_with_llm
            mock_extract.return_value = mock_requirement_state

            # Import and call the function
            from app.services.conversation.llm_service import (
                non_streaming_clarification,
            )

            response, updated_requirements = await non_streaming_clarification(
                user_message="テストメッセージ",
                previous_messages=[],
                current_requirements=mock_requirement_state,
            )

            # Verify we got a response
            assert response == "テストレスポンスです。詳しく教えてください。"

            # Verify flush was NOT called (since handler is None)
            mock_langfuse.flush.assert_not_called()

    @pytest.mark.asyncio
    async def test_langfuse_flush_called_on_exception(self, mock_requirement_state):
        """Test that Langfuse flush is called even when exception occurs."""
        with (
            patch(
                "app.services.conversation.llm_service.langfuse_service"
            ) as mock_langfuse,
            patch(
                "app.services.conversation.llm_service.create_llm_with_fallback"
            ) as mock_llm_factory,
        ):
            # Setup mocks
            mock_handler = MagicMock()
            mock_langfuse.get_callback_handler.return_value = mock_handler
            mock_langfuse.flush = MagicMock()

            mock_model = MagicMock()
            mock_perf_tracker = MagicMock()
            mock_cost_tracker = MagicMock()
            mock_llm_factory.return_value = (
                mock_model,
                mock_perf_tracker,
                mock_cost_tracker,
            )

            # Mock async invoke to raise exception
            mock_model.ainvoke = AsyncMock(side_effect=Exception("LLM Error"))

            # Import and call the function
            from app.services.conversation.llm_service import (
                non_streaming_clarification,
            )

            with pytest.raises(Exception, match="LLM Error"):
                await non_streaming_clarification(
                    user_message="テストメッセージ",
                    previous_messages=[],
                    current_requirements=mock_requirement_state,
                    conversation_id="test_conv",
                )

            # Verify flush was still called (in finally block)
            mock_langfuse.flush.assert_called_once()
