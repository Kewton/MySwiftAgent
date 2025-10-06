"""Main FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import admin_endpoints, agent_endpoints, utility_endpoints
from core.logger import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup: Initialize logging
    setup_logging()
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="Expert Agent Service",
    version="0.1.0",
    description="Expert Agent Service for MySwiftAgent - LangGraph AI Agents API",
    root_path="/aiagent-api",
    swagger_ui_parameters={
        "docExpansion": "list",
        "defaultModelsExpandDepth": -1,
    },
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(agent_endpoints.router, prefix="/v1")
app.include_router(utility_endpoints.router, prefix="/v1")
app.include_router(admin_endpoints.router, prefix="/v1")


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
