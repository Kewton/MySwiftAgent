"""
Job Master Management Page

Streamlit page for managing job master templates including creation, editing,
deletion, and job creation from templates.
"""

import json
from typing import Any

import pandas as pd  # type: ignore[import-untyped]
import streamlit as st

from components.http_client import HTTPClient
from components.job_master_form import JobMasterForm
from components.job_master_merger import JobMasterMerger
from components.notifications import NotificationManager
from components.sidebar import SidebarManager
from core.config import config

# Page configuration
st.set_page_config(
    page_title="Job Masters - CommonUI",
    page_icon="🗂️",
    layout="wide",
)


def initialize_session_state() -> None:
    """Initialize session state variables for Job Masters page."""
    if "job_masters_list" not in st.session_state:
        st.session_state.job_masters_list = []
    if "selected_master_id" not in st.session_state:
        st.session_state.selected_master_id = None
    if "master_detail" not in st.session_state:
        st.session_state.master_detail = None


def load_masters() -> None:
    """Load job masters from API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            response = client.get("/api/v1/job-masters", params={"size": 100})
            st.session_state.job_masters_list = response.get("masters", [])

    except Exception as e:
        NotificationManager.handle_exception(e, "Load Job Masters")
        st.session_state.job_masters_list = []


def create_master(master_data: dict[str, Any]) -> None:
    """Create a new job master via API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            NotificationManager.operation_started("Creating job master")

            response = client.post("/api/v1/job-masters", master_data)

            master_id = response.get("master_id")
            NotificationManager.operation_completed("Job master creation")
            NotificationManager.success(
                f"Job master created successfully! ID: {master_id}",
            )

            # Refresh master list
            load_masters()

    except Exception as e:
        NotificationManager.handle_exception(e, "Job Master Creation")


def update_master(master_id: str, master_data: dict[str, Any]) -> None:
    """Update an existing job master via API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            NotificationManager.operation_started("Updating job master")

            client.put(f"/api/v1/job-masters/{master_id}", master_data)

            NotificationManager.operation_completed("Job master update")
            NotificationManager.success("Job master updated successfully!")

            # Refresh master list
            load_masters()

            # Refresh master detail
            if st.session_state.selected_master_id == master_id:
                load_master_detail(master_id)

    except Exception as e:
        NotificationManager.handle_exception(e, "Job Master Update")


def delete_master(master_id: str) -> None:
    """Delete (deactivate) a job master via API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            NotificationManager.operation_started("Deleting job master")

            client.delete(f"/api/v1/job-masters/{master_id}")

            NotificationManager.operation_completed("Job master deletion")
            NotificationManager.success("Job master deactivated successfully!")

            # Clear selection if deleted
            if st.session_state.selected_master_id == master_id:
                st.session_state.selected_master_id = None
                st.session_state.master_detail = None

            # Refresh master list
            load_masters()

    except Exception as e:
        NotificationManager.handle_exception(e, "Job Master Deletion")


def load_master_detail(master_id: str) -> None:
    """Load master detail from API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            master_detail = client.get(f"/api/v1/job-masters/{master_id}")
            st.session_state.master_detail = master_detail

    except Exception as e:
        NotificationManager.handle_exception(e, "Load Master Detail")
        st.session_state.master_detail = None


def create_job_from_master(master_id: str, override_data: dict[str, Any]) -> None:
    """Create a job from master template with overrides."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            NotificationManager.operation_started("Creating job from master")

            response = client.post(
                f"/api/v1/jobs/from-master/{master_id}",
                override_data,
            )

            job_id = response.get("job_id")
            NotificationManager.operation_completed("Job creation from master")
            NotificationManager.success(f"Job created successfully! ID: {job_id}")

            # Switch to JobQueue page with the new job
            st.info(f"🔗 View job details in JobQueue page: {job_id}")

    except Exception as e:
        NotificationManager.handle_exception(e, "Job Creation from Master")


def render_create_master_tab() -> None:
    """Render create master tab."""
    st.subheader("🆕 Create New Job Master")
    st.caption("Create a reusable template for HTTP job requests")

    form_data = JobMasterForm.render_master_form(mode="create")

    if form_data:
        create_master(form_data)


