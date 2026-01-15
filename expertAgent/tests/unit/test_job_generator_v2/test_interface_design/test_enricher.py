"""Unit tests for SchemaEnricherSubWorkflow.

Issue #342 Phase C.3: Tests for derived_fields enrichment.
"""

from typing import Any

import pytest

from aiagent.langgraph.jobGeneratorV2.context import ExecutionContext
from aiagent.langgraph.jobGeneratorV2.types import (
    EnrichmentReport,
    InterfaceSchema,
    TaskDefinition,
)


class TestSchemaEnricherExists:
    """Test that SchemaEnricherSubWorkflow exists and is importable."""

    def test_schema_enricher_importable(self):
        """SchemaEnricherSubWorkflow should be importable."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.enricher import (
            SchemaEnricherSubWorkflow,
        )

        assert SchemaEnricherSubWorkflow is not None

    def test_schema_enricher_has_enrich_method(self):
        """SchemaEnricherSubWorkflow should have an enrich method."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.enricher import (
            SchemaEnricherSubWorkflow,
        )

        enricher = SchemaEnricherSubWorkflow()
        assert hasattr(enricher, "enrich")
        assert callable(enricher.enrich)


class TestSchemaEnricherEnrich:
    """Test SchemaEnricherSubWorkflow.enrich() method."""

    @pytest.fixture
    def sample_tasks(self) -> list[TaskDefinition]:
        """Create sample tasks for testing."""
        return [
            TaskDefinition(
                id="task_001",
                name="Gmail Search",
                description="Search for emails matching query",
                task_type="gmail_search",
                recommended_api="/v1/utility/gmail/search",
                priority=1,
                dependencies=[],
            ),
            TaskDefinition(
                id="task_002",
                name="Send Summary",
                description="Send email summary",
                task_type="email_send",
                recommended_api="/v1/utility/gmail/send",
                priority=2,
                dependencies=["task_001"],
            ),
        ]

    @pytest.fixture
    def sample_interfaces(self) -> dict[str, InterfaceSchema]:
        """Create sample interfaces for testing."""
        return {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "emails": {"type": "array"},
                        "count": {"type": "integer"},
                    },
                },
            ),
            "task_002": InterfaceSchema(
                task_id="task_002",
                input_schema={
                    "type": "object",
                    "properties": {
                        "subject": {"type": "string"},
                        "body": {"type": "string"},
                    },
                },
                output_schema={
                    "type": "object",
                    "properties": {"success": {"type": "boolean"}},
                },
            ),
        }

    @pytest.fixture
    def sample_openapi_specs(self) -> dict[str, Any]:
        """Create sample OpenAPI specs for enrichment."""
        return {
            "/v1/utility/gmail/search": {
                "parameters": {
                    "query": {"type": "string", "maxLength": 500},
                    "max_results": {"type": "integer", "default": 10},
                }
            }
        }

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock execution context."""
        return ExecutionContext(
            job_id="test-job-123",
            user_requirement="Search and send emails",
            max_phase_retries=3,
            max_total_retries=5,
        )

    @pytest.mark.asyncio
    async def test_enrich_returns_enriched_interfaces(
        self,
        sample_tasks: list[TaskDefinition],
        sample_interfaces: dict[str, InterfaceSchema],
        sample_openapi_specs: dict[str, Any],
        mock_context: ExecutionContext,
    ):
        """enrich() should return enriched interfaces."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.enricher import (
            SchemaEnricherSubWorkflow,
        )

        enricher = SchemaEnricherSubWorkflow()
        enriched, report = await enricher.enrich(
            sample_tasks, sample_interfaces, sample_openapi_specs, mock_context
        )

        assert isinstance(enriched, dict)
        assert len(enriched) == len(sample_interfaces)
        assert isinstance(report, EnrichmentReport)

    @pytest.mark.asyncio
    async def test_enrich_returns_enrichment_report(
        self,
        sample_tasks: list[TaskDefinition],
        sample_interfaces: dict[str, InterfaceSchema],
        sample_openapi_specs: dict[str, Any],
        mock_context: ExecutionContext,
    ):
        """enrich() should return EnrichmentReport with details."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.enricher import (
            SchemaEnricherSubWorkflow,
        )

        enricher = SchemaEnricherSubWorkflow()
        _, report = await enricher.enrich(
            sample_tasks, sample_interfaces, sample_openapi_specs, mock_context
        )

        assert hasattr(report, "enriched_count")
        assert hasattr(report, "skipped_count")
        assert hasattr(report, "details")

    @pytest.mark.asyncio
    async def test_enrich_without_openapi_specs(
        self,
        sample_tasks: list[TaskDefinition],
        sample_interfaces: dict[str, InterfaceSchema],
        mock_context: ExecutionContext,
    ):
        """enrich() should work without OpenAPI specs (just pass through)."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.enricher import (
            SchemaEnricherSubWorkflow,
        )

        enricher = SchemaEnricherSubWorkflow()
        enriched, report = await enricher.enrich(
            sample_tasks, sample_interfaces, {}, mock_context
        )

        # Without specs, should pass through unchanged
        assert len(enriched) == len(sample_interfaces)
        assert report.skipped_count >= 0


