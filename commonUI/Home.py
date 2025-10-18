"""
CommonUI - MySwiftAgent Management Interface

Streamlit multi-page application for managing JobQueue and MyScheduler services.
"""

import logging
import sys
from pathlib import Path

import streamlit as st

from components.http_client import HTTPClient
from components.notifications import NotificationManager
from components.sidebar import SidebarManager
from core.config import config

# Configure logging
log_dir = Path(config.log_dir)
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "app.log"

logging.basicConfig(
    level=getattr(logging, config.log_level.upper(), logging.INFO),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, mode="a", encoding="utf-8"),
    ],
    force=True,  # Force reconfiguration even if logging was already configured
)

logger = logging.getLogger(__name__)
logger.info(
    "Logging configured (dir=%s, level=%s)",
    log_dir,
    config.log_level,
)

# Page configuration
st.set_page_config(
    page_title="CommonUI - MySwiftAgent",
    page_icon="🎨",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/Kewton/MySwiftAgent/issues",
        "Report a bug": "https://github.com/Kewton/MySwiftAgent/issues",
        "About": "CommonUI v0.1.0 - MySwiftAgent Management Interface",
    },
)


def render_welcome_section() -> None:
    """Render welcome section with overview."""
    st.title("🎨 CommonUI")
    st.subheader("MySwiftAgent Management Interface")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="🚀 Streamlit",
            value="Multi-Page",
            help="High-performance web interface",
        )

    with col2:
        st.metric(
            label="🔄 Services",
            value="3 Available",
            help="JobQueue, MyScheduler, and Job Masters management",
        )

    with col3:
        st.metric(
            label="🛡️ Features",
            value="Full Stack",
            help="Error handling, retries, notifications",
        )


def render_service_overview() -> None:
    """Render overview of available services."""
    st.header("📋 Available Services")

    col1, col2 = st.columns(2)

    with col1, st.container(border=True):
        st.subheader("📋 JobQueue")
        st.write("""
            **Job Queue Management System**

            Features:
            - ✅ Create and submit jobs
            - 📊 Monitor job status and progress
            - 🔄 View execution results
            - ⏹️ Cancel running jobs
            - 🔍 Search and filter job history
            - 🗂️ Manage job master templates
            """)

        if config.is_service_configured("JobQueue"):
            st.success("✅ Configured and ready")
        else:
            st.error("❌ Not configured")

        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("Open JobQueue", key="btn_jobqueue", use_container_width=True):
                st.switch_page("pages/1_📋_JobQueue.py")
        with col_btn2:
            if st.button("Job Masters", key="btn_jobmasters", use_container_width=True):
                st.switch_page("pages/4_🗂️_JobMasters.py")

    with col2, st.container(border=True):
        st.subheader("⏰ MyScheduler")
        st.write("""
            **Job Scheduling System**

            Features:
            - ⏰ Create cron, interval, and date-based schedules
            - 📅 View upcoming job executions
            - ▶️ Start, stop, and pause schedulers
            - 📊 Monitor scheduler health and status
            - 🔧 Manage job definitions
            """)

        if config.is_service_configured("MyScheduler"):
            st.success("✅ Configured and ready")
        else:
            st.error("❌ Not configured")

        if st.button(
            "Open MyScheduler",
            key="btn_myscheduler",
            use_container_width=True,
        ):
            st.switch_page("pages/2_⏰_MyScheduler.py")


