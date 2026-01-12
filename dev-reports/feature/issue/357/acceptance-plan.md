# 受入テスト計画書

**Issue**: #357
**作成日**: 2026-01-12
**作成者**: acceptance-plan-agent

---

## 1. 概要

### 対象Issue
- **番号**: #357
- **タイトル**: Issue #354-3: JSON Schema Single Source of Truth 導入
- **プロジェクト**: expertAgent / graphAiServer / shared

### 参照ドキュメント
- Issue: #357
- 設計方針書: `dev-reports/investigation/issue-353-pending-workflow/schema-unification-proposal.md`
- 親Issue: #354

### 機能概要
JSON Schemaを唯一の定義とし、TypeScript/Pythonスキーマを自動生成する仕組みを構築。
スキーマ変更を一箇所で管理し、各システムへの反映を自動化する。

---

## 2. 単体テスト結果レビュー

### Pre-TDD フェーズ

本計画はTDD実装前のフェーズで作成されているため、単体テスト結果は存在しません。

**TDD実装後に追加すべき検証項目**:

| 項目 | 確認内容 | 判定基準 |
|------|---------|---------|
| カバレッジ | `scripts/generate_schemas.py` のカバレッジ | 90%以上 |
| テスト数 | スキーマ生成関数に対するテスト数 | 各関数に最低1テスト |
| 静的解析 | Ruff/MyPyエラー | 0件 |
| TypeScript検証 | tsc コンパイルエラー | 0件 |

### TDD実装後に確認すべきモック使用の妥当性

```bash
# モック使用箇所を確認
grep -r "@patch\|Mock\|MagicMock" scripts/tests/ | wc -l

# subprocessモック（json-schema-to-typescript, datamodel-code-generator）
# これらは外部ツール呼び出しなのでモック使用は適切
```

---

## 3. 受入条件分析

### AC-1: JSON Schemaファイルの存在
- **原文**: `shared/schemas/taskflow/v1/workflow.schema.json` が存在
- **分類**: 機能要件
- **テスト方法**: ファイル存在確認 + JSON Schema妥当性検証
- **モック使用**: 不可
- **検証ポイント**:
  1. ファイルが指定パスに存在する
  2. JSON Schema Draft 2020-12 に準拠している
  3. 必須プロパティ（workflow_name, input_schema, output_schema, steps, output）が定義されている
  4. 既存のPydanticスキーマ（taskflow_schema.py）と互換性がある

### AC-2: 生成スクリプトの存在
- **原文**: `scripts/generate_schemas.py` が存在
- **分類**: 機能要件
- **テスト方法**: ファイル存在確認 + 実行可能性検証
- **モック使用**: 不可
- **検証ポイント**:
  1. ファイルが指定パスに存在する
  2. Pythonスクリプトとして構文エラーがない
  3. 必要な依存関係がインポート可能

### AC-3: TypeScript型自動生成
- **原文**: TypeScript型ファイルが自動生成される
- **分類**: 機能要件
- **テスト方法**: スクリプト実行 + ファイル生成確認
- **モック使用**: 不可
- **検証ポイント**:
  1. `python scripts/generate_schemas.py` 実行後、TypeScriptファイルが生成される
  2. 出力先: `graphAiServer/src/engine/schemas/generated/taskflow.d.ts`
  3. 生成されたファイルにTypeScript型定義が含まれる
  4. tscでコンパイルエラーがない

### AC-4: Pydanticモデル自動生成
- **原文**: Pydanticモデルファイルが自動生成される
- **分類**: 機能要件
- **テスト方法**: スクリプト実行 + ファイル生成確認
- **モック使用**: 不可
- **検証ポイント**:
  1. `python scripts/generate_schemas.py` 実行後、Pythonファイルが生成される
  2. 出力先: `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/schemas/generated/taskflow_types.py`
  3. 生成されたファイルにPydanticモデルが含まれる
  4. インポート可能

