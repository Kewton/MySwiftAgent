import asyncio
from typing import Any

import httpx

from ..core.logging import get_logger
from ..repositories.execution_repository import execution_repository

logger = get_logger(__name__)


def execute_http_job(
    url: str,
    method: str,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout_sec: float = 30.0,
    max_retries: int = 0,
    retry_backoff_sec: float = 1.0,
    job_id: str | None = None,  # 実行履歴記録用のjob_id
) -> None:
    """ジョブとして実行されるHTTPリクエスト関数（同期）"""

    # 実行中のジョブIDを取得（APSchedulerのコンテキストから）
    actual_job_id = job_id
    if not actual_job_id:
        try:
            # APSchedulerのJobExecutionContextから実行中のジョブIDを取得
            import inspect
            frame = inspect.currentframe()
            while frame:
                if '_job' in frame.f_locals:
                    apscheduler_job = frame.f_locals['_job']
                    if hasattr(apscheduler_job, 'id'):
                        actual_job_id = apscheduler_job.id
                        break
                frame = frame.f_back

            # フレームスタックでも見つからない場合は、グローバルから推測
            if not actual_job_id:
                from threading import current_thread
                thread_name = current_thread().name
                if 'APScheduler' in thread_name and url:
                    # ログから推測（最適ではないが、フォールバック）
                    logger.info(f"Executing HTTP job without explicit job_id, URL: {url}")
        except Exception as e:
            logger.debug(f"Could not determine job_id from context: {e}")

    # 実行履歴記録開始
    execution_id = None
    if actual_job_id:
        try:
            execution_id = execution_repository.create_execution(actual_job_id, "running")
            logger.info(f"Started execution tracking: {execution_id} for job {actual_job_id}")
        except Exception as e:
            logger.error(f"Failed to create execution record: {e}")

    async def _async_execute() -> dict[str, Any]:
        """非同期実行部分"""
        result = {
            "success": False,
            "status_code": None,
            "response_size": None,
            "response_body": None,
            "error_message": None,
            "attempts": 0,
        }

        async with httpx.AsyncClient() as client:
            for attempt in range(max_retries + 1):
                result["attempts"] = attempt + 1
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

                    result["status_code"] = response.status_code
                    result["response_size"] = len(response.content) if response.content else 0
                    
                    # レスポンスボディを保存
                    try:
                        result["response_body"] = response.json()
                    except Exception:
                        # JSONでない場合はテキストとして保存
                        result["response_body"] = response.text

                    # 4xxエラーはリトライしない
                    if 400 <= response.status_code < 500:
                        result["error_message"] = f"Client error {response.status_code}"
                        logger.error(f"Client error {response.status_code} for {method} {url}")
                        break

                    # 5xxエラーまたは200番台以外はリトライ対象
                    if response.status_code >= 500 or response.status_code < 200:
                        if attempt < max_retries:
                            await asyncio.sleep(retry_backoff_sec * (attempt + 1))
                            continue
                        else:
                            result["error_message"] = f"Max retries exceeded, last status: {response.status_code}"
                            logger.error(f"Max retries exceeded for {method} {url}")
                            break

                    # 成功
                    result["success"] = True
                    logger.info(f"Successfully executed {method} {url} - Status: {response.status_code}")
                    return result

                except Exception as e:
                    result["error_message"] = str(e)
                    logger.error(f"Error executing {method} {url}: {str(e)}")
                    if attempt < max_retries:
                        await asyncio.sleep(retry_backoff_sec * (attempt + 1))
                    else:
                        logger.error(f"Max retries exceeded for {method} {url}")
                        break

        return result

    # 実行とログ記録
    execution_result = None
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        execution_result = loop.run_until_complete(_async_execute())
    finally:
        loop.close()

    # 実行履歴記録終了
    if execution_id and actual_job_id:
        try:
            status = "completed" if execution_result and execution_result["success"] else "failed"
            execution_repository.update_execution(
                execution_id=execution_id,
                status=status,
                result=execution_result,
                error_message=execution_result.get("error_message") if execution_result else "Unknown error",
                http_status_code=execution_result.get("status_code") if execution_result else None,
                response_size=execution_result.get("response_size") if execution_result else None,
            )
            logger.info(f"Updated execution record: {execution_id} with status {status}")
        except Exception as e:
            logger.error(f"Failed to update execution record: {e}")
