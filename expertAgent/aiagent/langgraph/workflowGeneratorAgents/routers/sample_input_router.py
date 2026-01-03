"""Sample input router for object array detection.

Issue #340: Router to handle object array detection in sample_input_generator.
Routes to test_data_regenerator if object arrays are detected, or workflow_tester otherwise.

MF-1: Includes infinite loop prevention by tracking regeneration count.
"""

import logging
from typing import Literal

from ..state import WorkflowGeneratorState

logger = logging.getLogger(__name__)


def sample_input_router(
    state: WorkflowGeneratorState,
) -> Literal["workflow_tester", "test_data_regenerator"]:
    """Route based on object array detection results.

    Issue #340: If object array issues are detected, route to
    test_data_regenerator for data regeneration.

    MF-1: Infinite loop prevention - if regeneration count exceeds max,
    continue to workflow_tester with warning log.

    Args:
        state: Current workflow generator state

    Returns:
        "test_data_regenerator" if errors detected and regeneration available
        "workflow_tester" otherwise
    """
    has_object_array_errors = state.get("has_object_array_errors", False)
    regen_count = state.get("object_array_regeneration_count", 0)
    max_regen = state.get("max_object_array_regeneration", 2)

    if has_object_array_errors:
        issues = state.get("object_array_issues", [])

        # MF-1: Check regeneration limit to prevent infinite loops
        if regen_count < max_regen:
            logger.info(
                f"sample_input_router: {len(issues)} object array issues detected, "
                f"regeneration attempt {regen_count + 1}/{max_regen}, "
                "routing to test_data_regenerator"
            )
            return "test_data_regenerator"
        else:
            # Max regeneration exceeded, continue with errors
            logger.warning(
                f"sample_input_router: {len(issues)} object array issues remain "
                f"after {max_regen} regeneration attempts. "
                "Continuing to workflow_tester (may fail at runtime)."
            )
            return "workflow_tester"

    logger.info(
        "sample_input_router: no object array issues, continuing to workflow_tester"
    )
    return "workflow_tester"
