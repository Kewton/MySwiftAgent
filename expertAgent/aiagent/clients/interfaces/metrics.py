"""Metrics collection interfaces and implementations.

Issue #361: Metrics abstraction for observability.

This module provides:
- RequestMetrics: Data container for request metrics
- IMetricsCollector: Protocol for metrics collection
- NoOpMetricsCollector: Default no-op implementation
- LoggingMetricsCollector: Logging-based implementation
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class RequestMetrics:
    """Request metrics data container.

    Attributes:
        url: Request URL
        method: HTTP method
        status_code: Response status code
        latency_ms: Request latency in milliseconds
        request_size_bytes: Request body size
        response_size_bytes: Response body size
        success: Whether request was successful
        error_type: Error type if failed
        timestamp: When the request occurred
    """

    url: str
    method: str
    status_code: int
    latency_ms: float
    request_size_bytes: int
    response_size_bytes: int
    success: bool
    error_type: str | None = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


class IMetricsCollector(Protocol):
    """Metrics collector interface.

    Enables dependency injection of metrics collection,
    supporting future Prometheus/OpenTelemetry integration.

    Example:
        class PrometheusMetricsCollector:
            def record_request(self, metrics: RequestMetrics) -> None:
                REQUEST_LATENCY.labels(method=metrics.method).observe(metrics.latency_ms)

            def increment_counter(self, name: str, labels: dict) -> None:
                COUNTER_REGISTRY[name].labels(**labels).inc()
    """

    def record_request(self, metrics: RequestMetrics) -> None:
        """Record request metrics.

        Args:
            metrics: Request metrics to record
        """
        ...

    def increment_counter(self, name: str, labels: dict[str, str]) -> None:
        """Increment a named counter.

        Args:
            name: Counter name
            labels: Counter labels
        """
        ...


class NoOpMetricsCollector:
    """No-op metrics collector.

    Default implementation that does nothing.
    Used when metrics collection is not configured.
    """

    def record_request(self, metrics: RequestMetrics) -> None:
        """No-op: ignore request metrics."""
        pass

    def increment_counter(self, name: str, labels: dict[str, str]) -> None:
        """No-op: ignore counter increment."""
        pass


class LoggingMetricsCollector:
    """Logging-based metrics collector.

    Logs metrics using Python's logging module.
    Useful for development and debugging.

    Example:
        collector = LoggingMetricsCollector(logging.getLogger("metrics"))
        collector.record_request(metrics)
        # Logs: "HTTP POST /api/test -> 200 (150.00ms)"
    """

    def __init__(self, logger: logging.Logger):
        """Initialize collector.

        Args:
            logger: Logger instance to use
        """
        self._logger = logger

    def record_request(self, metrics: RequestMetrics) -> None:
        """Log request metrics.

        Args:
            metrics: Request metrics to log
        """
        self._logger.info(
            "HTTP %s %s -> %d (%.2fms)",
            metrics.method,
            metrics.url,
            metrics.status_code,
            metrics.latency_ms,
        )

    def increment_counter(self, name: str, labels: dict[str, str]) -> None:
        """Log counter increment.

        Args:
            name: Counter name
            labels: Counter labels
        """
        self._logger.debug("Counter %s: %s", name, labels)
