"""FastAPI JobQueue main application."""

import asyncio
import logging
import logging.handlers
import os
import sys
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import init_db
from app.core.worker import WorkerManager

# Get settings first
settings = get_settings()

# Configure logging (multi-worker compatible)
log_dir = Path(settings.LOG_DIR)
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "jobqueue.log"
error_log_file = log_dir / "jobqueue_rotation.log"

# Create handlers
stream_handler = logging.StreamHandler(sys.stdout)
rotating_handler = logging.handlers.RotatingFileHandler(
    log_file,
    mode="a",
    maxBytes=1024 * 1024,
    backupCount=5,
    encoding="utf-8",
)
error_handler = logging.handlers.TimedRotatingFileHandler(
    error_log_file,
    when="S",
    interval=1,
    backupCount=5,
    encoding="utf-8",
)
error_handler.setLevel(logging.ERROR)

handlers: list[logging.Handler] = [stream_handler, rotating_handler, error_handler]

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format="[%(process)d-%(thread)d]-%(asctime)s-%(levelname)s-%(message)s",
    handlers=handlers,
    force=True,  # Force reconfiguration for multi-worker mode
)

# SQLAlchemyのログレベルを調整（DEBUGログを抑制）
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)
logger.info(
    f"Logging configured: log_dir={log_dir}, log_level={settings.LOG_LEVEL}, PID={os.getpid()}"
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan management."""
    get_settings()

    # Initialize database
    await init_db()

    # Start background worker
    worker_manager = WorkerManager()
    worker_task = asyncio.create_task(worker_manager.start())

    try:
        yield
    finally:
        # Cleanup
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            logger.info("Worker task cancelled")


def create_app() -> FastAPI:
    """Create FastAPI application."""
    get_settings()

    app = FastAPI(
        title="JobQueue API",
        description="FastAPI-based HTTP API job queue with async execution and persistence",
        version="0.1.0",
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health_router)  # Root and health endpoints
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_app()
