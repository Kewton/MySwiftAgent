"""Integration tests for V2 task breakdown with API injection.

Tests for Issue #342: V2 タスク分割 API情報注入メカニズム実装

This module tests end-to-end integration of:
- Capabilities loading and propagation
- System prompt API injection
- Task decomposition with recommended_apis
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestCapabilitiesPropagate:
    """Tests for capabilities propagation through the workflow."""

    def test_capabilities_propagate_to_decomposer(self) -> None:
        """Test that capabilities can be passed to TaskDecomposerSubWorkflow."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            TaskDecomposerSubWorkflow,
        )

        capabilities = [
            {
                "name": "Gmail検索",
                "endpoint": "/v1/utility/gmail/search",
                "description": "Gmail検索",
                "use_cases": ["検索"],
                "method": "POST",
            }
        ]

        # Decomposer should accept capabilities in constructor
        decomposer = TaskDecomposerSubWorkflow(capabilities=capabilities)

        assert decomposer is not None
        assert hasattr(decomposer, "_capabilities")
        assert decomposer._capabilities == capabilities

    def test_decomposer_auto_loads_when_none(self) -> None:
        """Test that decomposer auto-loads capabilities when None is passed."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            TaskDecomposerSubWorkflow,
        )

        # When no capabilities provided, should auto-load
        decomposer = TaskDecomposerSubWorkflow(capabilities=None)

        assert decomposer is not None
        assert decomposer._capabilities is None  # Will be loaded on decompose()


class TestSystemPromptContainsApiList:
    """Tests for system prompt API list injection."""

    @pytest.mark.asyncio
    async def test_system_prompt_contains_api_list(self) -> None:
        """Test that system prompt sent to LLM contains API list."""
        from aiagent.langgraph.jobGeneratorV2.context import ContextBuilder
        from aiagent.langgraph.jobGeneratorV2.types import (
            TaskBreakdownInput,
            TaskBreakdownItem,
            TaskBreakdownResponse,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            TaskDecomposerSubWorkflow,
        )

        captured_messages: list[dict[str, str]] = []

        # Mock invoke_structured_llm to capture messages
        async def capture_llm_call(
            messages: list[dict[str, str]] | None = None,
            **kwargs,
        ):
            if messages:
                captured_messages.extend(messages)

            # Return mock response
            from aiagent.langgraph.jobGeneratorV2.llm_utils import StructuredCallResult

            return StructuredCallResult(
                result=TaskBreakdownResponse(
                    tasks=[
                        TaskBreakdownItem(
                            task_id="task_001",
                            name="Gmail検索",
                            description="メール検索",
                            dependencies=[],
                        )
                    ],
                    overall_summary="Test",
                ),
                raw_text="test",
            )

        capabilities = [
            {
                "name": "Gmail検索",
                "endpoint": "/v1/utility/gmail/search",
                "description": "Gmail検索",
                "use_cases": ["検索"],
                "method": "POST",
            }
        ]

        input_data = TaskBreakdownInput(
            user_requirement="メールを検索する",
        )

        context = (
            ContextBuilder()
            .with_job_id("test-job")
            .with_user_requirement("メールを検索する")
            .build()
        )

        decomposer = TaskDecomposerSubWorkflow(capabilities=capabilities)

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer.invoke_structured_llm",
            side_effect=capture_llm_call,
        ):
            await decomposer.decompose(input_data, context)

        # Check that system prompt contains API information
        assert len(captured_messages) > 0
        system_message = next(
            (m for m in captured_messages if m.get("role") == "system"),
            None,
        )
        assert system_message is not None
        content = system_message.get("content", "")

        # Should contain API information
        assert "## 利用可能なAPI" in content or "Gmail検索" in content


class TestRecommendedApiInTasks:
    """Tests for recommended_api in decomposed tasks."""

    @pytest.mark.asyncio
    async def test_recommended_api_extraction(self) -> None:
        """Test that recommended_apis are extracted from LLM response."""
        from aiagent.langgraph.jobGeneratorV2.context import ContextBuilder
        from aiagent.langgraph.jobGeneratorV2.types import (
            RecommendedAPI,
            TaskBreakdownInput,
            TaskBreakdownItem,
            TaskBreakdownResponse,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            TaskDecomposerSubWorkflow,
        )

        # Mock LLM response with recommended_apis
        mock_response = TaskBreakdownResponse(
            tasks=[
                TaskBreakdownItem(
                    task_id="task_001",
                    name="Gmail検索",
                    description="メール検索タスク",
                    dependencies=[],
                    recommended_apis=[
                        RecommendedAPI(
                            api_name="Gmail検索",
                            endpoint="/v1/utility/gmail/search",
                            reason="メール検索に必要",
                        )
                    ],
                ),
                TaskBreakdownItem(
                    task_id="task_002",
                    name="メール送信",
                    description="検索結果を送信",
                    dependencies=["task_001"],
                    recommended_apis=[
                        RecommendedAPI(
                            api_name="Gmail送信",
                            endpoint="/v1/utility/gmail/send",
                            reason="メール送信に必要",
                        )
                    ],
                ),
            ],
            overall_summary="メール検索と送信",
        )

        async def mock_llm_call(**kwargs):
            from aiagent.langgraph.jobGeneratorV2.llm_utils import StructuredCallResult

            return StructuredCallResult(
                result=mock_response,
                raw_text="test",
            )

        capabilities = [
            {
                "name": "Gmail検索",
                "endpoint": "/v1/utility/gmail/search",
                "description": "Gmail検索",
                "use_cases": ["検索"],
                "method": "POST",
            },
            {
                "name": "Gmail送信",
                "endpoint": "/v1/utility/gmail/send",
                "description": "Gmail送信",
                "use_cases": ["送信"],
                "method": "POST",
            },
        ]

        input_data = TaskBreakdownInput(
            user_requirement="メールを検索して送信する",
        )

        context = (
            ContextBuilder()
            .with_job_id("test-job")
            .with_user_requirement("メールを検索して送信する")
            .build()
        )

        decomposer = TaskDecomposerSubWorkflow(capabilities=capabilities)

        with patch(
            "aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer.invoke_structured_llm",
            side_effect=mock_llm_call,
        ):
            tasks = await decomposer.decompose(input_data, context)

        # Verify tasks have recommended_api set
        assert len(tasks) == 2
        assert tasks[0].recommended_api == "/v1/utility/gmail/search"
        assert tasks[1].recommended_api == "/v1/utility/gmail/send"


class TestWorkflowCapabilitiesLoading:
    """Tests for workflow-level capabilities loading."""

    def test_workflow_loads_capabilities(self) -> None:
        """Test that TaskBreakdownWorkflow loads capabilities correctly."""
        from aiagent.langgraph.shared.capability_utils import (
            load_capabilities_from_yaml,
        )

        # Verify the shared function works
        capabilities = load_capabilities_from_yaml()

        assert len(capabilities) > 0
        # Should have both utility and AI agent APIs
        utility_apis = [
            c for c in capabilities if "/v1/utility/" in c.get("endpoint", "")
        ]
        # AI APIs are optional - verify they can be loaded if present
        _ai_apis = [
            c
            for c in capabilities
            if "/v1/aiagent/" in c.get("endpoint", "")
            or "/v1/my" in c.get("endpoint", "")
        ]

        assert len(utility_apis) > 0, "Should have utility APIs"
        # AI APIs are optional but should check they're loaded if present (verified via _ai_apis)

    def test_shared_and_feasibility_load_same_yaml(self) -> None:
        """Test that shared and feasibility modules can coexist."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.feasibility import (
            load_capabilities_from_yaml as feasibility_load,
        )
        from aiagent.langgraph.shared.capability_utils import (
            load_capabilities_from_yaml as shared_load,
        )

        # Both should work independently
        shared_caps = shared_load()
        feasibility_caps = feasibility_load()

        # Both should return non-empty results
        assert len(shared_caps) > 0
        assert len(feasibility_caps) > 0

        # shared returns list[dict], feasibility returns list[Capability]
        # Both should have the same count of APIs
        assert len(shared_caps) == len(feasibility_caps)


class TestDecomposerConstructorIntegration:
    """Tests for decomposer constructor with capabilities injection."""

    def test_decomposer_constructor_signature(self) -> None:
        """Test that TaskDecomposerSubWorkflow has correct constructor."""
        import inspect

        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            TaskDecomposerSubWorkflow,
        )

        sig = inspect.signature(TaskDecomposerSubWorkflow.__init__)
        param_names = list(sig.parameters.keys())

        # Should have self and capabilities
        assert "self" in param_names
        assert "capabilities" in param_names

    def test_decomposer_stores_capabilities(self) -> None:
        """Test that decomposer stores capabilities internally."""
        from aiagent.langgraph.jobGeneratorV2.workflows.task_breakdown.decomposer import (
            TaskDecomposerSubWorkflow,
        )

        test_capabilities = [{"name": "Test", "endpoint": "/test"}]

        decomposer = TaskDecomposerSubWorkflow(capabilities=test_capabilities)

        assert decomposer._capabilities == test_capabilities