def render_system_status() -> None:
    """Render system status and configuration info."""
    st.header("🔧 System Status")

    # Configuration status
    with st.expander("📋 Configuration Status", expanded=False):
        services = ["JobQueue", "MyScheduler"]
        for service in services:
            is_configured = config.is_service_configured(service)
            status_icon = "✅" if is_configured else "❌"
            status_text = "Configured" if is_configured else "Not Configured"

            col1, col2 = st.columns([1, 3])
            with col1:
                st.write(f"{status_icon} **{service}**")
            with col2:
                st.write(f"{status_text}")
                if is_configured:
                    api_config = config.get_api_config(service)
                    st.caption(f"URL: {api_config.base_url}")

    # Quick setup guide
    with st.expander("🚀 Quick Setup Guide", expanded=False):
        st.markdown("""
        ### Environment Setup

        1. **Copy environment template:**
        ```bash
        cp .env.example .env
        ```

        2. **Configure API endpoints:**
        ```bash
        # JobQueue API
        JOBQUEUE_BASE_URL=http://localhost:8001
        JOBQUEUE_API_TOKEN=your-jobqueue-token

        # MyScheduler API
        MYSCHEDULER_BASE_URL=http://localhost:8002
        MYSCHEDULER_API_TOKEN=your-myscheduler-token
        ```

        3. **Start services:**
        ```bash
        # Run the startup script
        ./scripts/start_services.sh
        ```

        4. **Launch CommonUI:**
        ```bash
        uv run streamlit run Home.py
        ```
        """)


def render_footer() -> None:
    """Render footer with links and information."""
    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**🔗 Links**")
        st.markdown("- [GitHub Repository](https://github.com/Kewton/MySwiftAgent)")
        st.markdown(
            "- [Documentation](https://github.com/Kewton/MySwiftAgent/blob/main/commonUI/README.md)",
        )

    with col2:
        st.markdown("**📞 Support**")
        st.markdown("- [Issues](https://github.com/Kewton/MySwiftAgent/issues)")
        st.markdown(
            "- [Feature Requests](https://github.com/Kewton/MySwiftAgent/issues/new)",
        )

    with col3:
        st.markdown("**ℹ️ Version**")
        st.markdown("- CommonUI v0.1.0")
        st.markdown("- MySwiftAgent Framework")


def main() -> None:
    """Main application entry point."""
    try:
        # Handle OAuth2 callback if present (Google redirects to home page)
        query_params = st.query_params
        if "code" in query_params and "state" in query_params:
            st.info("🔄 Processing Google OAuth2 callback...")
            try:
                api_config = config.get_api_config("expertagent")
                with HTTPClient(api_config, "ExpertAgent") as client:
                    callback_data = {
                        "state": query_params["state"],
                        "code": query_params["code"],
                        "project": None,  # expertAgent will use stored value
                    }
                    response = client.post(
                        "/v1/google-auth/oauth2-callback",
                        callback_data,
                    )
                    project = response.get("project", "default_project")

                st.success(
                    f"✅ Google authentication successful for project: {project}",
                )
                st.info("✅ Token saved to MyVault")
                st.info("📍 Navigate to 🔐 MyVault → Google認証 tab to verify")

                # Clear query params
                st.query_params.clear()
                st.balloons()
            except Exception as e:
                st.error(f"❌ OAuth2 callback failed: {e}")
                st.query_params.clear()

        # Render sidebar
        selected_service, ui_settings = SidebarManager.render_complete_sidebar()

        # Store UI settings in session state for other pages
        st.session_state.ui_settings = ui_settings
        st.session_state.selected_service = selected_service

        # Main content area
        render_welcome_section()

        st.divider()

        render_service_overview()

        st.divider()

        render_system_status()

        render_footer()

        # Show initial configuration warning if needed
        unconfigured = [
            service
            for service in ["JobQueue", "MyScheduler"]
            if not config.is_service_configured(service)
        ]

        if unconfigured:
            services_text = "services are" if len(unconfigured) > 1 else "service is"
            st.warning(
                f"⚠️ **Configuration Required**: {', '.join(unconfigured)} "
                f"{services_text} not configured. "
                "Please check the Quick Setup Guide above.",
            )

    except Exception as e:
        NotificationManager.handle_exception(e, "Home Page")
        st.error(
            "An error occurred while loading the application. "
            "Please check the configuration.",
        )


if __name__ == "__main__":
    main()
