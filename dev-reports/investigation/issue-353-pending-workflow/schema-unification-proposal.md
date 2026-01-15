# TaskFlow スキーマ統一化設計書

**作成日**: 2026-01-12
**関連Issue**: #353
**ステータス**: 提案

---

## 1. 設計目標

| 目標 | 説明 |
|------|------|
| **Single Source of Truth** | スキーマ定義を一元管理し、派生を自動生成 |
| **Fail Fast** | 不整合を開発時・CI時に検出 |
| **Explicit Conversion** | システム間の変換を明示的なレイヤーで実施 |
| **Backward Compatible** | 既存コードへの影響を最小化 |

---

## 2. 推奨アーキテクチャ

### 2.1 概念図

```
┌─────────────────────────────────────────────────────────────────┐
│                    Single Source of Truth                        │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │          JSON Schema (taskflow-schema.json)                 │ │
│  │                                                              │ │
│  │  - ワークフロー定義の正式仕様                                │ │
│  │  - 言語非依存                                                │ │
│  │  - バージョン管理                                            │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│   GraphAiServer │ │   ExpertAgent   │ │   Documentation │
│                 │ │                 │ │                 │
│ ┌─────────────┐ │ │ ┌─────────────┐ │ │ ┌─────────────┐ │
│ │ Zod Schema  │ │ │ │  Pydantic   │ │ │ │  Markdown   │ │
│ │  (生成)     │ │ │ │   Schema    │ │ │ │   (生成)    │ │
│ └─────────────┘ │ │ │   (生成)    │ │ │ └─────────────┘ │
│                 │ │ └─────────────┘ │ │                 │
│ ┌─────────────┐ │ │                 │ └─────────────────┘
│ │  Validator  │ │ │ ┌─────────────┐ │
│ │  (既存)     │ │ │ │  Adapter    │ │
│ └─────────────┘ │ │ │  Layer      │ │
└─────────────────┘ │ │  (新規)     │ │
                    │ └─────────────┘ │
                    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ Contract Tests  │
                    │                 │
                    │ - Schema互換性  │
                    │ - 変換正確性    │
                    │ - E2E検証       │
                    └─────────────────┘
```

### 2.2 コンポーネント責務

| コンポーネント | 責務 | 配置 |
|--------------|------|------|
| **JSON Schema** | スキーマの正式定義 | `shared/schemas/taskflow/` |
| **Schema Generator** | JSON Schema → 各言語スキーマ生成 | `scripts/` |
| **Adapter Layer** | ExpertAgent出力 → GraphAiServer形式変換 | `expertAgent/.../adapter/` |
| **Contract Tests** | スキーマ整合性の自動検証 | `tests/contract/` |

---

## 3. 実装計画

### Phase 1: Adapter Layer（即時対応）

**目的**: 現在の問題を解決し、変換ロジックを一箇所に集約

#### 3.1.1 ファイル構成

```
expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/
├── adapter/
│   ├── __init__.py
│   ├── taskflow_adapter.py      # メイン変換ロジック
│   ├── schema_converter.py      # フィールド変換ユーティリティ
│   └── validation.py            # 変換前後のバリデーション
└── ...
```

#### 3.1.2 TaskFlowAdapter クラス設計

