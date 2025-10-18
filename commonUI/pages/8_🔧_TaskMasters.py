"""
TaskMaster Management Page

Streamlit page for managing TaskMasters including creation, editing,
deletion, and interface association management.
"""

import json
from typing import Any

import pandas as pd  # type: ignore[import-untyped]
import streamlit as st

from components.http_client import HTTPClient
from components.notifications import NotificationManager
from components.sidebar import SidebarManager
from core.config import config

# Page configuration
st.set_page_config(
    page_title="TaskMasters - CommonUI",
    page_icon="🔧",
    layout="wide",
)


def initialize_session_state() -> None:
    """Initialize session state variables for TaskMasters page."""
    if "task_masters_list" not in st.session_state:
        st.session_state.task_masters_list = []
    if "selected_task_master_id" not in st.session_state:
        st.session_state.selected_task_master_id = None
    if "task_master_detail" not in st.session_state:
        st.session_state.task_master_detail = None
    if "interface_masters_list" not in st.session_state:
        st.session_state.interface_masters_list = []


def load_task_masters() -> None:
    """Load TaskMasters from API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            response = client.get("/api/v1/task-masters", params={"size": 100})
            st.session_state.task_masters_list = response.get("task_masters", [])

    except Exception as e:
        NotificationManager.handle_exception(e, "Load TaskMasters")
        st.session_state.task_masters_list = []


def load_interface_masters() -> None:
    """Load InterfaceMasters for dropdown selections."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            response = client.get("/api/v1/interface-masters", params={"size": 100})
            st.session_state.interface_masters_list = response.get("interfaces", [])

    except Exception as e:
        NotificationManager.handle_exception(e, "Load InterfaceMasters")
        st.session_state.interface_masters_list = []


def create_task_master(task_data: dict[str, Any]) -> None:
    """Create a new TaskMaster via API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            NotificationManager.operation_started("Creating TaskMaster")

            response = client.post("/api/v1/task-masters", task_data)

            task_id = response.get("id")
            NotificationManager.operation_completed("TaskMaster creation")
            NotificationManager.success(
                f"TaskMaster created successfully! ID: {task_id}",
            )

            # Refresh task master list
            load_task_masters()

    except Exception as e:
        NotificationManager.handle_exception(e, "TaskMaster Creation")


def update_task_master(task_id: str, task_data: dict[str, Any]) -> None:
    """Update an existing TaskMaster via API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            NotificationManager.operation_started("Updating TaskMaster")

            client.put(f"/api/v1/task-masters/{task_id}", task_data)

            NotificationManager.operation_completed("TaskMaster update")
            NotificationManager.success("TaskMaster updated successfully!")

            # Refresh task master list
            load_task_masters()

            # Refresh detail if currently viewing
            if st.session_state.selected_task_master_id == task_id:
                load_task_master_detail(task_id)

    except Exception as e:
        NotificationManager.handle_exception(e, "TaskMaster Update")


def delete_task_master(task_id: str) -> None:
    """Delete (deactivate) a TaskMaster via API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            NotificationManager.operation_started("Deleting TaskMaster")

            client.delete(f"/api/v1/task-masters/{task_id}")

            NotificationManager.operation_completed("TaskMaster deletion")
            NotificationManager.success("TaskMaster deactivated successfully!")

            # Clear selection if deleted
            if st.session_state.selected_task_master_id == task_id:
                st.session_state.selected_task_master_id = None
                st.session_state.task_master_detail = None

            # Refresh task master list
            load_task_masters()

    except Exception as e:
        NotificationManager.handle_exception(e, "TaskMaster Deletion")


def load_task_master_detail(task_id: str) -> None:
    """Load TaskMaster detail from API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            task_detail = client.get(f"/api/v1/task-masters/{task_id}")
            st.session_state.task_master_detail = task_detail

    except Exception as e:
        NotificationManager.handle_exception(e, "Load TaskMaster Detail")
        st.session_state.task_master_detail = None


