"""Schema enrichment node for OpenAPI-based interface validation.

This module enriches interface definitions with actual API schemas from OpenAPI
specifications, ensuring workflow generation uses correct field names and types.

Key features:
- Fetches real API schemas from expertAgent OpenAPI spec
- Validates interface field names against actual API definitions
- Enriches interface definitions with accurate schema information
- Provides schema mismatch warnings for debugging

Usage:
    This node runs after interface_definition_node in the job generator workflow.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional

from core.openapi_schema_collector import (
    EndpointSchema,
    FieldSchema,
    OpenAPISchemaCollector,
)

from ..state import JobTaskGeneratorState

logger = logging.getLogger(__name__)

# expertAgent API base URL
EXPERTAGENT_BASE_URL = os.getenv(
    "EXPERTAGENT_BASE_URL",
    "http://localhost:8104",
)


def _extract_api_endpoint(task_description: str) -> Optional[tuple[str, str]]:
    """Extract API endpoint from task description.

    Args:
        task_description: Task description text

    Returns:
        Tuple of (method, path) if found, None otherwise

    Examples:
        >>> _extract_api_endpoint("Call Gmail search API at /v1/utility/gmail/search")
        ('POST', '/v1/utility/gmail/search')
        >>> _extract_api_endpoint("expertAgent の gmail/search APIを使用する")
        ('POST', '/v1/utility/gmail/search')
    """
    # Common patterns for API endpoint references
    patterns = [
        r"(GET|POST|PUT|PATCH|DELETE)\s+(/v1/[^\s]+)",  # "POST /v1/utility/gmail/search"
        r"API[:\s]+(/v1/[^\s]+)",  # "API: /v1/utility/gmail/search"
        r"endpoint[:\s]+(/v1/[^\s]+)",  # "endpoint: /v1/utility/gmail/search"
        r"(/v1/[a-z_/]+)",  # Direct path reference: "/v1/utility/gmail/search"
    ]

    for pattern in patterns:
        match = re.search(pattern, task_description, re.IGNORECASE)
        if match:
            if match.lastindex == 2:  # Method + path pattern
                return (match.group(1).upper(), match.group(2))
            else:  # Path only pattern - assume POST for utility APIs
                return ("POST", match.group(1))

    # Fallback: Map partial API names to full paths
    # Common expertAgent API shortcuts
    api_shortcuts = {
        "gmail/search": "/v1/utility/gmail/search",
        "gmail/send": "/v1/utility/gmail/send",
        "google_search": "/v1/utility/google_search",
        "drive/upload": "/v1/utility/drive/upload",
        "text_to_speech": "/v1/utility/text_to_speech",
        "text_to_speech_drive": "/v1/utility/text_to_speech_drive",
        "jsonoutput": "/v1/aiagent/utility/jsonoutput",
        "mylllm": "/v1/mylllm",
    }

    # Try to match partial API names
    description_lower = task_description.lower()
    for shortcut, full_path in api_shortcuts.items():
        if shortcut in description_lower:
            logger.debug(
                "Matched partial API name '%s' to full path '%s'",
                shortcut,
                full_path,
            )
            return ("POST", full_path)

    return None


def _compare_schemas(
    interface_fields: Dict[str, Any],
    api_fields: List[FieldSchema],
    schema_type: str = "input",
) -> Dict[str, Any]:
    """Compare interface schema with actual API schema.

    Args:
        interface_fields: Interface schema properties from JSON Schema
        api_fields: Actual API fields from OpenAPI spec
        schema_type: "input" or "output" for logging

    Returns:
        Dictionary with comparison results and enrichment suggestions
    """
    api_field_map = {f.name: f for f in api_fields}
    interface_field_names = set(interface_fields.keys())
    api_field_names = set(api_field_map.keys())

    # Find mismatches
    missing_in_api = interface_field_names - api_field_names
    missing_in_interface = api_field_names - interface_field_names

    # Required fields in API that are missing in interface
    required_api_fields = {f.name for f in api_fields if f.required}
    missing_required = required_api_fields - interface_field_names

    return {
        "has_mismatch": len(missing_in_api) > 0 or len(missing_required) > 0,
        "missing_in_api": list(missing_in_api),
        "missing_in_interface": list(missing_in_interface),
        "missing_required": list(missing_required),
        "api_field_map": api_field_map,
    }


def _enrich_schema_with_openapi(
    interface_schema: Dict[str, Any],
    api_schema: EndpointSchema,
    schema_type: str = "input",
) -> Dict[str, Any]:
    """Enrich interface schema with OpenAPI field definitions.

    Args:
        interface_schema: JSON Schema from interface definition
        api_schema: OpenAPI endpoint schema
        schema_type: "input" or "output"

    Returns:
        Enriched JSON Schema with correct field names and types
    """
    api_fields = (
        api_schema.request_fields
        if schema_type == "input"
        else api_schema.response_fields
    )

    if not api_fields:
        logger.warning(
            "No %s fields found in API schema for %s %s",
            schema_type,
            api_schema.method,
            api_schema.path,
        )
        return interface_schema

    properties = interface_schema.get("properties", {})
    comparison = _compare_schemas(properties, api_fields, schema_type)

    if comparison["has_mismatch"]:
        logger.warning(
            "Schema mismatch detected in %s schema:",
            schema_type,
        )
        if comparison["missing_in_api"]:
            logger.warning(
                "  Fields in interface but not in API: %s",
                comparison["missing_in_api"],
            )
        if comparison["missing_required"]:
            logger.warning(
                "  Required API fields missing in interface: %s",
                comparison["missing_required"],
            )

    # Enrich interface schema with API field definitions
    enriched_properties = {}
    api_field_map = comparison["api_field_map"]

    # Add all API fields with accurate definitions
    for field_name, api_field in api_field_map.items():
        enriched_properties[field_name] = {
            "type": api_field.type,
            "description": api_field.description or f"{field_name} field",
        }

        # Add constraints from API schema
        if api_field.default is not None:
            enriched_properties[field_name]["default"] = api_field.default
        if api_field.pattern:
            enriched_properties[field_name]["pattern"] = api_field.pattern
        if api_field.minimum is not None:
            enriched_properties[field_name]["minimum"] = api_field.minimum
        if api_field.maximum is not None:
            enriched_properties[field_name]["maximum"] = api_field.maximum
        if api_field.enum:
            enriched_properties[field_name]["enum"] = api_field.enum

    # Build required fields list
    required_fields = [f.name for f in api_fields if f.required]

    enriched_schema = {
        "type": "object",
        "properties": enriched_properties,
        "required": required_fields,
        "additionalProperties": False,
    }

    logger.info(
        "Enriched %s schema with %d API fields (required: %d)",
        schema_type,
        len(enriched_properties),
        len(required_fields),
    )

    return enriched_schema


async def schema_enrichment_node(
    state: JobTaskGeneratorState,
) -> JobTaskGeneratorState:
    """Enrich interface definitions with OpenAPI schemas.

    This node:
    1. Fetches OpenAPI specification from expertAgent
    2. Extracts API endpoints from task descriptions
    3. Enriches interface definitions with accurate API schemas
    4. Warns about schema mismatches for debugging

    Args:
        state: Current job task generator state

    Returns:
        Updated state with enriched interface definitions
    """
    logger.info("Starting schema enrichment node")

    interface_definitions = state.get("interface_definitions", {})
    task_breakdown = state.get("task_breakdown", [])

    if not interface_definitions or not task_breakdown:
        logger.info("No interfaces to enrich, skipping")
        return state

    # Initialize OpenAPI collector
    collector = OpenAPISchemaCollector(f"{EXPERTAGENT_BASE_URL}/aiagent-api")

    enriched_count = 0
    warning_count = 0

    for task_id, interface_def in interface_definitions.items():
        # Find corresponding task
        task = next((t for t in task_breakdown if t.get("task_id") == task_id), None)
        if not task:
            continue

        task_description = task.get("description", "")

        # Extract API endpoint from task description
        endpoint_info = _extract_api_endpoint(task_description)
        if not endpoint_info:
            logger.debug(
                "No API endpoint found in task %s description, skipping enrichment",
                task_id,
            )
            continue

        method, path = endpoint_info
        logger.info(
            "Enriching interface for task %s using API: %s %s",
            task_id,
            method,
            path,
        )

        try:
            # Fetch API schema from OpenAPI spec
            api_schema = await collector.get_endpoint_schema(method, path)

            if not api_schema:
                logger.warning(
                    "API schema not found for %s %s, skipping enrichment",
                    method,
                    path,
                )
                warning_count += 1
                continue

            # Enrich input schema
            original_input = interface_def.get("input_schema", {})
            enriched_input = _enrich_schema_with_openapi(
                original_input, api_schema, "input"
            )

            # Enrich output schema
            original_output = interface_def.get("output_schema", {})
            enriched_output = _enrich_schema_with_openapi(
                original_output, api_schema, "output"
            )

            # Update interface definition with enriched schemas
            interface_def["input_schema"] = enriched_input
            interface_def["output_schema"] = enriched_output
            interface_def["api_endpoint"] = f"{method} {path}"
            interface_def["schema_enriched"] = True

            enriched_count += 1

        except Exception as e:
            logger.error(
                "Failed to enrich schema for task %s: %s",
                task_id,
                str(e),
                exc_info=True,
            )
            warning_count += 1

    logger.info(
        "Schema enrichment completed: %d enriched, %d warnings",
        enriched_count,
        warning_count,
    )

    return {
        **state,
        "interface_definitions": interface_definitions,
        "schema_enrichment_stats": {
            "enriched_count": enriched_count,
            "warning_count": warning_count,
        },
    }
