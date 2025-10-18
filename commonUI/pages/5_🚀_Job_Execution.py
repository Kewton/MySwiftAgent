"""
Job Execution History Page

Streamlit page for monitoring job execution history, viewing task details,
and managing failed task retries.
"""

import time
from datetime import datetime

import pandas as pd
import streamlit as st

from components.http_client import HTTPClient
from components.notifications import NotificationManager
from components.sidebar import SidebarManager
from core.config import config

# Page configuration
st.set_page_config(
    page_title="Job Execution - CommonUI",
    page_icon="🚀",
    layout="wide",
)


def initialize_session_state() -> None:
    """Initialize session state variables for Job Execution page."""
    if "job_exec_job_masters" not in st.session_state:
        st.session_state.job_exec_job_masters = []
    if "job_exec_selected_master_id" not in st.session_state:
        st.session_state.job_exec_selected_master_id = None
    if "job_exec_jobs" not in st.session_state:
        st.session_state.job_exec_jobs = []
    if "job_exec_selected_job_id" not in st.session_state:
        st.session_state.job_exec_selected_job_id = None
    if "job_exec_tasks" not in st.session_state:
        st.session_state.job_exec_tasks = []
    if "job_exec_auto_refresh" not in st.session_state:
        st.session_state.job_exec_auto_refresh = False


def load_job_masters() -> None:
    """Load JobMasters from API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            response = client.get(
                "/api/v1/job-masters", params={"page": 1, "size": 100},
            )
            job_masters = response.get("masters", [])
            st.session_state.job_exec_job_masters = job_masters

    except Exception as e:
        NotificationManager.handle_exception(e, "Load JobMasters")
        st.session_state.job_exec_job_masters = []


def load_jobs_by_master(master_id: str, page: int = 1, size: int = 20) -> None:
    """Load Jobs from JobMaster."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            response = client.get(
                f"/api/v1/job-masters/{master_id}/jobs",
                params={"page": page, "size": size},
            )
            jobs = response.get("jobs", [])
            st.session_state.job_exec_jobs = jobs

    except Exception as e:
        NotificationManager.handle_exception(e, "Load Jobs")
        st.session_state.job_exec_jobs = []


def load_job_tasks(job_id: str) -> None:
    """Load Tasks for a Job."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            response = client.get(f"/api/v1/jobs/{job_id}/tasks")
            tasks = response.get("tasks", [])
            st.session_state.job_exec_tasks = tasks

    except Exception as e:
        NotificationManager.handle_exception(e, "Load Tasks")
        st.session_state.job_exec_tasks = []


def retry_task(task_id: str) -> None:
    """Retry a failed task."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            NotificationManager.operation_started("Retrying task")

            response = client.post(f"/api/v1/tasks/{task_id}/retry")

            NotificationManager.operation_completed("Task retry")
            NotificationManager.success(
                f"Task retry initiated: {response.get('message')}",
            )

            # Reload tasks
            if st.session_state.job_exec_selected_job_id:
                load_job_tasks(st.session_state.job_exec_selected_job_id)

            time.sleep(1)
            st.rerun()

    except Exception as e:
        NotificationManager.handle_exception(e, "Task Retry")


def get_status_icon(status: str) -> str:
    """Get status icon for display."""
    status_icons = {
        "queued": "⏳",
        "running": "🔄",
        "succeeded": "✓",
        "failed": "✗",
        "skipped": "⏭",
        "canceled": "⏹",
    }
    return status_icons.get(status.lower(), "❓")


def get_status_color(status: str) -> str:
    """Get status color for display."""
    status_colors = {
        "queued": "#FFA500",  # Orange
        "running": "#1E90FF",  # Blue
        "succeeded": "#28A745",  # Green
        "failed": "#DC3545",  # Red
        "skipped": "#6C757D",  # Gray
        "canceled": "#6C757D",  # Gray
    }
    return status_colors.get(status.lower(), "#000000")


def render_job_master_selector() -> None:
    """Render JobMaster selection UI."""
    st.subheader("📂 Select JobMaster")

    # Load JobMasters if not loaded
    if not st.session_state.job_exec_job_masters:
        load_job_masters()

    job_masters = st.session_state.job_exec_job_masters

    if not job_masters:
        st.warning("No JobMasters found. Please create a JobMaster first.")
        return

    # Create options for selectbox
    master_options = {
        f"{master['name']} ({master['id']})": master["id"] for master in job_masters
    }

    # Get current selection index
    current_master_id = st.session_state.job_exec_selected_master_id
    current_index = 0
    if current_master_id:
        for i, master_id in enumerate(master_options.values()):
            if master_id == current_master_id:
                current_index = i
                break

    selected_master_name = st.selectbox(
        "JobMaster",
        options=list(master_options.keys()),
        index=current_index,
        help="Select a JobMaster to view its execution history",
    )

    selected_master_id = master_options[selected_master_name]

    # Update session state if selection changed
    if selected_master_id != st.session_state.job_exec_selected_master_id:
        st.session_state.job_exec_selected_master_id = selected_master_id
        st.session_state.job_exec_selected_job_id = None  # Reset job selection
        load_jobs_by_master(selected_master_id)
        st.rerun()