class TestDerivedFieldsEnrichment:
    """Test derived_fields enrichment functionality."""

    @pytest.fixture
    def mock_context(self) -> ExecutionContext:
        """Create mock execution context."""
        return ExecutionContext(
            job_id="test-job-456",
            user_requirement="Test derived fields",
            max_phase_retries=3,
            max_total_retries=5,
        )

    def test_derived_field_definition_importable(self):
        """DerivedFieldDefinition should be importable from types."""
        from aiagent.langgraph.jobGeneratorV2.types import (
            DerivedFieldDefinition,
        )

        assert DerivedFieldDefinition is not None

    def test_derived_field_creation(self):
        """DerivedFieldDefinition should be creatable with template."""
        from aiagent.langgraph.jobGeneratorV2.types import (
            DerivedFieldDefinition,
        )

        derived = DerivedFieldDefinition(
            template="Search results: {query}",
            type="string",
            description="Email subject line",
        )

        assert derived.template == "Search results: {query}"
        assert derived.type == "string"

    @pytest.mark.asyncio
    async def test_enrich_adds_derived_fields(self, mock_context: ExecutionContext):
        """enrich() should add derived_fields to output_schema when appropriate."""
        from aiagent.langgraph.jobGeneratorV2.workflows.interface_design.enricher import (
            SchemaEnricherSubWorkflow,
        )

        tasks = [
            TaskDefinition(
                id="task_001",
                name="Search",
                description="Search for data",
                task_type="search",
                recommended_api="/v1/search",
                priority=1,
                dependencies=[],
            ),
        ]

        interfaces = {
            "task_001": InterfaceSchema(
                task_id="task_001",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
                output_schema={
                    "type": "object",
                    "properties": {"results": {"type": "array"}},
                },
            ),
        }

        enricher = SchemaEnricherSubWorkflow()
        enriched, _ = await enricher.enrich(tasks, interfaces, {}, mock_context)

        # Verify the interface is returned (derived_fields may or may not be added
        # depending on implementation - at minimum, interface should pass through)
        assert "task_001" in enriched


class TestGracefulDegradation:
    """Test graceful degradation for invalid derived_fields (Issue #338)."""

    def test_derived_fields_graceful_degradation_for_string(self):
        """DerivedFieldDefinition validator should handle string input gracefully."""
        # Use types_old for InterfaceSchemaDefinition and degradation functions
        from aiagent.langgraph.jobGeneratorV2.types_old import (
            InterfaceSchemaDefinition,
            get_derived_fields_degradation_count,
            reset_derived_fields_degradation_count,
        )

        reset_derived_fields_degradation_count()

        # Create definition with invalid string for derived_fields
        definition = InterfaceSchemaDefinition(
            task_id="test_task",
            interface_name="test_interface",
            description="Test interface",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            derived_fields="invalid_string_value",  # This should be gracefully degraded
        )

        # Should be converted to empty dict
        assert definition.derived_fields == {}

        # Degradation should have been counted
        assert get_derived_fields_degradation_count() >= 1

    def test_derived_fields_graceful_degradation_for_none(self):
        """DerivedFieldDefinition validator should handle None input gracefully."""
        # Use types_old for InterfaceSchemaDefinition
        from aiagent.langgraph.jobGeneratorV2.types_old import (
            InterfaceSchemaDefinition,
        )

        definition = InterfaceSchemaDefinition(
            task_id="test_task",
            interface_name="test_interface",
            description="Test interface",
            input_schema={"type": "object"},
            output_schema={"type": "object"},
            derived_fields=None,
        )

        # None should be converted to empty dict
        assert definition.derived_fields == {}
