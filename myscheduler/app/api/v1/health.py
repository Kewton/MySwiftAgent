from fastapi import APIRouter

from ...core.config import settings
from ...schemas.job import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """ヘルスチェック"""
    return HealthResponse(
        message="MyScheduler API is running",
        timezone=str(settings.tz),
        version=settings.app_version,
    )
