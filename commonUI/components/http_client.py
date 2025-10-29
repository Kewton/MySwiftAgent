"""HTTP client with retry logic for CommonUI application."""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Self, cast

import httpx

try:
    import streamlit as st  # type: ignore[import-not-found]
except ModuleNotFoundError:
    st = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from collections.abc import MutableMapping

from core.exceptions import (
    APIError,
    AuthenticationError,
    RateLimitError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)

RetryCallback = Callable[[int, int, str], None]


def _build_auth_headers(api_config: Any) -> MutableMapping[str, str]:
    headers: MutableMapping[str, str] = {}

    service_token = getattr(api_config, "service_token", "")
    service_name = getattr(api_config, "service_name", "")
    admin_token = getattr(api_config, "admin_token", "")
    bearer_token = getattr(api_config, "token", "")

    if service_name and service_token:
        headers["X-Service"] = service_name
        headers["X-Token"] = service_token
    elif admin_token and admin_token.strip():
        headers["X-Admin-Token"] = admin_token
    elif bearer_token and bearer_token.strip():
        headers["Authorization"] = f"Bearer {bearer_token}"

    return headers


def _default_retry_callback(
    retry: int,
    max_retries: int,
    service: str,
) -> None:
    if st is None:
        return
    st.info(
        f"{service} temporarily unavailable, retrying... ({retry}/{max_retries})",
    )


@dataclass(slots=True)
class HTTPClient:
    """HTTP client with automatic retries and error handling."""

    api_config: Any
    service_name: str
    retry_callback: RetryCallback | None = None
    timeout: float = 30.0
    _client: httpx.Client | None = None

    def __post_init__(self) -> None:
        headers = _build_auth_headers(self.api_config)
        self.retry_callback = self.retry_callback or _default_retry_callback
        self._client = httpx.Client(
            base_url=self.api_config.base_url,
            headers=headers,
            timeout=self.timeout,
        )

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.api_config.base_url,
                headers=_build_auth_headers(self.api_config),
                timeout=self.timeout,
            )
        return self._client

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def __enter__(self) -> Self:  # pragma: no cover - context sugar
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        try:
            if response.status_code in (200, 201):
                return cast("dict[str, Any]", response.json())
            if response.status_code == 204:
                return {"message": "Success"}
            if response.status_code == 401:
                raise AuthenticationError(self.service_name)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise RateLimitError(int(retry_after) if retry_after else None)
            if response.status_code >= 500:
                raise ServiceUnavailableError(
                    self.service_name,
                    self.api_config.base_url,
                )
            error_data: dict[str, Any] = {}
            with contextlib.suppress(Exception):
                error_data = dict(response.json())
            msg = f"HTTP {response.status_code}: {response.reason_phrase}"
            raise APIError(
                msg,
                status_code=response.status_code,
                response_data=error_data,
            )
        except (ValueError, KeyError):
            if response.status_code in (200, 201):
                return {"message": "Success", "data": response.text}
            msg = f"Invalid JSON response: {response.text[:100]}"
            raise APIError(
                msg,
                status_code=response.status_code,
            )

    def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                response = self.client.request(method, url, **kwargs)
                return self._handle_response(response)
            except ServiceUnavailableError:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                if self.retry_callback:
                    self.retry_callback(
                        retry_count,
                        max_retries,
                        self.service_name,
                    )
            except (AuthenticationError, RateLimitError, APIError):
                raise
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.exception("Unexpected error during %s %s", method, url)
                msg = f"Unexpected error: {exc!s}"
                raise APIError(msg)

        raise ServiceUnavailableError(
            self.service_name,
            getattr(self.api_config, "base_url", ""),
        )

    def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request_with_retry("GET", endpoint, params=params)

    def post(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request_with_retry("POST", endpoint, json=json_data)

    def put(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request_with_retry("PUT", endpoint, json=json_data)

    def patch(
        self,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._request_with_retry("PATCH", endpoint, json=json_data)

    def delete(self, endpoint: str) -> dict[str, Any]:
        return self._request_with_retry("DELETE", endpoint)

    def health_check(self) -> bool:
        try:
            self.get("/health")
            return True
        except Exception:
            return False