### AC-5: 既存テストとの互換性
- **原文**: 生成されたスキーマが既存テストをパス
- **分類**: 品質基準
- **テスト方法**: pytest実行
- **モック使用**: テストケースによる
- **検証ポイント**:
  1. expertAgentの既存単体テストがすべてパス
  2. graphAiServerの既存単体テストがすべてパス
  3. Contract Testsがすべてパス

### AC-6: JSON Schema妥当性検証
- **原文**: JSON Schema妥当性検証がパス
- **分類**: 品質基準
- **テスト方法**: jsonschema検証ツール
- **モック使用**: 不可
- **検証ポイント**:
  1. JSON Schemaの$schemaが有効
  2. $defsの参照が正しく解決される
  3. 必須フィールドが適切に定義されている

### AC-7: 生成スクリプト正常終了
- **原文**: `python scripts/generate_schemas.py` が正常終了
- **分類**: テストケース
- **テスト方法**: スクリプト実行
- **モック使用**: 不可
- **検証ポイント**:
  1. 終了コード 0
  2. エラー出力なし
  3. 期待するファイルが生成される

### AC-8: TypeScriptコンパイル成功
- **原文**: 生成されたTypeScript型がコンパイルエラーなし
- **分類**: テストケース
- **テスト方法**: tsc実行
- **モック使用**: 不可
- **検証ポイント**:
  1. `tsc --noEmit` が成功
  2. 型定義が既存のworkflow-schema.tsと互換性がある

### AC-9: Pydanticインポート成功
- **原文**: 生成されたPydanticモデルがインポート可能
- **分類**: テストケース
- **テスト方法**: Pythonインポート実行
- **モック使用**: 不可
- **検証ポイント**:
  1. `from ... import *` が成功
  2. 生成されたモデルがPydantic BaseModelを継承

---

## 4. 設計方針検証

### DP-1: Single Source of Truth アーキテクチャ
- **設計方針**: JSON Schemaを唯一の定義とし、各言語のスキーマを自動生成
- **検証方法**: ファイル構造確認 + 生成フロー検証
- **テスト項目**:
  1. `shared/schemas/taskflow/v1/workflow.schema.json` が存在
  2. TypeScript/Pydanticスキーマがこのファイルから生成される
  3. 手動で編集されたスキーマファイルが `generated/` 以外に存在しない

### DP-2: JSON Schema Draft 2020-12 準拠
- **設計方針**: JSON Schema Draft 2020-12 使用
- **検証方法**: スキーマ検証
- **テスト項目**:
  1. `$schema` が `https://json-schema.org/draft/2020-12/schema` である
  2. Draft 2020-12 の機能（$defs等）が正しく使用されている

### DP-3: 生成ツールの技術選定
- **設計方針**: json-schema-to-typescript（TypeScript）、datamodel-code-generator（Pydantic）
- **検証方法**: スクリプト実装確認
- **テスト項目**:
  1. TypeScript生成に `json-schema-to-typescript` (npx) が使用される
  2. Pydantic生成に `datamodel-codegen` が使用される
  3. 両ツールのバージョンが適切に管理されている

### DP-4: 既存スキーマとの互換性
- **設計方針**: Backward Compatible - 既存コードへの影響を最小化
- **検証方法**: 既存スキーマとの比較
- **テスト項目**:
  1. 既存の `taskflow_schema.py` の型と互換性がある
  2. 既存の `workflow-schema.ts` の型と互換性がある
  3. 既存のワークフロー定義がバリデーションを通過する

---

## 5. デッドコード検証計画

### F-1: generate_schemas.py
- **ファイル**: `scripts/generate_schemas.py`
- **種別**: script (main)
- **期待される呼び出し元**: CI/CD パイプライン、開発者の手動実行
- **検証方法**:
  ```bash
  # スクリプトが実行可能であることを確認
  python scripts/generate_schemas.py --help || python scripts/generate_schemas.py
  ```
- **E2Eでの確認方法**: スクリプト実行後、生成ファイルが存在し、有効であること

### F-2: validate_schema 関数
- **ファイル**: `scripts/generate_schemas.py` 内
- **種別**: function
- **期待される呼び出し元**: `generate_schemas.py` のmain関数
- **検証方法**:
  ```bash
  # 関数が呼び出されていることを確認
  grep -n "validate_schema" scripts/generate_schemas.py
  ```
