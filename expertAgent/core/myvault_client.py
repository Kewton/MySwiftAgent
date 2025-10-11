"""MyVault API client for secret management."""

import logging
from typing import Dict

import httpx

logger = logging.getLogger(__name__)


class MyVaultError(Exception):
    """Base exception for MyVault client errors."""

    pass


class MyVaultClient:
    """Client for MyVault API operations."""

    def __init__(self, base_url: str, service_name: str, token: str):
        """Initialize MyVault client.

        Args:
            base_url: MyVault API base URL (e.g., http://localhost:8000)
            service_name: Service identifier for authentication
            token: Service authentication token
        """
        self.base_url = base_url.rstrip("/")
        self.headers = {
            "X-Service": service_name,
            "X-Token": token,
            "Content-Type": "application/json",
        }
        self.client = httpx.Client(
            base_url=self.base_url, headers=self.headers, timeout=10.0
        )

    def close(self):
        """Close HTTP client connection."""
        self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        """Context manager exit."""
        self.close()

    def get_default_project(self) -> str | None:
        """Get default project name.

        Returns:
            Default project name, or None if no default project exists

        Raises:
            MyVaultError: If API request fails
        """
        try:
            response = self.client.get("/api/projects")
            response.raise_for_status()

            projects = response.json()
            for project in projects:
                if project.get("is_default", False):
                    return str(project["name"])

            return None

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            logger.error(f"Failed to get default project: HTTP {status_code}")
            raise MyVaultError(f"Failed to get default project: {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error getting default project: {e}")
            raise MyVaultError(f"Unexpected error: {e}") from e

    def get_secrets(self, project: str) -> Dict[str, str]:
        """Get all secrets for a project.

        Args:
            project: Project name

        Returns:
            Dictionary mapping secret names to values

        Raises:
            MyVaultError: If API request fails or project not found
        """
        try:
            response = self.client.get(f"/api/secrets/{project}")
            response.raise_for_status()

            secrets_list = response.json()
            # Convert list of {path, value, ...} to dict {path: value}
            return {secret["path"]: secret["value"] for secret in secrets_list}

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(f"Project '{project}' not found in MyVault")
                raise MyVaultError(f"Project '{project}' not found") from e
            status_code = e.response.status_code
            logger.error(
                f"Failed to get secrets for project '{project}': HTTP {status_code}"
            )
            raise MyVaultError(f"Failed to get secrets for '{project}': {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error getting secrets: {e}")
            raise MyVaultError(f"Unexpected error: {e}") from e

    def get_secret(self, project: str, secret_name: str) -> str:
        """Get a specific secret value.

        Args:
            project: Project name
            secret_name: Secret name

        Returns:
            Secret value

        Raises:
            MyVaultError: If secret not found or API request fails
        """
        try:
            response = self.client.get(f"/api/secrets/{project}/{secret_name}")
            response.raise_for_status()

            secret_data = response.json()
            return str(secret_data["value"])

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                logger.warning(
                    f"Secret '{secret_name}' not found in project '{project}'"
                )
                raise MyVaultError(
                    f"Secret '{secret_name}' not found in project '{project}'"
                ) from e
            status_code = e.response.status_code
            logger.error(f"Failed to get secret '{secret_name}': HTTP {status_code}")
            msg = f"Failed to get secret '{secret_name}': {e}"
            raise MyVaultError(msg) from e
        except Exception as e:
            logger.error(f"Unexpected error getting secret: {e}")
            raise MyVaultError(f"Unexpected error: {e}") from e

    def update_secret(self, project: str, path: str, value: str) -> None:
        """Update or create a secret in MyVault.

        Args:
            project: Project name
            path: Secret path/name (e.g., "GOOGLE_TOKEN_JSON")
            value: Secret value

        Raises:
            MyVaultError: If API request fails
        """
        try:
            # Try to update existing secret first
            try:
                response = self.client.patch(
                    f"/api/secrets/{project}/{path}", json={"value": value}
                )
                response.raise_for_status()
                logger.info(f"Updated secret '{path}' in project '{project}'")
                return
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # Secret doesn't exist, create it
                    response = self.client.post(
                        "/api/secrets",
                        json={"project": project, "path": path, "value": value},
                    )
                    response.raise_for_status()
                    logger.info(f"Created secret '{path}' in project '{project}'")
                    return
                else:
                    raise

        except httpx.HTTPStatusError as e:
            status_code = e.response.status_code
            logger.error(
                f"Failed to update secret '{path}' in project '{project}': "
                f"HTTP {status_code}"
            )
            raise MyVaultError(f"Failed to update secret '{path}': {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error updating secret: {e}")
            raise MyVaultError(f"Unexpected error: {e}") from e

    def health_check(self) -> bool:
        """Check if MyVault service is healthy.

        Returns:
            True if service is healthy, False otherwise
        """
        try:
            response = self.client.get("/health")
            return response.status_code == 200
        except Exception:
            return False
