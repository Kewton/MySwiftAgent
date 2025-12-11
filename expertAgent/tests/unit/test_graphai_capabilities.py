"""Unit tests for graphai_capabilities module - Issue #270.

Tests for:
1. ExpertAgentAPI Dataclass extension (method, request_schema, response_schema)
2. Schema normalization (output_schema -> response_schema)
3. Schema validation
4. Loader functions update
"""

import pytest

from aiagent.langgraph.jobTaskGeneratorAgents.utils.graphai_capabilities import (
    EXPERT_AGENT_APIS,
    VALID_SCHEMA_TYPES,
    ExpertAgentAPI,
    SchemaValidationError,
    _normalize_schema_keys,
    convert_to_json_schema,
    get_api_by_name,
    validate_api_schemas,
    validate_schema,
)


class TestExpertAgentAPIDataclass:
    """Test ExpertAgentAPI dataclass extension."""

    def test_dataclass_has_method_field(self) -> None:
        """Test that ExpertAgentAPI has method field with default POST."""
        api = ExpertAgentAPI(
            name="Test API",
            endpoint="/v1/test",
            category="utility",
            description="Test description",
            use_cases=["test"],
        )
        assert api.method == "POST"

    def test_dataclass_has_request_schema_field(self) -> None:
        """Test that ExpertAgentAPI has request_schema field."""
        api = ExpertAgentAPI(
            name="Test API",
            endpoint="/v1/test",
            category="utility",
            description="Test description",
            use_cases=["test"],
            request_schema={"query": {"type": "string", "required": True}},
        )
        assert api.request_schema is not None
        assert "query" in api.request_schema

    def test_dataclass_has_response_schema_field(self) -> None:
        """Test that ExpertAgentAPI has response_schema field."""
        api = ExpertAgentAPI(
            name="Test API",
            endpoint="/v1/test",
            category="utility",
            description="Test description",
            use_cases=["test"],
            response_schema={"result": {"type": "string"}},
        )
        assert api.response_schema is not None
        assert "result" in api.response_schema

    def test_dataclass_optional_fields_default_none(self) -> None:
        """Test that optional schema fields default to None."""
        api = ExpertAgentAPI(
            name="Test API",
            endpoint="/v1/test",
            category="utility",
            description="Test description",
            use_cases=["test"],
        )
        assert api.request_schema is None
        assert api.response_schema is None


class TestSchemaNormalization:
    """Test output_schema -> response_schema normalization (SF-01)."""

    def test_normalize_output_schema_to_response_schema(self) -> None:
        """Test that output_schema is converted to response_schema."""
        api_data = {
            "name": "Test API",
            "endpoint": "/v1/test",
            "output_schema": {"file_id": {"type": "string"}},
        }
        normalized = _normalize_schema_keys(api_data)
        assert "response_schema" in normalized
        assert "output_schema" not in normalized
        assert normalized["response_schema"]["file_id"]["type"] == "string"

    def test_normalize_preserves_response_schema_if_both_exist(self) -> None:
        """Test that response_schema takes precedence over output_schema."""
        api_data = {
            "name": "Test API",
            "endpoint": "/v1/test",
            "output_schema": {"old": {"type": "string"}},
            "response_schema": {"new": {"type": "string"}},
        }
        normalized = _normalize_schema_keys(api_data)
        assert "response_schema" in normalized
        assert "output_schema" not in normalized
        # response_schema should be preserved
        assert "new" in normalized["response_schema"]

    def test_normalize_no_change_if_no_output_schema(self) -> None:
        """Test that normalization is no-op if no output_schema."""
        api_data = {
            "name": "Test API",
            "endpoint": "/v1/test",
            "response_schema": {"result": {"type": "string"}},
        }
        normalized = _normalize_schema_keys(api_data.copy())
        assert "response_schema" in normalized
        assert normalized["response_schema"]["result"]["type"] == "string"


