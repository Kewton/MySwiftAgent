"""Interface definitions for HTTP client abstractions.

Issue #361: Protocol-based abstractions for testability and extensibility.
"""

from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerOpenError,
    CircuitState,
)
from .http_client import HttpResponse, HttpxClientAdapter, IHttpClient
from .metrics import (
    IMetricsCollector,
    LoggingMetricsCollector,
    NoOpMetricsCollector,
    RequestMetrics,
)

__all__ = [
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerOpenError",
    "CircuitState",
    # HTTP Client
    "HttpResponse",
    "HttpxClientAdapter",
    "IHttpClient",
    # Metrics
    "IMetricsCollector",
    "LoggingMetricsCollector",
    "NoOpMetricsCollector",
    "RequestMetrics",
]