- **E2Eでの確認方法**: スクリプト実行時にvalidationが実行されること（出力確認）

### F-3: generate_typescript 関数
- **ファイル**: `scripts/generate_schemas.py` 内
- **種別**: function
- **期待される呼び出し元**: `generate_schemas.py` のmain関数
- **検証方法**:
  ```bash
  # TypeScriptファイルが生成されることで確認
  ls -la graphAiServer/src/engine/schemas/generated/taskflow.d.ts
  ```
- **E2Eでの確認方法**: 生成されたTypeScriptファイルがコンパイル可能

### F-4: generate_python 関数
- **ファイル**: `scripts/generate_schemas.py` 内
- **種別**: function
- **期待される呼び出し元**: `generate_schemas.py` のmain関数
- **検証方法**:
  ```bash
  # Pydanticファイルが生成されることで確認
  ls -la expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/schemas/generated/taskflow_types.py
  ```
- **E2Eでの確認方法**: 生成されたPydanticモデルがインポート可能

### F-5: workflow.schema.json
- **ファイル**: `shared/schemas/taskflow/v1/workflow.schema.json`
- **種別**: schema file
- **期待される呼び出し元**: `generate_schemas.py`
- **検証方法**:
  ```bash
  # スクリプトがこのファイルを読み込むことを確認
  grep -n "workflow.schema.json" scripts/generate_schemas.py
  ```
- **E2Eでの確認方法**: スキーマから正しく型が生成される

---

## 6. テスト環境

### 必須サービス
| サービス | URL | ヘルスチェック |
|---------|-----|--------------|
| Node.js (npx) | - | `npx --version` |
| Python 3.11+ | - | `python --version` |
| datamodel-codegen | - | `datamodel-codegen --version` |

### 起動コマンド
```bash
# 本Issueのテストはサービス起動不要（スクリプト実行のみ）
# 依存ツールのインストール
pip install datamodel-code-generator
npm install -g json-schema-to-typescript
```

### 環境変数
| 変数名 | 説明 | 必須 |
|--------|------|------|
| PYTHONPATH | expertAgentルートを含める | 推奨 |

### テストデータ
- 既存のワークフロー定義（tests/contract/fixtures/）
- 既存のPydanticスキーマ（taskflow_schema.py）の型定義
- 既存のZodスキーマ（workflow-schema.ts）の型定義

---

## 7. テスト項目

### TC-001: JSON Schemaファイル存在確認
- **テスト観点**: AC-1 JSON Schemaファイルが存在し、有効なJSON Schemaである
- **関連する受入条件**: AC-1
- **関連する設計方針**: DP-1, DP-2
- **テスト種別**: E2E
- **テスト方法**: Bashコマンド + Python検証
- **前提条件**:
  1. リポジトリがクローンされている
  2. Python環境がセットアップされている
- **テスト手順**:
  1. JSON Schemaファイルの存在確認
  2. JSONとして読み込み可能か確認
  3. $schemaフィールドがDraft 2020-12を指していることを確認
  4. 必須プロパティが定義されていることを確認
- **期待結果**:
  - ファイルが存在する
  - 有効なJSONである
  - `$schema` が `https://json-schema.org/draft/2020-12/schema`
  - `properties` に workflow_name, input_schema, output_schema, steps, output が含まれる
- **Bashコマンド**:
  ```bash
  # ファイル存在確認
  ls -la shared/schemas/taskflow/v1/workflow.schema.json

  # JSON妥当性 + 構造確認
  python -c "
import json
with open('shared/schemas/taskflow/v1/workflow.schema.json') as f:
    schema = json.load(f)
assert '\$schema' in schema
assert 'draft/2020-12' in schema['\$schema']
assert 'properties' in schema
required_props = ['workflow_name', 'input_schema', 'output_schema', 'steps', 'output']
for prop in required_props:
    assert prop in schema['properties'], f'{prop} not found'
print('JSON Schema validation passed')
"
  ```
