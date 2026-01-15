"""Issue #356 受入テスト（L3: ローカル受入テスト）.

前提条件:
- サービスが起動していること (./scripts/dev-start.sh または make dev-all)
- .env に必要なAPIキーが設定されていること

実行方法:
  cd expertAgent
  uv run pytest tests/acceptance/test_issue_356_acceptance.py -v
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter import (
        TaskFlowAdapter,
    )


@pytest.mark.acceptance
class TestIssue356Acceptance:
    """Issue #356: TaskFlow Contract Tests 実装.

    受入条件:
    - JSON文字列フィールド変換の契約テストが存在
    - Pydanticモデル出力互換性の契約テストが存在
    - GraphAiServer検証の契約テスト（integration mark）が存在
    - 契約テストが全てパス
    - テストフィクスチャが3種類以上
    """

    CONTRACT_TESTS_DIR = Path(__file__).parent.parent / "contract"
    FIXTURES_DIR = CONTRACT_TESTS_DIR / "fixtures" / "valid_workflows"

    # ==========================================================================
    # TC-001: Contract Testsディレクトリ構造確認
    # ==========================================================================

    def test_tc_001_contract_tests_directory_structure_exists(self) -> None:
        """TC-001: Contract Testsディレクトリ構造が正しく存在する.

        受入条件: tests/contract/ ディレクトリ構造が存在
        """
        # Assert directory exists
        assert self.CONTRACT_TESTS_DIR.exists(), (
            f"Contract tests directory not found: {self.CONTRACT_TESTS_DIR}"
        )

        # Assert required files exist
        required_files = [
            "__init__.py",
            "conftest.py",
            "test_taskflow_schema_contract.py",
        ]
        for filename in required_files:
            filepath = self.CONTRACT_TESTS_DIR / filename
            assert filepath.exists(), f"Required file not found: {filepath}"

        # Assert fixtures directory exists
        assert self.FIXTURES_DIR.exists(), (
            f"Fixtures directory not found: {self.FIXTURES_DIR}"
        )

    # ==========================================================================
    # TC-002: test_json_string_fields_are_converted が存在しパス
    # ==========================================================================

    def test_tc_002_json_string_fields_test_exists(self) -> None:
        """TC-002: test_json_string_fields_are_converted テストが存在する.

        受入条件: test_json_string_fields_are_converted が存在しパス
        """
        test_file = self.CONTRACT_TESTS_DIR / "test_taskflow_schema_contract.py"
        content = test_file.read_text()

        assert "def test_json_string_fields_are_converted" in content, (
            "test_json_string_fields_are_converted method not found in test file"
        )

    def test_tc_002_json_string_fields_test_passes(self) -> None:
        """TC-002: JSON文字列フィールド変換の契約テストがパスする.

        受入条件: test_json_string_fields_are_converted がパス
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter import (
            TaskFlowAdapter,
        )

        adapter = TaskFlowAdapter()
        workflow = {
            "workflow_name": "test_workflow",
            "input_schema": '{"query": "string"}',
            "output_schema": '{"result": "string"}',
            "output": '{"result": "${step_001.output}"}',
            "steps": [],
        }

        result = adapter.convert(workflow)

        assert result.success is True
        assert isinstance(result.data, dict)
        assert isinstance(result.data["input_schema"], dict)
        assert isinstance(result.data["output_schema"], dict)
        assert isinstance(result.data["output"], dict)

    # ==========================================================================
    # TC-003: test_pydantic_model_output_is_convertible が存在しパス
    # ==========================================================================

    def test_tc_003_pydantic_model_test_exists(self) -> None:
        """TC-003: test_pydantic_model_output_is_convertible テストが存在する.

        受入条件: test_pydantic_model_output_is_convertible が存在しパス
        """
        test_file = self.CONTRACT_TESTS_DIR / "test_taskflow_schema_contract.py"
        content = test_file.read_text()

        assert "def test_pydantic_model_output_is_convertible" in content, (
            "test_pydantic_model_output_is_convertible method not found in test file"
        )

    def test_tc_003_pydantic_model_test_passes(self) -> None:
        """TC-003: Pydanticモデル出力互換性の契約テストがパスする.

        受入条件: test_pydantic_model_output_is_convertible がパス
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter import (
            TaskFlowAdapter,
        )

        adapter = TaskFlowAdapter()

        # Simulate Pydantic model output (dict with objects already)
        workflow = {
            "workflow_name": "pydantic_output_workflow",
            "input_schema": {"query": "string"},
            "output_schema": {"result": "string"},
            "output": {"result": "${step_001.output}"},
            "steps": [],
        }

        result = adapter.convert(workflow)

        assert result.success is True
        assert isinstance(result.data, dict)
        # Objects should be preserved as-is
        assert result.data["input_schema"] == {"query": "string"}
        assert result.data["output_schema"] == {"result": "string"}

    # ==========================================================================
    # TC-004: test_converted_workflow_passes_graphai_validation が存在
    # ==========================================================================

    def test_tc_004_graphai_validation_test_exists(self) -> None:
        """TC-004: test_converted_workflow_passes_graphai_validation テストが存在.

        受入条件: test_converted_workflow_passes_graphai_validation が存在
        """
        test_file = self.CONTRACT_TESTS_DIR / "test_taskflow_schema_contract.py"
        content = test_file.read_text()

        assert "def test_converted_workflow_passes_graphai_validation" in content, (
            "test_converted_workflow_passes_graphai_validation method not found"
        )

    def test_tc_004_graphai_validation_test_has_integration_mark(self) -> None:
        """TC-004: GraphAiServer検証テストにintegrationマーカーが付与されている.

        受入条件: GraphAiServer検証の契約テスト（integration mark）が存在
        """
        test_file = self.CONTRACT_TESTS_DIR / "test_taskflow_schema_contract.py"
        content = test_file.read_text()

        # Check for @pytest.mark.integration decorator
        assert "@pytest.mark.integration" in content, (
            "Integration marker not found in test file"
        )

    # ==========================================================================
    # TC-005: テストフィクスチャが3種類以上
    # ==========================================================================

    def test_tc_005_test_fixtures_exist(self) -> None:
        """TC-005: テストフィクスチャが3種類以上存在する.

        受入条件: テストフィクスチャが3種類以上
        """
        fixture_files = list(self.FIXTURES_DIR.glob("*.json"))

        assert len(fixture_files) >= 3, (
            f"Expected at least 3 fixture files, found {len(fixture_files)}: "
            f"{[f.name for f in fixture_files]}"
        )

    def test_tc_005_test_fixtures_are_valid_json(self) -> None:
        """TC-005: テストフィクスチャが有効なJSONである.

        受入条件: テストフィクスチャが有効なJSON
        """
        fixture_files = list(self.FIXTURES_DIR.glob("*.json"))

        for fixture_file in fixture_files:
            try:
                with open(fixture_file) as f:
                    data = json.load(f)
                assert isinstance(data, dict), f"Expected dict, got {type(data)}"
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in {fixture_file.name}: {e}")

    # ==========================================================================
    # TC-006: 全契約テストがパス
    # ==========================================================================

    def test_tc_006_all_contract_tests_pass(self) -> None:
        """TC-006: 全ての契約テストがパスする（unit tests only）.

        受入条件: 契約テストが全てパス

        Note: This test verifies that the contract test infrastructure is correct.
        The actual test execution is done via pytest directly.
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter import (
            TaskFlowAdapter,
        )

        adapter = TaskFlowAdapter()

        # Load and test all fixture workflows
        fixture_files = list(self.FIXTURES_DIR.glob("*.json"))

        for fixture_file in fixture_files:
            with open(fixture_file) as f:
                workflow = json.load(f)

            result = adapter.convert(workflow)

            assert result.success is True, (
                f"Fixture {fixture_file.name} conversion failed: {result.errors}"
            )

    # ==========================================================================
    # TC-007: CI/CDワークフロー設定確認
    # ==========================================================================

    def test_tc_007_cicd_workflow_exists(self) -> None:
        """TC-007: CI/CDワークフローファイルが存在する.

        受入条件: .github/workflows/contract-tests.yml が存在
        """
        project_root = Path(__file__).parent.parent.parent.parent
        workflow_file = project_root / ".github" / "workflows" / "contract-tests.yml"

        assert workflow_file.exists(), (
            f"CI/CD workflow file not found: {workflow_file}"
        )

    def test_tc_007_cicd_workflow_has_proper_triggers(self) -> None:
        """TC-007: CI/CDワークフローに適切なトリガーが設定されている.

        受入条件: 適切なパストリガーが設定されている
        """
        project_root = Path(__file__).parent.parent.parent.parent
        workflow_file = project_root / ".github" / "workflows" / "contract-tests.yml"

        content = workflow_file.read_text()

        # Check for path triggers related to schema files
        assert "paths:" in content, "Path triggers not found in workflow"
        assert "adapter" in content.lower() or "schema" in content.lower(), (
            "Schema or adapter path triggers not found"
        )

    # ==========================================================================
    # TC-008: TaskFlowAdapter統合確認
    # ==========================================================================

    def test_tc_008_taskflow_adapter_integration(self) -> None:
        """TC-008: Contract TestsがTaskFlowAdapterを正しく使用している.

        受入条件: TaskFlowAdapterがインポートされ使用されている
        """
        conftest_file = self.CONTRACT_TESTS_DIR / "conftest.py"
        content = conftest_file.read_text()

        assert "TaskFlowAdapter" in content, (
            "TaskFlowAdapter not imported in conftest.py"
        )
        assert "adapter" in content, "adapter fixture not defined in conftest.py"
