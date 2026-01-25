# __PENDING__ ワークフロー問題 - 根本原因分析レポート

**作成日**: 2026-01-12
**関連Issue**: #353
**ステータス**: 調査完了・クリーンアップ済み

---

## 1. 問題の概要

### 現象
Job Generator V2 で生成されたジョブを実行すると、以下のエラーで失敗する：

```
HTTP 404: {"error":{"code":"NOT_FOUND","message":"Workflow '__PENDING__' not found"}}
```

### 影響範囲
- **影響件数**: 124件の TaskMaster（クリーンアップ前）
- **影響率**: 全896件中の約14%
- **サービス影響**: 該当ジョブは実行不可

---

## 2. 根本原因

### 直接原因：スキーマ形式の不一致

Python側（LLM生成）は `input_schema`、`output_schema`、`output` を **JSON文字列** として生成：

```json
{
  "input_schema": "{\"query\": \"string\"}",
  "output_schema": "{\"result\": \"string\"}",
  "output": "{\"result\": \"${step_001.output}\"}"
}
```

GraphAiServer は同じフィールドを **JSONオブジェクト** として期待：

```json
{
  "input_schema": {"query": "string"},
  "output_schema": {"result": "string"},
  "output": {"result": "${step_001.output}"}
}
```

### 技術的詳細

| 項目 | 詳細 |
|------|------|
| **問題箇所** | `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/workflow_registrar.py` |
| **原因コード** | `register_taskflow_workflow()` が `workflow_json` をそのまま送信 |
| **欠落処理** | JSON文字列フィールドをオブジェクトに変換する処理がない |

### GraphAiServer側のバリデーション

```typescript
// graphAiServer/src/engine/schemas/workflow-schema.ts
export const IOSchema = z.record(z.string(), SimpleTypeSchema);
// → input_schema は object (record) を期待
```

### エラーメッセージ

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid workflow definition",
    "details": {
      "errors": [
        {"path": "input_schema", "message": "Required", "suggestion": "Expected object, got undefined"},
        {"path": "output_schema", "message": "Required", "suggestion": "Expected object, got undefined"},
        {"path": "output", "message": "Required", "suggestion": "Expected object, got undefined"}
      ]
    }
  }
}
```

---

## 3. なぜ `__PENDING__` が残存するか

### フェーズ間の処理フロー

```
REGISTRATION フェーズ:
  └── TaskMaster 作成
      └── body_template.workflow_name = "__PENDING__" (プレースホルダー)

WORKFLOW_GEN フェーズ:
  ├── 1. ワークフロー生成 (LLM) → 成功
  ├── 2. GraphAiServer 登録 → 失敗（スキーマ不一致）
  └── 3. TaskMaster 更新 → スキップ（登録失敗のため）

結果:
  └── body_template.workflow_name = "__PENDING__" のまま
```

### エラーハンドリングの問題

```python
# workflow.py:341-355
if not registration_result["success"]:
    logger.warning(
        "Workflow registration failed: %s",
        registration_result.get("error"),
    )
    # Registration failure is not fatal  ← ★問題：致命的エラーを非致命的として処理
```

---

## 4. 修正方法

### 即時対応（必須）

`workflow_registrar.py` に変換処理を追加：

```python
import json

def convert_json_strings_to_objects(workflow_json: dict) -> dict:
    """Convert JSON string fields to objects for GraphAiServer compatibility."""
    result = workflow_json.copy()
    for field in ["input_schema", "output_schema", "output"]:
        if field in result and isinstance(result[field], str):
            try:
                result[field] = json.loads(result[field])
            except json.JSONDecodeError:
                pass  # Keep as string if parsing fails
    return result

async def register_taskflow_workflow(...):
    # 変換処理を追加
    converted_json = convert_json_strings_to_objects(workflow_json)
    payload = {
        "workflow_name": workflow_name,
        "definition": converted_json,  # ← 変換後のJSONを使用
        "overwrite": True,
    }
    ...
```

### 中期対応（推奨）

1. **Pydanticスキーマの修正**: `input_schema` などを `dict` 型に変更
2. **エラーハンドリング強化**: 登録失敗を致命的エラーとして処理
3. **finalizationガード強化**: `__PENDING__` 検出時にジョブ登録をブロック（Issue #353で部分対応済み）

---

## 5. クリーンアップ実施結果

### 実施内容

```bash
# 2026-01-12 実行
# __PENDING__ を持つ全 TaskMaster をソフトデリート (is_active: false)
```

### 結果

| 項目 | 値 |
|------|-----|
| 対象件数 | 124件 |
| 削除成功 | 124件 |
| 残存（アクティブ） | 0件 |

### 確認コマンド

```bash
# クリーンアップ後の確認
curl -s "http://localhost:8001/api/v1/task-masters?size=100" | \
  jq '[.masters[] | select(.is_active == true and .body_template.workflow_name == "__PENDING__")] | length'
# → 0
```

---

## 6. 関連ファイル

| ファイル | 役割 |
|---------|------|
| `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/workflow_registrar.py` | ワークフロー登録処理 |
| `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/workflow_gen/schemas/taskflow_schema.py` | TaskFlow Pydanticスキーマ |
| `expertAgent/aiagent/langgraph/jobGeneratorV2/workflows/registration/master_manager.py` | TaskMaster作成（`__PENDING__`設定箇所） |
| `graphAiServer/src/engine/schemas/workflow-schema.ts` | GraphAiServer側のZodスキーマ |

---

## 7. 次のアクション

| 優先度 | アクション | 担当 |
|--------|----------|------|
| **P0** | `workflow_registrar.py` に JSON文字列→オブジェクト変換を追加 | 開発チーム |
| **P1** | 登録失敗時のエラーハンドリングを致命的エラーに変更 | 開発チーム |
| **P2** | Pydanticスキーマを `dict` 型に変更（LLM出力の安定性確認後） | 開発チーム |

---

## 8. 教訓

1. **型の整合性**: Python（Pydantic）とTypeScript（Zod）間のスキーマ型は明示的に確認する
2. **Fail-Fast原則**: 登録失敗は「非致命的」として処理せず、即座に失敗させる
3. **中間状態の管理**: `__PENDING__` のようなプレースホルダーは、トランザクション的に管理する
