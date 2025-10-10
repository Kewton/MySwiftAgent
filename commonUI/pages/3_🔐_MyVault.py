"""
MyVault Management Page

Streamlit page for managing secrets and projects in MyVault service.
"""

from pathlib import Path

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
        # Use /app/config/ path in Docker container, fallback to local path for development
        yaml_path = Path("/app/config/myvault_secrets.yaml")
        if not yaml_path.exists():
            # Fallback to local development path
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

    # Filter secrets for selected project (exclude system-managed secrets)
    all_secrets = st.session_state.myvault_secrets
    project_secrets = [
        s for s in all_secrets
        if s.get("project") == selected_project
        and s.get("path") != "GOOGLE_CREDS_ENCRYPTION_KEY"  # System-managed secret, hidden from UI
    ]

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
# Google Authentication API functions
# ============================================================================

def get_google_token_status(project: str) -> dict[str, Any]:
    """Get Google token status from ExpertAgent."""
    api_config = config.get_api_config("expertagent")
    with HTTPClient(api_config, "ExpertAgent") as client:
        params = {"project": project}
        return client.get("/v1/google-auth/token-status", params=params)


def save_google_credentials_to_myvault(project: str, credentials_json: str) -> None:
    """Save Google credentials to MyVault."""
    api_config = config.get_api_config("MyVault")
    with HTTPClient(api_config, "MyVault") as client:
        secret_data = {
            "project": project,
            "path": "GOOGLE_CREDENTIALS_JSON",
            "value": credentials_json,
        }
        # Check if secret exists
        try:
            existing = client.get(f"/api/secrets/{project}/GOOGLE_CREDENTIALS_JSON")
            # Update existing secret
            client.patch(f"/api/secrets/{project}/GOOGLE_CREDENTIALS_JSON", {"value": credentials_json})
        except Exception:
            # Create new secret
            client.post("/api/secrets", secret_data)


def sync_google_credentials_to_expertagent(project: str) -> None:
    """Sync Google credentials from MyVault to ExpertAgent."""
    api_config = config.get_api_config("expertagent")
    with HTTPClient(api_config, "ExpertAgent") as client:
        sync_data = {"project": project}
        client.post("/v1/google-auth/sync-from-myvault", sync_data)


def list_google_cached_projects() -> list[str]:
    """List projects with cached Google credentials in ExpertAgent."""
    api_config = config.get_api_config("expertagent")
    with HTTPClient(api_config, "ExpertAgent") as client:
        response = client.get("/v1/google-auth/list-projects")
        return response.get("projects", []) if isinstance(response, dict) else []


def start_google_oauth2_flow(project: str, redirect_uri: str | None = None) -> dict[str, Any]:
    """Start OAuth2 flow for Google authentication."""
    # Get redirect_uri dynamically from Streamlit config if not provided
    if redirect_uri is None:
        try:
            import streamlit as st_config
            port = st_config.config.get_option("server.port")
            redirect_uri = f"http://localhost:{port}"
        except Exception as e:
            # Fallback to default port
            st.sidebar.warning(f"⚠️ Could not detect port: {e}, using fallback 8501")
            redirect_uri = "http://localhost:8501"

    # Debug: Show detected redirect_uri
    st.sidebar.info(f"🔍 Using redirect_uri: {redirect_uri}")

    api_config = config.get_api_config("expertagent")
    with HTTPClient(api_config, "ExpertAgent") as client:
        request_data = {
            "project": project,
            "redirect_uri": redirect_uri
        }
        return client.post("/v1/google-auth/oauth2-start", request_data)


def complete_google_oauth2_flow(state: str, code: str, project: str | None = None) -> dict[str, Any]:
    """Complete OAuth2 flow with authorization code.

    Args:
        state: OAuth2 state parameter
        code: Authorization code from Google
        project: Optional project name (if None, uses stored value from state)

    Returns:
        Response dict with success status, message, and project name
    """
    api_config = config.get_api_config("expertagent")
    with HTTPClient(api_config, "ExpertAgent") as client:
        callback_data = {
            "state": state,
            "code": code,
            "project": project
        }
        return client.post("/v1/google-auth/oauth2-callback", callback_data)


def get_google_token_data(project: str) -> dict[str, Any]:
    """Get token.json data from ExpertAgent."""
    api_config = config.get_api_config("expertagent")
    with HTTPClient(api_config, "ExpertAgent") as client:
        params = {"project": project}
        return client.get("/v1/google-auth/token-data", params=params)


def save_google_token(project: str, token_json: str, save_to_myvault: bool = False) -> None:
    """Save token.json to ExpertAgent and optionally to MyVault."""
    api_config = config.get_api_config("expertagent")
    with HTTPClient(api_config, "ExpertAgent") as client:
        token_data = {
            "project": project,
            "token_json": token_json,
            "save_to_myvault": save_to_myvault
        }
        client.post("/v1/google-auth/save-token", token_data)


