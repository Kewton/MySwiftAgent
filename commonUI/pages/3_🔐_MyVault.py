"""
MyVault Management Page

Streamlit page for managing secrets and projects in MyVault service.
"""

from pathlib import Path

# IMPORTANT: Load .env BEFORE importing config
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

import json
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st
import yaml

from components.http_client import HTTPClient
from components.notifications import NotificationManager
from components.sidebar import SidebarManager
from core.config import config

# Page configuration
st.set_page_config(
    page_title="MyVault - CommonUI",
    page_icon="🔐",
    layout="wide"
)


def initialize_session_state() -> None:
    """Initialize session state variables for MyVault page."""
    if "myvault_projects" not in st.session_state:
        st.session_state.myvault_projects = []
    if "myvault_secrets" not in st.session_state:
        st.session_state.myvault_secrets = []
    if "myvault_selected_project" not in st.session_state:
        st.session_state.myvault_selected_project = None
    if "myvault_secret_definitions" not in st.session_state:
        st.session_state.myvault_secret_definitions = load_secret_definitions()


def load_secret_definitions() -> Dict[str, Any]:
    """Load secret definitions from YAML file."""
    try:
        yaml_path = Path(__file__).parent.parent / "data" / "myvault_secrets.yaml"
        if yaml_path.exists():
            with open(yaml_path, "r") as f:
                return yaml.safe_load(f)
        return {"projects": {}}
    except Exception as e:
        st.error(f"Failed to load secret definitions: {str(e)}")
        return {"projects": {}}


def render_project_management() -> None:
    """Render project management interface."""
    st.subheader("📁 Project Management")

    tab1, tab2 = st.tabs(["📋 Projects List", "🆕 Create/Edit Project"])

    with tab1:
        render_projects_list()

    with tab2:
        render_project_form()


def render_projects_list() -> None:
    """Render list of projects."""
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refresh Projects", use_container_width=True):
            load_projects()

    projects = st.session_state.myvault_projects
    if not projects:
        st.info("No projects found. Create your first project using the form in the next tab.")
        return

    # Convert to DataFrame for better display
    df = pd.DataFrame(projects)

    # Display as interactive table
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "id": "ID",
            "name": "Project Name",
            "description": "Description",
            "created_at": st.column_config.DatetimeColumn("Created At"),
            "created_by": "Created By",
        }
    )

    # Handle row selection
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_project = projects[selected_idx]
        st.session_state.myvault_selected_project = selected_project["name"]

        # Show delete button for selected project
        st.divider()
        col1, col2, col3 = st.columns([2, 1, 1])
        with col3:
            if st.button("🗑️ Delete Project", type="secondary", use_container_width=True):
                delete_project(selected_project["name"])


def render_project_form() -> None:
    """Render project creation/update form."""
    with st.form("project_form"):
        st.subheader("Create New Project")

        project_name = st.text_input(
            "Project Name*",
            placeholder="e.g., newsbot, myscheduler, jobqueue",
            help="Unique project identifier"
        )

        description = st.text_area(
            "Description",
            placeholder="Describe what this project is for",
            help="Optional project description"
        )

        submitted = st.form_submit_button("🚀 Create Project", type="primary", use_container_width=True)

        if submitted:
            if not project_name:
                st.error("Project name is required")
                return

            try:
                create_project({
                    "name": project_name,
                    "description": description or ""
                })
            except Exception as e:
                NotificationManager.handle_exception(e, "Project Creation")


def create_project(project_data: Dict[str, Any]) -> None:
    """Create a new project via API."""
    try:
        api_config = config.get_api_config("MyVault")
        with HTTPClient(api_config, "MyVault") as client:
            NotificationManager.operation_started("Creating project")

            response = client.post("/api/projects", project_data)

            NotificationManager.operation_completed("Project creation")
            NotificationManager.success(f"Project '{project_data['name']}' created successfully!")

            # Refresh project list
            load_projects()

            # Select the newly created project
            st.session_state.myvault_selected_project = project_data['name']

    except Exception as e:
        NotificationManager.handle_exception(e, "Project Creation")


def delete_project(project_name: str) -> None:
    """Delete a project via API."""
    try:
        api_config = config.get_api_config("MyVault")
        with HTTPClient(api_config, "MyVault") as client:
            NotificationManager.operation_started("Deleting project")

            client.delete(f"/api/projects/{project_name}")

            NotificationManager.operation_completed("Project deletion")
            NotificationManager.success(f"Project '{project_name}' deleted successfully!")

            # Clear selection
            st.session_state.myvault_selected_project = None

            # Refresh project list
            load_projects()

    except Exception as e:
        NotificationManager.handle_exception(e, "Project Deletion")


