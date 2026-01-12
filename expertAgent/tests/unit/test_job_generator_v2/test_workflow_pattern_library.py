"""Tests for WorkflowPatternLibrary.

Issue #342 Task 3.1: WorkflowPatternLibrary implementation tests.

This module tests:
- Standard pattern definitions
- Pattern selection logic
- Template generation
"""

import pytest


class TestWorkflowPatternLibrary:
    """Tests for WorkflowPatternLibrary."""

    @pytest.fixture
    def library(self):
        """Create WorkflowPatternLibrary instance."""
        from aiagent.langgraph.jobGeneratorV2.patterns.workflow_pattern_library import (
            WorkflowPatternLibrary,
        )

        return WorkflowPatternLibrary()

    def test_patterns_loaded(self, library):
        """Patterns are loaded on init."""
        assert library.patterns is not None
        assert len(library.patterns) > 0

    def test_get_search_and_summarize_pattern(self, library):
        """search_and_summarize pattern is available."""
        pattern = library.get_pattern("search_and_summarize")
        assert pattern is not None
        assert "description" in pattern
        assert "nodes" in pattern or "template" in pattern

    def test_get_search_fetch_summarize_pattern(self, library):
        """search_fetch_summarize pattern is available."""
        pattern = library.get_pattern("search_fetch_summarize")
        assert pattern is not None
        assert "description" in pattern

    def test_get_unknown_pattern(self, library):
        """Unknown pattern returns None."""
        pattern = library.get_pattern("nonexistent_pattern")
        assert pattern is None

    def test_list_all_patterns(self, library):
        """List all available patterns."""
        patterns = library.list_patterns()
        assert isinstance(patterns, list)
        assert "search_and_summarize" in patterns
        assert "search_fetch_summarize" in patterns

    def test_suggest_pattern_search_summarize(self, library):
        """Suggest pattern for search and summarize requirement."""
        suggestion = library.suggest_pattern(
            "Google検索結果を要約してください"
        )
        assert suggestion in ["search_and_summarize", "search_fetch_summarize"]

    def test_suggest_pattern_article_fetch(self, library):
        """Suggest pattern for article fetch requirement."""
        suggestion = library.suggest_pattern(
            "記事の内容を取得して要約してください"
        )
        assert suggestion == "search_fetch_summarize"

    def test_suggest_pattern_web_content(self, library):
        """Suggest pattern for web content requirement."""
        suggestion = library.suggest_pattern(
            "Webページの内容を取得して分析してください"
        )
        assert suggestion == "search_fetch_summarize"

    def test_suggest_pattern_default(self, library):
        """Default pattern suggestion for generic requirement."""
        suggestion = library.suggest_pattern(
            "何かをしてください"
        )
        assert suggestion is not None  # Should return some pattern


class TestWorkflowPatternLibraryTemplate:
    """Tests for pattern template generation."""

    @pytest.fixture
    def library(self):
        """Create WorkflowPatternLibrary instance."""
        from aiagent.langgraph.jobGeneratorV2.patterns.workflow_pattern_library import (
            WorkflowPatternLibrary,
        )

        return WorkflowPatternLibrary()

    def test_get_template_search_and_summarize(self, library):
        """Get template for search_and_summarize."""
        template = library.get_template("search_and_summarize")
        assert template is not None
        assert "version" in template
        assert "nodes" in template

    def test_template_has_source_node(self, library):
        """Template has source node."""
        template = library.get_template("search_and_summarize")
        assert "source" in template.get("nodes", {})

    def test_template_has_result_node(self, library):
        """Template has result node."""
        template = library.get_template("search_and_summarize")
        nodes = template.get("nodes", {})
        has_result = any(
            node.get("isResult", False)
            for name, node in nodes.items()
            if isinstance(node, dict)
        )
        assert has_result

    def test_template_valid_source_paths(self, library):
        """Template uses valid source paths."""
        template = library.get_template("search_and_summarize")
        template_str = str(template)
        # Should use :source.user_input.* not :source.*
        if ":source." in template_str:
            # All :source references should include user_input or job_params
            import re
            source_refs = re.findall(r":source\.\w+", template_str)
            for ref in source_refs:
                # :source.user_input or :source.job_params
                assert "user_input" in ref or "job_params" in ref, f"Invalid ref: {ref}"

    def test_template_valid_timeouts(self, library):
        """Template uses millisecond timeouts."""
        template = library.get_template("search_and_summarize")
        nodes = template.get("nodes", {})
        for node_name, node_def in nodes.items():
            if isinstance(node_def, dict) and "timeout" in node_def:
                timeout = node_def["timeout"]
                assert timeout >= 1000, f"Timeout {timeout} in {node_name} is too small"

    def test_template_no_env_vars(self, library):
        """Template does not use environment variables."""
        template = library.get_template("search_and_summarize")
        template_str = str(template)
        assert "${" not in template_str or "${" in template_str and "{{" not in template_str
        # Check for common env var patterns in URLs
        assert "${EXPERT" not in template_str
        assert "${API" not in template_str


