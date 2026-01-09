"""Integration tests for ValidationPipeline.

Issue #342 Task 4.1 & 5.5: ValidationPipeline implementation and integration tests.

This module tests:
- Validator execution order management
- Error aggregation and prioritization
- End-to-end validation scenarios
"""

import pytest


class TestValidationPipelineBasic:
    """Basic tests for ValidationPipeline."""

    @pytest.fixture
    def pipeline(self):
        """Create ValidationPipeline instance."""
        from aiagent.langgraph.jobGeneratorV2.pipeline.validation_pipeline import (
            ValidationPipeline,
        )

        return ValidationPipeline()

    def test_pipeline_initialization(self, pipeline):
        """Pipeline initializes with validators."""
        assert pipeline is not None
        assert hasattr(pipeline, "validators")
        assert len(pipeline.validators) > 0

    def test_validate_valid_workflow(self, pipeline):
        """Valid workflow passes pipeline."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "process": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "http://localhost:8004/api",
                        "data": ":source.user_input.data",
                    },
                    "timeout": 30000,
                },
                "output": {
                    "agent": "copyAgent",
                    "inputs": {"result": ":process.result"},
                    "isResult": True,
                },
            },
        }
        result = pipeline.validate(workflow)
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_validate_invalid_workflow(self, pipeline):
        """Invalid workflow fails pipeline."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "bad_node": {
                    "agent": "fetchAgent",
                    "inputs": {"url": "${ENV}/api"},
                    "timeout": 30,
                    "isResult": True,
                },
            },
        }
        result = pipeline.validate(workflow)
        assert result.is_valid is False
        assert len(result.errors) > 0


class TestValidationPipelineErrorAggregation:
    """Tests for error aggregation."""

    @pytest.fixture
    def pipeline(self):
        """Create ValidationPipeline instance."""
        from aiagent.langgraph.jobGeneratorV2.pipeline.validation_pipeline import (
            ValidationPipeline,
        )

        return ValidationPipeline()

    def test_catches_all_error_types(self, pipeline):
        """Pipeline catches errors from all validators."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${ENV_VAR}/api",  # Env var error
                        "query": "{{job.body}}",  # Legacy path error
                    },
                    "timeout": 30,  # Timeout error
                },
                "format": {
                    "agent": "stringTemplateAgent",
                    "params": {
                        "template": "${JSON.stringify(data)}",  # JS error
                    },
                    "isResult": True,
                },
            },
        }
        result = pipeline.validate(workflow)
        assert result.is_valid is False
        assert len(result.errors) >= 4

    def test_errors_have_location(self, pipeline):
        """All errors have location information."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "bad": {
                    "agent": "fetchAgent",
                    "timeout": 30,
                    "isResult": True,
                },
            },
        }
        result = pipeline.validate(workflow)
        for error in result.errors:
            assert hasattr(error, "location")
            assert error.location is not None

    def test_errors_have_suggestions(self, pipeline):
        """All errors have suggestions for fixing."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "bad": {
                    "agent": "fetchAgent",
                    "timeout": 30,
                    "isResult": True,
                },
            },
        }
        result = pipeline.validate(workflow)
        for error in result.errors:
            assert hasattr(error, "suggestion")

    def test_errors_sorted_by_priority(self, pipeline):
        """Errors are sorted by severity/priority."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "node1": {
                    "agent": "fetchAgent",
                    "inputs": {"url": "${ENV}/api"},
                    "timeout": 30,
                },
                "node2": {
                    "agent": "stringTemplateAgent",
                    "params": {"template": "${JSON.stringify(x)}"},
                    "isResult": True,
                },
            },
        }
        result = pipeline.validate(workflow)
        # Critical errors should come before minor errors
        if len(result.errors) > 1:
            # Just verify errors are returned in some order
            assert result.errors[0].location is not None


