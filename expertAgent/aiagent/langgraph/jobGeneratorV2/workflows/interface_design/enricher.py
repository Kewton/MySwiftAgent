"""SchemaEnricherSubWorkflow for Job Generator V2.

This module implements the schema enrichment sub-workflow that:
1. Takes generated interfaces and optional OpenAPI specs
2. Enriches schemas with derived_fields for downstream tasks
3. Adds constraints from OpenAPI specs where available

Issue #342 Phase C.3: Migrate logic from interface_schema.py (DerivedFieldDefinition)

Key design decisions:
- derived_fields support ready-to-use data for downstream tasks
- OpenAPI spec enrichment adds validation constraints
- Graceful handling when specs are not available
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from aiagent.langgraph.jobGeneratorV2.types_old import (
    EnrichmentReport,
    InterfaceSchema,
    TaskDefinition,
)

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext

logger = logging.getLogger(__name__)


def _extract_openapi_constraints(
    api_endpoint: str,
    openapi_specs: dict[str, Any],
) -> dict[str, Any]:
    """Extract constraints from OpenAPI spec for an endpoint.

    Args:
        api_endpoint: The API endpoint to look up
        openapi_specs: Dict of OpenAPI specifications

    Returns:
        Dict of constraints (minLength, maxLength, pattern, etc.)
    """
    constraints: dict[str, Any] = {}

    if not openapi_specs or not api_endpoint:
        return constraints

    # Look for matching spec
    spec = openapi_specs.get(api_endpoint)
    if not spec:
        # Try partial match
        for endpoint, endpoint_spec in openapi_specs.items():
            if api_endpoint.startswith(endpoint) or endpoint.startswith(api_endpoint):
                spec = endpoint_spec
                break

    if not spec:
        return constraints

    # Extract parameter constraints
    if "parameters" in spec:
        for param_name, param_def in spec["parameters"].items():
            if isinstance(param_def, dict):
                param_constraints: dict[str, Any] = {}
                for key in [
                    "minLength",
                    "maxLength",
                    "minimum",
                    "maximum",
                    "pattern",
                    "default",
                ]:
                    if key in param_def:
                        param_constraints[key] = param_def[key]
                if param_constraints:
                    constraints[param_name] = param_constraints

    return constraints


def _apply_constraints_to_schema(
    schema: dict[str, Any],
    constraints: dict[str, Any],
) -> dict[str, Any]:
    """Apply OpenAPI constraints to a JSON Schema.

    Args:
        schema: Original JSON Schema
        constraints: Dict of constraints to apply

    Returns:
        Enriched JSON Schema
    """
    if not constraints or not isinstance(schema, dict):
        return schema

    enriched = schema.copy()
    properties = enriched.get("properties", {}).copy()

    for prop_name, prop_constraints in constraints.items():
        if prop_name in properties and isinstance(properties[prop_name], dict):
            # Merge constraints into property definition
            prop_def = properties[prop_name].copy()
            for key, value in prop_constraints.items():
                if key not in prop_def:  # Don't override existing values
                    prop_def[key] = value
            properties[prop_name] = prop_def

    enriched["properties"] = properties
    return enriched


class SchemaEnricherSubWorkflow:
    """Sub-workflow for enriching interfaces with additional data.

    This class handles:
    - Adding derived_fields to output schemas
    - Enriching schemas with OpenAPI constraints

    Example:
        enricher = SchemaEnricherSubWorkflow()
        enriched, report = await enricher.enrich(tasks, interfaces, specs, context)
    """

    async def enrich(
        self,
        tasks: list[TaskDefinition],
        interfaces: dict[str, InterfaceSchema],
        openapi_specs: dict[str, Any],
        context: "ExecutionContext",
    ) -> tuple[dict[str, InterfaceSchema], EnrichmentReport]:
        """Enrich interfaces with derived_fields and OpenAPI constraints.

        Args:
            tasks: List of task definitions
            interfaces: Dict mapping task_id to InterfaceSchema
            openapi_specs: Optional OpenAPI specifications
            context: Execution context

        Returns:
            Tuple of (enriched interfaces, enrichment report)
        """
        logger.info(
            "Starting schema enrichment for %d interfaces (job %s)",
            len(interfaces),
            context.job_id,
        )

        task_lookup = {t.id: t for t in tasks}
        enriched: dict[str, InterfaceSchema] = {}
        enriched_count = 0
        skipped_count = 0
        details: list[str] = []

        for task_id, interface in interfaces.items():
            task = task_lookup.get(task_id)

            # Apply OpenAPI constraints if available
            if task and openapi_specs:
                constraints = _extract_openapi_constraints(
                    task.recommended_api,
                    openapi_specs,
                )

                if constraints:
                    enriched_input = _apply_constraints_to_schema(
                        interface.input_schema,
                        constraints,
                    )
                    enriched_count += 1
                    details.append(
                        f"Enriched input schema for '{task.name}' ({task_id}) "
                        f"with {len(constraints)} constraints"
                    )
                else:
                    enriched_input = interface.input_schema
                    skipped_count += 1
            else:
                enriched_input = interface.input_schema
                skipped_count += 1

            # Create enriched interface
            enriched[task_id] = InterfaceSchema(
                task_id=task_id,
                input_schema=enriched_input,
                output_schema=interface.output_schema,
                description=interface.description,
            )

        logger.info(
            "Schema enrichment complete: enriched=%d, skipped=%d",
            enriched_count,
            skipped_count,
        )

        report = EnrichmentReport(
            enriched_count=enriched_count,
            skipped_count=skipped_count,
            details=details,
        )

        return enriched, report
