"""Interface Service for Job Configuration page.

This module provides functions for fetching and caching interface information
from the JobQueue API.
"""

from __future__ import annotations

import json
import logging
from typing import Any

try:
    import streamlit as st  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover
    st = None  # type: ignore[assignment]

from components.http_client import HTTPClient
from core.config import config
from core.exceptions import APIError

logger = logging.getLogger(__name__)


def get_interface_info(interface_id: str) -> dict[str, Any] | None:
    """Fetch interface information from API.

    Args:
        interface_id: The interface master ID to fetch.

    Returns:
        Interface data dict if found, None otherwise.
    """
    try:
        api_config = config.get_api_config("JobQueue")
        with HTTPClient(api_config, "JobQueue") as client:
            return client.get(f"/api/v1/interface-masters/{interface_id}")
    except APIError as e:
        if e.status_code == 404:
            logger.debug("Interface not found: %s", interface_id)
            return None
        logger.warning("API error fetching interface %s: %s", interface_id, e)
        return None
    except Exception as e:
        logger.warning("Error fetching interface %s: %s", interface_id, e)
        return None


def get_cached_interface(interface_id: str | None) -> dict[str, Any] | None:
    """Get interface from cache or fetch from API.

    Args:
        interface_id: The interface master ID to fetch. Returns None if None.

    Returns:
        Interface data dict if found, None otherwise.
    """
    if interface_id is None:
        return None

    if st is None:
        # Fallback when streamlit is not available
        return get_interface_info(interface_id)

    # Ensure cache exists
    if not hasattr(st.session_state, "interface_cache"):
        st.session_state.interface_cache = {}

    # Check cache first
    if interface_id in st.session_state.interface_cache:
        cached: dict[str, Any] | None = st.session_state.interface_cache[interface_id]
        return cached

    # Fetch from API and cache
    interface = get_interface_info(interface_id)
    if interface is not None:
        st.session_state.interface_cache[interface_id] = interface

    return interface


def get_interface_name(interface_id: str | None) -> str:
    """Get interface name, returning 'Not Set' if interface is None or not found.

    Args:
        interface_id: The interface master ID.

    Returns:
        Interface name or 'Not Set' if not found.
    """
    if interface_id is None:
        return "Not Set"

    interface = get_cached_interface(interface_id)
    if interface is None:
        return f"Unknown ({interface_id[:8]}...)"

    name: str = interface.get("name", f"Unnamed ({interface_id[:8]}...)")
    return name


def render_task_interface_info(task: dict[str, Any]) -> None:
    """Render interface information for a task.

    Displays input and output interface names and schema expanders.

    Args:
        task: Task dictionary containing interface IDs.
    """
    if st is None:
        return

    input_interface_id = task.get("input_interface_id")
    output_interface_id = task.get("output_interface_id")

    input_interface = get_cached_interface(input_interface_id)
    output_interface = get_cached_interface(output_interface_id)

    # Display interface info
    st.markdown("**Interface Information**")

    col1, col2 = st.columns(2)

    with col1:
        input_name = (
            input_interface.get("name", "Not Set") if input_interface else "Not Set"
        )
        st.write(f"**Input:** {input_name}")
        if input_interface:
            render_interface_schema_expander(
                input_interface,
                "Input Schema",
                schema_key="input_schema",
            )

    with col2:
        output_name = (
            output_interface.get("name", "Not Set") if output_interface else "Not Set"
        )
        st.write(f"**Output:** {output_name}")
        if output_interface:
            render_interface_schema_expander(
                output_interface,
                "Output Schema",
                schema_key="output_schema",
            )


def render_interface_schema_expander(
    interface: dict[str, Any],
    title: str,
    schema_key: str = "input_schema",
) -> None:
    """Render interface JSON schema in an expander.

    Args:
        interface: Interface data dictionary containing input_schema/output_schema.
        title: Title for the expander.
        schema_key: Key to use for schema lookup ('input_schema' or 'output_schema').
    """
    if st is None:
        return

    interface_name = interface.get("name", "Unknown")
    json_schema = interface.get(schema_key, {})

    with st.expander(f"{title}: {interface_name}"):
        if not json_schema:
            st.info("No schema defined for this interface.")
            return

        # Display properties table
        properties = json_schema.get("properties", {})
        required_fields = json_schema.get("required", [])

        if properties:
            st.markdown("**Properties:**")
            for field_name, field_def in properties.items():
                field_type = field_def.get("type", "any")
                is_required = field_name in required_fields
                required_badge = " (required)" if is_required else " (optional)"
                description = field_def.get("description", "")

                st.markdown(f"- `{field_name}`: {field_type}{required_badge}")
                if description:
                    st.caption(f"  {description}")

        # Display raw JSON schema
        st.markdown("**Raw JSON Schema:**")
        st.code(
            json.dumps(json_schema, indent=2, ensure_ascii=False),
            language="json",
        )