def render_list_masters_tab() -> None:
    """Render list masters tab with filtering and detail view."""
    st.subheader("📋 Job Master List")

    # Filters
    col1, col2, col3 = st.columns([2, 2, 3])

    with col1:
        is_active_filter = st.selectbox(
            "Status Filter",
            ["All", "Active", "Inactive"],
            help="Filter by active/inactive status",
        )

    with col2:
        tags_filter = st.text_input(
            "Tags Filter",
            placeholder="tag1, tag2",
            help="Filter by tags (comma-separated)",
        )

    with col3:
        search_query = st.text_input(
            "Search",
            placeholder="Search by name or ID",
            help="Search masters by name or ID",
        )

    # Refresh button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refresh", key="refresh_list", width="stretch"):
            load_masters()

    # Display masters
    masters = st.session_state.job_masters_list
    if not masters:
        st.info("No job masters found. Create your first master using the Create tab.")
        return

    # Filter masters
    filtered_masters = filter_masters(
        masters,
        is_active_filter,
        tags_filter,
        search_query,
    )

    if not filtered_masters:
        st.warning("No masters match the current filters.")
        return

    # Convert to DataFrame for better display
    display_masters = [
        {
            "id": m["id"],
            "name": m["name"],
            "method": m["method"],
            "url": m["url"][:50] + "..."
            if len(m.get("url", "")) > 50
            else m.get("url", ""),
            "tags": ", ".join(m.get("tags", [])) if m.get("tags") else "",
            "is_active": "✅ Active" if m.get("is_active") else "❌ Inactive",
            "created_at": m.get("created_at", ""),
        }
        for m in filtered_masters
    ]

    df = pd.DataFrame(display_masters)

    # Display as interactive table
    event = st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "id": "Master ID",
            "name": "Name",
            "method": "Method",
            "url": "URL",
            "tags": "Tags",
            "is_active": "Status",
            "created_at": st.column_config.DatetimeColumn("Created"),
        },
    )

    # Handle row selection
    if hasattr(event, "selection") and event.selection.rows:  # type: ignore[attr-defined]
        selected_idx = event.selection.rows[0]  # type: ignore[attr-defined]
        selected_master = filtered_masters[selected_idx]
        st.session_state.selected_master_id = selected_master["id"]
        load_master_detail(selected_master["id"])

    st.divider()

    # Display master detail if selected
    if st.session_state.selected_master_id and st.session_state.master_detail:
        render_master_detail()


def filter_masters(
    masters: list[dict],
    is_active_filter: str,
    tags_filter: str,
    search_query: str,
) -> list[dict]:
    """Filter masters based on criteria."""
    filtered = masters

    # Active/Inactive filter
    if is_active_filter == "Active":
        filtered = [m for m in filtered if m.get("is_active")]
    elif is_active_filter == "Inactive":
        filtered = [m for m in filtered if not m.get("is_active")]

    # Tags filter
    if tags_filter:
        tag_list = [
            tag.strip().lower() for tag in tags_filter.split(",") if tag.strip()
        ]
        filtered = [
            m
            for m in filtered
            if m.get("tags")
            and any(any(tag in mtag.lower() for tag in tag_list) for mtag in m["tags"])
        ]

    # Search filter
    if search_query:
        query_lower = search_query.lower()
        filtered = [
            m
            for m in filtered
            if (
                query_lower in m.get("name", "").lower()
                or query_lower in str(m.get("id", ""))
            )
        ]

    return filtered


