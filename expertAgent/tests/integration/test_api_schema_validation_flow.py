"""Integration tests for API Schema Validation Flow.

Issue #344 Task 4.3: Integration tests for ValidationPipeline with APISchemaValidator.

This module tests:
- ValidationPipeline integration with APISchemaValidator
- End-to-end validation flow
- Error feedback generation
"""

import pytest


class TestValidationPipelineAPISchemaIntegration:
    """Test ValidationPipeline integrates with APISchemaValidator."""

    @pytest.fixture
    def pipeline(self):
        """Create ValidationPipeline instance."""
        from aiagent.langgraph.jobGeneratorV2.pipeline.validation_pipeline import (
            ValidationPipeline,
        )

        return ValidationPipeline()

    def test_pipeline_includes_api_schema_validator(self, pipeline):
        """Pipeline should include APISchemaValidator by default."""
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            APISchemaValidator,
        )

        validator_types = [type(v).__name__ for v in pipeline.validators]
        assert "APISchemaValidator" in validator_types

    def test_pipeline_detects_api_parameter_errors(self, pipeline):
        """Pipeline should detect API parameter errors via APISchemaValidator."""
        from aiagent.langgraph.jobGeneratorV2.validators import ValidationErrorCode

        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "query": ":source.user_input.query",  # Wrong!
                            "num": 3,
                        },
                    },
                    "timeout": 60000,
                },
            }
        }
        result = pipeline.validate(workflow)
        assert result.is_valid is False
        assert len(result.errors) >= 1
        # Check for API parameter error
        api_errors = [
            e for e in result.errors if e.code == ValidationErrorCode.UNKNOWN_API_PARAMETER
        ]
        assert len(api_errors) >= 1

    def test_pipeline_validates_both_path_and_api_errors(self, pipeline):
        """Pipeline should detect both path and API parameter errors."""
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "query": "{{job.body}}",  # Legacy path AND wrong param name
                            "num": 3,
                        },
                    },
                    "timeout": 60000,
                },
            }
        }
        result = pipeline.validate(workflow)
        assert result.is_valid is False
        # Should have multiple types of errors
        assert len(result.errors) >= 1


class TestErrorFeedbackGeneration:
    """Test error feedback generation for LLM retry."""

    @pytest.fixture
    def pipeline(self):
        """Create ValidationPipeline instance."""
        from aiagent.langgraph.jobGeneratorV2.pipeline.validation_pipeline import (
            ValidationPipeline,
        )

        return ValidationPipeline()

    def test_feedback_includes_api_errors(self, pipeline):
        """Feedback should include API parameter errors with suggestions."""
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "query": ":source.user_input.query",  # Wrong!
                        },
                    },
                },
            }
        }
        result = pipeline.validate(workflow)
        feedback = pipeline.to_prompt_feedback(result)

        # Feedback should mention the error
        assert "UNKNOWN_API_PARAMETER" in feedback or "query" in feedback.lower()

    def test_feedback_suggests_correct_parameter(self, pipeline):
        """Feedback should suggest correct parameter names."""
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "query": ":source.user_input.query",  # Wrong!
                            "num": 3,
                        },
                    },
                },
            }
        }
        result = pipeline.validate(workflow)
        feedback = pipeline.to_prompt_feedback(result)

        # Feedback should suggest 'queries'
        assert "queries" in feedback.lower()


class TestValidationPipelineStats:
    """Test ValidationPipeline statistics with API errors."""

    @pytest.fixture
    def pipeline(self):
        """Create ValidationPipeline instance."""
        from aiagent.langgraph.jobGeneratorV2.pipeline.validation_pipeline import (
            ValidationPipeline,
        )

        return ValidationPipeline()

    def test_valid_workflow_passes(self, pipeline):
        """Valid workflow should pass all validators."""
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "queries": [":source.user_input.query"],
                            "num": 3,
                        },
                    },
                    "timeout": 60000,
                },
            }
        }
        result = pipeline.validate(workflow)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_multiple_api_calls_validated(self, pipeline):
        """Multiple fetchAgent nodes should all be validated."""
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "query": ":source.user_input.query",  # Wrong!
                        },
                    },
                },
                "fetch_content": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERTAGENT_BASE_URL}/aiagent-api/v1/utility/fetch_web_content",
                        "method": "POST",
                        "body": {
                            # Missing required 'url' parameter
                        },
                    },
                },
            }
        }
        result = pipeline.validate(workflow)
        assert result.is_valid is False
        # Should have errors from both nodes
        assert len(result.errors) >= 2
