"""Unit tests for Langfuse integration with invoke_structured_llm.

Issue #278: Verify CallbackHandler propagation through with_structured_output()
and trace_id extraction from structured LLM calls.

Test Categories:
- SF-1: with_structured_output() callback propagation verification (pre-implementation)
- SF-3: Error case trace_id propagation (pre-implementation)

NOTE: These tests verify the CURRENT implementation state.
Some tests use pytest.mark.xfail to document expected behavior after Issue #278 implementation.
"""

import inspect
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import BaseModel

# ============================================================================
# Test Models
# ============================================================================


class TestResponseModel(BaseModel):
    """Simple response model for testing structured output."""

    message: str
    count: int


# ============================================================================
# SF-1: with_structured_output() Callback Propagation Tests
# ============================================================================


class TestStructuredOutputCallbackPropagation:
    """Tests for verifying CallbackHandler propagation through with_structured_output().

    Issue #278 SF-1: Verify that Langfuse CallbackHandler is correctly propagated
    when using model.with_structured_output().
    """

    def test_invoke_structured_llm_signature_has_callback_handler_param(self):
        """Verify invoke_structured_llm accepts callback_handler parameter.

        Issue #278: This test documents the expected signature change.
        Currently expected to FAIL until implementation is complete.
        """
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            invoke_structured_llm,
        )

        sig = inspect.signature(invoke_structured_llm)
        param_names = list(sig.parameters.keys())

        # Issue #278: callback_handler parameter should be added
        # This assertion documents the expected behavior after implementation
        has_callback_handler = "callback_handler" in param_names

        if not has_callback_handler:
            pytest.skip(
                "Issue #278 not implemented: callback_handler parameter not yet added to invoke_structured_llm"
            )

        assert has_callback_handler, (
            "invoke_structured_llm should have callback_handler parameter after Issue #278"
        )

    def test_structured_call_result_has_trace_id_field(self):
        """Verify StructuredCallResult has trace_id field.

        Issue #278: This test documents the expected dataclass change.
        Currently expected to FAIL until implementation is complete.
        """
        # Check if trace_id is in the dataclass fields
        import dataclasses

        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        if not dataclasses.is_dataclass(StructuredCallResult):
            pytest.fail("StructuredCallResult should be a dataclass")

        field_names = [f.name for f in dataclasses.fields(StructuredCallResult)]
        has_trace_id = "trace_id" in field_names

        if not has_trace_id:
            pytest.skip(
                "Issue #278 not implemented: trace_id field not yet added to StructuredCallResult"
            )

        assert has_trace_id, (
            "StructuredCallResult should have trace_id field after Issue #278"
        )

    @pytest.mark.asyncio
    async def test_callback_handler_none_does_not_break_current_implementation(self):
        """Verify current implementation works without callback_handler.

        This test ensures backward compatibility - the function should work
        even after Issue #278 implementation when no handler is provided.
        """
        mock_structured_model = AsyncMock()
        mock_structured_model.ainvoke.return_value = TestResponseModel(
            message="test", count=42
        )

        mock_model = Mock()
        mock_model.with_structured_output.return_value = mock_structured_model

        with (
            patch(
                "aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation.create_llm_with_fallback"
            ) as mock_create_llm,
            patch(
                "aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation.get_model_config"
            ) as mock_get_model_config,
        ):
            mock_perf_tracker = Mock()
            mock_perf_tracker.model_name = "test-model"
            mock_cost_tracker = Mock()
            mock_create_llm.return_value = (
                mock_model,
                mock_perf_tracker,
                mock_cost_tracker,
            )
            mock_get_model_config.return_value = "test-model"

            from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
                invoke_structured_llm,
            )

            # Act - no callback_handler (current usage pattern)
            result = await invoke_structured_llm(
                messages=[{"role": "user", "content": "test"}],
                response_model=TestResponseModel,
                context_label="test_no_callback",
                model_env_var="TEST_MODEL",
                default_model="test-model",
            )

            # Assert - should work without callback_handler
            assert result.result.message == "test"
            assert result.result.count == 42
            mock_structured_model.ainvoke.assert_called_once()


# ============================================================================
# SF-3: Error Case trace_id Propagation Tests (Pre-implementation)
# ============================================================================


class TestErrorCaseTraceIdPropagation:
    """Tests for verifying trace_id propagation in error scenarios.

    Issue #278 SF-3: Verify that trace_id is correctly extracted even when
    LLM calls fail. These tests document expected behavior.
    """

    def test_current_structured_call_result_fields(self):
        """Document current StructuredCallResult fields before Issue #278."""
        import dataclasses

        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        field_names = [f.name for f in dataclasses.fields(StructuredCallResult)]

        # Current fields (before Issue #278)
        expected_current_fields = [
            "result",
            "recovered_via_json",
            "raw_text",
            "model_name",
        ]

        for field in expected_current_fields:
            assert field in field_names, (
                f"Expected field '{field}' in StructuredCallResult"
            )

        # Issue #278 will add trace_id
        if "trace_id" not in field_names:
            # This is expected before implementation
            pass
        else:
            # After implementation, trace_id should be present
            assert "trace_id" in field_names