def load_projects() -> None:
    """Load projects from API."""
    try:
        api_config = config.get_api_config("MyVault")
        with HTTPClient(api_config, "MyVault") as client:
            response = client.get("/api/projects")
            st.session_state.myvault_projects = response if isinstance(response, list) else []

    except Exception as e:
        NotificationManager.handle_exception(e, "Load Projects")
        st.session_state.myvault_projects = []


def render_secret_management() -> None:
    """Render secret management interface."""
    st.subheader("🔐 Secret Management")

    selected_project = st.session_state.myvault_selected_project

    if not selected_project:
        st.info("👆 Select a project from the Projects List tab above to manage its secrets.")
        return

    st.info(f"📁 Managing secrets for project: **{selected_project}**")

    tab1, tab2 = st.tabs(["📋 Secrets List", "🆕 Create/Update Secret"])

    with tab1:
        render_secrets_list(selected_project)

    with tab2:
        render_secret_form(selected_project)


def render_secrets_list(project: str) -> None:
    """Render list of secrets for a project."""
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refresh Secrets", use_container_width=True):
            load_secrets(project)

    # Filter secrets for selected project
    all_secrets = st.session_state.myvault_secrets
    project_secrets = [s for s in all_secrets if s.get("project") == project]

    if not project_secrets:
        st.info("No secrets found for this project. Create your first secret using the form in the next tab.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(project_secrets)

    # Display as table
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "id": "ID",
            "project": "Project",
            "path": "Path",
            "version": "Version",
            "updated_at": st.column_config.DatetimeColumn("Updated At"),
            "updated_by": "Updated By",
        }
    )

    # Handle row selection - show update/delete actions
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_secret = project_secrets[selected_idx]

        st.divider()
        st.subheader(f"🔑 Secret: {selected_secret['path']}")

        # Show secret value
        show_value = st.checkbox("👁️ Show Secret Value", value=False)
        if show_value:
            try:
                secret_detail = get_secret(selected_secret['project'], selected_secret['path'])
                st.code(secret_detail.get('value', 'N/A'), language="text")
            except Exception as e:
                st.error(f"Failed to retrieve secret value: {str(e)}")

        # Actions
        col1, col2, col3 = st.columns([2, 1, 1])
        with col3:
            if st.button("🗑️ Delete Secret", type="secondary", use_container_width=True):
                delete_secret(selected_secret['project'], selected_secret['path'])


def render_secret_form(project: str) -> None:
    """Render secret creation/update form."""
    secret_defs = st.session_state.myvault_secret_definitions

    with st.form("secret_form"):
        st.subheader("Create or Update Secret")

        # Check if project has predefined secrets
        project_def = secret_defs.get("projects", {}).get(project, {})
        predefined_secrets = project_def.get("secrets", [])

        if predefined_secrets:
            st.caption(f"💡 Select from predefined secrets for '{project}' or enter custom path")

            # Dropdown for predefined secrets
            secret_options = ["-- Custom Path --"] + [s["name"] for s in predefined_secrets]
            selected_option = st.selectbox(
                "Secret Template",
                secret_options,
                help="Select a predefined secret or choose 'Custom Path'"
            )

            if selected_option != "-- Custom Path --":
                # Find selected secret definition
                selected_def = next((s for s in predefined_secrets if s["name"] == selected_option), None)
                if selected_def:
                    secret_path = st.text_input(
                        "Secret Path*",
                        value=selected_def["path"],
                        help=selected_def.get("description", "Secret path")
                    )
                    st.caption(f"ℹ️ {selected_def.get('description', '')}")
                else:
                    secret_path = st.text_input(
                        "Secret Path*",
                        placeholder="environment/secret-name",
                        help="Path for the secret (e.g., prod/api-key)"
                    )
            else:
                secret_path = st.text_input(
                    "Secret Path*",
                    placeholder="environment/secret-name",
                    help="Path for the secret (e.g., prod/api-key)"
                )
        else:
            st.caption("💡 No predefined secrets for this project. Enter custom secret path.")
            secret_path = st.text_input(
                "Secret Path*",
                placeholder="environment/secret-name",
                help="Path for the secret (e.g., prod/api-key)"
            )

        secret_value = st.text_area(
            "Secret Value*",
            placeholder="Enter the secret value",
            help="The actual secret value (will be encrypted)",
            type="password"
        )

        col1, col2 = st.columns(2)
        with col1:
            create_button = st.form_submit_button("🆕 Create Secret", type="primary", use_container_width=True)
        with col2:
            update_button = st.form_submit_button("🔄 Update Secret", type="secondary", use_container_width=True)

        if create_button or update_button:
            if not secret_path or not secret_value:
                st.error("Both secret path and value are required")
                return

            try:
                if create_button:
                    create_secret(project, secret_path, secret_value)
                else:
                    update_secret(project, secret_path, secret_value)
            except Exception as e:
                NotificationManager.handle_exception(e, "Secret Operation")


