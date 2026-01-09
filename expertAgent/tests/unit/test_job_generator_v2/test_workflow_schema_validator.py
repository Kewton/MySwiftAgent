"""Tests for WorkflowSchemaValidator.

Issue #342 Task 1.4: WorkflowSchemaValidator implementation tests.

This module tests:
- Multiple validator integration
- Error aggregation from all validators
- Workflow-level validation
"""

import pytest


class TestWorkflowSchemaValidator:
    """Tests for WorkflowSchemaValidator."""

    @pytest.fixture
    def validator(self):
        """Create WorkflowSchemaValidator instance."""
        from aiagent.langgraph.jobGeneratorV2.validators.workflow_schema_validator import (
            WorkflowSchemaValidator,
        )

        return WorkflowSchemaValidator()

    def test_valid_workflow(self, validator):
        """Valid workflow passes all validators."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "http://localhost:8004/api/search",
                        "method": "POST",
                        "body": {
                            "query": ":source.user_input.query",
                        },
                    },
                    "timeout": 30000,
                },
                "output": {
                    "agent": "copyAgent",
                    "inputs": {"data": ":search.results"},
                    "isResult": True,
                },
            },
        }
        errors = validator.validate(workflow)
        assert len(errors) == 0

    def test_invalid_env_var_in_url(self, validator):
        """URL with environment variable is invalid."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "fetch": {
                    "agent": "fetchAgent",
                    "inputs": {"url": "${EXPERT_AGENT_URL}/api"},
                    "isResult": True,
                },
            },
        }
        errors = validator.validate(workflow)
        assert len(errors) > 0
        assert any("environment" in e.message.lower() or "env" in e.message.lower() for e in errors)

    def test_invalid_timeout_seconds(self, validator):
        """Timeout in seconds (not milliseconds) is invalid."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "llm": {
                    "agent": "fetchAgent",
                    "inputs": {"url": "http://localhost:8004/api"},
                    "timeout": 60,  # 60ms vs 60s
                    "isResult": True,
                },
            },
        }
        errors = validator.validate(workflow)
        assert len(errors) > 0
        assert any("timeout" in e.message.lower() or "milliseconds" in e.message.lower() for e in errors)

    def test_invalid_source_path(self, validator):
        """Invalid source path is detected."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "process": {
                    "agent": "copyAgent",
                    "inputs": {
                        "data": ":source.query",  # Invalid: missing user_input
                    },
                    "isResult": True,
                },
            },
        }
        errors = validator.validate(workflow)
        assert len(errors) > 0
        assert any("source" in e.message.lower() or "user_input" in e.message.lower() for e in errors)

    def test_invalid_js_in_template(self, validator):
        """JavaScript in stringTemplateAgent is detected."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "format": {
                    "agent": "stringTemplateAgent",
                    "params": {"template": "Data: ${JSON.stringify(results)}"},
                    "isResult": True,
                },
            },
        }
        errors = validator.validate(workflow)
        assert len(errors) > 0
        assert any("javascript" in e.message.lower() or "json" in e.message.lower() for e in errors)

    def test_multiple_errors_aggregation(self, validator):
        """Multiple errors from different validators are aggregated."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "fetch": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${API_URL}/search",  # Error 1: env var
                        "query": ":source.query",  # Error 2: invalid path
                    },
                    "timeout": 30,  # Error 3: timeout too small
                },
                "format": {
                    "agent": "stringTemplateAgent",
                    "params": {"template": "${JSON.stringify(data)}"},  # Error 4: JS
                    "isResult": True,
                },
            },
        }
        errors = validator.validate(workflow)
        assert len(errors) >= 4

    def test_error_location_info(self, validator):
        """Errors contain location information."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "bad_node": {
                    "agent": "fetchAgent",
                    "inputs": {"url": "${ENV}/api"},
                    "isResult": True,
                },
            },
        }
        errors = validator.validate(workflow)
        assert len(errors) > 0
        assert all(hasattr(e, "location") and e.location for e in errors)
        assert any("bad_node" in e.location for e in errors)

    def test_error_suggestion_info(self, validator):
        """Errors contain suggestion information."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "fetch": {
                    "agent": "fetchAgent",
                    "timeout": 60,
                    "isResult": True,
                },
            },
        }
        errors = validator.validate(workflow)
        assert len(errors) > 0
        assert all(hasattr(e, "suggestion") for e in errors)