- **pytestメソッド**: `test_tc_001_json_schema_exists_and_valid`

### TC-002: 生成スクリプト存在確認
- **テスト観点**: AC-2 生成スクリプトが存在し、構文エラーがない
- **関連する受入条件**: AC-2
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: Bashコマンド
- **前提条件**:
  1. Python環境がセットアップされている
- **テスト手順**:
  1. スクリプトファイルの存在確認
  2. Python構文チェック
- **期待結果**:
  - ファイルが存在する
  - `python -m py_compile` が成功
- **Bashコマンド**:
  ```bash
  # ファイル存在確認
  ls -la scripts/generate_schemas.py

  # 構文チェック
  python -m py_compile scripts/generate_schemas.py
  echo "Syntax check passed"
  ```
- **pytestメソッド**: `test_tc_002_generate_script_exists`

### TC-003: 生成スクリプト実行
- **テスト観点**: AC-7 スクリプトが正常終了し、ファイルが生成される
- **関連する受入条件**: AC-3, AC-4, AC-7
- **関連する設計方針**: DP-1, DP-3
- **テスト種別**: E2E
- **テスト方法**: Bashコマンド
- **前提条件**:
  1. JSON Schemaファイルが存在する
  2. 必要なツール（datamodel-codegen, json-schema-to-typescript）がインストールされている
- **テスト手順**:
  1. 生成スクリプトを実行
  2. 終了コードを確認
  3. 出力ファイルの存在を確認
- **期待結果**:
  - 終了コード 0
  - TypeScriptファイルが生成される
  - Pydanticファイルが生成される
- **Bashコマンド**:
  ```bash
  # スクリプト実行
  python scripts/generate_schemas.py

  # 終了コード確認
  echo "Exit code: $?"

  # 生成ファイル確認
  ls -la graphAiServer/src/engine/schemas/generated/taskflow.d.ts
  ls -la expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/schemas/generated/taskflow_types.py
  ```
- **pytestメソッド**: `test_tc_003_generate_script_execution`

### TC-004: TypeScript型コンパイル確認
- **テスト観点**: AC-8 生成されたTypeScript型がコンパイルエラーなし
- **関連する受入条件**: AC-8
- **関連する設計方針**: DP-4
- **テスト種別**: E2E
- **テスト方法**: tscコマンド
- **前提条件**:
  1. TC-003が成功している
  2. TypeScript環境がセットアップされている
- **テスト手順**:
  1. graphAiServerディレクトリに移動
  2. tscでコンパイルチェック
- **期待結果**:
  - tsc --noEmit が成功
- **Bashコマンド**:
  ```bash
  cd graphAiServer

  # 生成されたファイルの型チェック
  npx tsc --noEmit src/engine/schemas/generated/taskflow.d.ts --skipLibCheck --esModuleInterop --module ES2022 --moduleResolution node

  echo "TypeScript compile check passed"
  ```
- **pytestメソッド**: `test_tc_004_typescript_compile_check`

### TC-005: Pydanticモデルインポート確認
- **テスト観点**: AC-9 生成されたPydanticモデルがインポート可能
- **関連する受入条件**: AC-9
- **関連する設計方針**: DP-4
- **テスト種別**: E2E
- **テスト方法**: Pythonインポート
- **前提条件**:
  1. TC-003が成功している
  2. expertAgent環境がセットアップされている
- **テスト手順**:
  1. 生成されたモジュールをインポート
  2. BaseModelを継承しているか確認
- **期待結果**:
  - インポートが成功
  - モデルがPydantic BaseModelを継承
- **Bashコマンド**:
  ```bash
  cd expertAgent

  python -c "
from pydantic import BaseModel
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.generated.taskflow_types import *

# 生成されたモデルがBaseModelを継承していることを確認
# (実際のクラス名は生成結果に依存)
print('Import successful')
print('Available classes:', dir())
"
  ```
- **pytestメソッド**: `test_tc_005_pydantic_import_check`

### TC-006: 既存テスト互換性確認
- **テスト観点**: AC-5 既存テストがすべてパスする
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-4
- **テスト種別**: 結合
- **テスト方法**: pytest
- **前提条件**:
  1. TC-003が成功している
  2. 既存テストスイートがセットアップされている
