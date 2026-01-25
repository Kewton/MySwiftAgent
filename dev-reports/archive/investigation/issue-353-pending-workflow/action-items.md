# __PENDING__ 問題 - アクションアイテム

**更新日**: 2026-01-12

## 完了済み

- [x] 根本原因の特定（スキーマ形式の不一致）
- [x] 既存データのクリーンアップ（124件をソフトデリート）
- [x] 問題レポートの作成
- [x] TaskFlowスキーマ総点検（追加の不整合を特定）

## 未対応（要修正）

### P0: 即時対応（`__PENDING__` 問題解決に必須）

- [ ] `workflow_registrar.py` に JSON文字列→オブジェクト変換処理を追加
  - 対象フィールド（ワークフローレベル）: `input_schema`, `output_schema`, `output`
  - 対象フィールド（ステップレベル）: `steps[*].config.body`（JSONの場合）
  - 実装箇所: `register_taskflow_workflow()` 関数内

```python
# 追加すべきコード（完全版）
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

    # ステップレベルの変換（config.body）
    if "steps" in result:
        for step in result["steps"]:
            if "config" in step and isinstance(step["config"].get("body"), str):
                try:
                    step["config"]["body"] = json.loads(step["config"]["body"])
                except json.JSONDecodeError:
                    pass

    return result
```

### P1: 中期対応

- [ ] 登録失敗時のエラーハンドリングを致命的エラーに変更
  - 対象: `workflow.py` 341-355行
  - 変更: `logger.warning` → `raise WorkflowError`

- [ ] `TaskFlowStep.params` の値型を拡張
  - 現状: `dict[str, str] | None`（文字列のみ）
  - 変更後: `dict[str, Any] | None`（任意の値）
  - 理由: GraphAiServerは `Record<string, unknown>` を期待

- [ ] `UnifiedStepConfig.body` の型を変更
  - 現状: `str | None`（JSON文字列）
  - 変更後: `Any`（任意のJSONオブジェクトも許容）

### P2: 長期対応

- [ ] Pydanticスキーマの `input_schema` 等を `str` から `dict` に変更
  - 注意: OpenAI Structured Output制約を考慮した設計が必要
- [ ] LLM出力の安定性テスト実施
- [ ] ステップレベルの `input_schema`/`output_schema` 追加
  - GraphAiServerは `IOSchema.optional()` をサポート
- [ ] transform設定の拡張
  - `source_field`: `z.string().optional()`
  - `strategy`: `z.enum(['shallow', 'deep']).optional()`

### P3: 将来検討

- [ ] Parallel/Conditionalブロックの再検討（非OpenAI LLM使用時）

## 関連ドキュメント

| ドキュメント | 内容 |
|-------------|------|
| [root-cause-analysis.md](./root-cause-analysis.md) | `__PENDING__` 問題の根本原因分析 |
| [taskflow-schema-comparison.md](./taskflow-schema-comparison.md) | GraphAiServer/ExpertAgent間のスキーマ総点検結果 |

## テスト確認

修正後、以下を確認：

1. 新規ジョブ生成が成功する
2. 生成されたジョブが実行可能
3. `__PENDING__` が残存しない
4. 複雑なパラメータ（ネストしたオブジェクト等）が正しく渡される
