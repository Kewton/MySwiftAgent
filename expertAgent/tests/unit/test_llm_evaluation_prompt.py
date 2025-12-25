"""Tests for LLM evaluation prompt generation.

This module tests the create_llm_evaluation_prompt function,
specifically focusing on handling different data formats for recommended_apis.

Issue #305: These tests were added after discovering a TypeError
when recommended_apis was passed as list[dict] instead of list[str].
"""


from aiagent.langgraph.workflowGeneratorAgents.prompts.llm_evaluation import (
    _format_recommended_apis,
    create_llm_evaluation_prompt,
)


class TestFormatRecommendedApis:
    """Tests for _format_recommended_apis helper function."""

    def test_format_with_string_list(self) -> None:
        """Test formatting with list[str] input."""
        result = _format_recommended_apis(["api1", "api2", "api3"])
        assert result == "api1, api2, api3"

    def test_format_with_dict_list(self) -> None:
        """Test formatting with list[dict] input - actual data format from TaskMaster."""
        result = _format_recommended_apis([
            {"name": "gmail_api", "endpoint": "/api/v1/gmail"},
            {"name": "drive_api", "endpoint": "/api/v1/drive"},
        ])
        assert result == "gmail_api, drive_api"

    def test_format_with_dict_list_using_api_name_key(self) -> None:
        """Test formatting with dict using 'api_name' key instead of 'name'."""
        result = _format_recommended_apis([
            {"api_name": "search_api"},
            {"api_name": "calendar_api"},
        ])
        assert result == "search_api, calendar_api"

    def test_format_with_mixed_list(self) -> None:
        """Test formatting with mixed list of str and dict."""
        result = _format_recommended_apis([
            "string_api",
            {"name": "dict_api"},
            123,  # Non-standard type
        ])
        assert "string_api" in result
        assert "dict_api" in result
        assert "123" in result

    def test_format_with_empty_list(self) -> None:
        """Test formatting with empty list."""
        result = _format_recommended_apis([])
        assert result == "None specified"

    def test_format_with_none(self) -> None:
        """Test formatting with None input."""
        result = _format_recommended_apis(None)
        assert result == "None specified"

    def test_format_with_dict_without_name_key(self) -> None:
        """Test formatting with dict that doesn't have 'name' or 'api_name' key."""
        result = _format_recommended_apis([
            {"endpoint": "/api/v1/test", "method": "GET"},
        ])
        # Should fallback to str(dict)
        assert "endpoint" in result or "{" in result


