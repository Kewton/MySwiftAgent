# 作業計画書: Issue #333

**Issue**: #333 ワークフロー生成時のAPI型・フィールド名検証機能
**作成日**: 2025-12-30
**対象プロジェクト**: expertAgent

---

## 参照ドキュメント

### 必須参照
- [x] [設計方針書](./design-policy.md)
- [x] [アーキテクチャレビュー](./architecture-review.md)
- [x] [job-generation-workflow.md](../../../docs/spec/job-generation-workflow.md) - LangGraphエージェント設計
- [x] [API_REFERENCE.md](../../../expertAgent/docs/API_REFERENCE.md) - API仕様

### 推奨参照
- [x] [GRAPHAI_WORKFLOW_GENERATION_RULES.md](../../../graphAiServer/docs/GRAPHAI_WORKFLOW_GENERATION_RULES.md) - ワークフロー生成ルール

---

## 作業概要

### 目的
ワークフロー生成時にAPI型・フィールド名の整合性を検証し、実行時エラー（HTTP 422）を事前に防止する。

### 背景
Issue #331 完了後も、以下の問題が発生していた：
1. **型ミスマッチ**: fetchAgent出力（Object型）を String型フィールドに渡す
2. **フィールド名エラー**: `system_prompt` vs `system_imput`（タイポ）

### 成果物
1. 強化されたワークフロー生成プロンプト
2. `workflow_schema_validator_node` 実装
3. APIスキーマのタイポ修正
4. 単体テスト（カバレッジ90%以上）

---

## Phase分解

### Phase 1: プロンプト強化（即効性・低コスト）

**目標**: ワークフロー生成時に型検証ルールをLLMに明示し、エラーを生成段階で防止

**作業項目**:

| No | タスク | ファイル | 工数 |
|----|--------|----------|------|
| 1-1 | 型検証ルール定数の追加 | `prompts/workflow_generation.py` | 0.5h |
| 1-2 | プロンプトへのルール組み込み | `prompts/workflow_generation.py` | 0.5h |
| 1-3 | 単体テスト作成 | `tests/unit/test_workflow_generation_prompts.py` | 1h |
| 1-4 | 動作確認 | - | 0.5h |

**追加コード（Phase 1-1, 1-2）**:
```python
# expertAgent/aiagent/langgraph/workflowGeneratorAgents/prompts/workflow_generation.py

TYPE_VALIDATION_RULES = """
## 重要な型検証ルール

### fetchAgent出力の型
- fetchAgentの出力は常にObject型（辞書）
- :previous_node は前ノードの出力全体を参照（Object型）
- :previous_node.field で特定フィールドを参照可能

### API期待型の確認
- `/v1/aiagent/utility/jsonoutput` の `user_input` は **String型** を期待
- Object型を渡す場合は `stringTemplateAgent` で JSON文字列に変換必要

### stringTemplateAgent による型変換パターン
```yaml
convert_to_string:
  agent: stringTemplateAgent
  inputs:
    text: "${JSON.stringify(:previous_node)}"
  isResult: false

next_node:
  agent: fetchAgent
  inputs:
    body:
      user_input: :convert_to_string.text  # String型
```

### フィールド名検証
- capabilities.yaml の Request Schema を正確に参照
- 特に注意: `system_prompt`（正しいフィールド名）
"""
```

**完了条件**:
- [ ] TYPE_VALIDATION_RULES が workflow_generation.py に追加
- [ ] WORKFLOW_GENERATION_PROMPT にルールが組み込み
- [ ] 単体テストがパス
- [ ] Ruff/MyPy エラーゼロ

---

### Phase 2: 検証ノード実装（高信頼性）

**目標**: `workflow_schema_validator_node` を追加し、生成後に静的検証を実行

**作業項目**:

| No | タスク | ファイル | 工数 |
|----|--------|----------|------|
| 2-1 | State フィールド追加 | `state.py` | 0.5h |
| 2-2 | 検証ノード実装 | `nodes/workflow_schema_validator.py` | 2h |
| 2-3 | グラフエッジ追加 | `agent.py` | 0.5h |
| 2-4 | capabilities.yaml コピー | `utils/config/` | 0.5h |
| 2-5 | 単体テスト作成 | `tests/unit/test_workflow_schema_validator.py` | 2h |
| 2-6 | 結合テスト作成 | `tests/integration/test_workflow_generator_validation.py` | 1h |

**State フィールド追加（Phase 2-1）**:
```python
# expertAgent/aiagent/langgraph/workflowGeneratorAgents/state.py

class WorkflowGeneratorState(TypedDict, total=False):
    # ... 既存フィールド ...

    # ===== Schema Validation (Issue #333) =====
    schema_validation_result: dict[str, Any] | None
    schema_validation_issues: list[dict[str, Any]]
    has_schema_errors: bool
```

**create_initial_state() 更新**:
```python
def create_initial_state(...) -> WorkflowGeneratorState:
    return {
        # ... 既存フィールド ...
        "schema_validation_result": None,
        "schema_validation_issues": [],
        "has_schema_errors": False,
    }
```

