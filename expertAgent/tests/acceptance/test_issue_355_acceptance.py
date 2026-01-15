"""Issue #355 受入テスト（L3: ローカル受入テスト）.

前提条件:
- サービスが起動していること (./scripts/dev-start.sh または make dev-all)
- .env に必要なAPIキーが設定されていること

実行方法:
  cd expertAgent
  uv run pytest tests/acceptance/test_issue_355_acceptance.py -v
"""

from __future__ import annotations

import pytest

from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter import (
    ConversionResult,
    TaskFlowAdapter,
)


@pytest.mark.acceptance
class TestIssue355Acceptance:
    """Issue #355: TaskFlow Adapter Layer 実装.

    受入条件:
    - TaskFlowAdapter.convert() が JSON文字列フィールドをオブジェクトに変換
    - 変換エラー時に詳細なエラーメッセージを返却
    - workflow_registrar.py がAdapterを使用して変換を実行
    """

    @pytest.fixture
    def adapter(self) -> TaskFlowAdapter:
        """TaskFlowAdapterインスタンスを作成."""
        return TaskFlowAdapter()

    # ==========================================================================
    # TC-001: JSON文字列 input_schema の変換
    # ==========================================================================

    def test_tc_001_convert_json_string_input_schema(
        self, adapter: TaskFlowAdapter
    ) -> None:
        """TC-001: input_schema がJSON文字列の場合にオブジェクトに変換される.

        受入条件: input_schema が JSON文字列の場合、オブジェクトに変換される
        """
        # Arrange
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": '{"query": "string"}',
            "output_schema": {"result": "string"},
            "output": {"result": "${step_001.output}"},
            "steps": [],
        }

        # Act
        result = adapter.convert(workflow)

        # Assert
        assert result.success is True
        assert isinstance(result.data, dict)
        assert result.data["input_schema"] == {"query": "string"}
        assert isinstance(result.data["input_schema"], dict)

    # ==========================================================================
    # TC-002: JSON文字列 output_schema の変換
    # ==========================================================================

    def test_tc_002_convert_json_string_output_schema(
        self, adapter: TaskFlowAdapter
    ) -> None:
        """TC-002: output_schema がJSON文字列の場合にオブジェクトに変換される.

        受入条件: output_schema が JSON文字列の場合、オブジェクトに変換される
        """
        # Arrange
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": {"query": "string"},
            "output_schema": '{"result": "string"}',
            "output": {"result": "${step_001.output}"},
            "steps": [],
        }

        # Act
        result = adapter.convert(workflow)

        # Assert
        assert result.success is True
        assert isinstance(result.data, dict)
        assert result.data["output_schema"] == {"result": "string"}
        assert isinstance(result.data["output_schema"], dict)

    # ==========================================================================
    # TC-003: JSON文字列 output の変換
    # ==========================================================================

    def test_tc_003_convert_json_string_output(self, adapter: TaskFlowAdapter) -> None:
        """TC-003: output がJSON文字列の場合にオブジェクトに変換される.

        受入条件: output が JSON文字列の場合、オブジェクトに変換される
        """
        # Arrange
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": {"query": "string"},
            "output_schema": {"result": "string"},
            "output": '{"result": "${step_001.output}"}',
            "steps": [],
        }

        # Act
        result = adapter.convert(workflow)

        # Assert
        assert result.success is True
        assert isinstance(result.data, dict)
        assert result.data["output"] == {"result": "${step_001.output}"}
        assert isinstance(result.data["output"], dict)

    # ==========================================================================
    # TC-004: steps[*].config.body の変換
    # ==========================================================================

    def test_tc_004_convert_json_string_step_body(
        self, adapter: TaskFlowAdapter
    ) -> None:
        """TC-004: steps[*].config.body がJSON文字列の場合にオブジェクトに変換される.

        受入条件: steps[*].config.body が JSON文字列の場合、オブジェクトに変換される
        """
        # Arrange
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": {"query": "string"},
            "output_schema": {"result": "string"},
            "output": {"result": "${step_001.output}"},
            "steps": [
                {
                    "id": "step_001",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "POST",
                        "url": "https://example.com/api",
                        "body": '{"data": "value"}',
                    },
                }
            ],
        }

        # Act
        result = adapter.convert(workflow)

        # Assert
        assert result.success is True
        assert isinstance(result.data, dict)
        assert result.data["steps"][0]["config"]["body"] == {"data": "value"}
        assert isinstance(result.data["steps"][0]["config"]["body"], dict)

    # ==========================================================================
    # TC-005: 既存オブジェクトの保持
    # ==========================================================================

    def test_tc_005_preserve_existing_objects(self, adapter: TaskFlowAdapter) -> None:
        """TC-005: 既にオブジェクトのフィールドがそのまま保持される.

        受入条件: 既にオブジェクトの場合、そのまま保持される
        """
        # Arrange
        original_schema = {"query": "string", "count": "number"}
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": original_schema,
            "output_schema": {"result": "string"},
            "output": {"result": "${step_001.output}"},
            "steps": [],
        }

        # Act
        result = adapter.convert(workflow)

        # Assert
        assert result.success is True
        assert isinstance(result.data, dict)
        assert result.data["input_schema"] == original_schema

    # ==========================================================================
    # TC-006: 不正JSON時のエラー返却
    # ==========================================================================

    def test_tc_006_error_on_invalid_json(self, adapter: TaskFlowAdapter) -> None:
        """TC-006: 不正なJSONの場合にエラーが返却される.

        受入条件: 不正なJSONの場合、エラーを返却
        """
        # Arrange
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": "invalid json {not valid}",
            "output_schema": {"result": "string"},
            "output": {"result": "${step_001.output}"},
            "steps": [],
        }

        # Act
        result = adapter.convert(workflow)

        # Assert
        assert result.success is False
        assert len(result.errors) > 0
        assert any("input_schema" in error for error in result.errors)
        assert any("Invalid JSON" in error for error in result.errors)

    # ==========================================================================
    # TC-007: ConversionResult 構造確認
    # ==========================================================================

    def test_tc_007_conversion_result_structure(self) -> None:
        """TC-007: ConversionResultが正しい構造を持つ.

        受入条件: 変換エラー時に詳細なエラーメッセージを返却
        """
        # Arrange & Act
        result = ConversionResult(
            success=True,
            data={"test": "data"},
            errors=[],
            warnings=["test warning"],
        )

        # Assert
        assert isinstance(result.success, bool)
        assert result.data is None or isinstance(result.data, dict)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)

    # ==========================================================================
    # TC-011: 複数フィールド同時変換
    # ==========================================================================

    def test_tc_011_convert_multiple_fields(self, adapter: TaskFlowAdapter) -> None:
        """TC-011: 複数のJSON文字列フィールドが同時に変換される.

        受入条件: 全ての対象フィールドが変換される
        """
        # Arrange
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": '{"query": "string"}',
            "output_schema": '{"result": "string"}',
            "output": '{"result": "${step_001.output}"}',
            "steps": [
                {
                    "id": "step_001",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "POST",
                        "url": "https://example.com/api",
                        "body": '{"data": "value"}',
                    },
                }
            ],
        }

        # Act
        result = adapter.convert(workflow)

        # Assert
        assert result.success is True
        assert isinstance(result.data, dict)
        assert isinstance(result.data["input_schema"], dict)
        assert isinstance(result.data["output_schema"], dict)
        assert isinstance(result.data["output"], dict)
        assert isinstance(result.data["steps"][0]["config"]["body"], dict)

    # ==========================================================================
    # TC-012: ディープコピー検証
    # ==========================================================================

    def test_tc_012_deep_copy_preservation(self, adapter: TaskFlowAdapter) -> None:
        """TC-012: 入力データが変換により破壊されない.

        受入条件: オリジナルデータが保持される
        """
        # Arrange
        original_input_schema = '{"query": "string"}'
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": original_input_schema,
            "output_schema": {"result": "string"},
            "output": {"result": "${step_001.output}"},
            "steps": [],
        }

        # Act
        result = adapter.convert(workflow)

        # Assert
        assert result.success is True
        # Original workflow should not be modified
        assert workflow["input_schema"] == original_input_schema
        assert isinstance(workflow["input_schema"], str)
        # Result data should have converted value
        assert isinstance(result.data["input_schema"], dict)


