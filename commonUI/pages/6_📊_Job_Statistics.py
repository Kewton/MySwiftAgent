"""
Job Master Statistics Page

Streamlit page for displaying JobMaster execution statistics and KPIs.
"""

import pandas as pd  # type: ignore[import-untyped]
import streamlit as st

from components.http_client import HTTPClient
from components.notifications import NotificationManager
from components.sidebar import SidebarManager
from core.config import config

# Page configuration
st.set_page_config(
    page_title="Job Statistics - CommonUI",
    page_icon="📊",
    layout="wide",
)


def initialize_session_state() -> None:
    """Initialize session state variables for Job Statistics page."""
    if "stats_job_masters_list" not in st.session_state:
        st.session_state.stats_job_masters_list = []
    if "selected_stats_master_id" not in st.session_state:
        st.session_state.selected_stats_master_id = None
    if "master_stats" not in st.session_state:
        st.session_state.master_stats = None


def load_job_masters() -> None:
    """Load job masters from API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            response = client.get("/api/v1/job-masters", params={"size": 100})
            st.session_state.stats_job_masters_list = response.get("masters", [])

    except Exception as e:
        NotificationManager.handle_exception(e, "Load Job Masters")
        st.session_state.stats_job_masters_list = []


def load_master_stats(master_id: str) -> None:
    """Load master statistics from API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            stats = client.get(f"/api/v1/job-masters/{master_id}/stats")
            st.session_state.master_stats = stats

    except Exception as e:
        NotificationManager.handle_exception(e, "Load Master Statistics")
        st.session_state.master_stats = None


def get_success_rate_color(success_rate: float) -> str:
    """Get color based on success rate."""
    if success_rate >= 95:
        return "green"
    if success_rate >= 80:
        return "normal"
    if success_rate >= 50:
        return "orange"
    return "red"


def render_job_master_selector() -> None:
    """Render JobMaster selection UI."""
    st.subheader("📂 Select JobMaster")

    masters = st.session_state.stats_job_masters_list
    if not masters:
        st.info("No job masters available. Please create a JobMaster first.")
        return

    # Filter active masters only
    active_masters = [m for m in masters if m.get("is_active")]
    if not active_masters:
        st.info("No active job masters available.")
        return

    # Create dropdown options
    master_options = {f"{m['name']} ({m['id']})": m["id"] for m in active_masters}

    # Add "Select..." option
    options_list = ["Select a JobMaster...", *master_options.keys()]

    # Get current selection index
    current_index = 0
    if st.session_state.selected_stats_master_id:
        for idx, option in enumerate(options_list[1:], 1):
            if master_options[option] == st.session_state.selected_stats_master_id:
                current_index = idx
                break

    selected_option = st.selectbox(
        "Select JobMaster",
        options=options_list,
        index=current_index,
        key="stats_master_selector",
        label_visibility="collapsed",
    )

    if selected_option and selected_option != "Select a JobMaster...":
        master_id = master_options[selected_option]
        if master_id != st.session_state.selected_stats_master_id:
            st.session_state.selected_stats_master_id = master_id
            load_master_stats(master_id)
            st.rerun()


def render_overall_statistics() -> None:
    """Render overall statistics section."""
    stats = st.session_state.master_stats
    if not stats:
        return

    st.subheader("📊 Overall Statistics")

    # Metrics row
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Executions",
            stats.get("total_executions", 0),
            help="Total number of Job executions from this master",
        )

    with col2:
        success_count = stats.get("success_count", 0)
        total = stats.get("total_executions", 0)
        success_pct = f"{(success_count / total * 100):.1f}%" if total > 0 else "N/A"
        st.metric(
            "Success",
            success_count,
            delta=success_pct,
            delta_color="off",
            help="Number and percentage of successful executions",
        )

    with col3:
        failure_count = stats.get("failure_count", 0)
        failure_pct = f"{(failure_count / total * 100):.1f}%" if total > 0 else "N/A"
        st.metric(
            "Failed",
            failure_count,
            delta=failure_pct,
            delta_color="off",
            help="Number and percentage of failed executions",
        )

    with col4:
        canceled_count = stats.get("canceled_count", 0)
        canceled_pct = f"{(canceled_count / total * 100):.1f}%" if total > 0 else "N/A"
        st.metric(
            "Canceled",
            canceled_count,
            delta=canceled_pct,
            delta_color="off",
            help="Number and percentage of canceled executions",
        )

    # Success rate gauge
    st.divider()
    col1, col2 = st.columns([2, 3])

    with col1:
        success_rate = stats.get("success_rate", 0.0)
        st.metric(
            "Success Rate",
            f"{success_rate:.2f}%",
            help="Percentage of successful executions",
        )

        # Visual gauge using progress bar
        normalized_rate = success_rate / 100.0
        color = get_success_rate_color(success_rate)

        if color == "green":
            st.success("🎉 Excellent success rate!")
        elif color == "normal":
            st.info("✅ Good success rate")
        elif color == "orange":
            st.warning("⚠️ Moderate success rate - consider improvements")
        else:
            st.error("❌ Low success rate - needs immediate attention")

        st.progress(normalized_rate, text=f"{success_rate:.1f}% Success Rate")

    with col2:
        last_executed = stats.get("last_executed_at")
        if last_executed:
            st.metric(
                "Last Executed",
                last_executed.split("T")[0] if "T" in last_executed else last_executed,
                help="Most recent execution timestamp",
            )
        else:
            st.info("No executions yet")


