"""myVault - Secure personal data vault and secret management service."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import projects, secrets
from app.core.database import init_db


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
