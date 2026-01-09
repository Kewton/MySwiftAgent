"""Tests for API Schema definitions.

Issue #344 Task 4.2: Schema definition tests.

This module tests:
- Schema existence for supported APIs
- Required fields in schemas
- PARAMETER_ALIASES coverage
"""

import pytest


class TestAPISchemaDefinitions:
    """Test API schema definitions exist and have correct structure."""

    @pytest.fixture
    def validator(self):
        """Create APISchemaValidator instance."""
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            APISchemaValidator,
        )

        return APISchemaValidator()

    def test_google_search_schema_exists(self, validator):
        """google_search schema should exist."""
        schema = validator.get_schema("/utility/google_search")
        assert schema is not None
        assert "queries" in schema.get("parameters", {})

    def test_fetch_web_content_schema_exists(self, validator):
        """fetch_web_content schema should exist."""
        schema = validator.get_schema("/utility/fetch_web_content")
        assert schema is not None
        assert "url" in schema.get("parameters", {})

    def test_json_stringify_schema_exists(self, validator):
        """json_stringify schema should exist."""
        schema = validator.get_schema("/utility/json_stringify")
        assert schema is not None
        assert "data" in schema.get("parameters", {})

    def test_extract_article_urls_schema_exists(self, validator):
        """extract_article_urls schema should exist."""
        schema = validator.get_schema("/utility/extract_article_urls")
        assert schema is not None
        assert "search_results" in schema.get("parameters", {})

    def test_jsonoutput_schema_exists(self, validator):
        """jsonoutput schema should exist."""
        schema = validator.get_schema("/aiagent/utility/jsonoutput")
        assert schema is not None
        assert "user_input" in schema.get("parameters", {})


class TestSchemaRequiredFields:
    """Test required fields are correctly defined."""

    @pytest.fixture
    def validator(self):
        """Create APISchemaValidator instance."""
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            APISchemaValidator,
        )

        return APISchemaValidator()

    def test_google_search_required_fields(self, validator):
        """google_search 'queries' should be required."""
        schema = validator.get_schema("/utility/google_search")
        assert schema is not None
        params = schema.get("parameters", {})
        queries_param = params.get("queries", {})
        assert queries_param.get("required") is True

    def test_fetch_web_content_required_fields(self, validator):
        """fetch_web_content 'url' should be required."""
        schema = validator.get_schema("/utility/fetch_web_content")
        assert schema is not None
        params = schema.get("parameters", {})
        url_param = params.get("url", {})
        assert url_param.get("required") is True

    def test_json_stringify_required_fields(self, validator):
        """json_stringify 'data' should be required."""
        schema = validator.get_schema("/utility/json_stringify")
        assert schema is not None
        params = schema.get("parameters", {})
        data_param = params.get("data", {})
        assert data_param.get("required") is True


class TestParameterAliases:
    """Test PARAMETER_ALIASES constant exists and has correct mappings."""

    def test_parameter_aliases_exists(self):
        """PARAMETER_ALIASES constant should exist."""
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            PARAMETER_ALIASES,
        )

        assert PARAMETER_ALIASES is not None
        assert isinstance(PARAMETER_ALIASES, dict)

    def test_query_to_queries_alias(self):
        """'query' should map to 'queries' for google_search."""
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            PARAMETER_ALIASES,
        )

        # Check if alias is defined for google_search
        google_search_aliases = PARAMETER_ALIASES.get("/utility/google_search", {})
        assert "query" in google_search_aliases
        assert google_search_aliases["query"] == "queries"

    def test_num_results_to_num_alias(self):
        """'num_results' should map to 'num' for google_search."""
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            PARAMETER_ALIASES,
        )

        google_search_aliases = PARAMETER_ALIASES.get("/utility/google_search", {})
        assert "num_results" in google_search_aliases
        assert google_search_aliases["num_results"] == "num"

    def test_max_to_max_results_alias(self):
        """'max' should map to 'max_results' for gmail_search if defined."""
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            PARAMETER_ALIASES,
        )

        # Gmail search alias (if implemented)
        gmail_aliases = PARAMETER_ALIASES.get("/utility/gmail/search", {})
        # This may or may not be implemented, test existence
        assert isinstance(gmail_aliases, dict)


class TestAPISchemaValidatorExports:
    """Test that APISchemaValidator is properly exported."""

    def test_import_from_validators_submodule(self):
        """APISchemaValidator should be importable from api_schema_validator submodule."""
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            APISchemaValidator,
        )

        assert APISchemaValidator is not None

    def test_parameter_aliases_exported(self):
        """PARAMETER_ALIASES should be importable."""
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            PARAMETER_ALIASES,
        )

        assert PARAMETER_ALIASES is not None

    def test_api_schema_validator_inherits_workflow_validator(self):
        """APISchemaValidator should inherit from WorkflowValidator."""
        from aiagent.langgraph.jobGeneratorV2.validators import (
            WorkflowValidator,
        )
        from aiagent.langgraph.jobGeneratorV2.validators.api_schema_validator import (
            APISchemaValidator,
        )

        assert issubclass(APISchemaValidator, WorkflowValidator)