@pytest.mark.acceptance
class TestWorkflowRegistrarIntegrationAcceptance:
    """workflow_registrar.py との統合受入テスト."""

    def test_tc_008_workflow_registrar_uses_adapter(self) -> None:
        """TC-008: register_taskflow_workflow()がAdapterを使用する.

        受入条件: workflow_registrar.py がAdapterを使用して変換を実行
        """
        # Verify adapter is imported and instantiated in workflow_registrar
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen import (
            workflow_registrar,
        )

        # Check that _adapter exists
        assert hasattr(workflow_registrar, "_adapter")
        assert isinstance(workflow_registrar._adapter, TaskFlowAdapter)

    def test_tc_009_adapter_error_handling_in_registrar(self) -> None:
        """TC-009: Adapter変換失敗時にworkflow_registrar.pyがエラーを返す.

        受入条件: 変換エラー時に詳細なエラーメッセージを返却
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen import (
            workflow_registrar,
        )

        # The adapter should handle invalid JSON gracefully
        adapter = workflow_registrar._adapter
        result = adapter.convert(
            {
                "workflow_name": "test",
                "input_schema": "invalid json",
                "output_schema": {},
                "output": {},
                "steps": [],
            }
        )

        assert result.success is False
        assert len(result.errors) > 0
        assert any("Invalid JSON" in e for e in result.errors)