class TestSchemaValidation:
    """Test schema validation (SF-02)."""

    def test_valid_schema_types_defined(self) -> None:
        """Test that VALID_SCHEMA_TYPES contains expected types."""
        expected_types = {"string", "integer", "number", "boolean", "array", "object"}
        assert VALID_SCHEMA_TYPES == expected_types

    def test_validate_schema_raises_on_missing_type(self) -> None:
        """Test that validation raises error when type is missing."""
        schema = {"field_without_type": {"description": "Missing type"}}
        with pytest.raises(SchemaValidationError) as exc_info:
            validate_schema(schema, "Test API", "request")
        assert "missing required 'type' attribute" in str(exc_info.value)

    def test_validate_schema_raises_on_invalid_type(self) -> None:
        """Test that validation raises error for invalid type name."""
        schema = {"invalid_field": {"type": "invalid_type"}}
        with pytest.raises(SchemaValidationError) as exc_info:
            validate_schema(schema, "Test API", "request")
        assert "invalid type 'invalid_type'" in str(exc_info.value)

    def test_validate_schema_warns_on_array_without_items(self) -> None:
        """Test that validation warns when array type missing items."""
        schema = {"array_field": {"type": "array"}}
        warnings = validate_schema(schema, "Test API", "request")
        assert len(warnings) == 1
        assert "missing 'items' definition" in warnings[0]

    def test_validate_schema_warns_on_object_without_properties(self) -> None:
        """Test that validation warns when object type missing properties."""
        schema = {"object_field": {"type": "object"}}
        warnings = validate_schema(schema, "Test API", "request")
        assert len(warnings) == 1
        assert "missing 'properties' definition" in warnings[0]

    def test_validate_schema_warns_on_non_boolean_required(self) -> None:
        """Test that validation warns when required is not boolean."""
        schema = {"field": {"type": "string", "required": "yes"}}
        warnings = validate_schema(schema, "Test API", "request")
        assert len(warnings) == 1
        assert "non-boolean 'required' value" in warnings[0]

    def test_validate_schema_passes_for_valid_schema(self) -> None:
        """Test that validation passes for valid schema."""
        schema = {
            "query": {"type": "string", "description": "Search query", "required": True},
            "max_results": {"type": "integer", "default": 10},
            "filters": {
                "type": "object",
                "properties": {"status": {"type": "string"}},
            },
            "tags": {"type": "array", "items": {"type": "string"}},
        }
        warnings = validate_schema(schema, "Test API", "request")
        assert len(warnings) == 0

    def test_validate_api_schemas_validates_both_schemas(self) -> None:
        """Test that validate_api_schemas checks both request and response."""
        api = {
            "name": "Test API",
            "request_schema": {"query": {"type": "string"}},
            "response_schema": {"result": {"type": "array"}},  # Missing items
        }
        warnings = validate_api_schemas(api)
        assert len(warnings) == 1
        assert "response_schema" in warnings[0]


class TestConvertToJsonSchema:
    """Test YAML schema to JSON Schema conversion."""

    def test_convert_simple_schema(self) -> None:
        """Test converting simple YAML schema to JSON Schema."""
        yaml_schema = {
            "query": {"type": "string", "description": "Search query", "required": True},
            "max_results": {
                "type": "integer",
                "description": "Max results",
                "default": 10,
            },
        }
        json_schema = convert_to_json_schema(yaml_schema)

        assert json_schema["type"] == "object"
        assert "properties" in json_schema
        assert "query" in json_schema["properties"]
        assert json_schema["properties"]["query"]["type"] == "string"
        assert "required" in json_schema
        assert "query" in json_schema["required"]
        assert json_schema["properties"]["max_results"]["default"] == 10

    def test_convert_empty_schema(self) -> None:
        """Test converting empty schema."""
        yaml_schema: dict = {}
        json_schema = convert_to_json_schema(yaml_schema)

        assert json_schema["type"] == "object"
        assert json_schema["properties"] == {}
        assert json_schema["required"] == []


