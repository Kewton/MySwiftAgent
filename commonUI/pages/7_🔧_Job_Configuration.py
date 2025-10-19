"""
Job Configuration Page

Streamlit page for configuring and managing JobMaster task workflows.
"""

import pandas as pd  # type: ignore[import-untyped]
import streamlit as st

from components.http_client import HTTPClient
from components.notifications import NotificationManager
from components.sidebar import SidebarManager
from core.config import config

# Page configuration
st.set_page_config(
    page_title="Job Configuration - CommonUI",
    page_icon="🔧",
    layout="wide",
)


def initialize_session_state() -> None:
    """Initialize session state variables for Workflow Builder page."""
    if "workflow_job_masters_list" not in st.session_state:
        st.session_state.workflow_job_masters_list = []
    if "selected_workflow_master_id" not in st.session_state:
        st.session_state.selected_workflow_master_id = None
    if "workflow_tasks" not in st.session_state:
        st.session_state.workflow_tasks = []
    if "available_task_masters" not in st.session_state:
        st.session_state.available_task_masters = []
    if "validation_report" not in st.session_state:
        st.session_state.validation_report = None


def load_job_masters() -> None:
    """Load job masters from API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            response = client.get("/api/v1/job-masters", params={"size": 100})
            st.session_state.workflow_job_masters_list = response.get("masters", [])

    except Exception as e:
        NotificationManager.handle_exception(e, "Load Job Masters")
        st.session_state.workflow_job_masters_list = []


def load_task_masters() -> None:
    """Load available task masters from API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            response = client.get("/api/v1/task-masters", params={"size": 100})
            st.session_state.available_task_masters = response.get("masters", [])

    except Exception as e:
        NotificationManager.handle_exception(e, "Load Task Masters")
        st.session_state.available_task_masters = []


def load_workflow_tasks(master_id: str) -> None:
    """Load workflow tasks for a specific JobMaster."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            response = client.get(f"/api/v1/job-masters/{master_id}/tasks")
            st.session_state.workflow_tasks = response.get("tasks", [])

    except Exception as e:
        NotificationManager.handle_exception(e, "Load Workflow Tasks")
        st.session_state.workflow_tasks = []


def load_validation_report(master_id: str) -> None:
    """Load workflow validation report."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            report = client.get(f"/api/v1/job-masters/{master_id}/validate-workflow")
            st.session_state.validation_report = report

    except Exception as e:
        NotificationManager.handle_exception(e, "Load Validation Report")
        st.session_state.validation_report = None


def add_task_to_workflow(
    master_id: str,
    task_master_id: str,
    order: int,
) -> bool:
    """Add a task to the workflow."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            client.post(
                f"/api/v1/job-masters/{master_id}/tasks",
                json_data={
                    "task_master_id": task_master_id,
                    "order": order,
                    "is_required": True,
                    "retry_on_failure": False,
                },
            )
        NotificationManager.success("Task added to workflow successfully")
        return True

    except Exception as e:
        NotificationManager.handle_exception(e, "Add Task to Workflow")
        return False


def remove_task_from_workflow(master_id: str, task_master_id: str) -> bool:
    """Remove a task from the workflow."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            client.delete(f"/api/v1/job-masters/{master_id}/tasks/{task_master_id}")
        NotificationManager.success("Task removed from workflow successfully")
        return True

    except Exception as e:
        NotificationManager.handle_exception(e, "Remove Task from Workflow")
        return False


def update_task_order(master_id: str, task_master_id: str, new_order: int) -> bool:
    """Update task order in the workflow."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            client.put(
                f"/api/v1/job-masters/{master_id}/tasks/{task_master_id}",
                json_data={"order": new_order},
            )
        NotificationManager.success("Task order updated successfully")
        return True

    except Exception as e:
        NotificationManager.handle_exception(e, "Update Task Order")
        return False


def publish_workflow_version(master_id: str) -> bool:
    """Publish a new workflow version with validation."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            response = client.post(f"/api/v1/job-masters/{master_id}/publish-version")
            NotificationManager.success(
                f"Workflow version published! Version: {response.get('current_version')}",
            )
        return True

    except Exception as e:
        NotificationManager.handle_exception(e, "Publish Workflow Version")
        return False


