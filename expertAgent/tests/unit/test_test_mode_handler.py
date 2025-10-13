"""Unit tests for test_mode_handler module."""

import pytest

from app.schemas.standardAiAgent import ExpertAiAgentResponse
from core.test_mode_handler import handle_test_mode


class TestHandleTestMode:
    """Tests for handle_test_mode function."""

    def test_normal_mode_returns_none(self):
        """Normal mode: test_mode=False should return None."""
        result = handle_test_mode(False, None, "test_endpoint")
        assert result is None

    def test_test_mode_with_dict_response(self):
        """Test mode: dict test_response should be returned as-is."""
        test_data = {"result": "test data", "custom_field": "custom value"}
        result = handle_test_mode(True, test_data, "test_endpoint")
        assert result == test_data
        assert isinstance(result, dict)

    def test_test_mode_with_string_response(self):
        """Test mode: string test_response should be wrapped in ExpertAiAgentResponse."""
        test_string = "This is a test response"
        result = handle_test_mode(True, test_string, "mylllm")
        assert isinstance(result, ExpertAiAgentResponse)
        assert result.result == test_string
        assert result.text == test_string
        assert result.type == "mylllm_test"

    def test_test_mode_without_response(self):
        """Test mode: no test_response should return default message."""
        result = handle_test_mode(True, None, "test_endpoint")
        assert isinstance(result, ExpertAiAgentResponse)
        assert "Test mode" in result.result
        assert "no test_response provided" in result.result
        assert result.type == "test_endpoint_test"

    def test_test_mode_with_complex_dict(self):
        """Test mode: complex nested dict should be returned as-is."""
        test_data = {
            "result": {
                "outline": [
                    {"title": "Chapter 1", "overview": "Overview 1"},
                    {"title": "Chapter 2", "overview": "Overview 2"},
                ]
            }
        }
        result = handle_test_mode(True, test_data, "jsonoutput")
        assert result == test_data
        assert result["result"]["outline"][0]["title"] == "Chapter 1"

    def test_normal_mode_ignores_test_response(self):
        """Normal mode: test_response should be ignored when test_mode=False."""
        test_data = {"result": "ignored"}
        result = handle_test_mode(False, test_data, "test_endpoint")
        assert result is None

    def test_endpoint_name_in_type(self):
        """Test mode: endpoint name should be included in response type."""
        result = handle_test_mode(True, "test", "explorer")
        assert isinstance(result, ExpertAiAgentResponse)
        assert result.type == "explorer_test"

    def test_empty_dict_response(self):
        """Test mode: empty dict should be returned as-is."""
        test_data = {}
        result = handle_test_mode(True, test_data, "test_endpoint")
        assert result == test_data
        assert isinstance(result, dict)

    def test_empty_string_response(self):
        """Test mode: empty string should be wrapped in ExpertAiAgentResponse."""
        result = handle_test_mode(True, "", "test_endpoint")
        assert isinstance(result, ExpertAiAgentResponse)
        assert result.result == ""
        assert result.text == ""
