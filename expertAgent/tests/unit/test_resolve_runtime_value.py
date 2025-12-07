"""Unit tests for resolve_runtime_value with type conversion support.

Issue #251: resolve_runtime_value 型変換対応
"""

from unittest.mock import patch

import pytest


class TestConvertRuntimeType:
    """Tests for _convert_runtime_type helper function."""

    def test_convert_to_str(self):
        """String conversion returns original value."""
        from core.secrets import _convert_runtime_type

        result = _convert_runtime_type("hello", str)
        assert result == "hello"
        assert isinstance(result, str)

    def test_convert_to_int_valid(self):
        """Integer conversion for valid numeric string."""
        from core.secrets import _convert_runtime_type

        result = _convert_runtime_type("6379", int)
        assert result == 6379
        assert isinstance(result, int)

    def test_convert_to_int_invalid(self):
        """Integer conversion raises ValueError for invalid input."""
        from core.secrets import _convert_runtime_type

        with pytest.raises(ValueError) as exc_info:
            _convert_runtime_type("not_a_number", int)

        assert "Failed to convert" in str(exc_info.value)
        assert "not_a_number" in str(exc_info.value)

    def test_convert_to_bool_true_values(self):
        """Boolean conversion for true values."""
        from core.secrets import _convert_runtime_type

        true_values = ["true", "True", "TRUE", "1", "yes", "Yes", "on", "ON"]
        for value in true_values:
            result = _convert_runtime_type(value, bool)
            assert result is True, f"Expected True for '{value}'"
            assert isinstance(result, bool)

    def test_convert_to_bool_false_values(self):
        """Boolean conversion for false values."""
        from core.secrets import _convert_runtime_type

        false_values = ["false", "False", "0", "no", "off", "anything_else"]
        for value in false_values:
            result = _convert_runtime_type(value, bool)
            assert result is False, f"Expected False for '{value}'"
            assert isinstance(result, bool)

    def test_convert_unsupported_type(self):
        """Unsupported type raises ValueError."""
        from core.secrets import _convert_runtime_type

        with pytest.raises(ValueError) as exc_info:
            _convert_runtime_type("value", list)

        assert "Unsupported type" in str(exc_info.value)


class TestResolveRuntimeValueTypeConversion:
    """Tests for resolve_runtime_value with value_type parameter."""

    def test_default_returns_string(self):
        """Default value_type returns string (backward compatibility)."""
        from core.secrets import resolve_runtime_value

        with patch("core.secrets.secrets_manager") as mock_manager:
            mock_manager.get_secret.return_value = "6379"

            result = resolve_runtime_value("VALKEY_PORT")

            assert result == "6379"
            assert isinstance(result, str)

    def test_value_type_int_from_myvault(self):
        """Integer conversion for MyVault values."""
        from core.secrets import resolve_runtime_value

        with patch("core.secrets.secrets_manager") as mock_manager:
            mock_manager.get_secret.return_value = "6379"

            result = resolve_runtime_value("VALKEY_PORT", value_type=int)

            assert result == 6379
            assert isinstance(result, int)

    def test_value_type_bool_from_myvault(self):
        """Boolean conversion for MyVault values."""
        from core.secrets import resolve_runtime_value

        with patch("core.secrets.secrets_manager") as mock_manager:
            mock_manager.get_secret.return_value = "true"

            result = resolve_runtime_value("FEATURE_ENABLED", value_type=bool)

            assert result is True
            assert isinstance(result, bool)

    def test_value_type_int_from_env_fallback(self):
        """Integer conversion for environment variable fallback."""
        from core.secrets import resolve_runtime_value

        with patch("core.secrets.secrets_manager") as mock_manager:
            mock_manager.get_secret.side_effect = ValueError("not found")

            with patch("core.secrets.settings") as mock_settings:
                mock_settings.VALKEY_PORT = 8080

                result = resolve_runtime_value("VALKEY_PORT", value_type=int)

                assert result == 8080
                assert isinstance(result, int)

    def test_settings_only_key_with_type_conversion(self):
        """Settings-only keys support type conversion."""
        from core.secrets import resolve_runtime_value

        with patch("core.secrets.settings") as mock_settings:
            mock_settings.MYVAULT_ENABLED = True

            result = resolve_runtime_value("MYVAULT_ENABLED", value_type=bool)

            assert result is True
            assert isinstance(result, bool)

    def test_backward_compatibility_no_value_type(self):
        """Existing calls without value_type continue to work."""
        from core.secrets import resolve_runtime_value

        with patch("core.secrets.secrets_manager") as mock_manager:
            mock_manager.get_secret.return_value = "test_value"

            # Call without value_type (existing pattern)
            result = resolve_runtime_value("API_KEY", project="test_project")

            assert result == "test_value"
            mock_manager.get_secret.assert_called_once_with(
                "API_KEY", project="test_project"
            )

    def test_default_value_returned_when_not_found(self):
        """Default value is returned when key not found."""
        from core.secrets import resolve_runtime_value

        with patch("core.secrets.secrets_manager") as mock_manager:
            mock_manager.get_secret.side_effect = ValueError("not found")

            with patch("core.secrets.settings") as mock_settings:
                # Simulate attribute not found
                del mock_settings.UNKNOWN_KEY

                result = resolve_runtime_value(
                    "UNKNOWN_KEY", default=42, value_type=int
                )

                assert result == 42

    def test_int_conversion_error_propagates(self):
        """Type conversion errors are propagated."""
        from core.secrets import resolve_runtime_value

        with patch("core.secrets.secrets_manager") as mock_manager:
            mock_manager.get_secret.return_value = "not_a_number"

            with pytest.raises(ValueError) as exc_info:
                resolve_runtime_value("PORT", value_type=int)

            assert "Failed to convert" in str(exc_info.value)

    def test_settings_only_key_returns_default_when_none(self):
        """Settings-only key returns default when setting value is None."""
        from core.secrets import resolve_runtime_value

        with patch("core.secrets.settings") as mock_settings:
            mock_settings.LOG_LEVEL = None

            result = resolve_runtime_value("LOG_LEVEL", default="INFO")

            assert result == "INFO"

    def test_unsupported_type_error_propagates(self):
        """Unsupported type errors are propagated."""
        from core.secrets import resolve_runtime_value

        with patch("core.secrets.secrets_manager") as mock_manager:
            mock_manager.get_secret.return_value = "value"

            with pytest.raises(ValueError) as exc_info:
                resolve_runtime_value("KEY", value_type=list)

            assert "Unsupported type" in str(exc_info.value)