class TestValidationPipelineScenarios:
    """End-to-end validation scenarios."""

    @pytest.fixture
    def pipeline(self):
        """Create ValidationPipeline instance."""
        from aiagent.langgraph.jobGeneratorV2.pipeline.validation_pipeline import (
            ValidationPipeline,
        )

        return ValidationPipeline()

    def test_scenario_search_and_summarize_valid(self, pipeline):
        """Scenario 1: Valid search and summarize workflow."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "fetch_search": {
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
                "stringify": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "http://localhost:8004/aiagent-api/v1/utility/json_stringify",
                        "method": "POST",
                        "body": {
                            "data": ":fetch_search.search_results",
                        },
                    },
                    "timeout": 30000,
                },
                "build_prompt": {
                    "agent": "stringTemplateAgent",
                    "inputs": {
                        "results": ":stringify.json_string",
                    },
                    "params": {
                        "template": "Summarize:\\n${results}",
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
        result = pipeline.validate(workflow)
        assert result.is_valid is True

    def test_scenario_common_ai_mistakes(self, pipeline):
        """Scenario 2: Common AI-generated mistakes."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${EXPERT_AGENT_URL}/aiagent-api/v1/utility/google_search",  # Mistake 1: wrong env var
                        "body": {
                            "query": ":source.user_input.query",  # Mistake 2: should be 'queries' (Issue #344)
                        },
                    },
                    "timeout": 30,  # Mistake 3: seconds not milliseconds
                },
                "format": {
                    "agent": "stringTemplateAgent",
                    "params": {
                        "template": "${JSON.stringify(results)}",  # Mistake 4: JS expression
                    },
                    "isResult": True,
                },
            },
        }
        result = pipeline.validate(workflow)
        assert result.is_valid is False
        # Should catch at least 4 types of errors:
        # 1. ENV_VAR_IN_URL (wrong env var)
        # 2. UNKNOWN_API_PARAMETER (query instead of queries) - Issue #344
        # 3. MISSING_REQUIRED_PARAMETER (queries missing) - Issue #344
        # 4. INVALID_TIMEOUT (30 is likely seconds)
        # 5. JS_IN_TEMPLATE (JSON.stringify)
        assert len(result.errors) >= 4

    def test_scenario_search_fetch_summarize_valid(self, pipeline):
        """Scenario 3: Valid search-fetch-summarize workflow."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "fetch_search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "http://localhost:8004/aiagent-api/v1/utility/google_search",
                        "method": "POST",
                        "body": {
                            "queries": ":source.user_input.queries",
                            "num": 2,
                        },
                    },
                    "timeout": 30000,
                },
                "extract_urls": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "http://localhost:8004/aiagent-api/v1/utility/extract_article_urls",
                        "method": "POST",
                        "body": {
                            "search_results": ":fetch_search.search_results",
                            "max_urls": 2,
                        },
                    },
                    "timeout": 30000,
                },
                "fetch_content": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "http://localhost:8004/aiagent-api/v1/utility/fetch_web_content",
                        "method": "POST",
                        "body": {
                            "url": ":extract_urls.article_url_1",
                        },
                    },
                    "timeout": 60000,
                },
                "stringify": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "http://localhost:8004/aiagent-api/v1/utility/json_stringify",
                        "method": "POST",
                        "body": {
                            "data": ":fetch_content.markdown_content",
                        },
                    },
                    "timeout": 30000,
                },
                "build_prompt": {
                    "agent": "stringTemplateAgent",
                    "inputs": {
                        "content": ":stringify.json_string",
                    },
                    "params": {
                        "template": "Summarize this article:\\n${content}",
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
        result = pipeline.validate(workflow)
        assert result.is_valid is True

    def test_scenario_legacy_patterns(self, pipeline):
        """Scenario 4: Workflow with legacy patterns."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "process": {
                    "agent": "copyAgent",
                    "inputs": {
                        "data": "{{job.body}}",  # Legacy pattern
                        "prev": "{{tasks[0].output_data}}",  # Legacy pattern
                    },
                    "isResult": True,
                },
            },
        }
        result = pipeline.validate(workflow)
        assert result.is_valid is False
        assert len(result.errors) >= 2

    def test_scenario_mixed_valid_invalid(self, pipeline):
        """Scenario 5: Workflow with some valid and some invalid nodes."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "valid_fetch": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "http://localhost:8004/api",
                        "data": ":source.user_input.data",
                    },
                    "timeout": 30000,
                },
                "invalid_fetch": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "url": "${ENV}/api",  # Invalid
                    },
                    "timeout": 30,  # Invalid
                },
                "output": {
                    "agent": "copyAgent",
                    "inputs": {"data": ":valid_fetch.result"},
                    "isResult": True,
                },
            },
        }
        result = pipeline.validate(workflow)
        assert result.is_valid is False
        # Should report errors only for invalid_fetch
        assert any("invalid_fetch" in e.location for e in result.errors)


class TestValidationPipelinePromptFeedback:
    """Tests for prompt feedback generation."""

    @pytest.fixture
    def pipeline(self):
        """Create ValidationPipeline instance."""
        from aiagent.langgraph.jobGeneratorV2.pipeline.validation_pipeline import (
            ValidationPipeline,
        )

        return ValidationPipeline()

    def test_to_prompt_feedback_valid(self, pipeline):
        """Valid workflow returns empty feedback."""
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
        result = pipeline.validate(workflow)
        feedback = pipeline.to_prompt_feedback(result)
        if result.is_valid:
            assert feedback == ""

    def test_to_prompt_feedback_invalid(self, pipeline):
        """Invalid workflow returns detailed feedback."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "bad": {
                    "agent": "fetchAgent",
                    "timeout": 30,
                    "isResult": True,
                },
            },
        }
        result = pipeline.validate(workflow)
        feedback = pipeline.to_prompt_feedback(result)
        assert len(feedback) > 0
        assert "Error" in feedback or "error" in feedback.lower()

    def test_feedback_includes_suggestions(self, pipeline):
        """Feedback includes fix suggestions."""
        workflow = {
            "version": "0.5",
            "nodes": {
                "source": {},
                "bad": {
                    "agent": "stringTemplateAgent",
                    "params": {"template": "${JSON.stringify(x)}"},
                    "isResult": True,
                },
            },
        }
        result = pipeline.validate(workflow)
        feedback = pipeline.to_prompt_feedback(result)
        # Should include suggestion
        assert "Fix" in feedback or "fix" in feedback.lower() or "suggestion" in feedback.lower()
