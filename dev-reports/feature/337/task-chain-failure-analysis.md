# タスクチェーン実行障害 根本原因分析レポート

**作成日**: 2026-01-02
**関連Issue**: #337 (タスクチェーン Ready-to-Use Output 原則の導入)
**対象Run**: run_1767280709819_wxo4mxh (v1.28)

---

## 概要

v1.28 のタスクチェーン実行で発生した障害を分析し、3つの表層的問題の背後にある**共通の真因**を特定しました。

---

## 問題の階層構造

```
表層問題
├── 問題1: ワークフローYAMLノード参照エラー
├── 問題2: ワークフロー出力 ↔ output_interface不一致
└── 問題3: タスク間データパス不一致

        ↓ 5 Whys 分析

真因（Root Cause）
└── インターフェース契約の強制メカニズム欠如
```

---

## 問題別 5 Whys 分析

### 問題1: ワークフローYAMLノード参照エラー

**現象**: `:execute_search.results` が存在せず `null` になる

| Why | 回答 |
|-----|------|
| Why 1 | ワークフローYAMLで存在しないパスを参照しているから |
| Why 2 | LLMがワークフロー生成時に誤ったパスを出力したから |
| Why 3 | LLMがGoogle Search APIの実際の応答構造を知らないから |
| Why 4 | ワークフロー生成プロンプトにAPI応答スキーマが含まれていないから |
| **Why 5** | **API仕様とワークフロー生成の間に情報連携がないから** |

**真因**: API応答スキーマがワークフロー生成コンテキストに含まれていない

---

### 問題2: ワークフロー出力 ↔ output_interface不一致

**現象**: Task 0の出力がネスト構造で、インターフェース定義と一致しない

| Why | 回答 |
|-----|------|
| Why 1 | GraphAI結果抽出が期待と異なる構造を返すから |
| Why 2 | `_extract_graphai_output` が `output` ノードを探すが、ワークフローは `format_results` を使用 |
| Why 3 | ワークフロー生成時に出力ノード名の規約がないから |
| Why 4 | ワークフロー生成とタスク実行基盤の間で命名規約が共有されていないから |
| **Why 5** | **ワークフロー生成仕様とタスク実行基盤の仕様が分離しているから** |

**真因**: 出力ノード命名規約（`output`）がワークフロー生成に強制されていない

**コード証拠**:

```python
# jobqueue/app/core/worker.py (line 640-644)
output_node = results.get("output")
if output_node is None:
    # No output node, return full results  ← ここで全結果が返される
    return results
```

```yaml
# 生成されたワークフロー
format_results:        # ← "output" ではない
  agent: copyAgent
  isResult: true       # ← isResult は考慮されていない
```

---

### 問題3: タスク間データパス不一致

**現象**: Task 1が期待するパスにデータがない

| Why | 回答 |
|-----|------|
| Why 1 | Task 1のワークフローが `:source.user_input.search_results` を参照するが存在しない |
| Why 2 | Task 0の出力が `{execute_search: {search_results: [...]}}` で、フラットな `search_results` がない |
| Why 3 | 問題2により、output_interfaceで定義した構造ではなく全ノード結果が渡されるから |
| Why 4 | タスク間データ連携がoutput_interface定義を尊重していないから |
| **Why 5** | **output_interface → 実際の出力 → input_interface の変換が自動化されていないから** |

**真因**: インターフェース定義に基づくデータ変換レイヤーが存在しない

---

## 共通の真因（Root Cause）

3つの問題すべてに共通する根本原因:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   インターフェース契約の強制メカニズムが存在しない              │
│                                                                 │
│   - input_interface / output_interface は「宣言」のみ           │
│   - 実際のデータフローは契約を無視して動作                      │
│   - 違反を検出するバリデーションがない                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 現状のデータフロー

