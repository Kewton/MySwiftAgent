"""
MyScheduler Management Page

Streamlit page for managing scheduled jobs including cron, interval,
and date-based scheduling with comprehensive monitoring.
"""

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
from croniter import croniter

from components.http_client import HTTPClient
from components.notifications import NotificationManager
from components.sidebar import SidebarManager
from core.config import config

# Page configuration
st.set_page_config(
    page_title="MyScheduler - CommonUI",
    page_icon="⏰",
    layout="wide"
)


def initialize_session_state() -> None:
    """Initialize session state variables for MyScheduler page."""
    if "scheduler_jobs" not in st.session_state:
        st.session_state.scheduler_jobs = []
    if "scheduler_selected_job" not in st.session_state:
        st.session_state.scheduler_selected_job = None
    if "scheduler_auto_refresh" not in st.session_state:
        st.session_state.scheduler_auto_refresh = False


def render_scheduler_creation_form() -> None:
    """Render scheduler job creation form."""
    st.subheader("🆕 Create New Scheduled Job")

    with st.form("scheduler_creation_form"):
        # Basic job information
        col1, col2 = st.columns(2)

        with col1:
            job_id = st.text_input(
                "Job ID*",
                placeholder="unique_job_identifier",
                help="Unique identifier for the scheduled job"
            )

            job_name = st.text_input(
                "Job Name*",
                placeholder="Enter descriptive job name",
                help="Human-readable name for the job"
            )

        with col2:
            job_function = st.text_input(
                "Function*",
                placeholder="module.function_name",
                help="Python function to execute (e.g., 'tasks.process_data')"
            )

            timezone = st.selectbox(
                "Timezone",
                ["UTC", "Asia/Tokyo", "US/Eastern", "US/Pacific", "Europe/London"],
                help="Timezone for schedule execution"
            )

        # Schedule configuration
        st.subheader("⏰ Schedule Configuration")
        schedule_type = st.selectbox(
            "Schedule Type*",
            ["cron", "interval", "date"],
            help="Type of schedule to create"
        )

        if schedule_type == "cron":
            render_cron_schedule_config()
        elif schedule_type == "interval":
            render_interval_schedule_config()
        else:  # date
            render_date_schedule_config()

        # Job arguments
        st.subheader("⚙️ Job Configuration")
        args = st.text_area(
            "Arguments (JSON Array)",
            placeholder='["arg1", "arg2", 123]',
            help="Function arguments as JSON array"
        )

        kwargs = st.text_area(
            "Keyword Arguments (JSON Object)",
            placeholder='{"param1": "value1", "param2": 42}',
            help="Function keyword arguments as JSON object"
        )

        # Advanced options
        with st.expander("🔧 Advanced Options"):
            max_instances = st.number_input(
                "Max Instances",
                min_value=1,
                max_value=10,
                value=1,
                help="Maximum concurrent instances of this job"
            )

            misfire_grace_time = st.number_input(
                "Misfire Grace Time (seconds)",
                min_value=0,
                max_value=3600,
                value=30,
                help="Grace time for missed executions"
            )

            coalesce = st.checkbox(
                "Coalesce",
                value=True,
                help="Combine multiple pending executions into one"
            )

        submitted = st.form_submit_button(
            "🚀 Create Scheduled Job",
            type="primary",
            use_container_width=True
        )

        if submitted:
            if not all([job_id, job_name, job_function]):
                st.error("Job ID, Name, and Function are required")
                return

            try:
                # Get schedule configuration
                schedule_config = get_schedule_config_from_session(schedule_type)
                if not schedule_config:
                    return

                # Parse arguments
                import json
                job_args = json.loads(args) if args.strip() else []
                job_kwargs = json.loads(kwargs) if kwargs.strip() else {}

                # Create job data
                job_data = {
                    "job_id": job_id,
                    "name": job_name,
                    "func": job_function,
                    "trigger": schedule_config["trigger"],
                    "args": job_args,
                    "kwargs": job_kwargs,
                    "timezone": timezone,
                    "max_instances": max_instances,
                    "misfire_grace_time": misfire_grace_time,
                    "coalesce": coalesce,
                    **schedule_config["params"]
                }

                create_scheduled_job(job_data)

            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON format: {e}")
            except Exception as e:
                NotificationManager.handle_exception(e, "Schedule Creation")