class TestWorkflowPatternLibrarySearchFetchSummarize:
    """Tests for search_fetch_summarize pattern."""

    @pytest.fixture
    def library(self):
        """Create WorkflowPatternLibrary instance."""
        from aiagent.langgraph.jobGeneratorV2.patterns.workflow_pattern_library import (
            WorkflowPatternLibrary,
        )

        return WorkflowPatternLibrary()

    def test_pattern_has_url_extraction(self, library):
        """Pattern includes URL extraction step."""
        template = library.get_template("search_fetch_summarize")
        nodes = template.get("nodes", {})
        node_names = list(nodes.keys())
        node_str = str(nodes).lower()
        # Should have extract_article_urls call
        assert "extract" in node_str or any("url" in n.lower() for n in node_names)

    def test_pattern_has_fetch_content(self, library):
        """Pattern includes fetch content step."""
        template = library.get_template("search_fetch_summarize")
        nodes = template.get("nodes", {})
        node_str = str(nodes).lower()
        # Should have fetch_web_content call
        assert "fetch" in node_str or "content" in node_str

    def test_pattern_has_stringify(self, library):
        """Pattern includes stringify step for template agent."""
        template = library.get_template("search_fetch_summarize")
        nodes = template.get("nodes", {})
        node_str = str(nodes).lower()
        # Should have json_stringify call
        assert "stringify" in node_str

    def test_pattern_correct_node_order(self, library):
        """Pattern nodes are in correct order."""
        template = library.get_template("search_fetch_summarize")
        nodes = template.get("nodes", {})
        # Verify nodes reference earlier nodes (not circular)
        node_names = list(nodes.keys())
        for i, (node_name, node_def) in enumerate(nodes.items()):
            if node_name == "source":
                continue
            if isinstance(node_def, dict):
                # Check inputs reference earlier nodes or source
                inputs = node_def.get("inputs", {})
                for _key, value in inputs.items():
                    if isinstance(value, str) and value.startswith(":"):
                        ref_node = value.split(".")[0][1:]  # Remove :
                        if ref_node != "source":
                            # Referenced node should be before current
                            if ref_node in node_names:
                                ref_idx = node_names.index(ref_node)
                                assert ref_idx < i, f"{node_name} refs {ref_node} which comes after"


class TestWorkflowPatternLibraryPatternProvider:
    """Tests for PatternProvider protocol implementation."""

    @pytest.fixture
    def library(self):
        """Create WorkflowPatternLibrary instance."""
        from aiagent.langgraph.jobGeneratorV2.patterns.workflow_pattern_library import (
            WorkflowPatternLibrary,
        )

        return WorkflowPatternLibrary()

    def test_implements_protocol(self, library):
        """WorkflowPatternLibrary implements PatternProvider protocol."""

        # Should have required methods
        assert hasattr(library, "get_pattern")
        assert hasattr(library, "suggest_pattern")
        assert callable(library.get_pattern)
        assert callable(library.suggest_pattern)
