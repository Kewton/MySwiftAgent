# TaskFlow スキーマ総点検レポート

**作成日**: 2026-01-12
**関連Issue**: #353 (`__PENDING__` 問題の根本原因調査)
**ステータス**: 調査完了

---

## 1. 概要

GraphAiServer（TypeScript/Zod）とExpertAgent（Python/Pydantic）間のTaskFlowスキーマを比較し、不整合を特定した。

### 調査対象ファイル

| システム | ファイル | 役割 |
|---------|---------|------|
| GraphAiServer | `src/engine/schemas/workflow-schema.ts` | Zodによるバリデーションスキーマ |
| GraphAiServer | `src/types/taskflow.ts` | TypeScript型定義 |
| ExpertAgent | `aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/schemas/taskflow_schema.py` | Pydanticスキーマ（LLM生成用） |
| ExpertAgent | `aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/workflow_registrar.py` | ワークフロー登録処理 |

---

## 2. 不整合一覧

### 2.1 ワークフローレベル（致命的）

| フィールド | GraphAiServer (Zod) | ExpertAgent (Pydantic) | 重大度 | 影響 |
|-----------|---------------------|------------------------|--------|------|
| `input_schema` | `IOSchema` = `Record<string, SimpleType>` (オブジェクト) | `str` (JSON文字列) | **P0** | 登録失敗 |
| `output_schema` | `IOSchema` (オブジェクト) | `str` (JSON文字列) | **P0** | 登録失敗 |
| `output` | `Record<string, string>` (オブジェクト) | `str` (JSON文字列) | **P0** | 登録失敗 |

**根本原因**: ExpertAgentはOpenAI Structured Outputとの互換性のため、これらのフィールドをJSON文字列として生成している。しかしGraphAiServerはオブジェクトを期待している。

**エラー例**:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid workflow definition",
    "details": {
      "errors": [
        {"path": "input_schema", "message": "Required", "suggestion": "Expected object, got undefined"}
      ]
    }
  }
}
```

### 2.2 ステップレベル（機能制限）

| フィールド | GraphAiServer (Zod) | ExpertAgent (Pydantic) | 重大度 | 影響 |
|-----------|---------------------|------------------------|--------|------|
| `params` | `Record<string, unknown>` (任意の値) | `dict[str, str] \| None` (文字列のみ) | **P1** | 複雑なパラメータが渡せない |
| `input_schema` | `IOSchema.optional()` | なし | **P2** | ステップ単位のスキーマ定義不可 |
| `output_schema` | `IOSchema.optional()` | なし | **P2** | ステップ単位のスキーマ定義不可 |
| `description` | `z.string().optional()` | なし (TaskFlowStepに存在しない) | **P3** | ステップ説明なし |

### 2.2.1 デフォルト値の差異

| フィールド | GraphAiServer デフォルト | ExpertAgent デフォルト | 影響 |
|-----------|------------------------|----------------------|------|
| `timeout_ms` | `30000` | `None` (未設定) | GraphAiServer側でデフォルト適用 |
| `verify_ssl` | `true` | `None` (未設定) | GraphAiServer側でデフォルト適用 |
| `function_name` | `'main'` | `None` (未設定) | GraphAiServer側でデフォルト適用 |
| `mode` (transform) | `'template'` | `None` (未設定) | GraphAiServer側でデフォルト適用 |
| `params` | `{}` (空オブジェクト) | `None` | GraphAiServer側でデフォルト適用 |

**注**: デフォルト値の差異は、GraphAiServer側でデフォルトが適用されるため機能上の問題は少ないが、テスト時の挙動差異に注意。

### 2.3 設定レベル（機能制限）

| フィールド | GraphAiServer (Zod) | ExpertAgent (Pydantic) | 重大度 | 影響 |
|-----------|---------------------|------------------------|--------|------|
| `body` (api_rest) | `z.unknown().optional()` (任意のJSON) | `str \| None` (JSON文字列) | **P1** | bodyが文字列として送信される可能性 |
| `source_field` (transform) | `z.string().optional()` | なし | **P2** | transform機能制限 |
| `strategy` (transform) | `z.enum(['shallow', 'deep']).optional()` | なし | **P2** | merge戦略指定不可 |

### 2.4 構造的差異

| 機能 | GraphAiServer | ExpertAgent | 理由 |
|------|--------------|-------------|------|
| Parallel blocks | `ParallelBlockSchema`でサポート | 削除済み | OpenAI Structured Output非対応 |
| Conditional blocks | `ConditionalBlockSchema`でサポート | 削除済み | OpenAI Structured Output非対応 |
| Config分離 | 型ごとに別スキーマ | `UnifiedStepConfig`で統合 | OpenAI Union型非対応 |

---

## 3. 型の詳細比較

### IOSchema (GraphAiServer)

```typescript
// workflow-schema.ts:30-40
export const SimpleTypeSchema = z.enum([
  'string', 'number', 'boolean', 'object', 'array',
  'string[]', 'number[]', 'boolean[]', 'object[]', 'array[]', 'any'
]);