def render_job_master_selector() -> None:
    """Render JobMaster selection UI."""
    st.subheader("📂 Select JobMaster")

    masters = st.session_state.workflow_job_masters_list
    if not masters:
        st.info("No job masters available. Please create a JobMaster first.")
        return

    # Filter active masters only
    active_masters = [m for m in masters if m.get("is_active")]
    if not active_masters:
        st.info("No active job masters available.")
        return

    # Create dropdown options
    master_options = {
        f"{m['name']} ({m['id']}[:8]...)": m["id"] for m in active_masters
    }

    # Add "Select..." option
    options_list = ["Select a JobMaster...", *master_options.keys()]

    # Get current selection index
    current_index = 0
    if st.session_state.selected_workflow_master_id:
        for idx, option in enumerate(options_list[1:], 1):
            if master_options[option] == st.session_state.selected_workflow_master_id:
                current_index = idx
                break

    selected_option = st.selectbox(
        "Select JobMaster to build workflow",
        options=options_list,
        index=current_index,
        key="workflow_master_selector",
        label_visibility="collapsed",
    )

    if selected_option and selected_option != "Select a JobMaster...":
        master_id = master_options[selected_option]
        if master_id != st.session_state.selected_workflow_master_id:
            st.session_state.selected_workflow_master_id = master_id
            load_workflow_tasks(master_id)
            load_validation_report(master_id)
            st.rerun()


def render_workflow_tasks() -> None:
    """Render workflow tasks list."""
    if not st.session_state.selected_workflow_master_id:
        return

    st.subheader("📋 Workflow Tasks")

    tasks = st.session_state.workflow_tasks
    if not tasks:
        st.info("No tasks in workflow yet. Add tasks using the panel below.")
        return

    # Prepare DataFrame
    task_data = []
    for task in tasks:
        task_data.append(
            {
                "Order": task.get("order", 0),
                "Task Name": task.get("task_name", ""),
                "Task ID": task.get("task_master_id", "")[:16] + "...",
                "Required": "✓" if task.get("is_required") else "✗",
                "Retry on Failure": "✓" if task.get("retry_on_failure") else "✗",
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
            "Task ID": st.column_config.TextColumn("Task ID", width="medium"),
            "Required": st.column_config.TextColumn("Required", width="small"),
            "Retry on Failure": st.column_config.TextColumn("Retry", width="small"),
        },
    )

    # Task management buttons
    st.divider()
    st.caption("Task Management")

    col1, col2, col3 = st.columns(3)

    with col1:
        # Move task up
        if len(tasks) > 1:
            task_to_move_up = st.selectbox(
                "Move task up",
                options=[""] + [f"{t['order']}: {t['task_name']}" for t in tasks[1:]],
                key="move_up_selector",
            )
            if st.button("⬆️ Move Up", key="move_up_btn", width="stretch"):
                if task_to_move_up:
                    order = int(task_to_move_up.split(":")[0])
                    task = next(t for t in tasks if t["order"] == order)
                    if update_task_order(
                        st.session_state.selected_workflow_master_id,
                        task["task_master_id"],
                        order - 1,
                    ):
                        load_workflow_tasks(
                            st.session_state.selected_workflow_master_id,
                        )
                        load_validation_report(
                            st.session_state.selected_workflow_master_id,
                        )
                        st.rerun()

    with col2:
        # Move task down
        if len(tasks) > 1:
            task_to_move_down = st.selectbox(
                "Move task down",
                options=[""] + [f"{t['order']}: {t['task_name']}" for t in tasks[:-1]],
                key="move_down_selector",
            )
            if st.button("⬇️ Move Down", key="move_down_btn", width="stretch"):
                if task_to_move_down:
                    order = int(task_to_move_down.split(":")[0])
                    task = next(t for t in tasks if t["order"] == order)
                    if update_task_order(
                        st.session_state.selected_workflow_master_id,
                        task["task_master_id"],
                        order + 1,
                    ):
                        load_workflow_tasks(
                            st.session_state.selected_workflow_master_id,
                        )
                        load_validation_report(
                            st.session_state.selected_workflow_master_id,
                        )
                        st.rerun()

    with col3:
        # Remove task
        task_to_remove = st.selectbox(
            "Remove task",
            options=[""] + [f"{t['order']}: {t['task_name']}" for t in tasks],
            key="remove_task_selector",
        )
        if st.button("🗑️ Remove", key="remove_task_btn", width="stretch"):
            if task_to_remove:
                order = int(task_to_remove.split(":")[0])
                task = next(t for t in tasks if t["order"] == order)
                if remove_task_from_workflow(
                    st.session_state.selected_workflow_master_id,
                    task["task_master_id"],
                ):
                    load_workflow_tasks(st.session_state.selected_workflow_master_id)
                    load_validation_report(st.session_state.selected_workflow_master_id)
                    st.rerun()