- **テスト手順**:
  1. expertAgentの単体テスト実行
  2. graphAiServerの単体テスト実行
  3. Contract Tests実行
- **期待結果**:
  - すべてのテストがパス
- **Bashコマンド**:
  ```bash
  # expertAgent単体テスト
  cd expertAgent && uv run pytest tests/unit/ -v --tb=short

  # graphAiServer単体テスト
  cd graphAiServer && npm test

  # Contract Tests（存在する場合）
  cd tests/contract && uv run pytest -v --tb=short || echo "No contract tests yet"
  ```
- **pytestメソッド**: `test_tc_006_existing_tests_pass`

### TC-007: スキーマ互換性検証
- **テスト観点**: 生成されたスキーマが既存のスキーマと互換性がある
- **関連する受入条件**: AC-5
- **関連する設計方針**: DP-4
- **テスト種別**: E2E
- **テスト方法**: スキーマ比較
- **前提条件**:
  1. TC-003が成功している
- **テスト手順**:
  1. 既存のtaskflow_schema.pyの型定義を取得
  2. 生成されたtaskflow_types.pyの型定義と比較
  3. 主要なフィールドが一致することを確認
- **期待結果**:
  - 主要なフィールド（workflow_name, input_schema, output_schema, steps, output）が一致
  - ステップタイプ（api_rest, transform, code_js）が定義されている
- **Bashコマンド**:
  ```bash
  cd expertAgent

  python -c "
# 既存スキーマの検証
from aiagent.langgraph.jobGeneratorV2.workflows.workflow_gen.schemas.taskflow_schema import TaskFlowWorkflow

# 必須フィールドの確認
fields = TaskFlowWorkflow.model_fields.keys()
required = ['workflow_name', 'input_schema', 'output_schema', 'steps', 'output']
for field in required:
    assert field in fields, f'{field} not found in existing schema'

print('Existing schema compatibility check passed')
print('Fields:', list(fields))
"
  ```
- **pytestメソッド**: `test_tc_007_schema_compatibility`

### TC-008: JSON Schema妥当性検証（詳細）
- **テスト観点**: AC-6 JSON Schemaが完全に妥当である
- **関連する受入条件**: AC-6
- **関連する設計方針**: DP-2
- **テスト種別**: E2E
- **テスト方法**: jsonschemaライブラリ
- **前提条件**:
  1. TC-001が成功している
  2. jsonschemaライブラリがインストールされている
- **テスト手順**:
  1. JSON Schemaを読み込み
  2. jsonschema.Draft202012Validatorで検証
  3. $defsの参照が解決されることを確認
- **期待結果**:
  - スキーマが有効
  - すべての$refが解決される
- **Bashコマンド**:
  ```bash
  pip install jsonschema

  python -c "
import json
from jsonschema import Draft202012Validator

with open('shared/schemas/taskflow/v1/workflow.schema.json') as f:
    schema = json.load(f)

# スキーマ自体の妥当性検証
Draft202012Validator.check_schema(schema)
print('JSON Schema is valid')

# テストデータでの検証（サンプルワークフロー）
validator = Draft202012Validator(schema)
sample_workflow = {
    'workflow_name': 'test_workflow',
    'description': 'Test',
    'input_schema': {'query': 'string'},
    'output_schema': {'result': 'string'},
    'steps': [{
        'id': 'step_001',
        'type': 'api_rest',
        'config': {
            'step_type': 'api_rest',
            'method': 'GET',
            'url': 'https://api.example.com'
        }
    }],
    'output': {'result': '\${step_001.output}'}
}
# Note: This may fail if schema requires different structure - adjust accordingly
print('Sample workflow structure created')
"
  ```
- **pytestメソッド**: `test_tc_008_json_schema_detailed_validation`