def render_job_list() -> None:
    """Render Job execution history list."""
    if not st.session_state.job_exec_selected_master_id:
        st.info("Please select a JobMaster above to view execution history.")
        return

    st.subheader("📋 Job Execution History")

    # Filters
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        status_filter = st.selectbox(
            "Status Filter",
            ["All", "queued", "running", "succeeded", "failed", "canceled"],
            help="Filter jobs by status",
        )

    with col2:
        search_query = st.text_input(
            "Search",
            placeholder="Search by Job name or ID",
            help="Search jobs by name or ID",
        )

    with col3:
        auto_refresh = st.checkbox(
            "Auto Refresh",
            value=st.session_state.job_exec_auto_refresh,
            help="Automatically refresh job list",
        )
        st.session_state.job_exec_auto_refresh = auto_refresh

    with col4:
        if st.button("🔄 Refresh", use_container_width=True):
            load_jobs_by_master(st.session_state.job_exec_selected_master_id)
            st.rerun()

    # Load jobs if not loaded
    if not st.session_state.job_exec_jobs:
        load_jobs_by_master(st.session_state.job_exec_selected_master_id)

    jobs = st.session_state.job_exec_jobs

    if not jobs:
        st.info("No jobs found for this JobMaster.")
        return

    # Filter jobs
    filtered_jobs = jobs
    if status_filter != "All":
        filtered_jobs = [
            job for job in filtered_jobs if job.get("status") == status_filter
        ]

    if search_query:
        query_lower = search_query.lower()
        filtered_jobs = [
            job
            for job in filtered_jobs
            if (
                query_lower in job.get("name", "").lower()
                or query_lower in str(job.get("id", ""))
            )
        ]

    if not filtered_jobs:
        st.warning("No jobs match the current filters.")
        return

    # Prepare data for display
    display_data = []
    for job in filtered_jobs:
        # Calculate task progress
        tasks_count = len(job.get("tasks", []))
        succeeded_tasks = sum(
            1 for task in job.get("tasks", []) if task.get("status") == "succeeded"
        )
        progress = f"{succeeded_tasks}/{tasks_count}" if tasks_count > 0 else "0/0"

        # Calculate duration
        created_at = job.get("created_at")
        finished_at = job.get("finished_at")
        duration = calculate_duration(created_at, finished_at)

        display_data.append(
            {
                "id": job.get("id"),
                "name": job.get("name", "Unnamed"),
                "status": job.get("status"),
                "progress": progress,
                "created_at": created_at,
                "duration": duration,
            },
        )

    # Convert to DataFrame
    df = pd.DataFrame(display_data)

    # Display as interactive table
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "id": "Job ID",
            "name": "Name",
            "status": st.column_config.TextColumn("Status"),
            "progress": "Task Progress",
            "created_at": st.column_config.DatetimeColumn("Created At"),
            "duration": "Duration",
        },
    )

    # Handle row selection
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_job = filtered_jobs[selected_idx]
        st.session_state.job_exec_selected_job_id = selected_job["id"]
        load_job_tasks(selected_job["id"])
        st.rerun()


