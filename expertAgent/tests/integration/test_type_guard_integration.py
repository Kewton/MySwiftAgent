"""Integration tests for Issue #338 Phase 5 - Type Guard Integration.

These tests verify that type guard functions work correctly when
integrated into the workflow generator nodes and prompt generation.

Issue #338: Type validation enhancement for recommended_apis.
"""

import pytest

from aiagent.langgraph.workflowGeneratorAgents.prompts.llm_evaluation import (
    create_llm_evaluation_prompt,
)
from aiagent.langgraph.workflowGeneratorAgents.prompts.test_data_regeneration import (
    create_test_data_regeneration_prompt,
)
from aiagent.langgraph.workflowGeneratorAgents.utils import (
    format_apis_comma_separated,
    normalize_recommended_apis,
)


@pytest.mark.integration
class TestTypeGuardPromptIntegration:
    """Integration tests for type guards with prompt generation."""

    def test_llm_evaluation_prompt_with_string_apis(self):
        """Test LLM evaluation prompt generation with list[str] APIs."""
        prompt = create_llm_evaluation_prompt(
            task_name="Test Task",
            task_description="Test description",
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
            },
            output_schema={
                "type": "object",
                "properties": {"result": {"type": "string"}},
            },
            recommended_apis=["google_search", "summarize_api"],
            yaml_content="version: 0.5\nnodes: {}",
            sample_input={"query": "test"},
            execution_result=None,
            rule_based_issues=[],
            is_regenerated_test_data=False,
            test_data_regeneration_count=0,
        )

        assert "google_search" in prompt
        assert "summarize_api" in prompt

    def test_llm_evaluation_prompt_with_dict_apis(self):
        """Test LLM evaluation prompt generation with list[dict] APIs."""
        prompt = create_llm_evaluation_prompt(
            task_name="Test Task",
            task_description="Test description",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            recommended_apis=[
                {"api_name": "gmail_api", "endpoint": "/v1/utility/gmail/send"},
                {"api_name": "drive_api", "endpoint": "/v1/utility/drive/upload"},
            ],
            yaml_content="version: 0.5\nnodes: {}",
            sample_input={"key": "value"},
            execution_result=None,
            rule_based_issues=[],
            is_regenerated_test_data=False,
            test_data_regeneration_count=0,
        )

        assert "gmail_api" in prompt
        assert "drive_api" in prompt

    def test_llm_evaluation_prompt_with_mixed_apis(self):
        """Test LLM evaluation prompt generation with mixed API types."""
        prompt = create_llm_evaluation_prompt(
            task_name="Mixed API Task",
            task_description="Task using mixed API formats",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            recommended_apis=[
                "google_search",  # string format
                {
                    "api_name": "summarize_api",
                    "endpoint": "/v1/ai/summarize",
                },  # dict format
                {"name": "legacy_api"},  # dict with 'name' key
            ],
            yaml_content="version: 0.5\nnodes: {}",
            sample_input={"query": "test"},
            execution_result=None,
            rule_based_issues=[],
            is_regenerated_test_data=False,
            test_data_regeneration_count=0,
        )

        assert "google_search" in prompt
        assert "summarize_api" in prompt
        assert "legacy_api" in prompt

    def test_test_data_regeneration_prompt_with_mixed_apis(self):
        """Test test data regeneration prompt with mixed API types."""
        prompt = create_test_data_regeneration_prompt(
            task_name="Test Task",
            task_description="Test description",
            input_schema={
                "type": "object",
                "properties": {"input": {"type": "string"}},
            },
            recommended_apis=[
                "api_string",
                {"api_name": "api_dict", "endpoint": "/v1/test"},
            ],
            previous_sample_input={"input": "old_value"},
            test_data_issues=["Low quality test data"],
            suggested_test_data=None,
        )

        assert "api_string" in prompt
        assert "api_dict" in prompt


@pytest.mark.integration
class TestTypeGuardNormalization:
    """Integration tests for API normalization."""

    def test_normalize_preserves_all_apis(self):
        """Test that normalization preserves all API information."""
        mixed_apis = [
            "string_api",
            {"api_name": "dict_api", "endpoint": "/v1/endpoint"},
            {"name": "legacy_api", "endpoint": "/v1/legacy"},
        ]

        normalized = normalize_recommended_apis(mixed_apis)

        assert len(normalized) == 3
        assert normalized[0]["api_name"] == "string_api"
        assert normalized[1]["api_name"] == "dict_api"
        assert normalized[1]["endpoint"] == "/v1/endpoint"
        assert normalized[2]["api_name"] == "legacy_api"

    def test_normalize_handles_empty_input(self):
        """Test that normalization handles empty inputs."""
        assert normalize_recommended_apis([]) == []
        assert normalize_recommended_apis(None) == []

    def test_format_apis_produces_valid_prompt_string(self):
        """Test that formatted APIs can be used in prompts."""
        mixed_apis = [
            "google_search",
            {"api_name": "gmail_api", "endpoint": "/v1/utility/gmail/send"},
        ]

        formatted = format_apis_comma_separated(mixed_apis)

        # Should be comma-separated and contain all API names
        assert "google_search" in formatted
        assert "gmail_api" in formatted
        assert ", " in formatted


@pytest.mark.integration
class TestTypeGuardRealWorldScenarios:
    """Integration tests with real-world API formats."""

    def test_workflow_generation_api_formats(self):
        """Test type guards with API formats from actual workflow generation."""
        # Format 1: Simple string (legacy)
        apis_v1 = ["fetchAgent", "jsonoutput API"]

        # Format 2: Dict with api_name (current standard)
        apis_v2 = [
            {"api_name": "Gmail検索", "endpoint": "/v1/utility/gmail/search"},
            {"api_name": "JSON Output Agent", "endpoint": "/v1/ai/jsonoutput"},
        ]

        # Format 3: Mixed (transition period)
        apis_v3 = [
            "google_search",
            {"api_name": "summarize", "endpoint": "/v1/ai/summarize"},
            {"name": "legacy_processor"},
        ]

        # All formats should work with type guards
        for apis in [apis_v1, apis_v2, apis_v3]:
            formatted = format_apis_comma_separated(apis)
            assert formatted != "None specified"
            assert len(formatted) > 0

    def test_task_breakdown_api_format(self):
        """Test type guards with API format from task breakdown output."""
        # This is the format produced by task breakdown node
        task_recommended_apis = [
            {
                "api_name": "Gmail検索",
                "endpoint": "/v1/utility/gmail/search",
                "reason": "メールの検索に必要",
            },
            {
                "api_name": "JSON Output Agent",
                "endpoint": "/v1/ai/jsonoutput",
                "reason": "構造化データ出力",
            },
        ]

        normalized = normalize_recommended_apis(task_recommended_apis)

        assert len(normalized) == 2
        assert normalized[0]["api_name"] == "Gmail検索"
        assert normalized[1]["api_name"] == "JSON Output Agent"

        formatted = format_apis_comma_separated(task_recommended_apis)
        assert "Gmail検索" in formatted
        assert "JSON Output Agent" in formatted