```python
# expertAgent/.../adapter/taskflow_adapter.py

from dataclasses import dataclass
from typing import Any
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class ConversionResult:
    """変換結果."""
    success: bool
    data: dict[str, Any] | None
    errors: list[str]
    warnings: list[str]


class TaskFlowAdapter:
    """ExpertAgent出力をGraphAiServer形式に変換するアダプター.

    Adapter Pattern を使用して、2つのシステム間のスキーマ差異を吸収する。

    責務:
    1. JSON文字列フィールドをオブジェクトに変換
    2. 欠落フィールドにデフォルト値を設定
    3. 変換エラーの詳細なレポート

    Usage:
        adapter = TaskFlowAdapter()
        result = adapter.convert(workflow_from_llm)
        if result.success:
            await register_workflow(result.data)
        else:
            handle_errors(result.errors)
    """

    # 変換対象フィールド（ワークフローレベル）
    WORKFLOW_JSON_STRING_FIELDS = ["input_schema", "output_schema", "output"]

    # 変換対象フィールド（ステップレベル）
    STEP_JSON_STRING_FIELDS = ["body"]

    # GraphAiServerのデフォルト値
    GRAPHAI_DEFAULTS = {
        "timeout_ms": 30000,
        "verify_ssl": True,
        "function_name": "main",
        "mode": "template",
        "params": {},
    }

    def convert(self, workflow: dict[str, Any]) -> ConversionResult:
        """ワークフローをGraphAiServer形式に変換.

        Args:
            workflow: ExpertAgent/LLMが生成したワークフロー定義

        Returns:
            ConversionResult with converted data or errors
        """
        errors: list[str] = []
        warnings: list[str] = []

        try:
            result = self._deep_copy(workflow)

            # Step 1: ワークフローレベルのJSON文字列変換
            for field in self.WORKFLOW_JSON_STRING_FIELDS:
                if field in result:
                    converted, error = self._convert_json_string(result[field], field)
                    if error:
                        errors.append(error)
                    else:
                        result[field] = converted

            # Step 2: ステップレベルの変換
            if "steps" in result:
                for i, step in enumerate(result["steps"]):
                    step_errors = self._convert_step(step, i)
                    errors.extend(step_errors)

            # Step 3: デフォルト値の適用（オプション）
            self._apply_defaults(result, warnings)

            if errors:
                return ConversionResult(
                    success=False,
                    data=None,
                    errors=errors,
                    warnings=warnings,
                )

            return ConversionResult(
                success=True,
                data=result,
                errors=[],
                warnings=warnings,
            )

        except Exception as e:
            logger.exception("Unexpected error during conversion")
            return ConversionResult(
                success=False,
                data=None,
                errors=[f"Unexpected conversion error: {e}"],
                warnings=warnings,
            )

    def _convert_json_string(
        self, value: Any, field_name: str
    ) -> tuple[Any, str | None]:
        """JSON文字列をオブジェクトに変換."""
        if value is None:
            return None, None

        if isinstance(value, dict):
            # 既にオブジェクトの場合はそのまま
            return value, None

        if isinstance(value, str):
            try:
                return json.loads(value), None
            except json.JSONDecodeError as e:
                return None, f"{field_name}: Invalid JSON string - {e}"

        return None, f"{field_name}: Expected dict or JSON string, got {type(value).__name__}"

    def _convert_step(self, step: dict[str, Any], index: int) -> list[str]:
        """ステップの変換."""
        errors: list[str] = []
        step_id = step.get("id", f"step_{index}")

        if "config" in step:
            config = step["config"]
            for field in self.STEP_JSON_STRING_FIELDS:
                if field in config and isinstance(config[field], str):
                    converted, error = self._convert_json_string(
                        config[field],
                        f"steps[{step_id}].config.{field}"
                    )
                    if error:
                        # bodyはJSON文字列のままでも許容される場合がある
                        # GraphAiServerはz.unknown()なので、文字列も受け入れる
                        pass  # 警告のみ、エラーにはしない
                    elif converted is not None:
                        config[field] = converted

        return errors

    def _apply_defaults(self, workflow: dict[str, Any], warnings: list[str]) -> None:
        """GraphAiServerのデフォルト値を明示的に設定（オプション）."""
        # 現在は何もしない（GraphAiServer側でデフォルト適用されるため）
        # 必要に応じてここでデフォルト値を設定可能
        pass

    def _deep_copy(self, obj: Any) -> Any:
        """ディープコピー."""
        import copy
        return copy.deepcopy(obj)
```

#### 3.1.3 workflow_registrar.py の修正

```python
# expertAgent/.../workflow_registrar.py

from .adapter import TaskFlowAdapter

# モジュールレベルでアダプターをインスタンス化
_adapter = TaskFlowAdapter()


async def register_taskflow_workflow(
    workflow_name: str,
    workflow_json: dict,
    admin_token: str | None = None,
) -> WorkflowRegistrationResult:
    """Register TaskFlow V2 workflow JSON to GraphAiServer."""

    # Step 1: アダプターで変換
    conversion_result = _adapter.convert(workflow_json)

    if not conversion_result.success:
        error_msg = "; ".join(conversion_result.errors)
        logger.error("Workflow conversion failed: %s", error_msg)
        return WorkflowRegistrationResult(
            success=False,
            error=f"Schema conversion failed: {error_msg}",
        )

    # 警告があればログ出力
    for warning in conversion_result.warnings:
        logger.warning("Workflow conversion warning: %s", warning)

    # Step 2: 変換後のデータで登録
    payload = {
        "workflow_name": workflow_name,
        "definition": conversion_result.data,  # 変換後のデータを使用
        "overwrite": True,
    }

    # ... 以降は既存のHTTPリクエスト処理
```

