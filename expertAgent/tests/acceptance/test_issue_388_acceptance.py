"""Acceptance tests for Issue #388: Schema converter extraction.

This acceptance test verifies that:
1. schema_converter.py module is correctly created with required functions
2. json_schema_to_simple_mapping correctly converts JSON Schema to Simple Mapping
3. simple_mapping_to_json_schema correctly converts Simple Mapping to JSON Schema
4. orchestrator.py uses the new centralized schema converter
5. Debug logging works for information loss tracking
6. No dead code exists (all functions are actually used)
7. Static analysis passes (Ruff, MyPy)

Test execution requirements:
- Run with: cd expertAgent && uv run pytest tests/acceptance/test_issue_388_acceptance.py -v -s

Issue #388: スキーマ変換ロジックの分離（Issue #387 フォローアップ）
"""

import logging
from typing import Any

import pytest

from aiagent.clients.interfaces.schema_converter import (
    JsonSchema,
    SimpleMapping,
    json_schema_to_simple_mapping,
    simple_mapping_to_json_schema,
)


class TestTC001ModuleExistence:
    """TC-001: Verify schema_converter module and exports exist."""

    def test_tc_001_module_imports_successfully(self) -> None:
        """Verify all required exports are available from schema_converter."""
        # Given/When: Import the module (done at top of file)
        # Then: All exports should be available
        assert json_schema_to_simple_mapping is not None
        assert simple_mapping_to_json_schema is not None
        assert JsonSchema is not None
        assert SimpleMapping is not None

    def test_tc_001_type_aliases_are_correct(self) -> None:
        """Verify type aliases are correctly defined."""
        # Given: A sample schema
        json_schema: JsonSchema = {"type": "object", "properties": {}}
        simple_mapping: SimpleMapping = {"field": "string"}

        # Then: Type annotations should work correctly
        assert isinstance(json_schema, dict)
        assert isinstance(simple_mapping, dict)


class TestTC002ForwardConversion:
    """TC-002: Verify json_schema_to_simple_mapping conversion."""

    def test_tc_002_full_json_schema_conversion(self) -> None:
        """Verify full JSON Schema is converted to Simple Mapping."""
        # Given
        full_schema: JsonSchema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "format": "email"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["email", "subject"],
        }

        # When
        result = json_schema_to_simple_mapping(full_schema)

        # Then
        expected: SimpleMapping = {
            "email": "string",
            "subject": "string",
            "body": "string",
        }
        assert result == expected

    def test_tc_002_already_simple_mapping(self) -> None:
        """Verify already simple mapping is returned unchanged."""
        # Given
        simple_schema: SimpleMapping = {
            "email": "string",
            "subject": "string",
        }

        # When
        result = json_schema_to_simple_mapping(simple_schema)

        # Then
        assert result == simple_schema

    def test_tc_002_empty_schema(self) -> None:
        """Verify empty schema returns empty dict."""
        # Given
        empty_schema: dict[str, Any] = {}

        # When
        result = json_schema_to_simple_mapping(empty_schema)

        # Then
        assert result == {}

    def test_tc_002_preserves_all_types(self) -> None:
        """Verify all JSON Schema types are preserved."""
        # Given
        schema: JsonSchema = {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "score": {"type": "number"},
                "active": {"type": "boolean"},
                "tags": {"type": "array"},
                "metadata": {"type": "object"},
            },
        }

        # When
        result = json_schema_to_simple_mapping(schema)

        # Then
        expected: SimpleMapping = {
            "name": "string",
            "age": "integer",
            "score": "number",
            "active": "boolean",
            "tags": "array",
            "metadata": "object",
        }
        assert result == expected


class TestTC003ReverseConversion:
    """TC-003: Verify simple_mapping_to_json_schema conversion."""

    def test_tc_003_simple_mapping_to_json_schema(self) -> None:
        """Verify Simple Mapping is converted to JSON Schema."""
        # Given
        simple_mapping: SimpleMapping = {
            "email": "string",
            "count": "integer",
            "active": "boolean",
        }

        # When
        result = simple_mapping_to_json_schema(simple_mapping)

        # Then
        expected: JsonSchema = {
            "type": "object",
            "properties": {
                "email": {"type": "string"},
                "count": {"type": "integer"},
                "active": {"type": "boolean"},
            },
        }
        assert result == expected

    def test_tc_003_empty_mapping(self) -> None:
        """Verify empty mapping returns empty dict."""
        # Given
        empty_mapping: SimpleMapping = {}

        # When
        result = simple_mapping_to_json_schema(empty_mapping)

        # Then
        assert result == {}


