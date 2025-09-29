"""Tests for CommonUI core functionality."""

import os
from unittest.mock import Mock, patch

import pytest

from core.config import Config
from core.exceptions import (
    APIError,
    AuthenticationError,
    CommonUIError,
    ConfigurationError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)


class TestConfig:
    """Test cases for Config class."""

    @patch.dict(os.environ, {
        'JOBQUEUE_BASE_URL': 'http://localhost:8001',
        'JOBQUEUE_API_TOKEN': 'test-jobqueue-token',
        'MYSCHEDULER_BASE_URL': 'http://localhost:8002',
        'MYSCHEDULER_API_TOKEN': 'test-myscheduler-token',
        'POLLING_INTERVAL': '10',
        'DEFAULT_SERVICE': 'MyScheduler',
        'OPERATION_MODE': 'readonly'
    })
    def test_config_from_environment(self):
        """Test configuration loading from environment variables."""
        config = Config()

        # Test JobQueue config
        jobqueue_config = config.get_api_config("jobqueue")
        assert jobqueue_config.base_url == "http://localhost:8001"
        assert jobqueue_config.token == "test-jobqueue-token"

        # Test MyScheduler config
        myscheduler_config = config.get_api_config("myscheduler")
        assert myscheduler_config.base_url == "http://localhost:8002"
        assert myscheduler_config.token == "test-myscheduler-token"

        # Test UI config
        assert config.ui.polling_interval == 10
        assert config.ui.default_service == "MyScheduler"
        assert config.ui.operation_mode == "readonly"

    def test_config_defaults(self):
        """Test configuration with default values."""
        with patch.dict(os.environ, {}, clear=True):
            config = Config()

            # Test default values
            assert config.ui.polling_interval == 5
            assert config.ui.default_service == "JobQueue"
            assert config.ui.operation_mode == "full"

            # Test default URLs
            jobqueue_config = config.get_api_config("jobqueue")
            assert jobqueue_config.base_url == "http://localhost:8001"

            myscheduler_config = config.get_api_config("myscheduler")
            assert myscheduler_config.base_url == "http://localhost:8002"

    def test_get_api_config_invalid_service(self):
        """Test getting API config for invalid service."""
        config = Config()

        with pytest.raises(ValueError, match="Unknown service: invalid"):
            config.get_api_config("invalid")

    @patch.dict(os.environ, {
        'JOBQUEUE_BASE_URL': 'http://localhost:8001',
        'JOBQUEUE_API_TOKEN': 'valid-token',
    })
    def test_is_service_configured_valid(self):
        """Test service configuration check for valid service."""
        config = Config()

        assert config.is_service_configured("jobqueue") is True

    @patch.dict(os.environ, {
        'JOBQUEUE_BASE_URL': 'http://localhost:8001',
        'JOBQUEUE_API_TOKEN': '',  # Empty token
    })
    def test_is_service_configured_missing_token(self):
        """Test service configuration check with missing token."""
        config = Config()

        assert config.is_service_configured("jobqueue") is False

    def test_is_service_configured_invalid_service(self):
        """Test service configuration check for invalid service."""
        config = Config()

        assert config.is_service_configured("invalid") is False

    def test_mask_token_empty(self):
        """Test token masking for empty token."""
        config = Config()

        masked = config.mask_token("")
        assert masked == "***EMPTY***"

    def test_mask_token_short(self):
        """Test token masking for short token."""
        config = Config()

        masked = config.mask_token("abc")
        assert masked == "***"

    def test_mask_token_normal(self):
        """Test token masking for normal token."""
        config = Config()

        masked = config.mask_token("abcdefghijklmnop")
        assert masked == "abcd***mnop"

    @patch('core.config.st')
    def test_streamlit_secrets_priority(self, mock_st):
        """Test that Streamlit secrets take priority over environment variables."""
        # Mock Streamlit secrets
        mock_secrets = {
            'JOBQUEUE_BASE_URL': 'http://secrets:8001',
            'JOBQUEUE_API_TOKEN': 'secret-token'
        }
        mock_st.secrets = mock_secrets

        # Set environment variables
        with patch.dict(os.environ, {
            'JOBQUEUE_BASE_URL': 'http://env:8001',
            'JOBQUEUE_API_TOKEN': 'env-token'
        }):
            config = Config()

            jobqueue_config = config.get_api_config("jobqueue")
            # Should use secrets, not environment
            assert jobqueue_config.base_url == "http://secrets:8001"
            assert jobqueue_config.token == "secret-token"


