"""
HTTP Method Validator Middleware

POST が必要なエンドポイントへの GET リクエストを JSON エラーで返却します。
これにより、誤って GET でアクセスした場合でも Swagger UI の HTML ではなく、
JSON エラーが返されることを保証します。

使用方法:
    app.add_middleware(
        MethodValidatorMiddleware,
        post_only_paths=["/v1/aiagent", "/v1/utility"]
    )
"""

import logging
from typing import cast

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class MethodValidatorMiddleware(BaseHTTPMiddleware):
    """
    POST 必須エンドポイントへの GET リクエストを拒否

    このミドルウェアは Layer 1 として機能し、
    以下の処理を行います:
    1. リクエストパスが post_only_paths に該当するかチェック
    2. GET リクエストの場合、405 Method Not Allowed を JSON で返却
    3. POST リクエストの場合、次のミドルウェアへ渡す
    """

    def __init__(self, app: ASGIApp, post_only_paths: list[str] | None = None):
        """
        Args:
            app: ASGI application
            post_only_paths: POST のみ許可するパスのプレフィックスリスト
                            例: ["/v1/aiagent", "/v1/utility"]
                            これらのパスで始まるエンドポイントは POST のみ許可
        """
        super().__init__(app)
        self.post_only_paths = post_only_paths or []

    async def dispatch(self, request: Request, call_next) -> Response:
        """
        GET リクエストを検証し、POST 必須パスの場合は JSON エラーを返却

        Args:
            request: FastAPI Request
            call_next: 次のミドルウェアまたはエンドポイント

        Returns:
            Response: JSON エラーまたは通常のレスポンス
        """
        # POST 必須パスかチェック
        is_post_only = any(
            request.url.path.startswith(path) for path in self.post_only_paths
        )

        if is_post_only and request.method == "GET":
            logger.warning(
                f"GET request rejected for POST-only endpoint: {request.url.path}"
            )
            return JSONResponse(
                status_code=405,  # Method Not Allowed
                content={
                    "detail": f"Method {request.method} not allowed. This endpoint requires POST.",
                    "allowed_methods": ["POST"],
                    "is_json_guaranteed": True,
                    "middleware_layer": "method_validator",
                },
            )

        return cast(Response, await call_next(request))
