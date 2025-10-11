"""Core functionality for CommonUI application."""

from .config import Config, config
from .exceptions import (
    APIError,
    AuthenticationError,
    CommonUIError,
    ConfigurationError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)

__all__ = [
    "APIError",
    "AuthenticationError",
    "CommonUIError",
    "Config",
    "ConfigurationError",
    "RateLimitError",
    "ServiceUnavailableError",
    "ValidationError",
    "config",
]
