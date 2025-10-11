"""Admin endpoints for expertAgent."""

import logging

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from core.config import settings
from core.secrets import secrets_manager

logger = logging.getLogger(__name__)

router = APIRouter()


class ReloadSecretsRequest(BaseModel):
    """Request schema for reloading secrets."""

    project: str | None = None  # Optional project to reload (all if not specified)


class ReloadSecretsResponse(BaseModel):
    """Response schema for reload secrets."""

    status: str
    message: str


@router.post(
    "/admin/reload-secrets",
    summary="Reload secrets cache",
    description="Manual reload of secrets cache. Requires ADMIN_TOKEN.",
    response_model=ReloadSecretsResponse,
)
async def reload_secrets(
    request: ReloadSecretsRequest,
    x_admin_token: str | None = Header(None, alias="X-Admin-Token"),
):
    """Manually reload secrets cache.

    Requires ADMIN_TOKEN in X-Admin-Token header for authentication.

    Args:
        request: Project to reload (optional, clears all if not specified)
        x_admin_token: Admin token from header

    Returns:
        Status message

    Raises:
        HTTPException: If authentication fails
    """
    # Check admin token
    if not settings.ADMIN_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="Admin token not configured. Set ADMIN_TOKEN environment variable.",
        )

    logger.info("reload_secrets called")
    logger.info(f"request: {request}")
    logger.info(f"x_admin_token: {x_admin_token}")
    logger.info(f"settings.ADMIN_TOKEN: {settings.ADMIN_TOKEN}")
    if not x_admin_token or x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing admin token")

    # Clear cache
    try:
        secrets_manager.clear_cache(project=request.project)

        if request.project:
            message = f"Secrets cache cleared for project: {request.project}"
        else:
            message = "All secrets cache cleared"

        return ReloadSecretsResponse(status="success", message=message)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to reload secrets: {str(e)}"
        ) from e


@router.get(
    "/admin/health",
    summary="Admin health check",
    description="Health check for admin endpoints",
)
async def admin_health(x_admin_token: str | None = Header(None, alias="X-Admin-Token")):
    """Admin health check endpoint.

    Requires ADMIN_TOKEN in X-Admin-Token header for authentication.

    Returns:
        Health status
    """
    # Check admin token
    if not settings.ADMIN_TOKEN:
        return {"status": "warning", "message": "Admin token not configured"}

    if not x_admin_token or x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing admin token")

    return {
        "status": "healthy",
        "myvault_enabled": settings.MYVAULT_ENABLED,
        "cache_ttl": settings.SECRETS_CACHE_TTL,
    }
