"""Unit tests for Langfuse integration with invoke_structured_llm.

Issue #278: Verify CallbackHandler propagation through with_structured_output()
and trace_id extraction from structured LLM calls.

Test Categories:
- SF-1: with_structured_output() callback propagation verification
- SF-2: trace_id extraction and return in StructuredCallResult
- SF-3: Error case trace_id propagation
- SF-4: Backward compatibility tests

TDD Implementation: RED -> GREEN -> REFACTOR
"""

import dataclasses
import inspect
from unittest.mock import AsyncMock, Mock, patch

import pytest
from pydantic import BaseModel

# ============================================================================
# Test Models
# ============================================================================


class SimpleResponseModel(BaseModel):
    """Simple response model for testing structured output."""

    message: str
    count: int


# ============================================================================
# SF-1: StructuredCallResult trace_id Field Tests
# ============================================================================


class TestStructuredCallResultTraceId:
    """Tests for StructuredCallResult trace_id field.

    Issue #278 Task 1.1: Add trace_id field to StructuredCallResult.
    """

    def test_structured_call_result_has_trace_id_field(self):
        """Verify StructuredCallResult has trace_id field.

        Issue #278 Task 1.1: trace_id field must be added to StructuredCallResult.
        """
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        assert dataclasses.is_dataclass(StructuredCallResult), (
            "StructuredCallResult should be a dataclass"
        )

        field_names = [f.name for f in dataclasses.fields(StructuredCallResult)]
        assert "trace_id" in field_names, (
            "StructuredCallResult should have trace_id field after Issue #278"
        )

    def test_structured_call_result_trace_id_type(self):
        """Verify trace_id field has correct type annotation (str | None)."""
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        fields = {f.name: f for f in dataclasses.fields(StructuredCallResult)}
        trace_id_field = fields.get("trace_id")

        assert trace_id_field is not None, "trace_id field must exist"
        # Type should be str | None
        assert trace_id_field.default is None, "trace_id should default to None"


# ============================================================================
# SF-2: invoke_structured_llm callback_handler Parameter Tests
# ============================================================================


class TestInvokeStructuredLlmCallbackHandler:
    """Tests for invoke_structured_llm callback_handler parameter.

    Issue #278 Task 1.2: Add callback_handler argument to invoke_structured_llm.
    """

    def test_invoke_structured_llm_signature_has_callback_handler_param(self):
        """Verify invoke_structured_llm accepts callback_handler parameter.

        Issue #278 Task 1.2: callback_handler parameter must be added.
        """
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            invoke_structured_llm,
        )

        sig = inspect.signature(invoke_structured_llm)
        param_names = list(sig.parameters.keys())

        assert "callback_handler" in param_names, (
            "invoke_structured_llm should have callback_handler parameter"
        )

    def test_callback_handler_param_defaults_to_none(self):
        """Verify callback_handler parameter defaults to None."""
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            invoke_structured_llm,
        )

        sig = inspect.signature(invoke_structured_llm)
        callback_handler_param = sig.parameters.get("callback_handler")

        assert callback_handler_param is not None, (
            "callback_handler parameter must exist"
        )
        assert callback_handler_param.default is None, (
            "callback_handler should default to None"
        )

    @pytest.mark.asyncio
    async def test_callback_handler_passed_to_ainvoke_config(self):
        """Verify callback_handler is passed to ainvoke via config.

        Issue #278 Task 1.3: ainvoke() must receive config with callbacks.
        """
        mock_structured_model = AsyncMock()
        mock_structured_model.ainvoke.return_value = SimpleResponseModel(
            message="test", count=42
        )

        mock_model = Mock()
        mock_model.with_structured_output.return_value = mock_structured_model

        mock_handler = Mock()
        mock_handler.last_trace_id = "test-trace-123"

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

            # Act - pass callback_handler
            await invoke_structured_llm(
                messages=[{"role": "user", "content": "test"}],
                response_model=SimpleResponseModel,
                context_label="test_with_callback",
                model_env_var="TEST_MODEL",
                default_model="test-model",
                callback_handler=mock_handler,
            )

            # Assert - ainvoke was called with config containing callbacks
            mock_structured_model.ainvoke.assert_called_once()
            call_args = mock_structured_model.ainvoke.call_args

            # Check config was passed
            assert "config" in call_args.kwargs, (
                "ainvoke must receive config keyword argument"
            )
            config = call_args.kwargs["config"]
            assert "callbacks" in config, "config must contain 'callbacks'"
            assert mock_handler in config["callbacks"], (
                "callback_handler must be in callbacks list"
            )


# ============================================================================
# SF-3: trace_id Extraction and Return Tests
# ============================================================================


