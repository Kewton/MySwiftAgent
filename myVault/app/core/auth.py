"""Authentication and authorization middleware."""

import fnmatch

from fastapi import Header, HTTPException, status

from app.core.config import settings


class AuthService:
    """Service for handling authentication and authorization."""

    def verify_service_auth(
        self, x_service: str | None = None, x_token: str | None = None
    ) -> str:
        """
        Verify service authentication via X-Service and X-Token headers.

        Args:
            x_service: Service name from X-Service header
            x_token: Token from X-Token header

        Returns:
            Authenticated service name

        Raises:
            HTTPException: If authentication fails
        """
        if not x_service or not x_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing X-Service or X-Token header",
                headers={"WWW-Authenticate": "X-Service, X-Token"},
            )

        # Check if service is allowed
        allowed_services = settings.get_allowed_services()
        if x_service not in allowed_services:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Service '{x_service}' is not allowed",
            )

        # Verify token
        expected_token = settings.get_service_token(x_service)
        if not expected_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"No token configured for service '{x_service}'",
            )

        if x_token != expected_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "X-Service, X-Token"},
            )

        return x_service

    def check_rbac_permission(
        self, service: str, action: str, resource: str
    ) -> bool:
        """
        Check if service has permission to perform action on resource using RBAC.

        Args:
            service: Service name
            action: Action to perform (read, write, delete, list)
            resource: Resource identifier (format: secret:project:path)

        Returns:
            True if permission is granted, False otherwise

        Example:
            check_rbac_permission("newsbot-api", "read", "secret:newsbot:prod/api-key")
            check_rbac_permission("newsbot-worker", "write", "secret:common:shared-config")
        """
        # Get roles assigned to the service
        roles = settings.get_service_roles(service)
        if not roles:
            return False

        # Get all policies
        policies = settings.get_policies()
        if not policies:
            return False

        # Build a policy lookup by name
        policy_map = {p.get("name"): p for p in policies if isinstance(p, dict)}

        # Check each role's permissions
        for role_name in roles:
            policy = policy_map.get(role_name)
            if not policy:
                continue

            permissions = policy.get("permissions", [])
            for perm in permissions:
                if not isinstance(perm, dict):
                    continue

                # Check effect (only "allow" supported for now)
                effect = perm.get("effect", "").lower()
                if effect != "allow":
                    continue

                # Check if action is allowed
                allowed_actions = perm.get("actions", [])
                if action not in allowed_actions:
                    continue

                # Check if resource matches
                allowed_resources = perm.get("resources", [])
                for resource_pattern in allowed_resources:
                    if self._match_resource(resource_pattern, resource):
                        return True

        return False

    def _match_resource(self, pattern: str, resource: str) -> bool:
        """
        Match resource against pattern with wildcard support.

        Args:
            pattern: Resource pattern (e.g., "secret:newsbot*:prod/*")
            resource: Actual resource (e.g., "secret:newsbot_test:prod/api-key")

        Returns:
            True if resource matches pattern
        """
        # Use fnmatch for wildcard matching
        return fnmatch.fnmatch(resource, pattern)

    def check_prefix_access(self, service: str, secret_path: str) -> bool:
        """
        Check if service has access to the given secret path based on prefix rules.

        DEPRECATED: Use check_rbac_permission() instead.
        This method is kept for backward compatibility.

        Args:
            service: Service name
            secret_path: Full path to secret (project:scope/env/name format)

        Returns:
            True if access is allowed, False otherwise
        """
        allowed_prefixes = settings.get_service_prefixes(service)
        if not allowed_prefixes:
            return False

        # Check if any allowed prefix matches the secret path
        for prefix in allowed_prefixes:
            # Support wildcard matching with fnmatch
            if "*" in prefix:
                if fnmatch.fnmatch(secret_path, prefix + "*"):
                    return True
            # Simple prefix matching
            elif secret_path.startswith(prefix):
                return True

        return False


# Global auth service instance
auth_service = AuthService()


# FastAPI dependency for authentication
async def get_current_service(
    x_service: str | None = Header(None), x_token: str | None = Header(None)
) -> str:
    """FastAPI dependency to get authenticated service name."""
    return auth_service.verify_service_auth(x_service, x_token)
