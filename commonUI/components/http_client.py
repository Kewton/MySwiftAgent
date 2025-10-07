"""HTTP client with retry logic for CommonUI application."""

import logging
from typing import Any

import httpx
import streamlit as st
from httpx import Response

from core.config import APIConfig, ExpertAgentConfig, GraphAiServerConfig, MyVaultConfig
from core.exceptions import (
    APIError,
    AuthenticationError,
    RateLimitError,
    ServiceUnavailableError,
)

logger = logging.getLogger(__name__)


class HTTPClient:
    """HTTP client with automatic retries and error handling."""

    def __init__(
        self,
        api_config: APIConfig | MyVaultConfig | ExpertAgentConfig | GraphAiServerConfig,
        service_name: str,
    ) -> None:
        """Initialize HTTP client with API configuration."""
        self.api_config = api_config
        self.service_name = service_name

        # Prepare headers based on service type
        headers = {}
        if isinstance(api_config, MyVaultConfig):
            # MyVault uses custom header authentication
            if api_config.service_name and api_config.service_token:
                headers["X-Service"] = api_config.service_name
                headers["X-Token"] = api_config.service_token
        elif isinstance(api_config, ExpertAgentConfig):
            # ExpertAgent uses admin token in X-Admin-Token header
            if api_config.admin_token and api_config.admin_token.strip():
                headers["X-Admin-Token"] = api_config.admin_token
        elif isinstance(api_config, GraphAiServerConfig):
            # GraphAiServer uses admin token in X-Admin-Token header
            if api_config.admin_token and api_config.admin_token.strip():
                headers["X-Admin-Token"] = api_config.admin_token
        elif isinstance(api_config, APIConfig):
            # Standard Bearer token authentication
            if api_config.token and api_config.token.strip():
                headers["Authorization"] = f"Bearer {api_config.token}"

        self.client = httpx.Client(
            base_url=api_config.base_url,
            headers=headers,
            timeout=30.0,
        )

    def __enter__(self) -> "HTTPClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.client.close()

    def _handle_response(self, response: Response) -> dict[str, Any]:
        """Handle HTTP response and raise appropriate exceptions."""
        try:
            if response.status_code in [200, 201]:  # Accept both 200 OK and 201 Created
                return response.json()
            if response.status_code == 204:  # No Content (e.g., successful DELETE)
                return {"message": "Success"}
            if response.status_code == 401:
                raise AuthenticationError(self.service_name)
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise RateLimitError(int(retry_after) if retry_after else None)
            if response.status_code >= 500:
                raise ServiceUnavailableError(self.service_name, self.api_config.base_url)
            error_data = {}
            try:
                error_data = response.json()
            except Exception:
                pass
            raise APIError(
                f"HTTP {response.status_code}: {response.reason_phrase}",
                status_code=response.status_code,
                response_data=error_data,
            )
        except (ValueError, KeyError):
            # Handle JSON decode errors (ValueError covers json.JSONDecodeError in older Python versions)
            if response.status_code in [200, 201]:  # Also update this condition
                return {"message": "Success", "data": response.text}
            raise APIError(
                f"Invalid JSON response: {response.text[:100]}",
                status_code=response.status_code,
            )

    def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> dict[str, Any]:
        """Make HTTP request with automatic retry for 5xx errors."""
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
                st.info(f"Service temporarily unavailable, retrying... ({retry_count}/{max_retries})")
            except (AuthenticationError, RateLimitError, APIError):
                raise
            except Exception as e:
                logger.exception(f"Unexpected error during {method} {url}")
                raise APIError(f"Unexpected error: {e!s}")

        raise ServiceUnavailableError(self.service_name, self.api_config.base_url)

    def get(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make GET request."""
        return self._request_with_retry("GET", endpoint, params=params)

    def post(self, endpoint: str, json_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make POST request."""
        return self._request_with_retry("POST", endpoint, json=json_data)

    def put(self, endpoint: str, json_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make PUT request."""
        return self._request_with_retry("PUT", endpoint, json=json_data)

    def patch(self, endpoint: str, json_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Make PATCH request."""
        return self._request_with_retry("PATCH", endpoint, json=json_data)

    def delete(self, endpoint: str) -> dict[str, Any]:
        """Make DELETE request."""
        return self._request_with_retry("DELETE", endpoint)

    def health_check(self) -> bool:
        """Perform health check on the service."""
        try:
            self.get("/health")
            return True
        except Exception:
            return False
