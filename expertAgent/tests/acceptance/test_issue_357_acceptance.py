"""Issue #357 受入テスト（L3: ローカル受入テスト）.

Issue #357: JSON Schema Single Source of Truth 導入

前提条件:
- 本Issueはサービス起動不要（ファイル存在・スクリプト実行のテスト）
- Python環境がセットアップされていること

実行方法:
  cd expertAgent
  uv run pytest tests/acceptance/test_issue_357_acceptance.py -v
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Repository root directory
# Path: expertAgent/tests/acceptance/test_issue_357_acceptance.py
# -> acceptance -> tests -> expertAgent -> MySwiftAgent (4 levels up)
REPO_ROOT = Path(__file__).parent.parent.parent.parent


@pytest.mark.acceptance
class TestIssue357Acceptance:
    """Issue #357: JSON Schema Single Source of Truth 導入.

    受入条件:
    - AC-1: JSON Schemaファイルが存在し、Draft 2020-12準拠
    - AC-2: 生成スクリプトが存在し、構文エラーなし
    - AC-3: TypeScript型ファイルが自動生成される
    - AC-4: Pydanticモデルファイルが自動生成される
    - AC-5: 既存テストとの互換性が保たれる
    - AC-6: JSON Schema妥当性検証がパス
    - AC-7: 生成スクリプト正常終了
    - AC-8: TypeScriptコンパイル成功
    - AC-9: Pydanticインポート成功
    """

    JSON_SCHEMA_PATH = REPO_ROOT / "shared/schemas/taskflow/v1/workflow.schema.json"
    GENERATE_SCRIPT_PATH = REPO_ROOT / "scripts/generate_schemas.py"
    TYPESCRIPT_OUTPUT_PATH = (
        REPO_ROOT / "graphAiServer/src/engine/schemas/generated/taskflow.d.ts"
    )
    PYDANTIC_OUTPUT_PATH = (
        REPO_ROOT
        / "expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/schemas/generated/taskflow_types.py"
    )

    # ==========================================================================
    # TC-001: JSON Schemaファイル存在確認
    # ==========================================================================

    def test_tc_001_json_schema_file_exists(self) -> None:
        """TC-001: JSON Schemaファイルが存在する.

        受入条件: AC-1 JSON Schemaファイルが存在
        """
        assert self.JSON_SCHEMA_PATH.exists(), (
            f"JSON Schema file not found: {self.JSON_SCHEMA_PATH}"
        )
        assert self.JSON_SCHEMA_PATH.is_file(), (
            f"JSON Schema path is not a file: {self.JSON_SCHEMA_PATH}"
        )

    def test_tc_001_json_schema_is_valid_json(self) -> None:
        """TC-001: JSON Schemaが有効なJSONである.

        受入条件: AC-1 有効なJSONである
        """
        with open(self.JSON_SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)
        assert isinstance(schema, dict), "Schema should be a JSON object"

    def test_tc_001_json_schema_is_draft_2020_12(self) -> None:
        """TC-001: JSON SchemaがDraft 2020-12準拠.

        受入条件: AC-1 Draft 2020-12準拠
        設計方針: DP-2
        """
        with open(self.JSON_SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)
        assert "$schema" in schema, "Schema must have $schema property"
        assert "draft/2020-12" in schema["$schema"], (
            f"Schema must be Draft 2020-12, got: {schema['$schema']}"
        )

    def test_tc_001_json_schema_has_required_properties(self) -> None:
        """TC-001: JSON Schemaに必須プロパティが定義されている.

        受入条件: AC-1 必須プロパティ定義
        """
        with open(self.JSON_SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)
        assert "properties" in schema, "Schema must have 'properties'"
        required_props = [
            "workflow_name",
            "input_schema",
            "output_schema",
            "steps",
            "output",
        ]
        for prop in required_props:
            assert prop in schema["properties"], f"Property '{prop}' not found"

    # ==========================================================================
    # TC-002: 生成スクリプト存在確認
    # ==========================================================================

    def test_tc_002_generate_script_exists(self) -> None:
        """TC-002: 生成スクリプトが存在する.

        受入条件: AC-2 生成スクリプトが存在
        """
        assert self.GENERATE_SCRIPT_PATH.exists(), (
            f"Generate script not found: {self.GENERATE_SCRIPT_PATH}"
        )
        assert self.GENERATE_SCRIPT_PATH.is_file(), (
            f"Generate script path is not a file: {self.GENERATE_SCRIPT_PATH}"
        )

    def test_tc_002_generate_script_no_syntax_errors(self) -> None:
        """TC-002: 生成スクリプトに構文エラーがない.

        受入条件: AC-2 構文エラーなし
        """
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(self.GENERATE_SCRIPT_PATH)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, (
            f"Syntax error in generate script: {result.stderr}"
        )

    # ==========================================================================
    # TC-003: TypeScriptファイル生成確認
    # ==========================================================================

    def test_tc_003_typescript_file_exists(self) -> None:
        """TC-003: TypeScriptファイルが生成されている.

        受入条件: AC-3 TypeScript型ファイルが自動生成される
        """
        assert self.TYPESCRIPT_OUTPUT_PATH.exists(), (
            f"TypeScript file not found: {self.TYPESCRIPT_OUTPUT_PATH}"
        )

    def test_tc_003_typescript_file_has_auto_generated_header(self) -> None:
        """TC-003: TypeScriptファイルに自動生成ヘッダーがある.

        受入条件: AC-3 自動生成されたファイルである
        """
        content = self.TYPESCRIPT_OUTPUT_PATH.read_text(encoding="utf-8")
        assert "Auto-generated" in content or "DO NOT EDIT" in content, (
            "TypeScript file should have auto-generated header"
        )

    def test_tc_003_typescript_file_has_workflow_type(self) -> None:
        """TC-003: TypeScriptファイルにワークフロー型が定義されている.

        受入条件: AC-3 型定義が含まれる
        """
        content = self.TYPESCRIPT_OUTPUT_PATH.read_text(encoding="utf-8")
        assert "TaskFlowWorkflowDefinition" in content, (
            "TypeScript file should have TaskFlowWorkflowDefinition type"
        )
        assert "Step" in content, "TypeScript file should have Step type"
        assert "ApiRestConfig" in content, (
            "TypeScript file should have ApiRestConfig type"
        )

    # ==========================================================================
    # TC-004: Pydanticファイル生成確認
    # ==========================================================================

    def test_tc_004_pydantic_file_exists(self) -> None:
        """TC-004: Pydanticファイルが生成されている.

        受入条件: AC-4 Pydanticモデルファイルが自動生成される
        """
        assert self.PYDANTIC_OUTPUT_PATH.exists(), (
            f"Pydantic file not found: {self.PYDANTIC_OUTPUT_PATH}"
        )

    def test_tc_004_pydantic_file_has_auto_generated_header(self) -> None:
        """TC-004: Pydanticファイルに自動生成ヘッダーがある.

        受入条件: AC-4 自動生成されたファイルである
        """
        content = self.PYDANTIC_OUTPUT_PATH.read_text(encoding="utf-8")
        assert "Auto-generated" in content or "DO NOT EDIT" in content, (
            "Pydantic file should have auto-generated header"
        )

    def test_tc_004_pydantic_file_is_importable(self) -> None:
        """TC-004: Pydanticモデルがインポート可能.

        受入条件: AC-4, AC-9 インポート成功
        """
        # Import the generated module
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.generated.taskflow_types import (
            ApiRestConfig,
            CodeJsConfig,
            Step,
            TaskflowWorkflowDefinition,
            TransformConfig,
        )
        from pydantic import BaseModel

        # Verify all classes are BaseModel subclasses
        assert issubclass(TaskflowWorkflowDefinition, BaseModel), (
            "TaskflowWorkflowDefinition should inherit from BaseModel"
        )
        assert issubclass(Step, BaseModel), "Step should inherit from BaseModel"
        assert issubclass(ApiRestConfig, BaseModel), (
            "ApiRestConfig should inherit from BaseModel"
        )
        assert issubclass(CodeJsConfig, BaseModel), (
            "CodeJsConfig should inherit from BaseModel"
        )
        assert issubclass(TransformConfig, BaseModel), (
            "TransformConfig should inherit from BaseModel"
        )

    def test_tc_004_pydantic_model_has_required_fields(self) -> None:
        """TC-004: Pydanticモデルに必須フィールドがある.

        受入条件: AC-4 必須フィールド定義
        """
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.generated.taskflow_types import (
            TaskflowWorkflowDefinition,
        )

        fields = TaskflowWorkflowDefinition.model_fields
        required_fields = [
            "workflow_name",
            "input_schema",
            "output_schema",
            "steps",
            "output",
        ]
        for field in required_fields:
            assert field in fields, f"Required field '{field}' not found in model"

    # ==========================================================================
    # TC-005: 既存テスト互換性確認
    # ==========================================================================

    def test_tc_005_unit_tests_pass(self) -> None:
        """TC-005: Issue #357の単体テストが全てパスする.

        受入条件: AC-5 既存テストとの互換性
        """
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(REPO_ROOT / "expertAgent/tests/unit/test_issue_357_json_schema.py"),
                str(
                    REPO_ROOT / "expertAgent/tests/unit/test_issue_357_generate_schemas.py"
                ),
                "-v",
                "--tb=short",
            ],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(REPO_ROOT / "expertAgent"),
        )
        assert result.returncode == 0, (
            f"Unit tests failed:\n{result.stdout}\n{result.stderr}"
        )

    # ==========================================================================
    # TC-006: JSON Schema妥当性検証
    # ==========================================================================

    def test_tc_006_json_schema_is_valid(self) -> None:
        """TC-006: JSON Schemaが妥当である.

        受入条件: AC-6 JSON Schema妥当性検証がパス
        """
        from jsonschema import Draft202012Validator

        with open(self.JSON_SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)

        # Validate the schema itself
        Draft202012Validator.check_schema(schema)

    def test_tc_006_json_schema_validates_sample_workflow(self) -> None:
        """TC-006: サンプルワークフローがスキーマ検証を通過する.

        受入条件: AC-6 実際のワークフローが検証可能
        """
        from jsonschema import Draft202012Validator

        with open(self.JSON_SCHEMA_PATH, encoding="utf-8") as f:
            schema = json.load(f)

        validator = Draft202012Validator(schema)

        # Create a valid sample workflow
        sample_workflow = {
            "workflow_name": "test_workflow",
            "description": "Test workflow for validation",
            "input_schema": {"query": "string"},
            "output_schema": {"result": "string"},
            "steps": [
                {
                    "id": "step_001",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "GET",
                        "url": "https://api.example.com/data",
                    },
                }
            ],
            "output": {"result": "${step_001.output.data}"},
        }

        # This should not raise any exceptions
        validator.validate(sample_workflow)

    # ==========================================================================
    # TC-007: スキーマ互換性検証
    # ==========================================================================

    def test_tc_007_schema_compatibility_with_existing(self) -> None:
        """TC-007: 生成されたスキーマが既存のスキーマと互換性がある.

        受入条件: AC-5 既存スキーマとの互換性
        設計方針: DP-4
        """
        # Import both schemas (sorted alphabetically per isort requirements)
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.generated.taskflow_types import (
            TaskflowWorkflowDefinition,
        )
        from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.taskflow_schema import (
            TaskFlowWorkflow,
        )

        # Compare field names
        existing_fields = set(TaskFlowWorkflow.model_fields.keys())
        generated_fields = set(TaskflowWorkflowDefinition.model_fields.keys())

        # Core fields should be present in both
        core_fields = {
            "workflow_name",
            "input_schema",
            "output_schema",
            "steps",
            "output",
        }
        assert core_fields.issubset(existing_fields), (
            f"Missing core fields in existing schema: {core_fields - existing_fields}"
        )
        assert core_fields.issubset(generated_fields), (
            f"Missing core fields in generated schema: {core_fields - generated_fields}"
        )

    # ==========================================================================
    # TC-008: Single Source of Truth検証
    # ==========================================================================

    def test_tc_008_single_source_of_truth_architecture(self) -> None:
        """TC-008: Single Source of Truthアーキテクチャが正しく実装されている.

        設計方針: DP-1
        """
        # Verify JSON Schema is the source
        assert self.JSON_SCHEMA_PATH.exists(), "JSON Schema (source) must exist"

        # Verify generated files exist in 'generated' directories
        assert "generated" in str(self.TYPESCRIPT_OUTPUT_PATH), (
            "TypeScript output should be in 'generated' directory"
        )
        assert "generated" in str(self.PYDANTIC_OUTPUT_PATH), (
            "Pydantic output should be in 'generated' directory"
        )

        # Verify generate script references the JSON Schema
        script_content = self.GENERATE_SCRIPT_PATH.read_text(encoding="utf-8")
        assert "workflow.schema.json" in script_content, (
            "Generate script should reference workflow.schema.json"
        )

    def test_tc_008_generated_files_have_source_reference(self) -> None:
        """TC-008: 生成されたファイルがソースを参照している.

        設計方針: DP-1
        """
        ts_content = self.TYPESCRIPT_OUTPUT_PATH.read_text(encoding="utf-8")
        py_content = self.PYDANTIC_OUTPUT_PATH.read_text(encoding="utf-8")

        # Both files should reference the source schema
        assert "workflow.schema.json" in ts_content, (
            "TypeScript file should reference source schema"
        )
        assert "workflow.schema.json" in py_content, (
            "Pydantic file should reference source schema"
        )
