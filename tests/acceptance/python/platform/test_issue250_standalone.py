"""Standalone Acceptance Tests for Issue #250: get_connection_config().

This is a standalone test file that doesn't depend on the conftest hierarchy.
It tests the real functionality of SecretsManager.get_connection_config() method.

Run with:
    cd expertAgent && uv run pytest ../tests/acceptance/python/platform/test_issue250_standalone.py -v
"""

import logging
import os
import sys

import httpx
import pytest

# Add expertAgent to path
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    )
)
EXPERT_AGENT_PATH = os.path.join(PROJECT_ROOT, "expertAgent")
if EXPERT_AGENT_PATH not in sys.path:
    sys.path.insert(0, EXPERT_AGENT_PATH)


# =============================================================================
# Setup
# =============================================================================


MYVAULT_URL = os.getenv("MYVAULT_URL", "http://localhost:8103")


def is_myvault_available() -> bool:
    """Check if MyVault service is running."""
    try:
        response = httpx.get(f"{MYVAULT_URL}/health", timeout=5.0)
        return response.status_code == 200
    except httpx.RequestError:
        return False


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture(scope="module")
def myvault_status():
    """Check MyVault availability once per module."""
    available = is_myvault_available()
    print(f"\n{'='*60}")
    print(f"MyVault Status: {'AVAILABLE' if available else 'NOT AVAILABLE'}")
    print(f"URL: {MYVAULT_URL}")
    print(f"{'='*60}")
    return available


@pytest.fixture
def secrets_manager():
    """Create SecretsManager instance."""
    from core.secrets import SecretsManager
    return SecretsManager()


# =============================================================================
# Test: MyVault Connection
# =============================================================================


class TestMyVaultConnection:
    """Test MyVault service connection."""

    def test_myvault_health_endpoint(self, myvault_status):
        """Verify MyVault health endpoint responds."""
        if not myvault_status:
            pytest.skip("MyVault is not available")

        response = httpx.get(f"{MYVAULT_URL}/health", timeout=5.0)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        print(f"\n[REAL TEST] MyVault health: {data}")

    def test_secrets_manager_initialization(self, myvault_status, secrets_manager):
        """Verify SecretsManager initializes with MyVault."""
        print(f"\n[REAL TEST] SecretsManager state:")
        print(f"  - myvault_enabled: {secrets_manager.myvault_enabled}")
        print(f"  - myvault_client: {secrets_manager.myvault_client is not None}")

        # The manager should be initialized regardless of MyVault availability
        assert hasattr(secrets_manager, "myvault_enabled")
        assert hasattr(secrets_manager, "get_connection_config")


# =============================================================================
# Test: Type Conversion (Real)
# =============================================================================


class TestTypeConversionReal:
    """Test type conversion with real SecretsManager."""

    def test_convert_type_int(self, secrets_manager):
        """Test integer conversion method directly."""
        result = secrets_manager._convert_type("6379", int)
        assert result == 6379
        assert isinstance(result, int)
        print(f"\n[REAL TEST] _convert_type('6379', int) = {result}")

    def test_convert_type_bool_true(self, secrets_manager):
        """Test boolean true conversion."""
        for value in ["true", "True", "TRUE", "1", "yes", "on"]:
            result = secrets_manager._convert_type(value, bool)
            assert result is True
            print(f"[REAL TEST] _convert_type('{value}', bool) = {result}")

    def test_convert_type_bool_false(self, secrets_manager):
        """Test boolean false conversion."""
        for value in ["false", "False", "FALSE", "0", "no", "off"]:
            result = secrets_manager._convert_type(value, bool)
            assert result is False
            print(f"[REAL TEST] _convert_type('{value}', bool) = {result}")

    def test_convert_type_invalid_int(self, secrets_manager):
        """Test invalid integer conversion raises error."""
        with pytest.raises(ValueError):
            secrets_manager._convert_type("not-a-number", int)
        print("\n[REAL TEST] Invalid int conversion raised ValueError as expected")

    def test_convert_type_invalid_bool(self, secrets_manager):
        """Test invalid boolean conversion raises error."""
        with pytest.raises(ValueError) as exc_info:
            secrets_manager._convert_type("maybe", bool)
        assert "Cannot convert" in str(exc_info.value)
        print(f"\n[REAL TEST] Invalid bool error: {exc_info.value}")


# =============================================================================
# Test: Validation (Real)
# =============================================================================


class TestValidationReal:
    """Test validation with real SecretsManager."""

    def test_validate_port_valid(self, secrets_manager):
        """Test valid port passes validation."""
        # Should not raise
        secrets_manager._validate_connection_config("VALKEY_PORT", 6379, int)
        secrets_manager._validate_connection_config("VALKEY_PORT", 1, int)
        secrets_manager._validate_connection_config("VALKEY_PORT", 65535, int)
        print("\n[REAL TEST] Valid ports (1, 6379, 65535) passed validation")

    def test_validate_port_invalid_low(self, secrets_manager):
        """Test port < 1 fails validation."""
        with pytest.raises(ValueError) as exc_info:
            secrets_manager._validate_connection_config("VALKEY_PORT", 0, int)
        assert "1" in str(exc_info.value) and "65535" in str(exc_info.value)
        print(f"\n[REAL TEST] Port 0 error: {exc_info.value}")

    def test_validate_port_invalid_high(self, secrets_manager):
        """Test port > 65535 fails validation."""
        with pytest.raises(ValueError) as exc_info:
            secrets_manager._validate_connection_config("VALKEY_PORT", 65536, int)
        print(f"\n[REAL TEST] Port 65536 error: {exc_info.value}")

    def test_validate_hostname_valid(self, secrets_manager):
        """Test valid hostname passes validation."""
        secrets_manager._validate_connection_config(
            "VALKEY_HOST", "redis.example.com", str
        )
        secrets_manager._validate_connection_config("VALKEY_HOST", "a", str)
        secrets_manager._validate_connection_config("VALKEY_HOST", "a" * 255, str)
        print("\n[REAL TEST] Valid hostnames passed validation")

    def test_validate_hostname_empty(self, secrets_manager):
        """Test empty hostname fails validation."""
        with pytest.raises(ValueError) as exc_info:
            secrets_manager._validate_connection_config("VALKEY_HOST", "", str)
        print(f"\n[REAL TEST] Empty hostname error: {exc_info.value}")

    def test_validate_hostname_too_long(self, secrets_manager):
        """Test hostname > 255 chars fails validation."""
        long_hostname = "a" * 256
        with pytest.raises(ValueError) as exc_info:
            secrets_manager._validate_connection_config("VALKEY_HOST", long_hostname, str)
        print(f"\n[REAL TEST] Long hostname error: {exc_info.value}")


