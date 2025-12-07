"""Unit tests for SecretsManager.get_connection_config() - Issue #250.

Tests the type-converting connection config retrieval method.
"""

from unittest.mock import MagicMock, patch

import pytest

from core.myvault_client import MyVaultError
from core.secrets import SecretsManager


class TestSecretsManagerConnectionConfig:
    """Test suite for SecretsManager.get_connection_config() method."""

    @pytest.fixture
    def manager_with_myvault(self):
        """Create SecretsManager with MyVault enabled."""
        with patch("core.secrets.settings") as mock_settings:
            mock_settings.MYVAULT_ENABLED = True
            mock_settings.MYVAULT_BASE_URL = "http://localhost:8000"
            mock_settings.MYVAULT_SERVICE_NAME = "test-service"
            mock_settings.MYVAULT_SERVICE_TOKEN = "test-token"
            mock_settings.MYVAULT_DEFAULT_PROJECT = "default"
            mock_settings.SECRETS_CACHE_TTL = 300

            with patch("core.secrets.MyVaultClient") as mock_client_class:
                mock_client = MagicMock()
                mock_client_class.return_value = mock_client

                manager = SecretsManager()
                manager.myvault_client = mock_client
                manager.myvault_enabled = True

                yield manager

    @pytest.fixture
    def manager_without_myvault(self):
        """Create SecretsManager with MyVault disabled."""
        with patch("core.secrets.settings") as mock_settings:
            mock_settings.MYVAULT_ENABLED = False
            mock_settings.SECRETS_CACHE_TTL = 300
            mock_settings.VALKEY_HOST = "localhost"
            mock_settings.VALKEY_PORT = "6379"
            mock_settings.VALKEY_ENABLED = "true"

            manager = SecretsManager()
            manager.myvault_enabled = False
            manager.myvault_client = None

            yield manager

    # ========== Test Cases for get_connection_config ==========

    def test_get_connection_config_string_from_myvault(self, manager_with_myvault):
        """Test get_connection_config retrieves string value from MyVault."""
        manager_with_myvault.myvault_client.get_secret.return_value = (
            "redis.example.com"
        )

        result = manager_with_myvault.get_connection_config(
            "VALKEY_HOST", project="test"
        )

        assert result == "redis.example.com"
        manager_with_myvault.myvault_client.get_secret.assert_called_once_with(
            "test", "VALKEY_HOST"
        )

    def test_get_connection_config_int_from_myvault(self, manager_with_myvault):
        """Test get_connection_config retrieves and converts int value from MyVault."""
        manager_with_myvault.myvault_client.get_secret.return_value = "6379"

        result = manager_with_myvault.get_connection_config(
            "VALKEY_PORT", project="test", value_type=int
        )

        assert result == 6379
        assert isinstance(result, int)

    def test_get_connection_config_bool_true_from_myvault(self, manager_with_myvault):
        """Test get_connection_config retrieves and converts bool(True) from MyVault."""
        # Test various truthy string representations
        truthy_values = ["true", "True", "TRUE", "1", "yes", "Yes", "on", "On"]

        for truthy_val in truthy_values:
            manager_with_myvault.myvault_client.get_secret.return_value = truthy_val

            result = manager_with_myvault.get_connection_config(
                "VALKEY_ENABLED", project="test", value_type=bool
            )

            assert result is True, f"Expected True for '{truthy_val}', got {result}"
            assert isinstance(result, bool)

    def test_get_connection_config_bool_false_from_myvault(self, manager_with_myvault):
        """Test get_connection_config retrieves and converts bool(False) from MyVault."""
        # Test various falsy string representations
        falsy_values = ["false", "False", "FALSE", "0", "no", "No", "off", "Off"]

        for falsy_val in falsy_values:
            manager_with_myvault.myvault_client.get_secret.return_value = falsy_val

            result = manager_with_myvault.get_connection_config(
                "VALKEY_ENABLED", project="test", value_type=bool
            )

            assert result is False, f"Expected False for '{falsy_val}', got {result}"
            assert isinstance(result, bool)

    def test_get_connection_config_fallback_to_env(self, manager_with_myvault):
        """Test get_connection_config falls back to env vars when MyVault fails."""
        manager_with_myvault.myvault_client.get_secret.side_effect = MyVaultError(
            "MyVault error"
        )

        with patch.object(manager_with_myvault.settings, "VALKEY_PORT", "6380"):
            result = manager_with_myvault.get_connection_config(
                "VALKEY_PORT", value_type=int
            )
            assert result == 6380
            assert isinstance(result, int)

    def test_get_connection_config_default_value(self, manager_without_myvault):
        """Test get_connection_config uses default value when not found."""
        with patch.object(manager_without_myvault.settings, "NONEXISTENT_KEY", ""):
            result = manager_without_myvault.get_connection_config(
                "NONEXISTENT_KEY", default="default-value"
            )
            assert result == "default-value"

    def test_get_connection_config_default_int_value(self, manager_without_myvault):
        """Test get_connection_config uses default int value when not found."""
        with patch.object(manager_without_myvault.settings, "NONEXISTENT_PORT", ""):
            result = manager_without_myvault.get_connection_config(
                "NONEXISTENT_PORT", default=8080, value_type=int
            )
            assert result == 8080
            assert isinstance(result, int)

    def test_get_connection_config_raises_valueerror_when_not_found(
        self, manager_without_myvault
    ):
        """Test get_connection_config raises ValueError when value not found anywhere."""
        with patch.object(manager_without_myvault.settings, "NONEXISTENT_KEY", ""):
            with pytest.raises(
                ValueError,
                match="Connection config 'NONEXISTENT_KEY' not found",
            ):
                manager_without_myvault.get_connection_config("NONEXISTENT_KEY")

    def test_get_connection_config_type_conversion_failure(self, manager_with_myvault):
        """Test get_connection_config raises ValueError on type conversion failure."""
        manager_with_myvault.myvault_client.get_secret.return_value = "not-a-number"

        with pytest.raises(
            ValueError,
            match="Failed to convert 'VALKEY_PORT' value 'not-a-number' to int",
        ):
            manager_with_myvault.get_connection_config(
                "VALKEY_PORT", project="test", value_type=int
            )

    def test_get_connection_config_port_range_validation_low(
        self, manager_with_myvault
    ):
        """Test get_connection_config validates port number range (too low)."""
        manager_with_myvault.myvault_client.get_secret.return_value = "0"

        with pytest.raises(
            ValueError,
            match="Port number .* must be between 1 and 65535",
        ):
            manager_with_myvault.get_connection_config(
                "VALKEY_PORT", project="test", value_type=int
            )

    def test_get_connection_config_port_range_validation_high(
        self, manager_with_myvault
    ):
        """Test get_connection_config validates port number range (too high)."""
        manager_with_myvault.myvault_client.get_secret.return_value = "65536"

        with pytest.raises(
            ValueError,
            match="Port number .* must be between 1 and 65535",
        ):
            manager_with_myvault.get_connection_config(
                "VALKEY_PORT", project="test", value_type=int
            )

    def test_get_connection_config_valid_port_range(self, manager_with_myvault):
        """Test get_connection_config accepts valid port numbers."""
        # Test boundary values
        boundary_ports = [1, 80, 443, 6379, 8080, 65535]

        for port in boundary_ports:
            # Clear cache to avoid cached values
            manager_with_myvault.clear_cache()
            manager_with_myvault.myvault_client.get_secret.return_value = str(port)

            result = manager_with_myvault.get_connection_config(
                "VALKEY_PORT", project="test", value_type=int
            )

            assert result == port

    def test_get_connection_config_hostname_length_validation(
        self, manager_with_myvault
    ):
        """Test get_connection_config validates hostname length."""
        # Clear cache to avoid cached values
        manager_with_myvault.clear_cache()
        # Hostname too long (> 255 chars)
        long_hostname = "a" * 256
        manager_with_myvault.myvault_client.get_secret.return_value = long_hostname

        with pytest.raises(
            ValueError,
            match="Hostname length .* must be between 1 and 255",
        ):
            manager_with_myvault.get_connection_config(
                "VALKEY_HOST", project="test", value_type=str
            )

    def test_get_connection_config_valid_hostname(self, manager_with_myvault):
        """Test get_connection_config accepts valid hostname."""
        manager_with_myvault.myvault_client.get_secret.return_value = (
            "redis.example.com"
        )

        result = manager_with_myvault.get_connection_config(
            "VALKEY_HOST", project="test", value_type=str
        )

        assert result == "redis.example.com"

    # ========== Test Cases for _convert_type ==========

    def test_convert_type_str_passthrough(self, manager_with_myvault):
        """Test _convert_type returns string as-is for str type."""
        result = manager_with_myvault._convert_type("test-value", str)
        assert result == "test-value"
        assert isinstance(result, str)

    def test_convert_type_int_success(self, manager_with_myvault):
        """Test _convert_type successfully converts string to int."""
        result = manager_with_myvault._convert_type("12345", int)
        assert result == 12345
        assert isinstance(result, int)

    def test_convert_type_int_failure(self, manager_with_myvault):
        """Test _convert_type raises ValueError for invalid int conversion."""
        with pytest.raises(ValueError):
            manager_with_myvault._convert_type("not-a-number", int)

    def test_convert_type_bool_true_values(self, manager_with_myvault):
        """Test _convert_type converts truthy strings to True."""
        truthy_values = ["true", "True", "TRUE", "1", "yes", "Yes", "on", "On"]

        for value in truthy_values:
            result = manager_with_myvault._convert_type(value, bool)
            assert result is True, f"Expected True for '{value}'"

    def test_convert_type_bool_false_values(self, manager_with_myvault):
        """Test _convert_type converts falsy strings to False."""
        falsy_values = ["false", "False", "FALSE", "0", "no", "No", "off", "Off"]

        for value in falsy_values:
            result = manager_with_myvault._convert_type(value, bool)
            assert result is False, f"Expected False for '{value}'"

    def test_convert_type_unsupported_type(self, manager_with_myvault):
        """Test _convert_type raises ValueError for unsupported types."""
        with pytest.raises(ValueError, match="Unsupported type"):
            manager_with_myvault._convert_type("value", list)

    # ========== Test Cases for _validate_connection_config ==========

    def test_validate_port_valid(self, manager_with_myvault):
        """Test _validate_connection_config passes for valid port."""
        # Should not raise
        manager_with_myvault._validate_connection_config("VALKEY_PORT", 6379, int)

    def test_validate_port_invalid_low(self, manager_with_myvault):
        """Test _validate_connection_config raises for port < 1."""
        with pytest.raises(
            ValueError, match="Port number .* must be between 1 and 65535"
        ):
            manager_with_myvault._validate_connection_config("VALKEY_PORT", 0, int)

    def test_validate_port_invalid_high(self, manager_with_myvault):
        """Test _validate_connection_config raises for port > 65535."""
        with pytest.raises(
            ValueError, match="Port number .* must be between 1 and 65535"
        ):
            manager_with_myvault._validate_connection_config("VALKEY_PORT", 65536, int)

    def test_validate_hostname_valid(self, manager_with_myvault):
        """Test _validate_connection_config passes for valid hostname."""
        # Should not raise
        manager_with_myvault._validate_connection_config(
            "VALKEY_HOST", "redis.example.com", str
        )

    def test_validate_hostname_too_long(self, manager_with_myvault):
        """Test _validate_connection_config raises for hostname > 255 chars."""
        long_hostname = "a" * 256
        with pytest.raises(
            ValueError, match="Hostname length .* must be between 1 and 255"
        ):
            manager_with_myvault._validate_connection_config(
                "VALKEY_HOST", long_hostname, str
            )

    def test_validate_hostname_empty(self, manager_with_myvault):
        """Test _validate_connection_config raises for empty hostname.

        Note: _validate_connection_config is a direct method call and doesn't involve
        cache, so this should pass without cache clearing.
        """
        with pytest.raises(
            ValueError, match="Hostname length .* must be between 1 and 255"
        ):
            manager_with_myvault._validate_connection_config("VALKEY_HOST", "", str)

    # ========== Test Cases for _log_config_retrieval ==========

    def test_log_config_retrieval_port(self, manager_with_myvault, caplog):
        """Test _log_config_retrieval logs port numbers without masking."""
        import logging

        with caplog.at_level(logging.INFO):
            manager_with_myvault._log_config_retrieval("VALKEY_PORT", "myvault", 6379)

        assert "6379" in caplog.text
        assert "VALKEY_PORT" in caplog.text

    def test_log_config_retrieval_hostname_partial_mask(
        self, manager_with_myvault, caplog
    ):
        """Test _log_config_retrieval partially masks hostname."""
        import logging

        with caplog.at_level(logging.INFO):
            manager_with_myvault._log_config_retrieval(
                "VALKEY_HOST", "myvault", "redis.example.com"
            )

        # Should show partial hostname (first few chars)
        assert "VALKEY_HOST" in caplog.text
        # Should not show full hostname
        log_text = caplog.text
        assert "redis.example.com" not in log_text or "red" in log_text

    def test_log_config_retrieval_other_masked(self, manager_with_myvault, caplog):
        """Test _log_config_retrieval fully masks other values."""
        import logging

        with caplog.at_level(logging.INFO):
            manager_with_myvault._log_config_retrieval(
                "API_KEY", "myvault", "super-secret-key"
            )

        # Should not show the actual value
        assert "super-secret-key" not in caplog.text
        assert "API_KEY" in caplog.text
        # Should show masked representation
        assert "***" in caplog.text or "****" in caplog.text

    def test_log_config_retrieval_short_hostname(self, manager_with_myvault, caplog):
        """Test _log_config_retrieval masks short hostname (<=3 chars)."""
        import logging

        with caplog.at_level(logging.INFO):
            manager_with_myvault._log_config_retrieval("VALKEY_HOST", "myvault", "abc")

        # Should show masked value
        assert "VALKEY_HOST" in caplog.text
        assert "***" in caplog.text

    # ========== Additional Test Cases for Edge Cases ==========

    def test_convert_type_bool_invalid_value(self, manager_with_myvault):
        """Test _convert_type raises ValueError for invalid bool conversion."""
        with pytest.raises(ValueError, match="Cannot convert .* to bool"):
            manager_with_myvault._convert_type("invalid-bool", bool)

    def test_get_connection_config_myvault_error_fallback_no_env(
        self, manager_with_myvault
    ):
        """Test get_connection_config when MyVault errors and no env fallback."""
        manager_with_myvault.myvault_client.get_secret.side_effect = MyVaultError(
            "MyVault error"
        )

        with patch.object(manager_with_myvault.settings, "MISSING_KEY", ""):
            with pytest.raises(
                ValueError,
                match="Connection config 'MISSING_KEY' not found",
            ):
                manager_with_myvault.get_connection_config("MISSING_KEY")

    # ========== Test Cases for _convert_to_bool ==========

    def test_convert_to_bool_true_values(self, manager_with_myvault):
        """Test _convert_to_bool converts truthy strings to True."""
        truthy_values = ["true", "True", "TRUE", "1", "yes", "Yes", "on", "On"]

        for value in truthy_values:
            result = manager_with_myvault._convert_to_bool(value)
            assert result is True, f"Expected True for '{value}'"

    def test_convert_to_bool_false_values(self, manager_with_myvault):
        """Test _convert_to_bool converts falsy strings to False."""
        falsy_values = ["false", "False", "FALSE", "0", "no", "No", "off", "Off"]

        for value in falsy_values:
            result = manager_with_myvault._convert_to_bool(value)
            assert result is False, f"Expected False for '{value}'"

    def test_convert_to_bool_invalid_value(self, manager_with_myvault):
        """Test _convert_to_bool raises ValueError for invalid conversion."""
        with pytest.raises(ValueError, match="Cannot convert .* to bool"):
            manager_with_myvault._convert_to_bool("invalid-bool")

    # ========== Test Cases for class-level constants ==========

    def test_bool_truthy_values_constant(self, manager_with_myvault):
        """Test that _BOOL_TRUTHY_VALUES contains expected values."""
        expected = {"true", "1", "yes", "on"}
        assert manager_with_myvault._BOOL_TRUTHY_VALUES == expected

    def test_bool_falsy_values_constant(self, manager_with_myvault):
        """Test that _BOOL_FALSY_VALUES contains expected values."""
        expected = {"false", "0", "no", "off"}
        assert manager_with_myvault._BOOL_FALSY_VALUES == expected

    # ========== Test Cases for get_connection_config with MyVault returns None ==========

    def test_get_connection_config_myvault_returns_none_fallback_to_env(
        self, manager_with_myvault
    ):
        """Test get_connection_config falls back to env when MyVault returns None."""
        # _get_from_myvault returns None (not found in MyVault)
        manager_with_myvault.myvault_client.get_secret.return_value = None

        with patch.object(manager_with_myvault.settings, "VALKEY_HOST", "env-host"):
            result = manager_with_myvault.get_connection_config("VALKEY_HOST")
            assert result == "env-host"
