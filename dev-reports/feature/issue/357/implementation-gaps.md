# Issue #354関連 実装ギャップ報告書

**作成日**: 2026-01-13
**関連Issue**: #354, #355, #356, #357
**調査トリガー**: Job Generator V2 で `SCHEMA_INVALID_UNION` エラー発生

---

## 1. エグゼクティブサマリー

Issue #354（TaskFlowスキーマ統一化）の関連Issueについて実装状況を調査した結果、以下の問題を発見・修正しました。

| カテゴリ | 件数 |
|---------|------|
| 本日修正済み | 4件 |
| 要対応（未修正） | 0件 |
| 設計上の注意点 | 2件 |

---

## 2. 発見した問題と修正状況

### 2.1 修正済みの問題

#### 問題1: TaskFlowAdapterがnullフィールドを削除していない (Issue #355)

| 項目 | 内容 |
|------|------|
| **重大度** | High |
| **状態** | **修正済み** |
| **修正ファイル** | `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/adapter/taskflow_adapter.py` |

**症状**:
- Job Generator V2でワークフロー生成後、GraphAiServerへの登録時に`SCHEMA_INVALID_UNION`エラーが発生
- エラー箇所: `steps.0`, `steps.1`

**根本原因**:
ExpertAgentの`UnifiedStepConfig`（Pydanticモデル）はOpenAI Structured Output互換のため、全step typeのフィールドを単一モデルに統合している。`model_dump()`実行時、未使用フィールドは`null`で出力される。

```python
# ExpertAgent出力例（api_rest step）
{
  "step_type": "api_rest",
  "method": "GET",
  "url": "https://...",
  "mode": null,       # transform用フィールド（不要）
  "template": null,   # transform用フィールド（不要）
  "path": null,       # code_js用フィールド（不要）
  "function_name": null  # code_js用フィールド（不要）
}
```

GraphAiServerのZodスキーマは`discriminatedUnion`を使用しており、各step typeで定義されたフィールドのみ許可する。余分な`null`フィールドがあるとどの型にもマッチせず、バリデーションエラーとなる。

**修正内容**:
1. `STEP_TYPE_ALLOWED_FIELDS`定数を追加（各step typeの許可フィールドを定義）
2. `_clean_config()`メソッドを追加（nullフィールドとstep typeに不要なフィールドを削除）
3. `_convert_step()`メソッドでconfig cleanupを実行

```python
# 修正後のクリーンアップ後出力
{
  "step_type": "api_rest",
  "method": "GET",
  "url": "https://..."
}
```

---

#### 問題2: Contract testsのポート設定が不正 (Issue #356)

| 項目 | 内容 |
|------|------|
| **重大度** | Medium |
| **状態** | **修正済み** |
| **修正ファイル** | `expertAgent/tests/contract/conftest.py` |

**症状**:
- Contract testsの2件がスキップされていた（GraphAiServer not reachable）

**根本原因**:
`DEFAULT_GRAPHAI_SERVER_URL`が`http://localhost:8105`に設定されていたが、ローカル開発環境のGraphAiServerは`8005`で動作している。

**修正内容**:
```python
# Before
DEFAULT_GRAPHAI_SERVER_URL = "http://localhost:8105"

# After
DEFAULT_GRAPHAI_SERVER_URL = "http://localhost:8005"
```

---

#### 問題3: Contract testsのAPIリクエスト形式が不正 (Issue #356)

| 項目 | 内容 |
|------|------|
| **重大度** | Medium |
| **状態** | **修正済み** |
| **修正ファイル** | `expertAgent/tests/contract/test_taskflow_schema_contract.py` |

**症状**:
- GraphAiServerへのバリデーションリクエストが400エラー
- エラーメッセージ: `"definition is required"`

**根本原因**:
GraphAiServerの`/api/v2/workflows/validate`エンドポイントは`{"definition": ...}`形式を期待するが、テストはワークフローを直接送信していた。

**修正内容**:
```python
# Before
response = httpx.post(graphai_validate_url, json=data, ...)

# After
response = httpx.post(graphai_validate_url, json={"definition": data}, ...)
```

---

### 2.2 修正済みの問題（本日追加修正）

#### 問題4: スキーマ生成スクリプトの依存関係不足 (Issue #357)

