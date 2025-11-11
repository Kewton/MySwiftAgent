"""
Service Metrics Collection Module for Issue #150

This module provides functionality to collect and analyze service metrics
including response time, success rate, and health status.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional
import json
from pathlib import Path


class HealthStatus(Enum):
    """Service health status enum."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ServiceMetrics:
    """Service metrics data class."""

    service_name: str
    success_rate: float = 0.0
    avg_response_time: float = 0.0
    total_requests: int = 0
    failed_requests: int = 0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """Convert metrics to dictionary format."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


class MetricsCollector:
    """Collects and aggregates service metrics."""

    def __init__(self, service_name: str, time_window_minutes: int = 5):
        """
        Initialize metrics collector.

        Args:
            service_name: Name of the service to monitor
            time_window_minutes: Time window for metrics aggregation (default: 5 minutes)
        """
        self.service_name = service_name
        self.time_window = timedelta(minutes=time_window_minutes)
        self._requests: List[dict] = []
        self._response_times: List[float] = []

    def record_request(
        self, success: bool, timestamp: Optional[datetime] = None
    ) -> None:
        """
        Record a request result.

        Args:
            success: Whether the request was successful
            timestamp: Request timestamp (default: now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        self._requests.append({"success": success, "timestamp": timestamp})

    def record_response_time(self, response_time: float) -> None:
        """
        Record a response time measurement.

        Args:
            response_time: Response time in seconds
        """
        self._response_times.append(response_time)

    def clear(self) -> None:
        """Clear all collected metrics."""
        self._requests.clear()
        self._response_times.clear()

    def _filter_by_time_window(self) -> List[dict]:
        """Filter requests within the time window."""
        cutoff_time = datetime.now() - self.time_window
        return [req for req in self._requests if req["timestamp"] >= cutoff_time]

    def get_metrics(self) -> ServiceMetrics:
        """
        Calculate and return current metrics.

        Returns:
            ServiceMetrics object with aggregated metrics
        """
        # Filter by time window
        recent_requests = self._filter_by_time_window()

        total = len(recent_requests)

        # Calculate success rate
        successful = sum(1 for req in recent_requests if req["success"])
        success_rate = successful / total if total > 0 else 0.0

        # Calculate average response time
        avg_response_time = (
            sum(self._response_times) / len(self._response_times)
            if self._response_times
            else 0.0
        )

        # Count failures
        failed = total - successful

        # Use max of requests count and response times count for total
        # to handle cases where only one type is recorded
        effective_total = max(total, len(self._response_times))

        return ServiceMetrics(
            service_name=self.service_name,
            success_rate=success_rate,
            avg_response_time=avg_response_time,
            total_requests=effective_total,
            failed_requests=failed,
        )

    def get_health_status(self) -> HealthStatus:
        """
        Determine health status based on current metrics.

        Returns:
            HealthStatus enum value
        """
        metrics = self.get_metrics()

        if metrics.success_rate >= 0.9:
            return HealthStatus.HEALTHY
        elif metrics.success_rate >= 0.7:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.UNHEALTHY

    def save_to_file(self, file_path: Path) -> None:
        """
        Save metrics to a JSON file.

        Args:
            file_path: Path to save metrics
        """
        metrics = self.get_metrics()
        with open(file_path, "w") as f:
            json.dump(metrics.to_dict(), f, indent=2)

    @classmethod
    def load_from_file(cls, file_path: Path) -> "MetricsCollector":
        """
        Load metrics from a JSON file.

        Args:
            file_path: Path to load metrics from

        Returns:
            MetricsCollector instance with loaded data
        """
        with open(file_path, "r") as f:
            data = json.load(f)

        collector = cls(service_name=data["service_name"])

        # Reconstruct requests based on metrics
        total = data.get("total_requests", 0)
        failed = data.get("failed_requests", 0)
        successful = total - failed

        for _ in range(successful):
            collector.record_request(success=True)
        for _ in range(failed):
            collector.record_request(success=False)

        # Reconstruct response times
        if data.get("avg_response_time", 0) > 0:
            for _ in range(total):
                collector.record_response_time(data["avg_response_time"])

        return collector


class AnomalyDetector:
    """Detects anomalies in service metrics."""

    def __init__(
        self,
        success_rate_threshold: float = 0.8,
        response_time_threshold: float = 2.0,
        consecutive_failures_threshold: int = 3,
    ):
        """
        Initialize anomaly detector.

        Args:
            success_rate_threshold: Minimum acceptable success rate
            response_time_threshold: Maximum acceptable response time (seconds)
            consecutive_failures_threshold: Number of consecutive failures to trigger alert
        """
        self.success_rate_threshold = success_rate_threshold
        self.response_time_threshold = response_time_threshold
        self.consecutive_failures_threshold = consecutive_failures_threshold
        self._consecutive_failures = 0

    def detect_anomaly(self, metrics: ServiceMetrics) -> bool:
        """
        Detect if metrics indicate an anomaly.

        Args:
            metrics: Service metrics to analyze

        Returns:
            True if anomaly detected, False otherwise
        """
        # Check success rate
        if metrics.success_rate < self.success_rate_threshold:
            return True

        # Check response time
        if metrics.avg_response_time > self.response_time_threshold:
            return True

        return False

    def check_consecutive_failures(self, success: bool) -> bool:
        """
        Check for consecutive failures.

        Args:
            success: Whether the latest request was successful

        Returns:
            True if consecutive failures threshold exceeded
        """
        if not success:
            self._consecutive_failures += 1
            if self._consecutive_failures >= self.consecutive_failures_threshold:
                return True
        else:
            self._consecutive_failures = 0

        return False