def render_master_detail() -> None:
    """Render detailed master information and controls."""
    master_detail = st.session_state.master_detail
    master_id = st.session_state.selected_master_id

    if not master_detail:
        return

    st.subheader(f"📄 Master Details - {master_detail.get('name', master_id)}")

    # Action buttons
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if st.button("✏️ Edit", key="edit_master", width="stretch"):
            st.session_state.edit_mode = True

    with col2:
        if master_detail.get("is_active") and st.button(
            "🗑️ Delete",
            key="delete_master",
            width="stretch",
        ):
            if st.session_state.get("confirm_delete") == master_id:
                delete_master(master_id)
                st.session_state.confirm_delete = None
            else:
                st.session_state.confirm_delete = master_id
                st.warning("⚠️ Click Delete again to confirm")

    with col3:
        if st.button("▶️ Create Job", key="create_job", width="stretch"):
            st.session_state.show_job_creation = True

    with col4:
        if st.button("🔄 Refresh", key="refresh_detail", width="stretch"):
            load_master_detail(master_id)

    # Show edit form if in edit mode
    if st.session_state.get("edit_mode"):
        st.divider()
        st.subheader("✏️ Edit Master")

        form_data = JobMasterForm.render_master_form(
            mode="edit",
            initial_data=master_detail,
        )

        if form_data:
            update_master(master_id, form_data)
            st.session_state.edit_mode = False
            st.rerun()

        if st.button("❌ Cancel Edit"):
            st.session_state.edit_mode = False
            st.rerun()

    # Show job creation form if requested
    if st.session_state.get("show_job_creation"):
        st.divider()
        render_job_from_master_form(master_detail)

        if st.button("❌ Cancel"):
            st.session_state.show_job_creation = False
            st.rerun()

    # Master detail tabs
    st.divider()
    tab1, tab2, tab3 = st.tabs(["📋 Definition", "📊 Jobs", "⚙️ Config"])

    with tab1:
        st.json(master_detail, expanded=False)

    with tab2:
        # List jobs created from this master
        try:
            api_config = config.get_api_config("JobQueue")
            with HTTPClient(api_config, "JobQueue") as client:
                jobs_response = client.get(f"/api/v1/job-masters/{master_id}/jobs")
                jobs = jobs_response.get("jobs", [])

                if jobs:
                    st.caption(f"Total jobs from this master: {len(jobs)}")
                    jobs_df = pd.DataFrame(
                        [
                            {
                                "id": j["id"],
                                "name": j.get("name", ""),
                                "status": j.get("status", ""),
                                "created_at": j.get("created_at", ""),
                            }
                            for j in jobs[:20]  # Limit to 20 most recent
                        ],
                    )
                    st.dataframe(jobs_df, width="stretch", hide_index=True)
                else:
                    st.info("No jobs have been created from this master yet.")

        except Exception as e:
            st.warning(f"Could not load jobs: {e}")

    with tab3:
        # Display key configuration
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Method", master_detail.get("method", ""))
            st.metric("Timeout", f"{master_detail.get('timeout_sec', 0)}s")
            st.metric("Max Attempts", master_detail.get("max_attempts", 0))

        with col2:
            st.metric("Backoff Strategy", master_detail.get("backoff_strategy", ""))
            st.metric("Backoff Seconds", f"{master_detail.get('backoff_seconds', 0)}s")
            st.metric("TTL", f"{master_detail.get('ttl_seconds', 0)}s")


