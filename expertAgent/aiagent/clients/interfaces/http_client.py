"""HTTP client interface and implementations.

Issue #361: Protocol-based HTTP client abstraction for testability.

This module provides:
- IHttpClient: Protocol for HTTP client abstraction
- HttpResponse: Response data container
- HttpxClientAdapter: httpx-based implementation
"""

import time
from dataclasses import dataclass
from typing import Any, Protocol

import httpx


@dataclass
class HttpResponse:
    """HTTP response abstraction.

    Attributes:
        status_code: HTTP status code
        json_data: Parsed JSON response data
        headers: Response headers
        elapsed_ms: Request latency in milliseconds
    """

    status_code: int
    json_data: dict[str, Any]
    headers: dict[str, str]
    elapsed_ms: float


class IHttpClient(Protocol):
    """HTTP client interface for testability.

    This protocol enables dependency injection of HTTP clients,
    making it easy to mock in tests.

    Example:
        class MockHttpClient:
            async def post(self, url, json, headers=None, timeout=None):
                return HttpResponse(status_code=200, json_data={}, ...)

            async def get(self, url, headers=None, timeout=None):
                return HttpResponse(status_code=200, json_data={}, ...)

            async def close(self):
                pass

        client = WorkflowGeneratorClient(http_client=MockHttpClient())
    """

    async def post(
        self,
        url: str,
        json: dict[str, Any],
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        """Send POST request.

        Args:
            url: Request URL (relative to base_url)
            json: Request body as JSON-serializable dict
            headers: Additional headers
            timeout: Request timeout in seconds

        Returns:
            HttpResponse with status, data, headers, and timing
        """
        ...

    async def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        """Send GET request.

        Args:
            url: Request URL (relative to base_url)
            headers: Additional headers
            timeout: Request timeout in seconds

        Returns:
            HttpResponse with status, data, headers, and timing
        """
        ...

    async def close(self) -> None:
        """Close and release resources."""
        ...


class HttpxClientAdapter:
    """httpx-based implementation of IHttpClient.

    Wraps httpx.AsyncClient to conform to IHttpClient protocol.

    Example:
        adapter = HttpxClientAdapter(
            base_url="http://localhost:8006",
            timeout=30.0
        )
        async with adapter:
            response = await adapter.post("/api/test", json={"data": "test"})
    """

    def __init__(self, base_url: str, timeout: float = 30.0):
        """Initialize adapter.

        Args:
            base_url: Base URL for all requests
            timeout: Default timeout in seconds
        """
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)
        self._base_url = base_url
        self._timeout = timeout

    async def post(
        self,
        url: str,
        json: dict[str, Any],
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        """Send POST request.

        Args:
            url: Request URL (relative to base_url)
            json: Request body
            headers: Additional headers
            timeout: Override default timeout

        Returns:
            HttpResponse with response data

        Raises:
            httpx.TimeoutException: On timeout
            httpx.HTTPStatusError: On HTTP error status
        """
        start_time = time.perf_counter()

        response = await self._client.post(
            url,
            json=json,
            headers=headers,
            timeout=timeout or self._timeout,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return HttpResponse(
            status_code=response.status_code,
            json_data=response.json(),
            headers=dict(response.headers),
            elapsed_ms=elapsed_ms,
        )

    async def get(
        self,
        url: str,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> HttpResponse:
        """Send GET request.

        Args:
            url: Request URL (relative to base_url)
            headers: Additional headers
            timeout: Override default timeout

        Returns:
            HttpResponse with response data

        Raises:
            httpx.TimeoutException: On timeout
            httpx.HTTPStatusError: On HTTP error status
        """
        start_time = time.perf_counter()

        response = await self._client.get(
            url,
            headers=headers,
            timeout=timeout or self._timeout,
        )

        elapsed_ms = (time.perf_counter() - start_time) * 1000

        return HttpResponse(
            status_code=response.status_code,
            json_data=response.json(),
            headers=dict(response.headers),
            elapsed_ms=elapsed_ms,
        )

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self._client.aclose()

    async def __aenter__(self) -> "HttpxClientAdapter":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.close()
