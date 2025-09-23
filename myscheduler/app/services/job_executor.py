import asyncio
from typing import Any

import httpx

from ..core.logging import get_logger

logger = get_logger(__name__)


def execute_http_job(
    url: str,
    method: str,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout_sec: float = 30.0,
    max_retries: int = 0,
    retry_backoff_sec: float = 1.0,
) -> None:
    """ジョブとして実行されるHTTPリクエスト関数（同期）"""

    async def _async_execute() -> None:
        """非同期実行部分"""
        async with httpx.AsyncClient() as client:
            for attempt in range(max_retries + 1):
                try:
                    if body and method.upper() in ["POST", "PUT", "PATCH"]:
                        response = await client.request(
                            method.upper(),
                            url,
                            json=body,
                            timeout=timeout_sec,
                            headers=headers or {}
                        )
                    else:
                        response = await client.request(
                            method.upper(),
                            url,
                            timeout=timeout_sec,
                            headers=headers or {}
                        )

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

    # 新しいイベントループで実行
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(_async_execute())
    finally:
        loop.close()