def render_cron_schedule_config() -> None:
    """Render cron schedule configuration."""
    col1, col2 = st.columns(2)

    with col1:
        cron_expression = st.text_input(
            "Cron Expression*",
            placeholder="0 */6 * * *",
            help="Cron expression (minute hour day month day_of_week)"
        )

        # Store in session state for form submission
        st.session_state.schedule_cron = cron_expression

    with col2:
        # Cron presets
        preset = st.selectbox(
            "Quick Presets",
            [
                "Custom",
                "Every minute (*/1 * * * *)",
                "Every hour (0 * * * *)",
                "Every 6 hours (0 */6 * * *)",
                "Daily at midnight (0 0 * * *)",
                "Weekly on Monday (0 0 * * 1)",
                "Monthly on 1st (0 0 1 * *)"
            ]
        )

        if preset != "Custom":
            preset_expr = preset.split("(")[1].split(")")[0]
            st.session_state.schedule_cron = preset_expr

    # Validate and show next runs
    if cron_expression:
        try:
            cron = croniter(cron_expression, datetime.now())
            st.success("✅ Valid cron expression")

            st.write("**Next 5 executions:**")
            for i in range(5):
                next_run = cron.get_next(datetime)
                st.write(f"- {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

        except Exception as e:
            st.error(f"❌ Invalid cron expression: {e}")


def render_interval_schedule_config() -> None:
    """Render interval schedule configuration."""
    col1, col2, col3 = st.columns(3)

    with col1:
        interval_value = st.number_input(
            "Interval Value*",
            min_value=1,
            value=5,
            help="Numeric value for the interval"
        )

    with col2:
        interval_unit = st.selectbox(
            "Interval Unit*",
            ["seconds", "minutes", "hours", "days", "weeks"],
            index=1,
            help="Unit of time for the interval"
        )

    with col3:
        start_date = st.date_input(
            "Start Date",
            help="When to start the recurring schedule"
        )

    # Store in session state
    st.session_state.schedule_interval_value = interval_value
    st.session_state.schedule_interval_unit = interval_unit
    st.session_state.schedule_start_date = start_date

    # Show next runs preview
    st.write("**Next 5 executions:**")
    current_time = datetime.combine(start_date, datetime.now().time())

    for i in range(5):
        if interval_unit == "seconds":
            next_run = current_time + timedelta(seconds=interval_value * i)
        elif interval_unit == "minutes":
            next_run = current_time + timedelta(minutes=interval_value * i)
        elif interval_unit == "hours":
            next_run = current_time + timedelta(hours=interval_value * i)
        elif interval_unit == "days":
            next_run = current_time + timedelta(days=interval_value * i)
        else:  # weeks
            next_run = current_time + timedelta(weeks=interval_value * i)

        st.write(f"- {next_run.strftime('%Y-%m-%d %H:%M:%S')}")


def render_date_schedule_config() -> None:
    """Render one-time date schedule configuration."""
    col1, col2 = st.columns(2)

    with col1:
        run_date = st.date_input(
            "Execution Date*",
            min_value=datetime.now().date(),
            help="Date when the job should run"
        )

    with col2:
        run_time = st.time_input(
            "Execution Time*",
            help="Time when the job should run"
        )

    # Store in session state
    st.session_state.schedule_run_date = run_date
    st.session_state.schedule_run_time = run_time

    # Show scheduled execution time
    scheduled_datetime = datetime.combine(run_date, run_time)
    st.info(f"**Scheduled for:** {scheduled_datetime.strftime('%Y-%m-%d %H:%M:%S')}")


def get_schedule_config_from_session(schedule_type: str) -> Optional[Dict]:
    """Get schedule configuration from session state."""
    try:
        if schedule_type == "cron":
            cron_expr = st.session_state.get("schedule_cron", "")
            if not cron_expr:
                st.error("Cron expression is required")
                return None
            return {
                "trigger": "cron",
                "params": {"cron": cron_expr}
            }

        elif schedule_type == "interval":
            value = st.session_state.get("schedule_interval_value", 5)
            unit = st.session_state.get("schedule_interval_unit", "minutes")
            start_date = st.session_state.get("schedule_start_date", datetime.now().date())

            return {
                "trigger": "interval",
                "params": {
                    f"{unit}": value,
                    "start_date": start_date.isoformat()
                }
            }

        else:  # date
            run_date = st.session_state.get("schedule_run_date")
            run_time = st.session_state.get("schedule_run_time")

            if not run_date or not run_time:
                st.error("Execution date and time are required")
                return None

            run_datetime = datetime.combine(run_date, run_time)
            return {
                "trigger": "date",
                "params": {"run_date": run_datetime.isoformat()}
            }

    except Exception as e:
        st.error(f"Schedule configuration error: {e}")
        return None


def create_scheduled_job(job_data: Dict[str, Any]) -> None:
    """Create a new scheduled job via API."""
    try:
        api_config = config.get_api_config("MyScheduler")
        with HTTPClient(api_config, "MyScheduler") as client:
            NotificationManager.operation_started("Creating scheduled job")

            response = client.post("/api/v1/jobs/", job_data)

            job_id = response.get("job_id", job_data["job_id"])
            NotificationManager.operation_completed("Scheduled job creation")
            NotificationManager.success(f"Scheduled job created successfully! ID: {job_id}")

            # Refresh job list
            load_scheduled_jobs()

            # Switch to job detail view
            st.session_state.scheduler_selected_job = job_id

    except Exception as e:
        NotificationManager.handle_exception(e, "Scheduled Job Creation")


def render_scheduler_job_list() -> None:
    """Render list of scheduled jobs."""
    st.subheader("⏰ Scheduled Jobs")

    # Controls
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        status_filter = st.selectbox(
            "Status Filter",
            ["All", "running", "paused", "completed", "error"],
            help="Filter jobs by status"
        )

    with col2:
        trigger_filter = st.selectbox(
            "Trigger Filter",
            ["All", "cron", "interval", "date"],
            help="Filter jobs by trigger type"
        )

    with col3:
        search_query = st.text_input(
            "Search Jobs",
            placeholder="Search by ID or name",
            help="Search jobs by ID or name"
        )

    with col4:
        auto_refresh = st.checkbox(
            "Auto Refresh",
            value=st.session_state.scheduler_auto_refresh,
            help="Automatically refresh job list"
        )
        st.session_state.scheduler_auto_refresh = auto_refresh

    # Refresh button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refresh", use_container_width=True):
            load_scheduled_jobs()

    # Display jobs
    jobs = st.session_state.scheduler_jobs
    if not jobs:
        st.info("No scheduled jobs found. Create your first scheduled job using the form above.")
        return

    # Filter jobs
    filtered_jobs = filter_scheduled_jobs(jobs, status_filter, trigger_filter, search_query)

    if not filtered_jobs:
        st.warning("No jobs match the current filters.")
        return

    # Display as table
    df = pd.DataFrame(filtered_jobs)

    # Format next run time for better display
    if 'next_run_time' in df.columns:
        df['next_run_time'] = pd.to_datetime(df['next_run_time']).dt.strftime('%Y-%m-%d %H:%M:%S')

    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "id": "Job ID",
            "name": "Name",
            "func": "Function",
            "trigger": st.column_config.SelectboxColumn(
                "Trigger",
                options=["cron", "interval", "date"],
            ),
            "next_run_time": st.column_config.DatetimeColumn("Next Run"),
            "status": st.column_config.SelectboxColumn(
                "Status",
                options=["running", "paused", "completed", "error"],
            ),
        }
    )

    # Handle row selection
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_job = filtered_jobs[selected_idx]
        st.session_state.scheduler_selected_job = selected_job["id"]


