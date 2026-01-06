"""Unit tests for type guard utilities.

Issue #338: Tests for type guard functions that handle mixed type inputs
(str | dict) for recommended_apis and similar fields.
"""

import pytest

from aiagent.langgraph.workflowGeneratorAgents.utils.type_guards import (
    format_apis_comma_separated,
    format_apis_for_prompt,
    get_api_endpoint,
    get_api_name,
    normalize_api_item,
    normalize_recommended_apis,
)


class TestNormalizeApiItem:
    """Tests for normalize_api_item function."""

    def test_normalize_string_input(self):
        """Test that string input is normalized to dict format."""
        result = normalize_api_item("google_search")
        assert result == {"api_name": "google_search", "endpoint": "google_search"}

    def test_normalize_dict_with_api_name(self):
        """Test dict input with api_name key."""
        result = normalize_api_item({"api_name": "test_api", "endpoint": "/v1/test"})
        assert result == {"api_name": "test_api", "endpoint": "/v1/test"}

    def test_normalize_dict_with_name_key(self):
        """Test dict input with 'name' key (fallback)."""
        result = normalize_api_item({"name": "legacy_api", "endpoint": "/v1/legacy"})
        assert result == {"api_name": "legacy_api", "endpoint": "/v1/legacy"}

    def test_normalize_dict_missing_endpoint(self):
        """Test dict input missing endpoint."""
        result = normalize_api_item({"api_name": "test_api"})
        assert result == {"api_name": "test_api", "endpoint": ""}

    def test_normalize_dict_missing_api_name(self):
        """Test dict input missing api_name."""
        result = normalize_api_item({"endpoint": "/v1/test"})
        assert result == {"api_name": "", "endpoint": "/v1/test"}

    def test_normalize_empty_dict(self):
        """Test empty dict input."""
        result = normalize_api_item({})
        assert result == {"api_name": "", "endpoint": ""}

    def test_normalize_invalid_type_raises_error(self):
        """Test that invalid type raises TypeError."""
        with pytest.raises(TypeError) as exc_info:
            normalize_api_item(123)  # type: ignore
        assert "Expected str or dict, got int" in str(exc_info.value)

    def test_normalize_none_raises_error(self):
        """Test that None raises TypeError."""
        with pytest.raises(TypeError) as exc_info:
            normalize_api_item(None)  # type: ignore
        assert "Expected str or dict, got NoneType" in str(exc_info.value)


class TestNormalizeRecommendedApis:
    """Tests for normalize_recommended_apis function."""

    def test_normalize_string_list(self):
        """Test list of strings is normalized."""
        result = normalize_recommended_apis(["api1", "api2", "api3"])
        expected = [
            {"api_name": "api1", "endpoint": "api1"},
            {"api_name": "api2", "endpoint": "api2"},
            {"api_name": "api3", "endpoint": "api3"},
        ]
        assert result == expected

    def test_normalize_dict_list(self):
        """Test list of dicts is normalized."""
        input_apis = [
            {"api_name": "api1", "endpoint": "/v1/api1"},
            {"api_name": "api2", "endpoint": "/v1/api2"},
        ]
        result = normalize_recommended_apis(input_apis)
        expected = [
            {"api_name": "api1", "endpoint": "/v1/api1"},
            {"api_name": "api2", "endpoint": "/v1/api2"},
        ]
        assert result == expected

    def test_normalize_mixed_list(self):
        """Test mixed list (str + dict) is normalized."""
        input_apis = [
            "string_api",
            {"api_name": "dict_api", "endpoint": "/v1/dict"},
        ]
        result = normalize_recommended_apis(input_apis)
        expected = [
            {"api_name": "string_api", "endpoint": "string_api"},
            {"api_name": "dict_api", "endpoint": "/v1/dict"},
        ]
        assert result == expected

    def test_normalize_empty_list(self):
        """Test empty list returns empty list."""
        result = normalize_recommended_apis([])
        assert result == []

    def test_normalize_none_returns_empty_list(self):
        """Test None input returns empty list."""
        result = normalize_recommended_apis(None)
        assert result == []


class TestGetApiName:
    """Tests for get_api_name function."""

    def test_get_name_from_string(self):
        """Test getting name from string input."""
        assert get_api_name("google_search") == "google_search"

    def test_get_name_from_dict_api_name(self):
        """Test getting name from dict with api_name."""
        assert get_api_name({"api_name": "test_api"}) == "test_api"

    def test_get_name_from_dict_name(self):
        """Test getting name from dict with name key."""
        assert get_api_name({"name": "legacy_api"}) == "legacy_api"

    def test_get_name_from_empty_dict(self):
        """Test getting name from empty dict."""
        assert get_api_name({}) == ""

    def test_get_name_from_invalid_type(self):
        """Test getting name from invalid type returns empty string."""
        assert get_api_name(123) == ""  # type: ignore


class TestGetApiEndpoint:
    """Tests for get_api_endpoint function."""

    def test_get_endpoint_from_string(self):
        """Test getting endpoint from string input."""
        assert get_api_endpoint("google_search") == "google_search"

    def test_get_endpoint_from_dict(self):
        """Test getting endpoint from dict."""
        assert get_api_endpoint({"endpoint": "/v1/test"}) == "/v1/test"

    def test_get_endpoint_from_dict_missing(self):
        """Test getting endpoint from dict without endpoint key."""
        assert get_api_endpoint({"api_name": "test"}) == ""

    def test_get_endpoint_from_invalid_type(self):
        """Test getting endpoint from invalid type returns empty string."""
        assert get_api_endpoint(123) == ""  # type: ignore