# ============================================================================
# OAuth2 Callback Handler (must be called outside tabs)
# ============================================================================

def handle_oauth2_callback():
    """Handle OAuth2 callback - must be called outside tabs to work correctly."""
    query_params = st.query_params

    # Debug: Always show query params check
    st.sidebar.write(f"🔍 Callback check: query_params = {dict(query_params)}")

    # Debug: Show query params
    if query_params:
        st.sidebar.write(f"DEBUG: Query params detected: {dict(query_params)}")

    if "code" in query_params and "state" in query_params:
        code = query_params["code"]
        state = query_params["state"]

        # State validation and project retrieval are performed on expertAgent side
        st.info("🔄 Completing OAuth2 authentication...")
        try:
            # Pass None for project - expertAgent will use the stored value
            response = complete_google_oauth2_flow(state, code, project=None)
            # Get project name from response
            callback_project = response.get("project", "default_project")

            st.success(f"✅ Token refreshed successfully for project: {callback_project}")
            st.info("✅ Token encrypted and cached locally in ExpertAgent")
            st.info("✅ Token automatically saved to MyVault")

            # Clear query params and session state
            if "oauth2_state" in st.session_state:
                del st.session_state.oauth2_state
            st.query_params.clear()

            # Restore selected project
            st.session_state.myvault_selected_project = callback_project
            st.rerun()

        except Exception as e:
            NotificationManager.handle_exception(e, "OAuth2 Callback")
            st.query_params.clear()
            st.rerun()


# ============================================================================
# Main function
# ============================================================================