def filter_scheduled_jobs(jobs: List[Dict], status_filter: str, trigger_filter: str, search_query: str) -> List[Dict]:
    """Filter scheduled jobs based on criteria."""
    filtered = jobs

    # Status filter
    if status_filter != "All":
        filtered = [job for job in filtered if job.get("status", "").lower() == status_filter.lower()]

    # Trigger filter
    if trigger_filter != "All":
        filtered = [job for job in filtered if job.get("trigger") == trigger_filter]

    # Search filter
    if search_query:
        query_lower = search_query.lower()
        filtered = [
            job for job in filtered
            if (query_lower in job.get("name", "").lower() or
                query_lower in str(job.get("id", "")))
        ]

    return filtered


def render_scheduler_job_detail() -> None:
    """Render detailed scheduled job information and controls."""
    job_id = st.session_state.scheduler_selected_job
    if not job_id:
        st.info("Select a scheduled job from the list above to view details.")
        return

    st.subheader(f"📄 Scheduled Job Details - {job_id}")

    try:
        api_config = config.get_api_config("MyScheduler")
        with HTTPClient(api_config, "MyScheduler") as client:
            job_detail = client.get(f"/api/v1/jobs/{job_id}")

            # Job metrics
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Status", job_detail.get("status", "Unknown"))

            with col2:
                st.metric("Trigger Type", job_detail.get("trigger", "Unknown"))

            with col3:
                next_run = job_detail.get("next_run_time", "Not scheduled")
                if next_run and next_run != "Not scheduled":
                    try:
                        next_run_dt = datetime.fromisoformat(next_run.replace("Z", "+00:00"))
                        next_run = next_run_dt.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        pass
                st.metric("Next Run", next_run)

            with col4:
                st.metric("Executions", job_detail.get("execution_count", 0))

            # Job controls
            st.subheader("🎛️ Schedule Controls")
            col1, col2, col3, col4 = st.columns(4)

            current_status = job_detail.get("status", "").lower()

            with col1:
                if current_status == "paused" and st.button("▶️ Resume", use_container_width=True):
                    control_scheduled_job(job_id, "resume")

            with col2:
                if current_status == "running" and st.button("⏸️ Pause", use_container_width=True):
                    control_scheduled_job(job_id, "pause")

            with col3:
                if st.button("🔄 Trigger Now", use_container_width=True):
                    control_scheduled_job(job_id, "trigger")

            with col4:
                if st.button("🗑️ Remove", use_container_width=True, type="secondary"):
                    control_scheduled_job(job_id, "remove")

            # Job details tabs
            tab1, tab2, tab3 = st.tabs(["📋 Configuration", "📊 Execution History", "📝 Schedule Info"])

            with tab1:
                st.json(job_detail, expanded=False)

            with tab2:
                # Execution history (if available)
                executions = job_detail.get("executions", [])
                if executions:
                    exec_df = pd.DataFrame(executions)
                    st.dataframe(exec_df, use_container_width=True)
                else:
                    st.info("No execution history available.")

            with tab3:
                # Human-readable schedule description
                schedule_description = generate_schedule_description(job_detail)
                st.markdown(f"**Schedule Description:**\n{schedule_description}")

                # Schedule details
                trigger_info = job_detail.get("trigger_info", {})
                if trigger_info:
                    st.subheader("Trigger Details")
                    st.json(trigger_info)

    except Exception as e:
        NotificationManager.handle_exception(e, "Scheduled Job Detail")