def render_task_statistics() -> None:
    """Render task-level statistics table."""
    stats = st.session_state.master_stats
    if not stats:
        return

    task_stats = stats.get("task_stats", [])
    if not task_stats:
        st.info("No task statistics available yet.")
        return

    st.subheader("📋 Task-level Statistics")
    st.caption("Statistics for each task in the workflow")

    # Prepare DataFrame
    task_data = []
    for ts in task_stats:
        success_rate = ts.get("success_rate", 0.0)
        avg_duration = ts.get("avg_duration_ms")

        # Status emoji based on success rate
        if success_rate >= 95:
            status_emoji = "✅"
        elif success_rate >= 80:
            status_emoji = "🟢"
        elif success_rate >= 50:
            status_emoji = "🟡"
        else:
            status_emoji = "🔴"

        # Format duration
        if avg_duration is not None:
            if avg_duration < 1000:
                duration_str = f"{avg_duration:.0f}ms"
            elif avg_duration < 60000:
                duration_str = f"{avg_duration / 1000:.2f}s"
            else:
                minutes = avg_duration / 60000
                duration_str = f"{minutes:.2f}m"
        else:
            duration_str = "-"

        task_data.append(
            {
                "Order": ts.get("order", 0),
                "Task Name": ts.get("task_name", ""),
                "Executions": ts.get("total_executions", 0),
                "Success": ts.get("success_count", 0),
                "Failed": ts.get("failure_count", 0),
                "Success Rate": f"{success_rate:.2f}%",
                "Status": status_emoji,
                "Avg Duration": duration_str,
            },
        )

    df = pd.DataFrame(task_data)

    # Display table
    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        column_config={
            "Order": st.column_config.NumberColumn("Order", width="small"),
            "Task Name": st.column_config.TextColumn("Task Name", width="large"),
            "Executions": st.column_config.NumberColumn("Total", width="small"),
            "Success": st.column_config.NumberColumn("✓", width="small"),
            "Failed": st.column_config.NumberColumn("✗", width="small"),
            "Success Rate": st.column_config.TextColumn("Success Rate", width="medium"),
            "Status": st.column_config.TextColumn("", width="small"),
            "Avg Duration": st.column_config.TextColumn("Avg Time", width="medium"),
        },
    )

    # Legend
    st.caption(
        "Status: ✅ Excellent (≥95%) | 🟢 Good (≥80%) | 🟡 Moderate (≥50%) | 🔴 Needs Attention (<50%)",
    )


def main() -> None:
    """Main Job Statistics page function."""
    # Initialize session state
    initialize_session_state()

    # Render sidebar
    SidebarManager.render_complete_sidebar()

    # Page header
    st.title("📊 Job Master Statistics")
    st.caption("Analyze JobMaster execution metrics and KPIs")

    # Check if service is configured
    if not config.is_service_configured("JobQueue"):
        st.error(
            "❌ JobQueue is not configured. Please check your environment settings.",
        )
        st.stop()

    # Load initial data
    if not st.session_state.stats_job_masters_list:
        load_job_masters()

    # Refresh button
    col1, _ = st.columns([1, 5])
    with col1:
        if st.button("🔄 Refresh", key="refresh_stats", width="stretch"):
            load_job_masters()
            if st.session_state.selected_stats_master_id:
                load_master_stats(st.session_state.selected_stats_master_id)
            st.rerun()

    st.divider()

    # JobMaster selector
    render_job_master_selector()

    # Show statistics if master is selected
    if st.session_state.selected_stats_master_id and st.session_state.master_stats:
        st.divider()
        render_overall_statistics()

        st.divider()
        render_task_statistics()
    elif st.session_state.selected_stats_master_id:
        st.info("Loading statistics...")


if __name__ == "__main__":
    main()