# =============================================================================
# Test: Log Masking (Real)
# =============================================================================


class TestLogMaskingReal:
    """Test log output masking with real SecretsManager."""

    def test_log_port_unmasked(self, secrets_manager, caplog):
        """Test port numbers are NOT masked in logs."""
        with caplog.at_level(logging.INFO):
            secrets_manager._log_config_retrieval("VALKEY_PORT", "myvault", 6379)

        assert "6379" in caplog.text
        print(f"\n[REAL TEST] Port log (unmasked): '6379' found in logs")

    def test_log_hostname_partially_masked(self, secrets_manager, caplog):
        """Test hostnames are partially masked in logs."""
        with caplog.at_level(logging.INFO):
            secrets_manager._log_config_retrieval(
                "VALKEY_HOST", "myvault", "redis.example.com"
            )

        # Should show "red***" not full hostname
        assert "***" in caplog.text
        assert "redis.example.com" not in caplog.text
        print(f"\n[REAL TEST] Hostname log (masked): '***' found, full hostname hidden")

    def test_log_secret_fully_masked(self, secrets_manager, caplog):
        """Test other values are fully masked in logs."""
        with caplog.at_level(logging.INFO):
            secrets_manager._log_config_retrieval(
                "API_KEY", "myvault", "sk-secret-key-12345"
            )

        assert "sk-secret-key-12345" not in caplog.text
        assert "****" in caplog.text
        print(f"\n[REAL TEST] Secret log (fully masked): original value hidden")


# =============================================================================
# Test: get_connection_config Integration
# =============================================================================


class TestGetConnectionConfigIntegration:
    """Test get_connection_config() end-to-end."""

    def test_default_value_returned(self, secrets_manager):
        """Test default value is returned when key not found."""
        # Use a key that definitely doesn't exist
        result = secrets_manager.get_connection_config(
            "THIS_KEY_DOES_NOT_EXIST_12345",
            default="my-default",
            value_type=str,
        )
        assert result == "my-default"
        print(f"\n[REAL TEST] Default value returned: {result}")

    def test_default_int_value_returned(self, secrets_manager):
        """Test default int value is returned when key not found."""
        result = secrets_manager.get_connection_config(
            "THIS_PORT_DOES_NOT_EXIST_12345",
            default=8080,
            value_type=int,
        )
        assert result == 8080
        assert isinstance(result, int)
        print(f"\n[REAL TEST] Default int value returned: {result}")

    def test_raises_when_not_found_no_default(self, secrets_manager):
        """Test ValueError when key not found and no default."""
        with pytest.raises(ValueError) as exc_info:
            secrets_manager.get_connection_config(
                "ABSOLUTELY_NOT_FOUND_KEY_99999",
            )
        assert "not found" in str(exc_info.value).lower()
        print(f"\n[REAL TEST] ValueError raised: {exc_info.value}")


# =============================================================================
# Test: Full Scenario
# =============================================================================


class TestFullScenario:
    """Test complete realistic scenario."""

    def test_valkey_configuration_scenario(self, secrets_manager):
        """Test realistic Valkey configuration retrieval."""
        # This simulates what would happen in real application code

        # Get config with defaults (what real code would do)
        host = secrets_manager.get_connection_config(
            "VALKEY_HOST_SCENARIO_TEST",
            default="localhost",
            value_type=str,
        )
        port = secrets_manager.get_connection_config(
            "VALKEY_PORT_SCENARIO_TEST",
            default=6379,
            value_type=int,
        )
        enabled = secrets_manager.get_connection_config(
            "VALKEY_ENABLED_SCENARIO_TEST",
            default=True,
            value_type=bool,
        )

        print(f"\n[REAL TEST] Valkey config scenario:")
        print(f"  - host: {host} (type: {type(host).__name__})")
        print(f"  - port: {port} (type: {type(port).__name__})")
        print(f"  - enabled: {enabled} (type: {type(enabled).__name__})")

        assert isinstance(host, str)
        assert isinstance(port, int)
        assert isinstance(enabled, bool)

        # Validate we could use these to connect
        assert 1 <= port <= 65535
        assert len(host) > 0


# =============================================================================
# Summary
# =============================================================================


if __name__ == "__main__":
    print("=" * 70)
    print("ACCEPTANCE TEST: Issue #250 - get_connection_config()")
    print("=" * 70)
    print("This test verifies REAL functionality, not mocked behavior.")
    print("=" * 70)
    pytest.main([__file__, "-v"])