def generate_schedule_description(job_detail: Dict) -> str:
    """Generate human-readable schedule description."""
    try:
        trigger = job_detail.get("trigger", "")
        trigger_info = job_detail.get("trigger_info", {})

        if trigger == "cron":
            cron_expr = trigger_info.get("cron", "")
            return f"Runs according to cron expression: `{cron_expr}`"

        elif trigger == "interval":
            interval_data = trigger_info
            unit_map = {
                "seconds": "second(s)",
                "minutes": "minute(s)",
                "hours": "hour(s)",
                "days": "day(s)",
                "weeks": "week(s)"
            }

            for unit, display in unit_map.items():
                if unit in interval_data:
                    value = interval_data[unit]
                    return f"Runs every {value} {display}"

        elif trigger == "date":
            run_date = trigger_info.get("run_date", "")
            if run_date:
                try:
                    run_dt = datetime.fromisoformat(run_date.replace("Z", "+00:00"))
                    return f"Runs once on {run_dt.strftime('%Y-%m-%d at %H:%M:%S')}"
                except Exception:
                    return f"Runs once on {run_date}"

        return "Schedule format not recognized"

    except Exception:
        return "Unable to generate description"


def control_scheduled_job(job_id: str, action: str) -> None:
    """Control scheduled job (resume, pause, trigger, remove)."""
    try:
        api_config = config.get_api_config("MyScheduler")
        with HTTPClient(api_config, "MyScheduler") as client:
            NotificationManager.operation_started(f"Scheduled job {action}")

            if action == "remove":
                client.delete(f"/api/v1/jobs/{job_id}")
                # Clear selected job if removed
                st.session_state.scheduler_selected_job = None
            else:
                client.post(f"/api/v1/jobs/{job_id}/{action}")

            NotificationManager.operation_completed(f"Scheduled job {action}")
            NotificationManager.success(f"Scheduled job {action} executed successfully!")

            # Refresh job list
            time.sleep(1)
            load_scheduled_jobs()
            st.rerun()

    except Exception as e:
        NotificationManager.handle_exception(e, f"Scheduled Job {action}")


def load_scheduled_jobs() -> None:
    """Load scheduled jobs from API."""
    try:
        api_config = config.get_api_config("MyScheduler")
        with HTTPClient(api_config, "MyScheduler") as client:
            response = client.get("/api/v1/jobs/")
            st.session_state.scheduler_jobs = response.get("jobs", [])

    except Exception as e:
        NotificationManager.handle_exception(e, "Load Scheduled Jobs")
        st.session_state.scheduler_jobs = []


def main() -> None:
    """Main MyScheduler page function."""
    # Initialize session state
    initialize_session_state()

    # Render sidebar
    selected_service, ui_settings = SidebarManager.render_complete_sidebar()

    # Page header
    st.title("⏰ MyScheduler Management")

    # Check if service is configured
    if not config.is_service_configured("MyScheduler"):
        st.error("❌ MyScheduler is not configured. Please check your environment settings.")
        st.stop()

    # Load initial data
    if not st.session_state.scheduler_jobs:
        load_scheduled_jobs()

    # Main content tabs
    tab1, tab2 = st.tabs(["🆕 Create Schedule", "⏰ Scheduled Jobs"])

    with tab1:
        render_scheduler_creation_form()

    with tab2:
        render_scheduler_job_list()
        st.divider()
        render_scheduler_job_detail()

    # Auto-refresh functionality
    if st.session_state.scheduler_auto_refresh:
        polling_interval = ui_settings.get("polling_interval", 5)
        time.sleep(polling_interval)
        st.rerun()


if __name__ == "__main__":
    main()