---

### Phase 2: Contract Tests（短期対応）

**目的**: スキーマ整合性を自動検証し、不整合を早期発見

#### 3.2.1 ファイル構成

```
tests/
├── contract/
│   ├── __init__.py
│   ├── conftest.py                    # 共通フィクスチャ
│   ├── test_taskflow_schema_contract.py  # スキーマ契約テスト
│   └── fixtures/
│       ├── valid_workflows/           # 正常系テストデータ
│       │   ├── simple_api_rest.json
│       │   ├── multi_step.json
│       │   └── transform_workflow.json
│       └── edge_cases/                # エッジケース
│           ├── json_string_fields.json
│           └── missing_optional.json
```

#### 3.2.2 契約テスト実装

```python
# tests/contract/test_taskflow_schema_contract.py

"""TaskFlow スキーマ契約テスト.

ExpertAgentの出力がGraphAiServerで受け入れられることを検証する。
これにより、スキーマ変更時の不整合を早期に検出できる。
"""

import pytest
import httpx
import json
from pathlib import Path

from expertAgent.aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.adapter import (
    TaskFlowAdapter,
)
from expertAgent.aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.taskflow_schema import (
    TaskFlowWorkflow,
)


# テストデータディレクトリ
FIXTURES_DIR = Path(__file__).parent / "fixtures"
VALID_WORKFLOWS_DIR = FIXTURES_DIR / "valid_workflows"


class TestSchemaContract:
    """スキーマ契約テスト."""

    @pytest.fixture
    def adapter(self) -> TaskFlowAdapter:
        return TaskFlowAdapter()

    @pytest.fixture
    def graphai_validate_url(self) -> str:
        return "http://localhost:8005/api/v2/workflows/validate"

    # =========================================
    # 契約1: JSON文字列フィールドの変換
    # =========================================

    @pytest.mark.parametrize("field", ["input_schema", "output_schema", "output"])
    def test_json_string_fields_are_converted(self, adapter: TaskFlowAdapter, field: str):
        """JSON文字列フィールドがオブジェクトに変換されることを検証."""
        workflow = {
            "workflow_name": "test_workflow",
            field: '{"key": "string"}',  # JSON文字列
            "steps": [
                {
                    "id": "step_001",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "GET",
                        "url": "https://example.com",
                    },
                }
            ],
        }
        # 他の必須フィールドを追加
        for f in ["input_schema", "output_schema", "output"]:
            if f not in workflow:
                workflow[f] = '{"default": "string"}'

        result = adapter.convert(workflow)

        assert result.success, f"Conversion failed: {result.errors}"
        assert isinstance(result.data[field], dict), f"{field} should be dict"
        assert result.data[field] == {"key": "string"}

    # =========================================
    # 契約2: Pydanticモデル出力の互換性
    # =========================================

    def test_pydantic_model_output_is_convertible(self, adapter: TaskFlowAdapter):
        """Pydanticモデルのmodel_dump()出力が変換可能であることを検証."""
        workflow = TaskFlowWorkflow(
            workflow_name="test_workflow",
            input_schema='{"query": "string"}',
            output_schema='{"result": "string"}',
            output='{"result": "${step_001.output}"}',
            steps=[
                {
                    "id": "step_001",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "GET",
                        "url": "https://api.example.com",
                    },
                }
            ],
        )

        # Pydanticモデルをdictに変換
        workflow_dict = workflow.model_dump()

        # アダプターで変換
        result = adapter.convert(workflow_dict)

        assert result.success, f"Conversion failed: {result.errors}"
        assert isinstance(result.data["input_schema"], dict)
        assert isinstance(result.data["output_schema"], dict)
        assert isinstance(result.data["output"], dict)

    # =========================================
    # 契約3: GraphAiServerでのバリデーション
    # =========================================

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_converted_workflow_passes_graphai_validation(
        self,
        adapter: TaskFlowAdapter,
        graphai_validate_url: str,
    ):
        """変換後のワークフローがGraphAiServerで検証を通ることを確認."""
        workflow = TaskFlowWorkflow(
            workflow_name="contract_test_workflow",
            description="Contract test workflow",
            input_schema='{"query": "string"}',
            output_schema='{"result": "string"}',
            output='{"result": "${step_001.output.data}"}',
            steps=[
                {
                    "id": "step_001",
                    "type": "api_rest",
                    "config": {
                        "step_type": "api_rest",
                        "method": "GET",
                        "url": "https://api.example.com/search",
                    },
                }
            ],
        )

        # 変換
        conversion_result = adapter.convert(workflow.model_dump())
        assert conversion_result.success

        # GraphAiServerで検証
        async with httpx.AsyncClient() as client:
            response = await client.post(
                graphai_validate_url,
                json={"definition": conversion_result.data},
                timeout=10.0,
            )

        assert response.status_code == 200, f"Validation failed: {response.text}"
        result = response.json()
        assert result.get("valid") is True, f"Validation errors: {result}"

    # =========================================
    # 契約4: フィクスチャファイルの検証
    # =========================================

    @pytest.mark.integration
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "fixture_file",
        list(VALID_WORKFLOWS_DIR.glob("*.json")) if VALID_WORKFLOWS_DIR.exists() else [],
        ids=lambda p: p.stem,
    )
    async def test_fixture_workflows_pass_validation(
        self,
        adapter: TaskFlowAdapter,
        graphai_validate_url: str,
        fixture_file: Path,
    ):
        """フィクスチャのワークフローがすべて検証を通ることを確認."""
        workflow = json.loads(fixture_file.read_text())

        # 変換
        conversion_result = adapter.convert(workflow)
        assert conversion_result.success, f"Conversion failed for {fixture_file}: {conversion_result.errors}"

        # GraphAiServerで検証
        async with httpx.AsyncClient() as client:
            response = await client.post(
                graphai_validate_url,
                json={"definition": conversion_result.data},
                timeout=10.0,
            )

        assert response.status_code == 200, f"Validation failed for {fixture_file}: {response.text}"


class TestSchemaFieldMapping:
    """フィールドマッピングの詳細テスト."""

    @pytest.fixture
    def adapter(self) -> TaskFlowAdapter:
        return TaskFlowAdapter()

    def test_params_with_non_string_values(self, adapter: TaskFlowAdapter):
        """params に非文字列値が含まれる場合の処理を検証.

        ExpertAgentは dict[str, str] を生成するが、
        GraphAiServerは dict[str, unknown] を受け入れる。
        将来的にExpertAgentが拡張された場合のための前方互換性テスト。
        """
        workflow = {
            "workflow_name": "test",
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
                        "url": "https://example.com",
                    },
                    "params": {
                        "string_param": "value",
                        "number_param": 42,  # 将来の拡張
                        "bool_param": True,   # 将来の拡張
                    },
                }
            ],
        }

        result = adapter.convert(workflow)

        # 変換は成功すべき（paramsはそのまま渡す）
        assert result.success
        assert result.data["steps"][0]["params"]["number_param"] == 42
```

