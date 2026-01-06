# 根本原因分析: Issue #338 ワークフロー生成の課題

**作成日**: 2026-01-06
**Issue**: [#338 Task Chain Interface Contract Enforcement](https://github.com/Kewton/MySwiftAgent/issues/338)

---

## 問題の全体像

テストジョブ（大谷翔平に関する最新情報をGoogle検索→サマリ生成→メール送信）の実行結果:

| Task | 結果 | スコア | 主要な問題 |
|------|------|-------|-----------|
| Task 1 (Google検索) | ✅ SUCCESS | 72 | "Critical" weakness が検出されたが通過 |
| Task 2 (サマリ生成) | ❌ FAILED | 25 | max_retries_exceeded |
| Task 3 (メール送信) | ❌ FAILED | - | `'str' object has no attribute 'get'` |

---

## 1. 誤ったフローを作り込んだ真因

### 真因 1-A: LLMの出力仮定と動的データの不整合

**現象**: Task 1のワークフローが「3件の検索結果」を固定で想定

**コード箇所**: `generator.py:206-208` (LLMへのプロンプト生成)

**問題の詳細**:
- ワークフロー生成時、LLMは検索結果の件数を動的に処理する設計ではなく、固定数(3件)のノードを生成
- `shiftAgent`で1件ずつ抽出する設計だが、0件や5件の場合への対応なし

```yaml
# 生成されたワークフローの問題パターン
nodes:
  extract_result_0:
    agent: shiftAgent
    inputs:
      array: :google_search.results
      index: 0
  extract_result_1:  # 結果が1件の場合は失敗
    agent: shiftAgent
    inputs:
      array: :google_search.results
      index: 1
```

**根本原因**: プロンプトに「動的な配列処理パターン」が含まれていない

---

### 真因 1-B: タスク間インターフェース契約の未定義

**現象**: Task 1の出力がTask 2の入力要件を満たさない

**コード箇所**: `sample_input_generator.py` (テストデータ生成)

**問題の詳細**:
- Task 1の`output_interface`に`search_results`配列が定義されている
- Task 2の`input_interface`は配列の各要素（title, snippet）を個別に期待
- 両者の契約が明示的に検証されていない

```python
# Task 1 Output
output_interface: {
  "schema": {
    "properties": {
      "search_results": {"type": "array", "items": {...}}  # 配列
    }
  }
}

# Task 2 Input (期待される形式)
input_interface: {
  "schema": {
    "properties": {
      "title": {"type": "string"},     # 個別フィールドを期待
      "snippet": {"type": "string"}
    }
  }
}
```

**根本原因**: タスクチェーン設計時に入出力インターフェースの整合性検証がない

---

### 真因 1-C: 複雑なスキーマに対するキーワード抽出の不備

**現象**: Task 2/3で「大谷翔平」キーワードが使用されない

**コード箇所**: `sample_input_generator.py:421-462`

**問題の詳細**:
- `_generate_string_sample()` は単純な文字列フィールドでのみキーワード抽出が機能
- ネストされたオブジェクトや配列内のフィールドでは `_TASK_CONTEXT` が参照されない

```python
# 現在のコード - 単純フィールドのみ対応
def _generate_string_sample(schema: dict, prop_name: str = "") -> str:
    # query_patterns に一致する場合のみキーワードを使用
    query_patterns = ["query", "keyword", "search", ...]
    if any(pattern in prop_lower for pattern in query_patterns):
        return _TASK_CONTEXT.get("primary_keyword")  # ここのみ機能
```

**根本原因**: 再帰的なスキーマ探索でコンテキストが伝播されない

---

## 2. 誤ったフローを検知・是正できなかった真因

### 真因 2-A: Critical評価と合格判定の乖離

**現象**: Task 1が「Critical」weakness を持ちながらスコア72で通過

**コード箇所**: `agent.py:145-161` (llm_evaluator_router)

```python
def llm_evaluator_router(state):
    failure_reason = evaluation_result.get("failure_reason", "none")

    # Critical weaknessがあってもfailure_reasonが"none"なら通過
    if failure_reason in ("workflow_quality", "both"):
        return "self_repair"  # ここに到達しない

    evaluation_score = state.get("evaluation_score") or 0
    if evaluation_score < 70:  # 72 >= 70 なので通過
        return "self_repair"  # ここに到達しない

    return "result_summary_generator"  # Critical なのに成功
```

**問題の詳細**:
- LLM評価が「Critical」を`weaknesses`に含めても、`failure_reason`を設定しない場合がある
- スコア72はしきい値70を超えているため、self-repairに入らない

**根本原因**: `failure_reason`がLLM判断任せで、weaknessesの重大度との連動がない

---

### 真因 2-B: 評価スコアと問題重大度の不一致

**現象**: test_data_quality_score = 25 でも max_retries_exceeded まで継続

**コード箇所**: `llm_evaluator.py:229-235`

```python
# 現在のロジック
is_acceptable = (
    evaluation_result.overall_score >= 70       # 72 >= 70 ✓
    and evaluation_result.requirement_score >= 60  # ?
    and evaluation_result.test_data_quality_score >= 50  # 25 < 50 ✗
    and not needs_regeneration
)
```

**問題の詳細**:
- `is_acceptable`の計算で`test_data_quality_score < 50`でも、ルーターは`evaluation_score`(72)のみを見る
- `is_acceptable=False`でも`final_is_valid`が`False`になるだけで、ルーターには影響しない

**根本原因**: `is_acceptable`フラグがルーティング判定に使用されていない

---

### 真因 2-C: Task 3のコード不具合 (`'str' object has no attribute 'get'`)

**現象**: Task 3でワークフロー生成前にクラッシュ

**コード箇所**: `workflow_generation.py:245-254` または類似箇所

**問題の詳細**:
- `recommended_apis`の形式が`list[str]`の場合と`list[dict]`の場合が混在
- 一部のコードパスでdict前提の`.get()`を呼び出している

```python
# 問題のあるコード例
for api in recommended_apis:
    api_name = api.get("api_name")  # api が str の場合エラー
```

**根本原因**: `recommended_apis`の型バリデーションが不完全

---

## 3. 真因の関係図

```
┌─────────────────────────────────────────────────────────────────┐
│                    根本原因の連鎖                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  [ワークフロー設計層]                                            │
│     │                                                           │
│     ├─ 動的配列処理パターンがプロンプトにない (1-A)              │
│     │     ↓                                                     │
│     └─ 固定数ノード生成 → 実データとの不整合                    │
│                                                                 │
│  [タスクチェーン層]                                              │
│     │                                                           │
│     ├─ 入出力インターフェース検証がない (1-B)                   │
│     │     ↓                                                     │
│     └─ Task間でデータ形式が合わない                             │
│                                                                 │
│  [テストデータ生成層]                                            │
│     │                                                           │
│     ├─ キーワード抽出がネストスキーマ未対応 (1-C)               │
│     │     ↓                                                     │
│     └─ 汎用データで検証 → 実運用時との乖離                      │
│                                                                 │
│  [評価・検知層]                                                  │
│     │                                                           │
│     ├─ Critical評価がルーティングに反映されない (2-A)           │
│     │                                                           │
│     ├─ is_acceptableがルーターで使用されない (2-B)              │
│     │     ↓                                                     │
│     └─ 問題あるワークフローが成功として出力                     │
│                                                                 │
│  [コード品質層]                                                  │
│     │                                                           │
│     └─ 型バリデーション不足 (2-C)                               │
│           ↓                                                     │
│         ランタイムエラーで処理中断                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. 優先度付き改善提案

| 優先度 | 真因 | 改善策 | 影響範囲 |
|--------|------|--------|----------|
| 🔴 高 | 2-A | `weaknesses`に"Critical"が含まれる場合、自動的に`failure_reason="workflow_quality"`を設定 | `llm_evaluator.py` |
| 🔴 高 | 2-B | `is_acceptable`をルーター判定に使用 | `agent.py` |
| 🔴 高 | 2-C | `recommended_apis`の型チェック追加 | `workflow_generation.py` 等 |
| 🟠 中 | 1-A | 動的配列処理パターンをプロンプトに追加 | `workflow_generation.py` プロンプト |
| 🟠 中 | 1-B | タスクチェーンの入出力インターフェース整合性検証 | 新規バリデーター |
| 🟡 低 | 1-C | ネストスキーマへのキーワード伝播 | `sample_input_generator.py` |

---

## 5. 実装済みの改善（本セッション）

### 5.1 キーワード抽出機能の追加

**ファイル**: `sample_input_generator.py`

```python
def _extract_keywords_from_description(description: str) -> list[str]:
    """Extract keywords from task description for contextual sample generation."""
    # 日本語パターンでキーワード抽出
    patterns = [
        r'(.+?)(?:に関する|について|の最新|をGoogle|で検索|を検索|を取得)',
        r'(.+?)(?:ニュース|情報|データ)',
    ]
    ...

def _set_task_context(task_data: dict[str, Any] | None) -> None:
    """Set the task context for keyword-aware sample generation."""
    global _TASK_CONTEXT
    ...
```

**結果**: Task 1で「大谷翔平」が正しく使用されることを確認

### 5.2 ワークフロー構造完全性検証の追加

**ファイル**: `generator.py`

```python
def _validate_workflow_completeness(yaml_content: str) -> tuple[bool, list[str]]:
    """Validate that the generated workflow is structurally complete."""
    # 必須フィールドチェック: version, nodes, source, isResult: true
    # テンプレート切り詰め検出
    # 最小ノード数検証
    ...
```

### 5.3 システムプロンプトへの完全性要件追加

**ファイル**: `workflow_generation.py`

```markdown
## WORKFLOW COMPLETENESS REQUIREMENT (Issue #338) - MANDATORY

**You MUST generate a COMPLETE and STRUCTURALLY VALID workflow.**

### Completeness Checklist (VERIFY BEFORE OUTPUT):
1. ✅ `version: 0.5` - REQUIRED at the top
2. ✅ `nodes:` - REQUIRED section containing all nodes
3. ✅ `source: {}` - REQUIRED empty object for user input
4. ✅ Output node with `isResult: true` - REQUIRED
5. ✅ All template blocks MUST be COMPLETE
6. ✅ All node definitions MUST have required fields
```

---

## 6. 次のステップ

1. **Phase 4**: 評価ルーティングの改善（2-A, 2-B）
2. **Phase 5**: 型バリデーション強化（2-C）
3. **Phase 6**: 動的配列処理パターン追加（1-A）
4. **Phase 7**: タスクチェーンインターフェース検証（1-B）

---

## 関連リンク

- [Issue #338](https://github.com/Kewton/MySwiftAgent/issues/338)
- [Issue #340 - [object Object]問題](https://github.com/Kewton/MySwiftAgent/issues/340)