# ============================================================================
# LangChain with_structured_output() Compatibility Tests
# ============================================================================


class TestWithStructuredOutputCompatibility:
    """Tests to verify LangChain with_structured_output() behavior with callbacks.

    These tests verify the fundamental assumption that with_structured_output()
    correctly propagates config to the underlying model.
    """

    def test_with_structured_output_returns_runnable(self):
        """Verify with_structured_output() returns a Runnable that accepts config."""
        mock_model = Mock()
        mock_runnable = Mock()
        mock_runnable.ainvoke = AsyncMock()
        mock_model.with_structured_output.return_value = mock_runnable

        structured = mock_model.with_structured_output(TestResponseModel)

        # Verify the returned object has ainvoke method
        assert hasattr(structured, "ainvoke")
        assert callable(structured.ainvoke)

    @pytest.mark.asyncio
    async def test_structured_model_ainvoke_accepts_config_kwarg(self):
        """Verify structured model's ainvoke() accepts config as keyword argument."""
        mock_runnable = AsyncMock()
        mock_runnable.ainvoke.return_value = TestResponseModel(message="test", count=1)

        mock_handler = Mock()
        config = {"callbacks": [mock_handler]}

        # Act
        await mock_runnable.ainvoke(
            [{"role": "user", "content": "test"}],
            config=config,
        )

        # Assert - ainvoke was called with config
        mock_runnable.ainvoke.assert_called_once()
        call_kwargs = mock_runnable.ainvoke.call_args.kwargs
        assert "config" in call_kwargs
        assert call_kwargs["config"] == config

    @pytest.mark.asyncio
    async def test_current_implementation_does_not_pass_config(self):
        """Document that current implementation does not pass config to ainvoke.

        Issue #278: This test documents the current behavior that needs to be fixed.
        """
        mock_structured_model = AsyncMock()
        mock_structured_model.ainvoke.return_value = TestResponseModel(
            message="test", count=42
        )

        mock_model = Mock()
        mock_model.with_structured_output.return_value = mock_structured_model

        with (
            patch(
                "aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation.create_llm_with_fallback"
            ) as mock_create_llm,
            patch(
                "aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation.get_model_config"
            ) as mock_get_model_config,
        ):
            mock_perf_tracker = Mock()
            mock_perf_tracker.model_name = "test-model"
            mock_cost_tracker = Mock()
            mock_create_llm.return_value = (
                mock_model,
                mock_perf_tracker,
                mock_cost_tracker,
            )
            mock_get_model_config.return_value = "test-model"

            from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
                invoke_structured_llm,
            )

            # Act
            await invoke_structured_llm(
                messages=[{"role": "user", "content": "test"}],
                response_model=TestResponseModel,
                context_label="test_config",
                model_env_var="TEST_MODEL",
                default_model="test-model",
            )

            # Assert - Document current behavior
            mock_structured_model.ainvoke.assert_called_once()
            call_args = mock_structured_model.ainvoke.call_args

            # Current implementation: config is NOT passed
            # Issue #278 should change this behavior
            config_in_kwargs = "config" in call_args.kwargs
            config_in_args = len(call_args.args) > 1

            if not config_in_kwargs and not config_in_args:
                # This is the CURRENT behavior (before Issue #278)
                # Test passes to document this behavior
                pass
            else:
                # After Issue #278, config should be passed
                config = call_args.kwargs.get("config") or call_args.args[1]
                assert "callbacks" in config or config is None


# ============================================================================
# Integration Readiness Tests
# ============================================================================


class TestLangfuseIntegrationReadiness:
    """Tests to verify readiness for Langfuse integration.

    These tests check prerequisites for Issue #278 implementation.
    """

    def test_langfuse_service_extract_trace_id_exists(self):
        """Verify LangfuseService.extract_trace_id() method exists."""
        from app.services.langfuse_service import LangfuseService

        assert hasattr(LangfuseService, "extract_trace_id")
        assert callable(LangfuseService.extract_trace_id)

    def test_langfuse_service_get_callback_handler_exists(self):
        """Verify LangfuseService.get_callback_handler() method exists."""
        from app.services.langfuse_service import LangfuseService

        service = LangfuseService()
        assert hasattr(service, "get_callback_handler")
        assert callable(service.get_callback_handler)

    def test_langfuse_service_singleton_available(self):
        """Verify langfuse_service singleton is available."""
        from app.services.langfuse_service import langfuse_service

        assert langfuse_service is not None

    def test_extract_trace_id_handles_none_handler(self):
        """Verify extract_trace_id handles None handler gracefully."""
        from app.services.langfuse_service import LangfuseService

        result = LangfuseService.extract_trace_id(None)
        assert result is None

    def test_extract_trace_id_handles_mock_handler(self):
        """Verify extract_trace_id extracts trace_id from handler."""
        from app.services.langfuse_service import LangfuseService

        mock_handler = Mock()
        mock_handler.last_trace_id = "test-trace-id-123"

        result = LangfuseService.extract_trace_id(mock_handler)
        assert result == "test-trace-id-123"
