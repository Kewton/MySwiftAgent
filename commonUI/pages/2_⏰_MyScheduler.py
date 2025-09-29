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
    """Render job creation form for scheduler management."""
    st.subheader("🕐 Schedule Configuration")
    
    # Move the cron schedule config outside the form to enable real-time updates
    render_cron_schedule_config()
    
    st.divider()

    with st.form("scheduler_creation_form"):
        # Basic job information
        st.subheader("📋 Basic Information")
        col1, col2 = st.columns(2)

        with col1:
            # Generate unique default job_id
            import uuid
            default_job_id = f"job_{uuid.uuid4().hex[:8]}"
            
            job_id = st.text_input(
                "Job ID*",
                value=default_job_id,
                help="Unique identifier for the scheduled job"
            )

            job_name = st.text_input(
                "Job Name*",
                placeholder="Enter descriptive job name",
                help="Human-readable name for the job"
            )

        with col2:
            # Available functions mapping (display name -> full module path)
            available_functions = {
                "execute_http_job": "app.services.job_executor.execute_http_job"
            }
            
            function_display_name = st.selectbox(
                "Function*",
                options=list(available_functions.keys()),
                help="Select the function to execute"
            )
            
            # Get the full module path for the selected function
            job_function = available_functions[function_display_name]

            timezone = st.selectbox(
                "Timezone",
                ["UTC", "Asia/Tokyo", "US/Eastern", "US/Pacific", "Europe/London"],
                help="Timezone for schedule execution"
            )

        # Function description
        if function_display_name == "execute_http_job":
            st.info("🌐 **execute_http_job**: Executes HTTP requests to external APIs with retry support and error handling.")

        # API Configuration Fields (always displayed for all job types)
        st.divider()
        st.subheader("🔗 API Configuration (Optional)")
        st.caption("Configure API settings if this scheduled job needs to make external API calls")
        
        # API URL and Method
        col1, col2 = st.columns([3, 1])
        with col1:
            api_url = st.text_input(
                "🌐 API Endpoint URL",
                placeholder="https://api.example.com/v1/endpoint",
                help="Target API endpoint URL"
            )
        with col2:
            api_method = st.selectbox(
                "📡 HTTP Method",
                ["GET", "POST", "PUT", "PATCH", "DELETE"],
                index=0,
                help="HTTP method"
            )
        
        # Headers configuration
        st.subheader("📋 Request Headers")
        st.caption("HTTP headers to include in the API request (Content-Type, Authorization, etc.)")
        api_headers = st.text_area(
            "Headers (JSON format)",
            placeholder='{\n  "Content-Type": "application/json",\n  "Authorization": "Bearer your-api-token",\n  "X-Custom-Header": "custom-value"\n}',
            help="HTTP headers in JSON format - commonly used for authentication and content type specification",
            height=100
        )
        
        # Query parameters (for GET/DELETE)
        if api_method in ["GET", "DELETE"]:
            st.subheader("🔍 URL Query Parameters")
            st.caption("Parameters that will be added to the URL (e.g., ?page=1&limit=100)")
            api_query_params = st.text_area(
                "Query Parameters (JSON format)",
                placeholder='{\n  "page": 1,\n  "limit": 100,\n  "filter": "active",\n  "sort": "created_at"\n}',
                help="Query parameters in JSON format - will be appended to the URL as ?key=value",
                height=80
            )
        else:
            api_query_params = ""
        
        # Request body (for POST/PUT/PATCH)
        if api_method in ["POST", "PUT", "PATCH"]:
            st.subheader("📤 Request Body Data")
            st.caption("Data to send in the request body")
            body_type = st.selectbox(
                "Body Data Type",
                ["JSON", "Form Data", "Raw Text"],
                help="Format of the request body data"
            )
            
            if body_type == "JSON":
                api_body = st.text_area(
                    "JSON Body Data",
                    placeholder='{\n  "name": "example",\n  "data": {\n    "field1": "value1",\n    "field2": 123,\n    "active": true\n  }\n}',
                    help="JSON data to send in the request body",
                    height=120
                )
            elif body_type == "Form Data":
                api_body = st.text_area(
                    "Form Fields Data (JSON format)",
                    placeholder='{\n  "username": "john_doe",\n  "email": "john@example.com",\n  "age": 30\n}',
                    help="Form fields as JSON - will be sent as application/x-www-form-urlencoded",
                    height=120
                )
            else:  # Raw Text
                api_body = st.text_area(
                    "Raw Text Body",
                    placeholder="Plain text content to send as request body",
                    help="Raw text content for request body",
                    height=120
                )
        else:
            api_body = ""
            body_type = "JSON"

        # Job arguments
        st.divider()
        st.subheader("⚙️ Job Configuration")
        
        # Function-specific argument hints
        if function_display_name == "execute_http_job":
            st.info("💡 **execute_http_job** requires URL and method as Arguments. Optional parameters can be set in Keyword Arguments.")
            args_placeholder = '["https://api.example.com/endpoint", "GET"]'
            kwargs_placeholder = '''{\n  "headers": {"Authorization": "Bearer token"},\n  "timeout_sec": 30,\n  "max_retries": 3,\n  "retry_backoff_sec": 2.0\n}'''
        else:
            args_placeholder = '["arg1", "arg2", 123]'
            kwargs_placeholder = '{"param1": "value1", "param2": 42}'
        
        args = st.text_area(
            "Arguments (JSON Array)",
            placeholder=args_placeholder,
            help="Function arguments as JSON array"
        )

        kwargs = st.text_area(
            "Keyword Arguments (JSON Object)",
            placeholder=kwargs_placeholder,
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

            # Check if schedule is configured
            if not st.session_state.get("schedule_cron"):
                st.error("Schedule configuration is required")
                return

            try:
                # Get schedule configuration from session state (always cron)
                schedule_config = {
                    "trigger": "cron",
                    "params": {}
                }
                
                # Parse cron expression from session state
                cron_expr = st.session_state.get("schedule_cron", "")
                if cron_expr:
                    # Parse cron parts: minute hour day month day_of_week
                    cron_parts = cron_expr.split()
                    if len(cron_parts) == 5:
                        schedule_config["params"] = {
                            "minute": cron_parts[0],
                            "hour": cron_parts[1], 
                            "day": cron_parts[2],
                            "month": cron_parts[3],
                            "day_of_week": cron_parts[4]
                        }
                    else:
                        st.error("Invalid cron expression format")
                        return
                else:
                    st.error("Cron expression is required")
                    return

                # Parse arguments
                import json
                job_args = json.loads(args) if args.strip() else []
                job_kwargs = json.loads(kwargs) if kwargs.strip() else {}

                # Build API configuration if any API settings are provided
                api_config = {}
                if api_url.strip():  # Only include API config if URL is provided
                    api_config = {
                        "url": api_url,
                        "method": api_method
                    }
                    
                    # Parse and add headers
                    if api_headers.strip():
                        try:
                            headers = json.loads(api_headers)
                            api_config["headers"] = headers
                        except json.JSONDecodeError:
                            st.error("Invalid JSON in Request Headers field")
                            return
                    
                    # Parse and add query parameters
                    if api_query_params.strip():
                        try:
                            query_params = json.loads(api_query_params)
                            api_config["query_params"] = query_params
                        except json.JSONDecodeError:
                            st.error("Invalid JSON in Query Parameters field")
                            return
                    
                    # Parse and add request body
                    if api_body.strip():
                        if api_method in ["POST", "PUT", "PATCH"]:
                            if body_type == "JSON":
                                try:
                                    body_data = json.loads(api_body)
                                    api_config["body"] = body_data
                                    api_config["body_type"] = "json"
                                except json.JSONDecodeError:
                                    st.error("Invalid JSON in Request Body field")
                                    return
                            elif body_type == "Form Data":
                                try:
                                    form_data = json.loads(api_body)
                                    api_config["body"] = form_data
                                    api_config["body_type"] = "form"
                                except json.JSONDecodeError:
                                    st.error("Invalid JSON in Form Data field")
                                    return
                            else:  # Raw Text
                                api_config["body"] = api_body
                                api_config["body_type"] = "raw"

                # Add API config to kwargs if provided
                if api_config:
                    job_kwargs["api_config"] = api_config

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
        # Quick Presets (moved to left column)
        preset = st.selectbox(
            "Quick Presets",
            [
                "Custom",
                "Every minute (*/1 * * * *)",
                "Every hour (0 * * * *)",
                "Every 6 hours (0 */6 * * *)",
                "Daily at midnight (0 0 * * *)",
                "Daily at 9 AM (0 9 * * *)",
                "Weekly on Monday (0 0 * * 1)",
                "Monthly on 1st (0 0 1 * *)"
            ],
            help="Select a preset schedule or choose Custom for manual entry"
        )

        # Show preset description
        if preset != "Custom":
            preset_descriptions = {
                "Every minute (*/1 * * * *)": "⏰ Executes every minute",
                "Every hour (0 * * * *)": "⏰ Executes at the beginning of every hour",
                "Every 6 hours (0 */6 * * *)": "⏰ Executes every 6 hours (00:00, 06:00, 12:00, 18:00)",
                "Daily at midnight (0 0 * * *)": "⏰ Executes daily at 00:00 (midnight)",
                "Daily at 9 AM (0 9 * * *)": "⏰ Executes daily at 09:00 (9 AM)",
                "Weekly on Monday (0 0 * * 1)": "⏰ Executes every Monday at 00:00",
                "Monthly on 1st (0 0 1 * *)": "⏰ Executes on the 1st day of each month at 00:00"
            }
            st.info(preset_descriptions.get(preset, ""))

    with col2:
        # Extract cron expression from preset if not Custom
        if preset != "Custom":
            preset_expr = preset.split("(")[1].split(")")[0]
            # Store preset expression in session state
            st.session_state.schedule_cron = preset_expr
            cron_expression = preset_expr
            disabled = True
        else:
            # For Custom, use existing value or empty string
            cron_expression = st.session_state.get("schedule_cron", "")
            disabled = False

        # Cron Expression (moved to right column)
        cron_input = st.text_input(
            "Cron Expression*",
            value=cron_expression,
            placeholder="0 */6 * * *",
            help="Cron expression (minute hour day month day_of_week)",
            disabled=disabled,
            key="cron_expression_input"
        )

        # Update session state based on input mode
        if preset == "Custom":
            st.session_state.schedule_cron = cron_input
        # For presets, session state is already updated above

    # Display current effective cron expression
    effective_cron = st.session_state.get("schedule_cron", "")
    
    if preset != "Custom":
        st.success(f"🎯 **Active Cron Expression**: `{effective_cron}`")

    # Validate and show next runs
    if effective_cron:
        try:
            from croniter import croniter
            from datetime import datetime
            
            cron = croniter(effective_cron, datetime.now())
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

            # Transform data to match MyScheduler API schema
            transformed_data = transform_job_data_for_api(job_data)
            
            response = client.post("/api/v1/jobs/", transformed_data)

            job_id = response.get("job_id", job_data["job_id"])
            NotificationManager.operation_completed("Scheduled job creation")
            NotificationManager.success(f"Scheduled job created successfully! ID: {job_id}")

            # Refresh job list
            load_scheduled_jobs()

            # Switch to job detail view
            st.session_state.scheduler_selected_job = job_id

    except Exception as e:
        NotificationManager.handle_exception(e, "Scheduled Job Creation")

def transform_job_data_for_api(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Transform CommonUI job data to MyScheduler API format."""
    kwargs = job_data.get("kwargs", {})
    api_config = kwargs.get("api_config", {})
    
    # Basic job configuration
    transformed_data = {
        "job_id": job_data.get("job_id"),
        "name": job_data.get("name"),  # Job Nameを追加
        "schedule_type": job_data.get("trigger", "cron"),
        "target_url": api_config.get("url", ""),
        "method": api_config.get("method", "GET"),
        "headers": api_config.get("headers"),
        "body": api_config.get("body"),
        "timeout_sec": float(kwargs.get("timeout_sec", 30.0)),
        "max_retries": int(kwargs.get("max_retries", 0)),
        "retry_backoff_sec": float(kwargs.get("retry_backoff_sec", 1.0)),
        "replace_existing": job_data.get("replace_existing", False)
    }
    
    # Remove None values
    transformed_data = {k: v for k, v in transformed_data.items() if v is not None}
    
    # Handle schedule configuration based on trigger type
    trigger = job_data.get("trigger", "cron")
    
    if trigger == "cron":
        # Cron fields are at the top level of job_data due to **schedule_config["params"]
        cron_config = {}
        
        # Map CommonUI cron fields to API format
        minute = job_data.get("minute")
        hour = job_data.get("hour") 
        day = job_data.get("day")
        month = job_data.get("month")
        day_of_week = job_data.get("day_of_week")
        
        # Only include non-null and non-* values
        if minute and minute != "*":
            cron_config["minute"] = minute
        if hour and hour != "*":
            cron_config["hour"] = hour
        if day and day != "*":
            cron_config["day"] = day
        if month and month != "*":
            cron_config["month"] = month
        if day_of_week and day_of_week != "*":
            cron_config["day_of_week"] = day_of_week
        
        # Always set second to "0" as default
        cron_config["second"] = "0"
        
        if cron_config:
            transformed_data["cron"] = cron_config
    
    elif trigger == "interval":
        # Handle interval configuration
        interval_config = {}
        for unit in ["weeks", "days", "hours", "minutes", "seconds"]:
            if unit in job_data:
                interval_config[unit] = int(job_data[unit])
        
        if interval_config:
            transformed_data["interval"] = interval_config
    
    elif trigger == "date":
        run_date = job_data.get("run_date")
        if run_date:
            transformed_data["run_at"] = run_date
    
    return transformed_data


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
        method_filter = st.selectbox(
            "Method Filter",
            ["All", "GET", "POST", "PUT", "PATCH", "DELETE"],
            help="Filter jobs by HTTP method"
        )

    with col4:
        search_query = st.text_input(
            "Search Jobs",
            placeholder="Search by ID, name, or URL",
            help="Search jobs by ID, name, or target URL"
        )

    # Second row of controls
    col1, col2, col3, col4 = st.columns(4)

    with col1:
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
    filtered_jobs = filter_scheduled_jobs(jobs, status_filter, trigger_filter, method_filter, search_query)

    # Show job statistics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Jobs", len(jobs))
    with col2:
        running_jobs = len([j for j in jobs if j.get("status") == "running"])
        st.metric("Running", running_jobs)
    with col3:
        paused_jobs = len([j for j in jobs if j.get("status") == "paused"])
        st.metric("Paused", paused_jobs)
    with col4:
        st.metric("Filtered", len(filtered_jobs))

    st.divider()

    if not filtered_jobs:
        st.warning("No jobs match the current filters.")
        return

    # Convert trigger format for display
    display_jobs = []
    for job in filtered_jobs:
        display_job = job.copy()
        # Convert trigger to display format
        if 'trigger' in display_job:
            display_job['trigger'] = parse_trigger_type(display_job['trigger'])

        # Remove duplicate job_id field to prevent duplicate columns
        # Keep only 'id' field for display (job_id and id have the same value)
        if 'job_id' in display_job and 'id' in display_job:
            del display_job['job_id']

        # Truncate long URLs for better display
        if 'target_url' in display_job and display_job['target_url']:
            url = display_job['target_url']
            if len(url) > 60:
                display_job['target_url'] = url[:57] + "..."

        display_jobs.append(display_job)

    # Display as table
    df = pd.DataFrame(display_jobs)

    # Format next run time for better display with proper ISO8601 parsing
    if 'next_run_time' in df.columns:
        try:
            # Use format='ISO8601' to properly parse ISO8601 formatted datetime strings
            df['next_run_time'] = pd.to_datetime(df['next_run_time'], format='ISO8601', errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            # Fallback: try to parse without format specification
            try:
                df['next_run_time'] = pd.to_datetime(df['next_run_time'], errors='coerce').dt.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                # If all parsing fails, keep original values
                st.warning("Warning: Could not parse some datetime values in next_run_time")

    event = st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "id": "Job ID",
            "name": "Name",
            "status": st.column_config.SelectboxColumn(
                "Status",
                options=["running", "paused", "completed", "error"],
            ),
            "trigger": st.column_config.SelectboxColumn(
                "Trigger",
                options=["cron", "interval", "date"],
            ),
            "target_url": st.column_config.LinkColumn(
                "Target URL",
                help="API endpoint that this job will call",
                max_chars=50,
            ),
            "method": st.column_config.SelectboxColumn(
                "Method",
                options=["GET", "POST", "PUT", "PATCH", "DELETE"],
            ),
            "next_run_time": st.column_config.DatetimeColumn("Next Run"),
            "execution_count": st.column_config.NumberColumn(
                "Executions",
                help="Number of times this job has been executed",
                min_value=0,
            ),
        }
    )

    # Handle row selection with safe key access
    if event.selection.rows:
        selected_idx = event.selection.rows[0]
        selected_job = filtered_jobs[selected_idx]  # Use original filtered data, not display_jobs
        
        # Safe access to job ID with fallback options
        job_id = None
        if "id" in selected_job:
            job_id = selected_job["id"]
        elif "job_id" in selected_job:
            job_id = selected_job["job_id"]
        else:
            # Debug: Show the actual structure of selected_job
            st.error(f"Error: Job data missing required 'id' or 'job_id' field. Available keys: {list(selected_job.keys())}")
            return
            
        st.session_state.scheduler_selected_job = job_id


def parse_trigger_type(trigger_str: str) -> str:
    """Extract trigger type from MyScheduler trigger string."""
    if not trigger_str:
        return "unknown"

    trigger_lower = trigger_str.lower()
    if trigger_lower.startswith("cron["):
        return "cron"
    elif trigger_lower.startswith("interval["):
        return "interval"
    elif trigger_lower.startswith("date["):
        return "date"
    else:
        return trigger_str  # Return original if unknown format


def filter_scheduled_jobs(jobs: List[Dict], status_filter: str, trigger_filter: str, method_filter: str, search_query: str) -> List[Dict]:
    """Filter scheduled jobs based on criteria."""
    filtered = jobs

    # Status filter
    if status_filter != "All":
        filtered = [job for job in filtered if job.get("status", "").lower() == status_filter.lower()]

    # Trigger filter
    if trigger_filter != "All":
        filtered = [job for job in filtered if parse_trigger_type(job.get("trigger", "")) == trigger_filter]

    # Method filter
    if method_filter != "All":
        filtered = [job for job in filtered if job.get("method", "").upper() == method_filter.upper()]

    # Search filter
    if search_query:
        query_lower = search_query.lower()
        filtered = [
            job for job in filtered
            if (query_lower in job.get("name", "").lower() or
                query_lower in str(job.get("id", "")) or
                query_lower in job.get("target_url", "").lower())
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
            # URL エンコーディングを追加してjob_idを安全にエンコード
            import urllib.parse
            encoded_job_id = urllib.parse.quote(str(job_id), safe='')
            
            # デバッグ情報を表示
            with st.expander("🔍 Debug Information", expanded=False):
                st.write(f"**Original job_id:** `{job_id}`")
                st.write(f"**Encoded job_id:** `{encoded_job_id}`")
                st.write(f"**API Endpoint:** `GET /api/v1/jobs/{encoded_job_id}`")
            
            job_detail = client.get(f"/api/v1/jobs/{encoded_job_id}")

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
        # 詳細なエラー情報を表示
        st.error("Failed to load job details")
        with st.expander("🔍 Error Details", expanded=True):
            st.write(f"**Error Type:** {type(e).__name__}")
            st.write(f"**Error Message:** {str(e)}")
            st.write(f"**Job ID:** `{job_id}`")
            if hasattr(e, 'response'):
                st.write(f"**HTTP Status:** {getattr(e.response, 'status_code', 'Unknown')}")
                st.write(f"**Response Body:** {getattr(e.response, 'text', 'No response body')}")
        
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
            response = client.get("/api/v1/jobs")  # Remove trailing slash
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