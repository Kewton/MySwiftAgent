"""
JobQueue Management Page

Streamlit page for managing job queue operations including job creation,
monitoring, and execution control.
"""

import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from components.http_client import HTTPClient
from components.notifications import NotificationManager
from components.sidebar import SidebarManager
from core.config import config

# Page configuration
st.set_page_config(
    page_title="JobQueue - CommonUI",
    page_icon="📋",
    layout="wide"
)


def initialize_session_state() -> None:
    """Initialize session state variables for JobQueue page."""
    if "jobqueue_jobs" not in st.session_state:
        st.session_state.jobqueue_jobs = []
    if "jobqueue_selected_job" not in st.session_state:
        st.session_state.jobqueue_selected_job = None
    if "jobqueue_auto_refresh" not in st.session_state:
        st.session_state.jobqueue_auto_refresh = False


def render_job_creation_form() -> None:
    """Render job creation form."""
    st.subheader("🆕 Create New Job")

    with st.form("job_creation_form"):
        col1, col2 = st.columns(2)

        with col1:
            job_name = st.text_input(
                "Job Name*",
                placeholder="Enter job name",
                help="Unique identifier for the job"
            )

            job_type = st.selectbox(
                "Job Type*",
                ["data_processing", "batch_analysis", "file_conversion", "api_sync", "custom"],
                help="Select the type of job to execute"
            )

            priority = st.selectbox(
                "Priority",
                ["low", "normal", "high", "urgent"],
                index=1,
                help="Job execution priority"
            )

        with col2:
            max_retries = st.number_input(
                "Max Retries",
                min_value=0,
                max_value=10,
                value=3,
                help="Maximum number of retry attempts"
            )

            timeout = st.number_input(
                "Timeout (seconds)",
                min_value=10,
                max_value=3600,
                value=300,
                help="Job execution timeout"
            )

        # Job parameters
        st.subheader("Job Parameters")
        parameters = st.text_area(
            "Parameters (JSON)",
            placeholder='{"key": "value", "input_file": "/path/to/file"}',
            help="Job parameters in JSON format"
        )

        # Tags
        tags = st.text_input(
            "Tags (comma-separated)",
            placeholder="tag1, tag2, tag3",
            help="Optional tags for job categorization"
        )

        submitted = st.form_submit_button(
            "🚀 Create Job",
            type="primary",
            use_container_width=True
        )

        if submitted:
            if not job_name:
                st.error("Job name is required")
                return

            try:
                # Parse parameters
                import json
                job_params = json.loads(parameters) if parameters.strip() else {}

                # Parse tags
                job_tags = [tag.strip() for tag in tags.split(",") if tag.strip()] if tags else []

                # Create job data
                job_data = {
                    "name": job_name,
                    "type": job_type,
                    "priority": priority,
                    "max_retries": max_retries,
                    "timeout": timeout,
                    "parameters": job_params,
                    "tags": job_tags
                }

                create_job(job_data)

            except json.JSONDecodeError:
                st.error("Invalid JSON in parameters field")
            except Exception as e:
                NotificationManager.handle_exception(e, "Job Creation")


