"""Unit tests for llm_utils system prompt with API information.

Tests for Issue #342: V2 タスク分割 API情報注入メカニズム実装

This module tests:
- _build_task_breakdown_system_prompt() with capabilities
- System prompt includes API information when capabilities provided
"""

from __future__ import annotations


class TestBuildTaskBreakdownSystemPrompt:
    """Tests for _build_task_breakdown_system_prompt function."""

    def test_system_prompt_exists(self) -> None:
        """Test that _build_task_breakdown_system_prompt function exists."""
        from aiagent.langgraph.jobGeneratorV2.llm_utils import (
            _build_task_breakdown_system_prompt,
        )

        assert callable(_build_task_breakdown_system_prompt)

    def test_system_prompt_includes_apis(self) -> None:
        """Test that system prompt includes API info when capabilities provided."""
        from aiagent.langgraph.jobGeneratorV2.llm_utils import (
            _build_task_breakdown_system_prompt,
        )

        capabilities = [
            {
                "name": "Gmail検索",
                "endpoint": "/v1/utility/gmail/search",
                "description": "Gmail検索（高速・AIフレンドリー）",
                "use_cases": ["キーワード検索", "日付範囲指定"],
                "method": "POST",
            },
            {
                "name": "Google検索",
                "endpoint": "/v1/utility/google_search",
                "description": "Web検索（Serper API使用）",
                "use_cases": ["キーワード検索"],
                "method": "POST",
            },
        ]

        result = _build_task_breakdown_system_prompt(capabilities=capabilities)

        # Should include API information
        assert "## 利用可能なAPI" in result
        assert "Gmail検索" in result
        assert "/v1/utility/gmail/search" in result
        # Should include recommended_apis instruction
        assert "recommended_apis" in result

    def test_system_prompt_without_apis(self) -> None:
        """Test that system prompt works without capabilities."""
        from aiagent.langgraph.jobGeneratorV2.llm_utils import (
            _build_task_breakdown_system_prompt,
        )

        # With None
        result = _build_task_breakdown_system_prompt(capabilities=None)
        assert "expert task decomposition" in result.lower()

        # With empty list
        result = _build_task_breakdown_system_prompt(capabilities=[])
        assert "expert task decomposition" in result.lower()
        # Should NOT include API section when no capabilities
        assert "## 利用可能なAPI" not in result

    def test_system_prompt_includes_few_shot_example(self) -> None:
        """Test that system prompt includes few-shot example when APIs provided."""
        from aiagent.langgraph.jobGeneratorV2.llm_utils import (
            _build_task_breakdown_system_prompt,
        )

        capabilities = [
            {
                "name": "Google検索",
                "endpoint": "/v1/utility/google_search",
                "description": "Web検索",
                "use_cases": ["検索"],
                "method": "POST",
            },
        ]

        result = _build_task_breakdown_system_prompt(capabilities=capabilities)

        # Should include example section
        assert "api_name" in result or "endpoint" in result
        assert "reason" in result or "推奨" in result

    def test_system_prompt_signature_accepts_capabilities(self) -> None:
        """Test that _build_task_breakdown_system_prompt accepts capabilities param."""
        import inspect

        from aiagent.langgraph.jobGeneratorV2.llm_utils import (
            _build_task_breakdown_system_prompt,
        )

        sig = inspect.signature(_build_task_breakdown_system_prompt)
        param_names = list(sig.parameters.keys())

        assert "capabilities" in param_names


class TestCreateTaskBreakdownPrompt:
    """Tests for create_task_breakdown_prompt function."""

    def test_create_prompt_with_capabilities(self) -> None:
        """Test create_task_breakdown_prompt includes available capabilities."""
        from aiagent.langgraph.jobGeneratorV2.llm_utils import (
            create_task_breakdown_prompt,
        )

        capabilities = [
            {
                "name": "Gmail検索",
                "description": "Gmail検索",
            },
        ]

        result = create_task_breakdown_prompt(
            user_requirement="メールを検索する",
            available_capabilities=capabilities,
        )

        # Should include capability info
        assert "Gmail検索" in result
        assert "メールを検索する" in result


class TestSystemPromptIntegrationWithShared:
    """Tests for integration between llm_utils and shared/capability_utils."""

    def test_system_prompt_uses_shared_format(self) -> None:
        """Test that system prompt can use shared format_capabilities_for_prompt."""
        from aiagent.langgraph.jobGeneratorV2.llm_utils import (
            _build_task_breakdown_system_prompt,
        )
        from aiagent.langgraph.shared.capability_utils import (
            format_capabilities_for_prompt,
            load_capabilities_from_yaml,
        )

        # Load actual capabilities
        capabilities = load_capabilities_from_yaml()

        # Build system prompt
        system_prompt = _build_task_breakdown_system_prompt(capabilities=capabilities)

        # The formatted capabilities should be in the system prompt
        formatted = format_capabilities_for_prompt(capabilities)
        # At minimum, the API header should be present
        if formatted:
            assert "## 利用可能なAPI" in system_prompt

    def test_prompt_contains_all_loaded_utility_apis(self) -> None:
        """Test that prompt contains utility APIs from YAML."""
        from aiagent.langgraph.jobGeneratorV2.llm_utils import (
            _build_task_breakdown_system_prompt,
        )
        from aiagent.langgraph.shared.capability_utils import (
            load_capabilities_from_yaml,
        )

        capabilities = load_capabilities_from_yaml()
        system_prompt = _build_task_breakdown_system_prompt(capabilities=capabilities)

        # Check that some known utility APIs are mentioned
        utility_apis = [c for c in capabilities if "/v1/utility/" in c.get("endpoint", "")]
        if utility_apis:
            # At least one utility API should be in the prompt
            found_any = any(
                api.get("name", "") in system_prompt
                for api in utility_apis[:3]  # Check first 3
            )
            assert found_any, "System prompt should contain utility API information"