class TestWorkflowSchemaValidatorValidationResult:
    """Tests for ValidationResult structure."""

    @pytest.fixture
    def validator(self):
        """Create WorkflowSchemaValidator instance."""
        from aiagent.langgraph.jobGeneratorV2.validators.workflow_schema_validator import (
            WorkflowSchemaValidator,
        )

        return WorkflowSchemaValidator()

    def test_validate_returns_validation_result(self, validator):
        """validate() returns ValidationResult with is_valid and errors."""
        workflow = {"version": "0.5", "nodes": {"source": {}}}
        result = validator.validate(workflow)
        # Result should be a list of ValidationError objects
        assert isinstance(result, list)

    def test_to_prompt_feedback_empty_on_success(self, validator):
        """to_prompt_feedback() returns empty string on success."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "output": {
                    "agent": "copyAgent",
                    "inputs": {"data": ":source.user_input.data"},
                    "isResult": True,
                },
            },
        }
        errors = validator.validate(workflow)
        if len(errors) == 0:
            feedback = validator.to_prompt_feedback(errors)
            assert feedback == ""

    def test_to_prompt_feedback_includes_errors(self, validator):
        """to_prompt_feedback() includes error details for LLM retry."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "fetch": {
                    "agent": "fetchAgent",
                    "timeout": 30,
                    "isResult": True,
                },
            },
        }
        errors = validator.validate(workflow)
        feedback = validator.to_prompt_feedback(errors)
        assert "Error" in feedback or "error" in feedback
        assert "timeout" in feedback.lower() or "milliseconds" in feedback.lower()


class TestWorkflowSchemaValidatorIntegration:
    """Integration tests for WorkflowSchemaValidator."""

    @pytest.fixture
    def validator(self):
        """Create WorkflowSchemaValidator instance."""
        from aiagent.langgraph.jobGeneratorV2.validators.workflow_schema_validator import (
            WorkflowSchemaValidator,
        )

        return WorkflowSchemaValidator()

    def test_real_world_workflow_search_summarize(self, validator):
        """Validate real-world search and summarize workflow."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "fetch_search_results": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "http://localhost:8004/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "queries": ":source.user_input.queries",
                            "num": 3,
                        },
                    },
                    "timeout": 30000,
                },
                "stringify_results": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "http://localhost:8004/aiagent-api/v1/utility/json_stringify",
                        "method": "POST",
                        "body": {
                            "data": ":fetch_search_results.search_results",
                        },
                    },
                    "timeout": 30000,
                },
                "build_prompt": {
                    "agent": "stringTemplateAgent",
                    "inputs": {
                        "results": ":stringify_results.json_string",
                    },
                    "params": {
                        "template": "Summarize the following search results:\\n${results}",
                    },
                },
                "call_llm": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "http://localhost:8004/aiagent-api/v1/aiagent/utility/jsonoutput",
                        "method": "POST",
                        "body": {
                            "user_input": ":build_prompt",
                            "model_name": "gemini-2.0-flash",
                        },
                    },
                    "timeout": 120000,
                    "isResult": True,
                },
            },
        }
        errors = validator.validate(workflow)
        assert len(errors) == 0

    def test_real_world_workflow_with_errors(self, validator):
        """Validate real-world workflow with common AI-generated errors."""
        # This is an example of what AI might incorrectly generate
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "fetch_search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERT_AGENT_URL}/utility/google_search",  # Error: env var
                        "method": "POST",
                        "body": {
                            "query": ":source.query",  # Error: missing user_input
                        },
                    },
                    "timeout": 30,  # Error: likely seconds not ms
                },
                "format_output": {
                    "agent": "stringTemplateAgent",
                    "params": {
                        "template": "Results: ${JSON.stringify(results)}",  # Error: JS
                    },
                    "isResult": True,
                },
            },
        }
        errors = validator.validate(workflow)
        assert len(errors) >= 4  # At least 4 errors
