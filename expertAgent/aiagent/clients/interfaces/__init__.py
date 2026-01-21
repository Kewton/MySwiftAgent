"""Interface definitions for HTTP client abstractions.

Issue #361: Protocol-based abstractions for testability and extensibility.
Issue #388: Added schema converter for interface format transformation.
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
from .schema_converter import (
    JsonSchema,
    SimpleMapping,
    json_schema_to_simple_mapping,
    simple_mapping_to_json_schema,
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
    # Schema Converter
    "JsonSchema",
    "SimpleMapping",
    "json_schema_to_simple_mapping",
    "simple_mapping_to_json_schema",
]
