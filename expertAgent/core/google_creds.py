"""Google credentials management with project support and encryption."""

import json
import logging
import tempfile
from pathlib import Path
from typing import Optional, Tuple

from cryptography.fernet import Fernet, InvalidToken
from google.oauth2.credentials import Credentials

from core.config import settings
from core.secrets import secrets_manager

logger = logging.getLogger(__name__)

# Credentials directory
CREDS_DIR = Path(__file__).parent.parent / ".google_credentials"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]


def get_project_name(project: Optional[str] = None) -> str:
    """Get project name with fallback to MyVault default project.

    Priority:
    1. Explicit project parameter
    2. Default project from MyVault API (is_default flag)
    3. Environment variable GOOGLE_APIS_DEFAULT_PROJECT (MCP context override)
    4. MYVAULT_DEFAULT_PROJECT setting (override)
    5. "default" (fallback)

    Note: This priority order matches _resolve_default_project() in secrets.py
    """
    import os

    logger.debug(f"[get_project_name] Called with project={project}")

    if project:
        logger.debug(f"[get_project_name] Using explicit project: {project}")
        return project

    # Try MyVault API first (standard behavior)
    logger.debug("[get_project_name] Checking MyVault API for default project...")
    logger.debug(
        f"[get_project_name] secrets_manager.myvault_client exists: {secrets_manager.myvault_client is not None}"
    )
    try:
        if secrets_manager.myvault_client:
            default_project = secrets_manager.myvault_client.get_default_project()
            if default_project:
                logger.debug(
                    f"[get_project_name] Using default project from MyVault API: {default_project}"
                )
                return default_project
    except Exception as e:
        logger.debug(
            f"[get_project_name] Failed to get default project from MyVault API: {e}"
        )
        pass  # Fall through to other options

    # Try environment variable (for MCP context override)
    env_project = os.getenv("GOOGLE_APIS_DEFAULT_PROJECT")
    logger.debug(f"[get_project_name] GOOGLE_APIS_DEFAULT_PROJECT env: {env_project}")
    if env_project:
        logger.debug(
            f"[get_project_name] Using default project from GOOGLE_APIS_DEFAULT_PROJECT env: {env_project}"
        )
        return env_project

    # Try MYVAULT_DEFAULT_PROJECT override
    logger.debug(
        f"[get_project_name] MYVAULT_DEFAULT_PROJECT setting: {settings.MYVAULT_DEFAULT_PROJECT}"
    )
    if settings.MYVAULT_DEFAULT_PROJECT:
        logger.debug(
            f"[get_project_name] Using default project from MYVAULT_DEFAULT_PROJECT setting: {settings.MYVAULT_DEFAULT_PROJECT}"
        )
        return settings.MYVAULT_DEFAULT_PROJECT

    logger.debug("[get_project_name] Using fallback: 'default'")
    return "default"


