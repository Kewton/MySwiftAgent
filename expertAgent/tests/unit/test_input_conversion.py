"""Unit tests for input conversion utilities.

This module tests the convert_sample_input_to_dict_or_str utility function
which handles various input types for LLM prompt generation.
"""

from aiagent.langgraph.workflowGeneratorAgents.utils.input_conversion import (
    convert_sample_input_to_dict_or_str,
)


class TestConvertSampleInputToDictOrStr:
    """Test convert_sample_input_to_dict_or_str function."""

    def test_none_input_returns_empty_dict(self):
        """Test that None input returns an empty dictionary."""
        result = convert_sample_input_to_dict_or_str(None)
        assert result == {}
        assert isinstance(result, dict)

    def test_dict_input_returns_same_dict(self):
        """Test that dict input is returned as-is."""
        input_data = {"key": "value", "nested": {"inner": 123}}
        result = convert_sample_input_to_dict_or_str(input_data)
        assert result == input_data
        assert isinstance(result, dict)

    def test_empty_dict_returns_empty_dict(self):
        """Test that empty dict input returns empty dict."""
        result = convert_sample_input_to_dict_or_str({})
        assert result == {}
        assert isinstance(result, dict)

    def test_string_input_returns_same_string(self):
        """Test that string input returns the same string."""
        input_data = "test string value"
        result = convert_sample_input_to_dict_or_str(input_data)
        assert result == "test string value"
        assert isinstance(result, str)

    def test_empty_string_returns_empty_string(self):
        """Test that empty string input returns empty string."""
        result = convert_sample_input_to_dict_or_str("")
        assert result == ""
        assert isinstance(result, str)

    def test_int_input_returns_string(self):
        """Test that integer input is converted to string."""
        result = convert_sample_input_to_dict_or_str(42)
        assert result == "42"
        assert isinstance(result, str)

    def test_zero_int_returns_string(self):
        """Test that zero integer is converted to string."""
        result = convert_sample_input_to_dict_or_str(0)
        assert result == "0"
        assert isinstance(result, str)

    def test_negative_int_returns_string(self):
        """Test that negative integer is converted to string."""
        result = convert_sample_input_to_dict_or_str(-123)
        assert result == "-123"
        assert isinstance(result, str)

    def test_float_input_returns_string(self):
        """Test that float input is converted to string."""
        result = convert_sample_input_to_dict_or_str(3.14159)
        assert result == "3.14159"
        assert isinstance(result, str)

    def test_zero_float_returns_string(self):
        """Test that zero float is converted to string."""
        result = convert_sample_input_to_dict_or_str(0.0)
        assert result == "0.0"
        assert isinstance(result, str)

    def test_bool_true_returns_string(self):
        """Test that True boolean is converted to string."""
        result = convert_sample_input_to_dict_or_str(True)
        assert result == "True"
        assert isinstance(result, str)

    def test_bool_false_returns_string(self):
        """Test that False boolean is converted to string."""
        result = convert_sample_input_to_dict_or_str(False)
        assert result == "False"
        assert isinstance(result, str)

    def test_list_input_returns_string(self):
        """Test that list input is converted to string representation."""
        input_data = [1, 2, 3, "four"]
        result = convert_sample_input_to_dict_or_str(input_data)
        assert result == "[1, 2, 3, 'four']"
        assert isinstance(result, str)

    def test_empty_list_returns_string(self):
        """Test that empty list is converted to string."""
        result = convert_sample_input_to_dict_or_str([])
        assert result == "[]"
        assert isinstance(result, str)

    def test_nested_list_returns_string(self):
        """Test that nested list is converted to string."""
        input_data = [[1, 2], [3, 4]]
        result = convert_sample_input_to_dict_or_str(input_data)
        assert result == "[[1, 2], [3, 4]]"
        assert isinstance(result, str)

    def test_complex_dict_preserved(self):
        """Test that complex dict with various value types is preserved."""
        input_data = {
            "string": "value",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "list": [1, 2, 3],
            "nested": {"key": "value"},
            "null": None,
        }
        result = convert_sample_input_to_dict_or_str(input_data)
        assert result == input_data
        assert isinstance(result, dict)


class TestConvertSampleInputEdgeCases:
    """Test edge cases for convert_sample_input_to_dict_or_str."""

    def test_unicode_string(self):
        """Test that unicode strings are handled correctly."""
        input_data = "Hello"
        result = convert_sample_input_to_dict_or_str(input_data)
        assert result == "Hello"
        assert isinstance(result, str)

    def test_dict_with_unicode_keys(self):
        """Test that dicts with unicode keys are preserved."""
        input_data = {"key": "value"}
        result = convert_sample_input_to_dict_or_str(input_data)
        assert result == input_data
        assert isinstance(result, dict)

    def test_large_int(self):
        """Test that large integers are converted correctly."""
        large_int = 12345678901234567890
        result = convert_sample_input_to_dict_or_str(large_int)
        assert result == str(large_int)
        assert isinstance(result, str)

    def test_scientific_notation_float(self):
        """Test that scientific notation floats are handled."""
        result = convert_sample_input_to_dict_or_str(1e10)
        assert "10000000000" in result or "1e+10" in result.lower() or "1e10" in result.lower()
        assert isinstance(result, str)
