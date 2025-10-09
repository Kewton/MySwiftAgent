"""Google API services with project-specific encrypted credentials."""

import atexit
import logging
import os
from typing import Any, Optional

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from core.google_creds import SCOPES, get_project_name, google_creds_manager

logger = logging.getLogger(__name__)

# Temp file cleanup
_temp_files: list[str] = []


def _cleanup_temp_files():
    """Clean up temporary credential files on exit."""
    for path in _temp_files:
        try:
            if os.path.exists(path):
                os.remove(path)
                logger.debug(f"Cleaned up temp file: {path}")
        except Exception as e:
            logger.warning(f"Failed to clean up {path}: {e}")


atexit.register(_cleanup_temp_files)


def get_googleapis_service(
    _serviceName: str, project: Optional[str] = None
) -> Optional[Any]:
    """
    Get Google API service with project-specific encrypted credentials.

    Args:
        _serviceName: Service name (gmail, drive, sheets)
        project: Project name (uses default if None)

    Returns:
        Google API service object or None if authentication fails
    """
    project_name = get_project_name(project)
    logger.info(f"Project: {project_name} - Checking credentials...")

    try:
        # Get decrypted credentials paths from encrypted storage
        credentials_path = google_creds_manager.get_credentials_path(project_name)
        _temp_files.append(credentials_path)

        token_path = google_creds_manager.get_token_path(project_name)
        if token_path:
            _temp_files.append(token_path)
    except FileNotFoundError as e:
        logger.error(f"Credentials not found: {e}")
        logger.info(
            f"Please add GOOGLE_CREDENTIALS_JSON to MyVault project: {project_name}"
        )
        logger.info("Use commonUI → MyVault → Google Auth tab to upload credentials")
        return None
    except ValueError as e:
        logger.error(f"Decryption failed: {e}")
        logger.info("Check GOOGLE_CREDS_ENCRYPTION_KEY in MyVault")
        return None
    except Exception as e:
        logger.error(f"Failed to get credentials: {e}")
        return None

    creds: Optional[Credentials] = None

    # Load token if exists
    if token_path and os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            logger.info("Loaded existing token")
        except Exception as e:
            logger.warning(f"Failed to load token: {e}")
            creds = None

    # Check validity and refresh if needed
    if not creds or not creds.valid:
        logger.info("Credentials invalid or expired")

        if creds and creds.expired and creds.refresh_token:
            logger.info("Attempting to refresh token...")
            try:
                creds.refresh(Request())
                logger.info("Token refresh successful")

                # Save refreshed token
                token_json = creds.to_json()
                google_creds_manager.save_token(token_json, project_name)
                logger.info(f"Saved refreshed token (project: {project_name})")
                logger.info(
                    "Manual MyVault update recommended: commonUI → MyVault → Google Auth tab"
                )
            except RefreshError as e:
                logger.error(f"Token refresh failed: {e}")
                logger.info("Re-authentication required")
                creds = None
            except Exception as e:
                logger.error(f"Unexpected error during refresh: {e}")
                creds = None

        # New authentication flow
        if not creds:
            logger.info("Starting new authentication flow...")

            if not os.path.exists(credentials_path):
                logger.error("Credentials file not found")
                logger.info(
                    "Please upload credentials.json via commonUI → MyVault → Google Auth tab"
                )
                return None

            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_path, SCOPES
                )
                creds = flow.run_local_server(
                    port=0,
                    authorization_prompt_message="Open browser to authenticate: {url}",
                    success_message="Authentication complete. You can close this window.",
                    open_browser=True,
                )
                logger.info("New authentication successful")

                # Save new token
                token_json = creds.to_json()
                google_creds_manager.save_token(token_json, project_name)
                logger.info(f"Saved new token (project: {project_name})")
                logger.info(
                    "Manual MyVault update recommended: commonUI → MyVault → Google Auth tab"
                )
            except Exception as e:
                logger.error(f"Authentication flow failed: {e}")
                return None

    # Final validation
    if not creds or not creds.valid:
        logger.error("Failed to obtain valid credentials")
        return None

    # Build service
    try:
        logger.info(f"Building '{_serviceName}' service...")
        if _serviceName == "gmail":
            service = build("gmail", "v1", credentials=creds)
        elif _serviceName == "drive":
            service = build("drive", "v3", credentials=creds)
        elif _serviceName == "sheets":
            service = build("sheets", "v4", credentials=creds)
        else:
            logger.error(f"Unknown service name: {_serviceName}")
            return None

        logger.info("Service build successful")
        return service
    except Exception as e:
        logger.error(f"Service build failed: {e}")
        return None
