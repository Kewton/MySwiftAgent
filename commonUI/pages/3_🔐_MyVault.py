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

from typing import Any

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
    layout="wide",
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
    if "myvault_editing_project" not in st.session_state:
        st.session_state.myvault_editing_project = None
    if "myvault_editing_secret" not in st.session_state:
        st.session_state.myvault_editing_secret = None


def load_secret_definitions() -> dict[str, Any]:
    """Load secret definitions from YAML file."""
    try:
        yaml_path = Path(__file__).parent.parent / "data" / "myvault_secrets.yaml"
        if yaml_path.exists():
            with open(yaml_path) as f:
                return yaml.safe_load(f)
        return {"secrets": []}
    except Exception as e:
        st.error(f"Failed to load secret definitions: {e!s}")
        return {"secrets": []}


# ============================================================================
# Dialog functions for project management
# ============================================================================

@st.dialog("🆕 Create New Project", width="large")
def show_create_project_dialog():
    """Show project creation dialog."""
    st.write("Register a new project in MyVault")

    project_name = st.text_input(
        "Project Name*",
        placeholder="e.g., newsbot, myscheduler, jobqueue",
        help="Unique project identifier",
    )

    description = st.text_area(
        "Description",
        placeholder="Describe what this project is for",
        help="Optional project description",
        height=100,
    )

    if st.button("🚀 Create Project", type="primary", use_container_width=True):
        if not project_name:
            st.error("Project name is required")
            return

        try:
            create_project({
                "name": project_name,
                "description": description or "",
            })
            st.success(f"Project '{project_name}' created successfully!")
            st.rerun()
        except Exception as e:
            NotificationManager.handle_exception(e, "Project Creation")