def create_secret(project: str, path: str, value: str) -> None:
    """Create a new secret via API."""
    try:
        api_config = config.get_api_config("MyVault")
        with HTTPClient(api_config, "MyVault") as client:
            NotificationManager.operation_started("Creating secret")

            secret_data = {
                "project": project,
                "path": path,
                "value": value
            }

            response = client.post("/api/secrets", secret_data)

            NotificationManager.operation_completed("Secret creation")
            NotificationManager.success(f"Secret '{project}:{path}' created successfully!")

            # Refresh secrets list
            load_secrets(project)

    except Exception as e:
        NotificationManager.handle_exception(e, "Secret Creation")


def update_secret(project: str, path: str, value: str) -> None:
    """Update an existing secret via API."""
    try:
        api_config = config.get_api_config("MyVault")
        with HTTPClient(api_config, "MyVault") as client:
            NotificationManager.operation_started("Updating secret")

            secret_data = {"value": value}

            response = client.patch(f"/api/secrets/{project}/{path}", secret_data)

            NotificationManager.operation_completed("Secret update")
            NotificationManager.success(f"Secret '{project}:{path}' updated successfully!")

            # Refresh secrets list
            load_secrets(project)

    except Exception as e:
        NotificationManager.handle_exception(e, "Secret Update")


def get_secret(project: str, path: str) -> Dict[str, Any]:
    """Get secret details via API."""
    api_config = config.get_api_config("MyVault")
    with HTTPClient(api_config, "MyVault") as client:
        return client.get(f"/api/secrets/{project}/{path}")


def delete_secret(project: str, path: str) -> None:
    """Delete a secret via API."""
    try:
        api_config = config.get_api_config("MyVault")
        with HTTPClient(api_config, "MyVault") as client:
            NotificationManager.operation_started("Deleting secret")

            client.delete(f"/api/secrets/{project}/{path}")

            NotificationManager.operation_completed("Secret deletion")
            NotificationManager.success(f"Secret '{project}:{path}' deleted successfully!")

            # Refresh secrets list
            load_secrets(project)

    except Exception as e:
        NotificationManager.handle_exception(e, "Secret Deletion")


def load_secrets(project: Optional[str] = None) -> None:
    """Load secrets from API."""
    try:
        api_config = config.get_api_config("MyVault")
        with HTTPClient(api_config, "MyVault") as client:
            params = {"project": project} if project else None
            response = client.get("/api/secrets", params=params)

            st.session_state.myvault_secrets = response if isinstance(response, list) else []

    except Exception as e:
        NotificationManager.handle_exception(e, "Load Secrets")
        st.session_state.myvault_secrets = []


def main() -> None:
    """Main MyVault page function."""
    # Initialize session state
    initialize_session_state()

    # Render sidebar
    selected_service, ui_settings = SidebarManager.render_complete_sidebar()

    # Page header
    st.title("🔐 MyVault Management")
    st.caption("Secure secret and project management")

    # Check if service is configured
    if not config.is_service_configured("MyVault"):
        st.error("❌ MyVault is not configured. Please check your environment settings.")
        st.info("""
        **Required Environment Variables:**
        - `MYVAULT_BASE_URL`: MyVault API base URL
        - `MYVAULT_SERVICE_NAME`: Service name for authentication
        - `MYVAULT_SERVICE_TOKEN`: Service token for authentication
        """)
        st.stop()

    # Load initial data
    if not st.session_state.myvault_projects:
        load_projects()

    # Main content
    render_project_management()

    st.divider()

    render_secret_management()


if __name__ == "__main__":
    main()
