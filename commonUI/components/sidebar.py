"""Sidebar components for CommonUI application."""

import streamlit as st

from components.http_client import HTTPClient
from components.notifications import NotificationManager
from core.config import config


class SidebarManager:
    """Manager for sidebar configuration and service switching."""

    @staticmethod
    def render_service_selector() -> str:
        """Render service selection in sidebar."""
        st.sidebar.header("🔧 Service Settings")

        service = st.sidebar.selectbox(
            "Select Service",
            ["JobQueue", "MyScheduler"],
            index=0 if config.ui.default_service == "JobQueue" else 1,
            help="Choose the service to manage"
        )

        return service

    @staticmethod
    def render_api_settings(service: str) -> None:
        """Render API configuration settings."""
        st.sidebar.subheader(f"{service} API")

        api_config = config.get_api_config(service)

        # Display current configuration
        st.sidebar.text_input(
            "Base URL",
            value=api_config.base_url,
            disabled=True,
            help="API base URL (configured via environment)"
        )

        # Masked token display
        masked_token = config.mask_token(api_config.token)
        st.sidebar.text_input(
            "API Token",
            value=masked_token,
            disabled=True,
            type="password",
            help="API authentication token (configured via environment)"
        )

        # Connection status check
        if st.sidebar.button(f"Test {service} Connection"):
            SidebarManager._test_connection(service, api_config)

    @staticmethod
    def _test_connection(service: str, api_config) -> None:
        """Test connection to the selected service."""
        try:
            with HTTPClient(api_config, service) as client:
                is_healthy = client.health_check()
                if is_healthy:
                    NotificationManager.connection_status(service, True)
                else:
                    NotificationManager.connection_status(service, False)
        except Exception as e:
            NotificationManager.handle_exception(e, f"{service} Connection Test")
            NotificationManager.connection_status(service, False)

    @staticmethod
    def render_ui_settings() -> dict:
        """Render UI configuration settings."""
        st.sidebar.subheader("⚙️ UI Settings")

        polling_interval = st.sidebar.slider(
            "Polling Interval (seconds)",
            min_value=1,
            max_value=30,
            value=config.ui.polling_interval,
            help="How often to refresh data from the API"
        )

        return {
            "polling_interval": polling_interval,
            "operation_mode": config.ui.operation_mode  # Use default from config
        }

    @staticmethod
    def render_system_info() -> None:
        """Render system information in sidebar."""
        st.sidebar.subheader("📊 System Info")

        # Service configuration status
        services_status = {}
        for service in ["JobQueue", "MyScheduler"]:
            is_configured = config.is_service_configured(service)
            services_status[service] = "✅" if is_configured else "❌"

        st.sidebar.write("**Service Configuration:**")
        for service, status in services_status.items():
            st.sidebar.write(f"{status} {service}")

        # Configuration warnings
        unconfigured_services = [
            service for service, status in services_status.items()
            if status == "❌"
        ]

        if unconfigured_services:
            st.sidebar.warning(
                f"⚠️ Configure: {', '.join(unconfigured_services)}\n\n"
                "Check your .env file or Streamlit secrets"
            )

    @staticmethod
    def render_complete_sidebar() -> tuple[str, dict]:
        """Render complete sidebar and return selected service and UI settings."""
        # UI settings
        ui_settings = SidebarManager.render_ui_settings()

        # Divider and app info
        st.sidebar.divider()
        st.sidebar.markdown(
            """
            **CommonUI v0.2.1**
            MySwiftAgent Management Interface

            📖 [Documentation](https://github.com/Kewton/MySwiftAgent)
            """
        )

        # Return default service from config
        selected_service = config.ui.default_service
        return selected_service, ui_settings