"""Job Master form component for creating and editing masters."""

import json
from typing import Any

import streamlit as st

from components.template_manager import TemplateManager


class JobMasterForm:
    """Job Master form component for CRUD operations."""

    @staticmethod
    def render_master_form(
        mode: str = "create",
        initial_data: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """
        Render job master creation/edit form.

        Args:
            mode: Form mode ("create" or "edit")
            initial_data: Initial form data for edit mode

        Returns:
            Form data if submitted, None otherwise
        """
        initial_data = initial_data or {}

        # Template management (create mode only)
        if mode == "create":
            template_mgr = TemplateManager("job_masters")

            # Collect current form data for template saving
            current_template_data = {
                "name": st.session_state.get("master_form_name", ""),
                "description": st.session_state.get("master_form_description", ""),
                "method": st.session_state.get("master_form_method", "GET"),
                "url": st.session_state.get("master_form_url", ""),
                "headers": st.session_state.get("master_form_headers", ""),
                "params": st.session_state.get("master_form_params", ""),
                "body": st.session_state.get("master_form_body", ""),
                "timeout_sec": st.session_state.get("master_form_timeout", 30),
                "max_attempts": st.session_state.get("master_form_max_attempts", 1),
                "backoff_strategy": st.session_state.get(
                    "master_form_backoff_strategy",
                    "exponential",
                ),
                "backoff_seconds": st.session_state.get(
                    "master_form_backoff_seconds",
                    5.0,
                ),
                "tags": st.session_state.get("master_form_tags", ""),
            }

            # Render template selector
            loaded_template = template_mgr.render_template_selector(
                current_template_data,
            )

            # Apply loaded template to form (only once)
            if loaded_template:
                template_key = f"master_template_{hash(str(loaded_template))}"

                if not st.session_state.get(template_key, False):
                    for key, value in loaded_template.items():
                        st.session_state[f"master_form_{key}"] = value
                    st.session_state[template_key] = True

                    # Clear other template flags
                    keys_to_clear = [
                        k
                        for k in st.session_state
                        if k.startswith("master_template_") and k != template_key
                    ]
                    for k in keys_to_clear:
                        del st.session_state[k]

            st.divider()

        # Form
        with st.form(f"job_master_form_{mode}"):
            # Basic Information
            st.subheader("📋 Basic Information")

            name = st.text_input(
                "Name*",
                value=initial_data.get("name", ""),
                key=f"master_form_name_{mode}",
                placeholder="API Notification Master",
                help="Unique identifier for the job master template",
            )

            description = st.text_area(
                "Description",
                value=initial_data.get("description", ""),
                key=f"master_form_description_{mode}",
                placeholder="Describe what this master template does...",
                help="Optional description of the master template purpose",
                height=80,
            )

            st.divider()

            # HTTP Request Configuration
            st.subheader("🌐 HTTP Request Configuration")

            col1, col2 = st.columns([3, 1])

            with col1:
                url = st.text_input(
                    "URL*",
                    value=initial_data.get("url", ""),
                    key=f"master_form_url_{mode}",
                    placeholder="https://api.example.com/v1/endpoint",
                    help="Target API endpoint URL",
                )

            with col2:
                methods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
                current_method = initial_data.get("method", "GET")
                method_index = (
                    methods.index(current_method) if current_method in methods else 0
                )

                method = st.selectbox(
                    "Method*",
                    methods,
                    index=method_index,
                    key=f"master_form_method_{mode}",
                    help="HTTP method",
                )

            timeout_sec = st.number_input(
                "Timeout (seconds)",
                min_value=1,
                max_value=3600,
                value=initial_data.get("timeout_sec", 30),
                key=f"master_form_timeout_{mode}",
                help="Request timeout in seconds (max: 3600)",
            )

            st.divider()

            # Request Configuration
            st.subheader("📋 Request Configuration")
            st.caption("Configure default HTTP request parameters (all optional)")

            # Headers
            headers_default = ""
            if initial_data.get("headers"):
                headers_default = json.dumps(initial_data["headers"], indent=2)

            headers = st.text_area(
                "Headers (JSON)",
                value=headers_default,
                key=f"master_form_headers_{mode}",
                placeholder='{\n  "Content-Type": "application/json",\n  "Authorization": "Bearer your-token"\n}',
                help="HTTP headers in JSON format",
                height=100,
            )

            # Query Parameters
            params_default = ""
            if initial_data.get("params"):
                params_default = json.dumps(initial_data["params"], indent=2)

            params = st.text_area(
                "Query Parameters (JSON)",
                value=params_default,
                key=f"master_form_params_{mode}",
                placeholder='{\n  "page": 1,\n  "limit": 100\n}',
                help="Query parameters in JSON format",
                height=80,
            )

            # Request Body
            body_default = ""
            if initial_data.get("body"):
                body_default = json.dumps(initial_data["body"], indent=2)

            body = st.text_area(
                "Request Body (JSON)",
                value=body_default,
                key=f"master_form_body_{mode}",
                placeholder='{\n  "event": "notification",\n  "data": {}\n}',
                help="Request body in JSON format (supports deep merge on override)",
                height=120,
            )

            st.divider()

            # Retry Configuration
            st.subheader("🔄 Retry Configuration")

            col1, col2, col3 = st.columns(3)

            with col1:
                max_attempts = st.number_input(
                    "Max Attempts",
                    min_value=1,
                    max_value=10,
                    value=initial_data.get("max_attempts", 1),
                    key=f"master_form_max_attempts_{mode}",
                    help="Maximum retry attempts (1-10)",
                )

            with col2:
                backoff_strategies = ["fixed", "linear", "exponential"]
                current_strategy = initial_data.get("backoff_strategy", "exponential")
                strategy_index = (
                    backoff_strategies.index(current_strategy)
                    if current_strategy in backoff_strategies
                    else 2
                )

                backoff_strategy = st.selectbox(
                    "Backoff Strategy",
                    backoff_strategies,
                    index=strategy_index,
                    key=f"master_form_backoff_strategy_{mode}",
                    help="Retry backoff strategy",
                )

            with col3:
                backoff_seconds = st.number_input(
                    "Backoff Seconds",
                    min_value=0.1,
                    max_value=300.0,
                    value=initial_data.get("backoff_seconds", 5.0),
                    step=0.5,
                    key=f"master_form_backoff_seconds_{mode}",
                    help="Base backoff time in seconds",
                )

            st.divider()

            # TTL and Tags
            st.subheader("⚙️ Additional Settings")

            col1, col2 = st.columns(2)

            with col1:
                ttl_seconds = st.number_input(
                    "TTL (seconds)",
                    min_value=0,
                    max_value=31536000,  # 1 year
                    value=initial_data.get("ttl_seconds", 604800),  # 7 days default
                    key=f"master_form_ttl_{mode}",
                    help="Time to live for jobs created from this master (default: 7 days)",
                )

            with col2:
                tags_default = ""
                if initial_data.get("tags"):
                    tags_default = ", ".join(initial_data["tags"])

                tags = st.text_input(
                    "Tags (comma-separated)",
                    value=tags_default,
                    key=f"master_form_tags_{mode}",
                    placeholder="api, webhook, notification",
                    help="Tags for categorizing the master",
                )

            # Submit button
            submitted = st.form_submit_button(
                f"{'🚀 Create' if mode == 'create' else '💾 Update'} Master",
                type="primary",
                use_container_width=True,
            )

            if submitted:
                # Validation
                if not name or not name.strip():
                    st.error("❌ Name is required")
                    return None

                if not url or not url.strip():
                    st.error("❌ URL is required")
                    return None

                # Parse JSON fields
                try:
                    headers_dict = json.loads(headers) if headers.strip() else None
                    params_dict = json.loads(params) if params.strip() else None
                    body_dict = json.loads(body) if body.strip() else None

                    # Parse tags
                    tags_list = (
                        [tag.strip() for tag in tags.split(",") if tag.strip()]
                        if tags
                        else None
                    )

                    # Build and return form data
                    return {
                        "name": name.strip(),
                        "description": description.strip()
                        if description.strip()
                        else None,
                        "method": method,
                        "url": url.strip(),
                        "headers": headers_dict,
                        "params": params_dict,
                        "body": body_dict,
                        "timeout_sec": timeout_sec,
                        "max_attempts": max_attempts,
                        "backoff_strategy": backoff_strategy,
                        "backoff_seconds": backoff_seconds,
                        "ttl_seconds": ttl_seconds,
                        "tags": tags_list,
                    }

                except json.JSONDecodeError as e:
                    st.error(f"❌ Invalid JSON format: {e}")
                    st.info(
                        "💡 Please check your Headers, Query Parameters, or Request Body fields",
                    )
                    return None

        return None
