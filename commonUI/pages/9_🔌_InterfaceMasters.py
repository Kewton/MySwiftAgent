"""
InterfaceMaster Management Page

Streamlit page for managing InterfaceMasters including creation, editing,
deletion, and JSON Schema validation.
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
    page_title="InterfaceMasters - CommonUI",
    page_icon="🔌",
    layout="wide",
)

# JSON Schema Templates
SCHEMA_TEMPLATES = {
    "Empty Schema": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {},
        "required": []
    },
    "Simple Object": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "name": {"type": "string"},
        },
        "required": ["id", "name"]
    },
    "Company Search": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "company_name": {"type": "string"},
            "country": {"type": "string"},
            "industry": {"type": "string"}
        },
        "required": ["company_name"]
    },
    "API Response": {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": ["success", "error"]},
            "data": {"type": "object"},
            "message": {"type": "string"}
        },
        "required": ["status"]
    },
}


def initialize_session_state() -> None:
    """Initialize session state variables for InterfaceMasters page."""
    if "interface_masters_list" not in st.session_state:
        st.session_state.interface_masters_list = []
    if "selected_interface_id" not in st.session_state:
        st.session_state.selected_interface_id = None
    if "interface_detail" not in st.session_state:
        st.session_state.interface_detail = None


def load_interface_masters() -> None:
    """Load InterfaceMasters from API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            response = client.get("/api/v1/interface-masters", params={"size": 100})
            st.session_state.interface_masters_list = response.get("interfaces", [])

    except Exception as e:
        NotificationManager.handle_exception(e, "Load InterfaceMasters")
        st.session_state.interface_masters_list = []


def create_interface_master(interface_data: dict[str, Any]) -> None:
    """Create a new InterfaceMaster via API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            NotificationManager.operation_started("Creating InterfaceMaster")

            response = client.post("/api/v1/interface-masters", interface_data)

            interface_id = response.get("id")
            NotificationManager.operation_completed("InterfaceMaster creation")
            NotificationManager.success(
                f"InterfaceMaster created successfully! ID: {interface_id}",
            )

            # Refresh interface master list
            load_interface_masters()

    except Exception as e:
        NotificationManager.handle_exception(e, "InterfaceMaster Creation")


def update_interface_master(interface_id: str, interface_data: dict[str, Any]) -> None:
    """Update an existing InterfaceMaster via API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            NotificationManager.operation_started("Updating InterfaceMaster")

            client.put(f"/api/v1/interface-masters/{interface_id}", interface_data)

            NotificationManager.operation_completed("InterfaceMaster update")
            NotificationManager.success("InterfaceMaster updated successfully!")

            # Refresh interface master list
            load_interface_masters()

            # Refresh detail if currently viewing
            if st.session_state.selected_interface_id == interface_id:
                load_interface_detail(interface_id)

    except Exception as e:
        NotificationManager.handle_exception(e, "InterfaceMaster Update")


def delete_interface_master(interface_id: str) -> None:
    """Delete (deactivate) an InterfaceMaster via API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            NotificationManager.operation_started("Deleting InterfaceMaster")

            client.delete(f"/api/v1/interface-masters/{interface_id}")

            NotificationManager.operation_completed("InterfaceMaster deletion")
            NotificationManager.success("InterfaceMaster deactivated successfully!")

            # Clear selection if deleted
            if st.session_state.selected_interface_id == interface_id:
                st.session_state.selected_interface_id = None
                st.session_state.interface_detail = None

            # Refresh interface master list
            load_interface_masters()

    except Exception as e:
        NotificationManager.handle_exception(e, "InterfaceMaster Deletion")


def load_interface_detail(interface_id: str) -> None:
    """Load InterfaceMaster detail from API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            interface_detail = client.get(f"/api/v1/interface-masters/{interface_id}")
            st.session_state.interface_detail = interface_detail

    except Exception as e:
        NotificationManager.handle_exception(e, "Load InterfaceMaster Detail")
        st.session_state.interface_detail = None