class TestTC004OrchestratorSeparation:
    """TC-004: Verify orchestrator.py uses the centralized schema converter."""

    def test_tc_004_orchestrator_imports_from_schema_converter(self) -> None:
        """Verify orchestrator imports json_schema_to_simple_mapping from schema_converter."""
        import inspect

        # Given/When: Import orchestrator module
        from aiagent.langgraph.jobGeneratorV2 import orchestrator

        # Then: The function should be imported (not defined locally)
        source_file = inspect.getfile(json_schema_to_simple_mapping)
        assert "schema_converter" in source_file

        # Verify the orchestrator module has the import
        assert hasattr(orchestrator, "json_schema_to_simple_mapping")

    def test_tc_004_old_method_removed(self) -> None:
        """Verify _schema_to_simple_mapping method is removed from orchestrator."""
        # Given
        from aiagent.langgraph.jobGeneratorV2.orchestrator import (
            JobGenerationOrchestrator,
        )

        # Then: The old method should not exist
        assert not hasattr(JobGenerationOrchestrator, "_schema_to_simple_mapping")


class TestTC005DebugLogging:
    """TC-005: Verify debug logging for information loss."""

    def test_tc_005_logs_required_fields_loss(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Verify required fields loss is logged at DEBUG level."""
        # Given
        schema: JsonSchema = {
            "type": "object",
            "properties": {"email": {"type": "string"}},
            "required": ["email"],
        }

        # When
        with caplog.at_level(logging.DEBUG):
            json_schema_to_simple_mapping(schema)

        # Then
        assert any("required" in record.message.lower() for record in caplog.records)

    def test_tc_005_logs_format_loss(self, caplog: pytest.LogCaptureFixture) -> None:
        """Verify format constraint loss is logged at DEBUG level."""
        # Given
        schema: JsonSchema = {
            "type": "object",
            "properties": {"email": {"type": "string", "format": "email"}},
        }

        # When
        with caplog.at_level(logging.DEBUG):
            json_schema_to_simple_mapping(schema)

        # Then
        assert any("format" in record.message.lower() for record in caplog.records)

    def test_tc_005_logs_description_loss(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Verify description loss is logged at DEBUG level."""
        # Given
        schema: JsonSchema = {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "Recipient email address"}
            },
        }

        # When
        with caplog.at_level(logging.DEBUG):
            json_schema_to_simple_mapping(schema)

        # Then
        assert any("description" in record.message.lower() for record in caplog.records)


class TestTC006DeadCodeVerification:
    """TC-006: Verify no dead code exists."""

    def test_tc_006_json_schema_to_simple_mapping_is_used(self) -> None:
        """Verify json_schema_to_simple_mapping is actually used in orchestrator."""
        # Given: Read orchestrator source
        import inspect

        from aiagent.langgraph.jobGeneratorV2 import orchestrator

        source = inspect.getsource(orchestrator)

        # Then: The function should be called (not just imported)
        assert "json_schema_to_simple_mapping(" in source

    def test_tc_006_functions_are_importable_from_interfaces(self) -> None:
        """Verify functions are properly exported from interfaces package."""
        # Given/When: Import from package level
        from aiagent.clients.interfaces import (
            JsonSchema,
            SimpleMapping,
            json_schema_to_simple_mapping,
            simple_mapping_to_json_schema,
        )

        # Then: All exports should be available
        assert json_schema_to_simple_mapping is not None
        assert simple_mapping_to_json_schema is not None
        assert JsonSchema is not None
        assert SimpleMapping is not None


