"""Security constants for URL validation.

Issue #359: Unified localhost/internal host definitions.

This module defines shared constants for URL security validation,
ensuring consistent behavior across Pydantic schema validators and
custom TaskFlow validators.

Usage:
    from .security_constants import ALLOWED_LOCAL_HOSTS, is_local_host

    # In Pydantic validator
    if hostname in ALLOWED_LOCAL_HOSTS or is_local_host(hostname):
        return value  # Allow HTTP for local hosts

    # In TaskFlowSecurityValidator
    if is_local_host(hostname):
        return ValidationResult(is_valid=True)
"""

# Allowed localhost hostnames for HTTP connections
# These hosts are permitted to use HTTP instead of HTTPS
ALLOWED_LOCAL_HOSTS: frozenset[str] = frozenset([
    "localhost",       # Standard localhost
    "127.0.0.1",       # IPv4 loopback
    "0.0.0.0",         # All interfaces (Docker networking)  # noqa: S104
    "[::1]",           # IPv6 loopback
])

# Allowed domain suffixes for local development
# Hosts ending with these suffixes are treated as local
ALLOWED_LOCAL_SUFFIXES: tuple[str, ...] = (
    ".local",          # mDNS/Bonjour local network
    ".localhost",      # localhost subdomains
    ".internal",       # Internal network
)


def is_local_host(hostname: str) -> bool:
    """Check if hostname is a local/internal host.

    Args:
        hostname: The hostname to check (e.g., "localhost", "myapp.local")

    Returns:
        True if the hostname is considered local/internal

    Examples:
        >>> is_local_host("localhost")
        True
        >>> is_local_host("127.0.0.1")
        True
        >>> is_local_host("[::1]")
        True
        >>> is_local_host("myapp.local")
        True
        >>> is_local_host("api.example.com")
        False
    """
    if not hostname:
        return False

    hostname_lower = hostname.lower()

    # Check exact match
    if hostname_lower in ALLOWED_LOCAL_HOSTS:
        return True

    # Check suffix match
    for suffix in ALLOWED_LOCAL_SUFFIXES:
        if hostname_lower.endswith(suffix):
            return True

    return False


def is_local_url(url: str) -> bool:
    """Check if URL points to a local/internal host.

    This is a convenience function that extracts the hostname from a URL
    and checks if it's a local host.

    Args:
        url: The URL to check

    Returns:
        True if the URL points to a local/internal host

    Examples:
        >>> is_local_url("http://localhost:8004/api/v1")
        True
        >>> is_local_url("https://api.example.com/endpoint")
        False
    """
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        return is_local_host(hostname)
    except Exception:
        return False


# Export all
__all__ = [
    "ALLOWED_LOCAL_HOSTS",
    "ALLOWED_LOCAL_SUFFIXES",
    "is_local_host",
    "is_local_url",
]