class TestExceptions:
    """Test cases for custom exceptions."""

    def test_common_ui_error_basic(self):
        """Test basic CommonUIError creation."""
        error = CommonUIError("Test error message")

        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.details == {}

    def test_common_ui_error_with_details(self):
        """Test CommonUIError with details."""
        details = {"key": "value", "code": 123}
        error = CommonUIError("Test error", details)

        assert error.message == "Test error"
        assert error.details == details

    def test_api_error_basic(self):
        """Test basic APIError creation."""
        error = APIError("API failed")

        assert str(error) == "API failed"
        assert error.message == "API failed"
        assert error.status_code is None
        assert error.response_data == {}

    def test_api_error_with_status_and_data(self):
        """Test APIError with status code and response data."""
        response_data = {"error": "Bad Request", "field": "name"}
        error = APIError("Request failed", status_code=400, response_data=response_data)

        assert error.message == "Request failed"
        assert error.status_code == 400
        assert error.response_data == response_data
        assert error.details["status_code"] == 400
        assert error.details["response_data"] == response_data

    def test_configuration_error(self):
        """Test ConfigurationError creation."""
        error = ConfigurationError("Invalid config")

        assert isinstance(error, CommonUIError)
        assert error.message == "Invalid config"

    def test_validation_error(self):
        """Test ValidationError creation."""
        details = {"field": "email", "error": "invalid format"}
        error = ValidationError("Validation failed", details)

        assert isinstance(error, CommonUIError)
        assert error.message == "Validation failed"
        assert error.details == details

    def test_service_unavailable_error(self):
        """Test ServiceUnavailableError creation."""
        error = ServiceUnavailableError("TestService", "http://localhost:8001")

        assert isinstance(error, APIError)
        assert error.service_name == "TestService"
        assert error.base_url == "http://localhost:8001"
        assert error.status_code == 503
        assert "TestService" in error.message
        assert "http://localhost:8001" in error.message

    def test_authentication_error(self):
        """Test AuthenticationError creation."""
        error = AuthenticationError("TestService")

        assert isinstance(error, APIError)
        assert error.service_name == "TestService"
        assert error.status_code == 401
        assert "TestService" in error.message
        assert "Authentication failed" in error.message

    def test_rate_limit_error_without_retry_after(self):
        """Test RateLimitError without retry-after."""
        error = RateLimitError()

        assert isinstance(error, APIError)
        assert error.status_code == 429
        assert error.retry_after is None
        assert error.message == "Rate limit exceeded"

    def test_rate_limit_error_with_retry_after(self):
        """Test RateLimitError with retry-after."""
        error = RateLimitError(retry_after=30)

        assert error.retry_after == 30
        assert error.status_code == 429
        assert "retry after 30 seconds" in error.message

    def test_exception_inheritance(self):
        """Test exception inheritance hierarchy."""
        # Test inheritance chain
        api_error = APIError("API error")
        assert isinstance(api_error, CommonUIError)
        assert isinstance(api_error, Exception)

        service_error = ServiceUnavailableError("Service", "URL")
        assert isinstance(service_error, APIError)
        assert isinstance(service_error, CommonUIError)

        auth_error = AuthenticationError("Service")
        assert isinstance(auth_error, APIError)
        assert isinstance(auth_error, CommonUIError)

        rate_error = RateLimitError()
        assert isinstance(rate_error, APIError)
        assert isinstance(rate_error, CommonUIError)

        config_error = ConfigurationError("Config error")
        assert isinstance(config_error, CommonUIError)

        validation_error = ValidationError("Validation error")
        assert isinstance(validation_error, CommonUIError)