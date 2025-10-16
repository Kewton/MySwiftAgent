"""Test mode handler for expertAgent endpoints.

This module provides a common handler for test mode functionality,
allowing endpoints to return mock responses without actual processing.
"""

import logging

from app.schemas.standardAiAgent import ExpertAiAgentResponse

logger = logging.getLogger(__name__)


def handle_test_mode(
    test_mode: bool,
    test_response: dict | str | None,
    endpoint_name: str,
) -> dict | ExpertAiAgentResponse | None:
    """Handle test mode request for any endpoint.

    Args:
        test_mode: Whether test mode is enabled
        test_response: The mock response to return (dict, str, or None)
        endpoint_name: Name of the endpoint (for logging and response type)

    Returns:
        - None if test_mode is False (normal processing should continue)
        - dict if test_response is a dict (returned as-is for custom field access)
        - ExpertAiAgentResponse if test_response is a string or None

    Examples:
        >>> # In your endpoint:
        >>> result = handle_test_mode(request.test_mode, request.test_response, "mylllm")
        >>> if result is not None:
        >>>     return result
        >>> # Continue with normal processing...
    """
    if not test_mode:
        return None

    logger.info(f"Test mode enabled for {endpoint_name} endpoint")

    if test_response is not None:
        logger.debug(f"Returning user-specified test_response: {test_response}")
        # If test_response is a dict, return it directly
        # This allows GraphAI workflows to access custom fields via :node.field
        if isinstance(test_response, dict):
            return test_response

        # If test_response is a string, wrap it in ExpertAiAgentResponse
        return ExpertAiAgentResponse(
            result=test_response,
            text=test_response,
            type=f"{endpoint_name}_test",
        )
    else:
        logger.debug("No test_response provided, returning default")
        return ExpertAiAgentResponse(
            result="Test mode: no test_response provided",
            text="Test mode: no test_response provided",
            type=f"{endpoint_name}_test",
        )
