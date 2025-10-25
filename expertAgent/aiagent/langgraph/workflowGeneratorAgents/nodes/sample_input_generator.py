"""Sample input generator node for workflow testing.

This module provides the sample input generator node that creates sample
user_input data from Input Interface JSON Schema for workflow testing.
"""

import logging
from typing import Any

from ..state import WorkflowGeneratorState

logger = logging.getLogger(__name__)


def _generate_sample_from_schema(schema: dict[str, Any]) -> dict[str, Any] | str:
    """Generate sample data from JSON Schema.

    Args:
        schema: JSON Schema object

    Returns:
        Sample data matching the schema
    """
    schema_type = schema.get("type", "object")

    if schema_type == "object":
        properties = schema.get("properties", {})
        sample = {}

        for prop_name, prop_schema in properties.items():
            prop_type = prop_schema.get("type", "string")
            prop_default = prop_schema.get("default")
            prop_example = prop_schema.get("example")

            # Use example or default if available
            if prop_example is not None:
                sample[prop_name] = prop_example
            elif prop_default is not None:
                sample[prop_name] = prop_default
            # Generate sample based on type
            elif prop_type == "string":
                sample[prop_name] = f"sample_{prop_name}"
            elif prop_type == "integer":
                sample[prop_name] = 123
            elif prop_type == "number":
                sample[prop_name] = 123.45
            elif prop_type == "boolean":
                sample[prop_name] = True
            elif prop_type == "array":
                sample[prop_name] = ["sample_item"]
            elif prop_type == "object":
                sample[prop_name] = _generate_sample_from_schema(prop_schema)
            else:
                sample[prop_name] = None

        return sample

    elif schema_type == "string":
        return schema.get("example", "sample input text")

    elif schema_type == "integer":
        return schema.get("example", 123)

    elif schema_type == "number":
        return schema.get("example", 123.45)

    elif schema_type == "boolean":
        return schema.get("example", True)

    elif schema_type == "array":
        items_schema = schema.get("items", {})
        return [_generate_sample_from_schema(items_schema)]

    else:
        return {}


async def sample_input_generator_node(
    state: WorkflowGeneratorState,
) -> WorkflowGeneratorState:
    """Generate sample user_input from Input Interface JSON Schema.

    This node:
    1. Extracts Input Interface JSON Schema from task_data
    2. Generates sample data matching the schema
    3. Updates state with sample_input

    Args:
        state: Current workflow generator state

    Returns:
        Updated state with sample_input
    """
    logger.info("Starting sample input generator node")

    task_data = state["task_data"]
    input_interface = task_data.get("input_interface", {})
    input_schema = input_interface.get("schema", {})

    logger.debug(f"Input schema: {input_schema}")

    try:
        # Generate sample input from schema
        sample_input = _generate_sample_from_schema(input_schema)

        logger.info(f"Generated sample input: {sample_input}")
        logger.debug(f"Sample input type: {type(sample_input)}")

        # Update state
        return {
            **state,
            "sample_input": sample_input,
            "status": "sample_input_generated",
        }

    except Exception as e:
        logger.error(f"Error during sample input generation: {e}", exc_info=True)
        return {
            **state,
            "status": "failed",
            "error_message": f"Sample input generation failed: {str(e)}",
        }
