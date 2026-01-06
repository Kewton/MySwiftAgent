"""Unit tests for Test Data Regeneration prompts.

This module tests the prompt generation functions for test data regeneration.

Issue #305: Added tests for handling both list[str] and list[dict] formats
for recommended_apis parameter.

Issue #338: Updated to use centralized type guard functions.
"""

from aiagent.langgraph.workflowGeneratorAgents.prompts.test_data_regeneration import (
    TEST_DATA_REGENERATION_SYSTEM_PROMPT,
    create_test_data_regeneration_prompt,
)
from aiagent.langgraph.workflowGeneratorAgents.utils.type_guards import (
    format_apis_comma_separated as _format_recommended_apis,
)


class TestFormatRecommendedApis:
    """Test _format_recommended_apis helper function.

    Issue #305: Tests for handling both list[str] and list[dict] formats.
    """

    def test_format_with_string_list(self):
        """Test formatting with list[str] input."""
        result = _format_recommended_apis(["api1", "api2", "api3"])
        assert result == "api1, api2, api3"

    def test_format_with_dict_list_name_key(self):
        """Test formatting with list[dict] using 'name' key."""
        result = _format_recommended_apis(
            [
                {"name": "gmail_api", "endpoint": "/api/v1/gmail"},
                {"name": "drive_api", "endpoint": "/api/v1/drive"},
            ]
        )
        assert result == "gmail_api, drive_api"

    def test_format_with_dict_list_api_name_key(self):
        """Test formatting with list[dict] using 'api_name' key."""
        result = _format_recommended_apis(
            [
                {"api_name": "search_api"},
                {"api_name": "calendar_api"},
            ]
        )
        assert result == "search_api, calendar_api"

    def test_format_with_empty_list(self):
        """Test formatting with empty list."""
        result = _format_recommended_apis([])
        assert result == "None specified"

    def test_format_with_none(self):
        """Test formatting with None input."""
        result = _format_recommended_apis(None)
        assert result == "None specified"

    def test_format_with_mixed_list(self):
        """Test formatting with mixed list of str and dict."""
        result = _format_recommended_apis(
            [
                "string_api",
                {"name": "dict_api"},
                {"api_name": "another_api"},
            ]
        )
        assert "string_api" in result
        assert "dict_api" in result
        assert "another_api" in result


class TestTestDataRegenerationSystemPrompt:
    """Test the system prompt constant."""

    def test_system_prompt_contains_guidelines(self):
        """Test that system prompt contains required guidelines."""
        assert "Realism" in TEST_DATA_REGENERATION_SYSTEM_PROMPT
        assert "Schema Compliance" in TEST_DATA_REGENERATION_SYSTEM_PROMPT
        assert "API Compatibility" in TEST_DATA_REGENERATION_SYSTEM_PROMPT
        assert "Test Effectiveness" in TEST_DATA_REGENERATION_SYSTEM_PROMPT

    def test_system_prompt_contains_output_format(self):
        """Test that system prompt specifies output format."""
        assert "sample_input" in TEST_DATA_REGENERATION_SYSTEM_PROMPT
        assert "generation_rationale" in TEST_DATA_REGENERATION_SYSTEM_PROMPT
        assert "expected_behavior" in TEST_DATA_REGENERATION_SYSTEM_PROMPT


