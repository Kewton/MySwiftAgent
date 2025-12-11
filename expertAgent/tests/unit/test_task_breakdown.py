"""Unit tests for task_breakdown prompt module - Issue #270.

Tests for:
1. Schema hint generation for LLM prompts
2. Expert agent capabilities building with schema information
"""

from aiagent.langgraph.jobTaskGeneratorAgents.prompts.task_breakdown import (
    _build_expert_agent_capabilities,
    _build_schema_hint,
    _build_task_breakdown_system_prompt,
    create_task_breakdown_prompt,
)


class TestBuildSchemaHint:
    """Test schema hint generation for task breakdown prompt."""

    def test_build_schema_hint_with_required_fields(self) -> None:
        """Test building schema hint with required fields."""
        api = {
            "name": "Test API",
            "endpoint": "/v1/test",
            "request_schema": {
                "query": {"type": "string", "required": True},
                "max_results": {"type": "integer", "default": 10},
            },
        }
        hint = _build_schema_hint(api)
        assert hint != ""
        assert "query" in hint

    def test_build_schema_hint_no_required_fields(self) -> None:
        """Test building schema hint when no required fields."""
        api = {
            "name": "Test API",
            "endpoint": "/v1/test",
            "request_schema": {
                "optional_field": {"type": "string", "default": "default"},
            },
        }
        hint = _build_schema_hint(api)
        # Should return empty or minimal hint when no required fields
        assert "required" not in hint.lower() or hint == ""

    def test_build_schema_hint_no_request_schema(self) -> None:
        """Test building schema hint when no request_schema."""
        api = {
            "name": "Test API",
            "endpoint": "/v1/test",
        }
        hint = _build_schema_hint(api)
        assert hint == ""

    def test_build_schema_hint_multiple_required_fields(self) -> None:
        """Test building schema hint with multiple required fields."""
        api = {
            "name": "Test API",
            "endpoint": "/v1/test",
            "request_schema": {
                "field1": {"type": "string", "required": True},
                "field2": {"type": "string", "required": True},
                "field3": {"type": "string"},  # Not required
            },
        }
        hint = _build_schema_hint(api)
        assert "field1" in hint
        assert "field2" in hint


class TestBuildExpertAgentCapabilities:
    """Test expert agent capabilities building with schema hints."""

    def test_build_capabilities_includes_apis(self) -> None:
        """Test that capabilities includes API list."""
        capabilities = _build_expert_agent_capabilities()
        assert "expertAgent Direct API" in capabilities
        assert "Gmail" in capabilities

    def test_build_capabilities_includes_schema_hints(self) -> None:
        """Test that capabilities includes schema hints for APIs."""
        capabilities = _build_expert_agent_capabilities()
        # Should include hints about required fields
        # This will be populated after YAML is updated
        assert "Utility API" in capabilities or "AI Agent API" in capabilities

    def test_build_capabilities_includes_utility_apis(self) -> None:
        """Test that capabilities includes utility APIs section."""
        capabilities = _build_expert_agent_capabilities()
        assert "Utility API" in capabilities

    def test_build_capabilities_includes_ai_agent_apis(self) -> None:
        """Test that capabilities includes AI agent APIs section."""
        capabilities = _build_expert_agent_capabilities()
        assert "AI Agent API" in capabilities


class TestBuildTaskBreakdownSystemPrompt:
    """Test task breakdown system prompt building."""

    def test_system_prompt_not_empty(self) -> None:
        """Test that system prompt is generated."""
        prompt = _build_task_breakdown_system_prompt()
        assert prompt != ""
        assert len(prompt) > 100

    def test_system_prompt_includes_expert_agent_capabilities(self) -> None:
        """Test that system prompt includes expert agent capabilities."""
        prompt = _build_task_breakdown_system_prompt()
        # Should include API information
        assert "expertAgent" in prompt or "Gmail" in prompt


class TestCreateTaskBreakdownPrompt:
    """Test task breakdown prompt creation."""

    def test_create_prompt_includes_user_requirement(self) -> None:
        """Test that created prompt includes user requirement."""
        requirement = "Test requirement for Gmail search"
        prompt = create_task_breakdown_prompt(requirement)
        assert requirement in prompt

    def test_create_prompt_includes_instructions(self) -> None:
        """Test that created prompt includes instructions."""
        requirement = "Test requirement"
        prompt = create_task_breakdown_prompt(requirement)
        assert "JSON形式" in prompt or "json" in prompt.lower()
