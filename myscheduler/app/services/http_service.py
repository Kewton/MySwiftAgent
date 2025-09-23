import asyncio
from typing import Any

import httpx

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class HTTPService:
    """HTTP実行サービス"""

    def __init__(self):
        self.client = httpx.AsyncClient()

    async def close(self) -> None:
        """HTTPクライアントを閉じる"""
        await self.client.aclose()

    async def execute_request(
        self,
        url: str,
        method: str,
        headers: dict[str, str] | None = None,
        body: dict[str, Any] | None = None,
        timeout_sec: float = None,
        max_retries: int = None,
        retry_backoff_sec: float = None,
    ) -> None:
        """外部APIへのHTTPリクエストを実行"""

        # デフォルト値の設定
        timeout_sec = timeout_sec or settings.http_timeout
        max_retries = max_retries or settings.max_retries
        retry_backoff_sec = retry_backoff_sec or settings.retry_backoff

        for attempt in range(max_retries + 1):
            try:
                kwargs = {"timeout": timeout_sec, "headers": headers or {}}

                if body and method.upper() in ["POST", "PUT", "PATCH"]:
                    kwargs["json"] = body

                response = await self.client.request(method.upper(), url, **kwargs)

                # 4xxエラーはリトライしない
                if 400 <= response.status_code < 500:
                    logger.error(
                        f"Client error {response.status_code} for {method} {url}"
                    )
                    break

                # 5xxエラーまたは200番台以外はリトライ対象
                if response.status_code >= 500 or response.status_code < 200:
                    if attempt < max_retries:
                        await asyncio.sleep(retry_backoff_sec * (attempt + 1))
                        continue
                    else:
                        logger.error(f"Max retries exceeded for {method} {url}")
                        break

                # 成功
                logger.info(
                    f"Successfully executed {method} {url} - Status: {response.status_code}"
                )
                return

            except Exception as e:
                logger.error(f"Error executing {method} {url}: {str(e)}")
                if attempt < max_retries:
                    await asyncio.sleep(retry_backoff_sec * (attempt + 1))
                else:
                    logger.error(f"Max retries exceeded for {method} {url}")
                    break


# グローバルHTTPサービス
http_service = HTTPService()
