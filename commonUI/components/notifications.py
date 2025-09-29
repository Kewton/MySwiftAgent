"""Notification and toast management for CommonUI application."""

import logging
from typing import Optional

import streamlit as st

from core.exceptions import (
    APIError,
    AuthenticationError,
    CommonUIError,
    ConfigurationError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)

logger = logging.getLogger(__name__)


class NotificationManager:
    """Manager for displaying notifications and toasts in Streamlit."""

    @staticmethod
    def success(message: str, show_toast: bool = True) -> None:
        """Display success notification."""
        st.success(message)
        if show_toast:
            st.toast(message, icon="✅")
        logger.info(f"Success: {message}")

    @staticmethod
    def info(message: str, show_toast: bool = False) -> None:
        """Display info notification."""
        st.info(message)
        if show_toast:
            st.toast(message, icon="ℹ️")
        logger.info(f"Info: {message}")

    @staticmethod
    def warning(message: str, show_toast: bool = True) -> None:
        """Display warning notification."""
        st.warning(message)
        if show_toast:
            st.toast(message, icon="⚠️")
        logger.warning(f"Warning: {message}")

    @staticmethod
    def error(message: str, show_toast: bool = True) -> None:
        """Display error notification."""
        st.error(message)
        if show_toast:
            st.toast(message, icon="❌")
        logger.error(f"Error: {message}")

    @staticmethod
    def handle_exception(e: Exception, context: Optional[str] = None) -> None:
        """Handle and display exceptions with appropriate notifications."""
        context_prefix = f"[{context}] " if context else ""

        if isinstance(e, ServiceUnavailableError):
            message = f"{context_prefix}Service '{e.service_name}' is unavailable. Please check if it's running."
            NotificationManager.error(message)
        elif isinstance(e, AuthenticationError):
            message = f"{context_prefix}Authentication failed for '{e.service_name}'. Please check your API token."
            NotificationManager.error(message)
        elif isinstance(e, RateLimitError):
            retry_msg = f" Try again in {e.retry_after} seconds." if e.retry_after else ""
            message = f"{context_prefix}Rate limit exceeded.{retry_msg}"
            NotificationManager.warning(message)
        elif isinstance(e, ConfigurationError):
            message = f"{context_prefix}Configuration error: {e.message}"
            NotificationManager.error(message)
        elif isinstance(e, ValidationError):
            message = f"{context_prefix}Validation error: {e.message}"
            NotificationManager.warning(message)
        elif isinstance(e, APIError):
            message = f"{context_prefix}API Error: {e.message}"
            if e.status_code:
                message += f" (Status: {e.status_code})"
            NotificationManager.error(message)
        elif isinstance(e, CommonUIError):
            message = f"{context_prefix}{e.message}"
            NotificationManager.error(message)
        else:
            message = f"{context_prefix}Unexpected error: {str(e)}"
            NotificationManager.error(message)
            logger.exception("Unexpected error occurred")

    @staticmethod
    def progress_toast(message: str) -> None:
        """Display progress toast for ongoing operations."""
        st.toast(message, icon="🔄")
        logger.info(f"Progress: {message}")

    @staticmethod
    def operation_started(operation: str) -> None:
        """Notify that an operation has started."""
        message = f"{operation} started..."
        NotificationManager.progress_toast(message)

    @staticmethod
    def operation_completed(operation: str, duration: Optional[float] = None) -> None:
        """Notify that an operation has completed."""
        message = f"{operation} completed"
        if duration:
            message += f" ({duration:.2f}s)"
        NotificationManager.success(message, show_toast=True)

    @staticmethod
    def connection_status(service_name: str, is_connected: bool) -> None:
        """Display connection status for a service."""
        if is_connected:
            NotificationManager.success(f"✅ Connected to {service_name}", show_toast=False)
        else:
            NotificationManager.error(f"❌ Cannot connect to {service_name}", show_toast=False)