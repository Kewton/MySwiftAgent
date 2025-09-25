"""HTTP client with retry logic for CommonUI application."""

import logging
from typing import Any, Dict, Optional

import httpx
import streamlit as st
from httpx import Response

from core.config import APIConfig
from core.exceptions import APIError, AuthenticationError, RateLimitError, ServiceUnavailableError

logger = logging.getLogger(__name__)


class HTTPClient:
    """HTTP client with automatic retries and error handling."""

    def __init__(self, api_config: APIConfig, service_name: str) -> None:
        """Initialize HTTP client with API configuration."""
        self.api_config = api_config
        self.service_name = service_name
        self.client = httpx.Client(
            base_url=api_config.base_url,
            headers={"Authorization": f"Bearer {api_config.token}"},
            timeout=30.0,
        )

    def __enter__(self) -> "HTTPClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.client.close()

    def _handle_response(self, response: Response) -> Dict[str, Any]:
        """Handle HTTP response and raise appropriate exceptions."""
        try:
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise AuthenticationError(self.service_name)
            elif response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise RateLimitError(int(retry_after) if retry_after else None)
            elif response.status_code >= 500:
                raise ServiceUnavailableError(self.service_name, self.api_config.base_url)
            else:
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
        except httpx.JSONDecodeError:
            if response.status_code == 200:
                return {"message": "Success", "data": response.text}
            raise APIError(
                f"Invalid JSON response: {response.text[:100]}",
                status_code=response.status_code,
            )

    def _request_with_retry(self, method: str, url: str, **kwargs: Any) -> Dict[str, Any]:
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
                raise APIError(f"Unexpected error: {str(e)}")

        raise ServiceUnavailableError(self.service_name, self.api_config.base_url)

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make GET request."""
        return self._request_with_retry("GET", endpoint, params=params)

    def post(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make POST request."""
        return self._request_with_retry("POST", endpoint, json=json_data)

    def put(self, endpoint: str, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make PUT request."""
        return self._request_with_retry("PUT", endpoint, json=json_data)

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make DELETE request."""
        return self._request_with_retry("DELETE", endpoint)

    def health_check(self) -> bool:
        """Perform health check on the service."""
        try:
            self.get("/health")
            return True
        except Exception:
            return False