class TestFormatApisForPrompt:
    """Tests for format_apis_for_prompt function."""

    def test_format_string_apis(self):
        """Test formatting list of string APIs."""
        result = format_apis_for_prompt(["api1", "api2"])
        assert "- api1" in result
        assert "- api2" in result

    def test_format_dict_apis_with_different_name_and_endpoint(self):
        """Test formatting dict APIs with different name and endpoint."""
        result = format_apis_for_prompt([
            {"api_name": "search", "endpoint": "/v1/search"}
        ])
        assert "- search (endpoint: /v1/search)" in result

    def test_format_dict_apis_same_name_and_endpoint(self):
        """Test formatting dict APIs with same name and endpoint."""
        result = format_apis_for_prompt([
            {"api_name": "test", "endpoint": "test"}
        ])
        assert result == "- test"

    def test_format_empty_list(self):
        """Test formatting empty list."""
        result = format_apis_for_prompt([])
        assert result == "None specified"

    def test_format_none_input(self):
        """Test formatting None input."""
        result = format_apis_for_prompt(None)
        assert result == "None specified"

    def test_format_mixed_apis(self):
        """Test formatting mixed string and dict APIs."""
        input_apis = [
            "string_api",
            {"api_name": "dict_api", "endpoint": "/v1/dict"},
        ]
        result = format_apis_for_prompt(input_apis)
        assert "- string_api" in result
        assert "- dict_api (endpoint: /v1/dict)" in result

    def test_format_dict_with_only_endpoint(self):
        """Test formatting dict with only endpoint."""
        result = format_apis_for_prompt([{"endpoint": "/v1/only"}])
        assert "- /v1/only" in result

    def test_format_empty_dict(self):
        """Test formatting empty dict results in no line."""
        result = format_apis_for_prompt([{}])
        assert result == "None specified"


class TestFormatApisCommaSeparated:
    """Tests for format_apis_comma_separated function."""

    def test_format_string_apis(self):
        """Test formatting list of string APIs."""
        result = format_apis_comma_separated(["api1", "api2", "api3"])
        assert result == "api1, api2, api3"

    def test_format_dict_apis(self):
        """Test formatting list of dict APIs."""
        result = format_apis_comma_separated([
            {"api_name": "search", "endpoint": "/v1/search"},
            {"api_name": "summarize", "endpoint": "/v1/summarize"},
        ])
        assert result == "search, summarize"

    def test_format_mixed_apis(self):
        """Test formatting mixed string and dict APIs."""
        result = format_apis_comma_separated([
            "string_api",
            {"api_name": "dict_api"},
        ])
        assert result == "string_api, dict_api"

    def test_format_empty_list(self):
        """Test formatting empty list."""
        result = format_apis_comma_separated([])
        assert result == "None specified"

    def test_format_none_input(self):
        """Test formatting None input."""
        result = format_apis_comma_separated(None)
        assert result == "None specified"

    def test_format_dict_with_name_key(self):
        """Test formatting dict with 'name' key (fallback)."""
        result = format_apis_comma_separated([{"name": "legacy_api"}])
        assert result == "legacy_api"


class TestIssue338Integration:
    """Integration tests for Issue #338 type guard scenarios."""

    def test_real_world_mixed_apis(self):
        """Test real-world scenario with mixed API types from LLM output."""
        # This simulates what might come from LLM-generated task data
        recommended_apis = [
            "google_search",
            {"api_name": "summarize_api", "endpoint": "/v1/summarize"},
            "translate_api",
            {"name": "legacy_api"},  # Using 'name' instead of 'api_name'
        ]

        normalized = normalize_recommended_apis(recommended_apis)

        assert len(normalized) == 4
        assert normalized[0]["api_name"] == "google_search"
        assert normalized[1]["api_name"] == "summarize_api"
        assert normalized[1]["endpoint"] == "/v1/summarize"
        assert normalized[2]["api_name"] == "translate_api"
        assert normalized[3]["api_name"] == "legacy_api"

    def test_safe_iteration_over_mixed_apis(self):
        """Test that normalized APIs can be safely iterated with .get() calls."""
        mixed_apis = ["api1", {"api_name": "api2", "endpoint": "/v1/api2"}]
        normalized = normalize_recommended_apis(mixed_apis)

        # This should not raise any errors
        for api in normalized:
            name = api.get("api_name", "")
            endpoint = api.get("endpoint", "")
            assert isinstance(name, str)
            assert isinstance(endpoint, str)

    def test_prompt_formatting_for_llm(self):
        """Test that formatted output is suitable for LLM prompts."""
        apis = [
            "google_search",
            {"api_name": "weather_api", "endpoint": "https://api.weather.com/v1"},
        ]

        formatted = format_apis_for_prompt(apis)

        # Should be human-readable for LLM
        assert "google_search" in formatted
        assert "weather_api" in formatted
        assert "https://api.weather.com/v1" in formatted