@st.dialog("✏️ Edit Project", width="large")
def show_edit_project_dialog(project: dict[str, Any]):
    """Show project editing dialog."""
    st.write(f"Edit project: **{project['name']}**")

    st.text_input(
        "Project Name",
        value=project["name"],
        disabled=True,
        help="Project name cannot be changed",
    )

    description = st.text_area(
        "Description",
        value=project.get("description", ""),
        placeholder="Describe what this project is for",
        help="Project description",
        height=100,
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Update", type="primary", use_container_width=True):
            try:
                update_project(project["name"], description)
                st.success(f"Project '{project['name']}' updated successfully!")
                st.rerun()
            except Exception as e:
                NotificationManager.handle_exception(e, "Project Update")

    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


# ============================================================================
# Dialog functions for secret management
# ============================================================================

@st.dialog("🆕 Create New Secret", width="large")
def show_create_secret_dialog(project: str):
    """Show secret creation dialog."""
    secret_defs = st.session_state.myvault_secret_definitions
    available_secrets = secret_defs.get("secrets", [])

    st.write(f"Create a new secret for project: **{project}**")

    # Secret selection dropdown
    secret_options = ["-- Custom --"] + [s["name"] for s in available_secrets]
    selected_option = st.selectbox(
        "Secret*",
        secret_options,
        help="Select a secret name or choose 'Custom' to enter your own",
    )

    # Handle custom vs predefined secret selection
    secret_name = None
    if selected_option == "-- Custom --":
        # Custom secret name input
        secret_name = st.text_input(
            "Custom Secret Name*",
            placeholder="e.g., my-custom-api-key",
            help="Enter a unique secret name for this project",
        )
    else:
        # Show description for selected secret
        selected_def = next((s for s in available_secrets if s["name"] == selected_option), None)
        if selected_def and selected_def.get("description"):
            st.info(f"ℹ️ {selected_def['description']}")
        secret_name = selected_option

    secret_value = st.text_area(
        "Secret Value*",
        placeholder="Enter the secret value",
        help="The actual secret value (will be encrypted)",
        height=100,
    )
    st.caption("⚠️ シークレット値は送信後に暗号化されます。")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Create Secret", type="primary", use_container_width=True):
            if not secret_name or not secret_value:
                st.error("Both secret name and value are required")
                return

            try:
                create_secret(project, secret_name, secret_value)
                st.success(f"Secret '{project}:{secret_name}' created successfully!")
                st.rerun()
            except Exception as e:
                NotificationManager.handle_exception(e, "Secret Creation")

    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


@st.dialog("✏️ Edit Secret", width="large")
def show_edit_secret_dialog(secret: dict[str, Any]):
    """Show secret editing dialog."""
    # Load secret definitions to show description
    secret_defs = st.session_state.myvault_secret_definitions
    available_secrets = secret_defs.get("secrets", [])
    selected_def = next((s for s in available_secrets if s["name"] == secret["path"]), None)

    st.write(f"Edit secret: **{secret['project']}:{secret['path']}**")

    st.text_input(
        "Project",
        value=secret["project"],
        disabled=True,
        help="Project name cannot be changed",
    )

    st.text_input(
        "Secret",
        value=secret["path"],
        disabled=True,
        help="Secret name cannot be changed",
    )

    # Show description if available
    if selected_def and selected_def.get("description"):
        st.info(f"ℹ️ {selected_def['description']}")

    st.caption("📌 Current version: " + str(secret.get("version", "N/A")))

    # Show current value option
    show_current = st.checkbox("👁️ Show current secret value", value=False)

    if show_current:
        try:
            secret_detail = get_secret(secret["project"], secret["path"])
            st.text_area(
                "Current Value",
                value=secret_detail.get("value", "N/A"),
                disabled=True,
                height=80,
            )
        except Exception as e:
            st.error(f"Failed to retrieve current value: {e!s}")

    st.divider()

    secret_value = st.text_area(
        "New Secret Value*",
        placeholder="Enter the new secret value",
        help="The new secret value (will be encrypted)",
        height=100,
    )
    st.caption("⚠️ 新しい値を入力してください。空欄の場合は更新されません。")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Update", type="primary", use_container_width=True):
            if not secret_value:
                st.error("Secret value is required")
                return

            try:
                update_secret(secret["project"], secret["path"], secret_value)
                st.success(f"Secret '{secret['project']}:{secret['path']}' updated successfully!")
                st.rerun()
            except Exception as e:
                NotificationManager.handle_exception(e, "Secret Update")

    with col2:
        if st.button("Cancel", use_container_width=True):
            st.rerun()


# ============================================================================
# Main content rendering functions
# ============================================================================

def render_projects_section():
    """Render projects section with action buttons."""
    col1, col2, col3 = st.columns([6, 1, 1])

    with col1:
        st.subheader("📁 Projects")

    with col2:
        if st.button("🔄 Refresh", key="refresh_projects", use_container_width=True):
            load_projects()
            st.rerun()

    with col3:
        if st.button("➕ New", key="new_project", type="primary", use_container_width=True):
            show_create_project_dialog()

    projects = st.session_state.myvault_projects

    if not projects:
        st.info("No projects found. Click '➕ New' to create your first project.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(projects)

    # Display as interactive table
    event = st.dataframe(
        df,
        width=None,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "name": st.column_config.TextColumn("Project Name", width="medium"),
            "description": st.column_config.TextColumn("Description", width="large"),
            "is_default": st.column_config.CheckboxColumn("⭐ Default", width="small"),
            "created_at": st.column_config.DatetimeColumn("Created At", width="medium"),
            "created_by": st.column_config.TextColumn("Created By", width="medium"),
        },
    )

    # Handle row selection
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_project = projects[selected_idx]
        st.session_state.myvault_selected_project = selected_project["name"]

        # Show action buttons
        st.divider()
        col1, col2, col3, col4, col5 = st.columns([6, 1, 1, 1, 1])

        with col1:
            default_indicator = "⭐" if selected_project.get("is_default", False) else ""
            st.write(f"**Selected:** {default_indicator} {selected_project['name']}")

        with col2:
            # Set default button (☆ or ⭐)
            is_default = selected_project.get("is_default", False)
            button_label = "⭐" if is_default else "☆"
            button_help = "Already default" if is_default else "Set as default project"

            if st.button(button_label, key="set_default_project", use_container_width=True, help=button_help, disabled=is_default):
                try:
                    set_default_project(selected_project["name"])
                    st.rerun()
                except Exception as e:
                    NotificationManager.handle_exception(e, "Set Default Project")

        with col3:
            if st.button("✏️ Edit", key="edit_project", use_container_width=True):
                show_edit_project_dialog(selected_project)

        with col4:
            if st.button("🗑️ Delete", key="delete_project", type="secondary", use_container_width=True):
                try:
                    delete_project(selected_project["name"])
                    st.session_state.myvault_selected_project = None
                    st.rerun()
                except Exception as e:
                    NotificationManager.handle_exception(e, "Project Deletion")


def render_secrets_section():
    """Render secrets section for selected project."""
    selected_project = st.session_state.myvault_selected_project

    if not selected_project:
        st.info("👆 Select a project above to view and manage its secrets.")
        return

    st.divider()

    col1, col2, col3, col4 = st.columns([5, 1, 1, 1])

    with col1:
        st.subheader(f"🔐 Secrets for: {selected_project}")

    with col2:
        if st.button("🔄 Reload Cache", key="reload_cache", use_container_width=True, help="Reload secrets cache in all services (graphAiServer, expertAgent)"):
            with st.spinner("Reloading cache..."):
                results = reload_all_services_cache(selected_project)
                success_count = sum(1 for v in results.values() if v)
                total_count = len(results)

                if success_count == total_count:
                    st.success(f"✅ Successfully reloaded cache for all services ({', '.join(results.keys())})")
                elif success_count > 0:
                    success_services = [k for k, v in results.items() if v]
                    failed_services = [k for k, v in results.items() if not v]
                    st.warning(f"⚠️ Partially reloaded: ✅ {', '.join(success_services)} | ❌ {', '.join(failed_services)}")
                else:
                    st.error("❌ Failed to reload cache for all services")

    with col3:
        if st.button("🔄 Refresh", key="refresh_secrets", use_container_width=True):
            load_secrets(selected_project)
            st.rerun()

    with col4:
        if st.button("➕ New", key="new_secret", type="primary", use_container_width=True):
            show_create_secret_dialog(selected_project)

    # Filter secrets for selected project
    all_secrets = st.session_state.myvault_secrets
    project_secrets = [s for s in all_secrets if s.get("project") == selected_project]

    if not project_secrets:
        st.info(f"No secrets found for '{selected_project}'. Click '➕ New' to create a secret.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(project_secrets)

    # Display as interactive table
    event = st.dataframe(
        df,
        width=None,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "id": st.column_config.NumberColumn("ID", width="small"),
            "project": st.column_config.TextColumn("Project", width="medium"),
            "path": st.column_config.TextColumn("Secret", width="large"),
            "version": st.column_config.NumberColumn("Version", width="small"),
            "updated_at": st.column_config.DatetimeColumn("Updated At", width="medium"),
            "updated_by": st.column_config.TextColumn("Updated By", width="medium"),
        },
    )

    # Handle row selection
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_secret = project_secrets[selected_idx]

        # Show action buttons
        st.divider()
        col1, col2, col3, col4 = st.columns([8, 1, 1, 1])

        with col1:
            st.write(f"**Selected:** {selected_secret['path']}")

        with col2:
            if st.button("✏️ Edit", key="edit_secret", use_container_width=True):
                show_edit_secret_dialog(selected_secret)

        with col3:
            if st.button("🗑️ Delete", key="delete_secret", type="secondary", use_container_width=True):
                try:
                    delete_secret(selected_secret["project"], selected_secret["path"])
                    st.rerun()
                except Exception as e:
                    NotificationManager.handle_exception(e, "Secret Deletion")


# ============================================================================
# API functions
# ============================================================================

def create_project(project_data: dict[str, Any]) -> None:
    """Create a new project via API."""
    api_config = config.get_api_config("MyVault")
    with HTTPClient(api_config, "MyVault") as client:
        response = client.post("/api/projects", project_data)
        load_projects()
        st.session_state.myvault_selected_project = project_data["name"]


def update_project(project_name: str, description: str) -> None:
    """Update a project via API."""
    api_config = config.get_api_config("MyVault")
    with HTTPClient(api_config, "MyVault") as client:
        project_data = {"description": description}
        response = client.patch(f"/api/projects/{project_name}", project_data)
        load_projects()


def delete_project(project_name: str) -> None:
    """Delete a project via API."""
    api_config = config.get_api_config("MyVault")
    with HTTPClient(api_config, "MyVault") as client:
        client.delete(f"/api/projects/{project_name}")
        load_projects()


def set_default_project(project_name: str) -> None:
    """Set a project as default via API."""
    api_config = config.get_api_config("MyVault")
    with HTTPClient(api_config, "MyVault") as client:
        client.put(f"/api/projects/{project_name}/set-default")
        load_projects()


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


def reload_expertagent_cache(project: str | None = None) -> None:
    """Reload expertAgent cache for a project.

    Args:
        project: Project name to reload cache for. If None, reloads all caches.
    """
    try:
        # Check if ExpertAgent is configured
        if not config.is_service_configured("expertagent"):
            return  # ExpertAgent not configured, skip reload

        api_config = config.get_api_config("expertagent")

        # Check if admin token is configured
        if not api_config.admin_token:
            return  # No admin token, skip reload

        # Call reload endpoint
        with HTTPClient(api_config, "ExpertAgent") as client:
            reload_data = {"project": project}
            client.post("/v1/admin/reload-secrets", reload_data)

    except Exception as e:
        # Log warning but don't fail the operation
        # Use st.toast for non-intrusive notification
        st.toast(f"⚠️ ExpertAgent cache reload failed: {e!s}", icon="⚠️")


def reload_graphaiserver_cache(project: str | None = None) -> None:
    """Reload graphAiServer cache for a project.

    Args:
        project: Project name to reload cache for. If None, reloads all caches.
    """
    try:
        # Check if GraphAiServer is configured
        if not config.is_service_configured("graphaiserver"):
            return  # GraphAiServer not configured, skip reload

        api_config = config.get_api_config("graphaiserver")

        # Check if admin token is configured
        if not api_config.admin_token:
            return  # No admin token, skip reload

        # Call reload endpoint
        with HTTPClient(api_config, "GraphAiServer") as client:
            reload_data = {"project": project} if project else {}
            client.post("/v1/admin/reload-secrets", reload_data)

    except Exception as e:
        # Log warning but don't fail the operation
        # Use st.toast for non-intrusive notification
        st.toast(f"⚠️ GraphAiServer cache reload failed: {e!s}", icon="⚠️")


def reload_all_services_cache(project: str | None = None) -> dict[str, bool]:
    """Reload secrets cache for all configured services.

    Args:
        project: Project name to reload cache for. If None, reloads all caches.

    Returns:
        Dictionary with service names as keys and success status as values.
    """
    results = {}

    # Reload ExpertAgent cache
    try:
        reload_expertagent_cache(project)
        results["expertAgent"] = True
    except Exception:
        results["expertAgent"] = False

    # Reload GraphAiServer cache
    try:
        reload_graphaiserver_cache(project)
        results["graphAiServer"] = True
    except Exception:
        results["graphAiServer"] = False

    return results


def create_secret(project: str, path: str, value: str) -> None:
    """Create a new secret via API."""
    api_config = config.get_api_config("MyVault")
    with HTTPClient(api_config, "MyVault") as client:
        secret_data = {
            "project": project,
            "path": path,
            "value": value,
        }
        response = client.post("/api/secrets", secret_data)
        load_secrets(project)
        reload_all_services_cache(project)


def update_secret(project: str, path: str, value: str) -> None:
    """Update an existing secret via API."""
    api_config = config.get_api_config("MyVault")
    with HTTPClient(api_config, "MyVault") as client:
        secret_data = {"value": value}
        response = client.patch(f"/api/secrets/{project}/{path}", secret_data)
        load_secrets(project)
        reload_all_services_cache(project)


def get_secret(project: str, path: str) -> dict[str, Any]:
    """Get secret details via API."""
    api_config = config.get_api_config("MyVault")
    with HTTPClient(api_config, "MyVault") as client:
        return client.get(f"/api/secrets/{project}/{path}")


def delete_secret(project: str, path: str) -> None:
    """Delete a secret via API."""
    api_config = config.get_api_config("MyVault")
    with HTTPClient(api_config, "MyVault") as client:
        client.delete(f"/api/secrets/{project}/{path}")
        load_secrets(project)
        reload_all_services_cache(project)


def load_secrets(project: str | None = None) -> None:
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


# ============================================================================
# Main function
# ============================================================================

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

        # Auto-select default project on first load
        if st.session_state.myvault_projects and not st.session_state.myvault_selected_project:
            default_project = next(
                (p for p in st.session_state.myvault_projects if p.get("is_default", False)),
                None,
            )
            if default_project:
                st.session_state.myvault_selected_project = default_project["name"]

    # Load secrets if project is selected
    if st.session_state.myvault_selected_project:
        if not st.session_state.myvault_secrets:
            load_secrets(st.session_state.myvault_selected_project)

    # Render main content
    render_projects_section()
    render_secrets_section()


if __name__ == "__main__":
    main()
