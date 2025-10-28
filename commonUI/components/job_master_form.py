"""Job Master form component for creating and editing masters."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from collections.abc import Callable

import streamlit as st  # type: ignore[import-not-found]

from components.template_manager import TemplateManager

JSONText = str

HEADERS_PLACEHOLDER = (
    '{\n  "Content-Type": "application/json",\n'
    '  "Authorization": "Bearer your-token"\n}'
)

PARAMS_PLACEHOLDER = '{\n  "page": 1,\n  "limit": 100\n}'

BODY_PLACEHOLDER = '{\n  "event": "notification",\n  "data": {}\n}'

JSON_ERROR_HELP = (
    "💡 Please check your Headers, Query Parameters, or Request Body fields"
)


def _session_key(field: str, mode: str | None = None) -> str:
    if mode:
        return f"master_form_{field}_{mode}"
    return f"master_form_{field}"


def _parse_json_field(value: JSONText) -> Any | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    return json.loads(cleaned)


def _parse_tags(value: str) -> list[str] | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    tags = [tag.strip() for tag in cleaned.split(",") if tag.strip()]
    return tags or None


def _template_flag_key(template_payload: dict[str, Any]) -> str:
    return f"master_template_{hash(str(sorted(template_payload.items())))}"


@dataclass(slots=True)
class TemplateSnapshot:
    name: str = ""
    description: str = ""
    method: str = "GET"
    url: str = ""
    headers: JSONText = ""
    params: JSONText = ""
    body: JSONText = ""
    timeout_sec: int = 30
    max_attempts: int = 1
    backoff_strategy: str = "exponential"
    backoff_seconds: float = 5.0
    tags: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "method": self.method,
            "url": self.url,
            "headers": self.headers,
            "params": self.params,
            "body": self.body,
            "timeout_sec": self.timeout_sec,
            "max_attempts": self.max_attempts,
            "backoff_strategy": self.backoff_strategy,
            "backoff_seconds": self.backoff_seconds,
            "tags": self.tags,
        }


def _collect_template_snapshot(mode: str) -> TemplateSnapshot:
    return TemplateSnapshot(
        name=st.session_state.get(_session_key("name", mode), ""),
        description=st.session_state.get(
            _session_key("description", mode),
            "",
        ),
        method=st.session_state.get(_session_key("method", mode), "GET"),
        url=st.session_state.get(_session_key("url", mode), ""),
        headers=st.session_state.get(_session_key("headers", mode), ""),
        params=st.session_state.get(_session_key("params", mode), ""),
        body=st.session_state.get(_session_key("body", mode), ""),
        timeout_sec=st.session_state.get(_session_key("timeout", mode), 30),
        max_attempts=st.session_state.get(
            _session_key("max_attempts", mode),
            1,
        ),
        backoff_strategy=st.session_state.get(
            _session_key("backoff_strategy", mode),
            "exponential",
        ),
        backoff_seconds=st.session_state.get(
            _session_key("backoff_seconds", mode),
            5.0,
        ),
        tags=st.session_state.get(_session_key("tags", mode), ""),
    )


def _apply_template_to_state(
    template_data: dict[str, Any],
    mode: str,
) -> None:
    template_key = _template_flag_key(template_data)
    if st.session_state.get(template_key):
        return

    for key, value in template_data.items():
        st.session_state[_session_key(key, mode)] = value

    st.session_state[template_key] = True

    keys_to_clear = [
        key
        for key in st.session_state
        if key.startswith("master_template_") and key != template_key
    ]
    for key in keys_to_clear:
        del st.session_state[key]


def _render_template_selector(mode: str) -> None:
    template_mgr = TemplateManager("job_masters")
    snapshot = _collect_template_snapshot(mode)
    loaded_template = template_mgr.render_template_selector(snapshot.as_dict())
    if loaded_template:
        _apply_template_to_state(loaded_template, mode)
    st.divider()


@dataclass(slots=True)
class FieldDefinitions:
    mode: str
    initial_data: dict[str, Any] = field(default_factory=dict)

    def text_input(
        self,
        label: str,
        field: str,
        default: str = "",
        **kwargs: Any,
    ) -> str:
        value = self.initial_data.get(field, default)
        return cast(
            "str",
            st.text_input(
                label,
                value=value,
                key=_session_key(field, self.mode),
                **kwargs,
            ),
        )

    def text_area(
        self,
        label: str,
        field: str,
        default: str = "",
        **kwargs: Any,
    ) -> str:
        value = self.initial_data.get(field, default)
        return cast(
            "str",
            st.text_area(
                label,
                value=value,
                key=_session_key(field, self.mode),
                **kwargs,
            ),
        )

    def number_input(
        self,
        label: str,
        field: str,
        default: float,
        **kwargs: Any,
    ) -> Any:
        value = self.initial_data.get(field, default)
        return st.number_input(
            label,
            value=value,
            key=_session_key(field, self.mode),
            **kwargs,
        )


class JobMasterForm:
    """Job Master form component for CRUD operations."""

    @staticmethod
    def render_master_form(
        mode: str = "create",
        initial_data: dict[str, Any] | None = None,
        *,
        template_renderer: Callable[[str], None] | None = None,
    ) -> dict[str, Any] | None:
        """Render job master creation/edit form."""

        initial_data = initial_data or {}
        template_renderer = template_renderer or _render_template_selector

        if mode == "create":
            template_renderer(mode)

        fields = FieldDefinitions(mode=mode, initial_data=initial_data)

        with st.form(f"job_master_form_{mode}"):
            st.subheader("📋 Basic Information")

            name = fields.text_input(
                "Name*",
                "name",
                default="",
                placeholder="API Notification Master",
                help="Unique identifier for the job master template",
            )

            description = fields.text_area(
                "Description",
                "description",
                default="",
                placeholder="Describe what this master template does...",
                help="Optional description of the master template purpose",
                height=80,
            )

            st.divider()

            st.subheader("🌐 HTTP Request Configuration")
            col1, col2 = st.columns([3, 1])

            with col1:
                url = fields.text_input(
                    "URL*",
                    "url",
                    placeholder="https://api.example.com/v1/endpoint",
                    help="Target API endpoint URL",
                )

            with col2:
                methods = [
                    "GET",
                    "POST",
                    "PUT",
                    "DELETE",
                    "PATCH",
                    "HEAD",
                    "OPTIONS",
                ]
                current_method = initial_data.get("method", "GET")
                method_index = (
                    methods.index(current_method) if current_method in methods else 0
                )
                method = st.selectbox(
                    "Method*",
                    methods,
                    index=method_index,
                    key=_session_key("method", mode),
                    help="HTTP method",
                )

            timeout_sec = fields.number_input(
                "Timeout (seconds)",
                "timeout",
                default=30,
                min_value=1,
                max_value=3600,
                help="Request timeout in seconds (max: 3600)",
            )

            st.divider()

            st.subheader("📋 Request Configuration")
            st.caption(
                "Configure default HTTP request parameters (all optional)",
            )

            headers_default = (
                json.dumps(initial_data["headers"], indent=2)
                if initial_data.get("headers")
                else ""
            )
            headers = fields.text_area(
                "Headers (JSON)",
                "headers",
                default=headers_default,
                placeholder=HEADERS_PLACEHOLDER,
                help="HTTP headers in JSON format",
                height=100,
            )

            params_default = (
                json.dumps(initial_data["params"], indent=2)
                if initial_data.get("params")
                else ""
            )
            params = fields.text_area(
                "Query Parameters (JSON)",
                "params",
                default=params_default,
                placeholder=PARAMS_PLACEHOLDER,
                help="Query parameters in JSON format",
                height=80,
            )

            body_default = (
                json.dumps(initial_data["body"], indent=2)
                if initial_data.get("body")
                else ""
            )
            body = fields.text_area(
                "Request Body (JSON)",
                "body",
                default=body_default,
                placeholder=BODY_PLACEHOLDER,
                help=("Request body in JSON format (supports deep merge on override)"),
                height=120,
            )

            st.divider()

            st.subheader("🔄 Retry Configuration")
            col1, col2, col3 = st.columns(3)

            with col1:
                max_attempts = fields.number_input(
                    "Max Attempts",
                    "max_attempts",
                    default=1,
                    min_value=1,
                    max_value=10,
                    help="Maximum retry attempts (1-10)",
                )

            with col2:
                backoff_strategies = ["fixed", "linear", "exponential"]
                current_strategy = initial_data.get(
                    "backoff_strategy",
                    "exponential",
                )
                strategy_index = (
                    backoff_strategies.index(current_strategy)
                    if current_strategy in backoff_strategies
                    else 2
                )
                backoff_strategy = st.selectbox(
                    "Backoff Strategy",
                    backoff_strategies,
                    index=strategy_index,
                    key=_session_key("backoff_strategy", mode),
                    help="Retry backoff strategy",
                )

            with col3:
                backoff_seconds = fields.number_input(
                    "Backoff Seconds",
                    "backoff_seconds",
                    default=5.0,
                    min_value=0.1,
                    max_value=300.0,
                    step=0.5,
                    help="Base backoff time in seconds",
                )

            st.divider()

            st.subheader("⚙️ Additional Settings")
            col1, col2 = st.columns(2)

            with col1:
                ttl_seconds = fields.number_input(
                    "TTL (seconds)",
                    "ttl",
                    default=604800,
                    min_value=0,
                    max_value=31_536_000,
                    help=(
                        "Time to live for jobs created from this master "
                        "(default: 7 days)"
                    ),
                )

            with col2:
                tags_default = (
                    ", ".join(initial_data["tags"]) if initial_data.get("tags") else ""
                )
                tags = fields.text_input(
                    "Tags (comma-separated)",
                    "tags",
                    default=tags_default,
                    placeholder="api, webhook, notification",
                    help="Tags for categorizing the master",
                )

            submitted = st.form_submit_button(
                f"{'🚀 Create' if mode == 'create' else '💾 Update'} Master",
                type="primary",
                use_container_width=True,
            )

            if not submitted:
                return None

            if not name.strip():
                st.error("❌ Name is required")
                return None

            if not url.strip():
                st.error("❌ URL is required")
                return None

            try:
                headers_dict = _parse_json_field(headers)
                params_dict = _parse_json_field(params)
                body_dict = _parse_json_field(body)
            except json.JSONDecodeError as exc:
                st.error(f"❌ Invalid JSON format: {exc}")
                st.info(JSON_ERROR_HELP)
                return None

            tags_list = _parse_tags(tags)

            return {
                "name": name.strip(),
                "description": description.strip() or None,
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

        return None