class GoogleCredsManager:
    """Manage encrypted Google credentials with project support."""

    def __init__(self):
        """Initialize credentials manager."""
        CREDS_DIR.mkdir(exist_ok=True, mode=0o700)
        self._fernet_cache: dict[str, Fernet] = {}
        self._current_project: Optional[str] = None

    def _get_project_dir(self, project: Optional[str] = None) -> Path:
        """Get project-specific credentials directory."""
        project_name = get_project_name(project)
        project_dir = CREDS_DIR / project_name
        project_dir.mkdir(exist_ok=True, mode=0o700)
        return project_dir

    def _get_credentials_file(self, project: Optional[str] = None) -> Path:
        """Get credentials file path for project."""
        return self._get_project_dir(project) / "credentials.json.enc"

    def _get_token_file(self, project: Optional[str] = None) -> Path:
        """Get token file path for project."""
        return self._get_project_dir(project) / "token.json.enc"

    def _get_encryption_key(self, project: Optional[str] = None) -> bytes:
        """
        Get encryption key from MyVault for specific project.
        """
        try:
            project_name = get_project_name(project)
            # Get project-specific encryption key from MyVault
            key_str = secrets_manager.get_secret(
                "GOOGLE_CREDS_ENCRYPTION_KEY", project=project_name
            )
            logger.info(
                f"✓ Encryption key loaded from MyVault (project: {project_name})"
            )
            return key_str.encode()
        except ValueError as e:
            project_name = get_project_name(project)
            logger.error(
                f"❌ Encryption key not found in MyVault (project: {project_name})"
            )
            raise ValueError(
                f"GOOGLE_CREDS_ENCRYPTION_KEY not found in MyVault for project: {project_name}. "
                "Please set up encryption key first."
            ) from e

    def _get_fernet(self, project: Optional[str] = None) -> Fernet:
        """Get Fernet cipher instance for specific project."""
        project_name = get_project_name(project)
        if project_name not in self._fernet_cache:
            key = self._get_encryption_key(project_name)
            self._fernet_cache[project_name] = Fernet(key)
        return self._fernet_cache[project_name]

    def _encrypt_file(
        self, data: str, file_path: Path, project: Optional[str] = None
    ) -> None:
        """Encrypt and write data to file."""
        fernet = self._get_fernet(project)
        encrypted = fernet.encrypt(data.encode())
        file_path.write_bytes(encrypted)
        file_path.chmod(0o600)
        logger.info(f"✓ Encrypted file written: {file_path.name}")

    def _decrypt_file(self, file_path: Path, project: Optional[str] = None) -> str:
        """Read and decrypt file."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        fernet = self._get_fernet(project)
        encrypted = file_path.read_bytes()
        try:
            decrypted = fernet.decrypt(encrypted)
            return decrypted.decode()
        except InvalidToken as e:
            logger.error(f"❌ Failed to decrypt {file_path.name}")
            raise ValueError("Decryption failed - encryption key may be wrong") from e

    def sync_from_myvault(self, project: Optional[str] = None) -> bool:
        """
        Sync credentials from MyVault to local encrypted files.
        """
        try:
            project_name = get_project_name(project)
            logger.info(f"🔄 Syncing credentials for project: {project_name}")
            logger.debug(
                f"[sync_from_myvault] secrets_manager.myvault_enabled: {secrets_manager.myvault_enabled}"
            )
            logger.debug(
                f"[sync_from_myvault] secrets_manager.myvault_client: {secrets_manager.myvault_client}"
            )

            # Get credentials from MyVault
            logger.debug(
                "[sync_from_myvault] Attempting to get GOOGLE_CREDENTIALS_JSON from MyVault..."
            )
            creds_json = secrets_manager.get_secret(
                "GOOGLE_CREDENTIALS_JSON", project=project_name
            )
            logger.debug(
                f"[sync_from_myvault] Successfully retrieved GOOGLE_CREDENTIALS_JSON (length: {len(creds_json)})"
            )

            # Validate JSON
            json.loads(creds_json)

            # Encrypt and save
            creds_file = self._get_credentials_file(project_name)
            self._encrypt_file(creds_json, creds_file, project_name)
            logger.info(f"✓ Credentials synced for project: {project_name}")

            # Try to sync token (optional)
            try:
                token_json = secrets_manager.get_secret(
                    "GOOGLE_TOKEN_JSON", project=project_name
                )
                json.loads(token_json)
                token_file = self._get_token_file(project_name)
                self._encrypt_file(token_json, token_file, project_name)
                logger.info(f"✓ Token synced for project: {project_name}")
            except ValueError:
                logger.info(f"ℹ Token not found for project: {project_name} (OK)")

            self._current_project = project_name
            return True

        except Exception as e:
            logger.error(f"❌ Failed to sync from MyVault: {e}")
            return False

    def get_credentials_path(self, project: Optional[str] = None) -> str:
        """
        Get credentials file path, syncing from MyVault if needed.
        Returns decrypted file path in temp location.
        """
        project_name = get_project_name(project)
        creds_file = self._get_credentials_file(project_name)

        # Check if encrypted file exists
        if not creds_file.exists():
            logger.warning(f"⚠ Credentials not found for project: {project_name}")
            logger.info("🔄 Syncing from MyVault...")
            if not self.sync_from_myvault(project_name):
                raise FileNotFoundError(
                    f"Credentials not found for project: {project_name}. "
                    "Please add GOOGLE_CREDENTIALS_JSON to MyVault."
                )

        # Decrypt to temp file
        creds_json = self._decrypt_file(creds_file, project_name)

        temp_file = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".json",
            delete=False,
            prefix=f"google_creds_{project_name}_",
        )
        temp_file.write(creds_json)
        temp_file.close()
        Path(temp_file.name).chmod(0o600)

        logger.info(f"✓ Credentials ready for project: {project_name}")
        return temp_file.name

    def get_token_path(self, project: Optional[str] = None) -> Optional[str]:
        """Get token file path, returns None if not exists."""
        project_name = get_project_name(project)
        token_file = self._get_token_file(project_name)

        if not token_file.exists():
            logger.info(f"ℹ Token not found for project: {project_name}")
            return None

        try:
            token_json = self._decrypt_file(token_file, project_name)

            temp_file = tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".json",
                delete=False,
                prefix=f"google_token_{project_name}_",
            )
            temp_file.write(token_json)
            temp_file.close()
            Path(temp_file.name).chmod(0o600)

            return temp_file.name
        except Exception as e:
            logger.error(f"❌ Failed to decrypt token: {e}")
            return None

    def save_token(self, token_json_str: str, project: Optional[str] = None) -> bool:
        """
        Save token to encrypted file and notify for MyVault update.
        """
        try:
            project_name = get_project_name(project)

            # Validate JSON
            json.loads(token_json_str)

            # Encrypt and save locally
            token_file = self._get_token_file(project_name)
            self._encrypt_file(token_json_str, token_file, project_name)
            logger.info(f"✓ Token saved for project: {project_name}")

            # NOTE: Manual MyVault update required via commonUI
            logger.warning(
                f"⚠ Manual MyVault update required for project: {project_name}"
            )
            logger.info(
                "Update GOOGLE_TOKEN_JSON in MyVault to persist across restarts"
            )

            return True
        except Exception as e:
            logger.error(f"❌ Failed to save token: {e}")
            return False

    def check_token_validity(
        self, project: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """Check if token exists and is valid for project."""
        project_name = get_project_name(project)
        token_file = self._get_token_file(project_name)

        if not token_file.exists():
            return False, f"Token not found for project: {project_name}"

        try:
            token_json = self._decrypt_file(token_file, project_name)
            token_dict = json.loads(token_json)

            # Create Credentials object to check validity
            creds = Credentials.from_authorized_user_info(token_dict, SCOPES)

            if not creds.valid:
                if creds.expired and creds.refresh_token:
                    return False, "Token expired (refresh available)"
                else:
                    return False, "Token invalid (no refresh token)"

            return True, None
        except Exception as e:
            return False, f"Token check failed: {str(e)}"

    def list_projects(self) -> list[str]:
        """List all projects with Google credentials."""
        if not CREDS_DIR.exists():
            return []

        projects = []
        for project_dir in CREDS_DIR.iterdir():
            if project_dir.is_dir():
                creds_file = project_dir / "credentials.json.enc"
                if creds_file.exists():
                    projects.append(project_dir.name)

        return sorted(projects)

    def switch_project(self, project: str) -> bool:
        """
        Switch to different project.
        Syncs credentials from MyVault if not cached.
        """
        try:
            logger.info(f"🔄 Switching to project: {project}")

            creds_file = self._get_credentials_file(project)
            if not creds_file.exists():
                logger.info("Credentials not cached, syncing from MyVault...")
                if not self.sync_from_myvault(project):
                    return False

            self._current_project = project
            logger.info(f"✓ Switched to project: {project}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to switch project: {e}")
            return False

    def initiate_oauth2_flow(
        self, project: Optional[str] = None, redirect_uri: str = "http://localhost:8501"
    ) -> Tuple[str, str]:
        """
        Initiate OAuth2 flow for web application.
        Returns (auth_url, state).

        Args:
            project: Project name
            redirect_uri: OAuth2 redirect URI (default: http://localhost:8501)

        Returns:
            Tuple of (authorization_url, state)
        """
        import secrets as py_secrets

        from google_auth_oauthlib.flow import Flow  # type: ignore[import-untyped]

        project_name = get_project_name(project)

        try:
            # Get decrypted credentials
            creds_path = self.get_credentials_path(project_name)

            # Create flow with web application configuration
            flow = Flow.from_client_secrets_file(
                creds_path, scopes=SCOPES, redirect_uri=redirect_uri
            )

            # Generate state for CSRF protection
            state = py_secrets.token_urlsafe(32)

            # Get authorization URL
            auth_url, _ = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                state=state,
                prompt="consent",  # Force consent to get refresh_token
            )

            # Store flow in memory (temporary)
            # In production, consider using Redis or similar
            if not hasattr(self, "_oauth_flows"):
                self._oauth_flows = {}
            self._oauth_flows[state] = {
                "flow": flow,
                "project": project_name,
                "redirect_uri": redirect_uri,
            }

            logger.info(
                f"✓ OAuth2 flow initiated for project: {project_name}, redirect_uri: {redirect_uri}"
            )
            return auth_url, state

        except Exception as e:
            logger.error(f"❌ Failed to initiate OAuth2 flow: {e}")
            raise ValueError(f"Failed to initiate OAuth2 flow: {e}") from e

    def complete_oauth2_flow(
        self, state: str, code: str, project: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Complete OAuth2 flow with authorization code.

        Args:
            state: State parameter from OAuth2 flow
            code: Authorization code from Google
            project: Project name (optional, will use stored value from state)

        Returns:
            Tuple of (success, project_name)
        """
        try:
            if not hasattr(self, "_oauth_flows") or state not in self._oauth_flows:
                raise ValueError("Invalid or expired OAuth2 state")

            flow_data = self._oauth_flows[state]
            flow = flow_data["flow"]
            project_name = project or flow_data["project"]

            # Exchange authorization code for credentials
            flow.fetch_token(code=code)
            creds = flow.credentials

            # Save token
            token_json = creds.to_json()
            success = self.save_token(token_json, project_name)

            # Clean up
            del self._oauth_flows[state]

            if success:
                logger.info(f"✓ OAuth2 flow completed for project: {project_name}")
                return True, project_name
            else:
                logger.error(f"❌ Failed to save token for project: {project_name}")
                return False, project_name

        except Exception as e:
            logger.error(f"❌ Failed to complete OAuth2 flow: {e}")
            return False, ""


# Global instance
google_creds_manager = GoogleCredsManager()