**検証ノード実装（Phase 2-2）**:
```python
# expertAgent/aiagent/langgraph/workflowGeneratorAgents/nodes/workflow_schema_validator.py

async def workflow_schema_validator_node(
    state: WorkflowGeneratorState,
) -> WorkflowGeneratorState:
    """Validate API schema compatibility in generated workflow.

    Checks:
    1. Type compatibility (Object vs String)
    2. Field name correctness
    3. Required fields presence
    """
    # 実装詳細は design-policy.md 参照
```

**グラフエッジ追加（Phase 2-3）**:
```python
# expertAgent/aiagent/langgraph/workflowGeneratorAgents/agent.py

# workflow_tester → workflow_schema_validator → validator
workflow.add_node("workflow_schema_validator", workflow_schema_validator_node)
workflow.add_edge("workflow_tester", "workflow_schema_validator")
workflow.add_edge("workflow_schema_validator", "validator")
```

**完了条件**:
- [ ] State に新規フィールド追加
- [ ] workflow_schema_validator_node が実装
- [ ] グラフに新ノードが組み込み
- [ ] 単体テストカバレッジ90%以上
- [ ] 結合テストがパス
- [ ] Ruff/MyPy エラーゼロ

---

### Phase 3: APIスキーマ修正（根本原因解消）

**目標**: `system_imput` タイポを修正し、後方互換性を維持

**作業項目**:

| No | タスク | ファイル | 工数 |
|----|--------|----------|------|
| 3-1 | スキーマ修正（エイリアス付き） | `app/schemas/standardAiAgent.py` | 0.5h |
| 3-2 | 影響範囲調査 | - | 0.5h |
| 3-3 | 既存テスト修正 | `tests/` | 1h |
| 3-4 | 移行ガイド作成（必要に応じて） | `docs/` | 0.5h |

**スキーマ修正（Phase 3-1）**:
```python
# expertAgent/app/schemas/standardAiAgent.py

from pydantic import Field

class ExpertAiAgentRequest(BaseModel):
    user_input: str
    system_prompt: str | None = Field(
        None,
        description="System prompt for LLM"
    )
    # 後方互換性のためエイリアスを設定（移行期間中）
    system_imput: str | None = Field(
        None,
        alias="system_imput",
        deprecated=True,
        description="[DEPRECATED] Use system_prompt instead"
    )
    # ... 他のフィールド

    def __init__(self, **data):
        # system_imput が渡された場合は system_prompt にマップ
        if "system_imput" in data and "system_prompt" not in data:
            data["system_prompt"] = data.pop("system_imput")
        super().__init__(**data)
```

**完了条件**:
- [ ] `system_prompt` フィールドが正式名称として使用可能
- [ ] `system_imput` が後方互換性のため引き続き動作
- [ ] deprecation warning がログ出力
- [ ] 既存テストがパス
- [ ] capabilities.yaml との整合性確保

---

## 品質担保

### テストカバレッジ目標

| カテゴリ | 目標 | 対象ファイル |
|---------|------|-------------|
| 単体テスト | 90%以上 | `workflow_schema_validator.py`, `workflow_generation.py` |
| 結合テスト | 50%以上 | workflowGeneratorAgents 全体 |

### 静的解析

```bash
# Phase 完了時に実行
cd expertAgent
uv run ruff check aiagent/langgraph/workflowGeneratorAgents/
uv run mypy aiagent/langgraph/workflowGeneratorAgents/
```

### pre-push チェック

```bash
# PR 作成前に実行
./scripts/pre-push-check-all.sh
```

---

## スケジュール

| Phase | タスク | 工数 | 状態 |
|-------|--------|------|------|
| Phase 1 | プロンプト強化 | 2.5h | 未着手 |
| Phase 2 | 検証ノード実装 | 6.5h | 未着手 |
| Phase 3 | APIスキーマ修正 | 2.5h | 未着手 |
| **合計** | | **11.5h** | |

---

## リスクと対策

| リスク | 影響度 | 対策 |
|--------|--------|------|
| Phase 3 の後方互換性破壊 | 高 | エイリアス設定 + 移行期間 |
| 検証ルールの過剰検出 | 中 | warning レベルの調整 |
| パフォーマンス劣化 | 低 | ~4ms 追加のみ、影響なし |

---

## 完了条件チェックリスト

### コード品質原則
- [ ] SOLID原則: 遵守（単一責任の検証ノード）
- [ ] KISS原則: 遵守（ルールベース検証優先）
- [ ] YAGNI原則: 遵守（必要最小限の検証ルール）
- [ ] DRY原則: 遵守（_issue() ヘルパー共通化）

### 品質担保方針
- [ ] 単体テストカバレッジ: 90%以上
- [ ] 結合テストカバレッジ: 50%以上
- [ ] Ruff linting: エラーゼロ
- [ ] MyPy type checking: エラーゼロ

### CI/CD準拠
- [ ] PRラベル: `feature` ラベル付与
- [ ] コミットメッセージ: 規約準拠
- [ ] pre-push-check-all.sh: パス

---

## 次のステップ

1. **Phase 1 着手**: `prompts/workflow_generation.py` の修正
2. **テスト実行**: 単体テスト作成・実行
3. **Phase 2 着手**: 検証ノード実装

---

**作成者**: Claude Code
**承認待ち**: ユーザー
