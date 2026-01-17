"""
Auto Recovery Module for Issue #150

This module provides automatic service recovery functionality including
restart management, history tracking, and retry limit enforcement.
"""

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional


class RecoveryAction(Enum):
    """Recovery action types."""

    RESTART = "RESTART"
    ALERT_ONLY = "ALERT_ONLY"
    WAIT = "WAIT"


class MaxRetriesExceededError(Exception):
    """Raised when maximum retry attempts are exceeded."""

    pass


@dataclass
class RecoveryConfig:
    """Configuration for auto recovery behavior."""

    enabled: bool = True
    max_retries: int = 3
    retry_interval_seconds: int = 60

    def __post_init__(self):
        """Validate configuration values."""
        if self.max_retries < 0:
            raise ValueError("max_retries must be positive")
        if self.retry_interval_seconds < 0:
            raise ValueError("retry_interval_seconds must be non-negative")


class AutoRecoveryManager:
    """Manages automatic service recovery."""

    def __init__(self, service_name: str, config: RecoveryConfig):
        """
        Initialize auto recovery manager.

        Args:
            service_name: Name of the service to manage
            config: Recovery configuration
        """
        self.service_name = service_name
        self.config = config
        self._restart_count = 0
        self._last_restart_time: Optional[datetime] = None

    def handle_anomaly(self) -> RecoveryAction:
        """
        Handle a detected anomaly.

        Returns:
            RecoveryAction indicating what action was taken

        Raises:
            MaxRetriesExceededError: If max retries exceeded
        """
        # Check if recovery is disabled
        if not self.config.enabled:
            return RecoveryAction.ALERT_ONLY

        # Check if max retries exceeded
        if self._restart_count >= self.config.max_retries:
            raise MaxRetriesExceededError(
                f"Maximum retries ({self.config.max_retries}) exceeded "
                f"for service: {self.service_name}"
            )

        # Check retry interval
        if self._last_restart_time is not None:
            time_since_last = datetime.now() - self._last_restart_time
            if time_since_last.total_seconds() < self.config.retry_interval_seconds:
                return RecoveryAction.WAIT

        # Perform restart
        self._restart_count += 1
        self._last_restart_time = datetime.now()

        return RecoveryAction.RESTART

    def get_restart_count(self) -> int:
        """
        Get the current restart count.

        Returns:
            Number of restarts performed
        """
        return self._restart_count

    def reset_on_success(self) -> None:
        """Reset restart counter after successful recovery."""
        self._restart_count = 0
        self._last_restart_time = None


class RecoveryHistory:
    """Tracks and persists recovery history."""

    def __init__(self, history_file: Path):
        """
        Initialize recovery history.

        Args:
            history_file: Path to history JSON file
        """
        self.history_file = history_file
        self._records: List[Dict] = []

        # Load existing history if file exists
        if self.history_file.exists():
            self._load_from_file()

    def record_restart(
        self,
        service_name: str,
        reason: str,
        action: RecoveryAction,
        timestamp: Optional[datetime] = None,
    ) -> None:
        """
        Record a restart event.

        Args:
            service_name: Name of the service
            reason: Reason for restart
            action: Action taken
            timestamp: Event timestamp (default: now)
        """
        if timestamp is None:
            timestamp = datetime.now()

        record = {
            "service_name": service_name,
            "reason": reason,
            "action": action.value,
            "timestamp": timestamp.isoformat(),
        }

        self._records.append(record)
        self._save_to_file()

    def get_records(self, service_name: str) -> List[Dict]:
        """
        Get all records for a specific service.

        Args:
            service_name: Name of the service

        Returns:
            List of restart records
        """
        return [record for record in self._records if record["service_name"] == service_name]

    def get_all_records(self) -> List[Dict]:
        """
        Get all restart records.

        Returns:
            List of all restart records
        """
        return self._records.copy()

    def get_restart_count(self, service_name: str) -> int:
        """
        Get total restart count for a service.

        Args:
            service_name: Name of the service

        Returns:
            Total number of restarts
        """
        return len(self.get_records(service_name))

    def get_recent_restarts(self, service_name: str, hours: int = 1) -> List[Dict]:
        """
        Get recent restarts within specified time window.

        Args:
            service_name: Name of the service
            hours: Number of hours to look back

        Returns:
            List of recent restart records
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        return [
            record
            for record in self.get_records(service_name)
            if datetime.fromisoformat(record["timestamp"]) >= cutoff_time
        ]

    def clear_old_records(self, retention_days: int = 30) -> None:
        """
        Remove records older than retention period.

        Args:
            retention_days: Number of days to retain records
        """
        cutoff_time = datetime.now() - timedelta(days=retention_days)

        self._records = [
            record
            for record in self._records
            if datetime.fromisoformat(record["timestamp"]) >= cutoff_time
        ]

        self._save_to_file()

    def _save_to_file(self) -> None:
        """Save records to file."""
        self.history_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.history_file, "w") as f:
            json.dump(self._records, f, indent=2)

    def _load_from_file(self) -> None:
        """Load records from file."""
        with open(self.history_file, "r") as f:
            self._records = json.load(f)