#### 3.2.3 CI統合

```yaml
# .github/workflows/contract-tests.yml

name: Contract Tests

on:
  push:
    paths:
      - 'expertAgent/**/schemas/**'
      - 'expertAgent/**/adapter/**'
      - 'graphAiServer/src/engine/schemas/**'
      - 'tests/contract/**'
  pull_request:
    paths:
      - 'expertAgent/**/schemas/**'
      - 'expertAgent/**/adapter/**'
      - 'graphAiServer/src/engine/schemas/**'
      - 'tests/contract/**'

jobs:
  contract-tests:
    runs-on: ubuntu-latest

    services:
      graphai-server:
        image: ghcr.io/${{ github.repository }}/graphai-server:latest
        ports:
          - 8005:8005

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r expertAgent/requirements.txt
          pip install pytest pytest-asyncio httpx

      - name: Wait for GraphAiServer
        run: |
          timeout 60 bash -c 'until curl -s http://localhost:8005/health; do sleep 2; done'

      - name: Run contract tests
        run: |
          pytest tests/contract/ -v --tb=short -m "not integration or integration"
```

---

### Phase 3: JSON Schema as Single Source of Truth（中期対応）

**目的**: スキーマ定義を一元化し、各言語のスキーマを自動生成

#### 3.3.1 JSON Schema 定義

