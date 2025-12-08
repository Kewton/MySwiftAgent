"""Integration tests for myVault connection configuration - Issue #248-5.

Tests for myVault integration with Valkey and Langfuse connection configuration.
These tests verify:
1. Normal case: myVault settings retrieved -> Valkey/Langfuse connection
2. Normal case: myVault not registered -> environment variable fallback
3. Error case: myVault down -> fallback behavior

Test categories:
- ValkeyConnectionConfig: Valkey connection configuration tests
- LangfuseConnectionConfig: Langfuse connection configuration tests
- FallbackBehavior: Fallback mechanism tests
"""

from unittest.mock import MagicMock

import pytest

# Import after path setup in conftest.py
from core.myvault_client import MyVaultClient, MyVaultError
from core.secrets import SecretsManager

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_myvault_client() -> MagicMock:
    """Create a mock MyVault client."""
    mock_client = MagicMock(spec=MyVaultClient)
    mock_client.get_secret = MagicMock()
    mock_client.get_secrets = MagicMock(return_value={})
    mock_client.get_default_project = MagicMock(return_value="test-project")
    mock_client.health_check = MagicMock(return_value=True)
    return mock_client


@pytest.fixture
def fresh_secrets_manager() -> SecretsManager:
    """Create a fresh SecretsManager instance for testing."""
    # Create a new instance to avoid state from other tests
    manager = SecretsManager()
    manager.clear_cache()
    return manager


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings for testing."""
    mock = MagicMock()
    mock.MYVAULT_ENABLED = True
    mock.MYVAULT_BASE_URL = "http://localhost:8103"
    mock.MYVAULT_SERVICE_NAME = "expertagent"
    mock.MYVAULT_SERVICE_TOKEN = "test-token"
    mock.MYVAULT_DEFAULT_PROJECT = "test-project"
    mock.SECRETS_CACHE_TTL = 300
    mock.VALKEY_HOST = "localhost"
    mock.VALKEY_PORT = 6379
    mock.VALKEY_DB = 0
    mock.VALKEY_ENABLED = True
    mock.VALKEY_TTL = 86400
    mock.LANGFUSE_HOST = "http://localhost:3001"
    mock.LANGFUSE_PUBLIC_KEY = "test-public-key"
    mock.LANGFUSE_SECRET_KEY = "test-secret-key"
    return mock


# =============================================================================
# Test: Valkey Connection Configuration from myVault
# =============================================================================


@pytest.mark.integration
class TestValkeyConnectionConfigFromMyVault:
    """Tests for Valkey connection configuration retrieval from myVault."""

    def test_valkey_host_from_myvault_success(
        self, fresh_secrets_manager: SecretsManager, mock_myvault_client: MagicMock
    ):
        """Test successful retrieval of VALKEY_HOST from myVault."""
        # Arrange
        mock_myvault_client.get_secret.return_value = "valkey.example.com"
        fresh_secrets_manager.myvault_enabled = True
        fresh_secrets_manager.myvault_client = mock_myvault_client
        fresh_secrets_manager.clear_cache()

        # Act
        result = fresh_secrets_manager.get_connection_config(
            "VALKEY_HOST", value_type=str
        )

        # Assert
        assert result == "valkey.example.com"
        mock_myvault_client.get_secret.assert_called()

    def test_valkey_port_from_myvault_success(
        self, fresh_secrets_manager: SecretsManager, mock_myvault_client: MagicMock
    ):
        """Test successful retrieval of VALKEY_PORT from myVault with type conversion."""
        # Arrange
        mock_myvault_client.get_secret.return_value = "6380"
        fresh_secrets_manager.myvault_enabled = True
        fresh_secrets_manager.myvault_client = mock_myvault_client
        fresh_secrets_manager.clear_cache()

        # Act
        result = fresh_secrets_manager.get_connection_config(
            "VALKEY_PORT", value_type=int
        )

        # Assert
        assert result == 6380
        assert isinstance(result, int)

    def test_valkey_enabled_from_myvault_success(
        self, fresh_secrets_manager: SecretsManager, mock_myvault_client: MagicMock
    ):
        """Test successful retrieval of VALKEY_ENABLED from myVault with bool conversion."""
        # Arrange
        mock_myvault_client.get_secret.return_value = "true"
        fresh_secrets_manager.myvault_enabled = True
        fresh_secrets_manager.myvault_client = mock_myvault_client
        fresh_secrets_manager.clear_cache()

        # Act
        result = fresh_secrets_manager.get_connection_config(
            "VALKEY_ENABLED", value_type=bool
        )

        # Assert
        assert result is True
        assert isinstance(result, bool)


# =============================================================================
# Test: Langfuse Connection Configuration from myVault
# =============================================================================


@pytest.mark.integration
class TestLangfuseConnectionConfigFromMyVault:
    """Tests for Langfuse connection configuration retrieval from myVault."""

    def test_langfuse_host_from_myvault_success(
        self, fresh_secrets_manager: SecretsManager, mock_myvault_client: MagicMock
    ):
        """Test successful retrieval of LANGFUSE_HOST from myVault."""
        # Arrange
        mock_myvault_client.get_secret.return_value = "http://langfuse.example.com:3001"
        fresh_secrets_manager.myvault_enabled = True
        fresh_secrets_manager.myvault_client = mock_myvault_client
        fresh_secrets_manager.clear_cache()

        # Act
        result = fresh_secrets_manager.get_connection_config(
            "LANGFUSE_HOST", value_type=str
        )

        # Assert
        assert result == "http://langfuse.example.com:3001"

    def test_langfuse_keys_from_myvault_success(
        self, fresh_secrets_manager: SecretsManager, mock_myvault_client: MagicMock
    ):
        """Test successful retrieval of Langfuse API keys from myVault."""
        # Arrange
        mock_myvault_client.get_secret.side_effect = lambda _project, key: {
            "LANGFUSE_PUBLIC_KEY": "pk-test-123",
            "LANGFUSE_SECRET_KEY": "sk-test-456",
        }.get(key, "")
        fresh_secrets_manager.myvault_enabled = True
        fresh_secrets_manager.myvault_client = mock_myvault_client
        fresh_secrets_manager.clear_cache()

        # Act
        public_key = fresh_secrets_manager.get_secret("LANGFUSE_PUBLIC_KEY")
        secret_key = fresh_secrets_manager.get_secret("LANGFUSE_SECRET_KEY")

        # Assert
        assert public_key == "pk-test-123"
        assert secret_key == "sk-test-456"


# =============================================================================
# Test: Environment Variable Fallback
# =============================================================================


@pytest.mark.integration
class TestEnvironmentVariableFallback:
    """Tests for environment variable fallback when myVault is unavailable."""

    def test_valkey_host_fallback_to_env(
        self, fresh_secrets_manager: SecretsManager, mock_settings: MagicMock
    ):
        """Test VALKEY_HOST fallback to environment variable when not in myVault."""
        # Arrange
        fresh_secrets_manager.myvault_enabled = False
        fresh_secrets_manager.myvault_client = None
        fresh_secrets_manager.settings = mock_settings
        mock_settings.VALKEY_HOST = "env-valkey-host.local"

        # Act
        result = fresh_secrets_manager.get_connection_config(
            "VALKEY_HOST", value_type=str
        )

        # Assert
        assert result == "env-valkey-host.local"

    def test_valkey_port_fallback_to_env(
        self, fresh_secrets_manager: SecretsManager, mock_settings: MagicMock
    ):
        """Test VALKEY_PORT fallback to environment variable with type conversion."""
        # Arrange
        fresh_secrets_manager.myvault_enabled = False
        fresh_secrets_manager.myvault_client = None
        fresh_secrets_manager.settings = mock_settings
        mock_settings.VALKEY_PORT = "6380"

        # Act
        result = fresh_secrets_manager.get_connection_config(
            "VALKEY_PORT", value_type=int
        )

        # Assert
        assert result == 6380
        assert isinstance(result, int)

    def test_langfuse_host_fallback_to_env(
        self, fresh_secrets_manager: SecretsManager, mock_settings: MagicMock
    ):
        """Test LANGFUSE_HOST fallback to environment variable."""
        # Arrange
        fresh_secrets_manager.myvault_enabled = False
        fresh_secrets_manager.myvault_client = None
        fresh_secrets_manager.settings = mock_settings
        mock_settings.LANGFUSE_HOST = "http://env-langfuse.local:3001"

        # Act
        result = fresh_secrets_manager.get_connection_config(
            "LANGFUSE_HOST", value_type=str
        )

        # Assert
        assert result == "http://env-langfuse.local:3001"

    def test_default_value_when_not_found(
        self, fresh_secrets_manager: SecretsManager, mock_settings: MagicMock
    ):
        """Test default value is returned when key not found anywhere."""
        # Arrange
        fresh_secrets_manager.myvault_enabled = False
        fresh_secrets_manager.myvault_client = None
        fresh_secrets_manager.settings = mock_settings
        mock_settings.NONEXISTENT_KEY = ""

        # Act
        result = fresh_secrets_manager.get_connection_config(
            "NONEXISTENT_KEY", default="default-value", value_type=str
        )

        # Assert
        assert result == "default-value"


# =============================================================================
# Test: myVault Down / Error Handling
# =============================================================================


@pytest.mark.integration
class TestMyVaultErrorHandling:
    """Tests for graceful degradation when myVault is down or errors occur."""

    def test_fallback_when_myvault_connection_fails(
        self, fresh_secrets_manager: SecretsManager, mock_settings: MagicMock
    ):
        """Test fallback to env var when myVault connection fails."""
        # Arrange
        mock_client = MagicMock(spec=MyVaultClient)
        mock_client.get_secret.side_effect = MyVaultError("Connection refused")
        mock_client.get_default_project.side_effect = MyVaultError("Connection refused")

        fresh_secrets_manager.myvault_enabled = True
        fresh_secrets_manager.myvault_client = mock_client
        fresh_secrets_manager.settings = mock_settings
        mock_settings.VALKEY_HOST = "fallback-host.local"
        fresh_secrets_manager.clear_cache()

        # Act
        result = fresh_secrets_manager.get_connection_config(
            "VALKEY_HOST", value_type=str
        )

        # Assert
        assert result == "fallback-host.local"

    def test_fallback_when_myvault_secret_not_found(
        self, fresh_secrets_manager: SecretsManager, mock_settings: MagicMock
    ):
        """Test fallback to env var when secret not found in myVault."""
        # Arrange
        mock_client = MagicMock(spec=MyVaultClient)
        mock_client.get_secret.side_effect = MyVaultError("Secret not found")
        mock_client.get_default_project.return_value = "test-project"

        fresh_secrets_manager.myvault_enabled = True
        fresh_secrets_manager.myvault_client = mock_client
        fresh_secrets_manager.settings = mock_settings
        mock_settings.VALKEY_PORT = "6379"
        fresh_secrets_manager.clear_cache()

        # Act
        result = fresh_secrets_manager.get_connection_config(
            "VALKEY_PORT", value_type=int
        )

        # Assert
        assert result == 6379

    def test_raises_error_when_not_found_anywhere(
        self, fresh_secrets_manager: SecretsManager, mock_settings: MagicMock
    ):
        """Test ValueError raised when key not found anywhere and no default."""
        # Arrange
        mock_client = MagicMock(spec=MyVaultClient)
        mock_client.get_secret.side_effect = MyVaultError("Secret not found")
        mock_client.get_default_project.return_value = "test-project"

        fresh_secrets_manager.myvault_enabled = True
        fresh_secrets_manager.myvault_client = mock_client
        fresh_secrets_manager.settings = mock_settings
        mock_settings.DEFINITELY_NOT_FOUND = ""
        fresh_secrets_manager.clear_cache()

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            fresh_secrets_manager.get_connection_config(
                "DEFINITELY_NOT_FOUND", value_type=str
            )

        assert "not found" in str(exc_info.value).lower()


# =============================================================================
# Test: Type Conversion
# =============================================================================


@pytest.mark.integration
class TestTypeConversion:
    """Tests for type conversion functionality."""

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("6379", 6379),
            ("8080", 8080),
            ("443", 443),
            ("1", 1),
            ("65535", 65535),
        ],
    )
    def test_int_conversion(
        self,
        fresh_secrets_manager: SecretsManager,
        mock_settings: MagicMock,
        value: str,
        expected: int,
    ):
        """Test integer type conversion with various port numbers."""
        # Arrange
        fresh_secrets_manager.myvault_enabled = False
        fresh_secrets_manager.myvault_client = None
        fresh_secrets_manager.settings = mock_settings
        mock_settings.TEST_PORT = value

        # Act
        result = fresh_secrets_manager.get_connection_config(
            "TEST_PORT", value_type=int
        )

        # Assert
        assert result == expected
        assert isinstance(result, int)

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("off", False),
        ],
    )
    def test_bool_conversion(
        self,
        fresh_secrets_manager: SecretsManager,
        mock_settings: MagicMock,
        value: str,
        expected: bool,
    ):
        """Test boolean type conversion with various truthy/falsy values."""
        # Arrange
        fresh_secrets_manager.myvault_enabled = False
        fresh_secrets_manager.myvault_client = None
        fresh_secrets_manager.settings = mock_settings
        mock_settings.TEST_FLAG = value

        # Act
        result = fresh_secrets_manager.get_connection_config(
            "TEST_FLAG", value_type=bool
        )

        # Assert
        assert result is expected
        assert isinstance(result, bool)


# =============================================================================
# Test: Port Validation
# =============================================================================


@pytest.mark.integration
class TestPortValidation:
    """Tests for port number validation."""

    def test_port_validation_too_low(
        self, fresh_secrets_manager: SecretsManager, mock_settings: MagicMock
    ):
        """Test port number validation rejects value < 1."""
        # Arrange
        fresh_secrets_manager.myvault_enabled = False
        fresh_secrets_manager.myvault_client = None
        fresh_secrets_manager.settings = mock_settings
        mock_settings.INVALID_PORT = "0"

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            fresh_secrets_manager.get_connection_config(
                "INVALID_PORT", value_type=int
            )

        assert "port" in str(exc_info.value).lower()
        assert "1" in str(exc_info.value) and "65535" in str(exc_info.value)

    def test_port_validation_too_high(
        self, fresh_secrets_manager: SecretsManager, mock_settings: MagicMock
    ):
        """Test port number validation rejects value > 65535."""
        # Arrange
        fresh_secrets_manager.myvault_enabled = False
        fresh_secrets_manager.myvault_client = None
        fresh_secrets_manager.settings = mock_settings
        mock_settings.INVALID_PORT = "65536"

        # Act & Assert
        with pytest.raises(ValueError) as exc_info:
            fresh_secrets_manager.get_connection_config(
                "INVALID_PORT", value_type=int
            )

        assert "port" in str(exc_info.value).lower()


# =============================================================================
# Test: Integration Scenario - Full Workflow
# =============================================================================


@pytest.mark.integration
class TestFullIntegrationScenario:
    """End-to-end integration scenarios for connection configuration."""

    def test_realistic_valkey_config_retrieval_from_myvault(
        self, fresh_secrets_manager: SecretsManager, mock_myvault_client: MagicMock
    ):
        """Test realistic Valkey configuration retrieval from myVault."""
        # Arrange
        mock_myvault_client.get_secret.side_effect = lambda _project, key: {
            "VALKEY_HOST": "valkey.production.com",
            "VALKEY_PORT": "6380",
            "VALKEY_ENABLED": "true",
            "VALKEY_DB": "1",
        }.get(key)
        mock_myvault_client.get_default_project.return_value = "production"

        fresh_secrets_manager.myvault_enabled = True
        fresh_secrets_manager.myvault_client = mock_myvault_client
        fresh_secrets_manager.clear_cache()

        # Act
        host = fresh_secrets_manager.get_connection_config(
            "VALKEY_HOST", value_type=str
        )
        port = fresh_secrets_manager.get_connection_config(
            "VALKEY_PORT", value_type=int
        )
        enabled = fresh_secrets_manager.get_connection_config(
            "VALKEY_ENABLED", value_type=bool
        )
        db = fresh_secrets_manager.get_connection_config(
            "VALKEY_DB", value_type=int
        )

        # Assert
        assert host == "valkey.production.com"
        assert port == 6380
        assert enabled is True
        assert db == 1

    def test_realistic_langfuse_config_retrieval_from_myvault(
        self, fresh_secrets_manager: SecretsManager, mock_myvault_client: MagicMock
    ):
        """Test realistic Langfuse configuration retrieval from myVault."""
        # Arrange
        mock_myvault_client.get_secret.side_effect = lambda _project, key: {
            "LANGFUSE_HOST": "https://langfuse.production.com",
            "LANGFUSE_PUBLIC_KEY": "pk-prod-123",
            "LANGFUSE_SECRET_KEY": "sk-prod-456",
        }.get(key)
        mock_myvault_client.get_default_project.return_value = "production"

        fresh_secrets_manager.myvault_enabled = True
        fresh_secrets_manager.myvault_client = mock_myvault_client
        fresh_secrets_manager.clear_cache()

        # Act
        host = fresh_secrets_manager.get_connection_config(
            "LANGFUSE_HOST", value_type=str
        )

        # Assert
        assert host == "https://langfuse.production.com"

    def test_mixed_sources_myvault_and_env(
        self, fresh_secrets_manager: SecretsManager, mock_settings: MagicMock
    ):
        """Test mixed configuration from myVault and environment variables."""
        # Arrange - myVault returns some values, others fallback to env
        mock_client = MagicMock(spec=MyVaultClient)
        mock_client.get_secret.side_effect = lambda _project, key: {
            "VALKEY_HOST": "myvault-host.com",
        }.get(key)  # Only VALKEY_HOST in myVault
        mock_client.get_default_project.return_value = "test-project"

        fresh_secrets_manager.myvault_enabled = True
        fresh_secrets_manager.myvault_client = mock_client
        fresh_secrets_manager.settings = mock_settings
        mock_settings.VALKEY_PORT = "6379"  # From env
        fresh_secrets_manager.clear_cache()

        # Act
        host = fresh_secrets_manager.get_connection_config(
            "VALKEY_HOST", value_type=str
        )
        port = fresh_secrets_manager.get_connection_config(
            "VALKEY_PORT", value_type=int
        )

        # Assert
        assert host == "myvault-host.com"  # From myVault
        assert port == 6379  # From env (fallback)
