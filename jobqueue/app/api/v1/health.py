"""Health check API endpoints."""

from fastapi import APIRouter

from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/", response_model=HealthResponse)
async def root_health() -> HealthResponse:
    """Root endpoint health check."""
    return HealthResponse(
        message="JobQueue API is running",
    )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Health check endpoint."""
    return HealthResponse(
        message="JobQueue API is healthy",
    )