class TestCreateTestDataRegenerationPrompt:
    """Test create_test_data_regeneration_prompt function."""

    def test_prompt_with_all_parameters(self):
        """Test prompt generation with all parameters provided."""
        prompt = create_test_data_regeneration_prompt(
            task_name="Get company info",
            task_description="Retrieve company information from database",
            input_schema={
                "type": "object",
                "properties": {"company_name": {"type": "string"}},
                "required": ["company_name"],
            },
            recommended_apis=["company_api", "search_api"],
            previous_sample_input={"company_name": "sample_text"},
            test_data_issues=[
                "Placeholder value used",
                "Not a realistic company name",
            ],
            suggested_test_data={"company_name": "Toyota Motor Corporation"},
        )

        assert "Get company info" in prompt
        assert "Retrieve company information from database" in prompt
        assert "company_api" in prompt
        assert "search_api" in prompt
        assert "sample_text" in prompt
        assert "Placeholder value used" in prompt
        assert "Not a realistic company name" in prompt
        assert "Toyota Motor Corporation" in prompt

    def test_prompt_with_empty_issues_list(self):
        """Test prompt generation when no issues are provided (covers line 69)."""
        prompt = create_test_data_regeneration_prompt(
            task_name="Test task",
            task_description="Test description",
            input_schema={"type": "object"},
            recommended_apis=[],
            previous_sample_input={"key": "value"},
            test_data_issues=[],  # Empty list
            suggested_test_data=None,
        )

        # Should contain the fallback text
        assert "No specific issues listed" in prompt

    def test_prompt_with_no_suggested_data(self):
        """Test prompt generation when no suggested data is provided."""
        prompt = create_test_data_regeneration_prompt(
            task_name="Test task",
            task_description="Test description",
            input_schema={"type": "object"},
            recommended_apis=[],
            previous_sample_input={"key": "value"},
            test_data_issues=["Some issue"],
            suggested_test_data=None,
        )

        assert "None" in prompt

    def test_prompt_with_no_recommended_apis(self):
        """Test prompt generation when no APIs are recommended."""
        prompt = create_test_data_regeneration_prompt(
            task_name="Test task",
            task_description="Test description",
            input_schema={"type": "object"},
            recommended_apis=[],
            previous_sample_input={"key": "value"},
            test_data_issues=["Issue"],
            suggested_test_data=None,
        )

        assert "None specified" in prompt

    def test_prompt_with_dict_recommended_apis(self):
        """Test prompt generation with list[dict] recommended_apis.

        Issue #305: This is the actual data format from TaskMaster that caused
        TypeError before the fix.
        """
        prompt = create_test_data_regeneration_prompt(
            task_name="Email send task",
            task_description="Send email via Gmail API",
            input_schema={
                "type": "object",
                "properties": {
                    "recipient": {"type": "string"},
                    "subject": {"type": "string"},
                },
            },
            recommended_apis=[
                {"name": "gmail_api", "endpoint": "/api/v1/gmail/send"},
                {"api_name": "oauth_api", "endpoint": "/api/v1/oauth/token"},
            ],
            previous_sample_input={"recipient": "test@example.com"},
            test_data_issues=["Missing subject field"],
            suggested_test_data=None,
        )

        # Should not raise TypeError and should contain API names
        assert "gmail_api" in prompt
        assert "oauth_api" in prompt
        assert "Email send task" in prompt

    def test_prompt_with_string_sample_input(self):
        """Test prompt generation with string sample input instead of dict."""
        prompt = create_test_data_regeneration_prompt(
            task_name="Test task",
            task_description="Test description",
            input_schema={"type": "object"},
            recommended_apis=["api1"],
            previous_sample_input="just a plain string",
            test_data_issues=["Invalid format"],
            suggested_test_data=None,
        )

        # String input should be included directly
        assert "just a plain string" in prompt

    def test_prompt_with_complex_schema(self):
        """Test prompt generation with complex nested schema."""
        complex_schema = {
            "type": "object",
            "properties": {
                "user": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "age": {"type": "integer"},
                    },
                },
                "items": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["user"],
        }

        prompt = create_test_data_regeneration_prompt(
            task_name="Complex task",
            task_description="Complex description",
            input_schema=complex_schema,
            recommended_apis=[],
            previous_sample_input={"user": {"name": "test"}},
            test_data_issues=["Missing age field"],
            suggested_test_data={"user": {"name": "John", "age": 30}},
        )

        assert "user" in prompt
        assert "name" in prompt
        assert "age" in prompt

    def test_prompt_with_unicode_content(self):
        """Test prompt generation with unicode characters."""
        prompt = create_test_data_regeneration_prompt(
            task_name="Company info",
            task_description="Retrieve information",
            input_schema={"type": "object"},
            recommended_apis=[],
            previous_sample_input={"company_name": "Toyota Motor Corporation"},
            test_data_issues=["Unicode issue"],
            suggested_test_data={"company_name": "Toyota Motor Corporation"},
        )

        assert "Toyota Motor Corporation" in prompt

    def test_prompt_with_empty_dict_sample_input(self):
        """Test prompt generation with empty dict sample input."""
        prompt = create_test_data_regeneration_prompt(
            task_name="Test task",
            task_description="Test description",
            input_schema={"type": "object"},
            recommended_apis=[],
            previous_sample_input={},
            test_data_issues=["Empty input"],
            suggested_test_data=None,
        )

        # Empty dict should be represented as {}
        assert "{}" in prompt

    def test_prompt_structure(self):
        """Test that prompt has expected structure with all sections."""
        prompt = create_test_data_regeneration_prompt(
            task_name="Test",
            task_description="Description",
            input_schema={},
            recommended_apis=[],
            previous_sample_input={},
            test_data_issues=[],
            suggested_test_data=None,
        )

        # Check for all section headers
        assert "## Task Information" in prompt
        assert "## Input Schema" in prompt
        assert "## Previous Test Data (Has Issues)" in prompt
        assert "## Issues with Previous Test Data" in prompt
        assert "## LLM Suggestion (Reference)" in prompt
        assert "Based on the above, please generate appropriate test data" in prompt
