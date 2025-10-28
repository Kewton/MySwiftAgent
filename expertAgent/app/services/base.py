"""Base class for application services."""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, TypeVar

from core.config import settings
from core.test_mode_handler import handle_test_mode

from .response_builder import ResponseBuilder
from .retry_policies import RetryConfig, RetryResult

_T = TypeVar("_T")


class BaseService:
    """Provide shared utilities for application services."""

    def __init__(
        self,
        *,
        logger: logging.Logger | None = None,
        response_builder: ResponseBuilder | None = None,
        retry_config: RetryConfig | None = None,
    ) -> None:
        self._logger = logger or logging.getLogger(self.__class__.__name__)
        self._response_builder = response_builder or ResponseBuilder()
        self._retry_config = retry_config or RetryConfig()

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def response_builder(self) -> ResponseBuilder:
        return self._response_builder

    @property
    def retry_config(self) -> RetryConfig:
        return self._retry_config

    def handle_test_mode(
        self,
        *,
        test_mode: bool,
        test_response: dict[str, Any] | str | None,
        endpoint_name: str,
    ) -> Any | None:
        """Delegate to shared test mode handler and log usage."""

        result = handle_test_mode(test_mode, test_response, endpoint_name)
        if result is not None:
            self.logger.info(
                "Returning test mode response for %s",
                endpoint_name,
            )
        return result

    async def run_with_retry(
        self,
        operation: Callable[[], Awaitable[_T]],
    ) -> RetryResult[_T]:
        """Execute an async operation with retry handling."""

        return await self.retry_config.run_async(operation, logger=self.logger)

    def get_setting(self, name: str, default: Any = None) -> Any:
        """Return attribute from global settings with optional default."""

        return getattr(settings, name, default)
