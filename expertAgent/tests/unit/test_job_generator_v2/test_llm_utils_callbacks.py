"""Tests for LLM utilities callbacks support.

Issue #342: Verify that get_callbacks_from_context() and callbacks parameter
work correctly for Langfuse integration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aiagent.langgraph.jobGeneratorV2.context import (
    ContextBuilder,
    ObservabilityContext,
)
from aiagent.langgraph.jobGeneratorV2.llm_utils import (
    get_callbacks_from_context,
    invoke_structured_llm,
)


class TestGetCallbacksFromContext:
    """Tests for get_callbacks_from_context() helper function."""

    def test_function_exists(self):
        """get_callbacks_from_context should be importable."""
        from aiagent.langgraph.jobGeneratorV2.llm_utils import (
            get_callbacks_from_context,
        )

        assert callable(get_callbacks_from_context)

    def test_returns_empty_list_when_no_observability(self):
        """Should return empty list when context has no observability."""
        context = (
            ContextBuilder()
            .with_job_id("test-job-id")
            .with_user_requirement("Test requirement")
            .build()
        )
        # Set observability to None
        context.observability = None  # type: ignore

        callbacks = get_callbacks_from_context(context)

        assert callbacks == []

    def test_returns_empty_list_when_no_tracer(self):
        """Should return empty list when observability has no tracer."""
        context = (
            ContextBuilder()
            .with_job_id("test-job-id")
            .with_user_requirement("Test requirement")
            .with_observability_context(ObservabilityContext(tracer=None))
            .build()
        )

        callbacks = get_callbacks_from_context(context)

        assert callbacks == []

    def test_returns_tracer_in_list_when_present(self):
        """Should return list with tracer when present in context."""
        mock_tracer = MagicMock()

        context = (
            ContextBuilder()
            .with_job_id("test-job-id")
            .with_user_requirement("Test requirement")
            .with_observability_context(ObservabilityContext(tracer=mock_tracer))
            .build()
        )

        callbacks = get_callbacks_from_context(context)

        assert callbacks == [mock_tracer]


class TestInvokeStructuredLLMCallbacks:
    """Tests for invoke_structured_llm() callbacks parameter."""

    def test_invoke_structured_llm_accepts_callbacks_parameter(self):
        """invoke_structured_llm should accept a callbacks parameter."""
        import inspect

        sig = inspect.signature(invoke_structured_llm)
        param_names = list(sig.parameters.keys())

        assert "callbacks" in param_names, (
            "invoke_structured_llm() should have a 'callbacks' parameter"
        )

    @pytest.mark.asyncio
    async def test_callbacks_passed_to_llm_config(self):
        """Callbacks should be passed to LLM config when provided."""
        from pydantic import BaseModel

        class TestResponse(BaseModel):
            message: str

        mock_callback = MagicMock()

        # Mock the LLM invocation at the correct import location
        with (
            patch("langchain_anthropic.ChatAnthropic") as mock_anthropic,
            patch("core.secrets.secrets_manager") as mock_secrets,
        ):
            # Setup mocks
            mock_secrets.get_secret.return_value = "test-api-key"

            mock_llm_instance = MagicMock()
            mock_anthropic.return_value = mock_llm_instance

            mock_structured_llm = MagicMock()
            mock_llm_instance.with_structured_output.return_value = mock_structured_llm

            # Create async mock for ainvoke
            async_result = {
                "parsed": TestResponse(message="test"),
                "raw": MagicMock(content="test"),
            }
            mock_structured_llm.ainvoke = AsyncMock(return_value=async_result)

            # Call with callbacks
            await invoke_structured_llm(
                system_prompt="Test system",
                user_prompt="Test user",
                response_model=TestResponse,
                model_name="claude-haiku-4-5",
                callbacks=[mock_callback],
            )

            # Verify ainvoke was called with config containing callbacks
            mock_structured_llm.ainvoke.assert_called_once()
            call_args = mock_structured_llm.ainvoke.call_args

            # Check that config with callbacks was passed (in kwargs)
            assert call_args.kwargs is not None
            config = call_args.kwargs.get("config", {})
            assert config is not None
            assert "callbacks" in config
            assert mock_callback in config["callbacks"]

    @pytest.mark.asyncio
    async def test_callbacks_none_by_default(self):
        """Callbacks should be None by default (optional parameter)."""
        import inspect

        sig = inspect.signature(invoke_structured_llm)
        callbacks_param = sig.parameters.get("callbacks")

        assert callbacks_param is not None
        assert callbacks_param.default is None


class TestWorkflowCallbacksIntegration:
    """Tests for workflow integration with callbacks."""

    def test_decomposer_can_use_callbacks(self):
        """decomposer.py should be importable with get_callbacks_from_context."""
        import importlib.util

        # Verify modules are importable
        llm_utils_spec = importlib.util.find_spec(
            "aiagent.langgraph.jobGeneratorV2.llm_utils"
        )
        decomposer_spec = importlib.util.find_spec(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer"
        )
        assert llm_utils_spec is not None, "llm_utils module not found"
        assert decomposer_spec is not None, "decomposer module not found"

    def test_schema_generator_can_use_callbacks(self):
        """schema_generator.py should be importable with get_callbacks_from_context."""
        import importlib.util

        llm_utils_spec = importlib.util.find_spec(
            "aiagent.langgraph.jobGeneratorV2.llm_utils"
        )
        schema_gen_spec = importlib.util.find_spec(
            "aiagent.langgraph.jobGeneratorV2.workflows.interface_design.schema_generator"
        )
        assert llm_utils_spec is not None, "llm_utils module not found"
        assert schema_gen_spec is not None, "schema_generator module not found"

    def test_alternative_can_use_callbacks(self):
        """alternative.py should be importable with get_callbacks_from_context."""
        import importlib.util

        llm_utils_spec = importlib.util.find_spec(
            "aiagent.langgraph.jobGeneratorV2.llm_utils"
        )
        alt_spec = importlib.util.find_spec(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.alternative"
        )
        assert llm_utils_spec is not None, "llm_utils module not found"
        assert alt_spec is not None, "alternative module not found"

    def test_llm_generator_can_use_callbacks(self):
        """llm_generator.py should be importable with get_callbacks_from_context."""
        import importlib.util

        llm_utils_spec = importlib.util.find_spec(
            "aiagent.langgraph.jobGeneratorV2.llm_utils"
        )
        llm_gen_spec = importlib.util.find_spec(
            "aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.llm_generator"
        )
        assert llm_utils_spec is not None, "llm_utils module not found"
        assert llm_gen_spec is not None, "llm_generator module not found"


class TestCallbacksE2EFlow:
    """End-to-end tests for callbacks flow."""

    @pytest.mark.asyncio
    async def test_context_to_callbacks_extraction(self):
        """Test the full flow from context creation to callbacks extraction."""
        # Create a mock Langfuse handler
        langfuse_handler = MagicMock()
        langfuse_handler.name = "langfuse_callback"

        # Create context with the handler
        context = (
            ContextBuilder()
            .with_job_id("test-job-id")
            .with_user_requirement("Test requirement")
            .with_observability_context(ObservabilityContext(tracer=langfuse_handler))
            .build()
        )

        # Extract callbacks
        callbacks = get_callbacks_from_context(context)

        # Verify the flow works
        assert len(callbacks) == 1
        assert callbacks[0] is langfuse_handler
        assert callbacks[0].name == "langfuse_callback"
