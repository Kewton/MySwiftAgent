"""
JobQueue Management Page

Streamlit page for managing job queue operations including job creation,
monitoring, and execution control.
"""

import time
from typing import Any

import pandas as pd
import streamlit as st

from components.http_client import HTTPClient
from components.notifications import NotificationManager
from components.sidebar import SidebarManager
from core.config import config

# Page configuration
st.set_page_config(
    page_title="JobQueue - CommonUI",
    page_icon="📋",
    layout="wide",
)


def initialize_session_state() -> None:
    """Initialize session state variables for JobQueue page."""
    if "jobqueue_jobs" not in st.session_state:
        st.session_state.jobqueue_jobs = []
    if "jobqueue_selected_job" not in st.session_state:
        st.session_state.jobqueue_selected_job = None
    if "jobqueue_auto_refresh" not in st.session_state:
        st.session_state.jobqueue_auto_refresh = False


def render_job_creation_form() -> None:
    """Render job creation form."""
    st.subheader("🆕 Create New Job")

    # Template management
    from components.template_manager import TemplateManager

    template_mgr = TemplateManager("jobqueue")

    # Collect current form data for template saving
    current_template_data = {
        "api_url": st.session_state.get("jobqueue_api_url_outside", ""),
        "api_method": st.session_state.get("jobqueue_current_api_method", "POST"),
        "api_headers": st.session_state.get("jobqueue_api_headers_outside", ""),
        "api_query_params": st.session_state.get(
            "jobqueue_api_query_params_outside", "",
        ),
        "api_body": st.session_state.get("jobqueue_api_body_outside", ""),
        "body_type": st.session_state.get("jobqueue_body_type_outside", "JSON"),
    }

    # Render template selector and get loaded template
    loaded_template = template_mgr.render_template_selector(current_template_data)

    # Apply loaded template to session state (only once when template changes)
    if loaded_template:
        # Use a flag to track if we've already applied this template
        template_key = f"jobqueue_loaded_template_{hash(str(loaded_template))}"

        if template_key not in st.session_state or not st.session_state.get(
            template_key, False,
        ):
            st.session_state["jobqueue_api_url_outside"] = loaded_template.get(
                "api_url", "",
            )
            st.session_state["jobqueue_current_api_method"] = loaded_template.get(
                "api_method", "POST",
            )
            st.session_state["jobqueue_api_headers_outside"] = loaded_template.get(
                "api_headers", "",
            )
            st.session_state["jobqueue_api_query_params_outside"] = loaded_template.get(
                "api_query_params", "",
            )
            st.session_state["jobqueue_api_body_outside"] = loaded_template.get(
                "api_body", "",
            )
            st.session_state["jobqueue_body_type_outside"] = loaded_template.get(
                "body_type", "JSON",
            )
            st.session_state["jobqueue_current_body_type"] = loaded_template.get(
                "body_type", "JSON",
            )
            st.session_state[template_key] = True

            # Clear other template flags
            keys_to_clear = [
                k
                for k in st.session_state
                if k.startswith("jobqueue_loaded_template_") and k != template_key
            ]
            for k in keys_to_clear:
                del st.session_state[k]

    st.divider()

    # Move API configuration outside the form to enable real-time conditional rendering
    st.subheader("🔗 API Configuration (Optional)")
    st.caption("Configure API settings if this job needs to make external API calls")

    col1, col2 = st.columns([3, 1])
    with col1:
        # Initialize session state if not exists
        if "jobqueue_api_url_outside" not in st.session_state:
            st.session_state["jobqueue_api_url_outside"] = ""

        api_url = st.text_input(
            "🌐 API Endpoint URL",
            key="jobqueue_api_url_outside",
            placeholder="https://api.example.com/v1/endpoint",
            help="Target API endpoint URL",
        )
    with col2:
        # Get method index
        methods = ["GET", "POST", "PUT", "PATCH", "DELETE"]
        current_method = st.session_state.get("jobqueue_current_api_method", "POST")
        method_index = methods.index(current_method) if current_method in methods else 1

        api_method = st.selectbox(
            "📡 HTTP Method",
            methods,
            key="jobqueue_api_method_outside",
            index=method_index,
            help="HTTP method",
        )

    # Store in session state for form access
    st.session_state["jobqueue_current_api_method"] = api_method
    st.session_state["jobqueue_current_api_url"] = api_url

    # Headers configuration (outside form for consistency)
    st.subheader("📋 Request Headers")
    st.caption(
        "HTTP headers to include in the API request (Content-Type, Authorization, etc.)",
    )

    # Initialize session state if not exists
    if "jobqueue_api_headers_outside" not in st.session_state:
        st.session_state["jobqueue_api_headers_outside"] = ""

    api_headers = st.text_area(
        "Headers (JSON format)",
        key="jobqueue_api_headers_outside",
        placeholder='{\n  "Content-Type": "application/json",\n  "Authorization": "Bearer your-api-token",\n  "X-Custom-Header": "custom-value"\n}',
        help="HTTP headers in JSON format - commonly used for authentication and content type specification",
        height=100,
    )
    st.session_state["jobqueue_current_api_headers"] = api_headers

    # Query parameters (for GET/DELETE) - conditional rendering works outside form
    if api_method in ["GET", "DELETE"]:
        st.subheader("🔍 URL Query Parameters")
        st.caption("Parameters that will be added to the URL (e.g., ?page=1&limit=100)")

        # Initialize session state if not exists
        if "jobqueue_api_query_params_outside" not in st.session_state:
            st.session_state["jobqueue_api_query_params_outside"] = ""

        api_query_params = st.text_area(
            "Query Parameters (JSON format)",
            key="jobqueue_api_query_params_outside",
            placeholder='{\n  "page": 1,\n  "limit": 100,\n  "filter": "active",\n  "sort": "created_at"\n}',
            help="Query parameters in JSON format - will be appended to the URL as ?key=value",
            height=80,
        )
        st.session_state["jobqueue_current_api_query_params"] = api_query_params
    else:
        st.session_state["jobqueue_current_api_query_params"] = ""

    # Request body (for POST/PUT/PATCH) - conditional rendering works outside form
    if api_method in ["POST", "PUT", "PATCH"]:
        st.subheader("📤 Request Body Data")
        st.caption("Data to send in the request body")

        # Get body type index
        body_types = ["JSON", "Form Data", "Raw Text"]
        current_body_type = st.session_state.get("jobqueue_body_type_outside", "JSON")
        body_type_index = (
            body_types.index(current_body_type)
            if current_body_type in body_types
            else 0
        )

        body_type = st.selectbox(
            "Body Data Type",
            body_types,
            key="jobqueue_body_type_outside",
            index=body_type_index,
            help="Format of the request body data",
        )

        # Initialize session state if not exists
        if "jobqueue_api_body_outside" not in st.session_state:
            st.session_state["jobqueue_api_body_outside"] = ""

        if body_type == "JSON":
            api_body = st.text_area(
                "JSON Body Data",
                key="jobqueue_api_body_outside",
                placeholder='{\n  "name": "example",\n  "data": {\n    "field1": "value1",\n    "field2": 123,\n    "active": true\n  }\n}',
                help="JSON data to send in the request body",
                height=120,
            )
        elif body_type == "Form Data":
            api_body = st.text_area(
                "Form Fields Data (JSON format)",
                key="jobqueue_api_body_outside",
                placeholder='{\n  "username": "john_doe",\n  "email": "john@example.com",\n  "age": 30\n}',
                help="Form fields as JSON - will be sent as application/x-www-form-urlencoded",
                height=120,
            )
        else:  # Raw Text
            api_body = st.text_area(
                "Raw Text Body",
                key="jobqueue_api_body_outside",
                placeholder="Plain text content to send as request body",
                help="Raw text content for request body",
                height=120,
            )
        st.session_state["jobqueue_current_api_body"] = api_body
        st.session_state["jobqueue_current_body_type"] = body_type
    else:
        st.session_state["jobqueue_current_api_body"] = ""
        st.session_state["jobqueue_current_body_type"] = "JSON"

    st.divider()

    with st.form("job_creation_form"):
        # Basic job information
        st.subheader("📋 Basic Information")
        col1, col2 = st.columns(2)

        with col1:
            job_name = st.text_input(
                "Job Name*",
                placeholder="Enter job name",
                help="Unique identifier for the job",
            )

            job_type = st.selectbox(
                "Job Type*",
                [
                    "api_sync",
                    "data_processing",
                    "batch_analysis",
                    "file_conversion",
                    "custom",
                ],
                help="Select the type of job to execute",
            )

            priority = st.selectbox(
                "Priority",
                ["low", "normal", "high", "urgent"],
                index=1,
                help="Job execution priority",
            )

        with col2:
            max_retries = st.number_input(
                "Max Retries",
                min_value=0,
                max_value=10,
                value=3,
                help="Maximum number of retry attempts",
            )

            timeout = st.number_input(
                "Timeout (seconds)",
                min_value=10,
                max_value=3600,
                value=300,
                help="Job execution timeout",
            )

        # Get API configuration from session state (set outside form)
        api_method = st.session_state.get("jobqueue_current_api_method", "POST")
        api_url = st.session_state.get("jobqueue_current_api_url", "")
        api_headers = st.session_state.get("jobqueue_current_api_headers", "")
        api_query_params = st.session_state.get("jobqueue_current_api_query_params", "")
        api_body = st.session_state.get("jobqueue_current_api_body", "")
        body_type = st.session_state.get("jobqueue_current_body_type", "JSON")

        # Job parameters
        st.divider()
        st.subheader("⚙️ Job Parameters")

        # Job type specific parameter hints
        parameter_placeholder = get_parameter_placeholder(job_type)

        parameters = st.text_area(
            "Parameters (JSON)",
            placeholder=parameter_placeholder,
            help="Job-specific parameters in JSON format",
            height=120,
        )

        # Tags
        tags = st.text_input(
            "Tags (comma-separated)",
            placeholder="tag1, tag2, tag3",
            help="Optional tags for job categorization",
        )

        submitted = st.form_submit_button(
            "🚀 Create Job",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            if not job_name:
                st.error("Job name is required")
                return

            try:
                # Parse job parameters
                import json

                job_params = json.loads(parameters) if parameters.strip() else {}

                # Parse tags
                job_tags = (
                    [tag.strip() for tag in tags.split(",") if tag.strip()]
                    if tags
                    else []
                )

                # Build API configuration if any API settings are provided
                api_config = {}
                if api_url.strip():  # Only include API config if URL is provided
                    api_config = {
                        "url": api_url,
                        "method": api_method,
                    }

                    # Parse and add headers
                    if api_headers.strip():
                        try:
                            headers = json.loads(api_headers)
                            api_config["headers"] = headers
                        except json.JSONDecodeError as e:
                            st.error(f"Invalid JSON in Request Headers field: {e!s}")
                            return

                    # Parse and add query parameters
                    if api_query_params.strip():
                        try:
                            query_params = json.loads(api_query_params)
                            api_config["query_params"] = query_params
                        except json.JSONDecodeError as e:
                            st.error(f"Invalid JSON in Query Parameters field: {e!s}")
                            return

                    # Parse and add request body
                    if api_body.strip():
                        if api_method in ["POST", "PUT", "PATCH"]:
                            if body_type == "JSON":
                                try:
                                    # First try to parse as-is
                                    body_data = json.loads(api_body)
                                    api_config["body"] = body_data
                                    api_config["body_type"] = "json"
                                except json.JSONDecodeError as e:
                                    # If parsing fails due to control characters, try to fix by escaping control chars
                                    if "Invalid control character" in str(e):
                                        try:
                                            import re

                                            # Replace control characters (newlines, tabs, etc.) in string values
                                            # This regex finds strings and replaces control chars within them
                                            def escape_control_chars(match):
                                                text = match.group(0)
                                                # Escape newlines, tabs, carriage returns
                                                text = text.replace("\n", "\\n")
                                                text = text.replace("\r", "\\r")
                                                return text.replace("\t", "\\t")

                                            # Find all string values (between quotes) and escape control chars
                                            fixed_json = re.sub(
                                                r'"[^"]*"',
                                                escape_control_chars,
                                                api_body,
                                            )
                                            body_data = json.loads(fixed_json)
                                            api_config["body"] = body_data
                                            api_config["body_type"] = "json"
                                            st.info(
                                                "💡 自動的に制御文字をエスケープしました。",
                                            )
                                        except Exception:
                                            st.error(
                                                f"❌ Invalid JSON in Request Body field: {e!s}",
                                            )
                                            st.info(
                                                "💡 Tip: JSON文字列値内で改行を使う場合は `\\n` を使用してください。または、Body Data Type を 'Raw Text' に変更してください。",
                                            )
                                            return
                                    else:
                                        st.error(
                                            f"❌ Invalid JSON in Request Body field: {e!s}",
                                        )
                                        st.info(
                                            "💡 Tip: JSON文字列値内で改行を使う場合は `\\n` を使用してください。または、Body Data Type を 'Raw Text' に変更してください。",
                                        )
                                        return
                            elif body_type == "Form Data":
                                try:
                                    form_data = json.loads(api_body)
                                    api_config["body"] = form_data
                                    api_config["body_type"] = "form"
                                except json.JSONDecodeError as e:
                                    st.error(f"Invalid JSON in Form Data field: {e!s}")
                                    return
                            else:  # Raw Text
                                # Wrap raw text in a dict for API compatibility
                                api_config["body"] = {"text": api_body}
                                api_config["body_type"] = "raw"

                # Integrate API config into job parameters if provided
                if api_config:
                    job_params["api_config"] = api_config

                # Create job data
                job_data = {
                    "name": job_name,
                    "type": job_type,
                    "priority": priority,
                    "max_retries": max_retries,
                    "timeout": timeout,
                    "parameters": job_params,
                    "tags": job_tags,
                }

                create_job(job_data)

            except json.JSONDecodeError as e:
                st.error(f"Invalid JSON format: {e!s}")
            except Exception as e:
                NotificationManager.handle_exception(e, "Job Creation")


def get_parameter_placeholder(job_type: str) -> str:
    """Get parameter placeholder text based on job type."""
    placeholders = {
        "api_sync": """{
  "sync_direction": "bidirectional",
  "source_filters": {
    "updated_since": "2024-01-01T00:00:00Z"
  },
  "batch_size": 100,
  "mapping_rules": {
    "source_field": "target_field"
  }
}""",
        "data_processing": """{
  "input_file": "/data/input.csv",
  "output_file": "/data/processed/output.csv",
  "operations": ["clean", "normalize", "validate"],
  "encoding": "utf-8"
}""",
        "batch_analysis": """{
  "data_source": "/data/analytics/dataset.csv",
  "analysis_type": "trend_analysis",
  "output_format": "report",
  "date_range": "last_30_days"
}""",
        "file_conversion": """{
  "input_directory": "/uploads/original/",
  "output_directory": "/uploads/converted/",
  "source_format": "pdf",
  "target_format": "docx",
  "quality": "high"
}""",
        "custom": """{
  "script_path": "/scripts/custom_job.py",
  "environment": "production",
  "custom_param": "value"
}""",
    }
    return placeholders.get(job_type, '{\n  "key": "value"\n}')


def create_job(job_data: dict[str, Any]) -> None:
    """Create a new job via API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            NotificationManager.operation_started("Creating job")

            # For api_sync jobs, transform data structure to match JobQueue API schema
            if job_data.get("type") == "api_sync":
                parameters = job_data.get("parameters", {})
                api_config_data = parameters.get("api_config", {})

                if api_config_data:
                    # Transform to JobQueue API format
                    transformed_data = {
                        "name": job_data.get("name"),  # Include job name
                        "method": api_config_data.get("method", "GET"),
                        "url": api_config_data.get("url", ""),
                        "headers": api_config_data.get("headers"),
                        "params": api_config_data.get(
                            "query_params",
                        ),  # Rename query_params to params
                        "body": api_config_data.get("body"),
                        "timeout_sec": job_data.get(
                            "timeout", 30,
                        ),  # Include timeout from job_data
                    }

                    # Remove None values
                    transformed_data = {
                        k: v for k, v in transformed_data.items() if v is not None
                    }

                    st.info("🚀 Sending POST request to JobQueue API...")
                    response = client.post("/api/v1/jobs", transformed_data)
                    st.success("✅ API responded successfully")
                else:
                    # No API config provided, use original structure
                    st.info("🚀 Sending POST request to JobQueue API...")
                    response = client.post("/api/v1/jobs", job_data)
                    st.success("✅ API responded successfully")
            else:
                # For non-api_sync jobs, use original structure
                st.info("🚀 Sending POST request to JobQueue API...")
                response = client.post("/api/v1/jobs", job_data)
                st.success("✅ API responded successfully")

            job_id = response.get("job_id")
            NotificationManager.operation_completed("Job creation")
            NotificationManager.success(f"Job created successfully! ID: {job_id}")

            # Refresh job list
            load_jobs()

            # Switch to job detail view
            st.session_state.jobqueue_selected_job = job_id

    except Exception as e:
        # HTTP 422エラーの場合、より詳細なメッセージを表示
        error_str = str(e).lower()
        if "422" in error_str or "unprocessable" in error_str:
            if "timeout" in error_str:
                st.error("❌ Timeout value exceeds maximum allowed (3600 seconds). Please reduce the timeout.")
            else:
                st.error(f"❌ Invalid request data: {e}")
                st.info("💡 Please check all fields meet the validation requirements.")
        else:
            NotificationManager.handle_exception(e, "Job Creation")


def render_job_list() -> None:
    """Render job list with filtering and search."""
    st.subheader("📋 Job List")

    # Filters - Updated to 5 columns to include Job Type filter
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        status_filter = st.selectbox(
            "Status Filter",
            ["All", "pending", "running", "completed", "failed", "cancelled"],
            help="Filter jobs by status",
        )

    with col2:
        priority_filter = st.selectbox(
            "Priority Filter",
            ["All", "low", "normal", "high", "urgent"],
            help="Filter jobs by priority",
        )

    with col3:
        job_type_filter = st.selectbox(
            "Job Type Filter",
            [
                "All",
                "api_sync",
                "data_processing",
                "batch_analysis",
                "file_conversion",
                "custom",
            ],
            help="Filter jobs by job type",
        )

    with col4:
        search_query = st.text_input(
            "Search Jobs",
            placeholder="Search by name or ID",
            help="Search jobs by name or job ID",
        )

    with col5:
        auto_refresh = st.checkbox(
            "Auto Refresh",
            value=st.session_state.jobqueue_auto_refresh,
            help="Automatically refresh job list",
        )
        st.session_state.jobqueue_auto_refresh = auto_refresh

    # Refresh button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Refresh", use_container_width=True):
            load_jobs()

    # Display jobs
    jobs = st.session_state.jobqueue_jobs
    if not jobs:
        st.info("No jobs found. Create your first job using the form above.")
        return

    # Filter jobs - Updated to include job type filter
    filtered_jobs = filter_jobs(
        jobs, status_filter, priority_filter, job_type_filter, search_query,
    )

    if not filtered_jobs:
        st.warning("No jobs match the current filters.")
        return

    # Convert to DataFrame for better display
    df = pd.DataFrame(filtered_jobs)

    # Display as interactive table
    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "id": "Job ID",  # Changed from "job_id" to "id"
            "name": "Name",
            "type": st.column_config.SelectboxColumn(
                "Type",
                options=[
                    "api_sync",
                    "data_processing",
                    "batch_analysis",
                    "file_conversion",
                    "custom",
                ],
            ),
            "status": st.column_config.SelectboxColumn(
                "Status",
                options=["pending", "running", "completed", "failed", "cancelled"],
            ),
            "priority": st.column_config.SelectboxColumn(
                "Priority",
                options=["low", "normal", "high", "urgent"],
            ),
            "created_at": st.column_config.DatetimeColumn("Created"),
            "updated_at": st.column_config.DatetimeColumn("Updated"),
        },
    )

    # Handle row selection
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_job = filtered_jobs[selected_idx]
        st.session_state.jobqueue_selected_job = selected_job[
            "id"
        ]  # Changed from "job_id" to "id"


def filter_jobs(
    jobs: list[dict],
    status_filter: str,
    priority_filter: str,
    job_type_filter: str,
    search_query: str,
) -> list[dict]:
    """Filter jobs based on criteria."""
    filtered = jobs

    # Status filter
    if status_filter != "All":
        filtered = [job for job in filtered if job.get("status") == status_filter]

    # Priority filter
    if priority_filter != "All":
        filtered = [job for job in filtered if job.get("priority") == priority_filter]

    # Job type filter
    if job_type_filter != "All":
        filtered = [job for job in filtered if job.get("type") == job_type_filter]

    # Search filter
    if search_query:
        query_lower = search_query.lower()
        filtered = [
            job
            for job in filtered
            if (
                query_lower in job.get("name", "").lower()
                or query_lower in str(job.get("id", ""))
            )  # Changed from "job_id" to "id"
        ]

    return filtered


def render_job_detail() -> None:
    """Render detailed job information and controls."""
    job_id = st.session_state.jobqueue_selected_job
    if not job_id:
        st.info("Select a job from the list above to view details.")
        return

    st.subheader(f"📄 Job Details - {job_id}")

    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            job_detail = client.get(f"/api/v1/jobs/{job_id}")

            # Job information
            col1, col2, col3 = st.columns(3)

            with col1:
                st.metric("Status", job_detail.get("status", "Unknown"))
                st.metric("Priority", job_detail.get("priority", "Unknown"))

            with col2:
                st.metric("Progress", f"{job_detail.get('progress', 0)}%")
                st.metric(
                    "Retries",
                    f"{job_detail.get('retry_count', 0)}/{job_detail.get('max_retries', 0)}",
                )

            with col3:
                created_at = job_detail.get("created_at", "Unknown")
                st.metric("Created", created_at)
                duration = calculate_duration(job_detail)
                st.metric("Duration", duration)

            # Job controls
            st.subheader("🎛️ Job Controls")
            col1, col2, col3, col4 = st.columns(4)

            current_status = job_detail.get("status")

            with col1:
                if current_status in ["pending", "failed"] and st.button(
                    "▶️ Start", use_container_width=True,
                ):
                    control_job(job_id, "start")

            with col2:
                if current_status == "running" and st.button(
                    "⏸️ Pause", use_container_width=True,
                ):
                    control_job(job_id, "pause")

            with col3:
                if current_status in ["running", "pending"] and st.button(
                    "⏹️ Cancel", use_container_width=True,
                ):
                    control_job(job_id, "cancel")

            with col4:
                if current_status == "failed" and st.button(
                    "🔄 Retry", use_container_width=True,
                ):
                    control_job(job_id, "retry")

            # Job details tabs - Removed Logs tab
            tab1, tab2, tab3 = st.tabs(["📋 Definition", "📊 Results", "⚙️ Parameters"])

            with tab1:
                st.json(job_detail, expanded=False)

            with tab2:
                # Fetch job results from separate endpoint
                try:
                    job_result = client.get(f"/api/v1/jobs/{job_id}/result")

                    # Check if result has actual data
                    if (
                        job_result.get("response_status") is not None
                        or job_result.get("response_body") is not None
                        or job_result.get("error") is not None
                    ):
                        st.subheader("🌐 HTTP Response")

                        # Show response status and duration
                        result_col1, result_col2 = st.columns(2)
                        with result_col1:
                            st.metric(
                                "Response Status",
                                job_result.get("response_status", "N/A"),
                            )
                        with result_col2:
                            duration_ms = job_result.get("duration_ms")
                            duration_display = (
                                f"{duration_ms}ms" if duration_ms is not None else "N/A"
                            )
                            st.metric("Duration", duration_display)

                        # Show error if exists
                        if job_result.get("error"):
                            st.error(f"**Error:** {job_result.get('error')}")

                        # Show response headers
                        response_headers = job_result.get("response_headers")
                        if response_headers:
                            st.subheader("📋 Response Headers")
                            st.json(response_headers)

                        # Show response body
                        response_body = job_result.get("response_body")
                        if response_body:
                            st.subheader("📄 Response Body")
                            st.json(response_body)
                    else:
                        st.info("No results available yet.")

                except Exception as result_error:
                    st.warning(f"Could not fetch results: {result_error!s}")

            with tab3:
                # Display HTTP request parameters
                st.subheader("🌐 HTTP Request Configuration")

                # Basic request info
                req_col1, req_col2 = st.columns(2)
                with req_col1:
                    st.text_input(
                        "Method", value=job_detail.get("method", ""), disabled=True,
                    )
                    st.text_input(
                        "Timeout (sec)",
                        value=str(job_detail.get("timeout_sec", "")),
                        disabled=True,
                    )
                with req_col2:
                    st.text_area(
                        "URL",
                        value=job_detail.get("url", ""),
                        disabled=True,
                        height=100,
                    )

                # Request Headers
                headers = job_detail.get("headers")
                if headers:
                    st.subheader("📋 Request Headers")
                    st.json(headers)

                # Query Parameters
                params = job_detail.get("params")
                if params:
                    st.subheader("🔗 Query Parameters")
                    st.json(params)

                # Request Body
                body = job_detail.get("body")
                if body:
                    st.subheader("📄 Request Body")
                    st.json(body)

                # Tags
                tags = job_detail.get("tags")
                if tags:
                    st.subheader("🏷️ Tags")
                    st.write(", ".join(tags))

                # Show message if no parameters
                if not any([headers, params, body, tags]):
                    st.info("No additional parameters specified for this job.")

    except Exception as e:
        NotificationManager.handle_exception(e, "Job Detail")


def calculate_duration(job_detail: dict) -> str:
    """Calculate job duration."""
    try:
        created_at = job_detail.get("created_at")
        updated_at = job_detail.get("updated_at")

        if created_at and updated_at:
            # Parse timestamps (assuming ISO format)
            from datetime import datetime

            start = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            end = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
            duration = end - start
            total_seconds = int(duration.total_seconds())

            if total_seconds < 60:
                return f"{total_seconds}s"
            if total_seconds < 3600:
                return f"{total_seconds // 60}m {total_seconds % 60}s"
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}h {minutes}m"

        return "N/A"
    except Exception:
        return "N/A"


def control_job(job_id: str, action: str) -> None:
    """Control job execution (start, pause, cancel, retry)."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            NotificationManager.operation_started(f"Job {action}")

            client.post(f"/api/v1/jobs/{job_id}/{action}")

            NotificationManager.operation_completed(f"Job {action}")
            NotificationManager.success(f"Job {action} executed successfully!")

            # Refresh job detail
            time.sleep(1)  # Brief delay for status update
            st.rerun()

    except Exception as e:
        NotificationManager.handle_exception(e, f"Job {action}")


def load_jobs() -> None:
    """Load jobs from API."""
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            response = client.get("/api/v1/jobs")
            st.session_state.jobqueue_jobs = response.get("jobs", [])

    except Exception as e:
        NotificationManager.handle_exception(e, "Load Jobs")
        st.session_state.jobqueue_jobs = []


def main() -> None:
    """Main JobQueue page function."""
    # Initialize session state
    initialize_session_state()

    # Render sidebar
    _selected_service, ui_settings = SidebarManager.render_complete_sidebar()

    # Page header
    st.title("📋 JobQueue Management")

    # Check if service is configured
    if not config.is_service_configured("JobQueue"):
        st.error(
            "❌ JobQueue is not configured. Please check your environment settings.",
        )
        st.stop()

    # Load initial data
    if not st.session_state.jobqueue_jobs:
        load_jobs()

    # Main content tabs
    tab1, tab2 = st.tabs(["🆕 Create Job", "📋 Job List"])

    with tab1:
        render_job_creation_form()

    with tab2:
        render_job_list()
        st.divider()
        render_job_detail()

    # Auto-refresh functionality
    if st.session_state.jobqueue_auto_refresh:
        polling_interval = ui_settings.get("polling_interval", 5)
        time.sleep(polling_interval)
        st.rerun()


if __name__ == "__main__":
    main()