def render_add_task_panel() -> None:
    """Render add task panel."""
    if not st.session_state.selected_workflow_master_id:
        return

    st.subheader("➕ Add Task to Workflow")

    available_tasks = st.session_state.available_task_masters
    if not available_tasks:
        st.info("No task masters available. Please create a TaskMaster first.")
        return

    # Filter active task masters
    active_tasks = [t for t in available_tasks if t.get("is_active")]
    if not active_tasks:
        st.info("No active task masters available.")
        return

    # Filter out tasks already in workflow
    workflow_task_ids = {t["task_master_id"] for t in st.session_state.workflow_tasks}
    available_to_add = [t for t in active_tasks if t["id"] not in workflow_task_ids]

    if not available_to_add:
        st.info("All available tasks are already in the workflow.")
        return

    # Task selection
    task_options = {
        f"{t['name']} ({t['id'][:16]}...)": t["id"] for t in available_to_add
    }

    selected_task = st.selectbox(
        "Select TaskMaster to add",
        options=["", *task_options.keys()],
        key="add_task_selector",
    )

    if selected_task and selected_task != "":
        task_id = task_options[selected_task]

        # Display task details
        task_detail = next(t for t in available_to_add if t["id"] == task_id)
        st.caption(
            f"**Description**: {task_detail.get('description', 'No description')}",
        )

        # Add button
        if st.button("➕ Add to Workflow", key="add_task_btn", width="stretch"):
            # Add at the end of workflow
            next_order = len(st.session_state.workflow_tasks)
            if add_task_to_workflow(
                st.session_state.selected_workflow_master_id,
                task_id,
                next_order,
            ):
                load_workflow_tasks(st.session_state.selected_workflow_master_id)
                load_validation_report(st.session_state.selected_workflow_master_id)
                st.rerun()


