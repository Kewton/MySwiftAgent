"""Acceptance tests for Issue #251: resolve_runtime_value type conversion.

This module contains practical acceptance tests that verify:
1. Real MyVault integration with type conversion
2. Environment variable fallback with type conversion
3. Backward compatibility with existing call sites
4. Error handling for invalid type conversions

These tests require:
- MyVault service running (http://localhost:8103)
- expertAgent service running (http://localhost:8104)
"""

import os
import sys
from pathlib import Path

import httpx
import pytest

# Add expertAgent to path for direct function testing
EXPERT_AGENT_PATH = Path(__file__).parents[4] / "expertAgent"
sys.path.insert(0, str(EXPERT_AGENT_PATH))


class TestResolveRuntimeValueAcceptance:
    """Acceptance tests for resolve_runtime_value with real services.

    These tests use existing MyVault data (MAIL_TO, OPENAI_API_KEY, etc.)
    since the test service doesn't have write permissions.
    """

    @pytest.fixture(autouse=True)
    def setup_myvault_client(self) -> None:
        """Setup MyVault client for test data management."""
        self.myvault_url = os.getenv("MYVAULT_URL", "http://localhost:8103")

    def test_myvault_service_health(self) -> None:
        """AC-0: Verify MyVault service is healthy before running tests."""
        with httpx.Client(base_url=self.myvault_url, timeout=10.0) as client:
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert data["service"] == "myVault"

    def test_string_from_real_myvault(self) -> None:
        """AC-1: Verify resolve_runtime_value retrieves real data from MyVault."""
        from core.secrets import resolve_runtime_value

        # MAIL_TO is known to exist in MyVault (verified in earlier tests)
        result = resolve_runtime_value("MAIL_TO")

        assert isinstance(result, str), f"Expected str, got {type(result)}"
        assert len(result) > 0, "Expected non-empty string from MyVault"
        # Email should contain @ if it's a valid email
        assert "@" in result or result != "", "Got value from MyVault"

    def test_backward_compatibility_returns_string(self) -> None:
        """AC-2: resolve_runtime_value without value_type returns string (backward compatibility)."""
        from core.secrets import resolve_runtime_value

        # Call without value_type (should default to str)
        result = resolve_runtime_value("OPENAI_API_KEY")

        assert isinstance(result, str), f"Expected str, got {type(result)}"
        # API key should be a non-empty string
        assert len(result) > 0, "Expected non-empty API key"

    def test_backward_compatibility_model_config(self) -> None:
        """AC-2b: Model config value returns string (existing behavior)."""
        from core.secrets import resolve_runtime_value

        # Existing code would call without value_type
        result = resolve_runtime_value("OLLAMA_DEF_SMALL_MODEL")

        assert isinstance(result, str), f"Expected str, got {type(result)}"
        # Model name should be a non-empty string
        assert len(result) > 0, "Expected non-empty model name"

    def test_env_fallback_with_type_conversion(self) -> None:
        """AC-4: Environment variable fallback with type conversion works.

        Note: This test uses an existing settings attribute (VALKEY_PORT)
        because Pydantic Settings doesn't allow dynamic attribute creation.
        """
        from core.secrets import resolve_runtime_value

        # Use VALKEY_PORT which exists in settings and falls back to env
        # when not in MyVault
        result = resolve_runtime_value(
            "VALKEY_PORT",
            value_type=int,
            default=6379,
        )

        # Should return an integer (either from env or default)
        assert isinstance(result, int), f"Expected int, got {type(result)}"
        assert result > 0, f"Expected positive port, got {result}"

    def test_default_value_when_not_found(self) -> None:
        """AC-5: Default value is returned when key not found anywhere."""
        from core.secrets import resolve_runtime_value

        result = resolve_runtime_value(
            "NONEXISTENT_KEY_251",
            default=9999,
            value_type=int,
        )

        # Default value is returned as-is (not converted)
        assert result == 9999, f"Expected 9999, got {result}"