export const IOSchema = z.record(z.string(), SimpleTypeSchema);
// 例: { "query": "string", "count": "number" }
```

### input_schema/output_schema (ExpertAgent)

```python
# taskflow_schema.py:338-345
input_schema: str = Field(
    ...,
    description='Input field definitions as JSON string. Example: \'{"query": "string"}\'',
)
output_schema: str = Field(
    ...,
    description='Output field definitions as JSON string. Example: \'{"result": "string"}\'',
)
# LLMが生成する値: '{"query": "string"}'（文字列）
```

---

## 4. 修正方針

### 4.1 P0: 即時対応（`__PENDING__` 問題解決に必須）

**`workflow_registrar.py` に変換処理を追加**:

```python
import json

def convert_json_strings_to_objects(workflow_json: dict) -> dict:
    """GraphAiServer互換のためJSON文字列フィールドをオブジェクトに変換."""
    result = workflow_json.copy()

    # ワークフローレベルの変換
    for field in ["input_schema", "output_schema", "output"]:
        if field in result and isinstance(result[field], str):
            try:
                result[field] = json.loads(result[field])
            except json.JSONDecodeError:
                pass  # 変換失敗時は元の値を保持

    # ステップレベルの変換（必要に応じて）
    if "steps" in result:
        for step in result["steps"]:
            if "config" in step and isinstance(step["config"].get("body"), str):
                try:
                    step["config"]["body"] = json.loads(step["config"]["body"])
                except json.JSONDecodeError:
                    pass

    return result

async def register_taskflow_workflow(
    workflow_name: str,
    workflow_json: dict,
    admin_token: str | None = None,
) -> WorkflowRegistrationResult:
    # 変換処理を追加
    converted_json = convert_json_strings_to_objects(workflow_json)

    payload = {
        "workflow_name": workflow_name,
        "definition": converted_json,  # 変換後のJSONを使用
        "overwrite": True,
    }
    # ...
```

### 4.2 P1: 中期対応

1. **paramsの値型拡張**: `dict[str, str]` → `dict[str, Any]`
2. **bodyの型変更**: `str | None` → `Any`（JSONオブジェクトも許容）

### 4.3 P2: 長期対応

1. **ステップレベルのinput_schema/output_schema追加**
2. **transform設定の完全化**（source_field, strategy）
3. **Parallel/Conditionalブロックの再検討**（非OpenAI LLM利用時）

---

## 5. OpenAI Structured Output制約

ExpertAgentがJSON文字列を使用する理由:

| 制約 | 説明 |
|------|------|
| **Union型非対応** | `Union[A, B]` は使用不可 → UnifiedStepConfigで統合 |
| **additionalProperties制限** | 動的キーを持つオブジェクトの生成が困難 |
| **再帰型非対応** | 自己参照型は使用不可 → Parallel/Conditional削除 |

**対策**: JSON文字列としてLLMに生成させ、登録時にオブジェクトへ変換する。

---

## 6. 変換が必要なフィールドの完全リスト

### ワークフローレベル

| フィールドパス | ExpertAgent出力 | GraphAiServer期待 | 変換方法 |
|---------------|-----------------|-------------------|---------|
| `input_schema` | `str` | `object` | `json.loads()` |
| `output_schema` | `str` | `object` | `json.loads()` |
| `output` | `str` | `object` | `json.loads()` |

### ステップレベル（config内）

| フィールドパス | ExpertAgent出力 | GraphAiServer期待 | 変換方法 |
|---------------|-----------------|-------------------|---------|
| `steps[*].config.body` | `str` | `any` | `json.loads()` (JSONの場合) |

---

## 7. 検証コマンド

### 変換前後のスキーマ確認

```bash
# ExpertAgentで生成されたワークフローの確認
curl -s http://localhost:8004/api/v1/workflow-gen/debug/last-generated | jq '.workflow'

# GraphAiServerでの登録テスト
curl -X POST http://localhost:8005/api/v2/workflows/validate \
  -H "Content-Type: application/json" \
  -d '{"definition": <上記の出力>}'
```

---

## 8. 関連ドキュメント

- [root-cause-analysis.md](./root-cause-analysis.md) - `__PENDING__` 問題の根本原因分析
- [action-items.md](./action-items.md) - 対応アクションアイテム

---

## 9. 次のアクション

| 優先度 | アクション | 推定工数 |
|--------|----------|---------|
| **P0** | `workflow_registrar.py` に `convert_json_strings_to_objects` を追加 | 2h |
| **P1** | `UnifiedStepConfig.body` の型を `Any` に変更 | 1h |
| **P1** | `TaskFlowStep.params` の値型を `Any` に変更 | 1h |
| **P2** | ステップレベルの `input_schema`/`output_schema` を追加 | 4h |
| **P2** | transform設定の拡張 | 2h |
