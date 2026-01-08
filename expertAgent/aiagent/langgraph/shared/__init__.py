"""Shared utilities for V1/V2 job generators.

This package provides common functions that can be shared between
V1 (jobTaskGeneratorAgents) and V2 (jobGeneratorV2) implementations.

Issue #342: Created for API information injection mechanism.
"""

from .capability_utils import (
    format_capabilities_for_prompt,
    load_capabilities_from_yaml,
)

__all__ = [
    "format_capabilities_for_prompt",
    "load_capabilities_from_yaml",
]
