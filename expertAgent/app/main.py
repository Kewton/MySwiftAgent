"""Main FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import (
    admin_endpoints,
    agent_endpoints,
    drive_endpoints,
    gmail_utility_endpoints,
    google_auth_endpoints,
    job_generator_endpoints,
    tts_endpoints,
    utility_endpoints,
)
from app.middleware import MethodValidatorMiddleware, ResponseValidatorMiddleware
from core.logger import setup_logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Initialize logging
    setup_logging()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="Expert Agent Service",
    version="0.2.0",
    description="Expert Agent Service for MySwiftAgent - LangGraph AI Agents API with JSON Response Guarantee",
    root_path="/aiagent-api",
    swagger_ui_parameters={
        "docExpansion": "list",
        "defaultModelsExpandDepth": -1,
    },
    lifespan=lifespan,
)

# Layer 1: Method Validator Middleware (GET リクエスト拒否)
app.add_middleware(
    MethodValidatorMiddleware,
    post_only_paths=["/v1/aiagent", "/v1/utility"],
)

# Layer 4: Response Validator Middleware (最終防衛線)
app.add_middleware(
    ResponseValidatorMiddleware,
    force_json_paths=["/v1/aiagent", "/v1/utility", "/v1/admin"],
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Layer 3: Global Exception Handlers


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    予期しない全ての例外を JSON 形式で返却（Layer 3）

    このハンドラは全ての未処理例外をキャッチし、JSON 形式のエラーレスポンスを返します。
    これにより、どんな状況でも JSON レスポンスが保証されます。
    """
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error occurred",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "is_json_guaranteed": True,
            "middleware_layer": "global_exception_handler",
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    HTTP 例外を JSON 形式で返却（Layer 3）

    404, 401, 405 などの HTTP エラーを JSON 形式で返却します。
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "is_json_guaranteed": True,
            "middleware_layer": "http_exception_handler",
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    リクエストバリデーションエラーを JSON 形式で返却（Layer 3）

    Pydantic バリデーションエラーを JSON 形式で返却します。
    """
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
            "is_json_guaranteed": True,
            "middleware_layer": "validation_exception_handler",
        },
    )


# Include routers
app.include_router(agent_endpoints.router, prefix="/v1")
app.include_router(utility_endpoints.router, prefix="/v1")
app.include_router(gmail_utility_endpoints.router, prefix="/v1")
app.include_router(drive_endpoints.router, prefix="/v1", tags=["Drive Utilities"])
app.include_router(tts_endpoints.router, prefix="/v1", tags=["TTS Utilities"])
app.include_router(job_generator_endpoints.router, prefix="/v1", tags=["Job Generator"])
app.include_router(admin_endpoints.router, prefix="/v1")
app.include_router(google_auth_endpoints.router, prefix="/v1")


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint (used by CI/CD)."""
    return {"status": "healthy", "service": "expertAgent"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Welcome to Expert Agent Service"}


@app.get("/api/v1/")
async def api_root() -> dict[str, str]:
    """API v1 root endpoint."""
    return {"version": "1.0", "service": "expertAgent"}