class TestCreateLLMEvaluationPrompt:
    """Tests for create_llm_evaluation_prompt function."""

    def test_create_prompt_with_string_recommended_apis(self) -> None:
        """Test prompt creation with list[str] recommended_apis."""
        prompt = create_llm_evaluation_prompt(
            task_name="Test Task",
            task_description="A test task",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            recommended_apis=["api1", "api2"],
            yaml_content="version: 0.5",
            sample_input={"key": "value"},
            execution_result=None,
            rule_based_issues=[],
        )

        assert "Test Task" in prompt
        assert "api1, api2" in prompt

    def test_create_prompt_with_dict_recommended_apis(self) -> None:
        """Test prompt creation with list[dict] recommended_apis.

        This is the actual data format that caused TypeError before the fix.
        """
        prompt = create_llm_evaluation_prompt(
            task_name="メール送信タスク",
            task_description="Gmailを使用してメールを送信する",
            input_schema={
                "type": "object",
                "properties": {
                    "recipient": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
            },
            output_schema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string"},
                    "status": {"type": "string"},
                },
            },
            recommended_apis=[
                {"name": "gmail_api", "endpoint": "/api/v1/gmail/send"},
                {"name": "oauth_api", "endpoint": "/api/v1/oauth/token"},
            ],
            yaml_content="version: 0.5\nnodes:\n  send_email:\n    agent: fetchAgent",
            sample_input={
                "recipient": "test@example.com",
                "subject": "テスト",
                "body": "本文",
            },
            execution_result={"status": "success"},
            rule_based_issues=[],
        )

        # Should not raise TypeError
        assert "gmail_api" in prompt
        assert "oauth_api" in prompt
        assert "メール送信タスク" in prompt

    def test_create_prompt_with_mixed_recommended_apis(self) -> None:
        """Test prompt creation with mixed format recommended_apis."""
        prompt = create_llm_evaluation_prompt(
            task_name="Mixed Task",
            task_description="Task with mixed API formats",
            input_schema={},
            output_schema={},
            recommended_apis=[
                "string_api",
                {"name": "dict_api"},
                {"api_name": "another_api"},
            ],
            yaml_content="version: 0.5",
            sample_input={},
            execution_result=None,
            rule_based_issues=[],
        )

        assert "string_api" in prompt
        assert "dict_api" in prompt
        assert "another_api" in prompt

    def test_create_prompt_with_empty_recommended_apis(self) -> None:
        """Test prompt creation with empty recommended_apis."""
        prompt = create_llm_evaluation_prompt(
            task_name="Task without APIs",
            task_description="No APIs recommended",
            input_schema={},
            output_schema={},
            recommended_apis=[],
            yaml_content="version: 0.5",
            sample_input={},
            execution_result=None,
            rule_based_issues=[],
        )

        assert "None specified" in prompt

    def test_create_prompt_with_rule_based_issues(self) -> None:
        """Test prompt includes rule-based validation issues."""
        prompt = create_llm_evaluation_prompt(
            task_name="Task with Issues",
            task_description="Task that has validation issues",
            input_schema={},
            output_schema={},
            recommended_apis=["api1"],
            yaml_content="invalid yaml",
            sample_input={},
            execution_result=None,
            rule_based_issues=[
                {"category": "yaml", "message": "YAML syntax error"},
                {"category": "http", "message": "HTTP 500 error"},
            ],
        )

        assert "[yaml] YAML syntax error" in prompt
        assert "[http] HTTP 500 error" in prompt

    def test_create_prompt_with_regenerated_test_data(self) -> None:
        """Test prompt indicates when test data was regenerated."""
        prompt = create_llm_evaluation_prompt(
            task_name="Regenerated Data Task",
            task_description="Task with regenerated test data",
            input_schema={},
            output_schema={},
            recommended_apis=[],
            yaml_content="version: 0.5",
            sample_input={"regenerated": True},
            execution_result=None,
            rule_based_issues=[],
            is_regenerated_test_data=True,
            test_data_regeneration_count=2,
        )

        assert "LLM regeneration" in prompt
        assert "2" in prompt  # regeneration count


class TestCreateLLMEvaluationPromptEdgeCases:
    """Edge case tests for create_llm_evaluation_prompt."""

    def test_create_prompt_with_string_sample_input(self) -> None:
        """Test prompt creation with string sample_input instead of dict."""
        prompt = create_llm_evaluation_prompt(
            task_name="String Input Task",
            task_description="Task with string input",
            input_schema={},
            output_schema={},
            recommended_apis=[],
            yaml_content="version: 0.5",
            sample_input="raw string input",
            execution_result=None,
            rule_based_issues=[],
        )

        assert "raw string input" in prompt

    def test_create_prompt_with_complex_nested_data(self) -> None:
        """Test prompt creation with complex nested data structures."""
        prompt = create_llm_evaluation_prompt(
            task_name="Complex Task",
            task_description="Task with nested data",
            input_schema={
                "type": "object",
                "properties": {
                    "nested": {
                        "type": "object",
                        "properties": {
                            "deep": {"type": "string"},
                        },
                    },
                },
            },
            output_schema={},
            recommended_apis=[
                {
                    "name": "complex_api",
                    "nested": {"config": {"key": "value"}},
                },
            ],
            yaml_content="version: 0.5",
            sample_input={"nested": {"deep": "value"}},
            execution_result={"result": {"nested": {"data": [1, 2, 3]}}},
            rule_based_issues=[],
        )

        assert "complex_api" in prompt
        assert "nested" in prompt
