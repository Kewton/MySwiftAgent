"""Unit tests for shared/capability_utils module.

Tests for Issue #342: V2 タスク分割 API情報注入メカニズム実装

This module tests:
- load_capabilities_from_yaml() function
- format_capabilities_for_prompt() function
- Capability type extensions (use_cases, method fields)
"""

from __future__ import annotations


class TestLoadCapabilitiesFromYaml:
    """Tests for load_capabilities_from_yaml function."""

    def test_load_capabilities_from_yaml(self) -> None:
        """Test that capabilities are loaded from YAML."""
        from aiagent.langgraph.shared.capability_utils import (
            load_capabilities_from_yaml,
        )

        capabilities = load_capabilities_from_yaml()

        assert capabilities is not None
        assert len(capabilities) > 0

    def test_load_capabilities_yaml_not_found(self) -> None:
        """Test that empty list is returned when YAML file is not found."""
        from pathlib import Path
        from unittest.mock import patch

        from aiagent.langgraph.shared.capability_utils import (
            load_capabilities_from_yaml,
        )

        # Use a non-existent path
        fake_path = Path("/non/existent/path")

        with patch(
            "aiagent.langgraph.shared.capability_utils._CONFIG_PATH",
            fake_path,
        ):
            result = load_capabilities_from_yaml()
            assert result == []

    def test_load_capabilities_yaml_parse_error(self) -> None:
        """Test that empty list is returned on YAML parse error."""
        import tempfile
        from pathlib import Path
        from unittest.mock import patch

        from aiagent.langgraph.shared.capability_utils import (
            load_capabilities_from_yaml,
        )

        # Create a temp file with invalid YAML
        with tempfile.TemporaryDirectory() as tmp_dir:
            yaml_path = Path(tmp_dir) / "expert_agent_capabilities.yaml"
            yaml_path.write_text("invalid: yaml: content: [", encoding="utf-8")

            with patch(
                "aiagent.langgraph.shared.capability_utils._CONFIG_PATH",
                Path(tmp_dir),
            ):
                result = load_capabilities_from_yaml()
                assert result == []

    def test_load_capabilities_includes_use_cases(self) -> None:
        """Test that loaded capabilities include use_cases field."""
        from aiagent.langgraph.shared.capability_utils import (
            load_capabilities_from_yaml,
        )

        capabilities = load_capabilities_from_yaml()

        # Find Gmail search API
        gmail_search = next(
            (c for c in capabilities if "Gmail検索" in c.get("name", "")),
            None,
        )
        assert gmail_search is not None, "Gmail検索 API should exist"
        assert "use_cases" in gmail_search
        assert isinstance(gmail_search["use_cases"], list)
        assert len(gmail_search["use_cases"]) > 0

    def test_load_capabilities_includes_method(self) -> None:
        """Test that loaded capabilities include method field."""
        from aiagent.langgraph.shared.capability_utils import (
            load_capabilities_from_yaml,
        )

        capabilities = load_capabilities_from_yaml()

        # All capabilities should have method field
        for cap in capabilities:
            assert "method" in cap, f"Capability '{cap.get('name')}' missing 'method'"
            assert cap["method"] in ["GET", "POST", "PUT", "DELETE"]


class TestFormatCapabilitiesForPrompt:
    """Tests for format_capabilities_for_prompt function."""

    def test_format_capabilities_empty(self) -> None:
        """Test format_capabilities_for_prompt with empty list."""
        from aiagent.langgraph.shared.capability_utils import (
            format_capabilities_for_prompt,
        )

        result = format_capabilities_for_prompt([])

        assert result == ""

    def test_format_capabilities_includes_api_info(self) -> None:
        """Test that formatted output includes API information."""
        from aiagent.langgraph.shared.capability_utils import (
            format_capabilities_for_prompt,
        )

        capabilities = [
            {
                "name": "Gmail検索",
                "endpoint": "/v1/utility/gmail/search",
                "description": "Gmail検索（高速・AIフレンドリー）",
                "use_cases": ["キーワード検索", "日付範囲指定"],
                "method": "POST",
            }
        ]

        result = format_capabilities_for_prompt(capabilities)

        assert "Gmail検索" in result
        assert "/v1/utility/gmail/search" in result
        assert "Gmail検索（高速・AIフレンドリー）" in result
        assert "キーワード検索" in result

    def test_format_capabilities_groups_by_type(self) -> None:
        """Test that capabilities are grouped by API type."""
        from aiagent.langgraph.shared.capability_utils import (
            format_capabilities_for_prompt,
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
                "name": "Direct LLM",
                "endpoint": "/v1/mylllm",
                "description": "LLM呼び出し",
                "use_cases": ["LLM処理"],
                "method": "POST",
            },
        ]

        result = format_capabilities_for_prompt(capabilities)

        assert "## 利用可能なAPI" in result
        assert "Utility API" in result
        assert "AI Agent API" in result

    def test_format_capabilities_integration(self) -> None:
        """Integration test: format capabilities loaded from YAML."""
        from aiagent.langgraph.shared.capability_utils import (
            format_capabilities_for_prompt,
            load_capabilities_from_yaml,
        )

        capabilities = load_capabilities_from_yaml()
        result = format_capabilities_for_prompt(capabilities)

        assert "## 利用可能なAPI" in result
        # Should contain at least some known APIs
        assert "/v1/utility/" in result or "/v1/aiagent/" in result


class TestCapabilityTypeExtension:
    """Tests for Capability type in types.py with new fields."""

    def test_capability_type_has_use_cases_field(self) -> None:
        """Test that Capability dataclass has use_cases field."""
        from aiagent.langgraph.jobGeneratorV2.types import Capability

        cap = Capability(
            name="Test API",
            description="Test description",
            endpoint="/v1/test",
            use_cases=["case1", "case2"],
        )

        assert hasattr(cap, "use_cases")
        assert cap.use_cases == ["case1", "case2"]

    def test_capability_type_has_method_field(self) -> None:
        """Test that Capability dataclass has method field."""
        from aiagent.langgraph.jobGeneratorV2.types import Capability

        cap = Capability(
            name="Test API",
            description="Test description",
            endpoint="/v1/test",
            method="POST",
        )

        assert hasattr(cap, "method")
        assert cap.method == "POST"

    def test_capability_type_defaults(self) -> None:
        """Test Capability default values for new fields."""
        from aiagent.langgraph.jobGeneratorV2.types import Capability

        cap = Capability(
            name="Test API",
            description="Test description",
            endpoint="/v1/test",
        )

        # Check default values
        assert cap.use_cases == []
        assert cap.method == "POST"
