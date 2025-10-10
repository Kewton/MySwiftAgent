"""myVault - Secure personal data vault and secret management service."""

import logging
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

# Configure logging
log_dir = Path(settings.log_dir)
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "app.log"

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file, mode="a", encoding="utf-8"),
    ],
    force=True,  # Force reconfiguration even if logging was already configured
)

logger = logging.getLogger(__name__)
logger.info(f"Logging configured: log_dir={log_dir}, log_level={settings.log_level}")


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
