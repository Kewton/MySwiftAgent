"""Backward compatibility alias for adapter module.

This module provides V3 aliases for adapter components.
Re-exports all components from adapter.py with V3 naming.
"""

from .adapter import JobGeneratorAdapter

# Alias for V3 naming convention used in tests
JobGeneratorV3Adapter = JobGeneratorAdapter

__all__ = [
    "JobGeneratorAdapter",
    "JobGeneratorV3Adapter",  # Alias
]
