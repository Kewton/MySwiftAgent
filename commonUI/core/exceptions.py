"""Custom exceptions for CommonUI application."""

from typing import Any


class CommonUIError(Exception):
    """Base exception for CommonUI application."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """Initialize exception with message and optional details."""
        super().__init__(message)
        self.message = message
        self.details = details or {}


class APIError(CommonUIError):
    """Exception for API-related errors."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[str, Any] | None = None,
    ) -> None:
        """Initialize API exception with status code and response data."""
        super().__init__(
            message, {"status_code": status_code, "response_data": response_data},
        )
        self.status_code = status_code
        self.response_data = response_data or {}


class ConfigurationError(CommonUIError):
    """Exception for configuration-related errors."""


class ValidationError(CommonUIError):
    """Exception for data validation errors."""


class ServiceUnavailableError(APIError):
    """Exception when external service is unavailable."""

    def __init__(self, service_name: str, base_url: str) -> None:
        """Initialize service unavailable exception."""
        message = f"Service '{service_name}' is unavailable at {base_url}"
        super().__init__(
            message,
            status_code=503,
            response_data={"service": service_name, "url": base_url},
        )
        self.service_name = service_name
        self.base_url = base_url


class AuthenticationError(APIError):
    """Exception for authentication failures."""

    def __init__(self, service_name: str) -> None:
        """Initialize authentication exception."""
        message = f"Authentication failed for service '{service_name}'"
        super().__init__(
            message, status_code=401, response_data={"service": service_name},
        )
        self.service_name = service_name


class RateLimitError(APIError):
    """Exception for rate limiting errors."""

    def __init__(self, retry_after: int | None = None) -> None:
        """Initialize rate limit exception."""
        message = "Rate limit exceeded"
        if retry_after:
            message += f", retry after {retry_after} seconds"
        super().__init__(
            message, status_code=429, response_data={"retry_after": retry_after},
        )
        self.retry_after = retry_after