def render_task_master_form(mode: str = "create", initial_data: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Render TaskMaster creation/edit form.

    Args:
        mode: "create" or "edit"
        initial_data: Initial form values for edit mode

    Returns:
        Form data dict if submitted, None otherwise
    """
    initial_data = initial_data or {}

    with st.form(f"task_master_form_{mode}"):
        st.subheader("📋 Basic Information")

        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input(
                "Name *",
                value=initial_data.get("name", ""),
                placeholder="e.g., company_search",
                help="Unique identifier name for this TaskMaster",
            )

        with col2:
            description = st.text_input(
                "Description",
                value=initial_data.get("description", ""),
                placeholder="e.g., Search for company information",
                help="Brief description of what this task does",
            )

        st.divider()
        st.subheader("🌐 HTTP Configuration")

        col1, col2 = st.columns(2)

        with col1:
            method = st.selectbox(
                "HTTP Method *",
                options=["GET", "POST", "PUT", "DELETE", "PATCH"],
                index=["GET", "POST", "PUT", "DELETE", "PATCH"].index(
                    initial_data.get("method", "POST")
                ),
                help="HTTP request method",
            )

        with col2:
            url = st.text_input(
                "URL *",
                value=initial_data.get("url", ""),
                placeholder="https://api.example.com/endpoint",
                help="Full URL endpoint for this task",
            )

        st.divider()
        st.subheader("🔄 Retry Settings")

        col1, col2 = st.columns(2)

        with col1:
            max_retries = st.number_input(
                "Max Retries",
                min_value=0,
                max_value=10,
                value=initial_data.get("max_retries", 3),
                help="Maximum number of retry attempts on failure",
            )

        with col2:
            retry_delay_sec = st.number_input(
                "Retry Delay (seconds)",
                min_value=0,
                max_value=300,
                value=initial_data.get("retry_delay_sec", 5),
                help="Delay between retry attempts in seconds",
            )

        st.divider()
        st.subheader("🔌 Interface Association")

        # Load interface masters if not already loaded
        if not st.session_state.interface_masters_list:
            load_interface_masters()

        interfaces = st.session_state.interface_masters_list

        # Create options for interface dropdowns
        interface_options = {
            "None": None,
            **{f"{iface['name']} ({iface['id']})": iface["id"] for iface in interfaces}
        }

        col1, col2 = st.columns(2)

        with col1:
            # Find current input interface index
            current_input_id = initial_data.get("input_interface_id")
            input_idx = 0
            if current_input_id:
                for i, (name, iface_id) in enumerate(interface_options.items()):
                    if iface_id == current_input_id:
                        input_idx = i
                        break

            input_interface_key = st.selectbox(
                "Input Interface",
                options=list(interface_options.keys()),
                index=input_idx,
                help="Interface schema for task input validation",
            )
            input_interface_id = interface_options[input_interface_key]

        with col2:
            # Find current output interface index
            current_output_id = initial_data.get("output_interface_id")
            output_idx = 0
            if current_output_id:
                for i, (name, iface_id) in enumerate(interface_options.items()):
                    if iface_id == current_output_id:
                        output_idx = i
                        break

            output_interface_key = st.selectbox(
                "Output Interface",
                options=list(interface_options.keys()),
                index=output_idx,
                help="Interface schema for task output validation",
            )
            output_interface_id = interface_options[output_interface_key]

        st.divider()
        st.subheader("⚙️ Advanced Settings")

        col1, col2 = st.columns(2)

        with col1:
            timeout_sec = st.number_input(
                "Timeout (seconds)",
                min_value=1,
                max_value=3600,
                value=initial_data.get("timeout_sec", 30),
                help="Request timeout in seconds",
            )

        with col2:
            is_active = st.checkbox(
                "Is Active",
                value=initial_data.get("is_active", True),
                help="Whether this TaskMaster is active and can be used",
            )

        # Submit button
        submitted = st.form_submit_button(
            f"{'✨ Create TaskMaster' if mode == 'create' else '💾 Update TaskMaster'}",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            # Validate required fields
            if not name or not url:
                st.error("❌ Name and URL are required fields")
                return None

            # Build form data
            form_data: dict[str, Any] = {
                "name": name,
                "description": description,
                "method": method,
                "url": url,
                "max_retries": max_retries,
                "retry_delay_sec": retry_delay_sec,
                "input_interface_id": input_interface_id,
                "output_interface_id": output_interface_id,
                "timeout_sec": timeout_sec,
                "is_active": is_active,
            }

            return form_data

    return None


def render_create_task_master_tab() -> None:
    """Render create TaskMaster tab."""
    st.subheader("🆕 Create New TaskMaster")
    st.caption("Create a reusable task template with interface validation")

    form_data = render_task_master_form(mode="create")

    if form_data:
        create_task_master(form_data)


def render_list_task_masters_tab() -> None:
    """Render list TaskMasters tab with filtering and detail view."""
    st.subheader("📋 TaskMaster List")

    # Filters
    col1, col2, col3 = st.columns([2, 2, 3])

    with col1:
        is_active_filter = st.selectbox(
            "Status Filter",
            ["All", "Active", "Inactive"],
            help="Filter by active/inactive status",
        )

    with col2:
        has_interface_filter = st.selectbox(
            "Interface Filter",
            ["All", "With Interfaces", "Without Interfaces"],
            help="Filter by interface association",
        )

    with col3:
        search_query = st.text_input(
            "Search",
            placeholder="Search by name or ID",
            help="Search TaskMasters by name or ID",
        )

    # Refresh button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refresh", key="refresh_list", use_container_width=True):
            load_task_masters()
            st.rerun()

    # Display task masters
    task_masters = st.session_state.task_masters_list
    if not task_masters:
        st.info("No TaskMasters found. Create your first TaskMaster using the Create tab.")
        return

    # Filter task masters
    filtered_masters = filter_task_masters(
        task_masters,
        is_active_filter,
        has_interface_filter,
        search_query,
    )

    if not filtered_masters:
        st.warning("No TaskMasters match the current filters.")
        return

    # Convert to DataFrame for better display
    display_masters = [
        {
            "id": m["id"],
            "name": m["name"],
            "method": m["method"],
            "url": m["url"][:40] + "..."
            if len(m.get("url", "")) > 40
            else m.get("url", ""),
            "interfaces": format_interfaces(m),
            "is_active": "✅ Active" if m.get("is_active") else "❌ Inactive",
            "version": m.get("current_version", 1),
        }
        for m in filtered_masters
    ]

    df = pd.DataFrame(display_masters)

    # Display as interactive table
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "id": "TaskMaster ID",
            "name": "Name",
            "method": "Method",
            "url": "URL",
            "interfaces": "Interfaces",
            "is_active": "Status",
            "version": "Version",
        },
    )

    # Handle row selection
    if hasattr(event, "selection") and event.selection.rows:  # type: ignore[attr-defined]
        selected_idx = event.selection.rows[0]  # type: ignore[attr-defined]
        selected_master = filtered_masters[selected_idx]
        st.session_state.selected_task_master_id = selected_master["id"]
        load_task_master_detail(selected_master["id"])

    st.divider()

    # Display task master detail if selected
    if st.session_state.selected_task_master_id and st.session_state.task_master_detail:
        render_task_master_detail()


def filter_task_masters(
    task_masters: list[dict],
    is_active_filter: str,
    has_interface_filter: str,
    search_query: str,
) -> list[dict]:
    """Filter task masters based on criteria."""
    filtered = task_masters

    # Active/Inactive filter
    if is_active_filter == "Active":
        filtered = [m for m in filtered if m.get("is_active")]
    elif is_active_filter == "Inactive":
        filtered = [m for m in filtered if not m.get("is_active")]

    # Interface filter
    if has_interface_filter == "With Interfaces":
        filtered = [
            m
            for m in filtered
            if m.get("input_interface_id") or m.get("output_interface_id")
        ]
    elif has_interface_filter == "Without Interfaces":
        filtered = [
            m
            for m in filtered
            if not (m.get("input_interface_id") or m.get("output_interface_id"))
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


def format_interfaces(task_master: dict[str, Any]) -> str:
    """Format interface information for display."""
    parts = []

    if task_master.get("input_interface_id"):
        parts.append(f"In: {task_master.get('input_interface_id')[:12]}...")

    if task_master.get("output_interface_id"):
        parts.append(f"Out: {task_master.get('output_interface_id')[:12]}...")

    return " | ".join(parts) if parts else "No interfaces"


def render_task_master_detail() -> None:
    """Render detailed TaskMaster information and controls."""
    task_detail = st.session_state.task_master_detail
    task_id = st.session_state.selected_task_master_id

    if not task_detail:
        return

    st.subheader(f"📄 TaskMaster Details - {task_detail.get('name', task_id)}")

    # Action buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("✏️ Edit", key="edit_task_master", use_container_width=True):
            st.session_state.edit_mode = True

    with col2:
        if task_detail.get("is_active") and st.button(
            "🗑️ Delete",
            key="delete_task_master",
            use_container_width=True,
        ):
            if st.session_state.get("confirm_delete") == task_id:
                delete_task_master(task_id)
                st.session_state.confirm_delete = None
            else:
                st.session_state.confirm_delete = task_id
                st.warning("⚠️ Click Delete again to confirm")

    with col3:
        if st.button("🔄 Refresh", key="refresh_detail", use_container_width=True):
            load_task_master_detail(task_id)

    # Show edit form if in edit mode
    if st.session_state.get("edit_mode"):
        st.divider()
        st.subheader("✏️ Edit TaskMaster")

        form_data = render_task_master_form(
            mode="edit",
            initial_data=task_detail,
        )

        if form_data:
            update_task_master(task_id, form_data)
            st.session_state.edit_mode = False
            st.rerun()

        if st.button("❌ Cancel Edit"):
            st.session_state.edit_mode = False
            st.rerun()

    # TaskMaster detail tabs
    st.divider()
    tab1, tab2, tab3 = st.tabs(["📋 Definition", "🔌 Interfaces", "⚙️ Config"])

    with tab1:
        st.json(task_detail, expanded=False)

    with tab2:
        # Display interface details
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📥 Input Interface")
            input_id = task_detail.get("input_interface_id")
            if input_id:
                try:
                    api_config = config.get_api_config("JobQueue")
                    with HTTPClient(api_config, "JobQueue") as client:
                        input_interface = client.get(f"/api/v1/interface-masters/{input_id}")
                        st.write(f"**Name:** {input_interface.get('name')}")
                        st.write(f"**Description:** {input_interface.get('description', 'N/A')}")

                        with st.expander("View Input Schema"):
                            st.json(input_interface.get("input_schema", {}))

                except Exception as e:
                    st.warning(f"Could not load input interface: {e}")
            else:
                st.info("No input interface configured")

        with col2:
            st.subheader("📤 Output Interface")
            output_id = task_detail.get("output_interface_id")
            if output_id:
                try:
                    api_config = config.get_api_config("JobQueue")
                    with HTTPClient(api_config, "JobQueue") as client:
                        output_interface = client.get(f"/api/v1/interface-masters/{output_id}")
                        st.write(f"**Name:** {output_interface.get('name')}")
                        st.write(f"**Description:** {output_interface.get('description', 'N/A')}")

                        with st.expander("View Output Schema"):
                            st.json(output_interface.get("output_schema", {}))

                except Exception as e:
                    st.warning(f"Could not load output interface: {e}")
            else:
                st.info("No output interface configured")

    with tab3:
        # Display key configuration
        col1, col2 = st.columns(2)

        with col1:
            st.metric("HTTP Method", task_detail.get("method", ""))
            st.metric("Timeout", f"{task_detail.get('timeout_sec', 0)}s")
            st.metric("Max Retries", task_detail.get("max_retries", 0))

        with col2:
            st.metric("Retry Delay", f"{task_detail.get('retry_delay_sec', 0)}s")
            st.metric("Current Version", task_detail.get("current_version", 1))
            st.metric("Is Active", "✅ Yes" if task_detail.get("is_active") else "❌ No")


def main() -> None:
    """Main TaskMasters page function."""
    # Initialize session state
    initialize_session_state()

    # Render sidebar
    SidebarManager.render_complete_sidebar()

    # Page header
    st.title("🔧 TaskMaster Management")
    st.caption("Manage reusable task templates with interface validation")

    # Check if service is configured
    if not config.is_service_configured("JobQueue"):
        st.error(
            "❌ JobQueue is not configured. Please check your environment settings.",
        )
        st.stop()

    # Load initial data
    if not st.session_state.task_masters_list:
        load_task_masters()

    if not st.session_state.interface_masters_list:
        load_interface_masters()

    # Main content tabs
    tab1, tab2 = st.tabs(
        ["🆕 Create TaskMaster", "📋 List TaskMasters"],
    )

    with tab1:
        render_create_task_master_tab()

    with tab2:
        render_list_task_masters_tab()


if __name__ == "__main__":
    main()
