"""
Response Validator Middleware

全てのレスポンスを検証し、JSON 以外のレスポンスを JSON に変換します。
これは最終防衛線として機能し、万が一 HTML や Plain Text が返された場合でも
強制的に JSON 形式に変換します。

使用方法:
    app.add_middleware(
        ResponseValidatorMiddleware,
        force_json_paths=["/v1/aiagent", "/v1/utility"]
    )
"""

import json
import logging
from typing import Callable, cast

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class ResponseValidatorMiddleware(BaseHTTPMiddleware):
    """
    全てのレスポンスを JSON 形式に保証するミドルウェア

    このミドルウェアは Layer 4（最終防衛線）として機能し、
    以下の処理を行います:
    1. Content-Type が application/json 以外のレスポンスを検出
    2. force_json_paths に該当するパスの場合、JSON に変換
    3. 変換できない場合は元のコンテンツを JSON にラップ
    """

    def __init__(self, app: ASGIApp, force_json_paths: list[str] | None = None):
        """
        Args:
            app: ASGI application
            force_json_paths: JSON を強制するパスのプレフィックスリスト
                             例: ["/v1/aiagent", "/v1/utility"]
                             これらのパスで始まるエンドポイントは必ず JSON を返す
        """
        super().__init__(app)
        self.force_json_paths = force_json_paths or []

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        レスポンスを検証し、必要に応じて JSON 形式に変換

        Args:
            request: FastAPI Request
            call_next: 次のミドルウェアまたはエンドポイント

        Returns:
            Response: JSON 形式が保証されたレスポンス
        """
        response = await call_next(request)

        # Force JSON が必要なパスかチェック
        should_force_json = any(
            request.url.path.startswith(path) for path in self.force_json_paths
        )

        if not should_force_json:
            # force_json_paths に該当しない場合はそのまま返す
            return cast(Response, response)

        # Content-Type が JSON 以外の場合、JSON に変換
        content_type = response.headers.get("content-type", "")

        if not content_type.startswith("application/json"):
            logger.warning(
                f"Non-JSON response detected: path={request.url.path}, "
                f"content_type={content_type}, status={response.status_code}"
            )

            # レスポンスボディを読み取り
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            # JSON に変換を試みる
            try:
                # 既に JSON の場合はそのまま返す
                json.loads(body.decode("utf-8"))
                json_body = body
                logger.info(
                    "Response body is valid JSON despite incorrect Content-Type"
                )
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                # JSON でない場合は JSON にラップ
                logger.error(
                    f"Forcing non-JSON content to JSON format: {body[:200]!r}... Error: {e}"
                )
                json_content = {
                    "detail": "Non-JSON response was converted to JSON",
                    "original_content_type": content_type,
                    "original_content": body.decode("utf-8", errors="replace")[:1000],
                    "is_json_guaranteed": True,
                    "middleware_layer": "response_validator",
                }
                json_body = json.dumps(json_content).encode("utf-8")

            # JSON レスポンスとして返却
            return Response(
                content=json_body,
                status_code=response.status_code,
                headers={
                    **dict(response.headers),
                    "content-type": "application/json",
                    "content-length": str(len(json_body)),
                },
            )

        return cast(Response, response)
