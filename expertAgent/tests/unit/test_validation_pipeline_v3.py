"""Unit tests for validators/pipeline.py enhancements.

Issue #359 Iteration 2 Task 2.2: Tests for ValidationPipeline enhancement.

TDD Red Phase: These tests define the expected behavior.
"""

import pytest
from unittest.mock import MagicMock

from aiagent.langgraph.jobGeneratorV2.validators import ValidationError, ValidationErrorCode


class TestStructuralValidator:
    """Test suite for StructuralValidator."""

    def test_validator_exists(self):
        """StructuralValidator should exist in pipeline module."""
        from aiagent.langgraph.jobGeneratorV2.validators.pipeline import (
            StructuralValidator,
        )

        validator = StructuralValidator()
        assert validator is not None

    def test_validates_workflow_structure(self):
        """StructuralValidator should validate basic workflow structure."""
        from aiagent.langgraph.jobGeneratorV2.validators.pipeline import (
            StructuralValidator,
        )

        validator = StructuralValidator()

        # Valid workflow
        valid_workflow = {
            "workflow_name": "test_workflow",
            "steps": [
                {"id": "step_001", "type": "api_rest", "config": {}}
            ],
            "input_schema": "{}",
            "output_schema": "{}",
            "output": "{}",
        }

        errors = validator.validate(valid_workflow)
        assert len(errors) == 0

    def test_detects_missing_workflow_name(self):
        """StructuralValidator should detect missing workflow_name."""
        from aiagent.langgraph.jobGeneratorV2.validators.pipeline import (
            StructuralValidator,
        )

        validator = StructuralValidator()

        invalid_workflow = {
            "steps": [],
            "input_schema": "{}",
            "output_schema": "{}",
            "output": "{}",
        }

        errors = validator.validate(invalid_workflow)
        assert len(errors) > 0
        assert any("workflow_name" in e.message.lower() for e in errors)

    def test_detects_missing_steps(self):
        """StructuralValidator should detect missing or empty steps."""
        from aiagent.langgraph.jobGeneratorV2.validators.pipeline import (
            StructuralValidator,
        )

        validator = StructuralValidator()

        invalid_workflow = {
            "workflow_name": "test",
            "input_schema": "{}",
            "output_schema": "{}",
            "output": "{}",
        }

        errors = validator.validate(invalid_workflow)
        assert len(errors) > 0


class TestSchemaValidator:
    """Test suite for SchemaValidator."""

    def test_validator_exists(self):
        """SchemaValidator should exist in pipeline module."""
        from aiagent.langgraph.jobGeneratorV2.validators.pipeline import (
            SchemaValidator,
        )

        validator = SchemaValidator()
        assert validator is not None

    def test_validates_input_schema(self):
        """SchemaValidator should validate input_schema is valid JSON."""
        from aiagent.langgraph.jobGeneratorV2.validators.pipeline import (
            SchemaValidator,
        )

        validator = SchemaValidator()

        workflow = {
            "workflow_name": "test",
            "input_schema": '{"type": "object"}',
            "output_schema": '{"type": "object"}',
            "output": '{}',
            "steps": [],
        }

        errors = validator.validate(workflow)
        schema_errors = [e for e in errors if "input_schema" in e.location]
        assert len(schema_errors) == 0

    def test_detects_invalid_json_schema(self):
        """SchemaValidator should detect invalid JSON in schema fields."""
        from aiagent.langgraph.jobGeneratorV2.validators.pipeline import (
            SchemaValidator,
        )

        validator = SchemaValidator()

        workflow = {
            "workflow_name": "test",
            "input_schema": "not valid json",
            "output_schema": '{}',
            "output": '{}',
            "steps": [],
        }

        errors = validator.validate(workflow)
        assert len(errors) > 0


