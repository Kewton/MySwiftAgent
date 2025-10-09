"""Google authentication management endpoints for commonUI."""

import logging
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

from core.config import settings
from core.google_creds import get_project_name, google_creds_manager
from core.secrets import secrets_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/google-auth", tags=["google-auth"])


class SyncFromMyVaultRequest(BaseModel):
    project: Optional[str] = None


class TokenStatusResponse(BaseModel):
    exists: bool
    is_valid: bool
    error_message: Optional[str] = None
    project: str


class ListProjectsResponse(BaseModel):
    projects: list[str]


class OAuth2StartRequest(BaseModel):
    project: Optional[str] = None
    redirect_uri: str = "http://localhost:8501"


class OAuth2StartResponse(BaseModel):
    auth_url: str
    state: str
    project: str


class OAuth2CallbackRequest(BaseModel):
    state: str
    code: str
    project: Optional[str] = None


class OAuth2CallbackResponse(BaseModel):
    success: bool
    message: str
    project: str


class TokenDataResponse(BaseModel):
    exists: bool
    token_json: Optional[str] = None
    project: str
    error_message: Optional[str] = None


class SaveTokenRequest(BaseModel):
    project: Optional[str] = None
    token_json: str
    save_to_myvault: bool = False


def verify_admin_token(x_admin_token: str = Header(...)):
    """Verify admin token for protected endpoints."""
    if not settings.ADMIN_TOKEN or x_admin_token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.get("/token-status", response_model=TokenStatusResponse)
async def get_token_status(
    project: Optional[str] = None, x_admin_token: str = Header(...)
):
    """Check Google token validity for specified project."""
    verify_admin_token(x_admin_token)

    project_name = get_project_name(project)
    is_valid, error_msg = google_creds_manager.check_token_validity(project_name)

    return TokenStatusResponse(
        exists=error_msg != f"Token not found for project: {project_name}",
        is_valid=is_valid,
        error_message=error_msg,
        project=project_name,
    )


@router.post("/sync-from-myvault")
async def sync_from_myvault(
    request: SyncFromMyVaultRequest, x_admin_token: str = Header(...)
):
    """Sync credentials from MyVault to local encrypted files."""
    verify_admin_token(x_admin_token)

    success = google_creds_manager.sync_from_myvault(request.project)

    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to sync from MyVault. Check logs."
        )

    project_name = get_project_name(request.project)
    return {
        "message": f"Synced from MyVault successfully for project: {project_name}",
        "project": project_name,
    }


@router.get("/list-projects", response_model=ListProjectsResponse)
async def list_projects(x_admin_token: str = Header(...)):
    """List all projects with Google credentials cached locally."""
    verify_admin_token(x_admin_token)

    projects = google_creds_manager.list_projects()

    return ListProjectsResponse(projects=projects)


@router.post("/oauth2-start", response_model=OAuth2StartResponse)
async def oauth2_start(request: OAuth2StartRequest, x_admin_token: str = Header(...)):
    """
    Initiate OAuth2 flow for web application.
    Returns authorization URL and state for CSRF protection.
    """
    verify_admin_token(x_admin_token)

    try:
        auth_url, state = google_creds_manager.initiate_oauth2_flow(
            project=request.project, redirect_uri=request.redirect_uri
        )

        project_name = get_project_name(request.project)

        return OAuth2StartResponse(auth_url=auth_url, state=state, project=project_name)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to initiate OAuth2 flow: {str(e)}"
        ) from e


@router.post("/oauth2-callback", response_model=OAuth2CallbackResponse)
async def oauth2_callback(
    request: OAuth2CallbackRequest, x_admin_token: str = Header(...)
):
    """
    Handle OAuth2 callback with authorization code.
    Exchanges code for tokens, saves them encrypted, and uploads to MyVault.
    """
    verify_admin_token(x_admin_token)

    success = google_creds_manager.complete_oauth2_flow(
        state=request.state, code=request.code, project=request.project
    )

    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to complete OAuth2 flow. Check logs."
        )

    project_name = get_project_name(request.project)

    # Auto-save token to MyVault
    try:
        # Get the token that was just saved
        token_path = google_creds_manager.get_token_path(project_name)
        if token_path and secrets_manager.myvault_client:
            with open(token_path) as f:
                token_json = f.read()

            # Save to MyVault
            secrets_manager.myvault_client.update_secret(
                project=project_name, path="GOOGLE_TOKEN_JSON", value=token_json
            )
            logger.info(f"Token auto-saved to MyVault for project: {project_name}")
    except Exception as e:
        # Non-fatal: token is saved locally, MyVault save failed
        logger.warning(f"Failed to auto-save token to MyVault: {e}")

    return OAuth2CallbackResponse(
        success=True,
        message=f"OAuth2 flow completed successfully for project: {project_name}",
        project=project_name,
    )


@router.get("/token-data", response_model=TokenDataResponse)
async def get_token_data(
    project: Optional[str] = None, x_admin_token: str = Header(...)
):
    """
    Get token.json data for specified project.
    Returns decrypted token content for viewing/backup.
    """
    verify_admin_token(x_admin_token)

    project_name = get_project_name(project)

    try:
        token_path = google_creds_manager.get_token_path(project_name)

        if not token_path:
            return TokenDataResponse(
                exists=False,
                token_json=None,
                project=project_name,
                error_message=f"Token not found for project: {project_name}",
            )

        # Read decrypted token content
        with open(token_path) as f:
            token_json = f.read()

        return TokenDataResponse(
            exists=True, token_json=token_json, project=project_name
        )

    except Exception as e:
        return TokenDataResponse(
            exists=False,
            token_json=None,
            project=project_name,
            error_message=f"Failed to read token: {str(e)}",
        )


@router.post("/save-token")
async def save_token(request: SaveTokenRequest, x_admin_token: str = Header(...)):
    """
    Save token.json to local encrypted storage and optionally to MyVault.
    """
    verify_admin_token(x_admin_token)

    project_name = get_project_name(request.project)

    # Save to local encrypted storage
    success = google_creds_manager.save_token(request.token_json, project_name)

    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to save token locally. Check logs."
        )

    # Optionally save to MyVault
    if request.save_to_myvault and secrets_manager.myvault_client:
        try:
            # Save to MyVault for persistence
            secrets_manager.myvault_client.update_secret(
                project=project_name, path="GOOGLE_TOKEN_JSON", value=request.token_json
            )
        except Exception as e:
            # Non-fatal: local save succeeded, MyVault save failed
            return {
                "success": True,
                "message": f"Token saved locally for project: {project_name}",
                "myvault_saved": False,
                "myvault_error": str(e),
                "project": project_name,
            }

    return {
        "success": True,
        "message": f"Token saved successfully for project: {project_name}",
        "myvault_saved": request.save_to_myvault,
        "project": project_name,
    }