### TC-009: CI統合確認（ドライラン）
- **テスト観点**: CI/CDパイプラインでスクリプトが実行可能
- **関連する受入条件**: 技術要件（GitHub Actions CI統合）
- **関連する設計方針**: DP-3
- **テスト種別**: E2E
- **テスト方法**: Bashコマンド
- **前提条件**:
  1. 必要なツールがインストールされている
- **テスト手順**:
  1. CI環境をシミュレート（クリーンな状態から）
  2. 依存関係インストール
  3. スクリプト実行
  4. 検証実行
- **期待結果**:
  - すべてのステップが成功
- **Bashコマンド**:
  ```bash
  # CI環境シミュレーション
  echo "=== CI Simulation Start ==="

  # 1. 依存関係確認
  which python && python --version
  which npm && npm --version
  which datamodel-codegen || pip install datamodel-code-generator

  # 2. スクリプト実行
  python scripts/generate_schemas.py

  # 3. 生成ファイル確認
  test -f graphAiServer/src/engine/schemas/generated/taskflow.d.ts && echo "TypeScript generated: OK"
  test -f expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/schemas/generated/taskflow_types.py && echo "Pydantic generated: OK"

  echo "=== CI Simulation End ==="
  ```
- **pytestメソッド**: `test_tc_009_ci_integration_dryrun`

---

## 8. テスト実行計画

### 実行順序
1. TC-001: JSON Schemaファイル存在確認
2. TC-002: 生成スクリプト存在確認
3. TC-003: 生成スクリプト実行
4. TC-004: TypeScript型コンパイル確認
5. TC-005: Pydanticモデルインポート確認
6. TC-006: 既存テスト互換性確認
7. TC-007: スキーマ互換性検証
8. TC-008: JSON Schema妥当性検証（詳細）
9. TC-009: CI統合確認（ドライラン）

### 依存関係

```
TC-001 ─┬─> TC-003 ─┬─> TC-004
TC-002 ─┘           ├─> TC-005
                    ├─> TC-006
                    └─> TC-007

TC-001 ─────────────────> TC-008

TC-001 ─┬─> TC-009
TC-002 ─┘
```

### 成功基準
- [ ] TC-001: JSON Schemaファイルが存在し、Draft 2020-12準拠
- [ ] TC-002: 生成スクリプトが存在し、構文エラーなし
- [ ] TC-003: スクリプト実行が成功し、ファイルが生成される
- [ ] TC-004: 生成されたTypeScriptがコンパイル成功
- [ ] TC-005: 生成されたPydanticモデルがインポート成功
- [ ] TC-006: 既存テストがすべてパス
- [ ] TC-007: スキーマ互換性が確認される
- [ ] TC-008: JSON Schema妥当性が検証される
- [ ] TC-009: CI統合ドライランが成功

### 受入テストファイル

```
expertAgent/tests/acceptance/test_issue_357_acceptance.py
```

---

## 9. 補足事項

### 技術的考慮事項

1. **json-schema-to-typescript の制限**
   - 複雑な型（oneOf, anyOf）の変換に制限がある可能性
   - 生成結果の手動補完が必要になる可能性あり

2. **datamodel-code-generator の制限**
   - Pydantic v2との互換性を確認
   - `--output-model-type pydantic_v2.BaseModel` オプションの使用

3. **既存スキーマとの差異**
   - 既存の `taskflow_schema.py` は OpenAI Structured Output 対応のため、Union型を避けている
   - 生成されたスキーマとの差異を確認し、必要に応じてAdapterを使用

4. **バージョニング**
   - `shared/schemas/taskflow/v1/` のバージョンディレクトリ構造
   - 将来的なスキーマ変更時の互換性管理

### 手動検証項目（ユーザー実施）

Issue #357の受入基準に記載された手動検証項目:

1. **運用検証**:
   - [ ] JSON Schema変更 → 生成スクリプト実行 → 各システムで動作確認
   - [ ] スキーマバージョニング戦略が文書化されている

### 参考リンク

- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12/json-schema-core.html)
- [json-schema-to-typescript](https://github.com/bcherny/json-schema-to-typescript)
- [datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator)
- 設計方針書: `dev-reports/investigation/issue-353-pending-workflow/schema-unification-proposal.md`