def render_google_auth_section():
    """Render Google authentication management section."""
    selected_project = st.session_state.myvault_selected_project

    if not selected_project:
        st.info("👆 Select a project in the 'Projects' tab to manage Google authentication.")
        return

    st.subheader(f"🔑 Google Authentication for: {selected_project}")
    st.caption("Manage Google OAuth 2.0 credentials and tokens for this project")

    # Check if ExpertAgent is configured
    if not config.is_service_configured("expertagent"):
        st.warning("⚠️ ExpertAgent is not configured. Google authentication requires ExpertAgent.")
        st.info("""
        **Required Environment Variables:**
        - `EXPERTAGENT_BASE_URL`: ExpertAgent API base URL
        - `EXPERTAGENT_ADMIN_TOKEN`: Admin token for authentication
        """)
        return

    # Get token status from ExpertAgent
    col1, col2 = st.columns([3, 1])

    with col1:
        st.markdown("### 📊 Current Status")

    with col2:
        if st.button("🔄 Refresh Status", key="refresh_google_status", use_container_width=True):
            st.rerun()

    try:
        token_status = get_google_token_status(selected_project)

        # Display status
        status_cols = st.columns(3)

        with status_cols[0]:
            if token_status.get("exists"):
                st.success("✅ Credentials exist")
            else:
                st.error("❌ Credentials not found")

        with status_cols[1]:
            if token_status.get("is_valid"):
                st.success("✅ Token is valid")
            elif token_status.get("exists"):
                st.warning("⚠️ Token expired or invalid")
            else:
                st.info("ℹ️ No token")

        with status_cols[2]:
            st.info(f"📁 Project: {token_status.get('project', 'N/A')}")

        if token_status.get("error_message"):
            st.caption(f"Details: {token_status['error_message']}")

    except Exception as e:
        st.error(f"Failed to get status: {e!s}")
        token_status = {"exists": False, "is_valid": False}

    st.divider()

    # Credentials setup help section
    st.markdown("### 📝 Credentials Setup")

    with st.expander("ℹ️ How to get Google Credentials (credentials.json)", expanded=False):
        st.markdown("""
        **Google OAuth 2.0 Credentials の取得方法:**

        1. **Google Cloud Console にアクセス**
           - [Google Cloud Console - APIs & Services - Credentials](https://console.cloud.google.com/apis/credentials)

        2. **OAuth 2.0 Client ID を作成**
           - 「+ CREATE CREDENTIALS」→「OAuth client ID」を選択
           - Application type: **Web application** を選択
           - Name: 任意の名前（例: MySwiftAgent）

        3. **Authorized redirect URIs の設定（重要）**
           - **Authorized JavaScript origins**: `http://localhost:8601`
           - **Authorized redirect URIs**: `http://localhost:8601`

        4. **credentials.json をダウンロード**
           - 作成したクライアントIDの右側の「⬇ Download JSON」をクリック
           - ダウンロードしたJSONファイルの内容をコピー

        5. **MyVault に保存**
           - このページの「🔐 Secrets」タブに移動
           - 「🆕 Add Secret」をクリック
           - **Path**: `GOOGLE_CREDENTIALS_JSON`
           - **Value**: コピーしたJSONの内容を貼り付け
           - 「💾 Save」をクリック

        6. **ExpertAgent に同期**
           - 下記の「🔄 Sync to ExpertAgent」ボタンをクリック

        **参考リンク:**
        - [公式ガイド - Create credentials](https://developers.google.com/workspace/guides/create-credentials?hl=ja#desktop-app)
        """)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔄 Sync to ExpertAgent", key="sync_google_creds", type="primary", use_container_width=True):
            try:
                sync_google_credentials_to_expertagent(selected_project)
                st.success(f"✅ Credentials synced to ExpertAgent for project: {selected_project}")
                st.info("Credentials are now encrypted and cached locally in ExpertAgent")
                st.rerun()

            except Exception as e:
                NotificationManager.handle_exception(e, "Sync Google Credentials")

    with col2:
        if st.button("📋 List Cached Projects", key="list_google_projects", use_container_width=True):
            try:
                projects = list_google_cached_projects()
                if projects:
                    st.success(f"Cached projects in ExpertAgent: {', '.join(projects)}")
                else:
                    st.info("No projects cached in ExpertAgent yet")

            except Exception as e:
                NotificationManager.handle_exception(e, "List Google Projects")

    st.divider()

    # Token management section
    st.markdown("### 🎫 Token Management")
    st.caption("View and manage your Google OAuth 2.0 token (token.json)")

    # Get token data
    with st.expander("📄 View/Edit Token Data", expanded=False):
        try:
            token_data_response = get_google_token_data(selected_project)

            if token_data_response.get("exists"):
                token_json_content = token_data_response.get("token_json", "")

                st.info("✅ Token exists for this project")

                # Display token data
                token_json_edit = st.text_area(
                    "token.json content",
                    value=token_json_content,
                    height=300,
                    help="View or edit your Google OAuth 2.0 token"
                )

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("💾 Save Locally", key="save_token_local", use_container_width=True):
                        try:
                            # Validate JSON
                            import json
                            json.loads(token_json_edit)

                            # Save locally only
                            save_google_token(selected_project, token_json_edit, save_to_myvault=False)
                            st.success(f"✅ Token saved locally for project: {selected_project}")
                            st.info("Token is encrypted and cached in ExpertAgent")

                        except json.JSONDecodeError as e:
                            st.error(f"Invalid JSON format: {e!s}")
                        except Exception as e:
                            NotificationManager.handle_exception(e, "Save Token Locally")

                with col2:
                    if st.button("💾 Save to MyVault", key="save_token_myvault", type="primary", use_container_width=True):
                        try:
                            # Validate JSON
                            import json
                            json.loads(token_json_edit)

                            # Save to both local and MyVault
                            save_google_token(selected_project, token_json_edit, save_to_myvault=True)
                            st.success(f"✅ Token saved to MyVault for project: {selected_project}")
                            st.info("Token is now persisted in MyVault and encrypted locally")

                        except json.JSONDecodeError as e:
                            st.error(f"Invalid JSON format: {e!s}")
                        except Exception as e:
                            NotificationManager.handle_exception(e, "Save Token to MyVault")

            else:
                error_msg = token_data_response.get("error_message", "Unknown error")
                st.warning(f"⚠️ {error_msg}")
                st.info("Token will be created automatically when you complete OAuth2 flow")

        except Exception as e:
            st.error(f"Failed to get token data: {e!s}")

    st.divider()

    # Token refresh section
    st.markdown("### 🔄 Token Refresh")
    st.caption("Refresh your Google OAuth 2.0 token periodically to maintain access")

    if st.button("🔄 Refresh Token", key="refresh_google_token", type="secondary", use_container_width=True):
        try:
            # Start OAuth2 flow (project info is stored in expertAgent's state)
            # redirect_uri will be auto-detected from Streamlit config
            response = start_google_oauth2_flow(selected_project)
            auth_url = response.get("auth_url")
            state = response.get("state")

            if auth_url and state:
                # Store state in session (may be lost after redirect, but kept for reference)
                st.session_state.oauth2_state = state

                st.info("🌐 Opening Google authentication in new window...")
                st.markdown(f"[🔗 Click here to authenticate with Google]({auth_url})")
                st.caption("After authentication, you will be redirected back to this page")
            else:
                st.error("Failed to start OAuth2 flow")

        except Exception as e:
            NotificationManager.handle_exception(e, "Start OAuth2 Flow")



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

    # Handle OAuth2 callback BEFORE creating tabs
    # This ensures callback is processed regardless of which tab is active
    handle_oauth2_callback()

    # Create tabs for different sections
    tab1, tab2, tab3 = st.tabs(["📁 Projects", "🔐 Secrets", "🔑 Google認証"])

    with tab1:
        render_projects_section()

    with tab2:
        render_secrets_section()

    with tab3:
        render_google_auth_section()


if __name__ == "__main__":
    main()