def render_validation_panel() -> None:
    """Render workflow validation panel."""
    if not st.session_state.selected_workflow_master_id:
        return

    st.subheader("🔍 Workflow Validation")

    report = st.session_state.validation_report
    if not report:
        st.info("No validation report available. Click 'Validate' to check workflow.")
        if st.button("🔍 Validate Workflow", key="validate_btn", width="stretch"):
            load_validation_report(st.session_state.selected_workflow_master_id)
            st.rerun()
        return

    # Display validation status
    is_valid = report.get("is_valid", False)
    if is_valid:
        st.success("✅ Workflow is valid! All interfaces are compatible.")
    else:
        st.error("❌ Workflow validation failed. Please fix the errors below.")

    # Display errors
    errors = report.get("errors", [])
    if errors:
        st.divider()
        st.caption("**Validation Errors**")
        for error in errors:
            with st.expander(
                f"🔴 {error.get('message', 'Unknown error')}",
                expanded=True,
            ):
                st.json(error.get("details", {}))

    # Display warnings
    warnings = report.get("warnings", [])
    if warnings:
        st.divider()
        st.caption("**Warnings**")
        for warning in warnings:
            st.warning(f"⚠️ {warning.get('message', 'Unknown warning')}")

    # Display task chain
    task_chain = report.get("task_chain", [])
    if task_chain:
        st.divider()
        st.caption("**Task Interface Chain**")

        chain_data = []
        for task in task_chain:
            chain_data.append(
                {
                    "Order": task.get("order", 0),
                    "Task": task.get("task_name", ""),
                    "Input Interface": task.get("input_interface_id", "None")[:20]
                    + "..."
                    if task.get("input_interface_id")
                    else "None",
                    "Output Interface": task.get("output_interface_id", "None")[:20]
                    + "..."
                    if task.get("output_interface_id")
                    else "None",
                },
            )

        df = pd.DataFrame(chain_data)
        st.dataframe(df, width="stretch", hide_index=True)

    # Re-validate button
    st.divider()
    if st.button("🔄 Re-validate", key="revalidate_btn", width="stretch"):
        load_validation_report(st.session_state.selected_workflow_master_id)
        st.rerun()


def render_publish_panel() -> None:
    """Render workflow publish panel."""
    if not st.session_state.selected_workflow_master_id:
        return

    st.subheader("🚀 Publish Workflow Version")

    # Check if validation passed
    report = st.session_state.validation_report
    if not report:
        st.warning("⚠️ Please validate workflow before publishing.")
        return

    is_valid = report.get("is_valid", False)
    if not is_valid:
        st.error(
            "❌ Cannot publish: Workflow validation failed. Please fix errors first.",
        )
        return

    st.success("✅ Workflow is ready to publish!")
    st.caption(
        "Publishing will create a new version and validate interface compatibility.",
    )

    if st.button(
        "🚀 Publish Version",
        key="publish_btn",
        width="stretch",
        type="primary",
    ):
        if publish_workflow_version(st.session_state.selected_workflow_master_id):
            load_validation_report(st.session_state.selected_workflow_master_id)
            st.rerun()


def main() -> None:
    """Main Job Configuration page function."""
    # Initialize session state
    initialize_session_state()

    # Render sidebar
    SidebarManager.render_complete_sidebar()

    # Page header
    st.title("🔧 Job Configuration")
    st.caption(
        "Configure and validate JobMaster task workflows with interface compatibility checking",
    )

    # Check if service is configured
    if not config.is_service_configured("JobQueue"):
        st.error(
            "❌ JobQueue is not configured. Please check your environment settings.",
        )
        st.stop()

    # Load initial data
    if not st.session_state.workflow_job_masters_list:
        load_job_masters()
    if not st.session_state.available_task_masters:
        load_task_masters()

    # Refresh button
    col1, _ = st.columns([1, 5])
    with col1:
        if st.button("🔄 Refresh", key="refresh_all", width="stretch"):
            load_job_masters()
            load_task_masters()
            if st.session_state.selected_workflow_master_id:
                load_workflow_tasks(st.session_state.selected_workflow_master_id)
                load_validation_report(st.session_state.selected_workflow_master_id)
            st.rerun()

    st.divider()

    # JobMaster selector
    render_job_master_selector()

    if st.session_state.selected_workflow_master_id:
        st.divider()

        # Two-column layout
        col_left, col_right = st.columns([2, 1])

        with col_left:
            # Workflow tasks list
            render_workflow_tasks()

            st.divider()

            # Add task panel
            render_add_task_panel()

        with col_right:
            # Validation panel
            render_validation_panel()

            st.divider()

            # Publish panel
            render_publish_panel()


if __name__ == "__main__":
    main()