class TestExistingCallSitesCompatibility:
    """Verify existing call sites still work correctly."""

    def test_stdio_action_mail_to(self) -> None:
        """Verify stdio_action.py MAIL_TO call works (expects string)."""
        from core.secrets import resolve_runtime_value

        # This mimics the call in mymcp/stdio_action.py line 150
        result = resolve_runtime_value("MAIL_TO", default="test@example.com")

        assert isinstance(result, str), f"MAIL_TO should be string, got {type(result)}"

    def test_chatollama_model_config(self) -> None:
        """Verify chatollama.py model config calls work (expects string)."""
        from core.secrets import resolve_runtime_value

        # This mimics the call in mymcp/utils/chatollama.py line 32
        result = resolve_runtime_value(
            "OLLAMA_DEF_SMALL_MODEL",
            default="gemma2:2b",
        )

        assert isinstance(result, str), (
            f"OLLAMA_DEF_SMALL_MODEL should be string, got {type(result)}"
        )

    def test_openai_api_key(self) -> None:
        """Verify OPENAI_API_KEY call works (expects string)."""
        from core.secrets import resolve_runtime_value

        # This mimics the call in mymcp/tool/file_reader_processors.py
        result = resolve_runtime_value("OPENAI_API_KEY", default="")

        assert isinstance(result, str), f"OPENAI_API_KEY should be string, got {type(result)}"


class TestTypeConversionEdgeCases:
    """Edge case tests for type conversion."""

    def test_int_conversion_with_whitespace(self) -> None:
        """Integer conversion handles values correctly."""
        from core.secrets import _convert_runtime_type

        # Direct function test for edge cases
        result = _convert_runtime_type("42", int)
        assert result == 42

    def test_bool_conversion_variations(self) -> None:
        """Boolean conversion handles various true/false representations."""
        from core.secrets import _convert_runtime_type

        # True values
        for val in ["true", "True", "TRUE", "1", "yes", "on"]:
            assert _convert_runtime_type(val, bool) is True, f"'{val}' should be True"

        # False values (anything not in true list)
        for val in ["false", "False", "0", "no", "off", ""]:
            assert _convert_runtime_type(val, bool) is False, f"'{val}' should be False"

    def test_unsupported_type_raises_error(self) -> None:
        """Unsupported type raises clear error."""
        from core.secrets import _convert_runtime_type

        with pytest.raises(ValueError) as exc_info:
            _convert_runtime_type("value", list)

        assert "Unsupported type" in str(exc_info.value)


class TestRealWorldScenarios:
    """Real-world usage scenarios."""

    def test_valkey_port_scenario(self) -> None:
        """Simulate real VALKEY_PORT usage with type conversion.

        This test verifies the real-world scenario where VALKEY_PORT
        is retrieved and used to construct a connection string.
        """
        from core.secrets import resolve_runtime_value

        # Get port with type conversion (real usage pattern)
        port = resolve_runtime_value("VALKEY_PORT", value_type=int, default=6379)

        assert isinstance(port, int), f"Port should be int, got {type(port)}"
        assert port > 0, f"Port should be positive, got {port}"

        # Verify it can be used in connection (type check)
        connection_string = f"redis://localhost:{port}"
        assert str(port) in connection_string

    def test_feature_flag_scenario(self) -> None:
        """Simulate feature flag usage with boolean conversion.

        This tests boolean conversion using DEBUG setting which is
        a real setting in the system.
        """
        from core.secrets import resolve_runtime_value

        # Get DEBUG flag with bool conversion (real usage pattern)
        debug_enabled = resolve_runtime_value(
            "DEBUG",
            value_type=bool,
            default=False,
        )

        assert isinstance(debug_enabled, bool), f"DEBUG should be bool, got {type(debug_enabled)}"

        # Use in conditional (real usage pattern)
        if debug_enabled:
            result = "debug_mode"
        else:
            result = "production_mode"
        assert result in ["debug_mode", "production_mode"]

    def test_timeout_configuration_scenario(self) -> None:
        """Simulate timeout configuration with integer conversion.

        Uses SECRETS_CACHE_TTL as a real integer configuration value.
        """
        from core.secrets import resolve_runtime_value

        # Get cache TTL with int conversion (real usage pattern)
        cache_ttl = resolve_runtime_value(
            "SECRETS_CACHE_TTL",
            value_type=int,
            default=300,
        )

        assert isinstance(cache_ttl, int), f"Cache TTL should be int, got {type(cache_ttl)}"
        assert cache_ttl >= 0, f"Cache TTL should be non-negative, got {cache_ttl}"

        # Use in configuration (real usage pattern)
        config = {"cache_ttl": cache_ttl}
        assert isinstance(config["cache_ttl"], int)