def create_job(job_data: Dict[str, Any]) -> None:
    """Create a new job via API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            NotificationManager.operation_started("Creating job")

            response = client.post("/api/v1/jobs", job_data)

            job_id = response.get("job_id")
            NotificationManager.operation_completed("Job creation")
            NotificationManager.success(f"Job created successfully! ID: {job_id}")

            # Refresh job list
            load_jobs()

            # Switch to job detail view
            st.session_state.jobqueue_selected_job = job_id

    except Exception as e:
        NotificationManager.handle_exception(e, "Job Creation")


def render_job_list() -> None:
    """Render job list with filtering and search."""
    st.subheader("📋 Job List")

    # Filters
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        status_filter = st.selectbox(
            "Status Filter",
            ["All", "pending", "running", "completed", "failed", "cancelled"],
            help="Filter jobs by status"
        )

    with col2:
        priority_filter = st.selectbox(
            "Priority Filter",
            ["All", "low", "normal", "high", "urgent"],
            help="Filter jobs by priority"
        )

    with col3:
        search_query = st.text_input(
            "Search Jobs",
            placeholder="Search by name or ID",
            help="Search jobs by name or job ID"
        )

    with col4:
        auto_refresh = st.checkbox(
            "Auto Refresh",
            value=st.session_state.jobqueue_auto_refresh,
            help="Automatically refresh job list"
        )
        st.session_state.jobqueue_auto_refresh = auto_refresh

    # Refresh button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refresh", use_container_width=True):
            load_jobs()

    # Display jobs
    jobs = st.session_state.jobqueue_jobs
    if not jobs:
        st.info("No jobs found. Create your first job using the form above.")
        return

    # Filter jobs
    filtered_jobs = filter_jobs(jobs, status_filter, priority_filter, search_query)

    if not filtered_jobs:
        st.warning("No jobs match the current filters.")
        return

    # Convert to DataFrame for better display
    df = pd.DataFrame(filtered_jobs)

    # Display as interactive table
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "job_id": "Job ID",
            "name": "Name",
            "status": st.column_config.SelectboxColumn(
                "Status",
                options=["pending", "running", "completed", "failed", "cancelled"],
            ),
            "priority": st.column_config.SelectboxColumn(
                "Priority",
                options=["low", "normal", "high", "urgent"],
            ),
            "created_at": st.column_config.DatetimeColumn("Created"),
            "updated_at": st.column_config.DatetimeColumn("Updated"),
        }
    )

    # Handle row selection
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_job = filtered_jobs[selected_idx]
        st.session_state.jobqueue_selected_job = selected_job["job_id"]


def filter_jobs(jobs: List[Dict], status_filter: str, priority_filter: str, search_query: str) -> List[Dict]:
    """Filter jobs based on criteria."""
    filtered = jobs

    # Status filter
    if status_filter != "All":
        filtered = [job for job in filtered if job.get("status") == status_filter]

    # Priority filter
    if priority_filter != "All":
        filtered = [job for job in filtered if job.get("priority") == priority_filter]

    # Search filter
    if search_query:
        query_lower = search_query.lower()
        filtered = [
            job for job in filtered
            if (query_lower in job.get("name", "").lower() or
                query_lower in str(job.get("job_id", "")))
        ]

    return filtered


def render_job_detail() -> None:
    """Render detailed job information and controls."""
    job_id = st.session_state.jobqueue_selected_job
    if not job_id:
        st.info("Select a job from the list above to view details.")
        return

    st.subheader(f"📄 Job Details - {job_id}")

    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            job_detail = client.get(f"/api/v1/jobs/{job_id}")

            # Job information
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Status", job_detail.get("status", "Unknown"))
                st.metric("Priority", job_detail.get("priority", "Unknown"))

            with col2:
                st.metric("Progress", f"{job_detail.get('progress', 0)}%")
                st.metric("Retries", f"{job_detail.get('retry_count', 0)}/{job_detail.get('max_retries', 0)}")

            with col3:
                created_at = job_detail.get("created_at", "Unknown")
                st.metric("Created", created_at)
                duration = calculate_duration(job_detail)
                st.metric("Duration", duration)

            # Job controls
            st.subheader("🎛️ Job Controls")
            col1, col2, col3, col4 = st.columns(4)

            current_status = job_detail.get("status")

            with col1:
                if current_status in ["pending", "failed"] and st.button("▶️ Start", use_container_width=True):
                    control_job(job_id, "start")

            with col2:
                if current_status == "running" and st.button("⏸️ Pause", use_container_width=True):
                    control_job(job_id, "pause")

            with col3:
                if current_status in ["running", "pending"] and st.button("⏹️ Cancel", use_container_width=True):
                    control_job(job_id, "cancel")

            with col4:
                if current_status == "failed" and st.button("🔄 Retry", use_container_width=True):
                    control_job(job_id, "retry")

            # Job details tabs
            tab1, tab2, tab3, tab4 = st.tabs(["📋 Definition", "📊 Results", "📝 Logs", "⚙️ Parameters"])

            with tab1:
                st.json(job_detail, expanded=False)

            with tab2:
                results = job_detail.get("results", {})
                if results:
                    st.json(results)
                else:
                    st.info("No results available yet.")

            with tab3:
                logs = job_detail.get("logs", [])
                if logs:
                    for log_entry in logs:
                        timestamp = log_entry.get("timestamp", "")
                        level = log_entry.get("level", "INFO")
                        message = log_entry.get("message", "")
                        st.text(f"[{timestamp}] {level}: {message}")
                else:
                    st.info("No logs available.")

            with tab4:
                parameters = job_detail.get("parameters", {})
                if parameters:
                    st.json(parameters)
                else:
                    st.info("No parameters specified.")

    except Exception as e:
        NotificationManager.handle_exception(e, "Job Detail")


def calculate_duration(job_detail: Dict) -> str:
    """Calculate job duration."""
    try:
        created_at = job_detail.get("created_at")
        updated_at = job_detail.get("updated_at")

        if created_at and updated_at:
            # Parse timestamps (assuming ISO format)
            from datetime import datetime
            start = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            duration = end - start
            total_seconds = int(duration.total_seconds())

            if total_seconds < 60:
                return f"{total_seconds}s"
            elif total_seconds < 3600:
                return f"{total_seconds // 60}m {total_seconds % 60}s"
            else:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                return f"{hours}h {minutes}m"

        return "N/A"
    except Exception:
        return "N/A"


def control_job(job_id: str, action: str) -> None:
    """Control job execution (start, pause, cancel, retry)."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            NotificationManager.operation_started(f"Job {action}")

            response = client.post(f"/api/v1/jobs/{job_id}/{action}")

            NotificationManager.operation_completed(f"Job {action}")
            NotificationManager.success(f"Job {action} executed successfully!")

            # Refresh job detail
            time.sleep(1)  # Brief delay for status update
            st.rerun()

    except Exception as e:
        NotificationManager.handle_exception(e, f"Job {action}")


def load_jobs() -> None:
    """Load jobs from API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            response = client.get("/api/v1/jobs")
            st.session_state.jobqueue_jobs = response.get("jobs", [])

    except Exception as e:
        NotificationManager.handle_exception(e, "Load Jobs")
        st.session_state.jobqueue_jobs = []


def main() -> None:
    """Main JobQueue page function."""
    # Initialize session state
    initialize_session_state()

    # Render sidebar
    selected_service, ui_settings = SidebarManager.render_complete_sidebar()

    # Page header
    st.title("📋 JobQueue Management")

    # Check if service is configured
    if not config.is_service_configured("JobQueue"):
        st.error("❌ JobQueue is not configured. Please check your environment settings.")
        st.stop()

    # Load initial data
    if not st.session_state.jobqueue_jobs:
        load_jobs()

    # Main content tabs
    tab1, tab2 = st.tabs(["🆕 Create Job", "📋 Job List"])

    with tab1:
        render_job_creation_form()

    with tab2:
        render_job_list()
        st.divider()
        render_job_detail()

    # Auto-refresh functionality
    if st.session_state.jobqueue_auto_refresh:
        polling_interval = ui_settings.get("polling_interval", 5)
        time.sleep(polling_interval)
        st.rerun()


if __name__ == "__main__":
    main()