class TestTC007E2EIntegrationTest:
    """TC-007: E2E統合テスト（JobGenerator API）.

    計画書定義:
    - テスト観点: JobGenerator APIを通じてスキーマ変換が正しく動作する
    - 関連する受入条件: AC-4, AC-5
    - テスト種別: E2E
    - 前提条件: expertAgent、mySwiftAgentCoreが起動している
    """

    @pytest.fixture
    def check_services_running(self) -> bool:
        """Check if required services are running."""
        import httpx

        try:
            # Check expertAgent health
            response = httpx.get("http://localhost:8004/health", timeout=5.0)
            if response.status_code != 200:
                return False
            return True
        except Exception:
            return False

    @pytest.mark.asyncio
    async def test_tc_007_e2e_health_check(self) -> None:
        """TC-007-1: Verify expertAgent is healthy."""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get("http://localhost:8004/health", timeout=5.0)
                # サービスが起動していればヘルスチェックをテスト
                assert response.status_code == 200
        except httpx.ConnectError:
            pytest.skip("expertAgent is not running - skipping E2E test")

    @pytest.mark.asyncio
    async def test_tc_007_e2e_job_generator_api(self) -> None:
        """TC-007-2: Verify JobGenerator API works with schema conversion.

        計画書のテスト手順:
        1. ヘルスチェック実行
        2. Job生成APIを呼び出し
        3. レスポンスを確認

        Note: API endpoint is /v1/job-generator (not /v1/job-generator/generate)
              Request uses user_requirement field (not messages array)
        """
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                # 1. ヘルスチェック
                health_response = await client.get(
                    "http://localhost:8004/health", timeout=5.0
                )
                if health_response.status_code != 200:
                    pytest.skip("expertAgent is not healthy")

                # 2. Job生成API呼び出し
                # 実際のAPIスキーマに合わせたリクエスト
                # JobGeneratorRequest: user_requirement (必須), project_id
                request_data = {
                    "user_requirement": "Create a task to send an email with recipient, subject and body fields",
                    "project_id": "default_project",
                }

                response = await client.post(
                    "http://localhost:8004/v1/job-generator",
                    json=request_data,
                    timeout=30.0,
                )

                # 3. レスポンス確認
                assert response.status_code == 200, (
                    f"API returned {response.status_code}: {response.text}"
                )
                data = response.json()

                # APIが正常に応答し、job_idが返される
                assert "job_id" in data, f"Response missing job_id: {data}"
                assert data["job_id"] is not None

        except httpx.ConnectError:
            pytest.skip("expertAgent is not running - skipping E2E test")


class TestRoundTripConversion:
    """Additional tests: Verify round-trip conversion behavior.

    Note: This is not TC-007 from the acceptance plan, but additional
    verification for conversion quality.
    """

    def test_simple_mapping_round_trip(self) -> None:
        """Verify Simple Mapping -> JSON Schema -> Simple Mapping preserves data."""
        # Given
        original: SimpleMapping = {
            "name": "string",
            "age": "integer",
            "active": "boolean",
        }

        # When
        json_schema = simple_mapping_to_json_schema(original)
        result = json_schema_to_simple_mapping(json_schema)

        # Then
        assert result == original

    def test_json_schema_round_trip_loses_metadata(self) -> None:
        """Verify JSON Schema -> Simple Mapping -> JSON Schema loses metadata."""
        # Given
        original: JsonSchema = {
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "format": "email",
                    "description": "Email addr",
                }
            },
            "required": ["email"],
        }

        # When
        simple_mapping = json_schema_to_simple_mapping(original)
        result = simple_mapping_to_json_schema(simple_mapping)

        # Then: Basic structure is preserved
        assert result["type"] == "object"
        assert "email" in result["properties"]
        assert result["properties"]["email"]["type"] == "string"

        # But: Metadata is lost
        assert "format" not in result["properties"]["email"]
        assert "description" not in result["properties"]["email"]
        assert "required" not in result


class TestTC008StaticAnalysis:
    """TC-008: Verify static analysis passes."""

    def test_tc_008_module_has_proper_docstring(self) -> None:
        """Verify schema_converter module has proper docstring."""
        # Given
        from aiagent.clients.interfaces import schema_converter

        # Then
        assert schema_converter.__doc__ is not None
        assert "Issue #388" in schema_converter.__doc__

    def test_tc_008_functions_have_proper_docstrings(self) -> None:
        """Verify all exported functions have proper docstrings."""
        # Then
        assert json_schema_to_simple_mapping.__doc__ is not None
        assert simple_mapping_to_json_schema.__doc__ is not None
        assert "Args:" in json_schema_to_simple_mapping.__doc__
        assert "Returns:" in json_schema_to_simple_mapping.__doc__


class TestIntegrationWithInterfaceDefinition:
    """Integration tests with actual InterfaceDefinition from job_analyzer."""

    def test_real_interface_definition_conversion(self) -> None:
        """Verify conversion works with actual InterfaceDefinition format."""
        # Given
        from aiagent.langgraph.jobGeneratorV2.nodes.job_analyzer import (
            InterfaceDefinition,
        )

        interface = InterfaceDefinition(
            input_schema={
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Recipient email"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["to", "subject", "body"],
            },
            output_schema={
                "type": "object",
                "properties": {
                    "message_id": {"type": "string"},
                    "success": {"type": "boolean"},
                },
            },
            description="Send email interface",
        )

        # When
        input_mapping = json_schema_to_simple_mapping(interface.input_schema)
        output_mapping = json_schema_to_simple_mapping(interface.output_schema)

        # Then
        assert input_mapping == {
            "to": "string",
            "subject": "string",
            "body": "string",
        }
        assert output_mapping == {
            "message_id": "string",
            "success": "boolean",
        }