class TestYAMLLoading:
    """Test YAML loading with new schema fields."""

    def test_expert_agent_apis_loaded(self) -> None:
        """Test that EXPERT_AGENT_APIS is loaded and non-empty."""
        assert len(EXPERT_AGENT_APIS) > 0

    def test_gmail_search_api_has_request_schema(self) -> None:
        """Test that Gmail Search API has request_schema."""
        gmail_search = get_api_by_name("Gmail検索")
        assert gmail_search is not None
        assert gmail_search.request_schema is not None
        assert "query" in gmail_search.request_schema

    def test_gmail_search_api_has_response_schema(self) -> None:
        """Test that Gmail Search API has response_schema."""
        gmail_search = get_api_by_name("Gmail検索")
        assert gmail_search is not None
        assert gmail_search.response_schema is not None
        assert "messages" in gmail_search.response_schema

    def test_tts_drive_api_has_response_schema(self) -> None:
        """Test that TTS Drive API has response_schema (migrated from output_schema)."""
        tts_drive = get_api_by_name("Text-to-Speech + Google Drive")
        assert tts_drive is not None
        assert tts_drive.response_schema is not None
        assert "file_id" in tts_drive.response_schema

    def test_utility_apis_have_method_field(self) -> None:
        """Test that utility APIs have method field."""
        gmail_search = get_api_by_name("Gmail検索")
        assert gmail_search is not None
        assert gmail_search.method == "POST"

    def test_at_least_10_apis_have_schemas(self) -> None:
        """Test that at least 10 APIs have schemas (acceptance criteria)."""
        apis_with_schema = [
            api
            for api in EXPERT_AGENT_APIS
            if api.request_schema is not None or api.response_schema is not None
        ]
        assert len(apis_with_schema) >= 10


class TestAPISchemaContents:
    """Test specific API schema contents for accuracy."""

    def test_gmail_search_request_schema_fields(self) -> None:
        """Test Gmail Search request schema has correct fields."""
        gmail_search = get_api_by_name("Gmail検索")
        assert gmail_search is not None
        req_schema = gmail_search.request_schema
        assert req_schema is not None

        # Check required fields
        assert "query" in req_schema
        assert req_schema["query"]["type"] == "string"
        assert req_schema["query"].get("required") is True

        # Check optional fields
        assert "max_results" in req_schema
        assert req_schema["max_results"]["type"] == "integer"

    def test_gmail_send_request_schema_fields(self) -> None:
        """Test Gmail Send request schema has correct fields."""
        gmail_send = get_api_by_name("Gmail送信")
        assert gmail_send is not None
        req_schema = gmail_send.request_schema
        assert req_schema is not None

        assert "to" in req_schema
        assert "subject" in req_schema
        assert "body" in req_schema

    def test_google_drive_upload_request_schema(self) -> None:
        """Test Google Drive Upload request schema."""
        drive_upload = get_api_by_name("Google Drive Upload")
        assert drive_upload is not None
        req_schema = drive_upload.request_schema
        assert req_schema is not None

        assert "file_path" in req_schema
        assert req_schema["file_path"]["type"] == "string"

    def test_text_to_speech_request_schema(self) -> None:
        """Test TTS request schema."""
        tts = get_api_by_name("Text-to-Speech（Base64）")
        assert tts is not None
        req_schema = tts.request_schema
        assert req_schema is not None

        assert "text" in req_schema
        assert "model" in req_schema
        assert "voice" in req_schema

    def test_google_search_request_schema(self) -> None:
        """Test Google Search request schema."""
        google_search = get_api_by_name("Google検索")
        assert google_search is not None
        req_schema = google_search.request_schema
        assert req_schema is not None

        assert "queries" in req_schema
        assert req_schema["queries"]["type"] == "array"

    def test_json_output_agent_request_schema(self) -> None:
        """Test JSON Output Agent request schema."""
        json_output = get_api_by_name("JSON Output Agent")
        assert json_output is not None
        req_schema = json_output.request_schema
        assert req_schema is not None

        assert "user_input" in req_schema