```
[インターフェース定義]          [実際のデータフロー]

output_interface: {             GraphAI結果: {
  success: bool                   source: {...},
  search_results: [...]           execute_search: {
  error_message: string             search_results: [...]
}                                 },
       ↓                          format_results: {...}
    無視される                  }
       ↓                               ↓
input_interface: {              user_input: (全結果)
  search_results: [...]                ↓
  summary_format: string        :source.user_input.search_results
}                                      ↓
                                   undefined!
```

### 理想のデータフロー

```
[インターフェース定義]          [実際のデータフロー]

output_interface: {             GraphAI結果
  success: bool                      ↓
  search_results: [...]         output_interface変換
  error_message: string              ↓
}                               {
       ↓                          success: true,
    強制される                    search_results: [...],
       ↓                          error_message: ""
input_interface: {              }
  search_results: [...]              ↓
  summary_format: string        user_input: (変換後データ)
}                                    ↓
                                :source.user_input.search_results
                                     ↓
                                  正常動作!
```

---

## 対策案

### 対策1: 出力ノード命名規約の強制（問題2対策）

**実装難易度**: 低
**効果**: 高

**現状**:
- ワークフロー生成時に出力ノード名が自由
- `_extract_graphai_output` は `output` ノードのみを期待

**対策**:

```python
# A案: ワークフロー生成時に強制
# expertAgent/prompts/workflow_generation/default.yaml に追加

system_prompt: |
  ...
  CRITICAL REQUIREMENT:
  - 出力ノードは必ず "output" という名前にする
  - isResult: true と組み合わせる

  正しい例:
  output:
    agent: copyAgent
    inputs:
      success: true
      search_results: :execute_search.search_results
    isResult: true
```

```python
# B案: 抽出ロジックを isResult 対応に変更
# jobqueue/app/core/worker.py

def _extract_graphai_output(response_data: Any) -> Any:
    results = response_data.get("results", {})

    # isResult: true のノードを探す
    for node_name, node_result in results.items():
        if node_name.endswith("_result") or node_name == "output":
            return node_result

    # フォールバック: 全結果を返す
    return results
```

**推奨**: A案（ワークフロー生成時の強制）

---

### 対策2: output_interface変換レイヤーの追加（問題2, 3対策）

**実装難易度**: 中
**効果**: 高

**概要**: タスク出力を `output_interface` 定義に基づいて変換

```python
# jobqueue/app/core/worker.py

async def _execute_tasks(self, job: Job, tasks: list[Task]) -> None:
    for task in tasks:
        # ... 既存の実行ロジック ...

        # NEW: output_interface に基づく変換
        output_interface = await self._get_output_interface(task.master_id)
        if output_interface:
            task.output_data = self._transform_to_interface(
                raw_output=task.output_data,
                interface_schema=output_interface
            )

def _transform_to_interface(
    self,
    raw_output: dict,
    interface_schema: dict
) -> dict:
    """output_interface定義に基づいてデータを変換"""
    result = {}
    properties = interface_schema.get("properties", {})

    for field_name, field_def in properties.items():
        # 生データから該当フィールドを探索
        value = self._find_field_value(raw_output, field_name)
        result[field_name] = value

    return result
```

---

### 対策3: ワークフロー生成時のAPI応答スキーマ提供（問題1対策）

**実装難易度**: 中
**効果**: 高

**概要**: ワークフロー生成プロンプトにAPI応答スキーマを含める

```yaml
# expertAgent/prompts/workflow_generation/default.yaml

system_prompt: |
  ...

  ## API Response Schemas

  When using Google Search API (/v1/utility/google_search):
  - Response structure:
    {
      "search_results": [
        {"title": str, "link": str, "knowledge": str}
      ],
      "search_results_count": int,
      "status": str
    }
  - Note: Use "link" not "url", "knowledge" not "snippet"

  When referencing API response in workflow:
  - Correct: :execute_search.search_results
  - Wrong: :execute_search.results
```

**自動化案**:

```python
# expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/utils/workflow_helper.py

async def generate_workflow_for_task(task_master, langfuse_handler):
    # API応答スキーマを取得
    recommended_apis = task_master.get("recommended_apis", [])
    api_schemas = await _fetch_api_response_schemas(recommended_apis)

    # プロンプトに追加
    context = {
        "task_master": task_master,
        "api_response_schemas": api_schemas  # NEW
    }

    # ワークフロー生成
    ...
```

---

### 対策4: インターフェース整合性検証（問題3対策）

**実装難易度**: 低
**効果**: 中

**概要**: ジョブ生成時にタスク間インターフェースの整合性を検証

```python
# expertAgent/aiagent/langgraph/jobTaskGeneratorAgents/nodes/evaluator.py

def check_interface_compatibility(tasks: list[dict]) -> list[str]:
    """タスク間のインターフェース整合性を検証"""
    warnings = []

    for i in range(len(tasks) - 1):
        current_task = tasks[i]
        next_task = tasks[i + 1]

        current_output = current_task.get("output_interface", {})
        next_input = next_task.get("input_interface", {})

        # 必須フィールドの存在確認
        required_fields = next_input.get("required", [])
        available_fields = current_output.get("properties", {}).keys()

        for field in required_fields:
            if field not in available_fields:
                warnings.append(
                    f"Task {i+1} output missing field '{field}' "
                    f"required by Task {i+2}"
                )

    return warnings
```

---

## 対策優先度

| 優先度 | 対策 | 効果 | 難易度 | 対象問題 |
|--------|------|------|--------|---------|
| 1 | 出力ノード命名規約の強制 | 高 | 低 | 問題2 |
| 2 | output_interface変換レイヤー | 高 | 中 | 問題2, 3 |
| 3 | API応答スキーマ提供 | 高 | 中 | 問題1 |
| 4 | インターフェース整合性検証 | 中 | 低 | 問題3 |

---

## 実装ロードマップ

### Phase 1: 緊急対応（1-2日）

1. **ワークフロー生成プロンプト修正**
   - 出力ノード名を `output` に強制
   - Google Search APIの正しいパス参照を明記

2. **v1.28ワークフロー手動修正**
   - `:execute_search.results` → `:execute_search.search_results`
   - `format_results` → `output`

### Phase 2: 短期対応（1週間）

3. **output_interface変換レイヤー実装**
   - jobqueue/app/core/worker.py に変換ロジック追加
   - 単体テスト作成

4. **インターフェース整合性検証実装**
   - evaluator.py に検証関数追加
   - ジョブ生成時に警告出力

### Phase 3: 中期対応（2-3週間）

5. **API応答スキーマ自動提供**
   - expert_agent_capabilities.yaml にスキーマ追加
   - ワークフロー生成コンテキストに自動注入

6. **ワークフロー生成後検証**
   - 生成されたYAMLの参照パスを検証
   - 不正なパスがあれば再生成

---

## 結論

今回の障害は、**インターフェース契約がシステム全体で強制されていない**という設計上の問題に起因しています。

`input_interface` / `output_interface` は現状「ドキュメント」としてしか機能しておらず、実際のデータフローはこれらの契約を無視して動作しています。

対策の本質は、**インターフェース契約を「宣言」から「強制」に変えること**です。

---

## 参考: 関連コード箇所

| コンポーネント | ファイル | 行 | 役割 |
|---------------|---------|-----|------|
| GraphAI結果抽出 | jobqueue/app/core/worker.py | 606-661 | `_extract_graphai_output` |
| テンプレート解決 | jobqueue/app/services/template_resolver.py | 28-70 | タスク間参照解決 |
| ワークフロー生成 | expertAgent/.../workflow_generation.py | 全体 | LLMによるYAML生成 |
| ワークフロー実行 | graphAiServer/src/services/graphai.ts | 187-330 | GraphAI実行 |
| TaskMaster設定 | jobqueue (API) | - | body_template定義 |

---

**レポート作成者**: Claude Code (Issue #337 調査)