def render_job_detail() -> None:
    """Render detailed Job information with Task execution timeline."""
    job_id = st.session_state.job_exec_selected_job_id

    if not job_id:
        st.info("Select a job from the list above to view details.")
        return

    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            job_detail = client.get(f"/api/v1/jobs/{job_id}")

            st.divider()
            st.subheader(f"📄 Job Details - {job_detail.get('name', job_id)}")

            # Job information
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                status = job_detail.get("status", "unknown")
                status_icon = get_status_icon(status)
                st.metric("Status", f"{status_icon} {status.upper()}")

            with col2:
                created_at = job_detail.get("created_at", "Unknown")
                st.metric("Created At", format_datetime(created_at))

            with col3:
                started_at = job_detail.get("started_at")
                st.metric(
                    "Started At",
                    format_datetime(started_at) if started_at else "Not started",
                )

            with col4:
                finished_at = job_detail.get("finished_at")
                duration = calculate_duration(job_detail.get("created_at"), finished_at)
                st.metric("Duration", duration)

            # Task Execution Timeline
            st.divider()
            st.subheader("📊 Task Execution Timeline")

            tasks = st.session_state.job_exec_tasks

            if not tasks:
                st.info("No tasks found for this job.")
                return

            # Display tasks as table
            task_data = []
            for task in tasks:
                task_status = task.get("status", "unknown")
                status_icon = get_status_icon(task_status)

                task_data.append(
                    {
                        "Order": task.get("order", 0),
                        "Task Name": task.get("master_id", "Unknown")[
                            :20
                        ],  # Truncate long IDs
                        "Status": f"{status_icon} {task_status.upper()}",
                        "Duration": format_duration_ms(task.get("duration_ms")),
                        "Attempt": task.get("attempt", 0),
                        "task_id": task.get("id"),  # Hidden column for actions
                        "full_status": task_status,  # Hidden column for styling
                    },
                )

            # Create DataFrame
            task_df = pd.DataFrame(task_data)

            # Display table with conditional formatting
            st.dataframe(
                task_df.drop(columns=["task_id", "full_status"]),
                use_container_width=True,
                hide_index=True,
            )

            # Task Details Section
            st.divider()
            st.subheader("🔍 Task Details")

            for i, task in enumerate(tasks):
                task_status = task.get("status", "unknown")
                task_name = task.get("master_id", "Unknown Task")
                order = task.get("order", i)

                # Highlight failed tasks
                is_failed = task_status.lower() == "failed"
                expander_label = f"Task {order}: {task_name} - {get_status_icon(task_status)} {task_status.upper()}"

                with st.expander(expander_label, expanded=is_failed):
                    # Task information
                    task_col1, task_col2 = st.columns(2)

                    with task_col1:
                        st.write("**Task ID:**", task.get("id", "N/A"))
                        st.write("**Master ID:**", task.get("master_id", "N/A"))
                        st.write(
                            "**Master Version:**", task.get("master_version", "N/A"),
                        )
                        st.write("**Attempt:**", task.get("attempt", 0))

                    with task_col2:
                        st.write(
                            "**Started At:**", format_datetime(task.get("started_at")),
                        )
                        st.write(
                            "**Finished At:**", format_datetime(task.get("finished_at")),
                        )
                        st.write(
                            "**Duration:**", format_duration_ms(task.get("duration_ms")),
                        )

                    # Input Data
                    st.write("**▼ Input Data**")
                    input_data = task.get("input_data")
                    if input_data:
                        st.json(input_data)
                    else:
                        st.write("_No input data_")

                    # Output Data
                    st.write("**▼ Output Data**")
                    output_data = task.get("output_data")
                    if output_data:
                        st.json(output_data)
                    else:
                        st.write("_No output data_")

                    # Error
                    error = task.get("error")
                    if error:
                        st.error(f"**Error:** {error}")

                    # Retry button for failed tasks
                    if is_failed:
                        if st.button(
                            "🔄 Retry from this Task",
                            key=f"retry_{task.get('id')}",
                            use_container_width=True,
                        ):
                            retry_task(task.get("id"))

    except Exception as e:
        NotificationManager.handle_exception(e, "Job Detail")


def calculate_duration(start_time: str | None, end_time: str | None) -> str:
    """Calculate duration between two timestamps."""
    if not start_time or not end_time:
        return "N/A"

    try:
        start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
        end = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        duration = end - start
        total_seconds = int(duration.total_seconds())

        if total_seconds < 60:
            return f"{total_seconds}s"
        if total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}m {seconds}s"

        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}h {minutes}m"

    except Exception:
        return "N/A"


def format_datetime(timestamp: str | None) -> str:
    """Format timestamp for display."""
    if not timestamp:
        return "N/A"

    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return timestamp


def format_duration_ms(duration_ms: int | None) -> str:
    """Format duration in milliseconds for display."""
    if duration_ms is None:
        return "N/A"

    if duration_ms < 1000:
        return f"{duration_ms}ms"
    if duration_ms < 60000:
        seconds = duration_ms / 1000
        return f"{seconds:.2f}s"

    minutes = duration_ms // 60000
    seconds = (duration_ms % 60000) / 1000
    return f"{minutes}m {seconds:.1f}s"


def main() -> None:
    """Main Job Execution page function."""
    # Initialize session state
    initialize_session_state()

    # Render sidebar
    _selected_service, ui_settings = SidebarManager.render_complete_sidebar()

    # Page header
    st.title("🚀 Job Execution History")
    st.caption("Monitor job execution history and manage task retries")

    # Check if service is configured
    if not config.is_service_configured("JobQueue"):
        st.error(
            "❌ JobQueue is not configured. Please check your environment settings.",
        )
        st.stop()

    # Main content
    render_job_master_selector()

    st.divider()

    render_job_list()

    render_job_detail()

    # Auto-refresh functionality
    if st.session_state.job_exec_auto_refresh:
        polling_interval = ui_settings.get("polling_interval", 5)
        time.sleep(polling_interval)
        st.rerun()


if __name__ == "__main__":
    main()
