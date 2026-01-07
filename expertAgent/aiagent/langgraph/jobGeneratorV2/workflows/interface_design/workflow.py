"""InterfaceDesignWorkflow for Job Generator V2.

This module implements the main InterfaceDesignWorkflow that:
1. Orchestrates sub-workflows (schema_generator, compatibility, enricher)
2. Implements WorkflowProtocol for orchestrator integration
3. Returns InterfaceDesignOutput with appropriate PhaseStatus

Issue #342 Phase C.4: Main workflow orchestrating sub-workflows

Key design decisions:
- Implements WorkflowProtocol for use with JobGenerationOrchestrator
- Orchestrates: schema_generator -> compatibility -> enricher
- Returns NEEDS_RETRY when compatibility issues found
- Uses ExecutionContext's phase-specific retry state (bug fix)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from aiagent.langgraph.jobGeneratorV2.protocols import (
    ErrorType,
    RetryPolicy,
    WorkflowError,
)
from aiagent.langgraph.jobGeneratorV2.types import (
    InterfaceDesignInput,
    InterfaceDesignOutput,
    Phase,
    PhaseStatus,
)

from .compatibility import CompatibilityCheckerSubWorkflow
from .enricher import SchemaEnricherSubWorkflow
from .schema_generator import SchemaGeneratorSubWorkflow

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext

logger = logging.getLogger(__name__)


class InterfaceDesignWorkflow:
    """Main workflow for interface design phase.

    This workflow orchestrates the interface design process:
    1. Generate JSON Schema for each task's I/O
    2. Check compatibility between dependent tasks
    3. Enrich schemas with derived_fields and OpenAPI constraints
    4. Return appropriate output based on results

    Implements WorkflowProtocol for use with JobGenerationOrchestrator.

    Example:
        workflow = InterfaceDesignWorkflow()
        output = await workflow.execute(input_data, context)
    """

    def __init__(self) -> None:
        """Initialize InterfaceDesignWorkflow."""
        self._retry_policy: RetryPolicy = RetryPolicy(
            max_retries=3,
            backoff_factor=1.5,
            retry_on=[
                ErrorType.TRANSIENT,
                ErrorType.VALIDATION,
                ErrorType.COMPATIBILITY,
            ],
        )

    def get_retry_policy(self) -> RetryPolicy:
        """Get the retry policy for this workflow.

        Returns:
            RetryPolicy instance
        """
        return self._retry_policy

    async def execute(
        self,
        input_data: InterfaceDesignInput,
        context: "ExecutionContext",
    ) -> InterfaceDesignOutput:
        """Execute the interface design workflow.

        Args:
            input_data: InterfaceDesignInput with tasks
            context: Execution context

        Returns:
            InterfaceDesignOutput with results

        Raises:
            WorkflowError: If a recoverable error occurs
        """
        logger.info(
            "Starting InterfaceDesignWorkflow for job %s",
            context.job_id,
        )

        tasks = input_data.tasks
        openapi_specs = input_data.openapi_specs

        if not tasks:
            logger.warning("No tasks provided for interface design")
            return InterfaceDesignOutput(
                status=PhaseStatus.FAILED,
                interfaces={},
                compatibility_report=None,
                enrichment_report=None,
            )

        # Step 1: Generate JSON Schema for each task
        schema_generator = SchemaGeneratorSubWorkflow()
        try:
            interfaces = await schema_generator.generate(tasks, context)
        except WorkflowError:
            raise
        except Exception as e:
            logger.error("Unexpected error in schema generation: %s", e, exc_info=True)
            raise WorkflowError(
                f"Schema generation failed: {e}",
                ErrorType.TRANSIENT,
                Phase.INTERFACE_DESIGN,
            ) from e

        if not interfaces:
            logger.error("Schema generator returned no interfaces")
            raise WorkflowError(
                "Schema generation produced no interfaces",
                ErrorType.VALIDATION,
                Phase.INTERFACE_DESIGN,
            )

        logger.info("Generated %d interface schemas", len(interfaces))

        # Step 2: Check compatibility
        compatibility_checker = CompatibilityCheckerSubWorkflow()
        compatibility_report = await compatibility_checker.check(
            tasks, interfaces, context
        )

        logger.info(
            "Compatibility check: is_compatible=%s, issues=%d",
            compatibility_report.is_compatible,
            len(compatibility_report.issues),
        )

        # Step 3: Enrich schemas (even if incompatible, we return what we have)
        enricher = SchemaEnricherSubWorkflow()
        enriched_interfaces, enrichment_report = await enricher.enrich(
            tasks, interfaces, openapi_specs, context
        )

        logger.info(
            "Schema enrichment: enriched=%d, skipped=%d",
            enrichment_report.enriched_count,
            enrichment_report.skipped_count,
        )

        # Step 4: Determine status based on compatibility
        if compatibility_report.is_compatible:
            status = PhaseStatus.SUCCESS
            logger.info("InterfaceDesignWorkflow completed successfully")
        else:
            status = PhaseStatus.NEEDS_RETRY
            logger.warning(
                "InterfaceDesignWorkflow needs retry due to compatibility issues: %s",
                compatibility_report.issues,
            )

        return InterfaceDesignOutput(
            status=status,
            interfaces=enriched_interfaces,
            compatibility_report=compatibility_report,
            enrichment_report=enrichment_report,
        )