| 項目 | 内容 |
|------|------|
| **重大度** | Medium |
| **状態** | **修正済み** |
| **修正ファイル** | `/pyproject.toml`, `README.md` |

**症状（修正前）**:
```bash
$ python scripts/generate_schemas.py
Step 3: Generating Pydantic models...
Python generation failed: No module named datamodel_code_generator
```

**根本原因**:
スクリプトは`datamodel-code-generator`パッケージを使用してJSON SchemaからPydanticモデルを生成するが、このパッケージがどのpyproject.tomlにも依存関係として登録されていなかった。

**修正内容**:
```toml
# /pyproject.toml に追加
[project.optional-dependencies]
schema-gen = [
    "datamodel-code-generator>=0.25.0",
    "jsonschema>=4.0.0",
]
```

**使用方法**:
```bash
# 依存関係のインストール
uv sync --extra schema-gen

# スキーマ生成
uv run python scripts/generate_schemas.py
```

---

### 2.3 設計上の注意点（技術的負債）

#### 注意点1: 生成されたPydanticモデルが未使用

| 項目 | 内容 |
|------|------|
| **リスク** | Low（現時点） |
| **将来リスク** | Medium |

**現状**:
- `generated/taskflow_types.py`（JSON Schemaから自動生成）は**テストでのみ使用**
- 実際のアプリケーションは`taskflow_schema.py`（手動作成、UnifiedStepConfig）を使用

**理由**:
OpenAI Structured Outputは`oneOf`（Union型）をサポートしないため、全フィールドを単一モデルに統合した`UnifiedStepConfig`が必要。

**リスク**:
- JSON Schemaと手動作成スキーマが乖離するリスク
- 将来的にメンテナンスコストが増加

**緩和策**:
- Contract testsで両スキーマの互換性を検証（実装済み）
- JSON Schema変更時は手動スキーマも更新する運用ルール

---

#### 注意点2: CI workflow のDockerイメージ依存

| 項目 | 内容 |
|------|------|
| **リスク** | Low |

**現状**:
`contract-tests.yml`のintegration testsはGraphAiServerのDockerイメージに依存:
```yaml
services:
  graphai:
    image: ghcr.io/${{ github.repository_owner }}/graphaiserver:latest
```

**リスク**:
- イメージが存在しない場合、integration testsがスキップされる
- `continue-on-error: true`設定のため、CIは失敗しない

**現状の対応**:
- unit testsは常に実行（GraphAiServer不要）
- integration testsはoptional（失敗してもCIは通過）

---

## 3. テスト結果

### 修正後のContract tests結果

```
======================== 15 passed, 8 warnings in 0.06s ========================
```

| テストカテゴリ | 件数 | 状態 |
|---------------|------|------|
| Adapter unit tests | 8 | PASSED |
| Schema contract tests | 5 | PASSED |
| GraphAiServer validation | 2 | PASSED |
| **合計** | **15** | **ALL PASSED** |

---

## 4. 推奨アクション

### 即座に対応が必要

| # | アクション | 優先度 | 状態 |
|---|-----------|--------|------|
| 1 | `datamodel-code-generator`を依存関係に追加 | Medium | **完了** |

### 将来的に検討

| # | アクション | 優先度 |
|---|-----------|--------|
| 2 | 生成スキーマと手動スキーマの差分検出テスト追加 | Low |
| 3 | GraphAiServer Dockerイメージの自動ビルド | Low |

---

## 5. 修正ファイル一覧

| ファイル | 変更内容 |
|---------|---------|
| `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/adapter/taskflow_adapter.py` | nullフィールド削除機能追加 |
| `expertAgent/tests/contract/conftest.py` | ポート設定修正 |
| `expertAgent/tests/contract/test_taskflow_schema_contract.py` | APIリクエスト形式修正 |
| `/pyproject.toml` | schema-genオプション依存関係追加 |
| `README.md` | Schema Generationセクション追加 |

---

## 6. 次のステップ

1. **ユーザー確認**: http://localhost:8000 でgenerate jobを実行し、成功を確認
2. ~~**依存関係修正**: `datamodel-code-generator`を追加（オプション）~~ → **完了**
3. **PR作成**: 本修正をdevelopブランチにマージ
