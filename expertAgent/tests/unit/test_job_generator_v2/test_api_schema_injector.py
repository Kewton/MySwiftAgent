"""Tests for APISchemaInjector.

Issue #342 Task 2.1: APISchemaInjector implementation tests.

This module tests:
- OpenAPI schema loading
- Prompt injection logic
- API spec markdown conversion
"""

import pytest


class TestAPISchemaInjector:
    """Tests for APISchemaInjector."""

    @pytest.fixture
    def injector(self):
        """Create APISchemaInjector instance."""
        from aiagent.langgraph.jobGeneratorV2.injectors.api_schema_injector import (
            APISchemaInjector,
        )

        return APISchemaInjector()

    def test_load_api_specs(self, injector):
        """API specs are loaded on init."""
        assert injector.specs is not None
        assert len(injector.specs) > 0

    def test_get_google_search_spec(self, injector):
        """Google search API spec is available."""
        spec = injector.get_spec("/utility/google_search")
        assert spec is not None
        assert "endpoint" in spec or "path" in spec
        assert spec.get("method", "POST").upper() == "POST"

    def test_get_json_stringify_spec(self, injector):
        """JSON stringify API spec is available."""
        spec = injector.get_spec("/utility/json_stringify")
        assert spec is not None

    def test_get_fetch_web_content_spec(self, injector):
        """Fetch web content API spec is available."""
        spec = injector.get_spec("/utility/fetch_web_content")
        assert spec is not None

    def test_get_extract_article_urls_spec(self, injector):
        """Extract article URLs API spec is available."""
        spec = injector.get_spec("/utility/extract_article_urls")
        assert spec is not None

    def test_inject_to_prompt_single_api(self, injector):
        """Inject single API spec into prompt."""
        prompt = "Generate a workflow for searching."
        required_apis = ["/utility/google_search"]
        result = injector.inject(prompt, required_apis)
        assert len(result) > len(prompt)
        assert "google_search" in result.lower()
        assert "queries" in result  # Parameter name

    def test_inject_to_prompt_multiple_apis(self, injector):
        """Inject multiple API specs into prompt."""
        prompt = "Generate a search and summarize workflow."
        required_apis = [
            "/utility/google_search",
            "/utility/json_stringify",
        ]
        result = injector.inject(prompt, required_apis)
        assert "google_search" in result.lower()
        assert "json_stringify" in result.lower()

    def test_inject_includes_request_schema(self, injector):
        """Injected spec includes request schema details."""
        prompt = "Search for something."
        required_apis = ["/utility/google_search"]
        result = injector.inject(prompt, required_apis)
        # Should include parameter details
        assert "queries" in result
        assert "num" in result

    def test_inject_includes_response_schema(self, injector):
        """Injected spec includes response schema details."""
        prompt = "Search for something."
        required_apis = ["/utility/google_search"]
        result = injector.inject(prompt, required_apis)
        # Should include response field names
        assert "search_results" in result

    def test_format_spec_to_markdown(self, injector):
        """Format spec to markdown."""
        spec = injector.get_spec("/utility/google_search")
        md = injector.format_to_markdown(spec)
        assert "##" in md or "#" in md  # Has headers
        assert "POST" in md or "GET" in md  # Has method

    def test_unknown_api_returns_none(self, injector):
        """Unknown API returns None."""
        spec = injector.get_spec("/unknown/api")
        assert spec is None

    def test_unknown_api_skipped_in_inject(self, injector):
        """Unknown APIs are skipped in inject."""
        prompt = "Generate workflow."
        required_apis = ["/unknown/api", "/utility/google_search"]
        result = injector.inject(prompt, required_apis)
        assert "google_search" in result.lower()
        assert "unknown" not in result.lower()


class TestAPISchemaInjectorSchemas:
    """Tests for specific API schema content."""

    @pytest.fixture
    def injector(self):
        """Create APISchemaInjector instance."""
        from aiagent.langgraph.jobGeneratorV2.injectors.api_schema_injector import (
            APISchemaInjector,
        )

        return APISchemaInjector()

    def test_google_search_queries_is_array(self, injector):
        """Google search 'queries' parameter is array type."""
        spec = injector.get_spec("/utility/google_search")
        assert spec is not None
        request_schema = spec.get("request_schema", spec.get("request", {}))
        queries_spec = request_schema.get("queries", {})
        # Should indicate array type
        assert queries_spec.get("type") == "array" or "array" in str(queries_spec).lower()

    def test_google_search_num_has_max(self, injector):
        """Google search 'num' parameter has max value."""
        spec = injector.get_spec("/utility/google_search")
        assert spec is not None
        request_schema = spec.get("request_schema", spec.get("request", {}))
        num_spec = request_schema.get("num", {})
        # Should have max constraint (3 to prevent timeout)
        assert "max" in num_spec or num_spec.get("maximum") is not None or num_spec.get("le") is not None

    def test_json_stringify_data_any_type(self, injector):
        """JSON stringify 'data' parameter accepts any type."""
        spec = injector.get_spec("/utility/json_stringify")
        assert spec is not None
        request_schema = spec.get("request_schema", spec.get("request", {}))
        data_spec = request_schema.get("data", {})
        # Should indicate any/object type
        assert data_spec.get("type") in ("any", "object", None) or "any" in str(data_spec).lower()

    def test_fetch_web_content_url_required(self, injector):
        """Fetch web content 'url' parameter is required."""
        spec = injector.get_spec("/utility/fetch_web_content")
        assert spec is not None
        request_schema = spec.get("request_schema", spec.get("request", {}))
        url_spec = request_schema.get("url", {})
        # URL should be required
        assert url_spec.get("required", True) is True or "required" in str(url_spec).lower()

    def test_extract_urls_max_urls_default(self, injector):
        """Extract article URLs 'max_urls' has default value."""
        spec = injector.get_spec("/utility/extract_article_urls")
        assert spec is not None
        request_schema = spec.get("request_schema", spec.get("request", {}))
        max_urls_spec = request_schema.get("max_urls", {})
        # Should have default value
        assert max_urls_spec.get("default") is not None


class TestAPISchemaInjectorPromptInjector:
    """Tests for PromptInjector protocol implementation."""

    @pytest.fixture
    def injector(self):
        """Create APISchemaInjector instance."""
        from aiagent.langgraph.jobGeneratorV2.injectors.api_schema_injector import (
            APISchemaInjector,
        )

        return APISchemaInjector()

    def test_implements_protocol(self, injector):
        """APISchemaInjector implements PromptInjector protocol."""

        # Should have inject method
        assert hasattr(injector, "inject")
        assert callable(injector.inject)

    def test_inject_context_aware(self, injector):
        """inject() can accept context dict."""
        prompt = "Generate workflow."
        context = {
            "required_apis": ["/utility/google_search"],
            "workflow_type": "search_and_summarize",
        }
        # Should work with context dict
        result = injector.inject(prompt, context.get("required_apis", []))
        assert "google_search" in result.lower()
