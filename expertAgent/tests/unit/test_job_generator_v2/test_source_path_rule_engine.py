"""Tests for SourcePathRuleEngine.

Issue #342 Task 1.2: SourcePathRuleEngine implementation tests.

This module tests:
- Path validation (valid/invalid patterns)
- Path generation for different contexts
- Error message generation
"""

import pytest


class TestSourcePathRuleEngine:
    """Tests for SourcePathRuleEngine."""

    @pytest.fixture
    def engine(self):
        """Create SourcePathRuleEngine instance."""
        from aiagent.langgraph.jobGeneratorV2.validators.source_path_rule_engine import (
            SourcePathRuleEngine,
        )

        return SourcePathRuleEngine()

    # ========== Path Validation Tests ==========

    def test_validate_path_with_valid_user_input(self, engine):
        """Valid path: :source.user_input.query"""
        is_valid, error = engine.validate_path(":source.user_input.query")
        assert is_valid is True
        assert error == ""

    def test_validate_path_with_valid_user_input_nested(self, engine):
        """Valid path: :source.user_input.search_results[0].title"""
        is_valid, error = engine.validate_path(
            ":source.user_input.search_results[0].title"
        )
        assert is_valid is True
        assert error == ""

    def test_validate_path_with_valid_job_params(self, engine):
        """Valid path: :source.job_params.model_name"""
        is_valid, error = engine.validate_path(":source.job_params.model_name")
        assert is_valid is True
        assert error == ""

    def test_validate_path_with_valid_node_reference(self, engine):
        """Valid path: :search_node.results"""
        is_valid, error = engine.validate_path(":search_node.results")
        assert is_valid is True
        assert error == ""

    def test_validate_path_with_valid_node_reference_nested(self, engine):
        """Valid path: :fetch_data.response.items[0].name"""
        is_valid, error = engine.validate_path(":fetch_data.response.items[0].name")
        assert is_valid is True
        assert error == ""

    def test_validate_path_with_invalid_source_direct(self, engine):
        """Invalid path: :source.query (missing user_input/job_params)"""
        is_valid, error = engine.validate_path(":source.query")
        assert is_valid is False
        assert "user_input" in error or "job_params" in error

    def test_validate_path_with_invalid_source_body(self, engine):
        """Invalid path: :source.body.field (body is not valid)"""
        is_valid, error = engine.validate_path(":source.body.field")
        assert is_valid is False
        assert "user_input" in error or "job_params" in error

    def test_validate_path_with_invalid_source_results(self, engine):
        """Invalid path: :source.search_results (should be user_input.search_results)"""
        is_valid, error = engine.validate_path(":source.search_results")
        assert is_valid is False
        assert "user_input" in error or "job_params" in error

    def test_validate_path_with_legacy_job_body(self, engine):
        """Invalid path: {{job.body}} (legacy pattern)"""
        is_valid, error = engine.validate_path("{{job.body}}")
        assert is_valid is False
        assert "legacy" in error.lower() or "job.body" in error

    def test_validate_path_with_legacy_task_output(self, engine):
        """Invalid path: {{tasks[N].output_data}} (legacy pattern)"""
        is_valid, error = engine.validate_path("{{tasks[0].output_data}}")
        assert is_valid is False
        assert "legacy" in error.lower() or "tasks" in error

    # ========== Path Generation Tests ==========

    def test_generate_path_previous_task(self, engine):
        """Generate path for previous task output."""
        path = engine.generate_path("previous_task", "search_results")
        assert path == ":source.user_input.search_results"

    def test_generate_path_job_params(self, engine):
        """Generate path for job parameters."""
        path = engine.generate_path("job_params", "query")
        assert path == ":source.job_params.query"

    def test_generate_path_node_reference(self, engine):
        """Generate path for node reference."""
        path = engine.generate_path("node", "search_node.results", node_name="search_node")
        assert path == ":search_node.results"

    def test_generate_path_invalid_context(self, engine):
        """Raise error for invalid context."""
        with pytest.raises(ValueError) as exc_info:
            engine.generate_path("invalid_context", "field")
        assert "unknown context" in str(exc_info.value).lower()

    # ========== Workflow Validation Tests ==========

    def test_validate_workflow_with_valid_paths(self, engine):
        """Validate workflow with all valid paths."""
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "query": ":source.user_input.query",
                        "num": ":source.job_params.num",
                    },
                },
                "output": {
                    "agent": "copyAgent",
                    "inputs": {
                        "results": ":search.search_results",
                    },
                    "isResult": True,
                },
            }
        }
        errors = engine.validate_workflow(workflow)
        assert len(errors) == 0

    def test_validate_workflow_with_invalid_paths(self, engine):
        """Validate workflow detects invalid paths."""
        workflow = {
            "nodes": {
                "source": {},
                "search": {
                    "agent": "fetchAgent",
                    "inputs": {
                        "query": ":source.query",  # Invalid: missing user_input
                        "results": ":source.body.field",  # Invalid: body
                    },
                },
            }
        }
        errors = engine.validate_workflow(workflow)
        assert len(errors) >= 2

    def test_validate_workflow_with_legacy_patterns(self, engine):
        """Validate workflow detects legacy patterns."""
        workflow = {
            "nodes": {
                "source": {},
                "transform": {
                    "agent": "stringTemplateAgent",
                    "inputs": {
                        "data": "{{job.body}}",
                    },
                },
            }
        }
        errors = engine.validate_workflow(workflow)
        assert len(errors) >= 1
        assert any("legacy" in e.lower() or "job.body" in e for e in errors)


class TestSourcePathRuleEngineEdgeCases:
    """Edge case tests for SourcePathRuleEngine."""

    @pytest.fixture
    def engine(self):
        """Create SourcePathRuleEngine instance."""
        from aiagent.langgraph.jobGeneratorV2.validators.source_path_rule_engine import (
            SourcePathRuleEngine,
        )

        return SourcePathRuleEngine()

    def test_empty_path(self, engine):
        """Empty path should be invalid."""
        is_valid, error = engine.validate_path("")
        assert is_valid is False

    def test_none_path(self, engine):
        """None path should be invalid."""
        is_valid, error = engine.validate_path(None)
        assert is_valid is False

    def test_numeric_path(self, engine):
        """Numeric path should be invalid."""
        is_valid, error = engine.validate_path(":1234")
        assert is_valid is False

    def test_url_like_path(self, engine):
        """URL-like paths (http://...) should be skipped/valid."""
        is_valid, error = engine.validate_path("http://localhost:8004/api")
        # URLs are not path references, so they should be valid (skipped)
        assert is_valid is True

    def test_deeply_nested_path(self, engine):
        """Deeply nested path should be valid."""
        is_valid, error = engine.validate_path(
            ":source.user_input.data[0].items[1].nested.field"
        )
        assert is_valid is True
