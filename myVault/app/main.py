"""myVault - Secure personal data vault and secret management service."""

import logging
import logging.handlers
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import projects, secrets
from app.core.config import settings
from app.core.database import init_db

# Load .env file from project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Configure logging (multi-worker compatible)
log_dir = Path(settings.log_dir)
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "myvault.log"
error_log_file = log_dir / "myvault_rotation.log"

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
    level=getattr(logging, settings.log_level.upper()),
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
    f"Logging configured: log_dir={log_dir}, log_level={settings.log_level}, PID={os.getpid()}"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup: Initialize database
    init_db()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="myVault",
    version="0.1.0",
    description="Secure personal data vault and secret management service",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects.router)
app.include_router(secrets.router)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint (required for CI/CD)."""
    return {"status": "healthy", "service": "myVault"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Welcome to myVault - Secure data vault service"}
