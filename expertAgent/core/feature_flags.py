"""Feature flags for ExpertAgent service.

This module provides centralized access to feature flags, making it easy
to control feature rollouts and A/B testing.

Issue #342: Feature flag for Job Generator V2 architecture migration.

Usage:
    from core.feature_flags import use_job_generator_v2

    if use_job_generator_v2():
        # Use V2 implementation
        ...
    else:
        # Use V1 implementation
        ...
"""

from core.config import settings


def use_job_generator_v2() -> bool:
    """Check if Job Generator V2 should be used.

    Returns:
        True if USE_JOB_GENERATOR_V2 environment variable is set to true,
        False otherwise (defaults to False for backward compatibility).

    Issue #342: The V2 architecture provides improved retry management
    to fix the infinite loop bug in the original implementation.
    """
    return settings.USE_JOB_GENERATOR_V2