```json
// shared/schemas/taskflow/v1/workflow.schema.json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://myswiftagent.local/schemas/taskflow/v1/workflow.json",
  "title": "TaskFlow Workflow Definition",
  "description": "TaskFlow V2 ワークフロー定義スキーマ",
  "type": "object",
  "required": ["workflow_name", "input_schema", "output_schema", "steps", "output"],
  "properties": {
    "workflow_name": {
      "type": "string",
      "pattern": "^[a-zA-Z_][a-zA-Z0-9_-]*$",
      "description": "ワークフロー名（英数字、アンダースコア、ハイフン）"
    },
    "description": {
      "type": "string",
      "description": "ワークフローの説明"
    },
    "input_schema": {
      "$ref": "#/$defs/IOSchema",
      "description": "入力フィールド定義"
    },
    "output_schema": {
      "$ref": "#/$defs/IOSchema",
      "description": "出力フィールド定義"
    },
    "steps": {
      "type": "array",
      "minItems": 1,
      "items": {
        "$ref": "#/$defs/Step"
      },
      "description": "ワークフローステップ"
    },
    "output": {
      "type": "object",
      "additionalProperties": {
        "type": "string"
      },
      "description": "出力フィールドマッピング"
    }
  },
  "$defs": {
    "SimpleType": {
      "type": "string",
      "enum": ["string", "number", "boolean", "array", "object", "null"]
    },
    "IOSchema": {
      "type": "object",
      "additionalProperties": {
        "$ref": "#/$defs/SimpleType"
      }
    },
    "Step": {
      "type": "object",
      "required": ["id", "type", "config"],
      "properties": {
        "id": {
          "type": "string",
          "pattern": "^[a-zA-Z_][a-zA-Z0-9_-]*$"
        },
        "type": {
          "type": "string",
          "enum": ["api_rest", "code_js", "transform"]
        },
        "description": {
          "type": "string"
        },
        "config": {
          "oneOf": [
            { "$ref": "#/$defs/ApiRestConfig" },
            { "$ref": "#/$defs/CodeJsConfig" },
            { "$ref": "#/$defs/TransformConfig" }
          ]
        },
        "params": {
          "type": "object",
          "additionalProperties": true
        },
        "input_schema": {
          "$ref": "#/$defs/IOSchema"
        },
        "output_schema": {
          "$ref": "#/$defs/IOSchema"
        }
      }
    },
    "ApiRestConfig": {
      "type": "object",
      "required": ["method", "url"],
      "properties": {
        "step_type": { "const": "api_rest" },
        "method": { "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"] },
        "url": { "type": "string" },
        "headers": {
          "type": "object",
          "additionalProperties": { "type": "string" }
        },
        "body": {},
        "timeout_ms": { "type": "integer", "minimum": 1, "default": 30000 },
        "verify_ssl": { "type": "boolean", "default": true }
      }
    },
    "CodeJsConfig": {
      "type": "object",
      "required": ["path"],
      "properties": {
        "step_type": { "const": "code_js" },
        "path": { "type": "string" },
        "function_name": { "type": "string", "default": "main" }
      }
    },
    "TransformConfig": {
      "type": "object",
      "properties": {
        "step_type": { "const": "transform" },
        "mode": { "enum": ["template", "concat", "map", "merge"], "default": "template" },
        "template": { "type": "string" },
        "separator": { "type": "string" },
        "fields": { "type": "array", "items": { "type": "string" } },
        "source_field": { "type": "string" },
        "strategy": { "enum": ["shallow", "deep"] }
      }
    }
  }
}
```

#### 3.3.2 スキーマ生成スクリプト

