"""FastAPI JobQueue main application."""

import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.health import router as health_router
from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import init_db
from app.core.worker import WorkerManager

logger = logging.getLogger(__name__)


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