class TestSemanticValidator:
    """Test suite for SemanticValidator."""

    def test_validator_exists(self):
        """SemanticValidator should exist in pipeline module."""
        from aiagent.langgraph.jobGeneratorV2.validators.pipeline import (
            SemanticValidator,
        )

        validator = SemanticValidator()
        assert validator is not None

    def test_validates_step_references(self):
        """SemanticValidator should validate step references are valid."""
        from aiagent.langgraph.jobGeneratorV2.validators.pipeline import (
            SemanticValidator,
        )

        validator = SemanticValidator()

        workflow = {
            "workflow_name": "test",
            "steps": [
                {"id": "step_001", "type": "api_rest", "config": {}},
                {
                    "id": "step_002",
                    "type": "transform",
                    "config": {
                        "step_type": "transform",
                        "mode": "template",
                        "template": "${step_001.output}",
                    }
                },
            ],
            "input_schema": '{}',
            "output_schema": '{}',
            "output": '{"result": "${step_002.output}"}',
        }

        errors = validator.validate(workflow)
        # step_001 is referenced by step_002, which is valid
        ref_errors = [e for e in errors if "reference" in e.message.lower()]
        assert len(ref_errors) == 0

    def test_detects_invalid_step_reference(self):
        """SemanticValidator should detect references to non-existent steps."""
        from aiagent.langgraph.jobGeneratorV2.validators.pipeline import (
            SemanticValidator,
        )

        validator = SemanticValidator()

        workflow = {
            "workflow_name": "test",
            "steps": [
                {"id": "step_001", "type": "api_rest", "config": {}},
            ],
            "input_schema": '{}',
            "output_schema": '{}',
            "output": '{"result": "${nonexistent_step.output}"}',
        }

        errors = validator.validate(workflow)
        assert len(errors) > 0
        assert any("nonexistent" in e.message.lower() or "reference" in e.message.lower()
                   for e in errors)


class TestEnhancedValidationPipeline:
    """Test suite for enhanced ValidationPipeline."""

    def test_pipeline_includes_new_validators(self):
        """Pipeline should include Structural, Schema, and Semantic validators."""
        from aiagent.langgraph.jobGeneratorV2.validators.pipeline import (
            ValidationPipelineV3,
            StructuralValidator,
            SchemaValidator,
            SemanticValidator,
        )

        pipeline = ValidationPipelineV3()

        validator_types = [type(v).__name__ for v in pipeline.validators]

        assert "StructuralValidator" in validator_types
        assert "SchemaValidator" in validator_types
        assert "SemanticValidator" in validator_types

    def test_pipeline_runs_validators_in_order(self):
        """Pipeline should run validators in correct order."""
        from aiagent.langgraph.jobGeneratorV2.validators.pipeline import (
            ValidationPipelineV3,
        )

        pipeline = ValidationPipelineV3()

        # Structural should come before Schema which should come before Semantic
        validator_names = [type(v).__name__ for v in pipeline.validators]

        structural_idx = validator_names.index("StructuralValidator")
        schema_idx = validator_names.index("SchemaValidator")
        semantic_idx = validator_names.index("SemanticValidator")

        assert structural_idx < schema_idx < semantic_idx

    def test_pipeline_aggregates_errors(self):
        """Pipeline should aggregate errors from all validators."""
        from aiagent.langgraph.jobGeneratorV2.validators.pipeline import (
            ValidationPipelineV3,
        )

        pipeline = ValidationPipelineV3()

        # Workflow with multiple issues
        workflow = {
            # Missing workflow_name - structural error
            "steps": [],  # Empty steps - structural error
            "input_schema": "invalid json",  # Schema error
            "output_schema": '{}',
            "output": '{}',
        }

        result = pipeline.validate(workflow)

        assert not result.is_valid
        # Should have errors from multiple validators
        assert len(result.errors) >= 2


class TestValidationPipelineChaining:
    """Test chain pattern implementation."""

    def test_early_exit_on_structural_failure(self):
        """Pipeline should optionally exit early on critical structural failures."""
        from aiagent.langgraph.jobGeneratorV2.validators.pipeline import (
            ValidationPipelineV3,
        )

        pipeline = ValidationPipelineV3(fail_fast=True)

        # Completely invalid workflow
        workflow = {}

        result = pipeline.validate(workflow)

        assert not result.is_valid
        # With fail_fast, should stop after structural validation
        # (implementation-dependent, but errors should be present)
        assert len(result.errors) > 0

    def test_continue_on_minor_errors(self):
        """Pipeline should continue validation on minor errors."""
        from aiagent.langgraph.jobGeneratorV2.validators.pipeline import (
            ValidationPipelineV3,
        )

        pipeline = ValidationPipelineV3(fail_fast=False)

        workflow = {
            "workflow_name": "test",
            "steps": [{"id": "step_001", "type": "api_rest", "config": {}}],
            "input_schema": '{}',
            "output_schema": '{}',
            "output": '{"result": "${missing_step.output}"}',  # Semantic error
        }

        result = pipeline.validate(workflow)

        # Should have run all validators even with semantic error
        assert not result.is_valid