def validate_json_schema(schema_str: str) -> tuple[bool, str | None, dict[str, Any] | None]:
    """Validate JSON Schema syntax.

    Returns:
        (is_valid, error_message, parsed_schema)
    """
    try:
        schema = json.loads(schema_str)

        # Basic validation - check for required Draft 7 fields
        if not isinstance(schema, dict):
            return (False, "Schema must be a JSON object", None)

        if "$schema" not in schema:
            return (False, "Missing $schema field (use Draft 7)", None)

        if "type" not in schema:
            return (False, "Missing type field", None)

        return (True, None, schema)

    except json.JSONDecodeError as e:
        return (False, f"Invalid JSON: {e}", None)


def render_schema_editor(
    label: str,
    initial_value: dict[str, Any] | None = None,
    key_prefix: str = "",
) -> tuple[str, bool, str | None]:
    """Render JSON Schema editor with template selector and validation.

    Returns:
        (schema_text, is_valid, error_message)
    """
    st.write(f"**{label}**")

    # Template selector
    template_options = ["Custom"] + list(SCHEMA_TEMPLATES.keys())
    selected_template = st.selectbox(
        "Template",
        options=template_options,
        key=f"{key_prefix}_template",
        help="Select a template to start with",
    )

    # Get initial schema text
    if selected_template != "Custom" and selected_template in SCHEMA_TEMPLATES:
        initial_schema = SCHEMA_TEMPLATES[selected_template]
    elif initial_value:
        initial_schema = initial_value
    else:
        initial_schema = SCHEMA_TEMPLATES["Empty Schema"]

    initial_text = json.dumps(initial_schema, indent=2)

    # JSON editor
    schema_text = st.text_area(
        "JSON Schema (Draft 7)",
        value=initial_text,
        height=300,
        key=f"{key_prefix}_schema",
        help="Enter JSON Schema definition conforming to Draft 7 specification",
    )

    # Validate schema
    is_valid, error_message, _ = validate_json_schema(schema_text)

    # Show validation status
    if is_valid:
        st.success("✅ Valid JSON Schema")
    else:
        st.error(f"❌ {error_message}")

    return (schema_text, is_valid, error_message)