class TestTraceIdExtraction:
    """Tests for trace_id extraction from CallbackHandler.

    Issue #278 Task 1.4: Extract trace_id from handler and return in result.
    """

    @pytest.mark.asyncio
    async def test_trace_id_extracted_from_handler_on_success(self):
        """Verify trace_id is extracted from handler after successful call."""
        mock_structured_model = AsyncMock()
        mock_structured_model.ainvoke.return_value = SimpleResponseModel(
            message="success", count=100
        )

        mock_model = Mock()
        mock_model.with_structured_output.return_value = mock_structured_model

        mock_handler = Mock()
        mock_handler.last_trace_id = "trace-success-123"

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
            result = await invoke_structured_llm(
                messages=[{"role": "user", "content": "test"}],
                response_model=SimpleResponseModel,
                context_label="test_trace_extraction",
                model_env_var="TEST_MODEL",
                default_model="test-model",
                callback_handler=mock_handler,
            )

            # Assert
            assert result.trace_id == "trace-success-123", (
                "trace_id should be extracted from handler"
            )

    @pytest.mark.asyncio
    async def test_trace_id_none_when_no_handler(self):
        """Verify trace_id is None when no callback_handler is provided."""
        mock_structured_model = AsyncMock()
        mock_structured_model.ainvoke.return_value = SimpleResponseModel(
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

            # Act - no callback_handler
            result = await invoke_structured_llm(
                messages=[{"role": "user", "content": "test"}],
                response_model=SimpleResponseModel,
                context_label="test_no_handler",
                model_env_var="TEST_MODEL",
                default_model="test-model",
            )

            # Assert
            assert result.trace_id is None, (
                "trace_id should be None when no handler provided"
            )

    @pytest.mark.asyncio
    async def test_trace_id_none_when_handler_has_no_trace_id(self):
        """Verify trace_id is None when handler has no last_trace_id attribute."""
        mock_structured_model = AsyncMock()
        mock_structured_model.ainvoke.return_value = SimpleResponseModel(
            message="test", count=42
        )

        mock_model = Mock()
        mock_model.with_structured_output.return_value = mock_structured_model

        mock_handler = Mock(spec=[])  # No last_trace_id attribute

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
            result = await invoke_structured_llm(
                messages=[{"role": "user", "content": "test"}],
                response_model=SimpleResponseModel,
                context_label="test_no_trace_id_attr",
                model_env_var="TEST_MODEL",
                default_model="test-model",
                callback_handler=mock_handler,
            )

            # Assert
            assert result.trace_id is None, (
                "trace_id should be None when handler has no last_trace_id"
            )


# ============================================================================
# SF-4: JSON Recovery Path trace_id Tests
# ============================================================================


class TestJsonRecoveryTraceId:
    """Tests for trace_id handling in JSON recovery path.

    Issue #278: trace_id should be captured even when JSON fallback is used.
    """

    @pytest.mark.asyncio
    async def test_trace_id_preserved_in_json_recovery(self):
        """Verify trace_id is preserved when recovering via JSON fallback."""
        # Setup mock for primary failure, then JSON recovery success
        mock_structured_model = AsyncMock()
        mock_structured_model.ainvoke.side_effect = ValueError(
            "Structured output failed"
        )

        mock_raw_response = Mock()
        mock_raw_response.content = '{"message": "recovered", "count": 99}'
        mock_raw_response.usage_metadata = None

        mock_model = Mock()
        mock_model.with_structured_output.return_value = mock_structured_model
        mock_model.ainvoke = AsyncMock(return_value=mock_raw_response)

        mock_handler = Mock()
        mock_handler.last_trace_id = "trace-recovery-456"

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
            result = await invoke_structured_llm(
                messages=[{"role": "user", "content": "test"}],
                response_model=SimpleResponseModel,
                context_label="test_json_recovery",
                model_env_var="TEST_MODEL",
                default_model="test-model",
                callback_handler=mock_handler,
            )

            # Assert
            assert result.recovered_via_json is True, "Should be recovered via JSON"
            assert result.trace_id == "trace-recovery-456", (
                "trace_id should be preserved in JSON recovery path"
            )


# ============================================================================
# SF-5: Backward Compatibility Tests
# ============================================================================


class TestBackwardCompatibility:
    """Tests for backward compatibility after Issue #278.

    Ensure existing code without callback_handler continues to work.
    """

    @pytest.mark.asyncio
    async def test_invoke_without_callback_handler_works(self):
        """Verify function works without callback_handler parameter."""
        mock_structured_model = AsyncMock()
        mock_structured_model.ainvoke.return_value = SimpleResponseModel(
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

            # Act - no callback_handler (existing usage pattern)
            result = await invoke_structured_llm(
                messages=[{"role": "user", "content": "test"}],
                response_model=SimpleResponseModel,
                context_label="test_backward_compat",
                model_env_var="TEST_MODEL",
                default_model="test-model",
            )

            # Assert
            assert result.result.message == "test"
            assert result.result.count == 42
            assert result.trace_id is None, "trace_id should be None without handler"

    def test_structured_call_result_has_all_original_fields(self):
        """Verify all original fields are still present."""
        from aiagent.langgraph.jobTaskGeneratorAgents.utils.llm_invocation import (
            StructuredCallResult,
        )

        field_names = [f.name for f in dataclasses.fields(StructuredCallResult)]

        # Original fields must still exist
        expected_original_fields = [
            "result",
            "recovered_via_json",
            "raw_text",
            "model_name",
        ]

        for field in expected_original_fields:
            assert field in field_names, f"Original field '{field}' must be preserved"


# ============================================================================
# LangfuseService Integration Readiness Tests
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