def render_from_master_tab() -> None:
    """Render create job from master tab."""
    st.subheader("📊 Create Job from Master Template")
    st.caption("Select a master template and optionally override parameters")

    # Master selection
    masters = st.session_state.job_masters_list
    if not masters:
        st.info("No job masters available. Create a master first.")
        return

    # Filter active masters only
    active_masters = [m for m in masters if m.get("is_active")]
    if not active_masters:
        st.info("No active job masters available. Please activate a master first.")
        return

    # Master selector
    master_options = {f"{m['name']} ({m['id']})": m for m in active_masters}
    selected_option = st.selectbox(
        "🗂️ Select Master Template",
        options=list(master_options.keys()),
        help="Choose a master template to use as base",
    )

    if not selected_option:
        return

    master_data = master_options[selected_option]

    # Display master defaults
    st.subheader("📋 Master Template Defaults")
    with st.expander("View Master Configuration", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Method", value=master_data.get("method", ""), disabled=True)
            st.text_input(
                "Timeout",
                value=f"{master_data.get('timeout_sec', '')}s",
                disabled=True,
            )
        with col2:
            st.text_area(
                "URL",
                value=master_data.get("url", ""),
                disabled=True,
                height=100,
            )

        if master_data.get("headers"):
            st.subheader("Headers")
            st.json(master_data["headers"])

        if master_data.get("params"):
            st.subheader("Query Parameters")
            st.json(master_data["params"])

        if master_data.get("body"):
            st.subheader("Request Body")
            st.json(master_data["body"])

    st.divider()

    # Render job creation form
    render_job_from_master_form(master_data)


def render_job_from_master_form(master_data: dict[str, Any]) -> None:
    """Render job creation form with parameter override."""
    with st.form("job_from_master_form"):
        st.subheader("⚙️ Override Parameters (Optional)")
        st.caption("Specify parameters to override master defaults")

        # Job name override
        job_name = st.text_input(
            "Job Name",
            placeholder="Leave empty to use master name",
            help="Optional job name override",
        )

        # Headers override
        headers_override = st.text_area(
            "Headers Override (JSON)",
            placeholder='{\n  "X-Priority": "high"\n}',
            help="Additional headers or overrides (shallow merge)",
            height=80,
        )

        # Query params override
        params_override = st.text_area(
            "Query Parameters Override (JSON)",
            placeholder='{\n  "filter": "urgent"\n}',
            help="Additional query parameters or overrides (shallow merge)",
            height=80,
        )

        # Body override
        body_override = st.text_area(
            "Request Body Override (JSON)",
            placeholder='{\n  "priority": "high"\n}',
            help="Body overrides (deep merge with master body)",
            height=100,
        )

        # Tags override
        tags_override = st.text_input(
            "Additional Tags",
            placeholder="urgent, priority",
            help="Additional tags (merged with master tags)",
        )

        # Scheduling and priority
        col1, col2, col3 = st.columns(3)

        with col1:
            priority = st.number_input(
                "Priority",
                min_value=1,
                max_value=10,
                value=5,
                help="Job priority (1=highest, 10=lowest)",
            )

        with col2:
            timeout_override = st.number_input(
                "Timeout Override (sec)",
                min_value=0,
                max_value=3600,
                value=0,
                help="Override timeout (0 = use master default)",
            )

        with col3:
            max_attempts_override = st.number_input(
                "Max Attempts Override",
                min_value=0,
                max_value=10,
                value=0,
                help="Override max attempts (0 = use master default)",
            )

        # Scheduled execution
        scheduled_at = st.date_input(
            "Scheduled At (Optional)",
            value=None,
            help="Schedule job for future execution",
        )

        # Submit button
        submitted = st.form_submit_button(
            "🚀 Create Job from Master",
            type="primary",
            width="stretch",
        )

        if submitted:
            try:
                # Parse override parameters
                override_data: dict[str, Any] = {}

                if job_name:
                    override_data["name"] = job_name

                if headers_override.strip():
                    override_data["headers"] = json.loads(headers_override)

                if params_override.strip():
                    override_data["params"] = json.loads(params_override)

                if body_override.strip():
                    override_data["body"] = json.loads(body_override)

                if tags_override.strip():
                    override_data["tags"] = [
                        t.strip() for t in tags_override.split(",") if t.strip()
                    ]

                if priority != 5:
                    override_data["priority"] = priority

                if timeout_override > 0:
                    override_data["timeout_sec"] = timeout_override

                if max_attempts_override > 0:
                    override_data["max_attempts"] = max_attempts_override

                if scheduled_at:
                    override_data["scheduled_at"] = scheduled_at.isoformat()

                # Show merge preview
                if override_data:
                    JobMasterMerger.render_merge_preview(master_data, override_data)

                # Create job
                create_job_from_master(master_data["id"], override_data)

            except json.JSONDecodeError as e:
                st.error(f"❌ Invalid JSON format: {e}")
                st.info("💡 Please check your override parameters")


def main() -> None:
    """Main Job Masters page function."""
    # Initialize session state
    initialize_session_state()

    # Render sidebar
    SidebarManager.render_complete_sidebar()

    # Page header
    st.title("🗂️ Job Master Management")
    st.caption("Manage reusable HTTP job request templates")

    # Check if service is configured
    if not config.is_service_configured("JobQueue"):
        st.error(
            "❌ JobQueue is not configured. Please check your environment settings.",
        )
        st.stop()

    # Load initial data
    if not st.session_state.job_masters_list:
        load_masters()

    # Main content tabs
    tab1, tab2, tab3 = st.tabs(
        ["🆕 Create Master", "📋 List Masters", "📊 From Master"],
    )

    with tab1:
        render_create_master_tab()

    with tab2:
        render_list_masters_tab()

    with tab3:
        render_from_master_tab()


if __name__ == "__main__":
    main()