def render_interface_master_form(mode: str = "create", initial_data: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Render InterfaceMaster creation/edit form.

    Args:
        mode: "create" or "edit"
        initial_data: Initial form values for edit mode

    Returns:
        Form data dict if submitted, None otherwise
    """
    initial_data = initial_data or {}

    with st.form(f"interface_master_form_{mode}"):
        st.subheader("📋 Basic Information")

        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input(
                "Name *",
                value=initial_data.get("name", ""),
                placeholder="e.g., CompanySearchInterface",
                help="Unique identifier name for this InterfaceMaster",
            )

        with col2:
            description = st.text_input(
                "Description",
                value=initial_data.get("description", ""),
                placeholder="e.g., Interface for company search input/output",
                help="Brief description of what this interface represents",
            )

        st.divider()
        st.subheader("📥 Input Schema (JSON Schema Draft 7)")

        input_schema_text, input_valid, input_error = render_schema_editor(
            "Input Schema",
            initial_value=initial_data.get("input_schema"),
            key_prefix=f"{mode}_input",
        )

        st.divider()
        st.subheader("📤 Output Schema (JSON Schema Draft 7)")

        output_schema_text, output_valid, output_error = render_schema_editor(
            "Output Schema",
            initial_value=initial_data.get("output_schema"),
            key_prefix=f"{mode}_output",
        )

        st.divider()
        st.subheader("⚙️ Advanced Settings")

        is_active = st.checkbox(
            "Is Active",
            value=initial_data.get("is_active", True),
            help="Whether this InterfaceMaster is active and can be used",
        )

        # Submit button
        submitted = st.form_submit_button(
            f"{'✨ Create InterfaceMaster' if mode == 'create' else '💾 Update InterfaceMaster'}",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            # Validate required fields
            if not name:
                st.error("❌ Name is required")
                return None

            # Validate schemas
            if not input_valid:
                st.error(f"❌ Invalid input schema: {input_error}")
                return None

            if not output_valid:
                st.error(f"❌ Invalid output schema: {output_error}")
                return None

            # Parse schemas
            _, _, input_schema = validate_json_schema(input_schema_text)
            _, _, output_schema = validate_json_schema(output_schema_text)

            # Build form data
            form_data: dict[str, Any] = {
                "name": name,
                "description": description,
                "input_schema": input_schema,
                "output_schema": output_schema,
                "is_active": is_active,
            }

            return form_data

    return None


def render_create_interface_master_tab() -> None:
    """Render create InterfaceMaster tab."""
    st.subheader("🆕 Create New InterfaceMaster")
    st.caption("Create a reusable interface schema for input/output validation")

    form_data = render_interface_master_form(mode="create")

    if form_data:
        create_interface_master(form_data)


def render_list_interface_masters_tab() -> None:
    """Render list InterfaceMasters tab with filtering and detail view."""
    st.subheader("📋 InterfaceMaster List")

    # Filters
    col1, col2, col3 = st.columns([2, 2, 3])

    with col1:
        is_active_filter = st.selectbox(
            "Status Filter",
            ["All", "Active", "Inactive"],
            help="Filter by active/inactive status",
        )

    with col2:
        schema_filter = st.selectbox(
            "Schema Filter",
            ["All", "Has Input", "Has Output", "Has Both"],
            help="Filter by schema presence",
        )

    with col3:
        search_query = st.text_input(
            "Search",
            placeholder="Search by name or ID",
            help="Search InterfaceMasters by name or ID",
        )

    # Refresh button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refresh", key="refresh_list", use_container_width=True):
            load_interface_masters()
            st.rerun()

    # Display interface masters
    interface_masters = st.session_state.interface_masters_list
    if not interface_masters:
        st.info("No InterfaceMasters found. Create your first InterfaceMaster using the Create tab.")
        return

    # Filter interface masters
    filtered_masters = filter_interface_masters(
        interface_masters,
        is_active_filter,
        schema_filter,
        search_query,
    )

    if not filtered_masters:
        st.warning("No InterfaceMasters match the current filters.")
        return

    # Convert to DataFrame for better display
    display_masters = [
        {
            "id": m["id"],
            "name": m["name"],
            "description": m.get("description", "")[:50] + "..."
            if len(m.get("description", "")) > 50
            else m.get("description", ""),
            "has_input": "✓" if m.get("input_schema") else "✗",
            "has_output": "✓" if m.get("output_schema") else "✗",
            "is_active": "✅ Active" if m.get("is_active") else "❌ Inactive",
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
            "id": "InterfaceMaster ID",
            "name": "Name",
            "description": "Description",
            "has_input": "Input Schema",
            "has_output": "Output Schema",
            "is_active": "Status",
        },
    )

    # Handle row selection
    if hasattr(event, "selection") and event.selection.rows:  # type: ignore[attr-defined]
        selected_idx = event.selection.rows[0]  # type: ignore[attr-defined]
        selected_master = filtered_masters[selected_idx]
        st.session_state.selected_interface_id = selected_master["id"]
        load_interface_detail(selected_master["id"])

    st.divider()

    # Display interface master detail if selected
    if st.session_state.selected_interface_id and st.session_state.interface_detail:
        render_interface_detail()


def filter_interface_masters(
    interface_masters: list[dict],
    is_active_filter: str,
    schema_filter: str,
    search_query: str,
) -> list[dict]:
    """Filter interface masters based on criteria."""
    filtered = interface_masters

    # Active/Inactive filter
    if is_active_filter == "Active":
        filtered = [m for m in filtered if m.get("is_active")]
    elif is_active_filter == "Inactive":
        filtered = [m for m in filtered if not m.get("is_active")]

    # Schema filter
    if schema_filter == "Has Input":
        filtered = [m for m in filtered if m.get("input_schema")]
    elif schema_filter == "Has Output":
        filtered = [m for m in filtered if m.get("output_schema")]
    elif schema_filter == "Has Both":
        filtered = [
            m
            for m in filtered
            if m.get("input_schema") and m.get("output_schema")
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


def render_interface_detail() -> None:
    """Render detailed InterfaceMaster information and controls."""
    interface_detail = st.session_state.interface_detail
    interface_id = st.session_state.selected_interface_id

    if not interface_detail:
        return

    st.subheader(f"📄 InterfaceMaster Details - {interface_detail.get('name', interface_id)}")

    # Action buttons
    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("✏️ Edit", key="edit_interface", use_container_width=True):
            st.session_state.edit_mode = True

    with col2:
        if interface_detail.get("is_active") and st.button(
            "🗑️ Delete",
            key="delete_interface",
            use_container_width=True,
        ):
            if st.session_state.get("confirm_delete") == interface_id:
                delete_interface_master(interface_id)
                st.session_state.confirm_delete = None
            else:
                st.session_state.confirm_delete = interface_id
                st.warning("⚠️ Click Delete again to confirm")

    with col3:
        if st.button("🔄 Refresh", key="refresh_detail", use_container_width=True):
            load_interface_detail(interface_id)

    # Show edit form if in edit mode
    if st.session_state.get("edit_mode"):
        st.divider()
        st.subheader("✏️ Edit InterfaceMaster")

        form_data = render_interface_master_form(
            mode="edit",
            initial_data=interface_detail,
        )

        if form_data:
            update_interface_master(interface_id, form_data)
            st.session_state.edit_mode = False
            st.rerun()

        if st.button("❌ Cancel Edit"):
            st.session_state.edit_mode = False
            st.rerun()

    # InterfaceMaster detail tabs
    st.divider()
    tab1, tab2, tab3 = st.tabs(["📋 Schemas", "🔗 Usage", "⚙️ Config"])

    with tab1:
        # Display schemas
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📥 Input Schema")
            input_schema = interface_detail.get("input_schema")
            if input_schema:
                st.json(input_schema)

                # Show property tree
                with st.expander("Property Tree"):
                    render_property_tree(input_schema)
            else:
                st.info("No input schema defined")

        with col2:
            st.subheader("📤 Output Schema")
            output_schema = interface_detail.get("output_schema")
            if output_schema:
                st.json(output_schema)

                # Show property tree
                with st.expander("Property Tree"):
                    render_property_tree(output_schema)
            else:
                st.info("No output schema defined")

    with tab2:
        # Display TaskMasters using this interface
        st.subheader("🔧 TaskMasters Using This Interface")

        try:
            api_config = config.get_api_config("JobQueue")
            with HTTPClient(api_config, "JobQueue") as client:
                response = client.get(
                    f"/api/v1/interface-masters/{interface_id}/task-masters"
                )
                task_masters = response.get("task_masters", [])

                if task_masters:
                    task_df = pd.DataFrame(
                        [
                            {
                                "Name": tm.get("name", ""),
                                "Usage": tm.get("usage_type", ""),
                                "Method": tm.get("method", ""),
                            }
                            for tm in task_masters
                        ]
                    )
                    st.dataframe(task_df, use_container_width=True, hide_index=True)
                else:
                    st.info("No TaskMasters are currently using this interface")

        except Exception as e:
            st.warning(f"Could not load usage information: {e}")

    with tab3:
        # Display key configuration
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Is Active", "✅ Yes" if interface_detail.get("is_active") else "❌ No")
            st.metric("Created At", interface_detail.get("created_at", "N/A"))

        with col2:
            st.metric("Updated At", interface_detail.get("updated_at", "N/A"))


def render_property_tree(schema: dict[str, Any]) -> None:
    """Render schema property tree visualization."""
    properties = schema.get("properties", {})
    required = schema.get("required", [])

    if not properties:
        st.write("_No properties defined_")
        return

    for prop_name, prop_def in properties.items():
        prop_type = prop_def.get("type", "unknown")
        is_required = "✳️" if prop_name in required else ""

        # Format property line
        line = f"- **{prop_name}** {is_required}: `{prop_type}`"

        # Add enum info if present
        if "enum" in prop_def:
            enum_values = ", ".join([str(v) for v in prop_def["enum"]])
            line += f" (enum: {enum_values})"

        st.write(line)

        # Show description if present
        if "description" in prop_def:
            st.caption(f"  _{prop_def['description']}_")


def main() -> None:
    """Main InterfaceMasters page function."""
    # Initialize session state
    initialize_session_state()

    # Render sidebar
    SidebarManager.render_complete_sidebar()

    # Page header
    st.title("🔌 InterfaceMaster Management")
    st.caption("Manage reusable interface schemas for input/output validation")

    # Check if service is configured
    if not config.is_service_configured("JobQueue"):
        st.error(
            "❌ JobQueue is not configured. Please check your environment settings.",
        )
        st.stop()

    # Load initial data
    if not st.session_state.interface_masters_list:
        load_interface_masters()

    # Main content tabs
    tab1, tab2 = st.tabs(
        ["🆕 Create InterfaceMaster", "📋 List InterfaceMasters"],
    )

    with tab1:
        render_create_interface_master_tab()

    with tab2:
        render_list_interface_masters_tab()


if __name__ == "__main__":
    main()