```python
# scripts/generate_schemas.py

"""JSON Schema から各言語のスキーマを生成するスクリプト.

Usage:
    python scripts/generate_schemas.py

Generated files:
    - graphAiServer/src/engine/schemas/generated/taskflow.ts
    - expertAgent/.../schemas/generated/taskflow_types.py
"""

import json
import subprocess
from pathlib import Path

SCHEMA_DIR = Path("shared/schemas/taskflow/v1")
GRAPHAI_OUTPUT = Path("graphAiServer/src/engine/schemas/generated")
EXPERT_OUTPUT = Path("expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/schemas/generated")


def generate_typescript():
    """json-schema-to-typescript を使用してTypeScript型を生成."""
    subprocess.run([
        "npx", "json-schema-to-typescript",
        str(SCHEMA_DIR / "workflow.schema.json"),
        "-o", str(GRAPHAI_OUTPUT / "taskflow.d.ts"),
        "--bannerComment", "// Auto-generated from JSON Schema. DO NOT EDIT.",
    ], check=True)
    print(f"Generated: {GRAPHAI_OUTPUT / 'taskflow.d.ts'}")


def generate_python():
    """datamodel-code-generator を使用してPydanticモデルを生成."""
    subprocess.run([
        "datamodel-codegen",
        "--input", str(SCHEMA_DIR / "workflow.schema.json"),
        "--output", str(EXPERT_OUTPUT / "taskflow_types.py"),
        "--input-file-type", "jsonschema",
        "--output-model-type", "pydantic_v2.BaseModel",
        "--target-python-version", "3.11",
    ], check=True)
    print(f"Generated: {EXPERT_OUTPUT / 'taskflow_types.py'}")


def validate_schema():
    """JSON Schemaの妥当性を検証."""
    schema_file = SCHEMA_DIR / "workflow.schema.json"
    schema = json.loads(schema_file.read_text())

    # 基本的な検証
    assert "$schema" in schema
    assert "properties" in schema
    assert "workflow_name" in schema["properties"]
    print("Schema validation passed")


if __name__ == "__main__":
    validate_schema()

    GRAPHAI_OUTPUT.mkdir(parents=True, exist_ok=True)
    EXPERT_OUTPUT.mkdir(parents=True, exist_ok=True)

    generate_typescript()
    generate_python()

    print("\nSchema generation completed!")
```

---

## 4. 実装ロードマップ

| フェーズ | 内容 | 工数 | 優先度 |
|---------|------|------|--------|
| **Phase 1** | Adapter Layer実装 | 2日 | P0 |
| **Phase 2** | Contract Tests実装 | 2日 | P0 |
| **Phase 3** | JSON Schema導入 | 5日 | P1 |
| **Phase 4** | 自動生成パイプライン | 3日 | P2 |

### 詳細スケジュール

```
Week 1:
├── Day 1-2: Phase 1 - Adapter Layer
│   ├── TaskFlowAdapter クラス実装
│   ├── workflow_registrar.py 修正
│   └── 単体テスト作成
│
└── Day 3-4: Phase 2 - Contract Tests
    ├── テストフレームワーク設定
    ├── 契約テスト実装
    └── CI統合

Week 2:
└── Day 5-9: Phase 3 - JSON Schema
    ├── スキーマ定義
    ├── 生成スクリプト実装
    └── 既存コードとの統合
```

---

## 5. リスクと対策

| リスク | 対策 |
|--------|------|
| JSON Schema生成ツールの制限 | 複雑な型は手動補完、生成と手動のハイブリッド |
| OpenAI Structured Output制約 | Adapter Layerで吸収、LLM用スキーマは別途管理 |
| 既存コードへの影響 | 段階的移行、互換性レイヤー維持 |
| テスト環境の構築 | Docker Composeで統一環境提供 |

---

## 6. 成功指標

| 指標 | 目標値 | 測定方法 |
|------|--------|---------|
| スキーマ不整合によるバグ | 0件/リリース | Issue追跡 |
| 契約テストカバレッジ | 100% | テストレポート |
| スキーマ変更からデプロイまでの時間 | 1日以内 | CI/CDログ |
| 手動スキーマ同期作業 | 0時間/月 | 作業記録 |

---

## 7. 次のアクション

1. [ ] Phase 1 Issue作成: 「TaskFlow Adapter Layer実装」
2. [ ] Phase 2 Issue作成: 「TaskFlow Contract Tests実装」
3. [ ] Phase 3 Issue作成: 「JSON Schema Single Source of Truth導入」
4. [ ] 本設計書のレビュー依頼
